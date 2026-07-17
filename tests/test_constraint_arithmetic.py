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
    _dcp_height_metres,
    _dcp_value_conflict,
    _estimate_lot_dimensions,
    _has_battleaxe_head,
    _get_dcp_value,
    _identify_binding_constraint,
    _lot_band_match,
    _resolve_lot_band,
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

    def test_lep_envelope_is_clean_headline(self):
        # Headline LEP envelope = min(FSR 450, clean height 600*3=1800) = 450.
        # DCP erosion no longer drags the envelope down — it feeds dcp_adjusted.
        assert self.result.lep_envelope_gfa_m2 == 450.0

    def test_dcp_adjusted_after_coverage_then_landscaping(self):
        """Secondary figure: setbacks->coverage cap 300. Landscaping (30%=180m2)
        is an OPEN-SPACE requirement, not a further subtraction from the already
        coverage-capped footprint: a 300m2 build + 180m2 landscaping = 480m2 fits
        on the 600m2 lot, so the footprint stays 300 (cap = min(300, 600-180=420)).
        Height GFA 300*3=900; min(FSR 450, 900) = 450. (The old 360 double-counted
        landscaping against a footprint that already left room for it.)"""
        assert self.result.dcp_adjusted_gfa_m2 == 450.0

    def test_realistic_gfa(self):
        # Headline = the clean LEP envelope (FSR-bound here).
        assert self.result.realistic_gfa_m2 == 450.0

    def test_realistic_dwellings(self):
        # GATE-1: a dwelling house is ONE dwelling regardless of envelope GFA.
        # (The old 450/65 -> 6 was the pre-GATE-1 bug; GFA-scaled yield only
        # applies to multi-unit forms — see tests/test_dwelling_form.py.)
        assert self.result.realistic_dwellings == 1

    def test_binding_constraint(self):
        # FSR (450m2) < landscaping path (468m2) — FSR is more restrictive
        assert self.result.binding_constraint == ConstraintType.LEP_FSR

    def test_confidence_high(self):
        assert self.result.confidence == "high"

    def test_no_gaps(self):
        assert len(self.result.gaps) == 0

    def test_steps_present(self):
        assert len(self.result.steps) >= 4


class TestDcpHeightFallbackRegional:
    """Regional / DCP-only councils (e.g. Wingecarribee) map no LEP height or
    FSR, controlling built form through the DCP. The engine must fall back to
    the structured DCP max_height so yield does not collapse to null — and the
    landscaping requirement must cap the footprint, not double-subtract it.
    Bowral-style flag lot: 4096m2, DCP 8.5m height, 25% coverage, 75% landscaping.
    """

    def setup_method(self):
        controls = [
            _make_dcp("max_height", 8.5),
            _make_dcp("front_setback", 15.0),
            _make_dcp("rear_setback", 10.0),
            _make_dcp("side_setback", 3.5),
            _make_dcp("max_site_coverage", 25.0),
            _make_dcp("landscaping_min", 75.0),
        ]
        self.result = compute_constraint_arithmetic(
            lot_area_m2=4096,
            dev_type="dwelling_house",
            lep_height_str=None,   # LEP maps no height
            lep_fsr_str=None,      # and no FSR
            dcp_controls=controls,
        )

    def test_lep_height_stays_none(self):
        # We do not fake an LEP height — the LEP genuinely has none.
        assert self.result.lep_height_m is None

    def test_storeys_come_from_dcp_height(self):
        # 8.5m DCP height / 3.0m per storey = 2 storeys — envelope now computable.
        assert self.result.lep_max_storeys == 2

    def test_dcp_height_provenance_is_surfaced(self):
        assert any("taken from the council DCP" in g for g in self.result.gaps)

    def test_landscaping_caps_not_zeroes_footprint(self):
        # 25% coverage caps the working footprint to 1024m2; 75% landscaping
        # (3072m2) is open space that fits alongside (1024 + 3072 = 4096), so the
        # landscaping step caps at min(1024, 4096-3072)=1024. The old code
        # subtracted 3072 from 1024 and drove the footprint to 0.
        land_step = next(
            s for s in self.result.steps
            if s.constraint == ConstraintType.DCP_LANDSCAPING
        )
        assert land_step.footprint_m2 == 1024.0

    def test_yield_is_now_computable(self):
        # With a height envelope and a non-zero footprint, a GFA exists where the
        # pre-fix engine returned null for every DCP-only council.
        assert self.result.realistic_gfa_m2 is not None
        assert self.result.realistic_gfa_m2 > 0


