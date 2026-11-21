"""Route map data (services/lmr_route_map.py) and its plumbing. Fake dicts only: no network, no database, no saved surface files."""
from __future__ import annotations

import re
import sys
import types

import pytest

from services import evidence_statement as es
from services import housing_sepp_gates_api as api
from services import lmr_area_decision as dec
from services import lmr_area_inputs as inp
from services import lmr_route_map as rm

E0, N0 = 330000.0, 6250000.0
ANCHOR = "Test station"


class _FakeTransformer:
    """A straight-line stand-in for pyproj (tests/conftest_mocks.py stubs pyproj with a transformer that returns (0, 0)).
    Metres near E0/N0 <-> degrees near Sydney; exact inverses of each other, which is all the module needs."""
    def __init__(self, forward):
        self.forward = forward

    @classmethod
    def from_crs(cls, src, dst, always_xy=True):
        return cls(forward=(int(src) == 28356))

    def transform(self, a, b):
        if self.forward:
            return 151.0 + (a - E0) / 90000.0, -33.0 + (b - N0) / 110000.0
        return E0 + (a - 151.0) * 90000.0, N0 + (b + 33.0) * 110000.0


@pytest.fixture(autouse=True)
def _straight_line_projection(monkeypatch):
    monkeypatch.setattr(rm, "Transformer", _FakeTransformer)


def _ll(x, y):
    lon, lat = _FakeTransformer(True).transform(x, y)
    return lat, lon


def _route(length=500.0, anchor=ANCHOR, points="default", entrance_id="node/1", end_gap=3.0):
    pts = [[E0 + 100, N0 + 100], [E0 + 200, N0 + 200]] if points == "default" else points
    return {"epsg": 28356, "lot_xy": [E0, N0], "points": pts, "length_m": length, "end_gap_m": end_gap, "anchor": anchor,
            "entrance_id": entrance_id, "busy_pts": [[E0 + 50, N0 + 50]], "osm_extract": "t"}


def _stations(dx=2.0, dy=0.0, with_station_point=True):
    elat, elon = _ll(E0 + 200 + dx, N0 + 200 + dy)
    st = {"name": ANCHOR, "entrances": [{"id": "node/1", "lat": elat, "lon": elon}]}
    if with_station_point:
        st.update(lat=elat, lon=elon)
    return {"stations": [st]}


def _walk(m=500.0, anchor=ANCHOR, valid=True, entrance_id="node/1"):
    return {"valid": valid, "m": m, "anchor": anchor, "entrance_id": entrance_id}   # the real walk record carries the entrance it ended at


def _m(careful=None, normal=None, careful_walk=None, normal_walk=None, normal_valid=True):
    m = {}
    if careful_walk is not None:
        m["walk_safe"] = {**careful_walk, "route": careful}
    if normal_walk is not None:
        m["walk"] = normal_walk
    if normal is not None:
        m["route_normal"] = {"valid": normal_valid, "route": normal}
    return m


def _strings(o):
    if isinstance(o, str):
        yield o
    elif isinstance(o, dict):
        for v in o.values():
            yield from _strings(v)
    elif isinstance(o, (list, tuple)):
        for v in o:
            yield from _strings(v)


# ---- A. build ---------------------------------------------------------------------------------------------
def test_careful_route_within_2m_of_the_walk_is_drawn_with_lot_first_and_entrance_last():
    out = rm.build(_m(careful=_route(501.5), careful_walk=_walk(500.0)), _stations())
    c = out["careful"]
    assert out["status"] == "ok" and c is not None
    lat0, lon0 = _ll(E0, N0)
    assert c["points"][0] == [round(lat0, 6), round(lon0, 6)]
    assert len(c["points"]) == 4                       # lot + 2 route points + appended entrance
    assert c["points"][-1] == [round(c["entrance"]["lat"], 6), round(c["entrance"]["lon"], 6)]
    for lat, lon in c["points"]:
        assert -38 < lat < -28 and 140 < lon < 154     # inside NSW, as [lat, lon]
    blat, blon = _ll(E0 + 50, N0 + 50)
    assert c["busy_road_points"] == [[round(blat, 6), round(blon, 6)]]


