"""dcp_fidelity_gate.py's chapter-scoping SQL (chapters_query), verified
against the REAL production database -- not conftest_mocks.py's MagicMock
stub, and not a hand-copied approximation of the query in a mock cursor.

Why this needs a real connection and not a mock: the whole point of the
scoping change (2026-09-07, in direct response to "only deal with provisions
that are being served and in scope") is a correlated EXISTS subquery against
regulatory_provisions -- a mock cursor's .fetchall() just returns whatever
the test hard-codes, so it can prove the Python calling code handles rows
correctly but can never prove the SQL ITSELF selects the right chapters.
This file proves the query against three real, already-verified-by-hand
fixtures from the same investigation that motivated the change:
  - blacktown/part-a-car-parking: confirmed zero live+actionable provisions
    exist under this exact (council, chapter_key) -- must be EXCLUDED by
    default, INCLUDED with --include-backlog.
  - ashfield/chapter-d-precinct-guidelines: confirmed real live+actionable
    provisions exist -- must be INCLUDED by default.
  - a council/chapter combination that has never existed, in either table --
    must never appear regardless of the flag (guards against a query that
    accidentally matches everything).

Opt-in via PYTEST_REAL_DB=1, @pytest.mark.database (deselected by default
per pytest.ini), following the exact convention tests/test_drawdown_verify_
real_db.py already established -- not a new pattern.

Run it:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_dcp_fidelity_gate_real_db.py -v
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

# Same reasoning as test_drawdown_verify_real_db.py (Sol cross-review,
# 2026-09-04): only load the real DATABASE_URL into the process when the
# real-DB flag is explicitly set, so a plain `pytest` run never has it in
# scope even though psycopg2 stays stubbed for it anyway.
_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

import dcp_fidelity_gate as gate  # noqa: E402  (after dotenv/marker setup)


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip(
            "Real-DB test. Run with: PYTEST_REAL_DB=1 DATABASE_URL=... "
            "pytest -m database tests/test_dcp_fidelity_gate_real_db.py"
        )
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def _matched_chapters(council, chapter, include_backlog):
    import psycopg2
    conn = psycopg2.connect(os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL"))
    try:
        cur = conn.cursor()
        sql, params = gate.chapters_query(council, chapter, include_backlog)
        cur.execute(sql, params)
        return cur.fetchall()
    finally:
        conn.close()


class TestChaptersQueryAgainstRealData:
    def test_backlog_chapter_excluded_by_default(self):
        """blacktown/part-a-car-parking: measured live 2026-09-07, zero
        regulatory_provisions rows exist under this (council, chapter_key) at
        all -- confirmed the actual chapter behind blacktown's real 36 pending
        review-queue rows is not yet approved for the first time, not a
        chapter with stale-but-fine served content."""
        _skip_if_no_real_db()
        rows = _matched_chapters("blacktown", "part-a-car-parking", include_backlog=False)
        assert rows == []

    def test_backlog_chapter_included_with_flag(self):
        """The same chapter must reappear the moment --include-backlog is
        passed -- proves the flag actually widens the query rather than the
        chapter being excluded by some OTHER condition (e.g. a missing
        r2_current_path, which would make both assertions pass for the wrong
        reason)."""
        _skip_if_no_real_db()
        rows = _matched_chapters("blacktown", "part-a-car-parking", include_backlog=True)
        assert len(rows) == 1
        assert rows[0][0] == "part-a-car-parking"

    def test_live_chapter_included_by_default(self):
        """ashfield/chapter-d-precinct-guidelines: measured live 2026-09-07,
        real live+actionable regulatory_provisions rows exist -- must be
        graded by default, no flag needed."""
        _skip_if_no_real_db()
        rows = _matched_chapters("ashfield", "chapter-d-precinct-guidelines", include_backlog=False)
        assert len(rows) == 1
        assert rows[0][0] == "chapter-d-precinct-guidelines"

    def test_nonexistent_chapter_never_matches_either_way(self):
        """Guards against a query broad enough to match anything -- a
        council/chapter that exists in neither table must return empty
        whether or not --include-backlog is passed."""
        _skip_if_no_real_db()
        for include_backlog in (False, True):
            rows = _matched_chapters(
                "blacktown", "this-chapter-key-has-never-existed-in-either-table",
                include_backlog=include_backlog,
            )
            assert rows == [], f"include_backlog={include_backlog}"
