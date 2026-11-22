"""The saved-map reader answers only from a copy it can prove, and never gives a clear otherwise."""
from __future__ import annotations

import gzip
import hashlib
import json
from datetime import date, timedelta
from pathlib import Path

import pytest

from services import lmr_map_copy as mc

TODAY = date(2026, 11, 20)
# A square 0.01 degrees wide (about 1 km) with its south-west corner at lng 151.00, lat -33.00.
SQUARE = {"type": "Polygon", "coordinates": [[[151.00, -33.00], [151.01, -33.00], [151.01, -32.99], [151.00, -32.99], [151.00, -33.00]]]}
ZERO = {"type": "Polygon", "coordinates": [[[151.5, -33.5], [151.5, -33.5], [151.5, -33.5], [151.5, -33.5]]]}


def _write(tmp: Path, features: list, read_on: str = "2026-11-18", name: str = "tod_sites", count: int | None = None, bad_hash: bool = False) -> Path:
    raw = gzip.compress(json.dumps({"type": "FeatureCollection", "features": features}).encode())
    (tmp / f"{name}.geojson.gz").write_bytes(raw)
    sha = "0" * 64 if bad_hash else hashlib.sha256(raw).hexdigest()
    (tmp / "manifest.json").write_text(json.dumps({"read_on": read_on, "layers": {name: {
        "features": len(features) if count is None else count, "files": [{"file": f"{name}.geojson.gz", "sha256": sha}]}}}))
    return tmp


def _feat(g=SQUARE, **props):
    return {"type": "Feature", "geometry": g, "properties": props}


def _copy(tmp_path, features=None, **kw):
    return mc.MapCopy(_write(tmp_path, features if features is not None else [_feat()], **kw))


def test_point_inside_is_a_hit_and_outside_is_not(tmp_path):
    c = _copy(tmp_path)
    assert c.check("tod_map", -32.995, 151.005, today=TODAY)["point"] is True
    out = c.check("tod_map", -32.95, 151.2, today=TODAY)
    assert out["point"] is False and out["as_of"] == "2026-11-18"


def test_near_edge_is_flagged_so_the_caller_asks_the_live_map(tmp_path):
    c = _copy(tmp_path)
    near = c.check("tod_map", -32.995, 151.0100 + 2 / 111000, today=TODAY)        # about 2 m outside the east edge
    far = c.check("tod_map", -32.995, 151.0100 + 50 / 111000, today=TODAY)        # about 50 m outside
    assert near["near_edge"] is True and far["near_edge"] is False


def test_a_lot_straddling_an_edge_is_part_not_clear(tmp_path):
    c = _copy(tmp_path)
    ring = [[151.0095, -32.995], [151.0115, -32.995], [151.0115, -32.9945], [151.0095, -32.9945], [151.0095, -32.995]]
    out = c.check("tod_map", -32.9948, 151.0113, rings=ring, today=TODAY)   # point outside, lot overlaps
    assert out["point"] is False and out["lot"] is True


def test_no_lot_outline_gives_lot_none_not_false(tmp_path):
    assert _copy(tmp_path).check("tod_map", -32.995, 151.005, today=TODAY)["lot"] is None
    assert _copy(tmp_path).check("tod_map", -32.995, 151.005, rings=[[1, 2]], today=TODAY)["lot"] is None


def test_unknown_layer_key_is_no_answer(tmp_path):
    assert _copy(tmp_path).check("bushfire", -32.995, 151.005, today=TODAY) is None


@pytest.mark.parametrize("kw", [{"bad_hash": True}, {"count": 99}])
def test_a_copy_that_cannot_be_proven_is_no_answer_never_clear(tmp_path, kw):
    assert _copy(tmp_path, **kw).check("tod_map", -32.995, 151.005, today=TODAY) is None


