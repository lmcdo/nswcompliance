"""Real-layer test of POST /pipeline/cdc/lot-requirements: real database (read-only
session) and live Planning Portal, through FastAPI's TestClient."""
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

pytestmark = [pytest.mark.database, pytest.mark.integration]

from fastapi import FastAPI  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

import services.cdc_lot_requirements_api as api  # noqa: E402


@pytest.mark.database
@pytest.mark.integration
def test_mascot_end_to_end(monkeypatch):
    if os.environ.get("PYTEST_REAL_HTTP") != "1":
        pytest.skip("Live-HTTP test. Run with: PYTEST_REAL_DB=1 PYTEST_REAL_HTTP=1 pytest -m integration " + __file__)
    conn = _real_conn()
    monkeypatch.setattr(api, "_connect", lambda: conn)
    app = FastAPI()
    app.include_router(api.router)
    resp = TestClient(app).post("/pipeline/cdc/lot-requirements",
                                json={"address": "1 Coward Street, Mascot NSW 2020"})
    body = resp.json()
    if resp.status_code == 503:
        # Until the width standard is signed off, the only permitted failure.
        assert body["result"] == "UNAVAILABLE" and body["criteria"] == []
        assert all("not manually verified" in f for f in body["authority_failures"])
        return
    assert resp.status_code == 200
    assert body["result"] == "EXCLUDED"
    area = [c for c in body["criteria"] if c["criterion"] == "lot_area"][0]
    assert area["outcome"] == "FAIL"
    assert area["authority"]["source_url"].startswith("https://legislation.nsw.gov.au/")
    assert area["authority"]["pdf_pages"] == [112, 113]
