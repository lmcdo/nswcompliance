"""_capacity_ceiling against the real database and the real Planning Portal layers.

Opt-in (same pattern as tests/test_drawdown_verify_real_db.py):
    PYTEST_REAL_DB=1 pytest -m database tests/test_intelligence_brief_capacity_ceiling_live.py -v

Expected values measured 2026-10-19 with the same calls (Winston Hills R2 Parramatta and
Concord R3 Canada Bay; neither is on low/mid-rise land): they change only if the LEP land use
table or the SEPP maps change, which is exactly when this should be looked at again.
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

from services import intelligence_brief as ib  # noqa: E402


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_intelligence_brief_capacity_ceiling_live.py")
    if not os.environ.get("DATABASE_URL") and not os.environ.get("SUPABASE_DB_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL/SUPABASE_DB_URL available.")


@pytest.mark.parametrize("zone,lga,lat,lng,area,ceiling", [
    ("R2", "CITY OF PARRAMATTA", -33.7765, 150.9856, 688.05, "dual_occupancy"),
    ("R3", "CANADA BAY", -33.8540, 151.1047, 848.36, "multi_dwelling_housing"),
])
def test_live_ceiling(zone, lga, lat, lng, area, ceiling):
    _skip_if_no_real_db()
    floor, got, from_lmr, _citation = ib._capacity_ceiling(zone, lga, lat, lng, area, False)
    assert (floor, got, from_lmr) == ("dwelling_house", ceiling, False)


def test_live_unknown_lga_fails_safe_to_a_house():
    _skip_if_no_real_db()
    _floor, got, _lmr, _c = ib._capacity_ceiling("R2", "NOT A REAL COUNCIL", -33.7765, 150.9856, 688.05, False)
    assert got == "dwelling_house"
