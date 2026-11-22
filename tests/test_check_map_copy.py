"""The age and integrity check goes red before the reader stops using the copy, and on any layer it cannot prove."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "lmr_area"))
import check_map_copy as cm  # noqa: E402
from services import lmr_map_copy as mc  # noqa: E402

TODAY = date(2026, 11, 21)
SQUARE = {"type": "Polygon", "coordinates": [[[151.0, -33.0], [151.01, -33.0], [151.01, -32.99], [151.0, -32.99], [151.0, -33.0]]]}


def _maps(tmp: Path, read_on: str, bad_layer: str | None = None) -> Path:
    layers = {}
    for name in mc.COPY_KEYS.values():
        raw = gzip.compress(json.dumps({"features": [{"type": "Feature", "geometry": SQUARE, "properties": {}}]}).encode())
        (tmp / f"{name}.geojson.gz").write_bytes(raw)
        layers[name] = {"features": 1, "files": [{"file": f"{name}.geojson.gz", "sha256": "0" * 64 if name == bad_layer else hashlib.sha256(raw).hexdigest()}]}
    (tmp / "manifest.json").write_text(json.dumps({"read_on": read_on, "layers": layers}))
    return tmp


def test_a_fresh_intact_copy_passes(tmp_path):
    ok, lines = cm.age_and_integrity(TODAY, _maps(tmp_path, (TODAY - timedelta(days=3)).isoformat()))
    assert ok and any("all 8 layers load" in ln for ln in lines)


def test_the_reminder_day_goes_red_and_the_day_before_does_not(tmp_path):
    m = _maps(tmp_path, (TODAY - timedelta(days=cm.WARN_DAYS - 1)).isoformat())
    assert cm.age_and_integrity(TODAY, m)[0] is True
    ok, lines = cm.age_and_integrity(TODAY + timedelta(days=1), m)
    assert ok is False and any("Refresh now" in ln for ln in lines)


def test_the_reminder_comes_before_the_reader_stops_using_the_copy():
    assert cm.WARN_DAYS < mc.MAX_AGE_DAYS


def test_one_layer_that_fails_its_hash_goes_red_and_is_named(tmp_path):
    ok, lines = cm.age_and_integrity(TODAY, _maps(tmp_path, TODAY.isoformat(), bad_layer="hn_catchment"))
    assert ok is False and any("hn_catchment" in ln for ln in lines)


def test_a_missing_or_future_manifest_goes_red(tmp_path):
    assert cm.age_and_integrity(TODAY, tmp_path)[0] is False
    ok, lines = cm.age_and_integrity(TODAY, _maps(tmp_path, (TODAY + timedelta(days=5)).isoformat()))
    assert ok is False and any("future" in ln for ln in lines)


def test_the_real_committed_copy_passes_on_the_day_it_was_read():
    read_on = date.fromisoformat(json.loads((mc.MAPS_DIR / "manifest.json").read_text())["read_on"])
    assert cm.age_and_integrity(read_on)[0] is True


def _lots(n):
    sq = [[151.0, -33.0], [151.001, -33.0], [151.001, -32.999], [151.0, -32.999], [151.0, -33.0]]
    return [{"lat": -32.9995, "lng": 151.0005, "rings": sq} for _ in range(n)]


def test_a_compare_where_the_live_maps_answer_nothing_fails_it_does_not_pass(monkeypatch):
    monkeypatch.setattr(cm, "_sample_lots", lambda n, seed: _lots(n))
    monkeypatch.setattr(cm.inp, "_layer", lambda *a, **k: {"point": None, "lot": None})
    monkeypatch.setattr(cm.mc, "check", lambda *a, **k: {"point": False, "lot": False, "as_of": "2026-11-18", "near_edge": False})
    ok, lines = cm.compare(5, 1)
    assert ok is False and any("answered only 0%" in ln for ln in lines)


def test_a_compare_where_everything_agrees_passes(monkeypatch):
    monkeypatch.setattr(cm, "_sample_lots", lambda n, seed: _lots(n))
    monkeypatch.setattr(cm.inp, "_layer", lambda *a, **k: {"point": False, "lot": False})
    monkeypatch.setattr(cm.mc, "check", lambda *a, **k: {"point": False, "lot": False, "as_of": "2026-11-18", "near_edge": False})
    assert cm.compare(5, 1)[0] is True


def test_a_difference_the_reader_would_not_send_to_live_fails_but_an_edge_difference_does_not(monkeypatch):
    monkeypatch.setattr(cm, "_sample_lots", lambda n, seed: _lots(n))
    monkeypatch.setattr(cm.inp, "_layer", lambda *a, **k: {"point": True, "lot": True})
    monkeypatch.setattr(cm.mc, "check", lambda *a, **k: {"point": False, "lot": False, "as_of": "x", "near_edge": False})
    assert cm.compare(5, 1)[0] is False
    monkeypatch.setattr(cm.mc, "check", lambda *a, **k: {"point": False, "lot": False, "as_of": "x", "near_edge": True})
    assert cm.compare(5, 1)[0] is True


def test_too_few_sampled_lots_fails(monkeypatch):
    monkeypatch.setattr(cm, "_sample_lots", lambda n, seed: _lots(2))
    assert cm.compare(5, 1)[0] is False
