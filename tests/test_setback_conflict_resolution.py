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

    def test_burwood_conflict_is_listed_not_picked(self):
        # The real Burwood defect: front_setback 9m AND 15m, no distinguishing condition.
        controls = [
            _c("front_setback", 9.0), _c("front_setback", 15.0), _c("front_setback", 15.0),
            _c("side_setback", 0.9), _c("rear_setback", 3.0),
        ]
        r = self._compute(controls)
        assert r.setback_front_m is None  # not picked: which applies is not known here
        assert [o.value_m for o in r.setback_front_options] == [9.0, 15.0]  # duplicate listed once
        assert r.setback_side_m == 0.9 and r.setback_rear_m == 3.0
        assert r.buildable_footprint_m2 is None
        gap_text = " ".join(r.gaps)
        assert "2 front setbacks (9 m and 15 m)" in gap_text
        assert "conservative" not in gap_text.lower()
        assert "No current" not in gap_text  # listed is not missing
        step = next(s for s in r.steps if s.constraint.value == "dcp_setbacks")
        assert step.footprint_m2 is None and "0.0" not in step.note
        assert step.label == "Buildable area after setbacks — not shown"

    def test_single_setbacks_emit_no_conflict_gap(self):
        controls = [_c("front_setback", 6.0), _c("side_setback", 0.9), _c("rear_setback", 3.0)]
        r = self._compute(controls)
        assert r.setback_front_m == 6.0 and r.setback_front_options == []
        assert not any("setbacks (" in g for g in r.gaps)
        assert r.buildable_footprint_m2 is not None


def _cc(control_type, value_min, condition):
    return DCPControl(control_type=control_type, dev_type="dwelling_house",
                      value_min=value_min, unit="m", condition=condition)


class TestSiteContext:
    """The lot's own known facts settle a setback; unknown facts never do."""

    def _compute(self, controls, corner):
        return compute_constraint_arithmetic(
            lot_area_m2=688.0, dev_type="dwelling_house", lep_height_str="9", lep_fsr_str="0.5",
            lot_dimensions=LotDimensions(area_m2=688.0, frontage_m=22.4, depth_m=39.7, is_corner=False),
            dcp_controls=controls, site_is_corner=corner,
        )

    def _rows(self, front):
        return front + [_c("side_setback", 0.9), _c("rear_setback", 6.0)]

    def test_corner_row_dropped_on_a_measured_non_corner_lot(self):
        r = self._compute(self._rows([_c("front_setback", 6.0), _cc("front_setback", 3.0, "corner lot; secondary street")]), False)
        assert r.setback_front_m == 6.0 and r.setback_front_options == []
        assert any("3 m front setback (corner lot; secondary street) does not apply here: this lot is not on a corner" in g
                   for g in r.gaps)
        assert r.buildable_footprint_m2 is not None

    def test_unknown_corner_rules_nothing_out(self):
        r = self._compute(self._rows([_c("front_setback", 6.0), _cc("front_setback", 3.0, "corner lot")]), None)
        assert r.setback_front_m is None
        assert [o.value_m for o in r.setback_front_options] == [3.0, 6.0]

    def test_road_class_is_never_guessed(self):
        r = self._compute(self._rows([_c("front_setback", 6.0), _cc("front_setback", 10.0, "state and regional roads")]), False)
        assert r.setback_front_m is None
        assert [o.value_m for o in r.setback_front_options] == [6.0, 10.0]

    def test_other_housing_type_row_dropped(self):
        rows = [_c("front_setback", 6.0), _c("side_setback", 0.9), _cc("side_setback", 1.5, "terraces"),
                _c("rear_setback", 6.0)]
        r = self._compute(rows, None)
        assert r.setback_side_m == 0.9
        assert any("1.5 m side setback (terraces) does not apply here: it is for a different type of housing" in g
                   for g in r.gaps)

    def test_row_naming_own_type_is_kept(self):
        rows = [_c("front_setback", 6.0), _c("side_setback", 0.9),
                _cc("side_setback", 1.5, "dwelling houses and terraces, upper floor"), _c("rear_setback", 6.0)]
        r = self._compute(rows, None)
        assert r.setback_side_m is None and [o.value_m for o in r.setback_side_options] == [0.9, 1.5]

    def test_every_row_ruled_out_is_not_a_listing(self):
        rows = [_c("front_setback", 6.0), _cc("side_setback", 1.2, "terraces"), _cc("side_setback", 1.5, "dual occupancy"),
                _c("rear_setback", 6.0)]
        r = self._compute(rows, None)
        assert r.setback_side_m is None and r.setback_side_options == []
        assert any("No current side setback" in g for g in r.gaps)


