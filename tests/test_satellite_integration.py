"""
Intelligence Brief — Stage 4a Satellite Integration Tests.

Tests:
  1. _build_satellite_data assembly — each pipeline result maps correctly
  2. Bushfire detail mapping (category, BAL, cross-overlays)
  3. Flood detail mapping (EPI, JRC, WOfS, gauge, studies)
  4. Climate risk detail mapping (score, band, hazards)
  5. Granny flat detection-only mapping (structure count, SEPP eligible)
  6. Pre-DA history mapping (timeline, heritage, council)
  7. None/empty inputs produce NOT_AVAILABLE DataFields
  8. Satellite compound constraints — structure_no_da, flood_exceeds_statutory
  9. include_satellite=False → satellite=None on brief
  10. include_premium=False → pre_da_history NOT_AVAILABLE
"""
import pytest
from datetime import date

from services.intelligence_brief import (
    AssessmentManifest,
    BushfireDetail,
    ClimateDisclosureProfile,
    ConfidenceLevel,
    DataField,
    EmpiricalFinding,
    FloodDetail,
    GrannyFlatDetection,
    PreDAHistoryDetail,
    SatelliteData,
    UnavailableSource,
    _build_satellite_data,
)
from services.compound_constraints import (
    detect_staleness,
    evaluate_satellite_constraints,
    EMPIRICAL_STALENESS_THRESHOLDS,
)
from services.intelligence_brief import CompoundSeverity


# ---------------------------------------------------------------------------
# Sample pipeline outputs (matching real pipeline response shapes)
# ---------------------------------------------------------------------------

# Real run_bushfire output shape: flat keys + compliance.cross_overlays
# (bushfire_prescreen.py:557-572), NOT a nested 'rfs' dict.
SAMPLE_BUSHFIRE_RAW = {
    "address": "10 Test St",
    "outputs": {
        "is_bushfire_prone": True,
        "designation_category": "Vegetation Category 1",
        "estimated_bal_band": "BAL-29",
        "designation_guideline": "10/50 Vegetation Clearing",
        "fire_signal": "elevated",
        "compliance": {
            "cross_overlays": [{"type": "heritage", "value": "HCA"}],
        },
    },
    "confidence": "high",
    "data_sources": ["rfs_bfpl", "postgis_overlays"],
}

# Real run_flood normalised output keys (flood_truth.py:1387-1411).
SAMPLE_FLOOD_RAW = {
    "address": "10 Test St",
    "outputs": {
        "epi_flood_class": "flood_planning_area",
        "epi_flood_label": "Flood Planning Area",
        "jrc_water_occurrence_pct": 4.2,
        "dea_wofs_frequency_pct": 3.1,
        "bom_gauge_distance_km": 2.5,
        "flood_studies": [{"study": "Hawkesbury FRMSP", "depth_m": 1.2}],
    },
    "confidence": "medium",
}

SAMPLE_CLIMATE_RAW = {
    "score": 62,
    "band": "High",
    "hazards": [
        {"hazard": "flood", "raw_score": 75, "weight": 0.25, "weighted_score": 18.75, "present": True},
        {"hazard": "bushfire", "raw_score": 40, "weight": 0.20, "weighted_score": 8.0, "present": True},
    ],
    "interaction_bonus": 5.0,
    "methodology_version": "1.1",
}

SAMPLE_GRANNY_FLAT_RAW = {
    "address": "10 Test St",
    "lat": -33.88,
    "lng": 151.21,
    "prop_id": "12345",
    "lot_area_m2": 520.0,
    "sepp_eligible": True,
    "sepp_ineligible_reason": None,
    "samgeo_structure_count": 2,
    "samgeo_validated": True,
    "confirmation_required": True,
    "detected_structures": [],
}

SAMPLE_PRE_DA_RAW = {
    "address": "10 Test St",
    "lat": -33.88,
    "lon": 151.21,
    "council": "Inner West",
    "heritage_flag": True,
    "timeline": [
        {"year": 2020, "annotation": "stable", "ndvi_delta": 0.02},
        {"year": 2021, "annotation": "minor_change", "ndvi_delta": -0.08},
    ],
    "data_quality_note": "Tessera coverage from 2020 onwards only",
}


