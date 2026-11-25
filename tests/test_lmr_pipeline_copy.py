"""Gas pipelines from our own saved copy: the reader (MapCopy.pipeline), the checks on its answer (_pipeline_from_copy) and the wiring in gather()."""
from __future__ import annotations

import gzip
import hashlib
import json
import math
from datetime import date
from pathlib import Path

import pytest

from services import lmr_area_inputs as inp
from services import lmr_map_copy as mc

TODAY = date(2026, 11, 26)
LAT, LNG = -33.0, 151.0
MX, MY = 111320.0 * math.cos(math.radians(LAT)), 110540.0   # the flat metres-per-degree scale the code documents


def east(m: float, name: str = "East Line", half: float = 0.01) -> dict:
    """A north-south LineString m metres due east of the point."""
    x = LNG + m / MX
    return {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[x, LAT - half], [x, LAT + half]]}, "properties": {"feature_name": name}}


def north(m: float, name: str = "North Line", half: float = 0.01) -> dict:
    """An east-west MultiLineString m metres due north of the point."""
    y = LAT + m / MY
    return {"type": "Feature", "geometry": {"type": "MultiLineString", "coordinates": [[[LNG - half, y], [LNG + half, y]]]}, "properties": {"feature_name": name}}


def _write(tmp: Path, features: list, read_on: str = "2026-11-26", name: str = "gas_pipelines", count=None, bad_hash: bool = False) -> Path:
    raw = gzip.compress(json.dumps({"type": "FeatureCollection", "features": features}).encode())
    (tmp / f"{name}.geojson.gz").write_bytes(raw)
    sha = "0" * 64 if bad_hash else hashlib.sha256(raw).hexdigest()
    (tmp / "manifest.json").write_text(json.dumps({"read_on": "2026-11-18", "layers": {name: {
        "read_on": read_on, "features": len(features) if count is None else count, "files": [{"file": f"{name}.geojson.gz", "sha256": sha}]}}}))
    return tmp


def _copy(tmp_path, features, **kw):
    return mc.MapCopy(_write(tmp_path, features, **kw))


def _sub(tmp_path, name):
    d = tmp_path / name
    d.mkdir()
    return d


def _pl(c, metres=200, rings=None, lat=LAT, lng=LNG):
    return c.pipeline(lat, lng, rings, metres, today=TODAY)


def _box(west_m, east_m, half_m=20):
    """A lot outline from west_m to east_m east of the point (metres), 2*half_m tall."""
    w, e, h = LNG + west_m / MX, LNG + east_m / MX, half_m / MY
    return [[w, LAT - h], [e, LAT - h], [e, LAT + h], [w, LAT + h], [w, LAT - h]]


# ---- (A) MapCopy.pipeline ---------------------------------------------------------------------------------
def test_hit_true_inside_the_distance_and_false_outside_with_names(tmp_path):
    out = _pl(_copy(tmp_path, [east(150, "Near"), east(400, "Far")]))
    assert out["hit"] is True and out["names"] == ["Near"] and out["as_of"] == "2026-11-26"
    assert out["nearest_m"] == 150 and out["nearest_name"] == "Near"
    out2 = _pl(_copy(_sub(tmp_path, "b"), [east(260, "A"), east(400, "B")]))
    assert out2["hit"] is False and out2["names"] == [] and out2["nearest_m"] == 260 and out2["nearest_name"] == "A"


def test_names_lists_every_pipeline_within_the_distance_not_just_the_nearest(tmp_path):
    out = _pl(_copy(tmp_path, [east(150, "One"), north(100, "Two"), east(500, "Three")]))
    assert sorted(out["names"]) == ["One", "Two"] and out["nearest_name"] == "Two" and out["nearest_m"] == 100


def test_the_threshold_moves_with_the_metres_argument(tmp_path):
    c = _copy(tmp_path, [east(150)])
    assert _pl(c, metres=100)["hit"] is False
    assert _pl(c, metres=300)["hit"] is True


def test_a_lot_outline_within_the_distance_is_a_hit_even_when_the_point_is_farther(tmp_path):
    c = _copy(tmp_path, [east(300, "Edge")])
    with_lot = _pl(c, metres=100, rings=_box(0, 250))     # the lot reaches 50 m short of the pipeline
    assert with_lot["hit"] is True and with_lot["names"] == ["Edge"]
    assert with_lot["nearest_m"] == 300                   # nearest is from the POINT, not the outline
    point_only = _pl(c, metres=100)
    assert point_only["hit"] is False and point_only["names"] == []


