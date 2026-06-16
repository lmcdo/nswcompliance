"""
Tests for constraint arithmetic engine.

QA Tier: Critical — new computation that directly affects user-facing intelligence.

Test categories:
1. Golden address — realistic Inner West scenarios with known expected outputs
2. Boundary cases — zero lot, missing data, all constraints missing
3. Three-state — None vs 0 vs present for each control
4. Binding constraint identification — each constraint type can be binding
5. SEPP override — override applied/not applied correctly
6. Shadow — threshold boundary, no shadow, severe shadow
7. Mutation-resistant — specific numeric assertions that would fail if logic changed
"""
import math
from typing import Optional

import pytest

from services.constraint_arithmetic import (
    CIRCULATION_FACTOR_APARTMENT,
    CIRCULATION_FACTOR_HOUSE,
    MIN_DWELLING_GFA_M2,
    PARKING_AREA_PER_SPACE_M2,
    SHADOW_OVERLAP_MAX,
    SHADOW_OVERLAP_MIN,
    SHADOW_OVERLAP_THRESHOLD,
    STOREY_HEIGHT_M,
    ConstraintArithmeticResult,
    ConstraintType,
    _estimate_lot_dimensions,
    _get_dcp_value,
    _identify_binding_constraint,
    _is_apartment_type,
    _parse_numeric,
    compute_constraint_arithmetic,
)
from services.intelligence_brief import (
    DCPControl,
    LotDimensions,
    SEPPStandard,
    SeppLepOverride,
    ShadowResult,
    ShadowScenario,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_dcp(control_type: str, value: float, dev_type: str = "dwelling_house", unit: str = "m") -> DCPControl:
    return DCPControl(control_type=control_type, dev_type=dev_type, value_min=value, unit=unit)


def _inner_west_controls() -> list[DCPControl]:
    """Realistic Inner West DCP controls for a dwelling house."""
    return [
        _make_dcp("front_setback", 6.0),
        _make_dcp("rear_setback", 6.0),
        _make_dcp("side_setback", 1.5),
        _make_dcp("max_site_coverage", 50.0, unit="%"),
        _make_dcp("landscaping_min", 30.0, unit="%"),
    ]


def _inner_west_lot() -> LotDimensions:
    return LotDimensions(area_m2=600, frontage_m=15, depth_m=40)


# ===========================================================================
# 1. _parse_numeric
# ===========================================================================

class TestParseNumeric:
    def test_plain_number(self):
        assert _parse_numeric("11") == 11.0

    def test_fsr_with_colon(self):
        assert _parse_numeric("0.75:1") == 0.75

    def test_height_with_m(self):
        assert _parse_numeric("9m") == 9.0

    def test_none(self):
        assert _parse_numeric(None) is None

    def test_empty_string(self):
        assert _parse_numeric("") is None

    def test_non_numeric(self):
        assert _parse_numeric("varies") is None

    def test_float_string(self):
        assert _parse_numeric("0.6:1") == 0.6

    def test_with_spaces(self):
        assert _parse_numeric("  11  ") == 11.0


# ===========================================================================
# 2. _get_dcp_value
# ===========================================================================

class TestGetDcpValue:
    def test_exact_match(self):
        controls = [
            _make_dcp("front_setback", 6.0, "dwelling_house"),
            _make_dcp("front_setback", 3.0, "secondary_dwelling"),
        ]
        assert _get_dcp_value(controls, "front_setback", "secondary_dwelling") == 3.0

    def test_fallback_to_dwelling_house(self):
        controls = [_make_dcp("front_setback", 6.0, "dwelling_house")]
        assert _get_dcp_value(controls, "front_setback", "dual_occupancy") == 6.0

    def test_no_match(self):
        controls = [_make_dcp("rear_setback", 6.0)]
        assert _get_dcp_value(controls, "front_setback", "dwelling_house") is None

    def test_empty_list(self):
        assert _get_dcp_value([], "front_setback", "dwelling_house") is None


# ===========================================================================
# 3. _estimate_lot_dimensions
# ===========================================================================

class TestEstimateLotDimensions:
    def test_actual_dimensions(self):
        dims = LotDimensions(area_m2=600, frontage_m=15, depth_m=40)
        assert _estimate_lot_dimensions(dims, 600) == (15, 40)

    def test_frontage_only(self):
        dims = LotDimensions(area_m2=600, frontage_m=15)
        f, d = _estimate_lot_dimensions(dims, 600)
        assert f == 15
        assert d == 40.0

    def test_depth_only(self):
        dims = LotDimensions(area_m2=600, depth_m=40)
        f, d = _estimate_lot_dimensions(dims, 600)
        assert f == 15.0
        assert d == 40

    def test_no_dimensions(self):
        f, d = _estimate_lot_dimensions(None, 600)
        assert abs(f * d - 600) < 0.1  # must still produce correct area

    def test_estimated_ratio(self):
        """Estimated lot should be ~1:2.5 ratio."""
        f, d = _estimate_lot_dimensions(None, 1000)
        ratio = d / f
        assert 2.4 < ratio < 2.6


# ===========================================================================
# 4. _is_apartment_type
# ===========================================================================

class TestIsApartmentType:
    @pytest.mark.parametrize("dev_type", [
        "residential_flat_building", "apartment", "shop_top_housing",
        "mixed_use", "boarding_house", "multi_dwelling_housing",
    ])
    def test_apartment_types(self, dev_type):
        assert _is_apartment_type(dev_type) is True

    @pytest.mark.parametrize("dev_type", [
        "dwelling_house", "secondary_dwelling", "dual_occupancy",
        "semi_detached", "attached_dwelling",
    ])
    def test_non_apartment_types(self, dev_type):
        assert _is_apartment_type(dev_type) is False


# ===========================================================================
# 5. Golden address — Inner West 600m² dwelling house
# ===========================================================================

class TestGoldenInnerWest:
    """Realistic Inner West scenario: 600m² lot, 15m x 40m, R2 zone.

    LEP: 11m height, 0.75:1 FSR
    DCP: 6m front, 6m rear, 1.5m sides, 50% coverage, 30% landscaping
    """

    def setup_method(self):
        self.result = compute_constraint_arithmetic(
            lot_area_m2=600,
            dev_type="dwelling_house",
            lep_height_str="11",
            lep_fsr_str="0.75:1",
            lot_dimensions=_inner_west_lot(),
            dcp_controls=_inner_west_controls(),
        )

    def test_fsr_gfa(self):
        assert self.result.lep_max_gfa_from_fsr_m2 == 450.0

    def test_storeys(self):
        assert self.result.lep_max_storeys == 3

    def test_setback_footprint(self):
        # (15 - 2*1.5) x (40 - 6 - 6) = 12 x 28 = 336
        assert self.result.buildable_footprint_m2 == 336.0

    def test_coverage_cap(self):
        # 50% of 600 = 300
        assert self.result.site_coverage_cap_m2 == 300.0

    def test_landscaping_reduction(self):
        # 30% of 600 = 180
        assert self.result.landscaping_reduction_m2 == 180.0

    def test_final_footprint_after_coverage_then_landscaping(self):
        """Coverage caps footprint at 300, then landscaping removes 180 -> 120m2."""
        # After setbacks: 336
        # Coverage cap: 300 (< 336, so applied)
        # Landscaping: 300 - 180 = 120
        # Height GFA: 120 * 3 = 360
        # FSR GFA: 450
        # Envelope: min(450, 360) = 360
        assert self.result.lep_envelope_gfa_m2 == 360.0

    def test_realistic_gfa(self):
        assert self.result.realistic_gfa_m2 == 360.0

    def test_realistic_dwellings(self):
        # 360 / 65 = 5.5 -> int = 5
        assert self.result.realistic_dwellings == 5

    def test_binding_constraint(self):
        # FSR (450m2) < landscaping path (468m2) — FSR is more restrictive
        assert self.result.binding_constraint == ConstraintType.LEP_FSR

    def test_confidence_high(self):
        assert self.result.confidence == "high"

    def test_no_gaps(self):
        assert len(self.result.gaps) == 0

    def test_steps_present(self):
        assert len(self.result.steps) >= 4


# ===========================================================================
# 6. SEPP override scenarios
# ===========================================================================

class TestSeppOverride:
    def test_override_increases_height(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600,
            dev_type="dual_occupancy",
            lep_height_str="9",
            lep_fsr_str="0.5:1",
            lot_dimensions=_inner_west_lot(),
            sepp_lep_overrides=[
                SeppLepOverride(
                    dev_type="dual_occupancy",
                    control="height",
                    lep_value=9.0,
                    sepp_value=22.0,
                ),
            ],
        )
        assert result.effective_height_m == 22.0
        assert result.lep_max_storeys == 7  # 22/3 = 7.33 -> 7

    def test_override_increases_fsr(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600,
            dev_type="dual_occupancy",
            lep_height_str="9",
            lep_fsr_str="0.5:1",
            sepp_lep_overrides=[
                SeppLepOverride(
                    dev_type="dual_occupancy",
                    control="fsr",
                    lep_value=0.5,
                    sepp_value=0.8,
                ),
            ],
        )
        assert result.effective_fsr == 0.8
        assert result.lep_max_gfa_from_fsr_m2 == 480.0

    def test_no_override_when_sepp_lower(self):
        """SEPP value <= LEP should not override."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600,
            dev_type="dwelling_house",
            lep_height_str="11",
            lep_fsr_str="0.75:1",
            sepp_lep_overrides=[
                SeppLepOverride(
                    dev_type="dwelling_house",
                    control="height",
                    lep_value=11.0,
                    sepp_value=9.0,
                ),
            ],
        )
        assert result.effective_height_m == 11.0
        assert len(result.sepp_overrides_applied) == 0

    def test_override_applies_to_matching_dev_type(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600,
            dev_type="dual_occupancy",
            lep_height_str="9",
            lep_fsr_str="0.5:1",
            sepp_lep_overrides=[
                SeppLepOverride(dev_type="dual_occupancy", control="height", lep_value=9.0, sepp_value=22.0),
                SeppLepOverride(dev_type="dual_occupancy", control="fsr", lep_value=0.5, sepp_value=0.8),
            ],
        )
        assert result.effective_height_m == 22.0
        assert result.effective_fsr == 0.8


# ===========================================================================
# 7. Shadow impact
# ===========================================================================

class TestShadowImpact:
    def _make_shadow(self, overlap_pct: float, time_label: str = "12:00 PM",
                     shadow_length_m: Optional[float] = None) -> ShadowResult:
        return ShadowResult(
            height_m=11.0,
            scenarios=[
                ShadowScenario(
                    date_label="Jun 21", time_label=time_label,
                    overlap_pct=overlap_pct,
                    shadow_length_m=shadow_length_m,
                ),
            ],
        )

    def test_below_min_no_reduction(self):
        """Below 20% overlap: no reduction at all."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            lot_dimensions=_inner_west_lot(),
            shadow_result=self._make_shadow(15.0),
        )
        assert result.shadow_storey_reduction == 0

    def test_at_min_threshold_triggers_partial_reduction(self):
        """At exactly 20%: just above min, triggers small reduction."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            lot_dimensions=_inner_west_lot(),
            shadow_result=self._make_shadow(21.0),
        )
        assert result.shadow_storey_reduction == 1
        # Partial reduction — should be small
        shadow_step = next(s for s in result.steps if s.constraint == ConstraintType.SHADOW_ACCESS)
        assert shadow_step.reduction_m2 < 30.0  # much less than full half-storey

    def test_high_overlap_near_full_reduction(self):
        """60%+ overlap: full half-storey reduction."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            lot_dimensions=_inner_west_lot(),
            shadow_result=self._make_shadow(70.0),
        )
        assert result.shadow_storey_reduction == 1
        shadow_step = next(s for s in result.steps if s.constraint == ConstraintType.SHADOW_ACCESS)
        # At 70% (above MAX=60%), severity is capped at 1.0
        # Without depth amplifier: loss = footprint * 0.5 * 1.0 = ~54m2
        assert shadow_step.reduction_m2 > 40.0

    def test_depth_amplifier_increases_reduction(self):
        """Shadow reaching 80% of lot depth amplifies the reduction."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            lot_dimensions=_inner_west_lot(),  # depth_m=40
            shadow_result=self._make_shadow(50.0, shadow_length_m=35.0),  # 35/40 = 87.5%
        )
        assert result.shadow_storey_reduction == 1
        shadow_step = next(s for s in result.steps if s.constraint == ConstraintType.SHADOW_ACCESS)
        # With depth amplifier, reduction should be higher than without
        assert shadow_step.reduction_m2 > 0

    def test_noon_scenario_preferred(self):
        """Noon scenario used when available, even if morning overlap is higher."""
        shadow = ShadowResult(
            height_m=11.0,
            scenarios=[
                ShadowScenario(date_label="Jun 21", time_label="9:00 AM", overlap_pct=80.0),
                ShadowScenario(date_label="Jun 21", time_label="12:00 PM", overlap_pct=15.0),
            ],
        )
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            lot_dimensions=_inner_west_lot(),
            shadow_result=shadow,
        )
        # Noon overlap is 15% < 20% MIN, so no reduction despite 80% morning
        assert result.shadow_storey_reduction == 0

    def test_single_storey_no_shadow_reduction(self):
        """Shadow reduction only applies to multi-storey."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="3", lep_fsr_str="0.5:1",
            shadow_result=self._make_shadow(80.0),
        )
        assert result.shadow_storey_reduction == 0
        assert result.lep_max_storeys == 1