# ---------------------------------------------------------------------------
# 1. Full satellite data assembly
# ---------------------------------------------------------------------------

class TestBuildSatelliteData:
    def test_all_pipelines_populated(self):
        sat = _build_satellite_data(
            SAMPLE_BUSHFIRE_RAW, SAMPLE_FLOOD_RAW, SAMPLE_CLIMATE_RAW,
            SAMPLE_GRANNY_FLAT_RAW, SAMPLE_PRE_DA_RAW,
        )
        assert sat.bushfire.value is not None
        assert sat.bushfire.confidence == ConfidenceLevel.AUTHORITATIVE
        assert sat.flood.value is not None
        assert sat.flood.confidence == ConfidenceLevel.ESTIMATED
        assert sat.climate_disclosure.value is not None
        assert sat.granny_flat.value is not None
        assert sat.pre_da_history.value is not None

    def test_all_none_produces_not_available(self):
        sat = _build_satellite_data(None, None, None, None, None)
        assert sat.bushfire.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert sat.flood.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert sat.climate_disclosure.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert sat.granny_flat.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert sat.pre_da_history.confidence == ConfidenceLevel.NOT_AVAILABLE


# ---------------------------------------------------------------------------
# 2. Bushfire detail
# ---------------------------------------------------------------------------

class TestBushfireDetail:
    def test_category_mapped(self):
        sat = _build_satellite_data(SAMPLE_BUSHFIRE_RAW, None, None, None, None)
        bf = sat.bushfire.value
        assert bf.is_bushfire_prone is True
        assert bf.category == "Vegetation Category 1"
        assert bf.bal_estimate == "BAL-29"
        assert bf.vegetation_type == "10/50 Vegetation Clearing"
        assert bf.fire_signal == "elevated"
        assert bf.cross_overlays is not None

    def test_empty_bushfire_outputs(self):
        raw = {"outputs": {}, "confidence": "low"}
        sat = _build_satellite_data(raw, None, None, None, None)
        bf = sat.bushfire.value
        assert bf.category is None
        # No category → NOT_AVAILABLE confidence
        assert sat.bushfire.confidence == ConfidenceLevel.NOT_AVAILABLE


# ---------------------------------------------------------------------------
# 3. Flood detail
# ---------------------------------------------------------------------------

class TestFloodDetail:
    def test_all_fields_mapped(self):
        sat = _build_satellite_data(None, SAMPLE_FLOOD_RAW, None, None, None)
        fl = sat.flood.value
        assert fl.epi_flood is True
        assert fl.jrc_occurrence_pct == 4.2
        assert fl.wofs_frequency_pct == 3.1
        assert fl.bom_gauge_distance_km == 2.5
        assert len(fl.flood_studies) == 1

    def test_empty_outputs(self):
        raw = {"outputs": {}, "confidence": "low"}
        sat = _build_satellite_data(None, raw, None, None, None)
        fl = sat.flood.value
        assert fl.epi_flood is None
        assert fl.jrc_occurrence_pct is None


# ---------------------------------------------------------------------------
# 4. Climate risk detail
# ---------------------------------------------------------------------------