def test_a_lot_outline_far_from_the_pipeline_is_not_a_hit_even_if_the_point_is_close(tmp_path):
    c = _copy(tmp_path, [east(60)])
    out = _pl(c, metres=100, rings=_box(-500, -400))      # the lot is west; the point is 60 m from the line
    assert out["hit"] is False and out["names"] == []


def test_a_degenerate_outline_falls_back_to_the_point(tmp_path):
    c = _copy(tmp_path, [east(150, "Near")])
    assert _pl(c, rings=[[LNG, LAT]] * 4)["hit"] is True      # repairs to nothing: the point is used
    assert _pl(c, rings=[[LNG, LAT]])["hit"] is True          # fewer than 4 points: not an outline


def test_nearest_is_whole_metres_from_the_point(tmp_path):
    out = _pl(_copy(tmp_path, [east(1234.4)]))
    assert out["nearest_m"] == 1234 and isinstance(out["nearest_m"], int)
    assert _pl(_copy(_sub(tmp_path, "b"), [east(1234.6)]))["nearest_m"] == 1235


def test_nearest_none_when_the_only_pipeline_is_beyond_sixty_km(tmp_path):
    outside_box = _pl(_copy(tmp_path, [east(75000)]))
    assert outside_box["nearest_m"] is None and outside_box["nearest_name"] is None and outside_box["searched_m"] == 60000
    assert outside_box["hit"] is False and outside_box["names"] == [] and outside_box["near_edge"] is False
    in_box_past_60 = _pl(_copy(_sub(tmp_path, "b"), [east(61000)]))   # inside the search box, still more than 60 km
    assert in_box_past_60["nearest_m"] is None and in_box_past_60["searched_m"] == 60000
    within = _pl(_copy(_sub(tmp_path, "c"), [east(59000, "Just in")]))
    assert within["nearest_m"] == 59000 and within["nearest_name"] == "Just in"


@pytest.mark.parametrize("d,edge", [(198, True), (203, True), (150, False), (260, False), (196, True), (207, False)])
def test_near_edge_flags_a_pipeline_within_5_m_of_the_distance(tmp_path, d, edge):
    out = _pl(_copy(tmp_path, [east(d)]), metres=200)
    assert out["near_edge"] is edge
    assert out["hit"] is (d <= 200)


def test_near_edge_is_measured_from_the_lot_outline_when_there_is_one(tmp_path):
    c = _copy(tmp_path, [east(300)])
    assert _pl(c, metres=100, rings=_box(0, 198))["near_edge"] is True    # 102 m from the lot, distance 100: within 5 m
    assert _pl(c, metres=100, rings=_box(0, 150))["near_edge"] is False   # 150 m from the lot


def test_layer_too_old_gives_no_answer_and_the_age_limit_is_45_days(tmp_path):
    assert _pl(_copy(tmp_path, [east(150)], read_on="2026-10-01")) is None                              # 56 days
    assert _pl(_copy(_sub(tmp_path, "b"), [east(150)], read_on="2026-10-12")) is not None               # exactly 45 days


def test_layer_missing_from_the_manifest_or_hash_wrong_gives_no_answer(tmp_path):
    assert _pl(_copy(tmp_path, [east(150)], name="tod_sites")) is None
    assert _pl(_copy(_sub(tmp_path, "h"), [east(150)], bad_hash=True)) is None


def test_wrong_feature_count_gives_no_answer(tmp_path):
    assert _pl(_copy(tmp_path, [east(150)], count=2)) is None


def test_a_feature_with_empty_geometry_makes_the_layer_incomplete_so_no_answer(tmp_path):
    ghost = {"type": "Feature", "geometry": None, "properties": {"feature_name": "Ghost"}}
    assert _pl(_copy(tmp_path, [east(150), ghost])) is None
    ghost2 = {"type": "Feature", "geometry": {"type": "LineString", "coordinates": []}, "properties": {"feature_name": "Ghost"}}
    assert _pl(_copy(_sub(tmp_path, "e"), [east(150), ghost2])) is None


