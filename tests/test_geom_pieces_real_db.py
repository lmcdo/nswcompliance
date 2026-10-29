"""services/geom_pieces.delete_replaced against the REAL database, always rolled back.

A loader re-run must clear what an earlier run stored for the same features (the
original row and every piece key in its range) before it upserts the new pieces.
Measured 2026-10-29: for Cessnock's 15 flood features it removes exactly the 3,950
stored pieces. Opt-in like tests/test_drawdown_verify_real_db.py:

    PYTEST_REAL_DB=1 pytest -m database tests/test_geom_pieces_real_db.py -v
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")

pytestmark = pytest.mark.database

KEY = "PARTIAL_CESSNOCK_1PCT_1pctAEP"


def test_a_rerun_clears_every_stored_piece_of_its_features_then_rolls_back():
    if not _REAL_DB_REQUESTED or not os.environ.get("DATABASE_URL"):
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database tests/test_geom_pieces_real_db.py")
    import psycopg2
    from services.geom_pieces import delete_replaced

    conn = psycopg2.connect(os.environ["DATABASE_URL"], options="-c statement_timeout=25000")
    try:
        cur = conn.cursor()
        cur.execute("SELECT count(*) FROM spatial_overlays WHERE layer_type='flood' AND instrument_key=%s", (KEY,))
        stored = cur.fetchone()[0]
        assert stored > 0
        rows = [(KEY, "CESSNOCK", "flood", None, None, None, oid, "") for oid in range(1, 16)]
        assert delete_replaced(cur, rows) == stored
        cur.execute("SELECT count(*) FROM spatial_overlays WHERE layer_type='flood' AND instrument_key=%s", (KEY,))
        assert cur.fetchone()[0] == 0
    finally:
        conn.rollback()
        conn.close()
