"""B: live lot-level Protection-overlay fallback.

When our ingested coverage is missing riparian/wetlands/biodiversity, the brief
live-queries the NSW Protection layer for THIS lot instead of leaking an internal
"Layer not ingested" gap. These tests pin: DB coverage wins (no live call); live
'present' -> the real class; live 'none here' -> a clean False (good news);
a failed live query or missing coords -> the conservative NOT_AVAILABLE fallback.
"""
import pytest

import services.intelligence_brief as ib
import services.portal_constraints as pc


@pytest.fixture(autouse=True)
def _stub_anef(monkeypatch):
    # Keep the live ANEF layer (Protection ArcGIS) offline by default so the
    # overlay tests don't do live I/O. ANEF tests override this. anef_zones is
    # quarantined (#686) — stubbed too so any regression is loud, not live.
    monkeypatch.setattr(ib, "fetch_anef_zone", lambda lat, lng: None)
    monkeypatch.setattr(pc, "fetch_anef", lambda lat, lng: None)


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


# --- ANEF: live LEP/SEPP-mapped layer only (anef_zones quarantined, #686) ---

def test_anef_zones_never_consulted(monkeypatch):
    # Data-quality quarantine (#686): the coarse anef_zones digitisations must
    # never feed the brief's ANEF field. Mutation check: re-adding the
    # fetch_anef_zone step to _anef_fields fails this.
    def _boom(lat, lng):
        raise AssertionError("anef_zones consulted by the brief's ANEF field")
    monkeypatch.setattr(ib, "fetch_anef_zone", _boom)
    monkeypatch.setattr(pc, "fetch_anef", lambda lat, lng: None)
    env = _env({"overlays": [], "covered_layers": []})
    assert env.anef.source != "anef_zones"


def test_anef_live_layer_value_renders(monkeypatch):
    monkeypatch.setattr(pc, "fetch_anef", lambda lat, lng: {"anef_code": "20 - 25"})
    env = _env({"overlays": [], "covered_layers": []})
    assert "20 - 25" in (env.anef.value or "")
    assert env.anef.source == "planning_portal_protection"


def test_anef_no_mapped_contour_is_honest():
    # autouse stub: live layer None -> honest "no contour in the mapped layers",
    # scoped to what was actually checked — never "no noise".
    env = _env({"overlays": [], "covered_layers": []})
    assert env.anef.value == "No ANEF contour in the mapped planning layers at this property"
    assert env.anef.confidence == ib.ConfidenceLevel.AUTHORITATIVE


def test_anef_missing_coords_is_not_available(monkeypatch):
    called = {"n": 0}
    monkeypatch.setattr(pc, "fetch_anef", lambda lat, lng: called.__setitem__("n", called["n"] + 1))
    env = _env({"overlays": [], "covered_layers": []}, lat=None, lng=None)
    assert env.anef.confidence == ib.ConfidenceLevel.NOT_AVAILABLE
    assert called["n"] == 0


def test_anef_covered_but_empty_falls_through_to_live(monkeypatch):
    # 'anef' is "covered" for the LGA but carries no value at this lot (the sparse
    # ingested-overlay case). This must NOT short-circuit to a blank — it falls
    # through to the live LEP/SEPP-mapped layer.
    monkeypatch.setattr(pc, "fetch_anef", lambda lat, lng: {"anef_code": "25 - 30"})
    env = _env({"overlays": [], "covered_layers": ["anef"]})
    assert "25 - 30" in (env.anef.value or "")
    assert env.anef.source == "planning_portal_protection"


def test_anef_covered_with_value_still_uses_overlay(monkeypatch):
    # When the ingested overlay actually has a value, it wins — the live layer
    # is not consulted (guards against over-correcting the fix).
    def _boom(lat, lng):
        raise AssertionError("live ANEF layer must not be queried when the overlay has a value")

    monkeypatch.setattr(pc, "fetch_anef", _boom)
    env = _env({"overlays": [{"layer_type": "anef", "value": "ANEF 25-30"}],
                "covered_layers": ["anef"]})
    assert env.anef.value == "ANEF 25-30"
    assert env.anef.source == "postgis_overlays"
