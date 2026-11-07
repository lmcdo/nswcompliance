"""GET /pipeline/housing-sepp/area-check: the route's own behaviour (the rules are tested in tests/test_lmr_area_*.py).

What the route can get wrong: let a swapped or foreign coordinate through, hand the area check no flood function, or let a failing
flood function turn into a clear.
"""
import sys
import types

import pytest
from fastapi import HTTPException

from services import housing_sepp_gates_api as api


def _capture(monkeypatch):
    seen = {}

    def fake_area_check(lat, lng, **kw):
        seen.update(lat=lat, lng=lng, **kw)
        return {"pathway": "lmr", "headline": "x"}
    mod = types.ModuleType("services.lmr_area_inputs")
    mod.area_check = fake_area_check
    monkeypatch.setitem(sys.modules, "services.lmr_area_inputs", mod)
    return seen


def test_route_passes_the_point_and_a_flood_function_to_the_area_check(monkeypatch):
    seen = _capture(monkeypatch)
    out = api.housing_sepp_area_check(-33.889, 151.126)
    assert out == {"pathway": "lmr", "headline": "x"}
    assert (seen["lat"], seen["lng"]) == (-33.889, 151.126) and callable(seen["flood_fn"])


@pytest.mark.parametrize("lat,lng", [(0.0, 0.0), (151.126, -33.889), (-33.889, 10.0), (-27.0, 151.0), (-39.0, 151.0)])
def test_route_refuses_a_point_outside_nsw_before_any_query(monkeypatch, lat, lng):
    seen = _capture(monkeypatch)
    with pytest.raises(HTTPException) as e:
        api.housing_sepp_area_check(lat, lng)
    assert e.value.status_code == 422 and seen == {}


def test_flood_function_uses_the_existing_flood_answer_and_passes_the_lot(monkeypatch):
    calls = []
    mod = types.ModuleType("scripts.generate_conveyancing_report")
    mod.get_flood_planning_status = lambda lat, lng, wkt=None: calls.append((lat, lng, wkt)) or {"value": False}
    monkeypatch.setitem(sys.modules, "scripts.generate_conveyancing_report", mod)
    fn = api._flood_answer_for(-32.93, 151.78)
    assert fn("POLYGON((0 0,1 0,1 1,0 0))") == {"value": False}
    assert calls == [(-32.93, 151.78, "POLYGON((0 0,1 0,1 1,0 0))")]


def test_a_failing_or_missing_flood_answer_is_unknown_never_clear(monkeypatch):
    def boom(*a, **k):
        raise RuntimeError("database down")
    mod = types.ModuleType("scripts.generate_conveyancing_report")
    mod.get_flood_planning_status = boom
    monkeypatch.setitem(sys.modules, "scripts.generate_conveyancing_report", mod)
    assert api._flood_answer_for(-32.93, 151.78)(None)["value"] is None
    monkeypatch.setitem(sys.modules, "scripts.generate_conveyancing_report", None)      # import fails
    monkeypatch.setitem(sys.modules, "generate_conveyancing_report", None)
    assert api._flood_answer_for(-32.93, 151.78)(None)["value"] is None
