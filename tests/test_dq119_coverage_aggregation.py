"""A finding that is recorded everywhere and counted nowhere.

`ai_extractor.coverage_gap()` has scored every extraction for months, and
`dcp_extract_changed` stamps the verdict onto each review-queue row as a
`suspect_reason`. Nobody aggregated it, so `ashfield/chapter-a-miscellaneous`
could record "15/15 TOC sections missing" and keep serving an older extraction
with no one told. DQ-119 is that aggregation.

These tests cover the SHAPE of the query, not the live count -- no network, no
database. The count is exercised by running the probe. What is guarded here is
the three ways the query can be simplified into something that still returns a
number and no longer means anything, each of which this repo has already
shipped once under a different id.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import dq_probe_live as probe  # noqa: E402

DQ = "DQ-119"


def _sql_and_params() -> tuple[str, tuple]:
    headline, sql, params, meaning = probe.PROBES[DQ]
    return " ".join(sql.split()), tuple(params)


def test_the_row_exists_in_both_the_probe_and_the_ledger():
    """A row in one file and not the other is the state dq_check.py refuses.

    The probe is what runs; the ledger is what a person reads. A probe with no
    ledger entry is an unwatched check, and a ledger entry with no probe is a
    claim with nothing behind it.
    """
    assert DQ in probe.PROBES
    checks = json.loads((ROOT / ".claude" / "dq_checks.json").read_text(encoding="utf-8"))["checks"]
    assert DQ in checks, f"{DQ} is in the probe but not dq_checks.json"
    assert checks[DQ]["declared"] == "open"
    tracker = (ROOT / ".claude" / "DATA_QUALITY_TRACKER.md").read_text(encoding="utf-8")
    assert f"{DQ}:" in tracker, f"{DQ} is not in DATA_QUALITY_TRACKER.md"


def test_it_counts_the_latest_extraction_only():
    """Counting every queue row reports faults a later read already fixed.

    `woollahra/chapter-b3-general-development` is exactly that case: it carries
    a `coverage_fail` on a SUPERSEDED batch and has been clean since. A check
    that never forgets is permanently red, which is as useless as permanently
    green and trains people to ignore the ledger.
    """
    sql, _ = _sql_and_params()
    assert "DISTINCT ON (q.council, q.chapter_key)" in sql
    assert re.search(r"ORDER BY q\.council, q\.chapter_key, q\.created_at DESC", sql), sql


def test_it_counts_served_chapters_not_queued_ones():
    """DQ-97's 2026-09-10 lesson, applied before it can happen again.

    DQ-97 counted `dcp_review_queue WHERE status='pending'`. On 2026-09-09 the
    backlog was approved in one night and the count fell 574 -> 0 while nothing
    was repaired -- the defect moved downstream into the served set and the
    check went green by the population draining. This query must be anchored to
    `regulatory_provisions`, which an operator cannot drain by approving rows.
    """
    sql, _ = _sql_and_params()
    assert "regulatory_provisions" in sql
    assert "p.is_current AND p.v2_is_actionable" in sql
    assert "EXISTS" in sql
    assert "status" not in sql, (
        "the count must not depend on review status -- that is the population "
        "an operator can drain without repairing anything")


def test_coverage_unknown_is_counted_not_excused():
    """The third state. Absence of evidence is not a pass.

    `coverage_unknown` means the contents page could not be read at all, so
    there is no list to check the extraction against. Dropping it would make
    this row green on exactly the documents nobody can verify -- the DQ-30
    "0% drift" shape, a check that cannot fail where it matters most.
    """
    _, params = _sql_and_params()
    assert any("coverage_unknown" in p for p in params), params
    assert any("coverage_fail" in p for p in params), params


def test_inert_chapters_are_excluded_but_inactive_is_not_the_same_as_clean():
    """Scope, stated rather than assumed.

    An inert chapter serves nothing, so a coverage fault in it exposes no one.
    `is_active` alone is not enough and `COALESCE` is required because a NULL
    `is_inert` must read as "not inert" rather than dropping the row.
    """
    sql, _ = _sql_and_params()
    assert "r.is_active" in sql
    assert "NOT COALESCE(r.is_inert, false)" in sql, (
        "a NULL is_inert must not silently remove a served chapter from the count")


def test_the_meaning_says_approving_the_queue_does_not_clear_it():
    """The ledger's text is read by whoever tries to clear the row.

    If it does not say so, the first thing someone will try is approving the
    pending rows, because that is what makes most queue-shaped numbers fall.
    """
    _, _, _, meaning = probe.PROBES[DQ]
    assert "does NOT clear by approving" in meaning or "not clear by approving" in meaning


@pytest.mark.parametrize("wrong", [
    "SELECT count(*) FROM dcp_review_queue WHERE suspect_reason LIKE '%coverage_fail%'",
    "SELECT count(*) FROM dcp_review_queue WHERE status = 'pending'",
])
def test_the_naive_queries_this_replaces_are_not_what_shipped(wrong: str):
    """Guard against a future simplification back to the shapes that failed.

    Both of these return a plausible number. The first never forgets a
    superseded batch; the second is the population DQ-97 was drained out of.
    """
    sql, _ = _sql_and_params()
    assert sql != " ".join(wrong.split())
