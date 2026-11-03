"""Migration 121 against a real, throwaway Postgres (CI job `rule-write-guard`, never production).

Each test is a case the guard exists for: the 2026-11-02 scratchpad write, a script stamping
'verbatim' on its own row, a tagged pipeline write, and a change to an unprotected column.
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

URL = os.environ.get("RULE_GUARD_TEST_DATABASE_URL")
pytestmark = pytest.mark.skipif(
    not URL, reason="needs RULE_GUARD_TEST_DATABASE_URL: a throwaway Postgres (CI job rule-write-guard)")

# Only the columns the trigger and these tests read; the real tables are wider.
STUBS = """
DROP TABLE IF EXISTS dcp_setback_controls, regulatory_provisions, dcp_chapter_registry,
                     rule_write_log, rule_write_guard CASCADE;
CREATE TABLE dcp_setback_controls (id serial PRIMARY KEY, lga text, source_text text,
    value_min numeric, value_max numeric, unit text, pdf_page int, section_ref text,
    source_chapter_key text, quote_status text, needs_review boolean, review_reason text,
    is_current boolean DEFAULT true, plain_summary text);
CREATE TABLE regulatory_provisions (id serial PRIMARY KEY, provision_text text, council_quote text,
    quote_status text, quote_page int, pdf_page int, source_council text, source_chapter_key text,
    is_current boolean DEFAULT true, v2_is_actionable boolean, v2_topic text);
CREATE TABLE dcp_chapter_registry (id serial PRIMARY KEY, council text, chapter_key text,
    r2_current_path text, content_hash text, page_start int, page_end int,
    needs_extraction boolean, is_active boolean DEFAULT true, council_url text, notes text);
"""


@pytest.fixture()
def db():
    import psycopg2
    conn = psycopg2.connect(URL)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(STUBS)
    cur.execute((ROOT / "migrations" / "121_rule_write_guard.sql").read_text(encoding="utf-8"))
    cur.execute("INSERT INTO dcp_setback_controls (lga, source_text, quote_status, needs_review) "
                "VALUES ('fairfield', 'old words', 'not_found', true)")
    cur.execute("DELETE FROM rule_write_log")      # the seed insert is not under test
    yield conn, cur
    conn.close()


def _mode(cur, mode):
    cur.execute("UPDATE rule_write_guard SET mode = %s", (mode,))


def _log(cur):
    cur.execute("SELECT table_name, columns, run_id FROM rule_write_log ORDER BY id")
    return cur.fetchall()


def test_record_mode_lets_an_untagged_write_through_and_logs_it_as_no_run(db):
    _, cur = db
    cur.execute("UPDATE dcp_setback_controls SET source_text = 'script words' WHERE id = 1")
    [(table, cols, run)] = _log(cur)
    assert table == "dcp_setback_controls" and "source_text" in cols and run is None


def test_enforce_refuses_the_scratchpad_write(db):
    """The 2026-11-02 batches: UPDATE source_text straight from a scratchpad script."""
    import psycopg2
    _, cur = db
    _mode(cur, "enforce")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege, match="no pipeline run"):
        cur.execute("UPDATE dcp_setback_controls SET source_text = 'script words' WHERE id = 1")
    cur.execute("SELECT source_text FROM dcp_setback_controls WHERE id = 1")
    assert cur.fetchone()[0] == "old words"
    assert _log(cur) == []


def test_enforce_refuses_a_script_stamping_verbatim_and_releasing(db):
    """Migration 120 trusts the stamp; this is the hole 121 closes."""
    import psycopg2
    _, cur = db
    _mode(cur, "enforce")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("UPDATE dcp_setback_controls SET quote_status = 'verbatim', needs_review = false "
                    "WHERE id = 1")


def test_a_tagged_pipeline_write_passes_and_names_its_run(db, monkeypatch):
    import pipeline_run
    monkeypatch.delenv(pipeline_run.ENV, raising=False)
    conn, cur = db
    _mode(cur, "enforce")
    rid = pipeline_run.tag(conn, "dcp_extract_changed")
    cur.execute("UPDATE dcp_setback_controls SET source_text = 'extractor words' WHERE id = 1")
    [(_, cols, run)] = _log(cur)
    assert run == rid and rid.startswith("dcp_extract_changed@") and cols == ["source_text"]


def test_an_unprotected_column_is_neither_refused_nor_logged(db):
    _, cur = db
    _mode(cur, "enforce")
    cur.execute("UPDATE dcp_setback_controls SET plain_summary = 'x' WHERE id = 1")
    assert _log(cur) == []


def test_insert_and_registry_page_range_are_guarded_too(db):
    import psycopg2
    _, cur = db
    _mode(cur, "enforce")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("INSERT INTO regulatory_provisions (provision_text) VALUES ('typed rule')")
    _mode(cur, "record")
    cur.execute("INSERT INTO dcp_chapter_registry (council, chapter_key) VALUES ('fairfield', '5a')")
    _mode(cur, "enforce")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("UPDATE dcp_chapter_registry SET page_start = 146, page_end = 172 WHERE chapter_key = '5a'")


def test_an_empty_tag_counts_as_no_run(db):
    import psycopg2
    _, cur = db
    _mode(cur, "enforce")
    cur.execute("SELECT set_config('app.pipeline_run', '', false)")
    with pytest.raises(psycopg2.errors.InsufficientPrivilege):
        cur.execute("UPDATE dcp_setback_controls SET source_text = 'x' WHERE id = 1")


def test_the_migration_ships_in_record_mode(db):
    _, cur = db
    cur.execute("SELECT mode FROM rule_write_guard")
    assert cur.fetchone()[0] == "record"