class TestClimateDisclosureProfile:
    def test_profile_from_legacy_climate_raw(self):
        sat = _build_satellite_data(None, None, SAMPLE_CLIMATE_RAW, None, None)
        profile = sat.climate_disclosure.value
        assert isinstance(profile, ClimateDisclosureProfile)
        assert profile.methodology_version == "2.0"
        assert profile.assessment_date is not None
        # Legacy hazard data preserved in per_hazard_detail
        assert len(profile.per_hazard_detail) == 2
        # No composite score fields
        assert not hasattr(profile, "score")
        assert not hasattr(profile, "band")

    def test_none_climate_raw(self):
        sat = _build_satellite_data(None, None, None, None, None)
        assert sat.climate_disclosure.value is None
        assert sat.climate_disclosure.confidence == ConfidenceLevel.NOT_AVAILABLE

    def test_empirical_uhi_populated(self):
        uhi = {"uhi_intensity": 6.75, "lga": "Sydney", "region": "Greater Sydney", "district": "Eastern City", "data_year": 2016}
        sat = _build_satellite_data(None, None, None, None, None, uhi_raw=uhi)
        profile = sat.climate_disclosure.value
        assert profile is not None
        assert len(profile.empirical_findings) == 1
        assert profile.empirical_findings[0].hazard == "urban_heat_island"
        assert profile.empirical_findings[0].value == 6.75

    def test_empirical_arr_populated(self):
        arr = {"durations_min": [60], "aep_pct": ["1.0"], "depths_mm": [[85.3]], "ifd_1pct_60min_mm": 85.3}
        sat = _build_satellite_data(None, None, None, None, None, arr_raw=arr)
        profile = sat.climate_disclosure.value
        assert len(profile.empirical_findings) == 1
        assert profile.empirical_findings[0].hazard == "extreme_rainfall"
        assert profile.empirical_findings[0].value == 85.3
        assert profile.empirical_findings[0].unit == "mm_1pct_aep_60min"

    def test_empirical_firms_with_detections(self):
        firms = {"hotspot_count": 3, "detections": [{"latitude": -33.87}], "search_days": 10, "search_radius_km": 0.5}
        sat = _build_satellite_data(None, None, None, None, None, firms_raw=firms)
        profile = sat.climate_disclosure.value
        assert len(profile.empirical_findings) == 1
        assert profile.empirical_findings[0].hazard == "active_fire"
        assert profile.empirical_findings[0].value == 3.0

    def test_empirical_firms_zero_detections_excluded(self):
        """FIRMS queried but 0 detections — profile created, no fire empirical finding."""
        firms = {"hotspot_count": 0, "detections": [], "search_days": 10, "search_radius_km": 0.5}
        sat = _build_satellite_data(None, None, None, None, None, firms_raw=firms)
        profile = sat.climate_disclosure.value
        assert profile is not None  # profile created (FIRMS was queried)
        assert len(profile.empirical_findings) == 0  # but no fire finding added

    def test_empirical_all_three_combined(self):
        uhi = {"uhi_intensity": 4.2, "lga": "Parramatta", "data_year": 2016}
        arr = {"ifd_1pct_60min_mm": 92.1, "durations_min": [60], "aep_pct": ["1.0"], "depths_mm": [[92.1]]}
        firms = {"hotspot_count": 2, "detections": [{}], "search_days": 10, "search_radius_km": 0.5}
        sat = _build_satellite_data(None, None, SAMPLE_CLIMATE_RAW, None, None, uhi_raw=uhi, arr_raw=arr, firms_raw=firms)
        profile = sat.climate_disclosure.value
        assert len(profile.empirical_findings) == 3
        hazards = [f.hazard for f in profile.empirical_findings]
        assert "urban_heat_island" in hazards
        assert "extreme_rainfall" in hazards
        assert "active_fire" in hazards
        # Legacy hazard detail still present
        assert len(profile.per_hazard_detail) == 2

    def test_empirical_only_no_climate_raw(self):
        """Empirical data alone triggers profile creation even without climate_raw."""
        uhi = {"uhi_intensity": 3.5, "lga": "Test", "data_year": 2016}
        sat = _build_satellite_data(None, None, None, None, None, uhi_raw=uhi)
        profile = sat.climate_disclosure.value
        assert profile is not None
        assert len(profile.per_hazard_detail) == 0  # no climate_raw
        assert len(profile.empirical_findings) == 1


# ---------------------------------------------------------------------------
# 4b. Manifest population
# ---------------------------------------------------------------------------

