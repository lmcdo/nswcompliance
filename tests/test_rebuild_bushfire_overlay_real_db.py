"""Real-database checks. Opt in: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -o addopts= -m database. Read-only. (conftest_mocks stubs psycopg2 otherwise.)"""
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))


def _conn():
    if os.environ.get("PYTEST_REAL_DB") != "1" or not os.environ.get("DATABASE_URL"):
        pytest.skip("real database test: run with PYTEST_REAL_DB=1 DATABASE_URL=... pytest -o addopts= -m database")
    import psycopg2

    c = psycopg2.connect(os.environ["DATABASE_URL"], connect_timeout=20)
    c.set_session(readonly=True, autocommit=True)
    c.cursor().execute("SET statement_timeout = '60000'")
    return c


@pytest.mark.database
def test_the_real_overlay_holds_every_staged_id_form_and_counts_split_pieces_as_their_area():
    import rebuild_bushfire_overlay as rb

    c = _conn()
    cur = c.cursor()
    cur.execute("SELECT count(*) FROM spatial_overlays WHERE layer_type = 'bushfire'")
    rows = cur.fetchone()[0]
    cur.execute("SELECT count(DISTINCT CASE WHEN source_oid >= %s THEN (source_oid - %s) / 100000 ELSE source_oid END) FROM spatial_overlays WHERE layer_type = 'bushfire'",
                (rb.PIECE_OID_BASE, rb.PIECE_OID_BASE))
    areas = cur.fetchone()[0]
    assert rows > 100_000 and 0 < areas <= rows


@pytest.mark.integration
def test_the_live_state_service_lists_a_full_layer():
    if os.environ.get("PYTEST_REAL_HTTP") != "1":
        pytest.skip("needs PYTEST_REAL_HTTP=1 (otherwise requests is a stand-in); not a pass")
    import rebuild_bushfire_overlay as rb

    assert len(rb.live_ids()) > 100_000
