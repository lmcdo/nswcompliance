"""Real-database and real-PDF check of the page-cells decision, read only. Opt in:
PYTEST_REAL_DB=1 DATABASE_URL=... R2_ACCOUNT_ID=... pytest tests/test_dcp_decide_by_page_cells_real_db.py -o addopts= -m database

conftest_mocks stubs psycopg2 by default, so the flag is required; without it the tests skip (never pass). Nothing is written."""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import dcp_decide_by_page_cells as d  # noqa: E402
from dcp_approve_proven import CHAPTER_ROWS_SQL  # noqa: E402


def _conn():
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL") or not os.environ.get("R2_BUCKET_NAME"):
        pytest.skip("real database and R2 test: run with PYTEST_REAL_DB=1 DATABASE_URL=... R2_* set -o addopts= -m database; skipped, not a pass")
    import psycopg2

    return psycopg2.connect(os.environ["DATABASE_URL"], options="-c default_transaction_read_only=on -c statement_timeout=30000")


@pytest.mark.database
def test_every_approved_row_of_a_real_sample_has_all_its_cells_on_its_page():
    conn = _conn()
    cur = conn.cursor()
    cur.execute(CHAPTER_ROWS_SQL, ("waverley", "waverley-dcp-2022"))
    rows = cur.fetchall()
    conn.close()
    if not rows:
        pytest.skip("no pending Waverley rows to sample (the chapter may be published)")
    pages = d.load_pages(rows[0][5])
    approved = 0
    for qid, change_type, ref, text, page, *_ in rows[:300]:
        window = d.page_window(pages, page)
        verdict = d.decide(change_type, text, window)
        assert verdict in ("approve", "skip")
        if verdict == "approve":
            approved += 1
            assert change_type != "removed" and text
            body = d.norm(__import__("re").sub(r"^#[^\n]*\n+", "", text))
            assert body in window or all(d.norm(c) in window for c in d.cells(text)), qid
    assert approved > 0
