"""Against the real database: the granny flat report never prints a setback clause whose
verdict is not shown (migration 077). Opt-in (PYTEST_REAL_DB=1 DATABASE_URL=...)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

pytestmark = [pytest.mark.database, pytest.mark.skipif(
    os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"),
    reason="real-DB test: set PYTEST_REAL_DB=1 and DATABASE_URL")]


@pytest.mark.database
def test_granny_flat_prints_the_page_for_every_withheld_clause():
    import psycopg2
    import conveyancing_db as cdb
    from services.granny_flat import _fetch_sd_setbacks
    conn = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    conn.set_session(readonly=True, autocommit=True)
    try:
        cur = conn.cursor()
        cur.execute("SET statement_timeout = '30000'")
        cur.execute("SELECT lga, section_ref FROM dcp_setback_controls WHERE is_current "
                    "AND (needs_review IS NULL OR needs_review = FALSE) "
                    "AND (applicability = 'secondary_dwelling_specific' OR dev_type = 'secondary_dwelling') "
                    "AND (citation_status IS NULL OR citation_status <> ALL(%s))",
                    (sorted(cdb.CLAUSE_SHOWN_STATUSES),))
        withheld = cur.fetchall()
        assert withheld, "no withheld secondary-dwelling clause to test against"
        for lga in sorted({lga for lga, _ in withheld})[:5]:
            refs = {ref for l, ref in withheld if l == lga and ref}
            for e in (_fetch_sd_setbacks(conn, lga) or {}).get("sd_setbacks") or []:
                assert e["clause"] not in refs, f"{lga}: withheld clause {e['clause']!r} printed"
    finally:
        conn.close()
