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
    import json
    import psycopg2
    plan = json.load(open(ap.PLAN, encoding="utf-8"))
    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=120000")
    try:
        cur = conn.cursor()
        state = {}
        for p in plan:
            cur.execute("SELECT provision_text, is_current FROM regulatory_provisions WHERE id = %s", (p["id"],))
            row = cur.fetchone()
            assert row is not None, f"row {p['id']} is missing"
            if row[1] and row[0] == p["old_text"]:
                state[p["id"]] = "before"
            elif p["action"] == "REPLACE" and row[1] and row[0] == p["new_text"]:
                state[p["id"]] = "after"
            elif p["action"] == "RETIRE" and not row[1]:
                state[p["id"]] = "after"
            else:
                state[p["id"]] = "other"
        assert "other" not in state.values(), f"rows that are neither before nor after the plan: {[i for i, v in state.items() if v == 'other']}"
        assert len(set(state.values())) == 1, "the plan is half applied"
        if set(state.values()) == {"before"}:
            assert ap.run(conn, False) == 0          # whole plan dry-runs cleanly; rolled back
    finally:
        conn.rollback()
        conn.close()