class TestDcpHeightUnits:
    """DCP height is unit-aware: commonly STOREYS, not metres (unlike the LEP).
    Live catch on 38 Park Rd Bowral — Wingecarribee's "2 storeys" was read as 2m."""

    def test_storeys_converted_to_metres(self):
        # "2 storeys" -> 2 * 3.0m = 6m (round-trips to 2 storeys downstream).
        ctrls = [_make_dcp("max_height", 2, unit="storeys")]
        assert _dcp_height_metres(ctrls, "dwelling_house") == (6.0, True)

    def test_prefers_general_over_hca_conditioned(self):
        # A "within a Heritage Conservation Area" row is an exception; the general
        # 2-storey control applies by default, not the 1-storey HCA one.
        general = _make_dcp("max_height", 2, unit="storeys")
        hca = DCPControl(control_type="max_height", dev_type="dwelling_house",
                         value_min=1, unit="storeys",
                         condition="within a Heritage Conservation Area")
        assert _dcp_height_metres([general, hca], "dwelling_house") == (6.0, True)

    def test_rejects_implausible_metre_height(self):
        # A sub-storey "height" (Canada Bay's 0.9m mistype class) is a mis-extraction.
        assert _dcp_height_metres([_make_dcp("max_height", 0.9, unit="m")], "dwelling_house") == (None, False)

    def test_plausible_metre_height_kept(self):
        assert _dcp_height_metres([_make_dcp("max_height", 8.5, unit="m")], "dwelling_house") == (8.5, False)

    def test_engine_uses_storey_height_end_to_end(self):
        # Wingecarribee-style: no LEP height, DCP "2 storeys" -> 2 storeys, not 1.
        result = compute_constraint_arithmetic(
            lot_area_m2=4096, dev_type="dwelling_house",
            lep_height_str=None, lep_fsr_str=None,
            dcp_controls=[
                _make_dcp("max_height", 2, unit="storeys"),
                _make_dcp("front_setback", 15.0), _make_dcp("side_setback", 3.5),
                _make_dcp("max_site_coverage", 25.0, unit="%"),
            ],
        )
        assert result.lep_max_storeys == 2
        assert any("2 storeys" in g for g in result.gaps)


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

    def test_setbacks_erode_dcp_adjusted(self):
        """Very large setbacks on a narrow lot reduce the secondary dcp_adjusted
        figure below the headline LEP envelope (binding headline stays FSR/height)."""
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
        assert result.binding_constraint == ConstraintType.LEP_FSR
        assert result.dcp_adjusted_gfa_m2 is not None
        assert result.dcp_adjusted_gfa_m2 < result.realistic_gfa_m2

    def test_coverage_erodes_dcp_adjusted(self):
        """Low site coverage erodes the secondary dcp_adjusted figure; the headline
        envelope binding remains the LEP control (FSR/height)."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="22", lep_fsr_str="2.0:1",
            lot_dimensions=_inner_west_lot(),
            dcp_controls=[
                _make_dcp("max_site_coverage", 20.0, unit="%"),
            ],
        )
        assert result.binding_constraint == ConstraintType.LEP_FSR
        assert result.dcp_adjusted_gfa_m2 is not None
        assert result.dcp_adjusted_gfa_m2 < result.realistic_gfa_m2

    def test_unreliable_geometry_keeps_lep_envelope_headline(self):
        """Regression (the Penrith=0 case): with no reliable frontage/depth and a
        heavy landscaping requirement, the headline must stay the LEP envelope —
        never zero — and the dcp_adjusted secondary is suppressed."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="8.5", lep_fsr_str="0.5:1",
            lot_dimensions=None,  # no reliable geometry
            dcp_controls=[
                _make_dcp("landscaping_min", 50.0, unit="%"),
                _make_dcp("front_setback", 6.0),
            ],
        )
        assert result.realistic_gfa_m2 == 300.0  # FSR 0.5 * 600 envelope, not zeroed
        assert result.dcp_adjusted_gfa_m2 is None  # geometry unreliable → suppressed


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
        # Parking reduces the secondary dcp_adjusted figure (not the LEP-envelope
        # headline) for a non-apartment.
        assert result.dcp_adjusted_gfa_m2 is not None
        assert result.dcp_adjusted_gfa_m2 < result.realistic_gfa_m2

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
        """GATE-1: a dwelling house yields ONE dwelling; envelope GFA does not
        multiply it (the 450/65 -> 6 figure was the pre-GATE-1 bug). The GFA
        floor-division path for multi-unit forms is locked in test_dwelling_form."""
        result = compute_constraint_arithmetic(
            lot_area_m2=600, dev_type="dwelling_house",
            lep_height_str="11", lep_fsr_str="0.75:1",
            lot_dimensions=_inner_west_lot(),
            dcp_controls=_inner_west_controls(),
        )
        assert result.realistic_dwellings == 1


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
        assert result.realistic_dwellings == 1  # GATE-1: dwelling_house is one dwelling
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


