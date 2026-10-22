"""The alarm's SQL against the REAL production database, on TEMP copies of the migration-116 tables.

Why: tests/test_verifyops_daily_check.py answers each query with canned rows, so a wrong predicate
(e.g. `last.outcome NOT IN` -> `IN`) survived mutation there. This runs the real queries on real
registry rows. The results tables are created as TEMP tables inside one transaction (they shadow
any permanent ones for this session only) and the transaction is rolled back: nothing is written.

Run: PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> pytest -m database tests/test_verifyops_coverage_real_db.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = pytest.mark.database
_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"


def temp_results_tables(cur) -> None:
    """CREATE the migration-116 tables as TEMP tables (their CREATE TABLE / INDEX text, unchanged)."""
    sql = (ROOT / "migrations" / "116_dcp_monitor_results.sql").read_text(encoding="utf-8")
    sql = re.sub(r"--[^\n]*", "", sql)
    for stmt in sql.split(";"):
        s = stmt.strip()
        if s.startswith("CREATE TABLE IF NOT EXISTS"):
            cur.execute(s.replace("CREATE TABLE IF NOT EXISTS", "CREATE TEMP TABLE", 1))
        elif s.startswith("CREATE INDEX IF NOT EXISTS"):
            cur.execute(s)


@pytest.fixture
def conn():
    if not _REAL_DB_REQUESTED or not os.environ.get("DATABASE_URL"):
        pytest.skip("Real-DB test: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database")
    import psycopg2
    c = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=30000")
    cur = c.cursor()
    temp_results_tables(cur)
    cur.close()
    yield c
    c.rollback()
    c.close()


def _a_checkable_chapter(cur) -> tuple[int, str, str]:
    cur.execute("""SELECT id, council, chapter_key FROM dcp_chapter_registry
                   WHERE is_active AND NOT COALESCE(is_inert, FALSE)
                     AND council_url IS NOT NULL AND btrim(council_url) <> ''
                   ORDER BY id LIMIT 1""")
    return cur.fetchone()


def test_the_queries_run_on_the_real_schema(conn):
    import verifyops_coverage as cov
    reds = cov.measure(conn)
    # With empty results tables: no run finished, so the fleet-level key is red, and every
    # checkable chapter is red as not checked in 8 days.
    assert "*|*|no_run_2d" in reds
    cid, council, key = _a_checkable_chapter(conn.cursor())
    assert f"{council}|{key}|not_checked_8d" in reds


def test_a_rate_limited_last_result_is_red_and_a_check_clears_it(conn):
    import verifyops_coverage as cov
    cur = conn.cursor()
    cid, council, key = _a_checkable_chapter(cur)
    cur.execute("INSERT INTO dcp_monitor_runs (mode, finished_at) VALUES ('daily', NOW()) RETURNING id")
    run = cur.fetchone()[0]
    cur.execute("INSERT INTO dcp_monitor_chapter_results (run_id, chapter_id, council, chapter_key, outcome)"
                " VALUES (%s, %s, %s, %s, 'rate_limited')", (run, cid, council, key))
    reds = cov.measure(conn)
    assert f"{council}|{key}|last_run_unchecked" in reds
    assert f"{council}|{key}|not_checked_8d" in reds
    assert "*|*|no_run_2d" not in reds
    cur.execute("INSERT INTO dcp_monitor_chapter_results (run_id, chapter_id, council, chapter_key, outcome)"
                " VALUES (%s, %s, %s, %s, 'unchanged_etag')", (run, cid, council, key))
    reds = cov.measure(conn)
    assert f"{council}|{key}|last_run_unchecked" not in reds
    assert f"{council}|{key}|not_checked_8d" not in reds


def test_a_list_read_ok_clears_list_not_read(conn):
    import verifyops_coverage as cov
    cur = conn.cursor()
    cur.execute("SELECT council FROM dcp_chapter_registry WHERE is_active AND NOT COALESCE(is_inert, FALSE)"
                " AND council_page_url IS NOT NULL ORDER BY council LIMIT 1")
    council = cur.fetchone()[0]
    assert f"{council}|*|list_not_read_2d" in cov.measure(conn)
    cur.execute("INSERT INTO dcp_monitor_runs (mode, finished_at) VALUES ('test', NOW()) RETURNING id")
    run = cur.fetchone()[0]
    cur.execute("INSERT INTO dcp_monitor_council_results (run_id, council, outcome) VALUES (%s, %s, 'blocked')",
                (run, council))
    assert f"{council}|*|list_not_read_2d" in cov.measure(conn)       # blocked is not a read
    cur.execute("INSERT INTO dcp_monitor_council_results (run_id, council, outcome) VALUES (%s, %s, 'ok')",
                (run, council))
    assert f"{council}|*|list_not_read_2d" not in cov.measure(conn)


def test_known_gaps_measured_on_2026_10_22_are_red(conn):
    # inner_west serves 495 rules with no registry row; statewide setbacks have no registry row.
    import verifyops_coverage as cov
    reds = cov.measure(conn)
    assert "inner_west|*|unwatched" in reds
    assert "nsw_statewide|*|unwatched" in reds


def test_a_one_council_run_does_not_count_as_the_fleet_run(conn):
    # Cross-review 2026-10-22: an operator's `--council bayside` run kept no_run_2d green
    # while every other council missed the scheduled run.
    import verifyops_coverage as cov
    cur = conn.cursor()
    cur.execute("INSERT INTO dcp_monitor_runs (mode, finished_at) VALUES ('council:bayside', NOW())")
    assert "*|*|no_run_2d" in cov.measure(conn)
    cur.execute("INSERT INTO dcp_monitor_runs (mode) VALUES ('daily')")          # still running
    assert "*|*|no_run_2d" in cov.measure(conn)
    cur.execute("INSERT INTO dcp_monitor_runs (mode, finished_at) VALUES ('daily', NOW())")
    assert "*|*|no_run_2d" not in cov.measure(conn)


def test_a_chapter_the_last_full_run_skipped_is_red(conn):
    # Cross-review 2026-10-22: yesterday's good result must not cover a chapter today's full run
    # never wrote a row for.
    import verifyops_coverage as cov
    cur = conn.cursor()
    cid, council, key = _a_checkable_chapter(cur)
    cur.execute("INSERT INTO dcp_monitor_runs (mode, finished_at) VALUES ('daily', NOW() - INTERVAL '1 day')"
                " RETURNING id")
    yesterday = cur.fetchone()[0]
    cur.execute("INSERT INTO dcp_monitor_chapter_results (run_id, chapter_id, council, chapter_key, outcome)"
                " VALUES (%s, %s, %s, %s, 'unchanged_etag')", (yesterday, cid, council, key))
    assert f"{council}|{key}|missing_from_last_run" not in cov.measure(conn)
    cur.execute("INSERT INTO dcp_monitor_runs (mode, finished_at) VALUES ('daily', NOW())")
    reds = cov.measure(conn)
    assert f"{council}|{key}|missing_from_last_run" in reds
    assert f"{council}|{key}|not_checked_8d" not in reds          # the old check alone would miss it
    # a later one-council run that DID check it does not stand in for the full run
    cur.execute("INSERT INTO dcp_monitor_runs (mode, finished_at) VALUES ('council:x', NOW()) RETURNING id")
    partial = cur.fetchone()[0]
    cur.execute("INSERT INTO dcp_monitor_chapter_results (run_id, chapter_id, council, chapter_key, outcome)"
                " VALUES (%s, %s, %s, %s, 'unchanged_etag')", (partial, cid, council, key))
    assert f"{council}|{key}|missing_from_last_run" in cov.measure(conn)


def test_no_list_page_query_runs_and_names_councils_only(conn):
    import verifyops_coverage as cov
    for k in cov.measure(conn):
        if k.endswith("|no_list_page"):
            assert k.split("|")[1] == "*"


def test_a_full_run_killed_mid_way_is_red_until_it_is_old_news(conn):
    """Run 1 (2026-10-22 20:23 UTC, daily, sha 732ef41b) was killed when the next image deployed
    at 20:30 and its finished_at stayed NULL. That row shape is the known-wrong case."""
    import verifyops_coverage as cov
    cur = conn.cursor()
    cur.execute("INSERT INTO dcp_monitor_runs (mode, started_at) VALUES ('daily', NOW() - INTERVAL '1 hour')")
    assert "*|*|run_unfinished" not in cov.measure(conn)       # may still be running
    cur.execute("INSERT INTO dcp_monitor_runs (mode, started_at, git_sha) VALUES "
                "('daily', NOW() - INTERVAL '13 hours', '732ef41b20da25fcc7b69023ec0c0b4e8878bf7e')")
    reds = cov.measure(conn)
    assert "*|*|run_unfinished" in reds
    cur.execute("UPDATE dcp_monitor_runs SET finished_at = NOW() WHERE finished_at IS NULL")
    assert "*|*|run_unfinished" not in cov.measure(conn)
    cur.execute("INSERT INTO dcp_monitor_runs (mode, started_at) VALUES ('council:x', NOW() - INTERVAL '9 hours')")
    assert "*|*|run_unfinished" not in cov.measure(conn)       # one-council runs never count


def test_the_latest_full_run_with_no_sha_is_deployed_not_main(conn):
    import verifyops_coverage as cov
    cur = conn.cursor()
    cur.execute("INSERT INTO dcp_monitor_runs (mode, finished_at) VALUES ('force', NOW())")
    assert "*|*|deployed_not_main" in cov.measure(conn)