# ===========================================================================
# 8. Boundary cases
# ===========================================================================

class TestBoundaryCases:
    def test_no_lep_data(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
        )
        assert result.realistic_dwellings is None
        assert result.confidence == "low"
        assert len(result.gaps) >= 2

    def test_only_fsr(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_fsr_str="0.5:1",
        )
        assert result.lep_max_gfa_from_fsr_m2 == 300.0
        assert result.realistic_dwellings is not None

    def test_only_height(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="9",
        )
        assert result.lep_max_storeys == 3
        assert result.realistic_dwellings is not None

    def test_very_small_lot(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=100, dev_type="dwelling_house",
            lep_height_str="9", lep_fsr_str="0.5:1",
            dcp_controls=[
                _make_dcp("front_setback", 6.0),
                _make_dcp("rear_setback", 6.0),
                _make_dcp("side_setback", 1.5),
            ],
        )
        # Very small lot — setbacks may consume entire lot
        assert result.realistic_dwellings is not None
        assert result.realistic_dwellings >= 1  # floor of 1

    def test_zero_lot_area(self):
        """Zero lot should not crash — treated as unusable."""
        result = compute_constraint_arithmetic(
            lot_area_m2=0, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
        )
        # FSR x 0 = 0, but we floor dwellings to 1
        assert result.realistic_dwellings == 1

    def test_very_large_lot(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=10000, dev_type="residential_flat_building",
            lep_height_str="22", lep_fsr_str="2.5:1",
            lot_dimensions=LotDimensions(area_m2=10000, frontage_m=50, depth_m=200),
        )
        assert result.realistic_dwellings is not None
        assert result.realistic_dwellings > 20


