"""Migration 111 (council quotes) proven on the REAL production table. Every test rolls back.

What a mocked connection cannot show: that the triggers really fire and the shape constraint
really refuses. Opt-in like tests/test_drawdown_verify_real_db.py:
    PYTEST_REAL_DB=1 pytest -m database tests/test_council_quote_real_db.py -o addopts=
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
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database tests/test_council_quote_real_db.py")
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
