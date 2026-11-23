"""Real-database check of the dependents sweep (read only). Opt in:
PYTEST_REAL_DB=1 DATABASE_URL=... pytest tests/test_check_provision_dependents_real_db.py -o addopts= -m database

conftest_mocks stubs psycopg2 by default, so the flag is required; without it the test skips (never passes). Nothing is written."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import check_provision_dependents as c  # noqa: E402


@pytest.mark.database
def test_the_real_sweep_finds_the_known_tables_checks_every_column_and_reports_dead_pointers_by_council():
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("real database test: run with PYTEST_REAL_DB=1 DATABASE_URL=... -o addopts= -m database; skipped, not a pass")
    import psycopg2

    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c default_transaction_read_only=on -c statement_timeout=60000")
    try:
        everywhere = c.sweep(conn, None)
        one = c.sweep(conn, "waverley")
    finally:
        conn.close()
    tables = {r["table"] for r in everywhere}
    assert {"project_brief_rows", "dcp_setback_controls", "da_responses"} <= tables
    assert not [r for r in everywhere if r.get("error")], "a column could not be checked"
    by_one = {(r["table"], r["column"]): r["dead"] for r in one}
    by_all = {(r["table"], r["column"]): r["dead"] for r in everywhere}
    assert all(by_one[k] <= by_all[k] for k in by_one)          # one council never has more dead pointers than all councils
