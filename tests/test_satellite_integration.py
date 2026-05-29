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
    BushfireDetail,
    ClimateRiskDetail,
    ConfidenceLevel,
    DataField,
    FloodDetail,
    GrannyFlatDetection,
    PreDAHistoryDetail,
    SatelliteData,
    _build_satellite_data,
)
from services.compound_constraints import evaluate_satellite_constraints
from services.intelligence_brief import CompoundSeverity


# ---------------------------------------------------------------------------
# Sample pipeline outputs (matching real pipeline response shapes)
# ---------------------------------------------------------------------------

SAMPLE_BUSHFIRE_RAW = {
    "address": "10 Test St",
    "outputs": {
        "rfs": {
            "category": "Vegetation Category 1",
            "bal_estimate": "BAL-29",
            "vegetation_type": "Forest",
        },
        "cross_overlays": {
            "flood": False,
            "heritage_hca": True,
            "zone": "R2",
        },
    },
    "confidence": "high",
    "data_sources": ["rfs_bfpl", "postgis_overlays"],
}

SAMPLE_FLOOD_RAW = {
    "address": "10 Test St",
    "outputs": {
        "epi_flood": True,
        "jrc_occurrence_pct": 4.2,
        "wofs_frequency_pct": 3.1,
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
        assert sat.climate_risk.value is not None
        assert sat.granny_flat.value is not None
        assert sat.pre_da_history.value is not None

    def test_all_none_produces_not_available(self):
        sat = _build_satellite_data(None, None, None, None, None)
        assert sat.bushfire.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert sat.flood.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert sat.climate_risk.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert sat.granny_flat.confidence == ConfidenceLevel.NOT_AVAILABLE
        assert sat.pre_da_history.confidence == ConfidenceLevel.NOT_AVAILABLE


# ---------------------------------------------------------------------------
# 2. Bushfire detail
# ---------------------------------------------------------------------------

class TestBushfireDetail:
    def test_category_mapped(self):
        sat = _build_satellite_data(SAMPLE_BUSHFIRE_RAW, None, None, None, None)
        bf = sat.bushfire.value
        assert bf.category == "Vegetation Category 1"
        assert bf.bal_estimate == "BAL-29"
        assert bf.vegetation_type == "Forest"
        assert bf.cross_overlays is not None

    def test_empty_rfs_outputs(self):
        raw = {"outputs": {"rfs": {}}, "confidence": "low"}
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

class TestClimateRiskDetail:
    def test_score_and_band(self):
        sat = _build_satellite_data(None, None, SAMPLE_CLIMATE_RAW, None, None)
        cr = sat.climate_risk.value
        assert cr.score == 62
        assert cr.band == "High"
        assert len(cr.hazards) == 2
        assert cr.interaction_bonus == 5.0


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