def test_endpoint_passes_measured_corner_status(monkeypatch):
    import asyncio
    from services import constraint_arithmetic as ca
    seen = {}
    real = ca.compute_constraint_arithmetic

    def spy(**kw):
        seen["corner"] = kw.get("site_is_corner")
        return real(**kw)

    monkeypatch.setattr(ca, "compute_constraint_arithmetic", spy)
    monkeypatch.setattr(ca, "_fetch_constraint_data_from_db", lambda **k: ([], [], []))
    monkeypatch.setattr(ca, "_fetch_dcp_coverage", lambda *a, **k: None)
    monkeypatch.setattr(ca, "_ceiling_for_request", lambda req: (None, False, None, None))
    for val in (False, None):
        asyncio.run(ca.constraint_arithmetic_full(ca.ConstraintArithmeticFullRequest(
            lot_area_m2=600.0, zone="R2", lep_height_str="9", is_corner=val)))
        assert seen["corner"] is val


class TestSiteContextSolFindings:
    """Sol cross-review of #1371/#1377 (2026-10-19): each case below was wrong on main."""

    def _compute(self, controls, corner=None, area=640.0):
        return compute_constraint_arithmetic(
            lot_area_m2=area, dev_type="dwelling_house", lep_height_str="9.5", lep_fsr_str=None,
            lot_dimensions=LotDimensions(area_m2=area, frontage_m=20.0, depth_m=32.0, is_corner=False),
            dcp_controls=controls, site_is_corner=corner,
        )

    def test_lone_upper_floor_row_is_listed_not_used_for_every_lot(self):
        rows = [_cc("front_setback", 6.0, None), _cc("rear_setback", 6.0, None),
                _cc("side_setback", 1.5, "upper floor walls")]
        r = self._compute(rows)
        assert r.setback_side_m is None
        assert [o.value_m for o in r.setback_side_options] == [1.5]
        assert r.buildable_footprint_m2 is None
        assert any("only for one case (upper floor walls)" in g for g in r.gaps)

    def test_lot_size_band_not_containing_the_lot_is_not_listed(self):
        rows = [_cc("front_setback", 4.5, "lot less than 900 m2"),
                _cc("front_setback", 6.5, "lot between 900 m2 and 1,500 m2"),
                _cc("front_setback", 3.5, "fronting open space"),
                _cc("rear_setback", 4.0, None), _cc("side_setback", 0.9, None)]
        r = self._compute(rows)
        assert [o.value_m for o in r.setback_front_options] == [3.5, 4.5]
        assert any("6.5 m front setback" in g and "different size" in g for g in r.gaps)

    def test_excluding_corner_lots_is_kept_on_a_non_corner_lot(self):
        rows = [_cc("front_setback", 6.0, "all lots excluding corner lots"),
                _cc("rear_setback", 6.0, None), _cc("side_setback", 0.9, None)]
        r = self._compute(rows, corner=False)
        assert r.setback_front_m == 6.0

    def test_semi_detached_row_is_not_a_dwelling_house_row(self):
        rows = [_cc("front_setback", 6.0, None), _cc("rear_setback", 6.0, None),
                _cc("side_setback", 0.9, None), _cc("side_setback", 0.0, "semi-detached party wall")]
        r = self._compute(rows)
        assert r.setback_side_m == 0.9


    def test_must_not_be_less_than_on_corner_lots_is_still_corner_only(self):
        rows = [_cc("front_setback", 6.0, None), _cc("rear_setback", 6.0, None),
                _cc("side_setback", 0.9, None),
                _cc("side_setback", 3.0, "setback must not be less than 3 m on corner lots")]
        r = TestSiteContextSolFindings()._compute(rows, corner=False)
        assert r.setback_side_m == 0.9
        assert any("3 m side setback" in g and "not on a corner" in g for g in r.gaps)


    def test_rule_excluding_corner_lots_is_dropped_on_a_corner_lot(self):
        rows = [_cc("front_setback", 6.0, "all lots excluding corner lots"), _cc("front_setback", 4.5, "corner lots"),
                _cc("rear_setback", 6.0, None), _cc("side_setback", 0.9, None)]
        r = TestSiteContextSolFindings()._compute(rows, corner=True)
        assert r.setback_front_options == [] or [o.value_m for o in r.setback_front_options] == [4.5]
        assert any("6 m front setback" in g and "excludes corner lots" in g for g in r.gaps)

    def test_excluding_non_corner_lots_is_a_corner_rule(self):
        rows = [_cc("front_setback", 6.0, None), _cc("rear_setback", 6.0, None), _cc("side_setback", 0.9, None),
                _cc("side_setback", 2.0, "excluding non-corner lots")]
        r = TestSiteContextSolFindings()._compute(rows, corner=False)
        assert r.setback_side_m == 0.9