# ===========================================================================
# Lot-size band resolution (Bowral regression: front pool 4.5/6.5/15 must
# resolve to ONE band, not a conservative-max + conflict note)
# ===========================================================================

def _wing_front_controls() -> list[DCPControl]:
    """The real Wingecarribee C2.6 front-setback tiers (verbatim conditions)."""
    return [
        DCPControl(control_type="front_setback", dev_type="dwelling_house", value_min=4.5, unit="m",
                   condition="lot less than 900m2; exclusive of garage setbacks; in general, subject to site assessment"),
        DCPControl(control_type="front_setback", dev_type="dwelling_house", value_min=6.5, unit="m",
                   condition="lot between 900m2 and 1500m2; exclusive of garage setbacks; subject to site assessment"),
        DCPControl(control_type="front_setback", dev_type="dwelling_house", value_min=15.0, unit="m",
                   condition="lot over 1500m2; exclusive of garage setbacks; subject to site assessment"),
    ]


class TestLotBandMatch:
    def test_less_than(self):
        assert _lot_band_match("lot less than 900m2", 600) is True
        assert _lot_band_match("lot less than 900m2", 900) is False

    def test_between_inclusive(self):
        assert _lot_band_match("lot between 900m2 and 1500m2", 900) is True
        assert _lot_band_match("lot between 900m2 and 1500m2", 1500) is True
        assert _lot_band_match("lot between 900m2 and 1500m2", 1501) is False

    def test_over_exclusive(self):
        assert _lot_band_match("lot over 1500m2", 1500) is False
        assert _lot_band_match("lot over 1500m2", 4096) is True

    def test_lot_size_variant_and_commas(self):
        assert _lot_band_match("Lot size less than 2,000m2 — minimum POS 35%", 1800) is True

    def test_near_miss_does_not_parse(self):
        # A range written without the band keywords must NOT be guessed at.
        assert _lot_band_match("lots 600-900m2; building height", 700) is None

    def test_no_condition(self):
        assert _lot_band_match(None, 700) is None
        assert _lot_band_match("subject to site assessment", 700) is None