class TestAssessmentManifest:
    def test_all_sources_succeed(self):
        uhi = {"uhi_intensity": 4.2, "lga": "Test", "data_year": 2016}
        arr = {"ifd_1pct_60min_mm": 85.0, "durations_min": [60], "aep_pct": ["1.0"], "depths_mm": [[85.0]]}
        firms = {"hotspot_count": 0, "detections": [], "search_days": 10, "search_radius_km": 0.5}
        climate_with_narclim = {**SAMPLE_CLIMATE_RAW, "narclim": {"hot_days_delta_2050": 4.3}}
        sat = _build_satellite_data(None, None, climate_with_narclim, None, None, uhi_raw=uhi, arr_raw=arr, firms_raw=firms)
        m = sat.climate_disclosure.value.manifest
        assert m.sources_queried == 5  # UHI + ARR + FIRMS + legacy climate + NARCLIM
        assert m.sources_successful == 5
        assert m.coverage_pct == 100.0
        assert len(m.sources_unavailable) == 0

    def test_partial_failure_tracked(self):
        """UHI succeeds, ARR and FIRMS fail — manifest tracks unavailable sources."""
        uhi = {"uhi_intensity": 5.0, "lga": "Test", "data_year": 2016}
        sat = _build_satellite_data(None, None, None, None, None, uhi_raw=uhi, arr_raw=None, firms_raw=None)
        m = sat.climate_disclosure.value.manifest
        assert m.sources_queried == 3  # UHI + ARR + FIRMS (no legacy climate)
        assert m.sources_successful == 1
        assert m.coverage_pct == pytest.approx(33.3, abs=0.1)
        assert len(m.sources_unavailable) == 2
        unavail_sources = [u.source for u in m.sources_unavailable]
        assert "arr_data_hub" in unavail_sources
        assert "nasa_firms" in unavail_sources

    def test_all_fail_manifest_still_present(self):
        """All empirical sources fail but FIRMS dict is truthy (hotspot_count 0) — FIRMS counts as success."""
        firms = {"hotspot_count": 0, "detections": [], "search_days": 10, "search_radius_km": 0.5}
        sat = _build_satellite_data(None, None, None, None, None, firms_raw=firms)
        m = sat.climate_disclosure.value.manifest
        assert m.sources_queried == 3
        assert m.sources_successful == 1  # FIRMS succeeded (returned data, just 0 hotspots)

    def test_uhi_quality_note(self):
        uhi = {"uhi_intensity": 3.0, "lga": "Test", "data_year": 2016}
        sat = _build_satellite_data(None, None, None, None, None, uhi_raw=uhi)
        m = sat.climate_disclosure.value.manifest
        assert any("2016" in n for n in m.data_quality_notes)

    def test_no_sources_no_manifest(self):
        """No climate/empirical data → no profile, no manifest."""
        sat = _build_satellite_data(None, None, None, None, None)
        assert sat.climate_disclosure.value is None


# ---------------------------------------------------------------------------
# 4c. Empirical staleness detection
# ---------------------------------------------------------------------------

class TestEmpiricalStaleness:
    def test_old_uhi_flagged_stale(self):
        """UHI data_date='2016' should be flagged stale (>3650 days old by 2027)."""
        uhi = {"uhi_intensity": 5.0, "lga": "Test", "data_year": 2016}
        sat = _build_satellite_data(None, None, None, None, None, uhi_raw=uhi)
        profile = sat.climate_disclosure.value
        finding = profile.empirical_findings[0]
        # Manually check: 2016-01-01 to today should be > 3650 days
        from datetime import datetime
        age = (date.today() - date(2016, 1, 1)).days
        if age > EMPIRICAL_STALENESS_THRESHOLDS["urban_heat_island"]:
            warnings = detect_staleness(sat)
            # #745 D7-7: the warning is now user-facing prose, not a slug/log line
            assert any("urban heat island" in w and "years old" in w for w in warnings)
            assert finding.confidence == ConfidenceLevel.STALE
        else:
            # UHI data not yet stale (before 2026) — verify no warning
            warnings = detect_staleness(sat)
            assert not any("urban_heat_island" in w for w in warnings)

    def test_fresh_arr_not_flagged(self):
        """Today's ARR data should not be flagged stale."""
        arr = {"ifd_1pct_60min_mm": 80.0, "durations_min": [60], "aep_pct": ["1.0"], "depths_mm": [[80.0]]}
        sat = _build_satellite_data(None, None, None, None, None, arr_raw=arr)
        warnings = detect_staleness(sat)
        assert not any("extreme_rainfall" in w for w in warnings)


# ---------------------------------------------------------------------------
# 5. Granny flat detection-only
# ---------------------------------------------------------------------------

class TestGrannyFlatDetection:
    def test_detection_mapped(self):
        sat = _build_satellite_data(None, None, None, SAMPLE_GRANNY_FLAT_RAW, None)
        gf = sat.granny_flat.value
        assert gf.structure_count == 2
        assert gf.sepp_eligible is True
        assert gf.confirmation_required is True

    def test_ineligible_lot(self):
        raw = {**SAMPLE_GRANNY_FLAT_RAW, "sepp_eligible": False, "sepp_ineligible_reason": "Lot too small"}
        sat = _build_satellite_data(None, None, None, raw, None)
        gf = sat.granny_flat.value
        assert gf.sepp_eligible is False
        assert gf.sepp_ineligible_reason == "Lot too small"


