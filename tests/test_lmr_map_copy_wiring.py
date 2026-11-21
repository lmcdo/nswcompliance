"""The area check uses our saved map copy only when it is proven, fresh and not near an edge; any doubt asks the live map, as before."""
from __future__ import annotations

import pytest

from services import lmr_area_decision as dec
from services import lmr_area_inputs as inp

RING = [[151.0, -33.0], [151.001, -33.0], [151.001, -32.999], [151.0, -32.999], [151.0, -33.0]]


@pytest.fixture
def live(monkeypatch):
    calls = []

    def fake(url, params, post=False, **kw):
        calls.append(url)
        return {"features": []}
    monkeypatch.setattr(inp, "_get_json", fake)
    return calls


def _good(point=False, lot=False, edge=False):
    return lambda key, lat, lng, rings: {"point": point, "lot": lot, "as_of": "2026-11-18", "near_edge": edge}


def test_a_proven_copy_answer_is_used_and_the_live_map_is_not_asked(live):
    out = inp._layer("tod_map", -33.0, 151.0, RING, _good(True, True))
    assert out["point"] is True and out["lot"] is True and out["copy_as_of"] == "2026-11-18" and live == []


def test_a_point_near_an_edge_asks_the_live_map(live):
    out = inp._layer("tod_map", -33.0, 151.0, RING, _good(edge=True))
    assert "copy_as_of" not in out and len(live) == 2   # point query and lot query


@pytest.mark.parametrize("fn", [None, lambda *a: None, lambda *a: (_ for _ in ()).throw(RuntimeError("x")),
                                lambda *a: {"point": None, "lot": False, "near_edge": False},
                                lambda *a: {"point": False, "lot": False}])
def test_no_answer_a_failure_or_a_half_answer_asks_the_live_map(live, fn):
    out = inp._layer("tod_map", -33.0, 151.0, RING, fn)
    assert "copy_as_of" not in out and len(live) == 2


@pytest.mark.parametrize("as_of", [None, "", "yesterday", 20261118, "2026-11-18T00:00"])
def test_a_copy_answer_without_a_readable_date_asks_the_live_map(live, as_of):
    out = inp._layer("tod_map", -33.0, 151.0, RING, lambda *a: {"point": False, "lot": False, "near_edge": False, "as_of": as_of})
    assert "copy_as_of" not in out and len(live) == 2


def test_the_endpoint_hands_the_copy_to_the_area_check(monkeypatch):
    from services import housing_sepp_gates_api as api
    seen = {}

    def fake_area_check(lat, lng, **kw):
        seen.update(kw)
        return {}
    monkeypatch.setattr(inp, "area_check", fake_area_check)
    api.housing_sepp_area_check(-33.75, 150.70)
    assert callable(seen.get("copy_fn"))


def test_the_area_check_passes_the_copy_down_to_the_layers(monkeypatch):
    got = {}
    monkeypatch.setattr(inp, "fetch_layers", lambda lat, lng, rings, lga_fallback=None, lga_guess=None, bushfire_fn=None, copy_fn=None: got.update(copy_fn=copy_fn) or {})
    marker = object()
    inp.area_check(-33.75, 150.70, copy_fn=marker)
    assert got.get("copy_fn") is marker


def test_a_copy_that_could_not_test_the_lot_outline_asks_the_live_map(live):
    out = inp._layer("tod_map", -33.0, 151.0, RING, lambda *a: {"point": False, "lot": None, "as_of": "x", "near_edge": False})
    assert "copy_as_of" not in out and len(live) == 2


def test_without_a_lot_outline_a_point_answer_is_enough_and_lot_stays_none(live):
    out = inp._layer("tod_map", -33.0, 151.0, None, lambda *a: {"point": False, "lot": None, "as_of": "2026-11-18", "near_edge": False})
    assert out == {"point": False, "lot": None, "copy_as_of": "2026-11-18"} and live == []


def test_layers_the_copy_does_not_hold_always_go_live(live):
    for key in ("bushfire", "airport_noise", "heritage_shr", "coastal_wetlands"):
        inp._layer(key, -33.0, 151.0, RING, _good())
    assert len(live) == 8   # 4 layers x (point + lot)


def test_a_clear_from_the_copy_is_a_clear_never_a_yes():
    m = {"lga": "Penrith", "tod_map": {"point": False, "lot": False, "copy_as_of": "2026-11-18"}, "map_copy": {"tod_map": "2026-11-18"}}
    assert dec.layer_state(m["tod_map"]) == "clear"
    r = dec.decide({**m, "accelerated": {"point": False, "lot": False}, "exclusion": {"point": False, "lot": False}})
    assert any("read from our own copy" in n and "2026-11-18" in n for n in r["notes"])


def test_the_note_is_absent_when_nothing_came_from_the_copy():
    r = dec.decide({"lga": "Penrith", "tod_map": {"point": False, "lot": False}})
    assert not any("our own copy (read on" in n for n in r["notes"])
