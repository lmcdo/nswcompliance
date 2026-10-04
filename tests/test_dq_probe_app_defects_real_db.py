"""dq_probe_app_defects: the house-number matcher, and the two SQL checks against the real database.

The matcher decides whether /api/property returned the property asked for (DQ-122), so a lax match
would turn the row green while the wrong property is served. The SQL checks run only when asked for:

    PYTEST_REAL_DB=1 pytest -m database tests/test_dq_probe_app_defects_real_db.py -o addopts=
"""
from __future__ import annotations

import json
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


# --- DQ-125: red when a served renderer stops handling tables, whatever the data says. ---

def test_dq125_red_when_a_renderer_is_not_routed(monkeypatch, tmp_path):
    fe = tmp_path / "frontend-nextjs"
    for rel, body in {
        "components/compliance/FormattedProvisionText.tsx": "splitProvisionTables(",
        "components/compliance/PageGroupedProvisions.tsx": "provisionTablesToPlainText(provision.provision_text",
        "components/pdf/ProvisionTable.tsx": "sanitizeForPdf(provision.provision_text)",  # not routed
    }.items():
        f = fe / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        f.write_text(body, encoding="utf-8")
    monkeypatch.setattr(p, "ROOT", tmp_path)
    monkeypatch.setattr(p, "_sql_count", lambda sql, what: (0, f"0 {what}"))
    rc, msg = p.dq125()
    assert rc == 1 and "pdf/ProvisionTable.tsx" in msg


def test_dq125_could_not_look_is_never_clean(monkeypatch):
    monkeypatch.setattr(p, "_sql_count", lambda sql, what: (2, "database unreachable"))
    assert p.dq125()[0] == 2


# --- DQ-127: another council's LEP in a Waverley property's currency panel. ---

class _Resp:
    def __init__(self, body):
        self._b = json.dumps(body).encode()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def read(self, *a):
        return self._b


def _serve(monkeypatch, rows):
    monkeypatch.setattr(p.urllib.request, "urlopen", lambda req, timeout=60: _Resp({"currency": rows}))


def test_dq127_red_on_a_foreign_lep(monkeypatch):
    _serve(monkeypatch, [{"instrument_key": "waverley_lep_2012", "instrument_type": "lep"},
                         {"instrument_key": "bayside_lep_2021", "instrument_type": "lep"}])
    rc, msg = p.dq127()
    assert rc == 1 and "bayside_lep_2021" in msg


def test_dq127_clean_with_own_lep_and_statewide_sepps(monkeypatch):
    _serve(monkeypatch, [{"instrument_key": "waverley_lep_2012", "instrument_type": "lep"},
                         {"instrument_key": "housing_sepp", "instrument_type": "sepp"}])
    assert p.dq127()[0] == 0


def test_dq127_unreachable_is_could_not_look(monkeypatch):
    def boom(req, timeout=60):
        raise OSError("down")
    monkeypatch.setattr(p.urllib.request, "urlopen", boom)
    assert p.dq127()[0] == 2


@pytest.mark.database
def test_dq127_runs_against_the_live_site():
    _need_db()
    rc, msg = p.dq127()
    assert rc in (0, 1), msg


def test_dq127_red_when_the_own_lep_is_missing(monkeypatch):
    _serve(monkeypatch, [{"instrument_key": "housing_sepp", "instrument_type": "sepp"}])
    rc, msg = p.dq127()
    assert rc == 1 and "exactly once" in msg


def test_dq127_red_when_the_own_lep_is_doubled(monkeypatch):
    _serve(monkeypatch, [{"instrument_key": "waverley_lep_2012", "instrument_type": "lep"}] * 2)
    assert p.dq127()[0] == 1