class TestBandResolution:
    def test_bowral_lot_resolves_to_over_band(self):
        # 38 Park Rd Bowral (4,189 m2): the ONLY applicable tier is over-1500.
        assert _get_dcp_value(_wing_front_controls(), "front_setback", "dwelling_house",
                              lot_area_m2=4189) == 15.0

    def test_small_lot_resolves_to_lowest_band(self):
        assert _get_dcp_value(_wing_front_controls(), "front_setback", "dwelling_house",
                              lot_area_m2=600) == 4.5

    def test_resolved_band_is_not_a_conflict(self):
        assert _dcp_value_conflict(_wing_front_controls(), "front_setback", "dwelling_house",
                                   lot_area_m2=4189) is None

    def test_resolved_band_missing_value_surfaces_conflict(self):
        # Regression: a lot resolves to the <900 band, but that band's row has NO
        # value_min (an extraction gap). _get_dcp_value falls back to the
        # conservative max across the OTHER (non-applicable) bands, so the
        # borrowed figure MUST be flagged for verification - previously the
        # conflict was suppressed simply because a band resolved, serving a
        # cross-band value with no warning.
        controls = [
            DCPControl(control_type="front_setback", dev_type="dwelling_house", value_min=None,
                       unit="m", condition="lot less than 900m2"),
            DCPControl(control_type="front_setback", dev_type="dwelling_house", value_min=6.5,
                       unit="m", condition="lot between 900m2 and 1500m2"),
            DCPControl(control_type="front_setback", dev_type="dwelling_house", value_min=15.0,
                       unit="m", condition="lot over 1500m2"),
        ]
        # 600 m2 resolves to the <900 band, which lacks a value.
        assert _resolve_lot_band(controls, 600) is not None
        # Conservative fallback value stands (fail-safe: largest = smallest envelope).
        assert _get_dcp_value(controls, "front_setback", "dwelling_house", lot_area_m2=600) == 15.0
        # ...but the gap now surfaces instead of being silently suppressed.
        assert _dcp_value_conflict(controls, "front_setback", "dwelling_house",
                                   lot_area_m2=600) == [6.5, 15.0]

    def test_unknown_area_stays_conservative(self):
        # No lot area -> cannot resolve -> conservative max, and the values
        # still surface as a conflict for the gap note.
        assert _get_dcp_value(_wing_front_controls(), "front_setback", "dwelling_house") == 15.0
        assert _dcp_value_conflict(_wing_front_controls(), "front_setback", "dwelling_house") == [4.5, 6.5, 15.0]

    def test_unbanded_candidate_blocks_resolution(self):
        # One general (unbanded) row in the pool -> a partial parse could drop
        # it silently, so resolution must refuse and keep the conservative max.
        controls = _wing_front_controls() + [
            DCPControl(control_type="front_setback", dev_type="dwelling_house", value_min=6.0, unit="m",
                       condition="corner lots"),
        ]
        assert _resolve_lot_band(controls, 4189) is None
        assert _get_dcp_value(controls, "front_setback", "dwelling_house", lot_area_m2=4189) == 15.0

    def test_two_matching_bands_blocks_resolution(self):
        controls = [
            DCPControl(control_type="front_setback", dev_type="dwelling_house", value_min=4.5,
                       condition="lot less than 900m2"),
            DCPControl(control_type="front_setback", dev_type="dwelling_house", value_min=6.0,
                       condition="lot less than 1500m2"),
        ]
        assert _resolve_lot_band(controls, 600) is None

    def test_dev_type_pool_not_polluted(self):
        # Medium-density rows must not enter the dwelling_house selection even
        # when their values are larger (the original Bowral pool regression).
        controls = _wing_front_controls() + [
            DCPControl(control_type="front_setback", dev_type="multi_dwelling_housing",
                       value_min=8.0, unit="m", condition=None),
        ]
        assert _get_dcp_value(controls, "front_setback", "dwelling_house", lot_area_m2=4189) == 15.0
        assert _get_dcp_value(controls, "front_setback", "multi_dwelling_housing") == 8.0


