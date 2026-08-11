"""
Compound Constraints — Stage 3 Tests.

Tests:
  1. Heritage HCA + Bushfire (landscape → WARNING, general → INFO)
  2. Heritage item + Flood → Heritage NSW concurrence warning
  3. TOD + Heritage HCA → density bonus restriction
  4. Marginal lot size → survey warning
  5. Flood EPI + Heritage item → floor level conflict
  6. Fix B — R3/R4/B1/B2 zone → higher density advisory
  7. Fix C — DA-shadow interaction (multi-storey DA within 100m)
  8. No constraints fire for clean property
  9. Staleness detection
  10. Gap verify_url enrichment
"""
import pytest
from datetime import date, timedelta
from unittest.mock import patch

from services.compound_constraints import (
    evaluate_compound_constraints,
    detect_staleness,
    enrich_gaps_with_verify_url,
    STALENESS_THRESHOLDS,
)
from services.intelligence_brief import (
    CompoundConstraint,
    CompoundSeverity,
    ConfidenceLevel,
    DataField,
    GapEntry,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _base_kwargs(**overrides):
    """Default kwargs for evaluate_compound_constraints — clean property, no constraints."""
    defaults = dict(
        heritage_items=[],
        heritage_hca=[],
        heritage_postgis=None,
        bushfire_designation=None,
        flood_epi=False,
        tod_area=False,
        lot_area_m2=600.0,
        min_lot_size_m2=450.0,
        zone_code="R2",
        nearby_das=[],
        overlays=[],
    )
    defaults.update(overrides)
    return defaults


# ---------------------------------------------------------------------------
# 1. Heritage HCA + Bushfire — landscape → WARNING
# ---------------------------------------------------------------------------

class TestHeritageHCABushfire:
    def test_landscape_heritage_high_severity(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(
            heritage_hca=["HCA - Petersham South"],
            bushfire_designation="Bushfire Prone Land",
            overlays=[{"layer_type": "heritage", "value": "Conservation Area - Landscape"}],
        ))
        match = [c for c in constraints if c.id == "heritage_hca_bushfire_vegetation"]
        assert len(match) == 1
        assert match[0].severity == CompoundSeverity.WARNING
        assert "10/50" in match[0].description

    def test_garden_element_in_postgis(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(
            heritage_hca=["HCA - Dulwich Hill"],
            bushfire_designation="Bushfire Prone Land",
            heritage_postgis={"raw": [{"heritage_element": "garden and setting"}], "has_heritage": True},
            overlays=[{"layer_type": "heritage", "value": "Conservation Area - General"}],
        ))
        match = [c for c in constraints if c.id == "heritage_hca_bushfire_vegetation"]
        assert len(match) == 1

    def test_general_heritage_info_severity(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(
            heritage_hca=["HCA - General"],
            bushfire_designation="Bushfire Prone Land",
            overlays=[{"layer_type": "heritage", "value": "Conservation Area - General"}],
        ))
        match = [c for c in constraints if c.id == "heritage_hca_bushfire_general"]
        assert len(match) == 1
        assert match[0].severity == CompoundSeverity.INFO

    def test_no_bushfire_no_constraint(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(
            heritage_hca=["HCA - Petersham South"],
            bushfire_designation=None,
        ))
        heritage_bushfire = [c for c in constraints if "bushfire" in c.id]
        assert len(heritage_bushfire) == 0


# ---------------------------------------------------------------------------
# 2. Heritage item + Flood
# ---------------------------------------------------------------------------

class TestHeritageItemFlood:
    def test_heritage_item_flood_fires(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(
            heritage_items=["St Stephen's Church"],
            flood_epi=True,
        ))
        match = [c for c in constraints if c.id == "heritage_item_flood"]
        assert len(match) == 1
        assert "Heritage NSW concurrence" in match[0].description

    def test_no_flood_no_constraint(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(
            heritage_items=["St Stephen's Church"],
            flood_epi=False,
        ))
        match = [c for c in constraints if c.id == "heritage_item_flood"]
        assert len(match) == 0


# ---------------------------------------------------------------------------
# 3. TOD + Heritage HCA
# ---------------------------------------------------------------------------

class TestTODHeritage:
    def test_tod_heritage_fires(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(
            tod_area=True,
            heritage_hca=["HCA - Petersham South"],
        ))
        match = [c for c in constraints if c.id == "tod_heritage_hca"]
        assert len(match) == 1
        assert "density bonus" in match[0].description

    def test_tod_no_heritage_no_constraint(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(
            tod_area=True,
            heritage_hca=[],
        ))
        match = [c for c in constraints if c.id == "tod_heritage_hca"]
        assert len(match) == 0


# ---------------------------------------------------------------------------
# 4. Marginal lot size
# ---------------------------------------------------------------------------

class TestMarginalLotSize:
    def test_marginal_fires(self):
        """Lot area 470m² with min 450m² → within 10%, should warn."""
        constraints = evaluate_compound_constraints(**_base_kwargs(
            lot_area_m2=470.0,
            min_lot_size_m2=450.0,
        ))
        match = [c for c in constraints if c.id == "marginal_lot_size"]
        assert len(match) == 1
        assert "survey" in match[0].caveat.lower()

    def test_comfortable_margin_no_constraint(self):
        """Lot area 600m² with min 450m² → well above 10%, no warning."""
        constraints = evaluate_compound_constraints(**_base_kwargs(
            lot_area_m2=600.0,
            min_lot_size_m2=450.0,
        ))
        match = [c for c in constraints if c.id == "marginal_lot_size"]
        assert len(match) == 0

    def test_undersized_no_constraint(self):
        """Lot below minimum doesn't trigger marginal warning (that's a different issue)."""
        constraints = evaluate_compound_constraints(**_base_kwargs(
            lot_area_m2=400.0,
            min_lot_size_m2=450.0,
        ))
        match = [c for c in constraints if c.id == "marginal_lot_size"]
        assert len(match) == 0


# ---------------------------------------------------------------------------
# 5. Flood EPI + Heritage item (floor level)
# ---------------------------------------------------------------------------

class TestFloodHeritageFloorLevel:
    def test_fires(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(
            flood_epi=True,
            heritage_items=["Heritage Item X"],
        ))
        match = [c for c in constraints if c.id == "flood_heritage_floor_level"]
        assert len(match) == 1


# ---------------------------------------------------------------------------
# 6. Fix B — Zone higher density advisory
# ---------------------------------------------------------------------------

class TestFixBZoneAdvisory:
    def test_r3_zone_fires(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(zone_code="R3"))
        match = [c for c in constraints if c.id == "zone_higher_density_advisory"]
        assert len(match) == 1
        assert "R3" in match[0].description
        assert match[0].severity == CompoundSeverity.INFO

    def test_r4_zone_fires(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(zone_code="R4"))
        match = [c for c in constraints if c.id == "zone_higher_density_advisory"]
        assert len(match) == 1

    def test_e1_zone_fires(self):
        """DQ-30 (.claude/DATA_QUALITY_TRACKER.md): was tested against 'B1', a
        retired NSW zone code (April 2023 Employment Zones Reform) that never
        appears as a live property's current zone — the check silently never
        fired for real commercial-zoned properties. Real current equivalent
        is E1."""
        constraints = evaluate_compound_constraints(**_base_kwargs(zone_code="E1"))
        match = [c for c in constraints if c.id == "zone_higher_density_advisory"]
        assert len(match) == 1

    def test_r2_zone_does_not_fire(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(zone_code="R2"))
        match = [c for c in constraints if c.id == "zone_higher_density_advisory"]
        assert len(match) == 0

    def test_mu1_zone_fires(self):
        constraints = evaluate_compound_constraints(**_base_kwargs(zone_code="MU1"))
        match = [c for c in constraints if c.id == "zone_higher_density_advisory"]
        assert len(match) == 1


# ---------------------------------------------------------------------------
# 7. Fix C — DA-shadow interaction
# ---------------------------------------------------------------------------

class TestFixCDAShadow:
    def test_approved_rfb_within_100m(self):
        das = [
            {"number": "DA/2025/0100", "distance_m": 80, "status": "Approved",
             "description": "Demolition and construction of residential flat building",
             "dev_type": "RFB"},
        ]
        constraints = evaluate_compound_constraints(**_base_kwargs(nearby_das=das))
        match = [c for c in constraints if c.id == "da_shadow_interaction"]
        assert len(match) == 1
        assert "DA/2025/0100" in match[0].description
        assert match[0].severity == CompoundSeverity.WARNING

    def test_assessed_multi_storey_fires(self):
        das = [
            {"number": "DA/2025/0200", "distance_m": 50, "status": "Under Assessment",
             "description": "New 4 storey mixed use building"},
        ]
        constraints = evaluate_compound_constraints(**_base_kwargs(nearby_das=das))
        match = [c for c in constraints if c.id == "da_shadow_interaction"]
        assert len(match) == 1

    def test_da_beyond_100m_no_constraint(self):
        das = [
            {"number": "DA/2025/0300", "distance_m": 150, "status": "Approved",
             "description": "Residential flat building"},
        ]
        constraints = evaluate_compound_constraints(**_base_kwargs(nearby_das=das))
        match = [c for c in constraints if c.id == "da_shadow_interaction"]
        assert len(match) == 0

    def test_single_dwelling_no_constraint(self):
        das = [
            {"number": "DA/2025/0400", "distance_m": 50, "status": "Approved",
             "description": "Alterations and additions to dwelling"},
        ]
        constraints = evaluate_compound_constraints(**_base_kwargs(nearby_das=das))
        match = [c for c in constraints if c.id == "da_shadow_interaction"]
        assert len(match) == 0

    def test_refused_da_no_constraint(self):
        das = [
            {"number": "DA/2025/0500", "distance_m": 50, "status": "Refused",
             "description": "New 6 storey apartment building"},
        ]
        constraints = evaluate_compound_constraints(**_base_kwargs(nearby_das=das))
        match = [c for c in constraints if c.id == "da_shadow_interaction"]
        assert len(match) == 0


# ---------------------------------------------------------------------------
# 8. Clean property — no constraints
# ---------------------------------------------------------------------------

class TestCleanProperty:
    def test_no_constraints(self):
        constraints = evaluate_compound_constraints(**_base_kwargs())
        assert len(constraints) == 0


# ---------------------------------------------------------------------------
# 9. Staleness detection
# ---------------------------------------------------------------------------

class TestStaleness:
    def test_stale_dcp_detected(self):
        old_date = (date.today() - timedelta(days=200)).isoformat()
        field = DataField(value="test", confidence=ConfidenceLevel.EXTRACTED, source="plotdetect_dcp", as_at=old_date)
        # Wrap in a minimal model-like structure
        from pydantic import BaseModel

        class FakeBrief(BaseModel):
            dcp: DataField[str]

        brief = FakeBrief(dcp=field)
        warnings = detect_staleness(brief)
        assert len(warnings) == 1
        assert "plotdetect_dcp" in warnings[0]
        assert brief.dcp.confidence == ConfidenceLevel.STALE

    def test_fresh_data_no_warning(self):
        today = date.today().isoformat()
        field = DataField(value="test", confidence=ConfidenceLevel.EXTRACTED, source="plotdetect_dcp", as_at=today)

        from pydantic import BaseModel

        class FakeBrief(BaseModel):
            dcp: DataField[str]

        brief = FakeBrief(dcp=field)
        warnings = detect_staleness(brief)
        assert len(warnings) == 0
        assert brief.dcp.confidence == ConfidenceLevel.EXTRACTED

    def test_not_available_skipped(self):
        field = DataField(value=None, confidence=ConfidenceLevel.NOT_AVAILABLE, source="plotdetect_dcp", as_at="2020-01-01")

        from pydantic import BaseModel

        class FakeBrief(BaseModel):
            dcp: DataField[str]

        brief = FakeBrief(dcp=field)
        warnings = detect_staleness(brief)
        assert len(warnings) == 0


# ---------------------------------------------------------------------------
# 10. Gap verify_url enrichment
# ---------------------------------------------------------------------------

class TestGapVerifyUrl:
    def test_dcp_gap_gets_url(self):
        gaps = [GapEntry(field="dcp_controls.controls", reason="DCP controls not yet extracted for 'marrickville'")]
        enriched = enrich_gaps_with_verify_url(gaps, "marrickville")
        assert enriched[0].verify_url is not None
        assert "innerwest" in enriched[0].verify_url

    def test_valuation_gap_gets_url(self):
        gaps = [GapEntry(field="economics.land_value", reason="VG API timeout")]
        enriched = enrich_gaps_with_verify_url(gaps, None)
        assert enriched[0].verify_url is not None
        assert "valuergeneral" in enriched[0].verify_url

    def test_unknown_gap_no_url(self):
        gaps = [GapEntry(field="some_field", reason="Unknown error")]
        enriched = enrich_gaps_with_verify_url(gaps, None)
        assert enriched[0].verify_url is None
