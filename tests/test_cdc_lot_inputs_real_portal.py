"""Real-HTTP layer for services/cdc_lot_inputs.py: live Planning Portal, Valuer
General and cadastre for addresses measured on 2026-10-07. A planning change at
one of these addresses (rezoning, subdivision) will fail this test, and that is
the point: the facts are re-read, never cached.
"""
import os
import sys
from pathlib import Path

import pytest
from dotenv import load_dotenv

# prior-art-checked: reuse — the real-layer pattern of tests/test_drawdown_verify_real_db.py
# (opt-in flag, scripts/dq_db.main_checkout() for the .env, explicit skip reason).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
from dq_db import main_checkout  # noqa: E402

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"
if _REAL_DB_REQUESTED:
    load_dotenv(main_checkout() / ".env")


def _real_conn():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m \"database or integration\" " + __file__)
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("PYTEST_REAL_DB=1 set but no DATABASE_URL available.")
    import psycopg2

    conn = psycopg2.connect(url, options="-c statement_timeout=30000 -c default_transaction_read_only=on")
    conn.autocommit = True
    return conn

pytestmark = pytest.mark.integration

from services.cdc_lot_inputs import load_lot_inputs  # noqa: E402


def _inputs(address):
    # conftest_mocks.py stubs `requests` unless PYTEST_REAL_HTTP=1; without it every
    # Portal call returns a MagicMock, so skip loudly rather than test a stub. A real
    # lookup that fails to resolve the address is a FAILURE, not a skip.
    if os.environ.get("PYTEST_REAL_HTTP") != "1":
        pytest.skip("Live-HTTP test. Run with: PYTEST_REAL_DB=1 PYTEST_REAL_HTTP=1 pytest -m integration " + __file__)
    conn = _real_conn()
    try:
        return load_lot_inputs(address, conn, 2)
    finally:
        conn.close()


def test_mascot_small_rectangular_r2_lot():
    _prop, inp = _inputs("1 Coward Street, Mascot NSW 2020")
    assert inp.zones == frozenset({"R2"})  # noqa: zone-codes — measured live fact for this address
    assert len(inp.areas) == 2 and all(r.value_m2 < 200 for r in inp.areas)
    assert inp.width_range_m is not None and inp.width_range_m[0] >= 6
    assert inp.ass_classes == frozenset({5})


def test_campsie_multi_lot_property_area_unknown():
    _prop, inp = _inputs("12 Second Avenue, Campsie NSW 2194")
    assert inp.areas == () and "lots" in (inp.area_reason or "")
    assert inp.width_range_m is None


def test_belmore_not_on_acid_sulfate_map():
    _prop, inp = _inputs("22 Yangoora Road, Belmore NSW 2192")
    assert inp.ass_classes == frozenset()
