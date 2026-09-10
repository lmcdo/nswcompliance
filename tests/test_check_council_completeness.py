"""Comparison logic for the per-council completeness check.

These are pure-function tests over `compare()`. No database: the whole point of
splitting measurement from comparison is that the part with the judgement in it
can be tested against constructed numbers, including numbers production has never
produced. The real-DB round trip lives in
tests/test_check_council_completeness_real_db.py.

The numbers used are the real defect this check exists to catch, not invented
ones: Ashfield's precinct fill fell from 733/2041 to 118/2041 on 2026-09-10, and
Marrickville's from 785/2403 to 37/2403.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

# check_council_completeness resolves .env at import time and, failing that,
# shells out to `git rev-parse` to find the main checkout from inside a worktree.
# Neither is wanted during collection of a test that never opens a connection, so
# a value is present for the import and removed immediately after. The module
# only reads DATABASE_URL inside run(), which these tests do not call.
_SAVED_DB_URL = os.environ.get("DATABASE_URL")
os.environ["DATABASE_URL"] = "postgresql://unused/import-only"
try:
    import check_council_completeness as ccc  # noqa: E402
finally:
    if _SAVED_DB_URL is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = _SAVED_DB_URL


def snap(served, **counts):
    """A snapshot with every watched field filled to `served` unless overridden."""
    full = {f: served for f in ccc.WATCHED_FIELDS}
    full.update(counts)
    return {"served": served, "counts": full}


def actionable(findings):
    return [f for f in findings if f["severity"] in (ccc.CRITICAL, ccc.STANDARD)]


def by_field(findings, field):
    return [f for f in findings if f["field"] == field]


# --- no baseline is not a pass --------------------------------------------

def test_first_ever_recording_is_info_not_a_finding():
    out = ccc.compare("ashfield", None, snap(2041))
    assert len(out) == 1
    assert out[0]["severity"] == ccc.INFO
    assert out[0]["state"] == "NO_BASELINE"
    assert actionable(out) == []


def test_a_field_absent_from_the_old_snapshot_is_no_baseline_not_a_drop():
    """The failure direction that matters.

    A field added to WATCHED_FIELDS later has no entry in older rows. Reading
    that missing key as 0 would manufacture a 100% "gain" on the first run and a
    fabricated drop the day the field is removed from the watch list. Absence of
    a measurement is not a measurement.
    """
    prev = snap(2041)
    del prev["counts"]["v2_provision_type"]
    out = ccc.compare("ashfield", prev, snap(2041))
    findings = by_field(out, "v2_provision_type")
    assert len(findings) == 1
    assert findings[0]["state"] == "NO_BASELINE"
    assert findings[0]["severity"] == ccc.INFO
    assert actionable(out) == []


def test_a_corrupt_counts_blob_does_not_read_as_zero():
    """load_previous returns None for a non-dict `counts`, so the caller sees
    'no baseline'. Asserted here at the compare boundary: None must never be
    treated as a snapshot of zeros, which would report every field as emptied."""
    out = ccc.compare("ashfield", None, snap(2041, v2_precinct_id=733))
    assert actionable(out) == []


# --- the defect it was built for ------------------------------------------

def test_the_ashfield_precinct_collapse_is_critical_and_quantified():
    prev = snap(2041, v2_precinct_id=733)
    now = snap(2041, v2_precinct_id=118)
    findings = by_field(ccc.compare("ashfield", prev, now), "v2_precinct_id")
    assert len(findings) == 1
    f = findings[0]
    assert f["severity"] == ccc.CRITICAL
    assert f["state"] == "DROP"
    # The message must carry the numbers, not just say "dropped": an alert that
    # does not say how far is one somebody has to go and query themselves.
    assert "35.9%" in f["message"] and "5.8%" in f["message"]
    assert "733/2041" in f["message"] and "118/2041" in f["message"]
    assert "30.1pp" in f["message"]


def test_the_marrickville_collapse_is_also_caught():
    prev = snap(2403, v2_precinct_id=785)
    now = snap(2403, v2_precinct_id=37)
    findings = by_field(ccc.compare("marrickville", prev, now), "v2_precinct_id")
    assert findings and findings[0]["severity"] == ccc.CRITICAL


# --- the confusable negative ----------------------------------------------

def test_an_unchanged_council_produces_nothing():
    s = snap(2041, v2_precinct_id=733, v2_provision_type=1426)
    assert ccc.compare("ashfield", s, dict(s)) == []


def test_a_field_that_improves_is_not_a_finding():
    prev = snap(2041, v2_provision_type=1426)
    now = snap(2041, v2_provision_type=2041)
    assert actionable(ccc.compare("ashfield", prev, now)) == []


def test_a_fall_just_under_the_threshold_is_not_reported():
    """Directly below MATERIAL_DROP_PP. Pairs with the test above it: a threshold
    only means something if a value on each side of it is asserted."""
    prev = snap(1000, v2_topic=1000)
    now = snap(1000, v2_topic=955)  # 100.0% -> 95.5%, a 4.5pp fall
    assert by_field(ccc.compare("x", prev, now), "v2_topic") == []


def test_a_fall_at_exactly_the_threshold_is_reported():
    prev = snap(1000, v2_topic=1000)
    now = snap(1000, v2_topic=950)  # exactly 5.0pp
    findings = by_field(ccc.compare("x", prev, now), "v2_topic")
    assert findings and findings[0]["severity"] == ccc.STANDARD


def test_a_large_fall_escalates_to_critical():
    prev = snap(1000, v2_topic=1000)
    now = snap(1000, v2_topic=740)  # 26.0pp, past CRITICAL_DROP_PP
    findings = by_field(ccc.compare("x", prev, now), "v2_topic")
    assert findings and findings[0]["severity"] == ccc.CRITICAL


# --- served-row movement ---------------------------------------------------

def test_a_council_that_serves_nothing_is_critical_and_stops_there():
    """0/0 makes every per-field ratio meaningless, so the per-field loop must
    not run: 'precinct 100% -> 0%' beside 'this council serves nothing' is six
    restatements of one fact, and noise is how an alert channel dies."""
    out = ccc.compare("ashfield", snap(2041, v2_precinct_id=733), snap(0, **{
        f: 0 for f in ccc.WATCHED_FIELDS}))
    assert len(out) == 1
    assert out[0]["severity"] == ccc.CRITICAL
    assert out[0]["field"] == "served"
    assert "serves nothing" in out[0]["message"]


def test_a_small_served_drop_is_tolerated():
    """A re-extraction legitimately changes row counts -- marrickville's heritage
    chapter went to 739 live from 680 superseded on a normal run."""
    out = by_field(ccc.compare("x", snap(1000), snap(950)), "served")
    assert out == []


def test_a_material_served_drop_is_standard():
    out = by_field(ccc.compare("x", snap(1000), snap(800)), "served")
    assert out and out[0]["severity"] == ccc.STANDARD
    assert "20.0% fewer" in out[0]["message"]


def test_losing_half_a_council_is_critical():
    out = by_field(ccc.compare("x", snap(1000), snap(400)), "served")
    assert out and out[0]["severity"] == ccc.CRITICAL


def test_new_rows_arriving_without_a_field_is_a_finding():
    """The #1080 shape seen from the other side: nothing was deleted, but 1,000
    new rows landed carrying no precinct key, so the served set is now half
    unkeyed. A check that only looked at absolute counts would see 733 -> 733
    and say nothing."""
    prev = snap(1000, v2_precinct_id=1000)
    now = snap(2000, v2_precinct_id=1000)
    findings = by_field(ccc.compare("x", prev, now), "v2_precinct_id")
    assert findings and findings[0]["severity"] == ccc.CRITICAL


# --- small councils --------------------------------------------------------

def test_a_small_council_is_compared_on_absolute_counts():
    """inner_west serves 11 rows; one row is 9.1pp, so a ratio rule would report
    every ordinary edit."""
    prev = snap(11, v2_topic=11)
    now = snap(11, v2_topic=10)
    findings = by_field(ccc.compare("inner_west", prev, now), "v2_topic")
    assert findings and findings[0]["severity"] == ccc.STANDARD
    assert "small council" in findings[0]["message"]


def test_a_small_council_losing_rows_does_not_report_every_field():
    """If the council genuinely shrank, each field's count falls with it. That is
    the served-count finding, reported once -- not once per field."""
    prev = snap(15, v2_topic=15, v2_precinct_id=15)
    now = snap(12, v2_topic=12, v2_precinct_id=12)
    assert by_field(ccc.compare("x", prev, now), "v2_topic") == []
    assert by_field(ccc.compare("x", prev, now), "v2_precinct_id") == []


def test_the_small_council_boundary_matches_the_constant():
    """Pinned to MIN_SERVED_FOR_RATIO rather than to 20, so moving the constant
    moves the test with it instead of silently contradicting it."""
    n = ccc.MIN_SERVED_FOR_RATIO
    prev = snap(n, v2_topic=n)
    now = snap(n, v2_topic=n - 1)
    findings = by_field(ccc.compare("x", prev, now), "v2_topic")
    # At exactly the boundary the ratio path applies; 1 row of MIN_SERVED is
    # 5pp when MIN_SERVED is 20, so this is reported either way -- what is
    # asserted is WHICH path produced it.
    assert findings
    assert "small council" not in findings[0]["message"]


# --- the watch list itself -------------------------------------------------

def test_zone_fill_is_not_watched():
    """v2_applicable_zones is 100% populated for every council because the #1081
    write guard falls back to ['ALL']. Watching it as a fill count would be a
    check that cannot fail; zone health comes from validate_zone_code_validity.py.
    Pinned so that re-adding it has to be a deliberate act."""
    assert "v2_applicable_zones" not in ccc.WATCHED_FIELDS


# --- parsing the precinct-exposure audit ----------------------------------

_AUDIT_OUTPUT = """LGA                   bounds  conn  keyed councils                   rule?  status
------------------------------------------------------------------------------
City of Parramatta        89    47  parramatta                       YES    protected
Woollahra                 14    14  woollahra                        NO     EXPOSED - re-extract un-keys it

