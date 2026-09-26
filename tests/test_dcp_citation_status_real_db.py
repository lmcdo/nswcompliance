"""Against the real database: every served DCP rule carries a known citation verdict.

Opt-in (PYTEST_REAL_DB=1 DATABASE_URL=...), because conftest_mocks stubs psycopg2.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

pytestmark = [pytest.mark.database, pytest.mark.skipif(
    os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"),
    reason="real-DB test: set PYTEST_REAL_DB=1 and DATABASE_URL")]


def test_every_served_rule_has_a_known_citation_verdict():
    import psycopg2
    import dcp_citation_status as S
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        cur.execute("SELECT citation_status, count(*) FROM regulatory_provisions WHERE is_current "
                    "AND v2_is_actionable AND source_council IS NOT NULL GROUP BY 1")
        got = dict(cur.fetchall())
    finally:
        conn.close()
    assert None not in got, f"{got.get(None)} served rules were never checked"
    assert set(got) <= set(S.STATUSES), f"unknown verdicts {set(got) - set(S.STATUSES)}"