def test_careful_route_more_than_2m_off_the_walk_is_not_drawn_and_status_is_unavailable():
    out = rm.build(_m(careful=_route(503.0), careful_walk=_walk(500.0)), _stations())
    assert out["status"] == "unavailable"
    assert "503" in out["reason"] and "500" in out["reason"] and "agree" in out["reason"]
    assert "careful" not in out


def test_careful_route_off_by_more_than_2m_leaves_careful_none_when_normal_is_drawn():
    out = rm.build(_m(careful=_route(503.0), careful_walk=_walk(500.0), normal=_route(500.0), normal_walk=_walk(500.0)), _stations())
    assert out["status"] == "ok" and out["careful"] is None
    assert "503" in out["careful_note"] and "500" in out["careful_note"] and "agree" in out["careful_note"]


def test_normal_route_within_15m_is_drawn():
    out = rm.build(_m(normal=_route(514.0), normal_walk=_walk(500.0)), _stations())
    assert out["status"] == "ok" and out["normal"]["length_m"] == 514.0 and out["normal"]["walk_m"] == 500.0


def test_normal_route_16m_off_is_not_drawn_and_the_note_names_15m():
    out = rm.build(_m(normal=_route(516.0), normal_walk=_walk(500.0)), _stations())
    assert out["status"] == "unavailable" and "15 m" in out["reason"]


def test_normal_route_to_a_different_station_is_not_drawn():
    out = rm.build(_m(normal=_route(500.0, anchor="Other"), normal_walk=_walk(500.0)), _stations())
    assert out["status"] == "unavailable" and "different station" in out["reason"]


@pytest.mark.parametrize("walk", [None, _walk(valid=False), {"valid": True, "m": None, "anchor": ANCHOR}])
def test_a_walk_that_is_invalid_or_missing_means_no_route_with_a_plain_reason(walk):
    m = {"route_normal": {"valid": True, "route": _route()}, "walk_safe": {"valid": False, "route": _route()}}
    if walk is not None:
        m["walk"] = walk
    out = rm.build(m, _stations())
    assert out["status"] == "unavailable" and "not measured" in out["reason"]


def test_build_with_nothing_gathered_never_raises():
    assert rm.build({}, None)["status"] == "unavailable"
    assert rm.build({"walk": "x", "walk_safe": 5, "route_normal": []}, {})["status"] == "unavailable"


def test_a_route_without_pointers_is_not_drawn_and_says_the_map_holds_no_route_information():
    out = rm.build(_m(careful=_route(points=None), careful_walk=_walk()), _stations())
    assert out["status"] == "unavailable" and "no route information" in out["reason"]


def test_entrance_farther_than_end_gap_plus_5m_is_not_appended_but_is_still_reported():
    out = rm.build(_m(careful=_route(end_gap=3.0), careful_walk=_walk()), _stations(dx=9.0))   # 9 m > 3 + 5
    c = out["careful"]
    assert len(c["points"]) == 3                       # lot + 2 route points, no entrance appended
    assert c["entrance"]["exact"] is True and c["entrance"]["name"] == ANCHOR


def test_entrance_just_inside_end_gap_plus_5m_is_appended():
    out = rm.build(_m(careful=_route(end_gap=3.0), careful_walk=_walk()), _stations(dx=7.0))
    assert len(out["careful"]["points"]) == 4


def test_unknown_entrance_id_falls_back_to_the_station_point_and_is_marked_not_exact():
    out = rm.build(_m(careful=_route(entrance_id="node/999"), careful_walk=_walk(entrance_id="node/999")), _stations())
    assert out["careful"]["entrance"]["exact"] is False and out["careful"]["entrance"]["name"] == ANCHOR