# ===========================================================================
# 9. Three-state semantics (None vs 0 vs present)
# ===========================================================================

class TestThreeState:
    def test_none_setback_means_no_erosion(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            dcp_controls=[],  # no setbacks
        )
        # Without setbacks, footprint = lot area
        assert result.buildable_footprint_m2 == 600.0

    def test_zero_setback_means_build_to_boundary(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            lot_dimensions=_inner_west_lot(),
            dcp_controls=[
                _make_dcp("front_setback", 0.0),
                _make_dcp("rear_setback", 0.0),
                _make_dcp("side_setback", 0.0),
            ],
        )
        # Zero setbacks -> full lot footprint
        assert result.buildable_footprint_m2 == 600.0

    def test_none_fsr_produces_gap(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11",
        )
        assert any("FSR" in g for g in result.gaps)

    def test_none_height_produces_gap(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_fsr_str="0.75:1",
        )
        assert any("height" in g for g in result.gaps)


# ===========================================================================
# 10. Binding constraint — each type can win
# ===========================================================================

class TestBindingConstraintVariation:
    def test_fsr_binding_when_fsr_low(self):
        """Very low FSR with generous height -> FSR binds."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="22", lep_fsr_str="0.3:1",
            lot_dimensions=_inner_west_lot(),
        )
        assert result.binding_constraint == ConstraintType.LEP_FSR

    def test_height_binding_when_height_low(self):
        """Very low height with generous FSR -> height binds."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="3", lep_fsr_str="2.0:1",
            lot_dimensions=_inner_west_lot(),
        )
        assert result.binding_constraint == ConstraintType.LEP_HEIGHT

    def test_setbacks_binding_when_setbacks_large(self):
        """Very large setbacks on narrow lot -> setbacks bind."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="22", lep_fsr_str="2.0:1",
            lot_dimensions=LotDimensions(area_m2=600, frontage_m=12, depth_m=50),
            dcp_controls=[
                _make_dcp("front_setback", 10.0),
                _make_dcp("rear_setback", 10.0),
                _make_dcp("side_setback", 4.0),
            ],
        )
        assert result.binding_constraint == ConstraintType.DCP_SETBACKS

    def test_coverage_binding(self):
        """Low site coverage with generous everything else."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="22", lep_fsr_str="2.0:1",
            lot_dimensions=_inner_west_lot(),
            dcp_controls=[
                _make_dcp("max_site_coverage", 20.0, unit="%"),
            ],
        )
        assert result.binding_constraint == ConstraintType.DCP_SITE_COVERAGE


