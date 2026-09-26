"""Against the real database: the page repair reads every served rule, and every one is checked.

Opt-in (PYTEST_REAL_DB=1 DATABASE_URL=...), because conftest_mocks stubs psycopg2.
The second test fails until migration 079 and `dcp_page_repair.py --apply` have run (DQ-113).
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


def _conn():
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    conn.cursor().execute("SET statement_timeout = '30000'")
    return conn


@pytest.mark.database
def test_the_repair_reads_every_served_rule_with_the_pdf_it_links_to():
    import dcp_page_repair as R
    conn = _conn()
    try:
        rows = R.fetch(conn, None)
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM regulatory_provisions WHERE is_current AND v2_is_actionable "
                    "AND source_council IS NOT NULL")
        served = cur.fetchone()[0]
    finally:
        conn.close()
    assert len(rows) == served, f"the repair reads {len(rows)} of {served} served council rules"
    assert all(r["r2_current_path"] for r in rows), "a served rule has no chapter PDF to check against"


@pytest.mark.database
def test_every_served_rule_page_was_checked_against_its_current_pdf():
    import dcp_page_repair as R
    conn = _conn()
    try:
        assert R.has_079(conn), "migration 079 not applied"
        assert R.check(conn) == 0, "served rules whose page link was never checked (DQ-113)"
    finally:
        conn.close()
