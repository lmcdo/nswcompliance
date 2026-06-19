"""GATE-1pt2 range model — compute_constraint_arithmetic emits floor + ceiling.

The dwelling count is a derived illustration of the (form-independent) GFA envelope.
The engine reports an as-of-right floor (the primary dev_type) and, when a ceiling form
is supplied, the permitted-ceiling upside — both off the same envelope. The conservative
``realistic_dwellings`` is unchanged so existing consumers keep the safe number.
"""
from services.constraint_arithmetic import compute_constraint_arithmetic


def _compute(dev_type, ceiling_dev_type):
    # 600 m² lot, FSR 0.5 -> ~300 m² envelope; no height/DCP/SEPP so FSR binds.
    return compute_constraint_arithmetic(
        lot_area_m2=600.0,
        dev_type=dev_type,
        ceiling_dev_type=ceiling_dev_type,
        lep_fsr_str="0.5",
        lep_height_str="8.5",
    )


def test_range_floor_is_conservative_ceiling_is_the_upside():
    r = _compute("dwelling_house", "multi_dwelling_housing")
    # Floor: a dwelling house is ONE dwelling regardless of envelope.
    assert r.as_of_right_form == "dwelling_house"
    assert r.as_of_right_dwellings == 1
    assert r.realistic_dwellings == 1  # unchanged conservative headline
    # Ceiling: multi-dwelling scales with the envelope -> more than one.
    assert r.max_permitted_form == "multi_dwelling_housing"
    assert r.max_permitted_dwellings is not None
    assert r.max_permitted_dwellings > 1


def test_floor_and_ceiling_share_one_envelope():
    r = _compute("dwelling_house", "residential_flat_building")
    # Same GFA envelope underlies both ends; only the counting method differs.
    assert r.realistic_gfa_m2 is not None
    assert r.as_of_right_dwellings == 1
    assert r.max_permitted_dwellings >= r.as_of_right_dwellings


def test_no_ceiling_form_leaves_max_permitted_unset():
    r = _compute("dwelling_house", None)
    assert r.as_of_right_dwellings == 1
    assert r.max_permitted_form is None
    assert r.max_permitted_dwellings is None


def test_dual_occupancy_ceiling_is_two_not_gfa_based():
    # R2 realistic upside: dual occ is exactly 2, never GFA-divided.
    r = _compute("dwelling_house", "dual_occupancy")
    assert r.as_of_right_dwellings == 1
    assert r.max_permitted_dwellings == 2
