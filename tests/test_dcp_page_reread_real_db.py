"""dcp_page_reread against the real database: every chapter it could touch has
what the publish step needs. Opt-in:
    PYTEST_REAL_DB=1 pytest -m database tests/test_dcp_page_reread_real_db.py -o addopts=
"""
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = [pytest.mark.database,
              pytest.mark.skipif(os.getenv("PYTEST_REAL_DB") != "1", reason="real-DB test")]


@pytest.fixture(scope="module")
def cur():
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    c = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    yield c.cursor()
    c.close()


@pytest.mark.database
def test_every_served_chapter_has_a_content_hash_to_queue_under(cur):
    # The tool refuses a chapter without one; the commit only takes rows whose
    # hash matches the registry. A missing hash would make that chapter unfixable.
    cur.execute("""SELECT count(*) FROM (SELECT DISTINCT source_council, source_chapter_key
                   FROM regulatory_provisions WHERE is_current AND source_council IS NOT NULL) s
                   JOIN dcp_chapter_registry r ON r.council = s.source_council
                    AND r.chapter_key = s.source_chapter_key AND r.is_active
                   WHERE r.content_hash IS NULL""")
    assert cur.fetchone()[0] == 0


@pytest.mark.database
def test_stored_ref_tails_are_what_merge_codes_compares(cur):
    import dcp_page_reread as R
    cur.execute("SELECT ref_number FROM regulatory_provisions WHERE is_current "
                "AND source_council='marrickville' AND source_chapter_key='part3-subdivision' LIMIT 5")
    tails = {r[0].rpartition("__")[2] for r in cur.fetchall()}
    assert tails and all("." not in t for t in tails)
    t = next(iter(tails))
    got, ext = R.merge_codes([{"code": t.replace("_", "."), "text": "x"}], taken=tails)
    assert got == [] and t in ext