def test_entrance_is_none_when_nothing_matches():
    out = rm.build(_m(careful=_route(entrance_id="node/999"), careful_walk=_walk(entrance_id="node/999")), _stations(with_station_point=False))
    assert out["careful"]["entrance"] is None and out["entrance"] is None and len(out["careful"]["points"]) == 3
    out2 = rm.build(_m(careful=_route(), careful_walk=_walk()), None)
    assert out2["careful"]["entrance"] is None


def test_both_routes_drawn_gives_ok_and_the_lot_is_the_careful_routes_first_point():
    out = rm.build(_m(careful=_route(500.0), careful_walk=_walk(500.0), normal=_route(505.0), normal_walk=_walk(500.0)), _stations())
    assert out["status"] == "ok" and out["careful"] and out["normal"]
    assert [out["lot"]["lat"], out["lot"]["lon"]] == out["careful"]["points"][0]


def test_no_returned_note_uses_the_word_safe():
    cases = [
        rm.build(_m(careful=_route(500.0), careful_walk=_walk(500.0), normal=_route(505.0), normal_walk=_walk(500.0)), _stations()),
        rm.build(_m(careful=_route(503.0), careful_walk=_walk(500.0), normal=_route(520.0, anchor="X"), normal_walk=_walk(500.0)), _stations()),
        rm.build(_m(careful=_route(points=None), careful_walk=_walk(valid=False), normal=_route(), normal_walk=None), _stations()),
        rm.build(_m(normal=_route(), normal_walk=_walk(), normal_valid=False), _stations()),
        rm.build({}, None),
    ]
    for out in cases:
        text = " ".join(_strings(out))
        assert text and not re.search(r"\bsafe(ly)?\b", text, re.I), text


# ---- B. area_check plumbing -------------------------------------------------------------------------------
def _gathered():
    m = {"lga": "Penrith", "tod_map": {"point": False, "lot": False}, "accelerated": {"point": False, "lot": False},
         "exclusion": {"point": False, "lot": False}, "bushfire": {"point": False, "lot": False},
         "heritage": {"item": False}, "sched12_straight_m": 99999.0, "straight_m": 300.0}  # noqa: regulatory-number -- test fixture
    m.update(_m(careful=_route(500.0), careful_walk=_walk(500.0), normal=_route(505.0), normal_walk=_walk(500.0)))
    return m


def _fake_gather(monkeypatch):
    calls = []

    def g(lat, lng, **kw):
        calls.append(kw)
        return _gathered()
    monkeypatch.setattr(inp, "gather", g)
    return calls


def test_area_check_with_want_route_adds_a_route_map(monkeypatch):
    calls = _fake_gather(monkeypatch)
    r = inp.area_check(-33.8, 150.7, want_route=True, stations=_stations())
    assert r["route_map"]["status"] == "ok" and r["route_map"]["careful"] and r["route_map"]["normal"]
    assert calls[0].get("want_route") is True and r.get("headline")


def test_area_check_without_want_route_has_no_route_map_key_and_gather_gets_no_want_route(monkeypatch):
    calls = _fake_gather(monkeypatch)
    r = inp.area_check(-33.8, 150.7)
    assert "route_map" not in r and "want_route" not in calls[0]


def test_a_failing_route_map_build_keeps_the_decision_and_reports_unavailable(monkeypatch):
    _fake_gather(monkeypatch)
    plain = inp.area_check(-33.8, 150.7)

    def boom(m, stations=None):
        raise ValueError("bad")
    monkeypatch.setattr(rm, "build", boom)
    r = inp.area_check(-33.8, 150.7, want_route=True, stations=_stations())
    assert r["route_map"]["status"] == "unavailable" and r["route_map"]["reason"]
    assert {k: v for k, v in r.items() if k != "route_map"} == plain


# ---- C. the two endpoints ---------------------------------------------------------------------------------
def _patch_area_check(monkeypatch):
    seen = {}

    def fake_area_check(lat, lng, **kw):
        seen.update(kw)
        return {"pathway": "lmr", "headline": "x", "measured": {"lga": "Penrith"}}
    mod = types.ModuleType("services.lmr_area_inputs")
    mod.area_check = fake_area_check
    monkeypatch.setitem(sys.modules, "services.lmr_area_inputs", mod)
    return seen