def test_missing_file_and_missing_manifest_are_no_answer(tmp_path):
    c = _copy(tmp_path)
    (tmp_path / "tod_sites.geojson.gz").unlink()
    assert c.check("tod_map", -32.995, 151.005, today=TODAY) is None
    assert mc.MapCopy(tmp_path / "nowhere").check("tod_map", -32.995, 151.005, today=TODAY) is None


def test_a_copy_older_than_the_limit_is_no_answer_and_the_limit_day_is_accepted(tmp_path):
    c = _copy(tmp_path, read_on=(TODAY - timedelta(days=mc.MAX_AGE_DAYS)).isoformat())
    assert c.check("tod_map", -32.995, 151.005, today=TODAY) is not None
    assert c.check("tod_map", -32.995, 151.005, today=TODAY + timedelta(days=1)) is None


def test_an_empty_layer_is_no_answer_because_empty_would_read_as_clear(tmp_path):
    assert _copy(tmp_path, features=[]).check("tod_map", -32.995, 151.005, today=TODAY) is None


def test_a_zero_area_polygon_is_counted_and_skipped_not_fatal(tmp_path):
    c = _copy(tmp_path, features=[_feat(), _feat(ZERO)])
    assert c.check("tod_map", -32.995, 151.005, today=TODAY)["point"] is True
    assert c.layer("tod_sites", TODAY).skipped == 1


def test_noise_bands_return_the_bands_the_lot_touches(tmp_path):
    c = mc.MapCopy(_write(tmp_path, [_feat(ANEF_CODE="25 - 30", LAY_NAME="Air Noise Exposure Forecast")], name="airport_noise"))
    assert c.noise_bands(-32.995, 151.005, today=TODAY) == [{"code": "25 - 30", "name": "Air Noise Exposure Forecast"}]
    assert c.noise_bands(-32.95, 151.2, today=TODAY) == []
    assert mc.MapCopy(tmp_path / "nowhere").noise_bands(-32.995, 151.005, today=TODAY) is None


def test_a_lot_edge_close_to_a_layer_edge_is_flagged_even_when_the_point_is_far(tmp_path):
    c = _copy(tmp_path)
    ring = [[151.0100 + 2 / 111000, -32.9950], [151.0110, -32.9950], [151.0110, -32.9940], [151.0100 + 2 / 111000, -32.9940], [151.0100 + 2 / 111000, -32.9950]]
    out = c.check("tod_map", -32.9945, 151.0300, rings=ring, today=TODAY)    # point 2 km away; the lot starts 2 m outside the layer
    assert out["point"] is False and out["lot"] is False and out["near_edge"] is True


def test_the_edge_tolerance_is_in_metres_east_west_too(tmp_path):
    c = _copy(tmp_path)
    four_m_east = 4.8 / (111000 * 0.8387)          # about 4.8 m of longitude at latitude -33: inside 5 m, but outside 5 m read as flat latitude degrees
    assert c.check("tod_map", -32.995, 151.0100 + four_m_east, today=TODAY)["near_edge"] is True


def test_a_degenerate_lot_ring_falls_back_to_the_point_for_noise(tmp_path):
    c = mc.MapCopy(_write(tmp_path, [_feat(ANEF_CODE="25 - 30", LAY_NAME="Air Noise Exposure Forecast")], name="airport_noise"))
    bad = [[151.005, -32.995]] * 5
    assert c.noise_bands(-32.995, 151.005, rings=bad, today=TODAY) == [{"code": "25 - 30", "name": "Air Noise Exposure Forecast"}]


def test_a_read_on_date_in_the_future_is_no_answer(tmp_path):
    c = _copy(tmp_path, read_on="2027-11-18")
    assert c.check("tod_map", -32.995, 151.005, today=TODAY) is None


