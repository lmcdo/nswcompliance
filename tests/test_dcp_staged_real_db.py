"""stage_file / publish_staged against the real dcp_chapter_registry schema (migration 125).

    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database tests/test_dcp_staged_real_db.py -o addopts=""

Writes only a throwaway row (council 'zz_staged_test', no provisions) inside a transaction that is always
rolled back, so the proof-clearing triggers on a path change have nothing to clear and nothing persists.
Skips, saying why, if the staged_* columns are not on the database yet.
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database


def _conn():
    if not _REAL:
        pytest.skip("Real-DB test. Run with PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database")
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL.")
    import psycopg2
    return psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=10)


def test_stage_leaves_live_columns_and_publish_switches_them_in_one_row():
    from scripts.dcp_staged import publish_staged, stage_file
    conn = _conn()
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30s'")
        cur.execute("SELECT 1 FROM information_schema.columns WHERE table_name='dcp_chapter_registry' "
                    "AND column_name='staged_r2_path'")
        if not cur.fetchone():
            pytest.skip("migration 125 is not applied to this database yet")
        cur.execute("INSERT INTO dcp_chapter_registry (council, dcp_name, chapter_key, r2_current_path, "
                    "r2_version_label, r2_public_pdf_url, content_hash) "
                    "VALUES ('zz_staged_test','t','c1','old.pdf','v1','https://x/old.pdf','h_old') RETURNING id")
        cid = cur.fetchone()[0]
        stage_file(cur, cid, r2_path="new.pdf", version="v2", public_url="https://x/new.pdf",
                   content_hash="h_new", content_length=7)
        cur.execute("SELECT r2_current_path, content_hash, r2_public_pdf_url, staged_r2_path, "
                    "staged_content_hash FROM dcp_chapter_registry WHERE id=%s", (cid,))
        assert cur.fetchone() == ("old.pdf", "h_old", "https://x/old.pdf", "new.pdf", "h_new")
        assert publish_staged(cur, "zz_staged_test", "c1") is True
        cur.execute("SELECT r2_current_path, r2_version_label, content_hash, r2_public_pdf_url, "
                    "url_content_length, staged_r2_path, staged_content_hash, staged_at "
                    "FROM dcp_chapter_registry WHERE id=%s", (cid,))
        assert cur.fetchone() == ("new.pdf", "v2", "h_new", "https://x/new.pdf", 7, None, None, None)
        assert publish_staged(cur, "zz_staged_test", "c1") is False   # nothing left to publish
    finally:
        conn.rollback()
        conn.close()
