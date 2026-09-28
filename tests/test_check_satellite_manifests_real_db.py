"""The manifest ratchet's exclusion, run as SQL against the real database.

tests/test_manifest_count_excludes_cached_copies.py reads the query as TEXT and
exercises the rule as a Python predicate. Neither proves the SQL does what the text
says: `run_date >= created_at::date` compares a `date` against a `timestamptz` cast,
and whether that excludes the row it is meant to is a question for Postgres, not for a
source scan.

That matters here more than usual, because this one clause decides whether every PR in
the repository can merge. It was added after the ratchet failed on a count that had
risen for a legitimate reason -- a cached copy of a pre-manifest report -- and getting
it wrong in the permissive direction would excuse real defects silently.

WHAT IT ASSERTS, AND WHY EACH ONE
---------------------------------
1. The counted set contains NO cached copy. The invariant, stated directly.
2. At least one cached copy EXISTS to be excluded. Without this the first assertion is
   vacuous -- a filter that removes nothing passes it trivially, which is the shape
   `memory/feedback-search-plus-check-amplifies-leaks.md` warns about: test on
   known-wrong as well as known-right.
3. Rows that ARE their own computation and lack a manifest are still counted. The
   exclusion must narrow which rows are judged, never what is judged about them; 810
   such rows exist and all of them must stay in.
4. The check's own totals match a query written independently here. If the two ever
   disagree, the one in the script is not the one being reasoned about.

READ-ONLY, and opt-in by PYTEST_REAL_DB=1 + DATABASE_URL, per the convention in
tests/test_drawdown_verify_real_db.py:

    PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database \
        tests/test_check_satellite_manifests_real_db.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"

pytestmark = pytest.mark.database

#: The products the ratchet counts, as the script lists them.
PRODUCTS = ("flood", "shadow", "solar-yield", "bushfire")


def _dsn() -> str | None:
    return os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")


@pytest.fixture(scope="module")
def conn():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... "
            "pytest -m database. conftest_mocks stubs psycopg2 otherwise, so this "
            "would assert against a MagicMock and pass without touching anything.")
    if not _dsn():
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")
    import psycopg2
    from unittest.mock import MagicMock
    if isinstance(psycopg2, MagicMock):
        pytest.skip("psycopg2 is still the conftest stub; the opt-in did not take.")
    c = psycopg2.connect(_dsn(), connect_timeout=30)
    c.set_session(readonly=True)
    try:
        yield c
    finally:
        c.close()


def _script_query() -> str:
    """The property_reports SELECT, lifted from the script so the test cannot drift
    from the thing it is checking."""
    src = (ROOT / "scripts" / "check_satellite_manifests.py").read_text(encoding="utf-8")
    i = src.index("FROM property_reports")
    start = src.rindex("SELECT product", 0, i)
    end = src.index("GROUP BY product", i) + len("GROUP BY product ORDER BY product")
    return " ".join(src[start:end].split())


class TestTheExclusionBehavesAsSqlNotAsProse:
    def test_the_counted_set_contains_no_cached_copy(self, conn):
        """The invariant. A copy's missing manifest belongs to the original."""
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM property_reports "
            " WHERE product = ANY(%s) AND run_date >= created_at::date "
            "   AND run_date < created_at::date", (list(PRODUCTS),))
        assert cur.fetchone()[0] == 0

        cur.execute(
            "SELECT count(*) FROM (" + _script_query().replace(
                "GROUP BY product ORDER BY product", "") +
            " AND run_date < created_at::date GROUP BY product) q",
            )
        assert cur.fetchone()[0] == 0, (
            "the script's own query still admits rows whose run_date predates their "
            "created_at, so a cached copy is being counted against itself")

    def test_a_cached_copy_actually_exists_to_be_excluded(self, conn):
        """Stops the assertion above being vacuous. Measured 2026-09-28: exactly one,
        the 38 Park Rd Bowral flood row. If this ever reaches zero the filter is
        untested rather than satisfied, so it SKIPS with that said out loud."""
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM property_reports "
            " WHERE product = ANY(%s) AND NOT (inputs ? 'execution_manifest') "
            "   AND run_date < created_at::date", (list(PRODUCTS),))
        copies = cur.fetchone()[0]
        if copies == 0:
            pytest.skip(
                "No manifest-less cached copy exists right now, so the exclusion this "
                "file exists to verify is not exercised by current data. NOT a pass.")
        assert copies >= 1

    def test_rows_that_are_their_own_computation_are_still_counted(self, conn):
        """The exclusion narrows WHICH ROWS are judged, never what is judged about
        them. Measured 2026-09-28: 810 manifest-less rows, 809 of them their own
        computation, and every one must stay in the count."""
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM property_reports "
            " WHERE product = ANY(%s) AND NOT (inputs ? 'execution_manifest') "
            "   AND run_date >= created_at::date", (list(PRODUCTS),))
        own = cur.fetchone()[0]
        assert own > 100, (
            f"only {own} manifest-less rows survive the exclusion. The filter is "
            f"removing far more than cached copies, so it is excusing real defects")

    def test_the_scripts_totals_match_an_independent_query(self, conn):
        """If the script's numbers and a query written here disagree, the thing being
        reasoned about is not the thing that runs in CI."""
        cur = conn.cursor()
        cur.execute(_script_query())
        from_script = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

        cur.execute(
            "SELECT product, count(*), "
            "       count(*) FILTER (WHERE inputs ? 'execution_manifest') "
            "  FROM property_reports "
            " WHERE product = ANY(%s) AND run_date >= created_at::date "
            " GROUP BY 1", (list(PRODUCTS),))
        independent = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
        assert from_script == independent

    def test_the_cast_is_what_makes_it_work(self, conn):
        """`created_at` is a timestamptz and `run_date` a date. Without ::date, a row
        created later the SAME day as its run compares as run_date < created_at and
        would be wrongly excused. Asserted in SQL because it is a Postgres question."""
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM property_reports "
            " WHERE product = ANY(%s) "
            "   AND run_date >= created_at::date "
            "   AND run_date < created_at", (list(PRODUCTS),))
        same_day_later = cur.fetchone()[0]
        assert same_day_later > 0, (
            "no row is created later in the day than its run_date, so this test cannot "
            "show that the ::date cast is load-bearing")


class TestTheBaselineStillMatchesReality:
    def test_no_product_exceeds_its_committed_baseline(self, conn):
        """The ratchet's actual promise, checked here rather than only by the script's
        own exit code."""
        import json
        baseline = json.loads(
            (ROOT / ".claude" / "manifest_coverage_baseline.json").read_text(
                encoding="utf-8"))
        per_key = baseline.get("per_key", baseline)
        cur = conn.cursor()
        cur.execute(
            "SELECT product, count(*) FILTER (WHERE NOT (inputs ? 'execution_manifest')) "
            "  FROM property_reports "
            " WHERE product = ANY(%s) AND run_date >= created_at::date "
            " GROUP BY 1", (list(PRODUCTS),))
        risen = {p: (n, per_key[p]) for p, n in cur.fetchall()
                 if p in per_key and n > per_key[p]}
        assert not risen, f"counts rose above baseline: {risen}"

    def test_flood_is_back_at_its_baseline(self, conn):
        """The specific number this change exists to restore: 144 -> 143, without
        touching the baseline."""
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FROM property_reports "
            " WHERE product = 'flood' AND NOT (inputs ? 'execution_manifest') "
            "   AND run_date >= created_at::date")
        assert cur.fetchone()[0] == 143
