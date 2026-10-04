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


# --- DQ-122 verdict: an address the register lacks must say NOT FOUND; one it holds must come back. ---

def _answers(mapping):
    """Stub _lookup: mapping[address] is ('found', addr) | ('not_found', '') | an exception to raise."""
    def fake(addr):
        got = mapping[addr]
        if isinstance(got, Exception):
            raise got
        return got
    return fake


def _correct():
    out = {}
    for addr, number, street, suburb, exists in p.ADDRESSES:
        out[addr] = ("found", f"{number} {street} {suburb} 2000") if exists else ("not_found", "")
    return out


def test_dq122_clean_when_each_address_is_itself_or_not_found(monkeypatch):
    monkeypatch.setattr(p, "_lookup", _answers(_correct()))
    rc, msg = p.dq122()
    assert rc == 0, msg


def test_dq122_red_when_a_missing_address_is_answered_with_a_neighbour(monkeypatch):
    answers = _correct()
    answers["700 New South Head Rd, Rose Bay NSW 2029"] = ("found", "893 NEW SOUTH HEAD ROAD ROSE BAY 2029")
    monkeypatch.setattr(p, "_lookup", _answers(answers))
    rc, msg = p.dq122()
    assert rc == 1 and "893" in msg


def test_dq122_red_when_a_real_address_is_refused(monkeypatch):
    """A fix that says 'not found' for everything must not read as fixed."""
    monkeypatch.setattr(p, "_lookup", _answers({a: ("not_found", "") for a, *_ in p.ADDRESSES}))
    rc, msg = p.dq122()
    assert rc == 1 and "exists in the address register" in msg


def test_dq122_red_when_the_street_differs(monkeypatch):
    answers = _correct()
    answers["60 Hall St, Bondi Beach NSW 2026"] = ("found", "60 OCEAN STREET BONDI BEACH 2026")
    monkeypatch.setattr(p, "_lookup", _answers(answers))
    assert p.dq122()[0] == 1


def test_dq122_red_when_only_the_street_type_differs(monkeypatch):
    """Hall Avenue is not Hall Street."""
    answers = _correct()
    answers["60 Hall St, Bondi Beach NSW 2026"] = ("found", "60 HALL AVENUE BONDI BEACH 2026")
    monkeypatch.setattr(p, "_lookup", _answers(answers))
    assert p.dq122()[0] == 1


def test_dq122_could_not_look_is_never_clean(monkeypatch):
    answers = _correct()
    answers["60 Hall St, Bondi Beach NSW 2026"] = OSError("unreachable")
    monkeypatch.setattr(p, "_lookup", _answers(answers))
    assert p.dq122()[0] == 2


@pytest.mark.database
def test_dq122_runs_against_the_live_site():
    """Real HTTP against DQ_APP_URL (default: production). Opt-in with the real-DB flag."""
    _need_db()
    rc, msg = p.dq122()
    assert rc in (0, 1), msg
    assert msg
