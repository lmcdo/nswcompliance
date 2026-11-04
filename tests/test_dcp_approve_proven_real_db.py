"""dcp_approve_proven.py run for real against the production queue -- dry run only.

Why a real connection: the approver's row selection (CHAPTER_ROWS_SQL, only rows read from
the chapter's active PDF) and its word-for-word proof against the live R2 PDF cannot be
proven with a mock cursor, which returns whatever a test hard-codes. This runs the real
script the way an operator would, without --apply, and checks the two things that matter:
it finds and proves rows, and it writes nothing.

Measured 2026-11-04 on sutherland_shire/sutherland-dcp-2015-ch2-dwelling-houses: 346
pending, 311 approvable. The test asserts > 0 rather than 311, because the queue moves.

Opt-in via PYTEST_REAL_DB=1, @pytest.mark.database, following
tests/test_dcp_fidelity_gate_real_db.py.

Run it:
    PYTEST_REAL_DB=1 pytest -m database tests/test_dcp_approve_proven_real_db.py -v
"""
import os
import re
import subprocess
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

_SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
_CHAPTER = "sutherland_shire/sutherland-dcp-2015-ch2-dwelling-houses"


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_dcp_approve_proven_real_db.py")
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL available.")


def _status_counts():
    import psycopg2
    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    try:
        cur = conn.cursor()
        council, key = _CHAPTER.split("/")
        cur.execute("SELECT status, count(*) FROM dcp_review_queue WHERE council = %s "
                    "AND chapter_key = %s GROUP BY 1", (council, key))
        return dict(cur.fetchall())
    finally:
        conn.close()


def test_dry_run_proves_rows_and_writes_nothing():
    _skip_if_no_real_db()
    before = _status_counts()
    out = subprocess.run([sys.executable, "dcp_approve_proven.py", "--chapters", _CHAPTER],
                         cwd=_SCRIPTS, capture_output=True, text=True, encoding="utf-8",
                         timeout=600)
    assert out.returncode == 0, out.stderr[-2000:]
    assert "dry run: nothing written" in out.stdout
    m = re.search(r"TOTAL approve (\d+) proven", out.stdout)
    assert m and int(m.group(1)) > 0, out.stdout[-2000:]
    assert _status_counts() == before
