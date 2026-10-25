"""dq_db.paged_rows against the REAL production database (read-only).

prior-art-checked: no test covers dq_db.paged_rows (new 2026-10-25); pattern from
tests/test_drawdown_verify_real_db.py.

Paging must return exactly the served set -- every row once, none skipped -- or a
DQ probe built on it could read clean while rows were missed.

Run it:
    PYTEST_REAL_DB=1 pytest -m database tests/test_dq_db_paged_real_db.py -v
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

pytestmark = pytest.mark.database

_REAL_DB_REQUESTED = os.environ.get("PYTEST_REAL_DB") == "1"


@pytest.fixture()
def conn():
    if not _REAL_DB_REQUESTED:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database "
                    "tests/test_dq_db_paged_real_db.py")
    import dq_db

    c = dq_db.connect()
    dq_db.pin_snapshot(c)
    yield c
    c.close()


def test_paged_rows_returns_every_served_row_once(conn):
    import dq_db

    cur = conn.cursor()
    rows = dq_db.paged_rows(cur, "id", "source_council IS NOT NULL")
    ids = [r[0] for r in rows]
    cur.execute("SELECT count(*) FROM regulatory_provisions "
                "WHERE is_current AND v2_is_actionable AND source_council IS NOT NULL")
    expected = cur.fetchone()[0]
    assert expected > 0
    assert len(ids) == expected
    assert len(set(ids)) == len(ids)
    assert ids == sorted(ids)


def test_paged_rows_only_serves_current_actionable_rows(conn):
    import dq_db

    cur = conn.cursor()
    ids = [r[0] for r in dq_db.paged_rows(cur, "id")]
    cur.execute("SELECT count(*) FROM regulatory_provisions "
                "WHERE id = ANY(%s) AND NOT (is_current AND v2_is_actionable)", (ids,))
    assert cur.fetchone()[0] == 0