@pytest.mark.parametrize("bad", [0, -5, float("nan"), float("inf"), True, False, None, "200"])
def test_bad_distance_gives_no_answer(tmp_path, bad):
    assert _pl(_copy(tmp_path, [east(150)]), metres=bad) is None


def test_east_west_and_north_south_are_the_same_metres(tmp_path):
    e = _pl(_copy(tmp_path, [east(150)]))
    n = _pl(_copy(_sub(tmp_path, "n"), [north(150)]))
    assert e["nearest_m"] == n["nearest_m"] == 150
    assert e["hit"] is True and n["hit"] is True
    lat2 = -34.5   # and the scale holds at another latitude (a degree of longitude is shorter there)
    x = LNG + 150 / (111320.0 * math.cos(math.radians(lat2)))
    feat = {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[x, lat2 - 0.01], [x, lat2 + 0.01]]}, "properties": {"feature_name": "L"}}
    assert _pl(_copy(_sub(tmp_path, "l"), [feat]), lat=lat2)["nearest_m"] == 150


def test_the_pipeline_layer_keeps_line_features_as_lines(tmp_path):
    lay = _copy(tmp_path, [east(150), north(150)]).layer("gas_pipelines", TODAY)
    assert lay is not None and lay.skipped == 0 and sorted(g.geom_type for g in lay.geoms) == ["LineString", "MultiLineString"]


# ---- (B) _pipeline_from_copy ------------------------------------------------------------------------------
def _good(**over):
    base = {"hit": False, "names": [], "nearest_m": 1234.4, "nearest_name": "P", "searched_m": 60000, "near_edge": False, "as_of": "2026-11-26"}
    base.update(over)
    return base


def _from(fn):
    return inp._pipeline_from_copy(fn, LAT, LNG, None, 200.0)


def _raises(*a):
    raise RuntimeError("boom")


@pytest.mark.parametrize("fn", [
    None,
    _raises,
    lambda *a: None,
    lambda *a: "text",
    lambda *a: _good(near_edge=True),
    lambda *a: _good(near_edge=None),
    lambda *a: {k: v for k, v in _good().items() if k != "near_edge"},
    lambda *a: _good(hit=None),
    lambda *a: _good(hit=1),
    lambda *a: _good(names="P"),
    lambda *a: _good(names=None),
    lambda *a: _good(names=["ok", 5]),
    lambda *a: _good(nearest_m=-1),
    lambda *a: _good(nearest_m=True),
    lambda *a: _good(nearest_m="12"),
    lambda *a: {k: v for k, v in _good().items() if k != "as_of"},
    lambda *a: _good(as_of=None),
    lambda *a: _good(as_of="26/11/2026"),
    lambda *a: _good(as_of="2026-11-26T00:00"),
])
def test_bad_copy_answers_are_not_used(fn):
    assert _from(fn) is None


def test_good_copy_answer_with_a_nearest_distance():
    out = _from(lambda *a: _good(hit=True, names=["A", None]))
    assert out == {"hit": True, "names": ["A", None], "copy_as_of": "2026-11-26", "nearest_m": 1234, "nearest_name": "P"}
    assert isinstance(out["nearest_m"], int)
    assert _from(lambda *a: _good(nearest_m=0))["nearest_m"] == 0


def test_good_copy_answer_with_no_pipeline_within_the_search():
    out = _from(lambda *a: _good(nearest_m=None, nearest_name=None))
    assert out == {"hit": False, "names": [], "copy_as_of": "2026-11-26", "nearest_m": None, "searched_m": 60000}


def test_the_reader_is_called_with_the_lot_and_the_distance():
    seen = []
    inp._pipeline_from_copy(lambda *a: seen.append(a) or _good(), LAT, LNG, [[1, 2]], 321.0)
    assert seen == [(LAT, LNG, [[1, 2]], 321.0)]


# ---- (C) gather wiring ------------------------------------------------------------------------------------
RING = [[LNG, LAT], [LNG + 0.0002, LAT], [LNG + 0.0002, LAT + 0.0002], [LNG, LAT + 0.0002], [LNG, LAT]]


