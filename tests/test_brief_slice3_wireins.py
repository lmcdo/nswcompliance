"""Slice 3 wire-in tests — strata detail, bushfire pathway, NARCLIM projections,
terrain interpretation shape.

Break-it scenarios covered:
  1. Bushfire cross_overlays is emitted as a LIST of {type,...} dicts; the old
     contract typed it as dict — validation would raise on every bushfire-prone
     lot with overlays and kill the whole stream (latent, found by trace).
  2. NARCLIM three states must stay distinct: deltas / queried-no-coverage /
     lookup-failed — a missing dataset must surface as an honest gap, never as
     fabricated projections or a silent absence.
  3. StrataHub supplementary fields are display-only — they must never change
     the classify_strata routing decision.
  4. A junk (non-numeric) NARCLIM delta must be skipped, not rendered.
"""
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import services.intelligence_brief as ib
from services.intelligence_brief import (
    BushfireServiceOutput,
    StrataServiceOutput,
    _build_bushfire_detail,
    _build_climate_disclosure,
    classify_strata,
    StrataType,
)

GOLDEN = Path(__file__).parent / "fixtures" / "brief_golden"


def _golden(name: str):
    with open(GOLDEN / f"{name}.json", encoding="utf-8") as fh:
        return json.load(fh)["output"]


# ── 1. bushfire: list-shaped cross_overlays + pathway fields ─────────────────

_PRONE_OUTPUTS = {
    "is_bushfire_prone": True,
    "designation_category": "Vegetation Category 1",
    "estimated_bal_band": "BAL-29",
    "designation_guideline": "Forest",
    "fire_signal": "elevated",
    "compliance": {
        "rfs_referral_required": True,
        "rfs_referral_triggers": ["Bushfire prone land", "Integrated development"],
        "cdc_pathway_available": False,
        "cross_overlays": [
            {"type": "flood", "value": "Flood planning area"},
            {"type": "heritage", "value": "HCA"},
        ],
    },
}


def test_prone_lot_with_overlay_list_does_not_kill_the_stream():
    """The exact shape bushfire_prescreen emits on a prone lot. The old
    Optional[dict] typing raised ValidationError here (stream-killing)."""
    detail = _build_bushfire_detail({"outputs": _PRONE_OUTPUTS, "confidence": "high"})
    assert detail is not None
    assert detail.cross_overlays == _PRONE_OUTPUTS["compliance"]["cross_overlays"]
    assert detail.bal_estimate == "BAL-29"
    assert detail.rfs_referral_required is True
    assert detail.rfs_referral_triggers == ["Bushfire prone land", "Integrated development"]
    assert detail.cdc_pathway_available is False


def test_not_prone_lot_keeps_null_pathway_fields():
    detail = _build_bushfire_detail({"outputs": {"is_bushfire_prone": False}, "confidence": "high"})
    assert detail.rfs_referral_required is None
    assert detail.cross_overlays is None


def test_bushfire_contract_accepts_null_compliance():
    out = BushfireServiceOutput.model_validate({"is_bushfire_prone": False, "compliance": None})
    assert out.compliance is None


# ── 2. NARCLIM projections — three states ────────────────────────────────────

_NARCLIM_OK = {
    "grid_distance_km": 1.2,
    "hot_days_baseline": 6.1,
    "hot_days_delta_2050": 4.3,
    "hot_days_delta_2090": 9.8,
    "temp_delta_2050": 1.1,
    "precip_delta_2090": -0.2,
}


def _climate_raw(narclim):
    raw = dict(_golden("climate_risk"))
    raw["narclim"] = narclim
    return raw


def test_narclim_deltas_become_projected_findings_with_provenance():
    profile = _build_climate_disclosure(_climate_raw(_NARCLIM_OK), None, None, None)
    assert len(profile.projected_findings) == 4  # only the numeric delta keys
    by = {(f.hazard, f.timeframe): f.value for f in profile.projected_findings}
    assert by[("extreme_heat_days", "2050")] == 4.3
    assert by[("extreme_heat_days", "2090")] == 9.8
    assert by[("mean_temperature", "2050")] == 1.1
    assert by[("daily_precipitation", "2090")] == -0.2
    # a projection is never presented bare — model + scenario ride along
    assert all(f.model and f.scenario for f in profile.projected_findings)


