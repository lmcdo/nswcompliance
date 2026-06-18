"""GATE-3 — the DCP site-coverage cap must not be silently dropped.

max_site_coverage stores its limit in value_max, but _get_dcp_value returned
value_min, so the cap came back None and ~80% coverage passed unchallenged. The
cap is now read with prefer_max and applied.
"""
from services.constraint_arithmetic import _get_dcp_value, compute_constraint_arithmetic
from services.constraint_models import DCPControl, LotDimensions


def _cov(value_min=None, value_max=None):
    return DCPControl(
        control_type="max_site_coverage", dev_type="dwelling_house",
        value_min=value_min, value_max=value_max,
    )


def test_prefer_max_reads_value_max():
    ctrls = [_cov(value_min=None, value_max=65.0)]
    # default (value_min) silently misses the cap...
    assert _get_dcp_value(ctrls, "max_site_coverage", "dwelling_house") is None
    # ...prefer_max reads it.
    assert _get_dcp_value(ctrls, "max_site_coverage", "dwelling_house", prefer_max=True) == 65.0


def test_prefer_max_falls_back_to_value_min():
    ctrls = [_cov(value_min=50.0, value_max=None)]
    assert _get_dcp_value(ctrls, "max_site_coverage", "dwelling_house", prefer_max=True) == 50.0


def test_default_min_path_unchanged_for_setbacks():
    s = DCPControl(control_type="front_setback", dev_type="dwelling_house", value_min=6.0, value_max=None)
    assert _get_dcp_value([s], "front_setback", "dwelling_house") == 6.0


def test_site_coverage_cap_from_value_max_is_applied():
    """600 m2 lot, 50% cap stored in value_max -> a 300 m2 cap must be applied,
    not silently dropped (pre-GATE-3 site_coverage_cap_m2 was None)."""
    r = compute_constraint_arithmetic(
        lot_area_m2=600, dev_type="dwelling_house",
        lep_height_str="9", lep_fsr_str="1.0",
        lot_dimensions=LotDimensions(area_m2=600, frontage_m=20, depth_m=30),
        dcp_controls=[_cov(value_min=None, value_max=50.0)],
    )
    assert r.site_coverage_cap_m2 == 300.0
