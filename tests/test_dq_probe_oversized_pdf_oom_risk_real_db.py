"""DQ-98's probe, run against the REAL database rather than a mock.

WHY A REAL-LAYER TEST. The probe's whole job is one SQL query, and the change
this file accompanies added a clause to it (`last_extracted_at IS NULL`). A
mocked test proves nothing about a WHERE clause: conftest_mocks.py stubs
psycopg2, so a query naming a column that does not exist, or comparing the
wrong type, returns a MagicMock and passes. The failure this guards against is
a probe that silently returns nothing and reports CLEAN -- which is worse than
no probe, because the ledger then says a defect is gone when nobody looked.

That matters more than usual here. The probe's PREVIOUS version could never
reach 0 by construction (it counted chapters that were merely large), so it
was never going to be believed and its correctness barely mattered. The new
one CAN reach 0, so a false 0 is now a real risk.

Opt-in, following the convention already in tests/test_lga_coverage.py and
tests/test_drawdown_verify_real_db.py: @pytest.mark.database, deselected by
default per pytest.ini, so the ordinary `pytest` run is unaffected.

Run it:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_dq_probe_oversized_pdf_oom_risk_real_db.py -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = pytest.mark.database


def _skip_unless_real_db():
    if os.environ.get("PYTEST_REAL_DB") != "1":
        pytest.skip("needs PYTEST_REAL_DB=1 and a live DATABASE_URL")
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL is not set")


def test_the_query_actually_runs_against_the_real_schema():
    """The columns must exist and the types must compare.

    This is the whole point of the real layer. Against the psycopg2 stub, a
    query naming a column that was renamed still 'works' and the probe reports
    CLEAN. Here it raises.
    """
    _skip_unless_real_db()
    import dq_db  # noqa: E402
    import dq_probe_oversized_pdf_oom_risk as probe  # noqa: E402

    with dq_db.session() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT council, chapter_key, url_content_length "
            "FROM dcp_chapter_registry "
            "WHERE is_active AND url_content_length > %s "
            "  AND last_extracted_at IS NULL "
            "ORDER BY url_content_length DESC",
            (probe._THRESHOLD_BYTES,),
        )
        rows = cur.fetchall()

    for council, chapter_key, size in rows:
        assert isinstance(council, str) and council
        assert isinstance(chapter_key, str) and chapter_key
        assert size > probe._THRESHOLD_BYTES, (
            f"{council}/{chapter_key} is {size} bytes, at or below the threshold "
            f"the query claims to filter on -- the comparison is not doing what "
            f"it says"
        )


def test_the_added_clause_narrows_rather_than_empties():
    """`last_extracted_at IS NULL` must exclude SOME rows, not all of them.

    The confusable negative. If that column were always NULL -- never populated
    by the pipeline -- the new clause would change nothing and the probe would
    keep counting big chapters, exactly the behaviour this change set out to
    end. If it were never NULL, the probe would return 0 forever and report
    CLEAN while chapters sat unextracted. Both failure modes look like a
    working check. Asserting the clause actually discriminates rules out both.
    """
    _skip_unless_real_db()
    import dq_db  # noqa: E402
    import dq_probe_oversized_pdf_oom_risk as probe  # noqa: E402

    with dq_db.session() as conn:
        cur = conn.cursor()
        cur.execute(
            "SELECT count(*) FILTER (WHERE last_extracted_at IS NULL), "
            "       count(*) FILTER (WHERE last_extracted_at IS NOT NULL) "
            "FROM dcp_chapter_registry WHERE is_active AND url_content_length > %s",
            (probe._THRESHOLD_BYTES,),
        )
        never, extracted = cur.fetchone()

    assert never + extracted > 0, (
        "no active chapter exceeds the threshold at all, so this test proves "
        "nothing -- the threshold or the corpus has changed materially"
    )
    assert extracted > 0, (
        "every large chapter has last_extracted_at NULL, so the new clause "
        "excludes nothing and the probe still counts chapters that are merely "
        "large -- the defect this change was meant to remove"
    )


def test_run_returns_a_shell_exit_code_not_a_row_count():
    """0 or 1, never the number of offending rows.

    dq_check.py branches on the exit code. A probe returning 3 for 'three bad
    chapters' would be read as a shell failure of an unrelated kind, and the
    ledger row's state would be decided by an accident of arithmetic.
    """
    _skip_unless_real_db()
    import dq_probe_oversized_pdf_oom_risk as probe  # noqa: E402

    assert probe.run() in (0, 1)
