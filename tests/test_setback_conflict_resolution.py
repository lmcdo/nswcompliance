"""Deterministic, conservative resolution of conflicting/tiered DCP controls.

Before this fix, ``_get_dcp_value`` matched on (control_type, dev_type) and kept
the LAST row in iteration order — so when several rows existed (tiered controls
by lot size / storey band, or a duplicate/garbled extraction such as Burwood's
front_setback 9m AND 15m) the chosen value was arbitrary and order-dependent.

A statewide read-only audit found 62 such conflict groups across 28 LGAs. The
fix makes selection deterministic and CONSERVATIVE (never over-reports buildable
capacity): the largest value_min for minimum-requirement controls, the smallest
value_max for caps — and surfaces a data-gap so a chosen-among-conflicts setback
is flagged for verification.
"""

from services.constraint_arithmetic import (
    _get_dcp_value,
    _matching_controls,
    _dcp_value_conflict,
    compute_constraint_arithmetic,
)
from services.constraint_models import DCPControl, LotDimensions


def _c(control_type, value_min=None, value_max=None, dev_type="dwelling_house"):
    return DCPControl(
        control_type=control_type, dev_type=dev_type,
        value_min=value_min, value_max=value_max, unit="m",
    )


# --- Deterministic, conservative selection ---------------------------------

class TestDeterministicSelection:
    def test_single_row_value_unchanged(self):
        assert _get_dcp_value([_c("front_setback", 6.0)], "front_setback", "dwelling_house") == 6.0

    def test_multiple_min_requirement_picks_max(self):
        ctrls = [_c("front_setback", 9.0), _c("front_setback", 15.0)]
        assert _get_dcp_value(ctrls, "front_setback", "dwelling_house") == 15.0

    def test_selection_is_order_independent(self):
        # Kills the "last row wins" (and "first row wins") behaviour: both
        # orderings must resolve to the same conservative value.
        forward = _get_dcp_value(
            [_c("front_setback", 9.0), _c("front_setback", 15.0)], "front_setback", "dwelling_house")
        reverse = _get_dcp_value(
            [_c("front_setback", 15.0), _c("front_setback", 9.0)], "front_setback", "dwelling_house")
        assert forward == reverse == 15.0

    def test_prefer_max_cap_picks_smallest_allowance(self):
        # Two site-coverage caps -> the tightest (smallest) is conservative.
        ctrls = [_c("max_site_coverage", value_max=50.0), _c("max_site_coverage", value_max=67.0)]
        assert _get_dcp_value(ctrls, "max_site_coverage", "dwelling_house", prefer_max=True) == 50.0

    def test_ignores_none_value_min(self):
        ctrls = [_c("front_setback", None), _c("front_setback", 6.0)]
        assert _get_dcp_value(ctrls, "front_setback", "dwelling_house") == 6.0

    def test_no_matching_control_returns_none(self):
        assert _get_dcp_value([_c("rear_setback", 3.0)], "front_setback", "dwelling_house") is None


# --- Exact dev_type vs dwelling_house fallback -----------------------------

class TestExactVsFallback:
    def test_exact_dev_type_preferred_over_dwelling_house(self):
        ctrls = [
            _c("front_setback", 6.0, dev_type="dwelling_house"),
            _c("front_setback", 3.0, dev_type="secondary_dwelling"),
        ]
        # Exact secondary_dwelling match wins; the dwelling_house row is NOT mixed in.
        assert _get_dcp_value(ctrls, "front_setback", "secondary_dwelling") == 3.0
        assert _matching_controls(ctrls, "front_setback", "secondary_dwelling") == [ctrls[1]]

    def test_falls_back_to_dwelling_house_when_no_exact(self):
        ctrls = [_c("front_setback", 6.0, dev_type="dwelling_house")]
        assert _get_dcp_value(ctrls, "front_setback", "secondary_dwelling") == 6.0


# --- Conflict detection ----------------------------------------------------

class TestConflictDetection:
    def test_returns_sorted_distinct_values_on_conflict(self):
        ctrls = [_c("front_setback", 15.0), _c("front_setback", 9.0)]
        assert _dcp_value_conflict(ctrls, "front_setback", "dwelling_house") == [9.0, 15.0]

    def test_single_value_is_not_a_conflict(self):
        assert _dcp_value_conflict([_c("front_setback", 6.0)], "front_setback", "dwelling_house") is None

    def test_identical_duplicate_values_are_not_a_conflict(self):
        ctrls = [_c("front_setback", 6.0), _c("front_setback", 6.0)]
        assert _dcp_value_conflict(ctrls, "front_setback", "dwelling_house") is None

    def test_no_rows_is_not_a_conflict(self):
        assert _dcp_value_conflict([], "front_setback", "dwelling_house") is None


# --- Integration through compute_constraint_arithmetic ---------------------

class TestComputeIntegration:
    def _compute(self, controls):
        return compute_constraint_arithmetic(
            lot_area_m2=1006.83,
            dev_type="dwelling_house",
            lep_height_str="8.5",
            lep_fsr_str="0.55",
            lot_dimensions=LotDimensions(area_m2=1006.83, frontage_m=14.7, depth_m=70.3, is_corner=False),
            dcp_controls=controls,
        )

    def test_burwood_conflict_uses_conservative_and_flags_gap(self):
        # The real Burwood defect: front_setback 9m AND 15m, no distinguishing condition.
        controls = [
            _c("front_setback", 9.0), _c("front_setback", 15.0),
            _c("side_setback", 0.9), _c("rear_setback", 3.0),
        ]
        r = self._compute(controls)
        assert r.setback_front_m == 15.0  # deterministic, conservative
        gap_text = " ".join(r.gaps).lower()
        assert "front setback" in gap_text
        assert "9m" in gap_text and "15m" in gap_text
        assert "conservative" in gap_text

    def test_single_setbacks_emit_no_conflict_gap(self):
        controls = [_c("front_setback", 6.0), _c("side_setback", 0.9), _c("rear_setback", 3.0)]
        r = self._compute(controls)
        assert r.setback_front_m == 6.0
        assert not any("differing values" in g for g in r.gaps)
