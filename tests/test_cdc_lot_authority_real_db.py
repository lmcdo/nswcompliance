"""Real-database layer for services/cdc_lot_authority.py (read-only session).

Proves the production rows themselves satisfy the authority contract: the three
founder-verified standards' quotes are found in their cited provision text, the
document carries a legislation.nsw.gov.au URL and PDF pages. The width standard
(migration 082) fails ONLY for lack of manual verification until the founder signs it.
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

pytestmark = pytest.mark.database

from services.cdc_lot_authority import REQUIRED_STANDARDS, load_authority, validate_authority  # noqa: E402


def test_production_authority_fails_only_on_unverified_standards():
    conn = _real_conn()
    try:
        outcome = load_authority(conn)
    finally:
        conn.close()
    if outcome.authority is not None:
        assert set(outcome.authority.standards) == set(REQUIRED_STANDARDS)
        return
    for f in outcome.failures:
        assert "not manually verified" in f, f  # no query, quote, URL or page failure


def test_production_rows_validate_once_every_standard_is_verified():
    """Same real rows, with manual_verified forced True in memory only: the quotes,
    provision text, source URL and PDF pages must all hold up."""
    conn = _real_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, standard_type, numeric_value, applicable_zones, ref_number, source_provision_ids, "
            "source_quote, manual_verified, verified_by, verified_at, stale_since, stale_reason "
            "FROM cdc_eligibility_standards WHERE code_name = 'housing_code' AND is_active "
            "AND standard_type = ANY(%s)", (list(REQUIRED_STANDARDS),))
        cols = [d[0] for d in cur.description]
        standards = [dict(zip(cols, r), manual_verified=True) for r in cur.fetchall()]
        ids = sorted({int(i) for s in standards for i in s.get("source_provision_ids") or []})
        cur.execute("SELECT id, document_id, provision_text, pdf_page, is_current "
                    "FROM regulatory_provisions WHERE id = ANY(%s)", (ids,))
        cols = [d[0] for d in cur.description]
        provisions = [dict(zip(cols, r)) for r in cur.fetchall()]
        cur.execute("SELECT id, source_url, r2_pdf_url FROM documents WHERE id = ANY(%s)",
                    (sorted({p.get("document_id") for p in provisions}),))
        cols = [d[0] for d in cur.description]
        documents = [dict(zip(cols, r)) for r in cur.fetchall()]
    finally:
        conn.close()
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is not None, outcome.failures