def test_area_check_endpoint_passes_no_want_route(monkeypatch):
    seen = _patch_area_check(monkeypatch)
    api.housing_sepp_area_check(-33.889, 151.126)
    assert seen and "want_route" not in seen


def test_evidence_endpoint_passes_want_route_true(monkeypatch):
    from services import evidence_council, evidence_statement
    seen = _patch_area_check(monkeypatch)
    monkeypatch.setattr(evidence_council, "council_controls", lambda lga: {"status": "ok"})
    monkeypatch.setattr(evidence_council, "council_files", lambda lga: {"status": "ok"})
    got = {}
    monkeypatch.setattr(evidence_statement, "build", lambda area, controls, files, *a, **k: got.update(area=area) or {"built": True})
    assert api.housing_sepp_evidence(-33.889, 151.126) == {"built": True}
    assert seen.get("want_route") is True and got["area"]["pathway"] == "lmr"


# ---- D. evidence_statement.build ---------------------------------------------------------------------------
def test_evidence_carries_the_route_map_and_none_when_the_area_has_none():
    facts = dec.LawFacts.load()
    area = dec.decide(_gathered(), facts)
    rmap = {"status": "ok", "marker": 1}
    assert es.build({**area, "route_map": rmap}, {}, {}, facts)["route_map"] == rmap
    assert es.build(area, {}, {}, facts)["route_map"] is None


# --- what the walk ends at: an entrance, a station outline, or the edge of a town centre ---

@pytest.mark.parametrize("entrance_id,kind", [("node/1", "entrance"), ("town centre edge", "town_centre_edge"),
                                              ("station outline (entrance not mapped)", "station_outline")])
def test_the_destination_says_what_the_walk_ends_at(entrance_id, kind):
    out = rm.build(_m(careful=_route(entrance_id=entrance_id), careful_walk=_walk(entrance_id=entrance_id)), _stations())
    assert out["status"] == "ok"
    assert out["destination"] == {"name": ANCHOR, "kind": kind} and out["careful"]["destination"] == {"name": ANCHOR, "kind": kind}


def test_a_town_centre_edge_has_no_entrance_but_the_route_still_ends_at_its_last_point():
    out = rm.build(_m(careful=_route(entrance_id="town centre edge", end_gap=0.0), careful_walk=_walk(entrance_id="town centre edge")), _stations())
    assert out["careful"]["entrance"] is None
    assert out["careful"]["points"][-1] == [round(v, 6) for v in _ll(E0 + 200, N0 + 200)]      # not extended to anywhere else (the module rounds to 6 places)


def test_the_destination_of_the_page_is_the_careful_routes_when_both_are_drawn():
    out = rm.build(_m(careful=_route(entrance_id="node/1"), normal=_route(entrance_id="town centre edge"),
                      careful_walk=_walk(), normal_walk=_walk(entrance_id="town centre edge")), _stations())
    assert out["destination"]["kind"] == "entrance" and out["normal"]["destination"]["kind"] == "town_centre_edge"


# --- the two walks can end at different places; the note says where each line comes from ---

def test_destinations_differ_when_the_two_walks_end_at_different_places():
    out = rm.build(_m(careful=_route(anchor=ANCHOR), normal=_route(anchor="Other station"),
                      careful_walk=_walk(anchor=ANCHOR), normal_walk=_walk(anchor="Other station")), _stations())
    assert out["status"] == "ok" and out["careful"] and out["normal"]
    assert out["destinations_differ"] is True
    assert out["careful"]["destination"]["name"] == ANCHOR and out["normal"]["destination"]["name"] == "Other station"


def test_destinations_do_not_differ_when_both_walks_end_at_the_same_place():
    out = rm.build(_m(careful=_route(), normal=_route(), careful_walk=_walk(), normal_walk=_walk()), _stations())
    assert out["destinations_differ"] is False


