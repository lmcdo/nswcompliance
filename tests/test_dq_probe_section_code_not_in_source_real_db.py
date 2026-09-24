"""DQ-111 probe against the real database: it judges exactly the served set.

The probe's number is only as good as the rows it reads. A join that silently
drops rows (no active registry entry) or duplicates them (two active entries)
would move the headline without any citation changing. Measured 2026-09-24:
14,509 served council rows, each joined to exactly one active registry PDF.

Opt-in, like every real-DB test here:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_dq_probe_section_code_not_in_source_real_db.py -o addopts=
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

pytestmark = [
    pytest.mark.database,
    pytest.mark.skipif(os.getenv("PYTEST_REAL_DB") != "1",
                       reason="real-DB test: set PYTEST_REAL_DB=1 and DATABASE_URL"),
]


@pytest.fixture(scope="module")
def conn():
    import psycopg2
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
    c = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=30)
    yield c
    c.close()


def test_every_served_row_is_judged_once_against_one_pdf(conn):
    import dq_probe_section_code_not_in_source as p
    served_total, rows = p.fetch_served(conn)
    ids = [r[0] for r in rows]
    assert len(ids) == len(set(ids)), "a served row joined more than one active PDF"
    assert len(rows) == served_total, "served rows with no active registry PDF are silently unjudged"
    assert all(r[4] for r in rows), "a row joined a registry entry with no R2 path"


def test_council_filter_narrows_without_losing_rows(conn):
    import dq_probe_section_code_not_in_source as p
    _, rows = p.fetch_served(conn, "woollahra")
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM regulatory_provisions WHERE is_current AND v2_is_actionable "
                "AND source_council = 'woollahra'")
    assert rows and {r[1] for r in rows} == {"woollahra"}
    assert len(rows) == cur.fetchone()[0]
