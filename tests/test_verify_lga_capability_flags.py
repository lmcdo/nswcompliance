"""scripts/verify_lga_capability_flags.py's comparison logic, without a database.

The script exists because frontend-nextjs/lib/lga-data/*.ts carries per-council
boolean claims (e.g. verify-lgas.ts's `hasDcpData: true`) that can go stale
without moving any of the aggregate figures scripts/verify_coverage_stats.py
already watches. These tests pin `find_drift`, the pure decision function the
script calls once it has fetched live counts from the database -- it takes a
plain {key: count} dict rather than a cursor, so the four failure/success
shapes below are exercised with no DATABASE_URL and no network call.

Each test name states the scenario the task asked this suite to cover.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPT = _ROOT / "scripts" / "verify_lga_capability_flags.py"

_spec = importlib.util.spec_from_file_location("verify_lga_capability_flags_under_test", _SCRIPT)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

find_drift = _mod.find_drift
parse_flag_entries = _mod.parse_flag_entries
db_slug = _mod.db_slug


def _entry(name: str, slug: str, **flags) -> dict:
    """Build one parsed-entry dict the way parse_flag_entries() would."""
    return {"name": name, "slug": slug, "_live_key": slug, **flags}


# ── find_drift: the four scenarios the task named ────────────────────────────

def test_flag_that_matches_the_data_is_not_drift():
    """A council claiming the flag, backed by at least one live row: clean."""
    entries = [_entry("Blacktown", "blacktown", hasDcpData=True)]
    live_counts = {"blacktown": 33}
    assert find_drift(entries, "hasDcpData", live_counts) == []


def test_flag_that_claims_a_capability_the_data_lacks_is_drift():
    """A council with a live row (key present) but zero of them: this is the
    exact failure mode the script exists to catch -- a matched council whose
    supporting rows have since been removed, not one that was never onboarded.
    """
    entries = [_entry("Lane Cove", "lane-cove", hasDcpData=True)]
    live_counts = {"lane-cove": 0}
    drift = find_drift(entries, "hasDcpData", live_counts)
    assert len(drift) == 1
    assert "Lane Cove" in drift[0]
    assert "lane-cove" in drift[0]


def test_council_in_file_missing_from_database_is_drift():
    """A council the file claims the flag for, absent from live_counts entirely
    (no key at all, not merely a zero) -- also unsupported, and must not raise
    a KeyError. This is the shape of the 8 real councils this check found on
    2026-09-10 (lane-cove, hawkesbury, wollongong, clarence-valley, yass-valley,
    bathurst-regional, tamworth-regional, forbes): none of them has ANY row in
    lga_registry, so the live-count dict never gets a key for them at all.
    """
    entries = [_entry("Forbes", "forbes", hasDcpData=True)]
    live_counts: dict[str, int] = {}  # 'forbes' key never fetched/added
    drift = find_drift(entries, "hasDcpData", live_counts)
    assert len(drift) == 1
    assert "Forbes" in drift[0]


def test_database_council_missing_from_file_is_silently_ignored():
    """A council present in live_counts that no entry in the file claims the
    flag for must not be reported as drift -- this script checks one direction
    only (does the FILE'S claim hold up?), never manufactures a claim nobody
    made. A council in the database that the file has never heard of is a
    missed opportunity, not an overclaim, and is out of scope by design.
    """
    entries = [_entry("Blacktown", "blacktown", hasDcpData=True)]
    live_counts = {"blacktown": 33, "some-other-council": 12}
    assert find_drift(entries, "hasDcpData", live_counts) == []


# ── find_drift: supporting behaviour ─────────────────────────────────────────

def test_a_false_claim_is_never_checked_even_with_zero_live_rows():
    """FALSE cannot overclaim a capability -- checking it would just re-report
    every not-yet-onboarded council as 'drift', which is noise, not a finding.
    """
    entries = [_entry("Somewhere", "somewhere", hasDcpData=False)]
    live_counts: dict[str, int] = {}
    assert find_drift(entries, "hasDcpData", live_counts) == []


def test_mixed_entries_report_only_the_unsupported_true_claims():
    """A realistic mixed batch: one clean true, one drifted true, one false
    (ignored regardless of its live count) -- only the drifted one is reported.
    """
    entries = [
        _entry("Blacktown", "blacktown", hasDcpData=True),
        _entry("Forbes", "forbes", hasDcpData=True),
        _entry("Somewhere", "somewhere", hasDcpData=False),
    ]
    live_counts = {"blacktown": 33, "somewhere": 0}  # 'forbes' absent entirely
    drift = find_drift(entries, "hasDcpData", live_counts)
    assert len(drift) == 1
    assert "Forbes" in drift[0]


# ── db_slug: the one hard-coded merger exception ─────────────────────────────

def test_db_slug_applies_the_hills_shire_override():
    """The one confirmed case where a straight hyphen-to-underscore swap is
    wrong: lga_registry's slug is 'the_hills', not 'the_hills_shire' (checked
    against the live database on 2026-09-10, not assumed).
    """
    assert db_slug("the-hills-shire") == "the_hills"


def test_db_slug_default_swaps_hyphens_for_underscores():
    assert db_slug("canterbury-bankstown") == "canterbury_bankstown"
    assert db_slug("ku-ring-gai") == "ku_ring_gai"


# ── parse_flag_entries: sanity against the real files ────────────────────────
# Not a database test -- these files ship in the repo, so parsing them is as
# available as any other fixture. Pins the parser against the two real files
# rather than only a synthetic string, since a regex that only ever sees its
# own test fixture is the way this kind of parser silently drifts from the
# file it is meant to read.

_VERIFY_LGAS_TS = _ROOT / "frontend-nextjs" / "lib" / "lga-data" / "verify-lgas.ts"
_GRANNY_FLAT_LGAS_TS = _ROOT / "frontend-nextjs" / "lib" / "lga-data" / "granny-flat-lgas.ts"


@pytest.mark.skipif(not _VERIFY_LGAS_TS.exists(), reason="verify-lgas.ts not present in this checkout")
def test_parses_every_verify_lgas_entry_with_a_boolean_flag():
    entries = parse_flag_entries(str(_VERIFY_LGAS_TS), ["hasDcpData"])
    assert len(entries) >= 30, "expected 30+ councils in verify-lgas.ts"
    assert all(isinstance(e["hasDcpData"], bool) for e in entries)
    slugs = [e["slug"] for e in entries]
    assert len(slugs) == len(set(slugs)), "duplicate slug parsed out of verify-lgas.ts"


@pytest.mark.skipif(not _GRANNY_FLAT_LGAS_TS.exists(), reason="granny-flat-lgas.ts not present in this checkout")
def test_parses_every_granny_flat_entry_with_both_boolean_flags():
    entries = parse_flag_entries(str(_GRANNY_FLAT_LGAS_TS), ["hasFloodData", "hasAriData"])
    assert len(entries) >= 15, "expected 15+ councils in granny-flat-lgas.ts"
    assert all(isinstance(e["hasFloodData"], bool) and isinstance(e["hasAriData"], bool) for e in entries)
