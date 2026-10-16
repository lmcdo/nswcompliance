"""Canterbury-Bankstown 7.2 centre outlines against the REAL boundaries table, read-only.

Every outline in centres_7_2.geojson is loaded, a point inside each is found by the site's own
lookup (ST_PointOnSurface -- the stored centroid is ST_Centroid and can sit between the parts of
a multi-part outline), and the address-audit lots outside every centre still resolve to nothing.
"""
import json
import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

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


def test_every_7_2_outline_is_live_and_found_by_the_site_lookup(ro_cursor):
    import import_cb_centre_boundaries as m
    ids = [f["properties"]["precinct_id"] for f in json.loads(
        (ROOT / "data" / "canterbury_bankstown_precincts" / "centres_7_2.geojson").read_text(encoding="utf-8"))["features"]]
    assert "7.2" in ids and set(ids) <= m.RASTER_IDS["centres_7_2.geojson"]
    for pid in ids:
        ro_cursor.execute("SELECT ST_X(ST_PointOnSurface(boundary)), ST_Y(ST_PointOnSurface(boundary))"
                          " FROM dcp_precinct_boundaries WHERE lga = %s AND precinct_id = %s", (m.LGA, pid))
        row = ro_cursor.fetchone()
        assert row, f"{pid} not loaded"
        ro_cursor.execute(m.LOOKUP_SQL, (row[0], row[1], "CANTERBURY-BANKSTOWN"))
        assert pid in {r[0] for r in ro_cursor.fetchall()}, pid
    for label, (x, y) in m.OUTSIDE_ALL.items():
        ro_cursor.execute(m.LOOKUP_SQL, (x, y, "CANTERBURY-BANKSTOWN"))
        assert ro_cursor.fetchall() == [], label
