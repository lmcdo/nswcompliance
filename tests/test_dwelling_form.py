"""GATE-1 (part 1) — dwelling yield must respect the permitted built form.

The engine previously divided the GFA envelope by ~65 m2 regardless of form, so a
dwelling house on R2 reported "6 dwellings" (397 / 65). By the Standard Instrument
a dwelling house is ONE dwelling; only multi-unit forms scale with GFA.
"""
import pytest

from services.constraint_arithmetic import (
    _dwellings_for_form,
    compute_constraint_arithmetic,
)


@pytest.mark.parametrize("dev_type,gfa_based,expected", [
    ("dwelling_house", 6, 1),
    ("DwellingHouse", 6, 1),
    ("dual_occupancy", 6, 2),
    ("secondary_dwelling", 6, 2),
    ("residential_flat_building", 6, 6),
    ("apartment", 5, 5),
    ("multi_dwelling_housing", 4, 4),
    ("townhouse", 3, 3),
    ("terrace", 3, 3),
    ("manor_house", 4, 4),
    ("", 6, 1),
    ("some_other_use", 6, 1),
])
def test_dwellings_for_form(dev_type, gfa_based, expected):
    assert _dwellings_for_form(dev_type, gfa_based) == expected


def test_dwelling_house_yields_one_not_gfa_over_65():
    """Regression: Haberfield-like lot (793 m2, FSR 0.5, height 7 -> envelope
    ~397 m2). Pre-GATE-1 this returned 6 (397 / 65)."""
    r = compute_constraint_arithmetic(
        lot_area_m2=793,
        dev_type="dwelling_house",
        lep_height_str="7",
        lep_fsr_str="0.5",
    )
    assert r.realistic_dwellings == 1


def test_dual_occupancy_yields_two():
    r = compute_constraint_arithmetic(
        lot_area_m2=793,
        dev_type="dual_occupancy",
        lep_height_str="7",
        lep_fsr_str="0.5",
    )
    assert r.realistic_dwellings == 2


def test_residential_flat_building_scales_with_gfa():
    r = compute_constraint_arithmetic(
        lot_area_m2=793,
        dev_type="residential_flat_building",
        lep_height_str="7",
        lep_fsr_str="0.5",
    )
    assert r.realistic_dwellings > 1
