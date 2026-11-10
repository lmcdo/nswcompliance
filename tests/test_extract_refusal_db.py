"""Migration 122 + the refusal counter and hold, on a throwaway Postgres (CI isolated-DB job)."""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
URL = os.environ.get("RULE_GUARD_TEST_DATABASE_URL")
pytestmark = [pytest.mark.database, pytest.mark.skipif(
    not URL, reason="needs RULE_GUARD_TEST_DATABASE_URL: a throwaway Postgres (CI isolated-DB job)")]


@pytest.fixture()
def cur():
    import psycopg2
    conn = psycopg2.connect(URL)
    conn.autocommit = True
    c = conn.cursor()
    c.execute("DROP TABLE IF EXISTS dcp_chapter_registry, dcp_review_queue CASCADE")
    c.execute("CREATE TABLE dcp_chapter_registry (id serial PRIMARY KEY, council text, chapter_key text, "
              "chapter_label text, r2_current_path text DEFAULT 'p', r2_version_label text, dcp_name text, "
              "content_hash text, council_url text, sort_order int DEFAULT 0, "
              "is_active boolean DEFAULT true, needs_extraction boolean DEFAULT true)")
    c.execute("CREATE TABLE dcp_review_queue (council text, chapter_key text, status text, source_content_hash text)")
    c.execute((ROOT / "migrations" / "122_chapter_extract_refusals.sql").read_text(encoding="utf-8"))
    # The selection reads the effective hash COALESCE(staged_content_hash, content_hash) (migration 125).
    # Its own BEGIN/COMMIT lines are dropped so the fixture's transaction still rolls everything back.
    m125 = (ROOT / "migrations" / "125_dcp_chapter_staged_file.sql").read_text(encoding="utf-8")
    c.execute("\n".join(l for l in m125.splitlines() if l.strip() not in ("BEGIN;", "COMMIT;")))
    c.execute("INSERT INTO dcp_chapter_registry (council, chapter_key, content_hash) VALUES "
              "('cb', 'ch7-6', 'h1'), ('su', 'ch2', 'h9'), ('nn', 'nohash', NULL)")
    yield c
    conn.close()


def _selected(cur):
    import dcp_extract_changed as dx
    q, p = dx._pending_chapters_sql(None, all_chapters=False)
    cur.execute(q, p)
    return sorted(r[2] for r in cur.fetchall())


def _refuse(cur, key):
    import dcp_extract_changed as dx
    cur.execute("SELECT id FROM dcp_chapter_registry WHERE chapter_key = %s", (key,))
    cur.execute(dx._record_refusal_sql(), ("PageLoss: pages 64, 139", cur.fetchone()[0]))


def test_held_after_two_refusals_of_the_same_pdf_and_only_that_chapter(cur):
    _refuse(cur, "ch7-6")
    assert "ch7-6" in _selected(cur)                 # one refusal: still read
    _refuse(cur, "ch7-6")
    assert _selected(cur) == ["ch2", "nohash"]       # two: held; the others still read


def test_a_new_pdf_restarts_the_count_and_is_read(cur):
    _refuse(cur, "ch7-6"); _refuse(cur, "ch7-6")
    cur.execute("UPDATE dcp_chapter_registry SET content_hash = 'h2' WHERE chapter_key = 'ch7-6'")
    assert "ch7-6" in _selected(cur)                 # new edition: read again
    _refuse(cur, "ch7-6")
    cur.execute("SELECT extract_refusals FROM dcp_chapter_registry WHERE chapter_key = 'ch7-6'")
    assert cur.fetchone()[0] == 1                    # counting starts again on the new file


def test_a_chapter_with_no_hash_is_never_held(cur):
    _refuse(cur, "nohash"); _refuse(cur, "nohash"); _refuse(cur, "nohash")
    assert "nohash" in _selected(cur)


def test_a_hold_ends_after_seven_days(cur):
    _refuse(cur, "ch7-6"); _refuse(cur, "ch7-6")
    assert "ch7-6" not in _selected(cur)
    cur.execute("UPDATE dcp_chapter_registry SET extract_refused_at = now() - interval '8 days' "
                "WHERE chapter_key = 'ch7-6'")
    assert "ch7-6" in _selected(cur)                 # tried once more after the hold


def test_a_null_refusal_time_reads_as_not_held(cur):
    """Sol review: NULL anywhere must not drop the chapter from both lists."""
    _refuse(cur, "ch7-6"); _refuse(cur, "ch7-6")
    cur.execute("UPDATE dcp_chapter_registry SET extract_refused_at = NULL WHERE chapter_key = 'ch7-6'")
    assert "ch7-6" in _selected(cur)
