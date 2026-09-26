"""Against the real database: setback controls carry a known clause verdict (migration 077).

Opt-in (PYTEST_REAL_DB=1 DATABASE_URL=...), because conftest_mocks stubs psycopg2.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

pytestmark = [pytest.mark.database, pytest.mark.skipif(
    os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"),
    reason="real-DB test: set PYTEST_REAL_DB=1 and DATABASE_URL")]


def _conn():
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    conn.set_session(readonly=True, autocommit=True)
    conn.cursor().execute("SET statement_timeout = '30000'")
    return conn


@pytest.mark.database
def test_every_served_setback_control_has_a_known_verdict():
    import dcp_setback_citation_status as S
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT citation_status, count(*) FROM dcp_setback_controls WHERE is_current "
                    "AND (needs_review IS NULL OR needs_review = FALSE) GROUP BY 1")
        got = dict(cur.fetchall())
    finally:
        conn.close()
    assert None not in got, f"{got.get(None)} served setback controls were never checked"
    assert set(got) <= set(S.STATUSES), f"unknown verdicts {set(got) - set(S.STATUSES)}"