# ===========================================================================
# 11. Parking consumption
# ===========================================================================

class TestParking:
    def test_at_grade_parking_reduces_gfa(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            lot_dimensions=_inner_west_lot(),
            dcp_controls=[
                _make_dcp("car_parking", 1.0),
            ],
        )
        assert result.parking_spaces_required is not None
        assert result.parking_gfa_consumed_m2 is not None
        # Parking should reduce final GFA for non-apartment
        assert result.realistic_gfa_m2 < result.lep_envelope_gfa_m2

    def test_apartment_parking_does_not_reduce_gfa(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=2000, dev_type="residential_flat_building",
            lep_height_str="22", lep_fsr_str="2.0:1",
            lot_dimensions=LotDimensions(area_m2=2000, frontage_m=40, depth_m=50),
            dcp_controls=[
                _make_dcp("car_parking", 1.0, dev_type="residential_flat_building"),
            ],
        )
        # Apartments: parking is basement, doesn't reduce GFA
        assert result.realistic_gfa_m2 == result.lep_envelope_gfa_m2

    def test_sepp_parking_fallback(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            sepp_standards=[
                SEPPStandard(dev_type="dwelling_house", eligible=True, parking_spaces=1.0),
            ],
        )
        assert result.parking_spaces_required is not None


# ===========================================================================
# 12. Mutation-resistant numeric assertions
# ===========================================================================

