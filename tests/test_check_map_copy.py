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


def _maps(tmp: Path, read_on: str, bad_layer: str | None = None, own: dict | None = None) -> Path:
    """`own` gives chosen layers their own manifest fields (read_on, max_age_days), as the flood-study layers have."""
    layers = {}
    for name in mc.COPY_KEYS.values():
        raw = gzip.compress(json.dumps({"features": [{"type": "Feature", "geometry": SQUARE, "properties": {}}]}).encode())
        (tmp / f"{name}.geojson.gz").write_bytes(raw)
        layers[name] = {"features": 1, "files": [{"file": f"{name}.geojson.gz", "sha256": "0" * 64 if name == bad_layer else hashlib.sha256(raw).hexdigest()},], **((own or {}).get(name) or {})}
    (tmp / "manifest.json").write_text(json.dumps({"read_on": read_on, "layers": layers}))
    return tmp


def test_a_fresh_intact_copy_passes(tmp_path):
    ok, lines = cm.age_and_integrity(TODAY, _maps(tmp_path, (TODAY - timedelta(days=3)).isoformat()))
    assert ok and any(f"all {len(mc.COPY_KEYS)} layers load" in ln for ln in lines)


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
    man = json.loads((mc.MAPS_DIR / "manifest.json").read_text())
    # the newest read date in the file: the flood-study layers carry their own, later, read_on
    read_on = max(date.fromisoformat(man["read_on"]), *[date.fromisoformat(v["read_on"]) for v in man["layers"].values() if v.get("read_on")])
    assert cm.age_and_integrity(read_on)[0] is True


# ---- layers that carry their own read date and age limit (the 2024 flood-study copy) are judged by those, the rest by the file-wide date and 45 days
FLOOD = ("hn_pmf", "hn_500aep", "hn_100aep")


def _own(read_on: date, max_age=400, names=FLOOD) -> dict:
    return {n: {"read_on": read_on.isoformat(), **({"max_age_days": max_age} if max_age is not None else {})} for n in names}


def test_a_layer_with_its_own_date_and_a_400_day_limit_is_fine_at_100_days_though_the_file_date_is_recent(tmp_path):
    m = _maps(tmp_path, (TODAY - timedelta(days=3)).isoformat(), own=_own(TODAY - timedelta(days=100)))
    ok, lines = cm.age_and_integrity(TODAY, m)
    assert ok is True, lines


def test_a_layer_with_its_own_limit_goes_red_15_days_before_that_limit_and_not_the_day_before(tmp_path):
    reminder = 400 - (mc.MAX_AGE_DAYS - cm.WARN_DAYS)
    (tmp_path / "a").mkdir()
    day_before = _maps(tmp_path / "a", (TODAY - timedelta(days=3)).isoformat(), own=_own(TODAY - timedelta(days=reminder - 1)))
    assert cm.age_and_integrity(TODAY, day_before)[0] is True
    (tmp_path / "b").mkdir()
    on_the_day = _maps(tmp_path / "b", (TODAY - timedelta(days=3)).isoformat(), own=_own(TODAY - timedelta(days=reminder)))
    ok, lines = cm.age_and_integrity(TODAY, on_the_day)
    assert ok is False and any("hn_pmf" in ln and "stops using it at 400" in ln for ln in lines)


def test_a_layer_with_no_limit_of_its_own_uses_the_readers_45_days(tmp_path):
    m = _maps(tmp_path, (TODAY - timedelta(days=3)).isoformat(), own=_own(TODAY - timedelta(days=cm.WARN_DAYS), max_age=None))
    ok, lines = cm.age_and_integrity(TODAY, m)
    assert ok is False and any("stops using it at 45" in ln for ln in lines)


def test_a_layer_dated_in_the_future_or_with_an_unreadable_date_goes_red(tmp_path):
    ok, lines = cm.age_and_integrity(TODAY, _maps(tmp_path, TODAY.isoformat(), own=_own(TODAY + timedelta(days=2))))
    assert ok is False and any("hn_pmf" in ln and "future" in ln for ln in lines)
    (tmp_path / "x").mkdir()
    m = _maps(tmp_path / "x", TODAY.isoformat(), own={"hn_pmf": {"read_on": "last tuesday"}})
    ok, lines = cm.age_and_integrity(TODAY, m)
    assert ok is False and any("hn_pmf" in ln and "unreadable read_on" in ln for ln in lines)


def test_a_flood_layer_that_fails_its_hash_goes_red_even_with_its_own_date(tmp_path):
    m = _maps(tmp_path, TODAY.isoformat(), bad_layer="hn_pmf", own=_own(TODAY - timedelta(days=5)))
    ok, lines = cm.age_and_integrity(TODAY, m)
    assert ok is False and any("hn_pmf" in ln and "hash or feature count" in ln for ln in lines)


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