def test_the_real_saved_files_load_and_match_the_manifest():
    """The committed files: every layer loads, the Georges River shape contains a known inside point, and each layer's hash and count hold."""
    c = mc.MapCopy()
    man = json.loads((mc.MAPS_DIR / "manifest.json").read_text())
    today = max(date.fromisoformat(man["read_on"]), *[date.fromisoformat(v["read_on"]) for v in man["layers"].values() if v.get("read_on")])   # a layer may carry its own, later, read_on
    for key in mc.COPY_KEYS:
        assert c.check(key, -33.9, 151.0, today=today) is not None, key
    lay = c.layer("georges_catchment", today)
    inside = lay.geoms[0].representative_point()
    got = c.check("georges_catchment", inside.y, inside.x, today=today)
    assert got["point"] is True and got["as_of"] == "2026-11-18"
    assert c.check("georges_catchment", -30.0, 145.0, today=today)["point"] is False   # far west of NSW's Georges River catchment


# ---- flood-study distances (MapCopy.flood_distance) -------------------------------------------------------
import math  # noqa: E402

FLAT = {"type": "Polygon", "coordinates": [[[150.70, -33.70], [150.71, -33.70], [150.71, -33.69], [150.70, -33.69], [150.70, -33.70]]]}   # 0.01 x 0.01 degrees
FLAT_EAST, FLAT_NORTH = 150.71, -33.69


def _m_per_deg(lat: float) -> tuple[float, float]:
    return 111320.0 * math.cos(math.radians(lat)), 110540.0


def _flood_write(tmp: Path, file_read_on: str = "2026-11-18", layer_read_on=None, max_age=None, count=None, bad_hash=False, name="hn_pmf") -> Path:
    raw = gzip.compress(json.dumps({"type": "FeatureCollection", "features": [_feat(FLAT)]}).encode())
    (tmp / f"{name}.geojson.gz").write_bytes(raw)
    meta: dict = {"features": 1 if count is None else count,
                  "files": [{"file": f"{name}.geojson.gz", "sha256": "0" * 64 if bad_hash else hashlib.sha256(raw).hexdigest()}]}
    if layer_read_on is not None:
        meta["read_on"] = layer_read_on
    if max_age is not None:
        meta["max_age_days"] = max_age
    (tmp / "manifest.json").write_text(json.dumps({"read_on": file_read_on, "layers": {name: meta}}))
    return tmp


def _flood(tmp_path, **kw):
    return mc.MapCopy(_flood_write(tmp_path, **kw))


def test_flood_point_inside_has_zero_nearest_and_a_positive_edge_distance(tmp_path):
    lat, lng = -33.695, 150.705
    out = _flood(tmp_path).flood_distance("hn_pmf", lat, lng, today=TODAY)
    mx, my = _m_per_deg(lat)
    expect = min(0.005 * mx, 0.005 * my)             # centre of the square: the nearest side is the east-west pair
    assert out["inside"] is True and out["nearest_m"] == 0.0 and out["within_box"] is True and out["used_outline"] is False
    assert out["edge_m"] == pytest.approx(expect, abs=1.0) and out["edge_m"] > 400
    assert out["as_of"] == "2026-11-18" and out["polygons"] == 1


def test_flood_point_50m_outside_the_edge_and_5km_outside(tmp_path):
    c = _flood(tmp_path)
    lat = -33.695
    mx, _ = _m_per_deg(lat)
    near = c.flood_distance("hn_pmf", lat, FLAT_EAST + 50 / mx, today=TODAY)
    assert near["inside"] is False and near["within_box"] is False       # just outside the layer's box too
    assert near["edge_m"] == pytest.approx(50, abs=5) and near["nearest_m"] == pytest.approx(50, abs=5)
    far = c.flood_distance("hn_pmf", lat, FLAT_EAST + 5000 / mx, today=TODAY)
    assert far["inside"] is False and far["nearest_m"] == pytest.approx(5000, rel=0.02) and far["edge_m"] == pytest.approx(5000, rel=0.02)


def test_flood_lot_outline_straddling_the_edge_is_inside_with_zero_edge(tmp_path):
    ring = [[150.7095, -33.695], [150.7115, -33.695], [150.7115, -33.6945], [150.7095, -33.6945], [150.7095, -33.695]]
    out = _flood(tmp_path).flood_distance("hn_pmf", -33.6948, 150.7120, rings=ring, today=TODAY)   # the point is outside, the lot overlaps
    assert out["inside"] is True and out["used_outline"] is True and out["edge_m"] < 1 and out["nearest_m"] == 0.0


