"""The tracing repair, against the REAL database it writes to.

The repair is one-shot and already applied, so these tests are not a rehearsal — they pin
the state it left behind and the guards that decided it, which is what a later change would
break silently. A mock cannot do that: the whole question is what is in the table.

Opt-in the way this repo does it (tests/test_drawdown_verify_real_db.py,
tests/test_lga_coverage.py): PYTEST_REAL_DB=1 plus @pytest.mark.database, deselected by
default per pytest.ini. Read-only — every test rolls back.

    PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database \
        tests/test_repair_plan_in_force_tracing_real_db.py -v
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database "
                    "tests/test_repair_plan_in_force_tracing_real_db.py")
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


def _conn():
    import repair_plan_in_force_tracing as r

    return r, r.psycopg2.connect(r._dsn(), connect_timeout=20)


class TestWhatTheRepairLeftBehind:
    def test_cumberland_serves_one_plan_name(self):
        """The defect: one plan registered under two spellings, read as two plans."""
        _skip_if_no_real_db()
        r, conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT DISTINCT dcp_name FROM dcp_chapter_registry "
                            "WHERE council = 'cumberland' AND is_active")
                names = sorted(n for (n,) in cur.fetchall())
        finally:
            conn.close()
        assert names == [r.CUMBERLAND_RIGHT], names

    def test_the_lep_controls_are_filed_as_a_state_instrument(self):
        """Six rows moved to _external_lep, where DQ-88 tracks their currency instead of a
        DCP confirmation. Not filtered by is_current on purpose: a superseded row left under
        the old key would still trace the council to two plans."""
        _skip_if_no_real_db()
        r, conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT id FROM dcp_setback_controls "
                            "WHERE source_chapter_key = %s ORDER BY id",
                            (r.SUTHERLAND_WRONG_KEY,))
                left = [i for (i,) in cur.fetchall()]
        finally:
            conn.close()
        assert left == sorted(r.HELD_BACK), left

    def test_the_held_back_row_is_still_held_back_and_still_wrong(self):
        """id=606 stores 5.5m where Sutherland Shire LEP 2015 page 109 says 7.5m. If this
        ever passes silently it means someone re-keyed it without reading the instrument."""
        _skip_if_no_real_db()
        r, conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT source_chapter_key, value_min FROM dcp_setback_controls "
                            "WHERE id = 606")
                row = cur.fetchone()
        finally:
            conn.close()
        assert row is not None
        key, value = row
        assert key == r.SUTHERLAND_WRONG_KEY
        assert float(value) == 5.5
        assert float(value) != 7.5, "if this row is corrected, drop it from HELD_BACK"


class TestTheRepairIsSafeToRunAgain:
    def test_a_dry_run_writes_nothing_and_reports_nothing_to_do(self):
        _skip_if_no_real_db()
        r, conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = '30s'")
                assert r.repair_cumberland(cur, apply=False) == 0
                assert r.repair_sutherland(cur, apply=False) == 0
            conn.rollback()
        finally:
            conn.close()

    def test_applying_twice_changes_nothing(self):
        """Idempotence proven by running the real write path and rolling it back, rather
        than by reading the code and believing it."""
        _skip_if_no_real_db()
        r, conn = _conn()
        try:
            with conn.cursor() as cur:
                cur.execute("SET statement_timeout = '30s'")
                assert r.repair_cumberland(cur, apply=True) == 0
                assert r.repair_sutherland(cur, apply=True) == 0
            conn.rollback()
        finally:
            conn.close()
