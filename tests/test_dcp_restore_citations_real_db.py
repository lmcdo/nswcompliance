"""The citation repair against the real database -- read-only.

drop_collisions is the only thing standing between a planned correction and
uq_provisions_current_identity aborting a batch midway (or two rules becoming
indistinguishable). It is checked here against a REAL current row: a plan that
reproduces that row's identity under another id must be refused, and a plan
with a fresh identity must pass.

Opt-in, like every real-DB test here:
    PYTEST_REAL_DB=1 DATABASE_URL=<supabase pooler url> pytest -m database \
        tests/test_dcp_restore_citations_real_db.py -o addopts=
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
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


@pytest.fixture(scope="module")
def live_row(conn):
    cur = conn.cursor()
    cur.execute("SELECT id, document_id, ref_number, section_header, provision_text "
                "FROM regulatory_provisions WHERE is_current AND source_council = 'woollahra' "
                "AND provision_text LIKE '#%%' ORDER BY id LIMIT 1")
    row = cur.fetchone()
    assert row, "no current woollahra row to test against"
    return row


def plan(row, **over):
    rid, doc, ref, header, text = row
    p = {"id": rid, "document_id": doc or "", "new_ref": ref, "new_header": header,
         "new_text": text, "old_ref": ref}
    p.update(over)
    return p


def test_a_plan_reproducing_another_current_rows_identity_is_refused(conn, live_row):
    import dcp_restore_citations as r
    clash = plan(live_row, id=-1)          # same identity, different row
    kept, clashes = r.drop_collisions(conn, [clash])
    assert kept == [] and clashes == [clash]


def test_a_fresh_identity_passes_and_the_batch_cannot_collide_with_itself(conn, live_row):
    import dcp_restore_citations as r
    fresh = plan(live_row, new_ref=live_row[2] + "__dq111_test_never_written")
    twin = dict(fresh, id=-2)
    kept, clashes = r.drop_collisions(conn, [fresh, twin])
    assert kept == [fresh] and clashes == [twin]
