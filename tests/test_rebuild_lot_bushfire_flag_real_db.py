"""Real-database checks. Opt in: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -o addopts= -m database. Read-only. (conftest_mocks stubs psycopg2 otherwise.)"""
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


def _conn():
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("real database test: run with PYTEST_REAL_DB=1 DATABASE_URL=... pytest -o addopts= -m database")
    import psycopg2

    c = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    c.set_session(readonly=True, autocommit=True)
    c.cursor().execute("SET statement_timeout = '60000'")
    return c


@pytest.mark.database
def test_the_real_lot_comparison_runs_and_agrees_with_the_stored_flag_after_the_rebuild():
    import rebuild_lot_bushfire_flag as rf

    c = _conn()
    cur = c.cursor()
    cur.execute("SELECT lotidstring FROM lot_search_index WHERE lotidstring > %s ORDER BY lotidstring LIMIT 300", ("3//DP",))
    ids = [r[0] for r in cur.fetchall()]
    if len(ids) < 100:
        pytest.skip("too few lots to compare; not a pass")
    cur.execute(rf._SQL_COMPARE, (ids,))
    rows = cur.fetchall()
    assert len(rows) == len(ids) and all(isinstance(new, bool) for _, _, new in rows)
    assert rf.changed_lots(rows) == []          # after the 2026-11-19 rebuild no lot in this sample differs from the layer