def test_flood_lot_outline_wholly_outside_is_not_inside_and_uses_the_outline(tmp_path):
    lat = -33.695
    mx, _ = _m_per_deg(lat)
    x0 = FLAT_EAST + 200 / mx
    ring = [[x0, lat], [x0 + 20 / mx, lat], [x0 + 20 / mx, lat + 0.0002], [x0, lat + 0.0002], [x0, lat]]
    out = _flood(tmp_path).flood_distance("hn_pmf", lat, x0, rings=ring, today=TODAY)
    assert out["inside"] is False and out["used_outline"] is True and out["edge_m"] == pytest.approx(200, abs=5)


@pytest.mark.parametrize("ring", [
    [[150.705, -33.695]] * 5,                                                                          # five identical points: zero area
    [[150.705, -33.695], [150.706, -33.695], [150.705, -33.695]],                                      # fewer than 4 points
    [[150.705, -33.695], [150.706, -33.695], [150.707, -33.695], [150.705, -33.695]],                  # collinear: zero area
])
def test_flood_degenerate_outline_falls_back_to_the_point(tmp_path, ring):
    out = _flood(tmp_path).flood_distance("hn_pmf", -33.695, 150.705, rings=ring, today=TODAY)
    assert out["used_outline"] is False and out["inside"] is True        # the point is inside, so a lost outline never reads as "nothing found"


def test_flood_point_outside_the_layer_box_but_near_is_not_within_box(tmp_path):
    out = _flood(tmp_path).flood_distance("hn_pmf", -33.60, 150.705, today=TODAY)   # about 10 km north of the square
    assert out["within_box"] is False and out["inside"] is False
    assert out["nearest_m"] == pytest.approx((-33.60 - FLAT_NORTH) * 110540.0, rel=0.02)


def test_flood_far_point_has_no_distances_and_is_not_inside(tmp_path):
    out = _flood(tmp_path).flood_distance("hn_pmf", -33.695, 151.5, today=TODAY)   # 0.8 degrees east: beyond FLOOD_SEARCH_DEG
    assert out["edge_m"] is None and out["nearest_m"] is None and out["inside"] is False and out["within_box"] is False and out["polygons"] == 0


def test_flood_layer_own_read_on_is_used_instead_of_the_file_wide_one(tmp_path):
    old_file = (TODAY - timedelta(days=100)).isoformat()      # the file-wide date alone would be too old for the 45-day limit
    c = _flood(tmp_path, file_read_on=old_file, layer_read_on=TODAY.isoformat())
    out = c.flood_distance("hn_pmf", -33.695, 150.705, today=TODAY)
    assert out is not None and out["as_of"] == TODAY.isoformat()
    assert c.flood_distance("hn_pmf", -33.695, 150.705, today=TODAY - timedelta(days=1)) is None   # its read_on is then in the future


def test_flood_layer_max_age_days_is_respected(tmp_path):
    ok = _flood(tmp_path, layer_read_on=(TODAY - timedelta(days=300)).isoformat(), max_age=400)
    assert ok.flood_distance("hn_pmf", -33.695, 150.705, today=TODAY)["inside"] is True
    old = _flood(tmp_path, layer_read_on=(TODAY - timedelta(days=401)).isoformat(), max_age=400)
    assert old.flood_distance("hn_pmf", -33.695, 150.705, today=TODAY) is None
    edge = _flood(tmp_path, layer_read_on=(TODAY - timedelta(days=400)).isoformat(), max_age=400)
    assert edge.flood_distance("hn_pmf", -33.695, 150.705, today=TODAY) is not None


