"""Tests for services/street_frontage.py: parity with the TypeScript module."""
import json
import sys
from pathlib import Path

import pytest

import services.street_frontage as sfm
from services.lot_dimensions import _scale_factor_for_ring
from services.street_frontage import (
    fetch_nearby_roads,
    measure_street_frontage,
    street_frontage_for_geometry,
    width_range,
    width_verdict,
)

FIX = Path(__file__).resolve().parent.parent / "frontend-nextjs" / "__tests__" / "fixtures" / "street-frontage"


def run(name):
    d = json.loads((FIX / f"{name}.json").read_text(encoding="utf-8"))
    return measure_street_frontage(d["lotRing"], d["roads"])


def road(sf, name):
    return next(r for r in sf.roads if r.road == name)


def test_winston_hills_wedge():
    sf = run("winston-hills-wedge")
    assert sf.status == "measured" and len(sf.roads) == 1
    r = road(sf, "BERRIGAN ST")
    assert r.frontage_m == pytest.approx(13.34, abs=0.1)
    assert r.min_front_half_m == pytest.approx(13.38, abs=0.2)
    assert r.max_all_m == pytest.approx(22.4, abs=0.3)
    assert width_verdict(sf, 12) == "meets"
    assert width_verdict(sf, 18) == "depends"


def test_padstow_gap():
    sf = run("padstow-gap")
    assert road(sf, "WYREEMA AVE").frontage_m == pytest.approx(15.27, abs=0.15)
    assert width_verdict(sf, 12) == "meets"
    assert width_verdict(sf, 18) == "below"


def test_mortdale_narrow():
    sf = run("mortdale-narrow")
    assert road(sf, "BROUGHTON ST").frontage_m == pytest.approx(6.19, abs=0.15)
    assert width_verdict(sf, 12) == "below"


def test_vaucluse_battleaxe():
    sf = run("vaucluse-battleaxe")
    assert road(sf, "HOPETOUN AVE").frontage_m == pytest.approx(5.99, abs=0.15)
    assert width_verdict(sf, 12) == "depends"


def test_haberfield_corner_lane():
    sf = run("haberfield-corner-lane")
    assert road(sf, "LOGAN AVE").frontage_m == pytest.approx(26.25, abs=0.2)
    assert road(sf, "NICHOLLS AVE").frontage_m == pytest.approx(46.14, abs=0.2)
    assert sf.unnamed_road_edge_m == pytest.approx(14, abs=0.5)
    for req in (6, 10, 12, 15, 20):
        each = [width_verdict(sfm.StreetFrontage("measured", [r]), req) for r in sf.roads]
        expected = each[0] if len(set(each)) == 1 else "depends"
        assert width_verdict(sf, req) == expected


# --- synthetic shapes -----------------------------------------------------------

Y0 = -3998985.0
SCALE = _scale_factor_for_ring([[0, Y0], [1, Y0], [1, Y0 + 1], [0, Y0 + 1], [0, Y0]])


def ring(pts):
    return [[x * SCALE, Y0 + y * SCALE] for x, y in [*pts, pts[0]]]


def rect(x0, y1, w, h):
    return ring([(x0, y1), (x0 + w, y1), (x0 + w, y1 + h), (x0, y1 + h)])


TEST_ST = {"name": "TEST ST", "rings": [ring([(-20, -10), (60, -10), (60, 0), (-20, 0)])]}


def test_rectangle_15x40():
    sf = measure_street_frontage(rect(0, 0, 15, 40), [{"name": "TEST ST", "rings": [rect(-20, -10, 55, 10)]}])
    r = sf.roads[0]
    assert 14.6 < r.frontage_m < 15.4
    assert r.min_front_half_m == pytest.approx(15, abs=0.4)
    assert [width_verdict(sf, v) for v in (12, 15, 20)] == ["meets", "depends", "below"]


def test_side_step_at_right_angle_is_not_frontage():
    lot = ring([(0, 0), (15, 0), (15, 4), (20, 4), (20, 40), (0, 40)])
    assert 14.6 < measure_street_frontage(lot, [TEST_ST]).roads[0].frontage_m < 15.4


def test_slanting_side_boundary_is_not_frontage():
    lot = ring([(0, 0), (15, 0), (40, 12), (40, 40), (0, 40)])
    assert 14.6 < measure_street_frontage(lot, [TEST_ST]).roads[0].frontage_m < 15.4


