"""S3 golden-fixture tests — REAL captured service output vs the S2 contracts.

Fixtures in tests/fixtures/brief_golden/ were captured 2026-07-04 by running
the real services (scripts/capture_brief_golden_fixtures.py) against the
verified demo addresses — NOT hand-written mocks.

⚠ CORRECTED 2026-08-07. This docstring used to claim the fixtures "cannot be
self-confirming: if a service renames a key, re-capture + these tests diverge."
That is only true for a RENAMED key. When a service ADDS one, a fixture and a
contract that both predate it are wrong in the same direction and every test
comparing one to the other stays green — which is what happened when
climate_risk_score.to_dict gained ``confidence_reason``. A captured fixture is
still a stored artefact, and comparing two stored artefacts cannot detect drift
in the thing they were both copied from. Contract tests here should reference a
LIVE call wherever the service can be invoked on this box.

Per-layer three-state coverage: populated / queried-empty / failed must each
render distinctly (never conflated).

Honest limit: flood/terrain/bushfire raster pipelines can't run on this dev
box (no rasterio/whitebox); their contracts were locked from the 2026-06-22
live capture (#597/#598) and stay covered by the live drift check.
"""
import dataclasses
import json
from pathlib import Path

import pytest

from brief_contract_drift import check_drift
from services.intelligence_brief import (
    ClimateHazardOutput,
    ClimateRiskServiceOutput,
    ConfidenceLevel,
    HousingSeppFormOutput,
    LepLandUseRow,
    StrataCoreOutput,
    StrataServiceOutput,
    TerrainAnalysisDetail,
    _build_climate_disclosure,
    _build_terrain_detail,
    classify_strata,
    StrataType,
)

GOLDEN = Path(__file__).parent / "fixtures" / "brief_golden"


def _load(name: str):
    path = GOLDEN / f"{name}.json"
    assert path.exists(), f"golden fixture missing: {path} — run scripts/capture_brief_golden_fixtures.py"
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)["output"]


# ── strata ───────────────────────────────────────────────────────────────────

def test_real_cadastre_output_satisfies_strata_contract():
    raw = _load("strata_cadastre")
    assert check_drift(StrataCoreOutput, raw)["drift"] is False
    out = StrataServiceOutput.model_validate(raw)
    assert out.is_strata is True
    assert out.strata_plan == "SP91614"  # the verified Hurstville scheme


def test_real_strata_hub_enrichment_classifies_apartment_not_heuristic():
    raw = _load("strata_cadastre")
    hub = _load("strata_hub")
    enriched = {**raw, "lot_total": hub["lot_total"], "dwelling_type": hub["dwelling_type"]}
    # 77 lots → apartment via the authoritative count, regardless of lot area.
    assert classify_strata(enriched, lot_area_m2=None) == StrataType.APARTMENT


def test_strata_queried_empty_is_not_strata_not_a_failure():
    # Torrens shape (all contract keys, is_strata False) = queried-and-empty.
    torrens = {"is_strata": False, "strata_plan": None, "plan_type": None,
               "source": "cadastre", "parent_has_strata": False, "plan_label": "1/DP1"}
    assert check_drift(StrataCoreOutput, torrens)["drift"] is False
    assert classify_strata(torrens, lot_area_m2=650.0) == StrataType.NOT_STRATA


# ── climate ──────────────────────────────────────────────────────────────────

def test_real_climate_output_satisfies_contract_and_passes_through_raw():
    raw = _load("climate_risk")
    assert check_drift(ClimateRiskServiceOutput, raw)["drift"] is False
    out = ClimateRiskServiceOutput.model_validate(raw)
    assert len(out.hazards) == 6  # flood/bushfire/coastal/landslide/fire_history/heat
    profile = _build_climate_disclosure(raw, uhi_raw=None, arr_raw=None, firms_raw=None)
    # populated: hazard dicts pass through RAW — byte-identical, nothing re-shaped
    assert profile.per_hazard_detail == raw["hazards"]


def test_new_climate_service_key_is_not_silently_dropped():
    raw = _load("climate_risk")
    raw["hazards"][0]["trend"] = "worsening"  # a future service addition
    profile = _build_climate_disclosure(raw, uhi_raw=None, arr_raw=None, firms_raw=None)
    assert profile.per_hazard_detail[0]["trend"] == "worsening"


def test_climate_contract_violation_becomes_failed_source_not_garbage():
    # Shape change (hazards as dict) previously raised inside assembly; now it
    # must degrade to an honest failed climate source while UHI still reports.
    bad = {"score": 40, "band": "Moderate", "hazards": {"flood": {"raw_score": 1}}}
    profile = _build_climate_disclosure(bad, uhi_raw={"uhi_intensity": 1.5},
                                        arr_raw=None, firms_raw=None)
    assert profile is not None
    assert profile.per_hazard_detail == []          # no fabricated hazard rows
    # climate is NOT counted as a queried+successful source (uhi+arr+firms only)
    assert profile.manifest.sources_queried == 3
    good = _load("climate_risk")
    ok_profile = _build_climate_disclosure(good, uhi_raw={"uhi_intensity": 1.5},
                                           arr_raw=None, firms_raw=None)
    assert ok_profile.manifest.sources_queried == 5  # distinct from the violation case (incl. NARCLIM slot)


