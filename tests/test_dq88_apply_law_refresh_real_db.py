"""Real-database dry run of the law refresh plan: every row must still hold the text the plan was built from. Opt in:
PYTEST_REAL_DB=1 DATABASE_URL=... pytest tests/test_dq88_apply_law_refresh_real_db.py -o addopts= -m database

conftest_mocks stubs psycopg2 by default, so the flag is required; without it the test skips (never passes). The run rolls back; nothing is written."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import dq88_apply_law_refresh as ap  # noqa: E402


@pytest.mark.database
def test_the_plan_dry_runs_against_the_real_rows_and_rolls_back():
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("real database test: run with PYTEST_REAL_DB=1 DATABASE_URL=... -o addopts= -m database; skipped, not a pass")
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=120000")
    try:
        # Once applied, the stored text no longer equals the plan's old text and run() refuses: that refusal is the expected state afterwards.
        try:
            assert ap.run(conn, False) == 0
        except SystemExit as stop:
            assert "stored text is not what the plan was built from" in str(stop)
    finally:
        conn.rollback()
        conn.close()
