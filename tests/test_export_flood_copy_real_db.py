"""scripts/lmr_area/export_flood_copy.py against the REAL database (opt-in: PYTEST_REAL_DB=1 DATABASE_URL=... pytest -m database -o addopts= ). Read-only: nothing is written to the database or the repo.

conftest_mocks.py stubs psycopg2 by default, so without the opt-in a mock would answer instead of the database.
"""
import json
import os
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

pytestmark = [pytest.mark.skipif(os.environ.get("PYTEST_REAL_DB") != "1", reason="needs PYTEST_REAL_DB=1 and a real DATABASE_URL: psycopg2 is stubbed by default")]


def _cursor():
    import psycopg2

    from scripts.lmr_area.export_flood_copy import database_url

    conn = psycopg2.connect(database_url(), connect_timeout=15)
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 25000")
    return conn, cur


@pytest.mark.database
def test_the_smallest_flood_layer_reads_back_in_full_and_matches_the_committed_manifest():
    from scripts.lmr_area import export_flood_copy as ex

    manifest = json.loads((REPO / "data" / "law" / "maps" / "manifest.json").read_text(encoding="utf-8"))
    conn, cur = _cursor()
    try:
        feats = ex.read_layer(cur, "HNRFS_2024_500AEP", ex.LAYERS["hn_500aep"][1])
        cur.execute("SELECT count(*) FROM spatial_overlays WHERE instrument_key = %s", ("HNRFS_2024_500AEP",))
        in_table = cur.fetchone()[0]
    finally:
        conn.close()
    assert feats is not None and len(feats) == in_table == manifest["layers"]["hn_500aep"]["features"]
    assert all(f["geometry"]["coordinates"] and f["properties"]["scenario"] == "500AEP" for f in feats)
    assert len({f["properties"]["source_oid"] for f in feats}) == len(feats)


@pytest.mark.database
def test_the_export_session_is_read_only():
    import psycopg2

    conn, cur = _cursor()
    try:
        with pytest.raises(psycopg2.Error):
            cur.execute("CREATE TEMP TABLE should_not_exist (x int)")
    finally:
        conn.close()