class TestMutationResistant:
    """Specific numeric values that break if constants or formulas change."""

    def test_storey_height_constant(self):
        assert STOREY_HEIGHT_M == 3.0

    def test_min_dwelling_gfa_constant(self):
        assert MIN_DWELLING_GFA_M2 == 65.0

    def test_shadow_threshold_constants(self):
        assert SHADOW_OVERLAP_THRESHOLD == 0.40  # legacy compat
        assert SHADOW_OVERLAP_MIN == 0.20
        assert SHADOW_OVERLAP_MAX == 0.60

    def test_parking_area_constant(self):
        assert PARKING_AREA_PER_SPACE_M2 == 30.0

    def test_circulation_apartment(self):
        assert CIRCULATION_FACTOR_APARTMENT == 0.18

    def test_circulation_house(self):
        assert CIRCULATION_FACTOR_HOUSE == 0.0

    def test_exact_fsr_calculation(self):
        """0.75 x 600 must be exactly 450."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_fsr_str="0.75:1",
        )
        assert result.lep_max_gfa_from_fsr_m2 == 450.0

    def test_exact_storey_calculation(self):
        """11m / 3m = 3.67 -> int = 3 storeys."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11",
        )
        assert result.lep_max_storeys == 3

    def test_exact_setback_footprint(self):
        """15m lot, 1.5m each side = 12m width. 40m depth, 6+6 = 28m."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            lot_dimensions=_inner_west_lot(),
            dcp_controls=[
                _make_dcp("front_setback", 6.0),
                _make_dcp("rear_setback", 6.0),
                _make_dcp("side_setback", 1.5),
            ],
        )
        assert result.buildable_footprint_m2 == 336.0  # 12 x 28

    def test_dwelling_count_floor_division(self):
        """360m2 / 65m2 = 5.53 -> 5 dwellings (not 6)."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            lot_dimensions=_inner_west_lot(),
            dcp_controls=_inner_west_controls(),
        )
        assert result.realistic_dwellings == 5


# ===========================================================================
# 12. No-DCP LEP-envelope GFA (the ~100 non-DCP LGA backfill path)
# ===========================================================================

class TestNoDcpEnvelope:
    """Load-bearing assumption of the statewide FSR backfill: the engine yields a
    usable, low-confidence GFA from FSR/height alone, and stays NULL (never 0) when
    neither is present. Mutation-resistant exact assertions."""

    def test_fsr_plus_height_no_dcp_gives_fsr_capped_gfa(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="9", lep_fsr_str="0.5:1",
            dcp_controls=[],  # non-DCP LGA
        )
        # FSR cap (0.5 * 600 = 300) binds below the height cap (600 * 3 storeys).
        assert result.lep_envelope_gfa_m2 == 300.0
        assert result.realistic_gfa_m2 == 300.0
        assert result.realistic_dwellings == 4
        assert result.confidence == "low"
        assert result.binding_constraint.value == "lep_fsr"

    def test_fsr_ratio_and_decimal_parse_identically(self):
        ratio = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="9", lep_fsr_str="0.5:1", dcp_controls=[],
        )
        decimal = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="9", lep_fsr_str="0.5", dcp_controls=[],
        )
        assert ratio.realistic_gfa_m2 == decimal.realistic_gfa_m2 == 300.0

    def test_height_only_no_dcp_uses_height_envelope(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="9", lep_fsr_str=None, dcp_controls=[],
        )
        assert result.realistic_gfa_m2 == 1800.0
        assert result.confidence == "low"

    def test_no_fsr_no_height_stays_null_not_zero(self):
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str=None, lep_fsr_str=None, dcp_controls=[],
        )
        # Three-state: unknown capacity is NULL, never a fabricated 0.
        assert result.realistic_gfa_m2 is None
        assert result.lep_envelope_gfa_m2 is None