def test_climate_queried_empty_distinct_from_failed():
    # All sources absent → no profile at all (card renders NOT_AVAILABLE).
    assert _build_climate_disclosure(None, None, None, None) is None
    # Climate present but hazard-free list → profile exists with empty detail.
    empty = {**_load("climate_risk"), "hazards": []}
    profile = _build_climate_disclosure(empty, None, None, None)
    assert profile is not None
    assert profile.per_hazard_detail == []


def test_climate_hazard_contract_matches_service_to_dict_keys():
    """Locks ClimateHazardOutput to the keys the service ACTUALLY emits.

    This compares against a LIVE ``to_dict()`` call. It previously compared the
    contract to the stored fixture — two stored artefacts — while its comment
    claimed it locked the contract to "the exact keys HazardScore.to_dict
    emits". It did not. When ``to_dict`` gained ``confidence_reason`` (the
    output-grounding work), neither the contract nor the fixture knew, both were
    wrong in the same direction, and this test stayed green for weeks.

    A check that compares a copy against a copy cannot detect drift in the
    original. The live call is now the reference, and the fixture is checked
    against it too — so a stale fixture fails here instead of hiding.
    """
    from services.climate_risk_score import ClimateRiskResult, HazardScore

    served = ClimateRiskResult(
        score=1, band="Low", lat=0.0, lng=0.0,
        hazards=[HazardScore(
            hazard="flood", raw_score=0.0, weight=0.167, weighted_score=0.0,
            present=False, detail="Flood planning layer: No",
            confidence="high", confidence_reason="queried, no intersection",
            data_source="spatial_overlays",
        )],
    ).to_dict()
    served_keys = set(served["hazards"][0].keys())

    assert set(ClimateHazardOutput.model_fields) == served_keys, (
        "ClimateHazardOutput has drifted from what climate_risk_score actually "
        "serialises"
    )

    raw = _load("climate_risk")
    assert set(raw["hazards"][0].keys()) == served_keys, (
        "the captured fixture has drifted from the live service — re-capture it"
    )


def test_climate_service_output_contract_matches_to_dict_top_level_keys():
    """Same live-reference rule for the top-level climate contract.

    Pins the composite's absence at the contract layer: if ``score``/``band``/
    ``interaction_bonus`` reappear in ``to_dict``, this fails rather than
    silently widening what the brief seam accepts.
    """
    from services.climate_risk_score import ClimateRiskResult

    served = ClimateRiskResult(score=1, band="Low", lat=0.0, lng=0.0).to_dict()
    # narclim is attached downstream by _fetch_climate_risk, not by to_dict;
    # lat/lng are echoed by the endpoint and not part of the brief seam.
    contract = set(ClimateRiskServiceOutput.model_fields) - {"narclim"}
    assert contract == set(served.keys()) - {"lat", "lng"}, (
        f"contract={sorted(contract)} vs served={sorted(served.keys())}"
    )
    for banned in ("score", "band", "interaction_bonus"):
        assert banned not in served
        assert banned not in ClimateRiskServiceOutput.model_fields


# ── housing SEPP eligibility ─────────────────────────────────────────────────

def test_housing_sepp_contract_locks_the_dataclass_fields():
    from services.housing_sepp_eligibility import FormEligibility

    dataclass_fields = {f.name for f in dataclasses.fields(FormEligibility)}
    assert set(HousingSeppFormOutput.model_fields) == dataclass_fields


def test_real_eligibility_output_parses_with_citations():
    rows = _load("housing_sepp_eligibility")
    assert len(rows) >= 1  # R3 Concord: 7 forms at capture time
    parsed = [HousingSeppFormOutput.model_validate(r) for r in rows]
    assert all(p.development_type for p in parsed)
    # the product's point: sourced claims — at least one row carries a citation
    assert any(p.source_clause for p in parsed)


