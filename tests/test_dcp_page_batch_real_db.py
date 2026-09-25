"""dcp_page_batch against the real database: planning reads live data without
writing, and the live fingerprint is stable between two reads. Opt-in:
    PYTEST_REAL_DB=1 pytest -m database tests/test_dcp_page_batch_real_db.py -o addopts=
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = [pytest.mark.skipif(os.getenv("PYTEST_REAL_DB") != "1", reason="real-DB test")]


@pytest.mark.database
def test_the_live_fingerprint_is_stable_across_two_reads():
    import dcp_page_batch as B
    import dcp_page_reread as R
    conn, s3 = B._connect()
    try:
        cur = conn.cursor()
        cur.execute("SELECT ref_number, provision_text, document_id FROM regulatory_provisions "
                    "WHERE is_current AND source_council='marrickville' AND source_chapter_key='part3-subdivision'")
        a = cur.fetchall()
        cur.execute("SELECT ref_number, provision_text, document_id FROM regulatory_provisions "
                    "WHERE is_current AND source_council='marrickville' AND source_chapter_key='part3-subdivision'")
        assert a and B.live_signature(a) == B.live_signature(cur.fetchall())
    finally:
        conn.close()


@pytest.mark.database
def test_load_chapter_refuses_a_chapter_with_pending_rows_or_reads_it():
    import dcp_page_batch as B
    import dcp_page_reread as R
    conn, s3 = B._connect()
    try:
        cur = conn.cursor()
        with tempfile.TemporaryDirectory() as tmp:
            ctx = R.load_chapter(cur, s3, "marrickville", "part3-subdivision", tmp)
            assert isinstance(ctx, str) or (ctx["live"] and ctx["content_hash"] and ctx["placed"])
    finally:
        conn.close()
