"""dq_probe_app_defects: the house-number matcher, and the two SQL checks against the real database.

The matcher decides whether /api/property returned the property asked for (DQ-122), so a lax match
would turn the row green while the wrong property is served. The SQL checks run only when asked for:

    PYTEST_REAL_DB=1 pytest -m database tests/test_dq_probe_app_defects_real_db.py -o addopts=
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]
from dq_db import main_checkout  # noqa: E402

_REAL_DB = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB:
    load_dotenv(main_checkout() / ".env")

import dq_probe_app_defects as p  # noqa: E402


@pytest.mark.parametrize("asked,returned,ok", [
    ("700", "893 NEW SOUTH HEAD ROAD ROSE BAY 2029", False),   # the 2026-10-04 defect
    ("235", "582 NEW SOUTH HEAD ROAD POINT PIPER 2027", False),
    ("680", "674-680 NEW SOUTH HEAD ROAD ROSE BAY 2029", True),  # inside a range
    ("20", "20 38 BAY STREET DOUBLE BAY 2028", True),
    ("20", "120 BAY STREET DOUBLE BAY 2028", False),            # a prefix is not a match
    ("203", "SHOP 24A 203-233 NEW SOUTH HEAD ROAD EDGECLIFF", True),
    ("", "60 HALL STREET", False),
    ("60", "", False),
])
def test_number_matches(asked, returned, ok):
    assert p._number_matches(asked, returned) is ok


def _need_db():
    if not _REAL_DB:
        pytest.skip("Real-DB test. Run with PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_dq_probe_app_defects_real_db.py -o addopts=")


@pytest.mark.database
@pytest.mark.parametrize("check", ["DQ-125", "DQ-126", "DQ-123"])
def test_sql_checks_run_against_the_real_database(check):
    _need_db()
    rc, msg = p.CHECKS[check]()
    assert rc in (0, 1), msg  # 2 would mean it could not look; a broken query raises
    assert msg
