"""B: live lot-level Protection-overlay fallback.

When our ingested coverage is missing riparian/wetlands/biodiversity, the brief
live-queries the NSW Protection layer for THIS lot instead of leaking an internal
"Layer not ingested" gap. These tests pin: DB coverage wins (no live call); live
'present' -> the real class; live 'none here' -> a clean False (good news);
a failed live query or missing coords -> the conservative NOT_AVAILABLE fallback.
"""
import services.intelligence_brief as ib
import services.portal_constraints as pc


def _env(overlays_data, lat=-33.8, lng=151.1):
    return ib._build_environmental({}, overlays_data, None, lat=lat, lng=lng)


def test_db_coverage_wins_no_live_call(monkeypatch):
    calls = {"n": 0}

    def _boom(*a, **k):
        calls["n"] += 1
        return {"present": True, "value": "x"}

    monkeypatch.setattr(pc, "fetch_protection_overlay", _boom)
    env = _env({
        "overlays": [{"layer_type": "riparian", "value": "Cat 1"}],
        "covered_layers": ["riparian", "wetlands", "biodiversity"],
    })
    assert env.riparian_land.value is True
    assert env.riparian_land.source == "postgis_overlays"
    assert calls["n"] == 0  # all three layers covered by DB -> no live calls


def test_live_present_reports_the_real_fact(monkeypatch):
    monkeypatch.setattr(pc, "fetch_protection_overlay", lambda lat, lng, lid, **k: {"present": True, "value": "Watercourse"})
    env = _env({"overlays": [], "covered_layers": []})
    assert env.riparian_land.value is True
    assert env.riparian_land.confidence == ib.ConfidenceLevel.AUTHORITATIVE
    assert env.riparian_land.source == "live_protection_overlay"


def test_live_absent_is_a_clean_false(monkeypatch):
    monkeypatch.setattr(pc, "fetch_protection_overlay", lambda lat, lng, lid, **k: {"present": False, "value": None})
    env = _env({"overlays": [], "covered_layers": []})
    assert env.wetlands.value is False
    assert env.wetlands.confidence == ib.ConfidenceLevel.AUTHORITATIVE


def test_live_failure_falls_back_to_not_available(monkeypatch):
    monkeypatch.setattr(pc, "fetch_protection_overlay", lambda lat, lng, lid, **k: None)
    env = _env({"overlays": [], "covered_layers": []})
    assert env.riparian_land.confidence == ib.ConfidenceLevel.NOT_AVAILABLE
    assert "not ingested" in (env.riparian_land.reason or "").lower()


def test_missing_coords_skips_live_and_is_not_available(monkeypatch):
    calls = {"n": 0}

    def _count(*a, **k):
        calls["n"] += 1
        return {"present": True, "value": "x"}

    monkeypatch.setattr(pc, "fetch_protection_overlay", _count)
    env = _env({"overlays": [], "covered_layers": []}, lat=None, lng=None)
    assert env.riparian_land.confidence == ib.ConfidenceLevel.NOT_AVAILABLE
    assert calls["n"] == 0


def test_all_three_protection_layers_use_the_fallback(monkeypatch):
    seen = []

    def _rec(lat, lng, lid, **k):
        seen.append(lid)
        return {"present": False, "value": None}

    monkeypatch.setattr(pc, "fetch_protection_overlay", _rec)
    env = _env({"overlays": [], "covered_layers": []})
    assert env.terrestrial_biodiversity.value is False
    assert env.riparian_land.value is False
    assert env.wetlands.value is False
    assert sorted(seen) == [7, 10, 11]