def test_bowral_battleaxe_resolves_head_width_not_unconfirmed():
    # 38 Park Rd Bowral is a battleaxe (flag) lot: the cadastral frontage is the
    # access handle, so the raw width is null. eligibility_lot_width resolves the
    # developable HEAD width (~70 m), which the brief — and now this capture — feed
    # to the engine. The width-gated forms must therefore be ELIGIBLE on their
    # measured width, NOT mislabelled "width unconfirmed" (the pre-#720 regression
    # this fixture used to encode, which made the brief disagree with itself).
    rows = _load("housing_sepp_eligibility_bowral")
    parsed = [HousingSeppFormOutput.model_validate(r) for r in rows]
    by_type = {p.development_type: p for p in parsed}

    for dt in ("secondary_dwelling", "dual_occupancy"):
        p = by_type[dt]
        assert p.eligible is True, f"{dt} must be eligible on the resolved head width"
        assert p.unconfirmed is False
        assert "unconfirmed" not in (p.reason or "").lower()

    # No form may fail on a MISSING lot width now that the head width resolves.
    for p in parsed:
        assert not (p.reason and "width unconfirmed" in p.reason.lower()), (
            f"{p.development_type} still reports width-unconfirmed on a resolvable "
            "battleaxe lot — the capture and the brief have diverged again"
        )

    # A form whose STANDARD is absent from the dataset (e.g. manor_house) may still
    # be conservatively unconfirmed — that is a dataset gap, not a width gap, and it
    # must stay ineligible and labelled.
    for p in parsed:
        if p.unconfirmed:
            assert p.eligible is False
            assert "dataset" in (p.reason or "").lower()


# ── LEP land-use rows ────────────────────────────────────────────────────────

def test_real_lep_rows_satisfy_contract():
    payload = _load("lep_land_use_rows")
    rows = payload["rows"]
    assert len(rows) >= 10
    for row in rows:
        parsed = LepLandUseRow.model_validate(row)
        assert parsed.permissibility  # never blank
        assert parsed.zone == "R3"  # the WHERE clause the brief consumes by
    # The two classes the brief consumes MUST exist in the real vocabulary —
    # if 'permitted' were renamed, _permitted_engine_forms would silently
    # return an empty set for every lot.
    assert {"permitted", "prohibited"} <= set(payload["permissibility_vocab"])


# ── vg comparables / sales ───────────────────────────────────────────────────

def test_real_vg_comparables_round_trip_through_service_models():
    from services.vg_comparables import ComparableAnalysis

    raw = _load("vg_comparables")
    parsed = ComparableAnalysis.model_validate(raw)
    assert parsed.comparable_count > 50          # Concord R3: 117 at capture
    assert parsed.median_value and parsed.median_value > 100_000
    assert parsed.assessment_signal in ("potentially_over", "in_range", "potentially_under")
    assert parsed.comparables[0].propid and parsed.comparables[0].address


def test_real_vg_sales_round_trip():
    from services.vg_comparables import PropertySale

    rows = _load("vg_sales")
    assert len(rows) >= 10
    sales = [PropertySale.model_validate(r) for r in rows]
    assert all(s.price > 0 for s in sales)


def test_vg_contract_field_sets_locked():
    # A rename in the VG service models is a wire-in break for Phase 2 — lock it.
    from services.vg_comparables import ComparableAnalysis, ComparableProperty, PropertySale

    assert set(ComparableAnalysis.model_fields) == {
        "subject_value", "subject_area_m2", "comparable_count", "median_value",
        "mean_value", "percentile_rank", "comparables", "assessment_signal",
    }
    assert set(ComparableProperty.model_fields) == {
        "propid", "address", "zone", "area_m2", "land_value", "valuation_date",
    }
    assert set(PropertySale.model_fields) == {
        "propid", "address", "price", "area_m2", "sale_date", "price_per_m2", "is_strata",
    }


# ── terrain ──────────────────────────────────────────────────────────────────

# The exact keys _run_terrain_chain emits on every run (values may be None).
# Raster deps can't run on this box — key list verified against the service
# source; the live drift check covers the running system.
_TERRAIN_REAL_SHAPE = {
    "slope_mean_deg": 3.2, "slope_max_deg": 8.9, "aspect_dominant_deg": 145.0,
    "aspect_direction": "SE", "elevation_min_m": 12.1, "elevation_max_m": 18.4,
    "elevation_range_m": 6.3, "drainage_direction": "SE", "terrain_ruggedness": 1.02,
    "landform_class": 6, "landform_type": "slope", "daylight_fraction": 0.94,
    "hillshade_png_b64": "data:image/png;base64,iVBORw0KGgo=",
}


def test_terrain_populated_maps_every_field():
    detail = _build_terrain_detail(_TERRAIN_REAL_SHAPE)
    assert detail is not None
    assert detail.slope_mean_deg == 3.2
    assert detail.landform_type == "slope"
    assert detail.hillshade_png_b64.startswith("data:image/png")


def test_terrain_failed_is_none_not_zeroed_detail():
    assert _build_terrain_detail(None) is None  # card renders NOT_AVAILABLE + reason


def test_terrain_contract_is_the_service_class_and_shape_matches():
    if len(TerrainAnalysisDetail.model_fields) < 10:
        pytest.skip("terrain stub active (rasterio truly absent AND unstubbed)")
    assert check_drift(TerrainAnalysisDetail, _TERRAIN_REAL_SHAPE)["drift"] is False


# ── drift registry covers the slice-0 services ───────────────────────────────

def test_drift_registry_includes_slice0_services():
    from brief_contract_drift import _registry

    reg = _registry()
    assert {"flood", "bushfire", "shadow", "strata", "terrain", "climate"} <= set(reg)