def _gather(monkeypatch, pipeline_fn, want_distances, live_near=None, live_nearest=None):
    monkeypatch.setattr(inp, "town_centre_polygons", lambda *a, **k: [])
    calls = {"near": 0, "nearest": 0}

    def near(*a):
        calls["near"] += 1
        if live_near is None:
            raise AssertionError("live _pipeline_near must not be called")
        return live_near

    def nearest(*a):
        calls["nearest"] += 1
        if live_nearest is None:
            raise AssertionError("live _pipeline_nearest must not be called")
        return live_nearest

    monkeypatch.setattr(inp, "_pipeline_near", near)
    monkeypatch.setattr(inp, "_pipeline_nearest", nearest)
    m = inp.gather(LAT, LNG, rings=RING, stations={}, layers={"lga": "X", "sydney_anef": {"x": 1}}, pipeline_fn=pipeline_fn, want_distances=want_distances)
    return m["pipeline"], calls


def test_gather_public_check_gets_the_copy_answer_without_distances_and_without_live_calls(monkeypatch):
    seen = []
    pl, calls = _gather(monkeypatch, lambda la, lo, r, metres: seen.append((r, metres)) or _good(hit=True, names=["P1"]), False)
    assert pl == {"hit": True, "names": ["P1"], "copy_as_of": "2026-11-26"}
    for k in ("nearest_m", "nearest_name", "searched_m"):
        assert k not in pl
    assert calls == {"near": 0, "nearest": 0}
    assert seen == [(RING, 200.0)]                    # the law's distance, the lot outline


def test_gather_evidence_gets_distances_from_the_copy_and_does_not_call_the_live_service(monkeypatch):
    pl, calls = _gather(monkeypatch, lambda *a: _good(), True)
    assert pl == {"hit": False, "names": [], "copy_as_of": "2026-11-26", "nearest_m": 1234, "nearest_name": "P"}
    assert calls == {"near": 0, "nearest": 0}
    none_found, calls2 = _gather(monkeypatch, lambda *a: _good(nearest_m=None, nearest_name=None), True)
    assert none_found["nearest_m"] is None and none_found["searched_m"] == 60000 and calls2 == {"near": 0, "nearest": 0}


def test_gather_evidence_with_a_copy_hit_keeps_the_copy_distance(monkeypatch):
    pl, calls = _gather(monkeypatch, lambda *a: _good(hit=True, names=["P"], nearest_m=80.0), True)
    assert pl["hit"] is True and pl["nearest_m"] == 80 and calls == {"near": 0, "nearest": 0}


def test_gather_falls_back_to_the_live_service_exactly_as_before_when_the_copy_gives_none(monkeypatch):
    live = {"hit": False, "names": []}
    pl, calls = _gather(monkeypatch, lambda *a: None, False, live_near=live)
    assert pl == live and calls == {"near": 1, "nearest": 0}
    pl2, calls2 = _gather(monkeypatch, lambda *a: None, True, live_near=live, live_nearest={"nearest_m": 777, "nearest_name": "L"})
    assert pl2 == {"hit": False, "names": [], "nearest_m": 777, "nearest_name": "L"} and calls2 == {"near": 1, "nearest": 1}
    pl3, calls3 = _gather(monkeypatch, None, False, live_near=live)         # no copy reader at all
    assert pl3 == live and calls3 == {"near": 1, "nearest": 0}


def test_gather_uses_the_live_service_when_the_copy_says_near_edge(monkeypatch):
    live = {"hit": True, "names": ["Live"]}
    pl, calls = _gather(monkeypatch, lambda *a: _good(near_edge=True, hit=False), True, live_near=live)
    assert pl == live and "copy_as_of" not in pl and calls == {"near": 1, "nearest": 0}


# ---- (D) the real committed layer -------------------------------------------------------------------------
def test_real_layer_nearest_pipeline_for_a_known_point():
    """Measured 2026-11-26 from data/law/maps/gas_pipelines.geojson.gz (14294 m, re-checked by a brute-force distance over every feature; the brief said 9333, which this file does not give). If that layer is refreshed these two numbers must be re-measured and updated here."""
    out = mc.MapCopy(mc.MAPS_DIR).pipeline(-33.7587, 150.7004, None, 200, today=date(2026, 11, 26))
    assert out is not None and out["as_of"] == "2026-11-25"
    assert out["nearest_m"] == 14294 and out["nearest_name"] == "Sydney to Newcastle Pipeline"
    assert out["hit"] is False and out["names"] == [] and out["near_edge"] is False


