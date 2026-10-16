"""Woollahra D1 centre outlines against the REAL boundaries table, read-only.

The importer's own proof (prove(): every test address inside its centre, every neighbour
address outside all of them) re-run on the outlines that are live, so a later edit to an
outline or to the lookup that breaks an address fails here rather than on the page.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

pytestmark = pytest.mark.database
_REAL = os.environ.get("PYTEST_REAL_DB") == "1"


@pytest.fixture
def ro_cursor():
    if not _REAL:
        pytest.skip("Real-DB test. Run with: PYTEST_REAL_DB=1 pytest -m database -o addopts= <file>")
    import dq_db
    conn = dq_db.connect()  # read-only session
    try:
        yield conn.cursor()
    finally:
        conn.close()


def test_every_live_d1_outline_passes_its_own_address_proof(ro_cursor):
    import import_woollahra_d1_centre_boundaries as m
    feats = m.load()
    assert len(feats) == 10  # nine centres + their union
    ro_cursor.execute("SELECT precinct_id FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = ANY(%s)",
                      (m.LGA, [f["properties"]["precinct_id"] for f in feats]))
    assert len(ro_cursor.fetchall()) == 10, "a D1 outline in centres.geojson is not loaded"
    assert m.prove(ro_cursor, feats) == []
