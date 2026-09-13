"""The section-loss guard, run against the REAL incident rows in production.

Read-only. On 2026-09-13 marrickville part4-s1-low-density was swapped back to its
better version (backup: data/db_rollback_backups/marrickville_run2_restore_pre_2026-09-13_1002.csv).
The worse version is still in the table, switched off, as ids 122563-122588. So both
sides of the incident exist and can be measured with the guard's own snapshot code:

  live now (the better version)   should read 215 rules
  the retired worse version       should read  26 rules

The guard must refuse a swap from the first to the second, and must NOT refuse the
chapter compared with itself. If the table has moved on since, the test skips and
says why rather than asserting on different rows.

Run:
    PYTEST_REAL_DB=1 pytest -m database tests/test_dcp_supersede_guard_real_db.py -o addopts=
"""
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))

pytestmark = pytest.mark.database

COUNCIL, CHAPTER = "marrickville", "part4-s1-low-density"
RETIRED_IDS = (122563, 122588)


def _conn():
    if os.environ.get("PYTEST_REAL_DB") != "1":
        pytest.skip("Real-DB test. Run with PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_dcp_supersede_guard_real_db.py -o addopts=")
    from dotenv import load_dotenv
    from dq_db import main_checkout  # a worktree has no .env of its own
    load_dotenv(main_checkout() / ".env")
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    if not url:
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")
    import psycopg2
    conn = psycopg2.connect(url, connect_timeout=20)
    conn.set_session(readonly=True, autocommit=True)
    return conn


def test_the_real_incident_is_refused_and_the_chapter_against_itself_is_not():
    import dcp_supersede_guard as g
    from dcp_chapter_measure import leading_code

    conn = _conn()
    try:
        cur = conn.cursor()
        live = g.snapshot(cur, COUNCIL, CHAPTER)
        cur.execute(
            """SELECT section_header FROM regulatory_provisions
               WHERE source_council = %s AND source_chapter_key = %s
                 AND NOT is_current AND id BETWEEN %s AND %s""",
            (COUNCIL, CHAPTER, *RETIRED_IDS))
        retired_headers = [r[0] for r in cur.fetchall()]
    finally:
        conn.close()

    if live.rows != 215 or len(retired_headers) != 26:
        pytest.skip(f"table has moved on: live {live.rows} rows (expected 215), "
                    f"retired {len(retired_headers)} (expected 26)")

    retired = g.Snapshot(
        codes=frozenset(c for c in (leading_code(h) for h in retired_headers) if c),
        rows=len(retired_headers))

    verdict = g.judge(live, retired)
    assert verdict.refused, verdict.describe(COUNCIL, CHAPTER)
    assert verdict.measure == "codes"
    assert not g.judge(live, live).refused