def test_with_one_route_drawn_the_destinations_do_not_differ():
    out = rm.build(_m(careful=_route(), careful_walk=_walk()), _stations())
    assert out["status"] == "ok" and out["destinations_differ"] is False


def test_the_note_says_where_each_line_comes_from_and_does_not_claim_one_source_for_both():
    note = rm.NOTE
    assert "crossings-only line is drawn from the same saved footpath data as its walking distance" in note
    assert "normal line is drawn from a separate copy" in note and f"{rm.NORMAL_AGREE_M:.0f} m" in note
    assert "same saved footpath data as the walking distances" not in note
    out = rm.build(_m(careful=_route(), careful_walk=_walk()), _stations())
    assert out["note"] == note


# --- a line that stops short of the station says by how much ---

def test_the_station_link_is_drawn_when_the_entrance_is_where_the_link_says_and_nothing_is_reported_missing():
    out = rm.build(_m(careful=_route(end_gap=3.0), careful_walk=_walk()), _stations(dx=2.0))
    assert out["careful"]["end_link_not_drawn_m"] == 0.0


def test_a_link_that_cannot_be_drawn_is_reported_with_its_length():
    # the entrance is 60 m from the last stored point but the walk says the link is only 20 m: it is not drawn, and 20 m of the walk is unexplained
    out = rm.build(_m(careful=_route(end_gap=20.0), careful_walk=_walk()), _stations(dx=60.0))
    assert out["careful"]["end_link_not_drawn_m"] == 20.0
    # and the line really does stop at its last stored point
    assert out["careful"]["points"][-1] == [round(v, 6) for v in _ll(E0 + 200, N0 + 200)]


def test_an_unknown_entrance_with_a_real_link_is_reported_not_silently_shortened():
    out = rm.build(_m(careful=_route(end_gap=35.0, entrance_id="node/999"), careful_walk=_walk(entrance_id="node/999")), {"stations": []})
    assert out["careful"]["entrance"] is None and out["careful"]["end_link_not_drawn_m"] == 35.0


def test_a_zero_length_link_reports_nothing_missing_even_with_no_entrance():
    out = rm.build(_m(careful=_route(end_gap=0.0, entrance_id="town centre edge"), careful_walk=_walk(entrance_id="town centre edge")), _stations())
    assert out["careful"]["end_link_not_drawn_m"] == 0.0


# --- the same ENTRANCE, not only the same station name; a link counts as drawn only if its length matches ---

def test_a_normal_route_to_a_different_entrance_of_the_same_station_is_not_drawn():
    out = rm.build(_m(careful=_route(), normal=_route(entrance_id="node/2"), careful_walk=_walk(), normal_walk=_walk(entrance_id="node/1")), _stations())
    assert out["normal"] is None and "different station or entrance" in out["normal_note"]
    assert out["status"] == "ok" and out["careful"]          # the crossings-only route is unaffected


def test_two_walks_to_different_entrances_of_one_station_are_different_ends():
    out = rm.build(_m(careful=_route(entrance_id="node/1"), normal=_route(entrance_id="node/2"),
                      careful_walk=_walk(entrance_id="node/1"), normal_walk=_walk(entrance_id="node/2")), _stations())
    assert out["careful"] and out["normal"] and out["destinations_differ"] is True
    assert out["careful"]["destination"] == out["normal"]["destination"]     # same name and kind: only the entrance id tells them apart


def test_an_entrance_much_nearer_than_the_link_says_is_not_used_to_draw_a_shorter_link():
    # the walk counts a 30 m link, but this entrance is 2 m from the last stored point: drawing 2 m would show a walk 28 m short
    out = rm.build(_m(careful=_route(end_gap=30.0), careful_walk=_walk()), _stations(dx=2.0))
    assert out["careful"]["end_link_not_drawn_m"] == 30.0
    assert out["careful"]["points"][-1] == [round(v, 6) for v in _ll(E0 + 200, N0 + 200)]
