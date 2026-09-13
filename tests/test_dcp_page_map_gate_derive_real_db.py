"""Waverley's part boundaries, derived from the REAL mirrored PDF.

tests/test_dcp_page_map_derive.py pins the rules on a fixture. This runs them on the
document they were measured against, downloaded from R2 exactly as the extractor
downloads it. Read-only.

Measured 2026-09-13 on the 448-page PDF, and asserted here:
  * 32 contiguous parts, B1 through F4, from 365 pages carrying an exact header;
  * C1 Low Density Residential on pages 167-198 -- the deleted map said 186-218;
  * no E7: the pages the old map gave "Edina Estate" are E-annexures in this version.

If the council republishes the document, these numbers move and the test fails.
That is the point: it says the derivation must be re-checked against the new PDF,
rather than letting a stale expectation pass quietly.

Run:
    PYTEST_REAL_DB=1 pytest -m database tests/test_dcp_page_map_gate_derive_real_db.py -o addopts=
"""
import os
import sys
import tempfile
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))

pytestmark = pytest.mark.database


def _download_waverley_pdf(target: str) -> None:
    if os.environ.get("PYTEST_REAL_DB") != "1":
        pytest.skip("Real-data test. Run with PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_dcp_page_map_gate_derive_real_db.py -o addopts=")
    from dotenv import load_dotenv
    from dq_db import main_checkout  # a worktree has no .env of its own
    load_dotenv(main_checkout() / ".env")
    url = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
    needed = ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET_NAME")
    if not url or not all(os.environ.get(k) for k in needed):
        pytest.fail("PYTEST_REAL_DB=1 was set but database or R2 credentials are missing "
                    "-- an explicitly requested real-data test must not pass by skipping.")
    import boto3
    import psycopg2
    conn = psycopg2.connect(url, connect_timeout=20)
    conn.set_session(readonly=True, autocommit=True)
    try:
        cur = conn.cursor()
        cur.execute("SELECT r2_current_path FROM dcp_chapter_registry "
                    "WHERE council='waverley' AND chapter_key='waverley-dcp-2022' AND is_active")
        row = cur.fetchone()
    finally:
        conn.close()
    assert row and row[0], "waverley-dcp-2022 has no mirrored PDF in the registry"
    s3 = boto3.client(
        "s3", endpoint_url="https://" + os.environ["R2_ACCOUNT_ID"] + ".r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"], region_name="auto")
    s3.download_file(os.environ["R2_BUCKET_NAME"], row[0], target)


def test_waverley_parts_are_derived_from_the_real_document():
    import pdfplumber
    from scripts.dcp_page_map_gate import (
        assert_map_usable, check_ranges_match_headers, derive_ranges_from_headers,
        page_part_codes)

    with tempfile.TemporaryDirectory() as td:
        local = os.path.join(td, "waverley.pdf")
        _download_waverley_pdf(local)
        with pdfplumber.open(local) as pdf:
            pdf_pages = len(pdf.pages)
            texts = []
            for page in pdf.pages:
                texts.append(page.extract_text() or "")
                page.flush_cache()

    ranges = derive_ranges_from_headers(texts)
    by_code = {code: (start, end) for code, _title, start, end in ranges}

    assert pdf_pages == 448, f"the mirrored PDF is now {pdf_pages} pages -- re-measure"
    assert len(ranges) == 32
    assert by_code["C1"] == (167, 198)
    assert "E7" not in by_code
    # The derived ranges must satisfy the same gate the extractor applies, and must
    # sit on their own pages by the gate's own header check.
    assert_map_usable("waverley", "waverley-dcp-2022", ranges, pdf_pages)
    assert check_ranges_match_headers(ranges, page_part_codes(texts), pdf_pages)["violations"] == []
