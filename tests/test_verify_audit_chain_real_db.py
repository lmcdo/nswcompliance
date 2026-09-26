"""Against the real database: the report audit trail's hash chain is intact and every row is
chained (migration 078). Opt-in (PYTEST_REAL_DB=1 DATABASE_URL=...)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

pytestmark = [pytest.mark.database, pytest.mark.skipif(
    os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"),
    reason="real-DB test: set PYTEST_REAL_DB=1 and DATABASE_URL")]


@pytest.mark.database
def test_the_audit_chain_verifies():
    import psycopg2
    import verify_audit_chain as V
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    conn.set_session(readonly=True, autocommit=True)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        cur.execute(V.CHECK_SQL)
        bad = cur.fetchall()
    finally:
        conn.close()
    assert not bad, f"{len(bad)} audit rows fail the chain: {bad[:5]}"
