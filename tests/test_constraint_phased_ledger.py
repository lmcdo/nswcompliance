"""3a — the computation chain is two labelled phases, each reconciling.

The headline (LEP) phase presents FSR vs height as ALTERNATIVES (min), not a
subtraction chain; the DCP phase is a reconciling erosion ledger where each
GFA-bearing step's output == input - reduction. The two are never one sum.
"""
from services.constraint_arithmetic import compute_constraint_arithmetic
from services.constraint_models import DCPControl, LotDimensions


def _ctrl(t, v, dev="dwelling_house", unit="m"):
    return DCPControl(control_type=t, dev_type=dev, value_min=v, unit=unit)


def _result():
    return compute_constraint_arithmetic(
        lot_area_m2=600,
        dev_type="dwelling_house",
        lep_height_str="11",
        lep_fsr_str="0.75:1",
        lot_dimensions=LotDimensions(area_m2=600, frontage_m=15, depth_m=40),
        dcp_controls=[
            _ctrl("front_setback", 6.0),
            _ctrl("rear_setback", 6.0),
            _ctrl("side_setback", 1.5),
            _ctrl("car_parking", 1.0, unit="spaces"),
        ],
    )


def test_every_step_has_a_phase():
    r = _result()
    assert r.steps
    for s in r.steps:
        assert s.phase in ("lep", "dcp"), f"{s.label} has phase={s.phase!r}"


def test_both_phases_present_and_separable():
    phases = {s.phase for s in _result().steps}
    assert "lep" in phases and "dcp" in phases


def test_dcp_gfa_steps_reconcile():
    # Within the DCP phase, every step that carries a GFA in/out must satisfy
    # output == round(input - reduction, 1). This is the anti-"broken sum" guard.
    r = _result()
    checked = 0
    for s in r.steps:
        if s.phase == "dcp" and s.input_gfa_m2 is not None and s.reduction_m2 is not None \
                and s.output_gfa_m2 is not None:
            assert s.output_gfa_m2 == round(s.input_gfa_m2 - s.reduction_m2, 1), \
                f"{s.label}: {s.input_gfa_m2} - {s.reduction_m2} != {s.output_gfa_m2}"
            checked += 1
    assert checked >= 1, "expected at least the parking step to reconcile in GFA"


def test_lep_steps_are_alternatives_not_a_chain():
    # LEP-phase steps establish the envelope as min(FSR, height) — they are
    # alternatives, so they must NOT chain an input_gfa_m2 from a prior step.
    for s in _result().steps:
        if s.phase == "lep":
            assert s.input_gfa_m2 is None, f"{s.label} should not have a chained input"


def test_height_step_shows_clean_full_lot_envelope():
    # 11m / 3m per storey = 3 storeys; clean height envelope = 600 x 3 = 1800,
    # the headline alternative to the FSR cap (450). Envelope = min(450, 1800) = 450.
    r = _result()
    assert r.lep_max_gfa_from_height_m2 == 1800.0
    assert r.lep_max_gfa_from_fsr_m2 == 450.0
    assert r.lep_envelope_gfa_m2 == 450.0
