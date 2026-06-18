"""GATE-2b — a SEPP override applies only to the form it belongs to.

The old `or not applied_overrides` fallback applied the first override (often an
LMR form bonus, e.g. dual-occupancy/manor 9.5m) to ANY dev_type, so a dwelling
house wrongly inherited an 8.5m -> 9.5m / 3-storey uplift (seen on 17 Corden Ave,
Five Dock). The override now applies only when ovr.dev_type == dev_type.
"""
from services.constraint_arithmetic import compute_constraint_arithmetic
from services.constraint_models import SeppLepOverride


def _ovr(dev_type, sepp_value, control="height", lep_value=8.5):
    return SeppLepOverride(dev_type=dev_type, control=control, lep_value=lep_value, sepp_value=sepp_value)


def test_override_does_not_apply_to_mismatched_form():
    """The 17 Corden case: a dual-occupancy 9.5m bonus must NOT inflate a dwelling house."""
    r = compute_constraint_arithmetic(
        lot_area_m2=398.4, dev_type="dwelling_house",
        lep_height_str="8.5", lep_fsr_str="0.5",
        sepp_lep_overrides=[_ovr("dual_occupancy", 9.5)],
    )
    assert r.effective_height_m == 8.5
    assert r.sepp_overrides_applied == []


def test_override_applies_to_matching_form():
    r = compute_constraint_arithmetic(
        lot_area_m2=398.4, dev_type="dual_occupancy",
        lep_height_str="8.5", lep_fsr_str="0.5",
        sepp_lep_overrides=[_ovr("dual_occupancy", 9.5)],
    )
    assert r.effective_height_m == 9.5
    assert len(r.sepp_overrides_applied) == 1


def test_fsr_override_only_for_matching_form():
    # An RFB FSR bonus must not lift a dwelling_house FSR.
    r = compute_constraint_arithmetic(
        lot_area_m2=398.4, dev_type="dwelling_house",
        lep_height_str="8.5", lep_fsr_str="0.5",
        sepp_lep_overrides=[_ovr("residential_flat_building", 1.0, control="fsr", lep_value=0.5)],
    )
    assert r.effective_fsr == 0.5
    assert r.sepp_overrides_applied == []


def test_override_ignored_when_not_more_generous():
    r = compute_constraint_arithmetic(
        lot_area_m2=398.4, dev_type="dual_occupancy",
        lep_height_str="9.5", lep_fsr_str="0.5",
        sepp_lep_overrides=[_ovr("dual_occupancy", 9.5)],  # equal, not strictly greater
    )
    assert r.effective_height_m == 9.5
    assert r.sepp_overrides_applied == []