def test_real_manifest_entry_has_its_own_read_on_and_the_file_matches_its_hash():
    man = json.loads((mc.MAPS_DIR / "manifest.json").read_text(encoding="utf-8"))
    meta = man["layers"]["gas_pipelines"]
    assert meta["read_on"] and meta["read_on"] != man.get("read_on")
    date.fromisoformat(meta["read_on"])
    f = meta["files"][0]
    assert hashlib.sha256((mc.MAPS_DIR / f["file"]).read_bytes()).hexdigest() == f["sha256"]
    lay = mc.MapCopy(mc.MAPS_DIR).layer("gas_pipelines", date.fromisoformat(meta["read_on"]))
    assert lay is not None and lay.skipped == 0 and len(lay.geoms) == meta["features"]


def test_the_two_metre_scales_are_not_mixed_up_a_pipeline_190_m_east_and_one_190_m_north_are_both_inside_200_m(tmp_path):
    """A degree of longitude is about 92.6 km at this latitude and a degree of latitude 110.5 km: with the scales swapped, 190 m east reads as 227 m and is missed."""
    for feature in (east(190), north(190)):
        got = _pl(_copy(_sub(tmp_path, "d" + feature["properties"]["feature_name"][:1]), [feature]))
        assert got["hit"] is True and got["near_edge"] is False and got["nearest_m"] == 190, feature["properties"]


# ---- review points (Sol, 2026-11-26): a long lot, a non-line shape, bad nearest fields, a date in the future ----
def test_a_pipeline_beside_the_far_end_of_a_very_long_lot_is_a_hit_even_when_it_is_over_60_km_from_the_point(tmp_path):
    far_east_deg = 70000.0 / MX                                   # the lot's far end is 70 km east of the reference point
    end_x = LNG + far_east_deg
    pipeline = {"type": "Feature", "geometry": {"type": "LineString", "coordinates": [[end_x + 100.0 / MX, LAT - 0.01], [end_x + 100.0 / MX, LAT + 0.01]]}, "properties": {"feature_name": "Far Line"}}
    h = 20.0 / MY
    outline = [[LNG, LAT - h], [end_x, LAT - h], [end_x, LAT + h], [LNG, LAT + h], [LNG, LAT - h]]
    got = _pl(_copy(tmp_path, [pipeline]), rings=outline)
    assert got is not None and got["hit"] is True and got["names"] == ["Far Line"]


def test_a_layer_holding_a_polygon_gives_no_answer_at_all(tmp_path):
    poly = {"type": "Feature", "geometry": {"type": "Polygon", "coordinates": [[[LNG - 0.01, LAT - 0.01], [LNG + 0.01, LAT - 0.01], [LNG + 0.01, LAT + 0.01], [LNG - 0.01, LAT - 0.01]]]}, "properties": {"feature_name": "Not a pipeline"}}
    assert _pl(_copy(tmp_path, [east(500), poly])) is None


@pytest.mark.parametrize("change", [{"nearest_m": float("nan")}, {"nearest_m": float("inf")}, {"nearest_name": 42}, {"nearest_m": None, "searched_m": "60000"}, {"nearest_m": None, "searched_m": float("nan")},
                                    {"nearest_m": None, "searched_m": None}, {"nearest_m": None, "searched_m": -1}])
def test_a_wrong_typed_nearest_field_sends_the_lookup_to_the_live_service(change):
    good = {"hit": False, "names": [], "nearest_m": 1500, "nearest_name": "X", "searched_m": 60000, "near_edge": False, "as_of": "2026-11-25"}
    assert inp._pipeline_from_copy(lambda *a: dict(good), LAT, LNG, None, 200.0) is not None
    assert inp._pipeline_from_copy(lambda *a: {**good, **change}, LAT, LNG, None, 200.0) is None


def test_the_committed_layer_is_not_dated_in_the_future_in_utc():
    """The service runs on UTC: a copy dated by a local date ahead of UTC would be refused as dated in the future until UTC caught up."""
    from datetime import datetime, timezone

    man = json.loads((Path(__file__).resolve().parents[1] / "data" / "law" / "maps" / "manifest.json").read_text(encoding="utf-8"))
    read_on = datetime.strptime(man["layers"]["gas_pipelines"]["read_on"], "%Y-%m-%d").date()
    assert read_on <= datetime.now(timezone.utc).date()
