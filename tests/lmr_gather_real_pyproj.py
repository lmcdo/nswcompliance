"""Projection-dependent tests for services/lmr_area_inputs.gather().

These need the REAL pyproj. tests/conftest_mocks.py replaces it with a stub whose transform returns (0, 0). This file is
deliberately not named test_*.py, so a normal run does not collect it (a skip would count against the skip ratchet);
tests/test_lmr_area_inputs.py runs it by path in a child pytest with --noconftest.
"""
import sys
from unittest.mock import MagicMock

import pytest

if isinstance(sys.modules.get("pyproj"), MagicMock):
    pytest.skip("pyproj is a stub in this process; run via test_lmr_area_inputs.py (child pytest --noconftest)",
                allow_module_level=True)

from pyproj import Transformer  # noqa: E402

from services import lmr_area_decision as dec  # noqa: E402
from services import lmr_area_inputs as inp  # noqa: E402
from services import lmr_walk_surface as ws  # noqa: E402

LAT, LNG = -33.8880, 151.1260  # a point in Ashfield
RING = [[LNG, LAT], [LNG + 0.0002, LAT], [LNG + 0.0002, LAT + 0.0002], [LNG, LAT + 0.0002], [LNG, LAT]]


def stations_doc(near_name="Ashfield station"):
    fac = dec.LawFacts.load()
    out = []
    for nm in fac.names("schedule_11_stations") + fac.names("schedule_12_stations"):
        near = nm == near_name
        out.append({"name": nm, "lat": LAT + (0.003 if near else 3.0), "lon": LNG, "entrances": [], "no_mapped_entrance": True})
    return {"stations": out}


@pytest.fixture(autouse=True)
def quiet(monkeypatch):
    monkeypatch.setattr(inp, "_get_json", lambda url, params, post=False: {"features": [{"attributes": {"lganame": "INNER WEST", "OBJECTID": 1}}]} if "FeatureServer/8" in url else {"features": []})
    monkeypatch.setattr(inp, "town_centre_polygons", lambda *a, **k: [])


def test_the_real_projection_is_in_use():
    to_m = Transformer.from_crs(4326, 28356, always_xy=True).transform
    assert to_m(LNG, LAT) != (0.0, 0.0)


def test_far_from_everything_is_decided_by_the_straight_line_alone():
    m = inp.gather(LAT, LNG, rings=RING, stations=stations_doc(near_name="none"))
    assert m["straight_m"] > 800 and m["walk"] is None
    r = dec.decide(m)
    assert r["lmr"]["answer"] in ("no", "cant_tell") and r["lmr"]["answer"] != "yes"


def test_a_nearby_station_gives_a_straight_distance_under_the_limit():
    m = inp.gather(LAT, LNG, rings=RING, stations=stations_doc())
    assert 250 < m["straight_m"] < 400  # the near station is 0.003 degrees (about 333 m) north


def test_walk_needs_a_surface_for_every_nearby_anchor():
    to_m = Transformer.from_crs(4326, 28356, always_xy=True).transform
    x, y = to_m(LNG, LAT)
    # a surface that covers the lot but belongs to a DIFFERENT anchor: Ashfield station (about 333 m away) has none built
    nodes = [[x - 100 + i * 5.0, y - 20, 300.0 + i * 5.0, 0] for i in range(300)]
    other = ws.Surface({"epsg": 28356, "built": "d", "osm_extract": "", "bbox_m": [x - 2000, y - 2000, x + 2000, y + 2000],
                        "anchors": [{"name": "Some other station", "entrance_id": "node/9"}], "nodes": nodes, "graph_nodes": 300}, "o")
    m = inp.gather(LAT, LNG, rings=RING, stations=stations_doc(), walk_surfaces=[other])
    assert m["straight_m"] < 800
    assert m["walk"]["valid"] is False and "Ashfield station" in m["walk"]["reason"]
    assert dec.decide(m)["lmr"]["answer"] != "yes"


def test_walk_is_accepted_when_the_nearby_anchor_has_a_surface():
    to_m = Transformer.from_crs(4326, 28356, always_xy=True).transform
    x, y = to_m(LNG, LAT)
    nodes = [[x - 100 + i * 5.0, y - 20, 300.0 + i * 5.0, 0] for i in range(300)]
    mine = ws.Surface({"epsg": 28356, "built": "d", "osm_extract": "", "bbox_m": [x - 2000, y - 2000, x + 2000, y + 2000],
                       "anchors": [{"name": "Ashfield station", "entrance_id": "station node", "no_mapped_entrance": True}],
                       "nodes": nodes, "graph_nodes": 300}, "m")
    m = inp.gather(LAT, LNG, rings=RING, stations=stations_doc(), walk_surfaces=[mine])
    assert m["walk"]["valid"] is True and m["walk"]["anchor"] == "Ashfield station"


def test_gather_reads_sydney_airports_chart_and_the_decision_uses_it():
    """End to end with the real projection: a lot on the runway is inside the 25 line and excluded; a lot in Parramatta is outside the chart's frame."""
    ring = [[151.1772, -33.9461], [151.1774, -33.9461], [151.1774, -33.9459], [151.1772, -33.9459], [151.1772, -33.9461]]
    m = inp.gather(-33.9460, 151.1773, rings=ring, stations=stations_doc(near_name="none"))
    assert m["sydney_anef"]["25"]["state"] == "inside"
    rules = [x for x in dec.decide(m)["lmr"]["rules"] if x["rule"] == "aircraft_noise_sydney"]
    assert rules and rules[0]["outcome"] == "excludes"
    far = inp.gather(-33.8148, 151.0017, rings=None, stations=stations_doc(near_name="none"))["sydney_anef"]
    assert far["25"]["state"] == "outside" and far["25"]["outside_frame"] is True


def test_a_ring_of_fewer_than_four_points_is_not_a_lot_outline():
    """gather() and the Sydney chart must agree on what counts as an outline: a one-point ring is neither."""
    m = inp.gather(-33.9460, 151.1773, rings=[[151.1773, -33.9460]], stations=stations_doc(near_name="none"))
    assert m["lot_outline"] is False
    assert dec.decide(m)["lmr"]["answer"] != "yes"