def test_flood_layer_without_max_age_days_uses_the_45_day_limit(tmp_path):
    assert mc.MAX_AGE_DAYS == 45
    at_limit = _flood(tmp_path, layer_read_on=(TODAY - timedelta(days=45)).isoformat())
    assert at_limit.flood_distance("hn_pmf", -33.695, 150.705, today=TODAY) is not None
    past = _flood(tmp_path, layer_read_on=(TODAY - timedelta(days=46)).isoformat())
    assert past.flood_distance("hn_pmf", -33.695, 150.705, today=TODAY) is None


@pytest.mark.parametrize("bad", [0, -5, True, "400", 4.5])
def test_flood_a_nonsense_max_age_days_falls_back_to_45(tmp_path, bad):
    c = _flood(tmp_path, layer_read_on=(TODAY - timedelta(days=100)).isoformat(), max_age=bad)
    assert c.flood_distance("hn_pmf", -33.695, 150.705, today=TODAY) is None


@pytest.mark.parametrize("kw", [{"bad_hash": True}, {"count": 99}])
def test_flood_a_copy_that_cannot_be_proven_is_no_answer(tmp_path, kw):
    assert _flood(tmp_path, layer_read_on=TODAY.isoformat(), **kw).flood_distance("hn_pmf", -33.695, 150.705, today=TODAY) is None


def test_flood_missing_file_missing_manifest_and_unknown_key_are_no_answer(tmp_path):
    c = _flood(tmp_path, layer_read_on=TODAY.isoformat())
    assert c.flood_distance("nope", -33.695, 150.705, today=TODAY) is None
    (tmp_path / "hn_pmf.geojson.gz").unlink()
    assert c.flood_distance("hn_pmf", -33.695, 150.705, today=TODAY) is None
    assert mc.MapCopy(tmp_path / "nowhere").flood_distance("hn_pmf", -33.695, 150.705, today=TODAY) is None


def test_flood_the_three_study_keys_map_to_their_own_files():
    assert {k: mc.COPY_KEYS[k] for k in ("hn_pmf", "hn_500aep", "hn_100aep")} == {"hn_pmf": "hn_pmf", "hn_500aep": "hn_500aep", "hn_100aep": "hn_100aep"}
    assert mc.FLOOD_EDGE_M == 100.0 and mc.FLOOD_SEARCH_DEG == 0.3


FLOOD_TODAY = date(2026, 11, 22)


def test_the_real_pmf_file_places_known_points():
    far = mc.flood_distance("hn_pmf", -33.7355, 151.1385, today=FLOOD_TODAY)
    assert far["inside"] is False and far["within_box"] is True and 9000 <= far["nearest_m"] <= 11000
    assert mc.flood_distance("hn_pmf", -33.6103, 150.8156, today=FLOOD_TODAY)["inside"] is True        # Windsor
    assert mc.flood_distance("hn_pmf", -33.73, 151.005, today=FLOOD_TODAY)["inside"] is False         # Castle Hill


def test_a_flood_layer_with_a_skipped_area_gives_no_answer_never_a_clear(tmp_path):
    """One unreadable or zero-area flood polygon means a lot inside it would read as clear, so the whole layer answers None (the area check then keeps its older rule)."""
    raw = gzip.compress(json.dumps({"type": "FeatureCollection", "features": [_feat(FLAT), _feat(ZERO)]}).encode())
    (tmp_path / "hn_pmf.geojson.gz").write_bytes(raw)
    (tmp_path / "manifest.json").write_text(json.dumps({"read_on": "2026-11-18", "layers": {"hn_pmf": {"features": 2, "files": [
        {"file": "hn_pmf.geojson.gz", "sha256": hashlib.sha256(raw).hexdigest()}]}}}))
    c = mc.MapCopy(tmp_path)
    assert c.layer("hn_pmf", TODAY).skipped == 1                                       # the layer itself loads (the generic loader tolerates it)
    assert c.flood_distance("hn_pmf", -33.695, 150.705, today=TODAY) is None           # but the flood answer refuses to rest on an incomplete layer
