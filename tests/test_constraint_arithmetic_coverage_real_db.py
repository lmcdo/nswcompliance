"""Real-database check of the DCP coverage lookup the building-area card reads (migration 105).

prior-art-checked: reuse, not reinvention -- follows tests/test_drawdown_verify_real_db.py:
opt-in via PYTEST_REAL_DB=1, @pytest.mark.database, .env located through scripts/dq_db.main_checkout,
and loaded only when the flag is set so a plain pytest run never pulls the production credential.

    PYTEST_REAL_DB=1 pytest -m database tests/test_constraint_arithmetic_coverage_real_db.py -o addopts=
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

from services.constraint_arithmetic import _fetch_dcp_coverage  # noqa: E402


def _skip_if_no_real_db():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_constraint_arithmetic_coverage_real_db.py -o addopts=")
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL available.")


def test_a_recorded_finding_is_returned_with_its_source():
    _skip_if_no_real_db()
    rows = _fetch_dcp_coverage("liverpool", "dual_occupancy")
    assert rows, "migration 105's Liverpool row is missing"
    found = rows[0]
    assert found["coverage"] == "none" and found["control_type"] is None
    assert "Liverpool DCP 2008" in found["statement"]
    assert found["evidence_url"].startswith("https://www.liverpool.nsw.gov.au/")


def test_a_partial_finding_carries_the_dcps_own_words():
    _skip_if_no_real_db()
    found = _fetch_dcp_coverage("ryde", "dual_occupancy")[0]
    assert found["coverage"] == "partial"
    assert found["evidence_quote"] == "Dwelling Houses and Dual Occupancy (attached)"


def test_no_finding_for_a_council_and_type_that_has_none():
    _skip_if_no_real_db()
    assert _fetch_dcp_coverage("liverpool", "dwelling_house") is None


def test_a_per_control_finding_names_its_control():
    _skip_if_no_real_db()
    rows = _fetch_dcp_coverage("city_of_sydney", "secondary_dwelling")
    assert {r["control_type"] for r in rows} >= {"front_setback", "side_setback", "rear_setback"}
