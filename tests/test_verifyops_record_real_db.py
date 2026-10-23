"""Recorder against the REAL database driver, on TEMP copies of the migration-116 tables.

Proves the INSERT column lists, the jsonb casts and the CHECK constraints agree with the migration
(the unit tests only see a fake cursor). Everything is TEMP inside one transaction and rolled back.

Run: PYTEST_REAL_DB=1 DATABASE_URL=<pooler url> pytest -m database tests/test_verifyops_record_real_db.py
"""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "tests"))

pytestmark = pytest.mark.database
_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"


class NoCommit:
    """The Recorder commits after each write; here a commit must not end the transaction that
    holds the TEMP tables, so commit is a no-op and the fixture rolls everything back."""

    def __init__(self, c):
        self.c = c

    def cursor(self):
        return self.c.cursor()

    def commit(self):
        pass

    def rollback(self):
        self.c.rollback()


@pytest.fixture
def conn():
    if not _REAL_DB_REQUESTED or not os.environ.get("DATABASE_URL"):
        pytest.skip("Real-DB test: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database")
    import psycopg2
    from test_verifyops_coverage_real_db import temp_results_tables
    c = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=30000")
    cur = c.cursor()
    temp_results_tables(cur)
    cur.close()
    yield NoCommit(c)
    c.rollback()
    c.close()


def test_a_run_round_trips(conn):
    from verifyops_record import Recorder
    rec = Recorder(conn, dry_run=False, mode="test")
    rec.start()
    assert rec.run_id is not None and rec.first_run_at is None
    rec.chapter(1, "bayside", "k", "rate_limited", detail="HEAD 429 twice")
    rec.council_list("bayside", "https://x", "ok", [{"href": "h", "norm": "h", "base": "h", "text": "t",
                                                      "chapter_key": None}], "fp", ["a line"], "d")
    rec.finish({"checked": 0})
    cur = conn.cursor()
    cur.execute("SELECT outcome, detail FROM dcp_monitor_chapter_results WHERE run_id = %s", (rec.run_id,))
    assert cur.fetchall() == [("rate_limited", "HEAD 429 twice")]
    cur.execute("SELECT finished_at IS NOT NULL, summary->>'checked' FROM dcp_monitor_runs WHERE id = %s",
                (rec.run_id,))
    assert cur.fetchone() == (True, "0")
    assert rec.previous_list("bayside")[0]["norm"] == "h"
    assert rec.previous_list("nowhere") is None


def test_a_blocked_day_never_becomes_the_list_to_compare_with(conn):
    # If it did, the blocked day's empty list would make every link "new" the next day.
    from verifyops_record import Recorder
    rec = Recorder(conn, dry_run=False, mode="test")
    rec.start()
    good = [{"href": "h", "norm": "h", "base": "h", "text": "t", "chapter_key": None}]
    rec.council_list("bayside", "https://x", "ok", good, "fp")
    rec.flush()
    rec.council_list("bayside", "https://x", "blocked", detail="403")
    rec.flush()
    assert rec.previous_list("bayside") == good


def test_the_check_constraint_refuses_an_unknown_outcome(conn):
    import psycopg2
    cur = conn.cursor()
    cur.execute("INSERT INTO dcp_monitor_runs (mode) VALUES ('test') RETURNING id")
    run = cur.fetchone()[0]
    cur.execute("SAVEPOINT s")
    with pytest.raises(psycopg2.errors.CheckViolation):
        cur.execute("INSERT INTO dcp_monitor_chapter_results (run_id, chapter_id, council, chapter_key, outcome)"
                    " VALUES (%s, 1, 'x', 'k', 'skipped')", (run,))
    cur.execute("ROLLBACK TO SAVEPOINT s")


def test_a_list_check_saves_then_diffs_the_real_bayside_list(conn):
    import json
    from verifyops_record import Recorder
    fx = json.loads((ROOT / "tests/fixtures/verifyops/bayside_list_2026-10-22.json").read_text(encoding="utf-8"))
    now = datetime(2026, 10, 22, tzinfo=timezone.utc)
    sent: list[str] = []
    rec = Recorder(conn, dry_run=False, mode="test")
    rec.start()
    first = rec.council_list_checked("bayside", fx["hub_url"], fx["discovered"], fx["held"],
                                     probe=lambda u: None, send=sent.append, now=now,
                                     plans=["Bayside DCP 2022"])
    rec.flush()
    assert first == []                                  # first scan: saved, no alerts
    second = rec.council_list_checked("bayside", fx["hub_url"], fx["discovered"], fx["held"],
                                      probe=lambda u: None, send=sent.append, now=now,
                                      plans=["Bayside DCP 2022"])
    assert second == [] and sent == []                  # same real list: nothing new


def test_the_last_good_list_is_found_for_a_cosmetically_different_address(conn):
    # Sol HIGH: www., a trailing slash or case must not start a fresh first scan.
    from verifyops_record import Recorder
    rec = Recorder(conn, dry_run=False, mode="test")
    rec.start()
    good = [{"href": "h", "norm": "h", "base": "h", "text": "t", "chapter_key": None}]
    rec.council_list("bayside", "https://www.bayside.nsw.gov.au/DCP", "ok", good, "fp")
    rec.council_list("bayside", "https://www.bayside.nsw.gov.au/notices", "ok", [], "fp2")
    rec.flush()
    assert rec.previous_list("bayside", "https://bayside.nsw.gov.au/dcp/") == good
    assert rec.previous_list("bayside", "https://www.bayside.nsw.gov.au/other") is None
    assert rec.previous_list("bayside") == []          # any page: the newest