def test_edge_cases():
    sf = measure_street_frontage(None, [])
    assert sf.status == "unavailable" and width_verdict(sf, 12) == "depends" and width_range(sf) is None
    d = json.loads((FIX / "winston-hills-wedge.json").read_text(encoding="utf-8"))
    sf = measure_street_frontage(d["lotRing"], [])
    assert sf.status == "not_identified" and width_verdict(sf, 12) == "depends" and width_range(sf) is None
    assert width_range(None) is None
    wr = width_range(run("winston-hills-wedge"))
    assert wr is not None and wr[0] <= wr[1]


# --- fetch ------------------------------------------------------------------------

GEOM = {"rings": [rect(0, 0, 15, 40)]}


class _Resp:
    def __init__(self, payload=None, err=None):
        self.payload, self.err = payload, err

    def raise_for_status(self):
        if self.err:
            raise self.err

    def json(self):
        return self.payload


def _patch_get(monkeypatch, fn):
    monkeypatch.setattr(sys.modules["requests"], "get", fn, raising=False)


def test_fetch_success_builds_roads_and_envelope(monkeypatch):
    seen = {}

    def fake(url, params=None, timeout=None):
        seen.update(url=url, params=params, timeout=timeout)
        return _Resp({"features": [
            {"attributes": {"roadnamelabel": "TEST ST"}, "geometry": {"rings": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}},
            {"attributes": {"roadnamelabel": "NOGEOM"}, "geometry": None},
        ]})

    _patch_get(monkeypatch, fake)
    roads = fetch_nearby_roads(GEOM)
    assert roads == [{"name": "TEST ST", "rings": [[[0, 0], [1, 0], [1, 1], [0, 0]]]}]
    assert seen["timeout"] == 10 and seen["params"]["geometryType"] == "esriGeometryEnvelope"
    assert seen["params"]["inSR"] == 3857 and seen["params"]["outFields"] == "roadnamelabel"
    xmin = float(seen["params"]["geometry"].split(",")[0])
    assert xmin == pytest.approx(-20 * SCALE, rel=1e-4)


def test_fetch_http_error_is_none(monkeypatch):
    _patch_get(monkeypatch, lambda *a, **k: _Resp(err=RuntimeError("500")))
    assert fetch_nearby_roads(GEOM) is None
    assert street_frontage_for_geometry(GEOM).status == "unavailable"


def test_fetch_exception_and_arcgis_error_body_are_none(monkeypatch):
    def boom(*a, **k):
        raise TimeoutError("slow")

    _patch_get(monkeypatch, boom)
    assert fetch_nearby_roads(GEOM) is None
    _patch_get(monkeypatch, lambda *a, **k: _Resp({"error": {"code": 400}}))
    assert fetch_nearby_roads(GEOM) is None
    assert street_frontage_for_geometry(None).status == "unavailable"


def test_for_geometry_measures_when_fetch_succeeds(monkeypatch):
    monkeypatch.setattr(sfm, "fetch_nearby_roads", lambda g: [{"name": "TEST ST", "rings": [rect(-20, -10, 55, 10)]}])
    sf = street_frontage_for_geometry(GEOM)
    assert sf.status == "measured" and sf.roads[0].road == "TEST ST"


@pytest.mark.integration
def test_live_road_layer_finds_berrigan_st_for_the_winston_hills_wedge():
    """Real HTTP to the NSW road-corridor layer: the query still returns the road and its geometry.

    Run with `pytest -m integration`. Skips (never passes) when the layer is unreachable from this machine.
    """
    import importlib

    stub = sys.modules.pop("requests", None)  # conftest_mocks stubs requests; fetch_nearby_roads imports it inside
    try:
        try:
            importlib.import_module("requests")
        except ImportError:
            pytest.skip("real requests module not installed")
        fx = json.loads((FIX / "winston-hills-wedge.json").read_text(encoding="utf-8"))
        roads = fetch_nearby_roads({"rings": [fx["lotRing"]], "spatialReference": {"wkid": 3857}})
        if roads is None:
            pytest.skip("NSW road-corridor layer unreachable")
        sf = measure_street_frontage(fx["lotRing"], roads)
        assert [r.road for r in sf.roads] == ["BERRIGAN ST"]
        assert abs(sf.roads[0].frontage_m - 13.34) <= 0.1
    finally:
        if stub is not None:
            sys.modules["requests"] = stub