# ---------------------------------------------------------------------------
# 6. Pre-DA history
# ---------------------------------------------------------------------------

class TestPreDAHistory:
    def test_timeline_mapped(self):
        sat = _build_satellite_data(None, None, None, None, SAMPLE_PRE_DA_RAW)
        pd = sat.pre_da_history.value
        assert len(pd.timeline) == 2
        assert pd.heritage_flag is True
        assert pd.council == "Inner West"
        assert pd.data_quality_note is not None


# ---------------------------------------------------------------------------
# 7. Satellite compound constraints
# ---------------------------------------------------------------------------

class TestSatelliteCompoundConstraints:
    def test_structure_no_da_record(self):
        """Multiple structures detected, no secondary dwelling DA → info constraint."""
        constraints = evaluate_satellite_constraints(
            granny_flat_structures=3,
            nearby_das=[
                {"description": "Alterations to dwelling", "dev_type": "dwelling"},
            ],
            flood_epi=False,
            flood_jrc_pct=None,
            flood_wofs_pct=None,
        )
        match = [c for c in constraints if c.id == "structure_no_da_record"]
        assert len(match) == 1
        assert "3 structures" in match[0].description
        assert match[0].severity == CompoundSeverity.INFO

    def test_structure_with_sd_da_no_constraint(self):
        """Structures detected but secondary dwelling DA exists → no constraint."""
        constraints = evaluate_satellite_constraints(
            granny_flat_structures=2,
            nearby_das=[
                {"description": "Secondary dwelling", "dev_type": "secondary_dwelling"},
            ],
            flood_epi=False,
            flood_jrc_pct=None,
            flood_wofs_pct=None,
        )
        match = [c for c in constraints if c.id == "structure_no_da_record"]
        assert len(match) == 0

    def test_single_structure_no_constraint(self):
        """Only 1 structure (main dwelling) → no constraint."""
        constraints = evaluate_satellite_constraints(
            granny_flat_structures=1,
            nearby_das=[],
            flood_epi=False,
            flood_jrc_pct=None,
            flood_wofs_pct=None,
        )
        match = [c for c in constraints if c.id == "structure_no_da_record"]
        assert len(match) == 0

    def test_flood_exceeds_statutory(self):
        """JRC > 2% but no EPI flood → warning."""
        constraints = evaluate_satellite_constraints(
            granny_flat_structures=None,
            nearby_das=[],
            flood_epi=False,
            flood_jrc_pct=5.3,
            flood_wofs_pct=0.5,
        )
        match = [c for c in constraints if c.id == "flood_evidence_exceeds_statutory"]
        assert len(match) == 1
        assert match[0].severity == CompoundSeverity.WARNING

    def test_flood_exceeds_wofs_only(self):
        """WOfS > 2% but no JRC, no EPI → warning."""
        constraints = evaluate_satellite_constraints(
            granny_flat_structures=None,
            nearby_das=[],
            flood_epi=False,
            flood_jrc_pct=0.5,
            flood_wofs_pct=3.8,
        )
        match = [c for c in constraints if c.id == "flood_evidence_exceeds_statutory"]
        assert len(match) == 1

    def test_flood_with_epi_no_constraint(self):
        """JRC > 2% but EPI flood already True → no constraint (statutory already covers it)."""
        constraints = evaluate_satellite_constraints(
            granny_flat_structures=None,
            nearby_das=[],
            flood_epi=True,
            flood_jrc_pct=5.0,
            flood_wofs_pct=4.0,
        )
        match = [c for c in constraints if c.id == "flood_evidence_exceeds_statutory"]
        assert len(match) == 0

    def test_no_satellite_data_no_constraints(self):
        """All None → no constraints."""
        constraints = evaluate_satellite_constraints(
            granny_flat_structures=None,
            nearby_das=[],
            flood_epi=False,
            flood_jrc_pct=None,
            flood_wofs_pct=None,
        )
        assert len(constraints) == 0
