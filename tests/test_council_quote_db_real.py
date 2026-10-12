"""Migration 111 (council quotes) proven on the REAL production table. Every test rolls back.

What a mocked connection cannot show: that the triggers really fire and the shape constraint
really refuses. Opt-in like tests/test_drawdown_verify_real_db.py:
    PYTEST_REAL_DB=1 pytest -m database tests/test_council_quote_db_real.py -o addopts=
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database


@pytest.fixture
def cur():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database tests/test_council_quote_db_real.py")
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL available.")
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    c = conn.cursor()
    c.execute("SET statement_timeout = 30000")
    try:
        yield c
    finally:
        conn.rollback()          # nothing these tests do is ever kept
        conn.close()


def _quoted_row(cur) -> tuple[int, str, str]:
    cur.execute("""SELECT id, source_council, source_chapter_key FROM regulatory_provisions
                    WHERE is_current AND quote_status = 'exact' ORDER BY id LIMIT 1""")
    row = cur.fetchone()
    assert row, "no stored exact quote: council_quote.py --apply has not run against this database"
    return row


def _status(cur, rid: int):
    cur.execute("SELECT quote_status, council_quote FROM regulatory_provisions WHERE id = %s", (rid,))
    return cur.fetchone()


def test_editing_a_rules_text_clears_its_quote(cur):
    rid, _c, _k = _quoted_row(cur)
    cur.execute("UPDATE regulatory_provisions SET provision_text = provision_text || ' ' WHERE id = %s", (rid,))
    assert _status(cur, rid) == (None, None)


def test_the_copiers_own_write_is_kept(cur):
    rid, _c, _k = _quoted_row(cur)
    cur.execute("""UPDATE regulatory_provisions SET quote_status = 'unconfirmed', council_quote = NULL,
                   quote_page = NULL, quote_source_path = NULL, quote_reason = 'test',
                   quote_checked_at = now() + interval '1 second' WHERE id = %s""", (rid,))
    assert _status(cur, rid) == ("unconfirmed", None)


def test_exact_without_a_quote_is_refused(cur):
    import psycopg2
    rid, _c, _k = _quoted_row(cur)
    with pytest.raises(psycopg2.errors.CheckViolation):
        cur.execute("UPDATE regulatory_provisions SET council_quote = NULL WHERE id = %s", (rid,))


def test_a_new_chapter_pdf_voids_its_quotes(cur):
    rid, council, key = _quoted_row(cur)
    cur.execute("""UPDATE dcp_chapter_registry SET r2_current_path = r2_current_path || '.test'
                    WHERE council = %s AND chapter_key = %s AND is_active""", (council, key))
    assert cur.rowcount == 1
    assert _status(cur, rid) == (None, None)
    cur.execute("""SELECT count(*) FROM regulatory_provisions
                    WHERE source_council = %s AND source_chapter_key = %s AND is_current
                      AND quote_status IS NOT NULL""", (council, key))
    assert cur.fetchone()[0] == 0


def test_a_text_edit_clears_the_quote_even_when_it_also_stamps_the_check_time(cur):
    # migration 112: no update that changes the text can be the copier's own
    rid, _c, _k = _quoted_row(cur)
    cur.execute("""UPDATE regulatory_provisions SET provision_text = provision_text || ' ',
                   quote_checked_at = now() + interval '1 second' WHERE id = %s""", (rid,))
    assert _status(cur, rid) == (None, None)


def test_a_new_chapter_pdf_voids_quotes_on_rows_not_current_too(cur):
    # migration 112: a non-current row must not carry an old PDF's quote back when made current
    rid, council, key = _quoted_row(cur)
    cur.execute("UPDATE regulatory_provisions SET is_current = false WHERE id = %s", (rid,))
    cur.execute("""UPDATE dcp_chapter_registry SET r2_current_path = r2_current_path || '.test'
                    WHERE council = %s AND chapter_key = %s AND is_active""", (council, key))
    assert _status(cur, rid) == (None, None)


def test_the_real_writer_stores_nothing_for_text_it_did_not_judge(cur):
    # council_quote_db.write against the real table: a stale text fingerprint matches no row,
    # so nothing is written and the stored verdict is untouched.
    import council_quote_db as store
    rid, _c, _k = _quoted_row(cur)
    cur.execute("""SELECT reg.r2_current_path, rp.quote_status, rp.quote_checked_at
                     FROM regulatory_provisions rp JOIN dcp_chapter_registry reg
                       ON reg.council = rp.source_council AND reg.chapter_key = rp.source_chapter_key
                      AND reg.is_active WHERE rp.id = %s""", (rid,))
    path, status, checked = cur.fetchone()
    n = store.write([{"id": rid, "text_md5": "0" * 32, "status": "unconfirmed", "reason": "test",
                      "source_path": path}])
    assert n == 0
    cur.connection.rollback()
    cur.execute("SET statement_timeout = 30000")
    cur.execute("SELECT quote_status, quote_checked_at FROM regulatory_provisions WHERE id = %s", (rid,))
    assert cur.fetchone() == (status, checked)