def test_narclim_no_coverage_is_an_honest_gap_not_silence():
    profile = _build_climate_disclosure(_climate_raw({}), None, None, None)
    assert profile.projected_findings == []
    assert any(u.source == "narclim_projections" and "coverage" in u.reason
               for u in profile.manifest.sources_unavailable)


def test_narclim_lookup_failure_is_distinct_from_no_coverage():
    profile = _build_climate_disclosure(_climate_raw(None), None, None, None)
    assert profile.projected_findings == []
    assert any(u.source == "narclim_projections" and "failed" in u.reason
               for u in profile.manifest.sources_unavailable)


def test_narclim_junk_delta_is_skipped_not_rendered():
    junk = dict(_NARCLIM_OK)
    junk["temp_delta_2090"] = "hot"
    profile = _build_climate_disclosure(_climate_raw(junk), None, None, None)
    assert ("mean_temperature", "2090") not in {
        (f.hazard, f.timeframe) for f in profile.projected_findings
    }


# ── 3. strata supplementary fields — display only, never routing ─────────────

def test_strata_contract_accepts_registration_date():
    hub = _golden("strata_hub")
    cad = _golden("strata_cadastre")
    enriched = {**cad, "lot_total": hub["lot_total"], "dwelling_type": hub["dwelling_type"],
                "registration_date": hub["registration_date"]}
    out = StrataServiceOutput.model_validate(enriched)
    assert out.registration_date == "2019-09-25"  # the verified SP91614 capture
    assert out.lot_total == 77


def test_supplementary_fields_never_change_routing():
    cad = _golden("strata_cadastre")
    base = {**cad, "lot_total": 77}
    with_extras = {**base, "dwelling_type": "apartment", "registration_date": "2019-09-25"}
    assert classify_strata(base, None) == classify_strata(with_extras, None) == StrataType.APARTMENT


def test_fetch_strata_copies_registration_date(monkeypatch):
    monkeypatch.setattr(ib, "detect_strata",
                        lambda addr, lat, lng: {"is_strata": True, "strata_plan": "SP91614",
                                                "plan_type": "strata", "source": "cadastre",
                                                "parent_has_strata": True, "plan_label": "SP91614"})
    hub = MagicMock(lot_total=77, dwelling_type="apartment", registration_date="2019-09-25")
    import services.strata_lookup as sl
    monkeypatch.setattr(sl, "query_strata_at_point", lambda lng, lat: hub)
    result = ib._fetch_strata("5/1 Treacy Street, Hurstville", -33.968, 151.108)
    assert result["registration_date"] == "2019-09-25"
    assert result["lot_total"] == 77


def test_brief_strata_info_carries_supplementary_fields():
    info = ib.StrataInfo(is_strata=True, strata_type=StrataType.APARTMENT,
                         lot_total=77, dwelling_type="apartment",
                         registration_date="2019-09-25")
    dumped = info.model_dump()
    assert dumped["lot_total"] == 77
    assert dumped["registration_date"] == "2019-09-25"


# ── 4. terrain interpretation shape (the card contract) ──────────────────────

def test_terrain_interpretation_builds_findings_from_metrics():
    from services.terrain_analysis import _build_terrain_interpretation

    interp = _build_terrain_interpretation({
        "slope_mean_deg": 3.2, "slope_max_deg": 8.9, "aspect_dominant_deg": 145.0,
        "aspect_direction": "SE", "elevation_min_m": 12.1, "elevation_max_m": 18.4,
        "elevation_range_m": 6.3, "drainage_direction": "SE", "terrain_ruggedness": 1.02,
        "landform_class": 6, "landform_type": "slope", "daylight_fraction": 0.94,
    })
    assert interp is not None
    dumped = interp.model_dump()
    assert dumped["findings"], "interpretation produced no findings"
    for f in dumped["findings"]:
        assert f["narrative"]  # the text the card renders
        assert f["severity"] in ("green", "amber", "red")
    assert dumped["disclaimer"]