class TestBattleaxeDimensions:
    def test_head_dimensions_used(self):
        # 38 Park Rd Bowral: head 43.1m wide, 3,710 m2 -> depth = area / width.
        dims = LotDimensions(area_m2=4189, frontage_m=None, depth_m=None,
                             lot_type="battleaxe",
                             battleaxe_access_way_width_m=3.05,
                             battleaxe_main_lot_width_m=43.1,
                             battleaxe_main_lot_area_m2=3710)
        f, d = _estimate_lot_dimensions(dims, 4189)
        assert f == 43.1
        assert abs(f * d - 3710) < 0.1  # envelope = HEAD area, not whole lot

    def test_battleaxe_without_head_falls_back(self):
        dims = LotDimensions(area_m2=4189, lot_type="battleaxe")
        f, d = _estimate_lot_dimensions(dims, 4189)
        assert abs(f * d - 4189) < 0.1

    def test_head_predicate_agrees_with_estimation(self):
        # Regression: the provenance label and the dimension estimation must use
        # the SAME predicate. They previously disagreed on a 0 measurement -
        # estimation fell back to the whole lot while the label still claimed the
        # envelope was computed on the head.
        inf, nan = float("inf"), float("nan")
        for width, area in ((0, 3710), (43.1, 0), (0, 0), (-43.1, 3710), (43.1, -1),
                            (inf, 3710), (43.1, inf), (nan, 3710), (43.1, nan)):
            dims = LotDimensions(area_m2=4189, lot_type="battleaxe",
                                 battleaxe_main_lot_width_m=width,
                                 battleaxe_main_lot_area_m2=area)
            assert _has_battleaxe_head(dims) is False, (width, area)
            # ...and estimation agrees: falls back to the WHOLE lot, not the head.
            f, d = _estimate_lot_dimensions(dims, 4189)
            assert abs(f * d - 4189) < 0.1, (width, area)

    def test_head_predicate_true_only_for_positive_pair(self):
        dims = LotDimensions(area_m2=4189, lot_type="battleaxe",
                             battleaxe_main_lot_width_m=43.1,
                             battleaxe_main_lot_area_m2=3710)
        assert _has_battleaxe_head(dims) is True
        # Non-battleaxe lots never count as having a head.
        assert _has_battleaxe_head(LotDimensions(area_m2=600, frontage_m=15, depth_m=40)) is False
        assert _has_battleaxe_head(None) is False

    def test_zero_width_head_does_not_claim_measured_envelope(self):
        # End-to-end: a 0-width head must NOT produce the head-based provenance
        # note, because the dimensions actually came from the 1:2.5 fallback.
        result = compute_constraint_arithmetic(
            lot_area_m2=4189,
            dev_type="dwelling_house",
            lep_height_str="9",
            lep_fsr_str="0.5:1",
            lot_dimensions=LotDimensions(area_m2=4189, lot_type="battleaxe",
                                         battleaxe_main_lot_width_m=0,
                                         battleaxe_main_lot_area_m2=3710),
            dcp_controls=[_make_dcp("front_setback", 6.0), _make_dcp("rear_setback", 6.0),
                          _make_dcp("side_setback", 1.5)],
        )
        assert not any("main lot" in g for g in result.gaps), result.gaps
        assert any("1:2.5" in g for g in result.gaps), result.gaps

    def test_head_envelope_note_is_an_estimate_not_a_measurement(self):
        # The depth is derived (area / width), so the note must not imply the head
        # was surveyed - it states the rectangular assumption and asks to verify.
        result = compute_constraint_arithmetic(
            lot_area_m2=4189,
            dev_type="dwelling_house",
            lep_height_str="9",
            lep_fsr_str="0.5:1",
            lot_dimensions=LotDimensions(area_m2=4189, lot_type="battleaxe",
                                         battleaxe_main_lot_width_m=43.1,
                                         battleaxe_main_lot_area_m2=3710),
            dcp_controls=[_make_dcp("front_setback", 6.0), _make_dcp("rear_setback", 6.0),
                          _make_dcp("side_setback", 1.5)],
        )
        note = next(g for g in result.gaps if "main lot" in g)
        assert "estimated" in note
        assert "assumed rectangular" in note
        assert "computed on" not in note  # the old overclaiming wording