>>> 1 LGA(s) EXPOSED (keyed, no reproducible rule): Woollahra
>>> Add a rule to scripts/derive_precinct_keys.py RULES, or do not re-extract them.
"""


def test_exposed_lgas_come_from_the_summary_line():
    assert ccc.parse_exposed(_AUDIT_OUTPUT) == {"Woollahra"}


def test_a_multi_word_lga_name_survives_parsing():
    """The bug this parser replaced: taking the first token off a table row turns
    'City of Parramatta' into 'City'. That name matches nothing, so it would read
    as a NEW exposure on the next run and a disappearance on the one after --
    an alert that invents its own churn."""
    out = _AUDIT_OUTPUT.replace(
        ">>> 1 LGA(s) EXPOSED (keyed, no reproducible rule): Woollahra",
        ">>> 2 LGA(s) EXPOSED (keyed, no reproducible rule): City of Parramatta, Woollahra")
    assert ccc.parse_exposed(out) == {"City of Parramatta", "Woollahra"}


def test_no_exposure_parses_to_an_empty_set():
    assert ccc.parse_exposed("All keyed LGAs have a reproducible rule.\n") == set()


def test_empty_output_does_not_raise():
    """The audit could fail to run at all; the parser must return, not explode,
    so the caller can report the failure as a finding."""
    assert ccc.parse_exposed("") == set()
    assert ccc.parse_exposed("   \n\n  \n") == set()


def test_the_watched_fields_are_the_ones_a_commit_writes():
    assert set(ccc.WATCHED_FIELDS) == {
        "v2_precinct_id", "ref_number", "pdf_page",
        "v2_topic", "v2_provision_type", "v2_applicable_dev_types",
    }
