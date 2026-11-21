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


def test_the_real_saved_files_load_and_match_the_manifest():
    """The committed files: every layer loads, the Georges River shape contains a known inside point, and each layer's hash and count hold."""
    c = mc.MapCopy()
    today = date.fromisoformat(json.loads((mc.MAPS_DIR / "manifest.json").read_text())["read_on"])
    for key in mc.COPY_KEYS:
        assert c.check(key, -33.9, 151.0, today=today) is not None, key
    lay = c.layer("georges_catchment", today)
    inside = lay.geoms[0].representative_point()
    got = c.check("georges_catchment", inside.y, inside.x, today=today)
    assert got["point"] is True and got["as_of"] == "2026-11-18"
    assert c.check("georges_catchment", -30.0, 145.0, today=today)["point"] is False   # far west of NSW's Georges River catchment
