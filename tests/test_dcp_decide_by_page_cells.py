"""dcp_decide_by_page_cells.decide: approve only a requirement whose every cell is on its page; skip the rest."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

from dcp_decide_by_page_cells import cells, decide, norm  # noqa: E402

PAGE = norm("7.2.6 Bicycle Parking Office Employee 0.5 spaces per 100m2 GFA Visitor 1.25 space per 2000m2 GFA")


def test_a_requirement_with_every_cell_on_the_page_is_approved():
    row = "# 7.2.6 Bicycle Parking\nOffice | Employee 0.5 spaces per 100m2 GFA | Visitor 1.25 space per 2000m2 GFA"
    assert decide("added", row, PAGE) == "approve"


def test_one_cell_not_on_the_page_is_skipped():
    row = "# 7.2.6 Bicycle Parking\nOffice | Employee 0.5 spaces per 100m2 GFA | Visitor 2.5 space per 2000m2 GFA"
    assert decide("added", row, PAGE) == "skip"


def test_a_removal_is_never_approved_here():
    assert decide("removed", "Office | Employee 0.5 spaces per 100m2 GFA", PAGE) == "skip"


def test_text_that_is_not_a_requirement_is_skipped():
    page = norm("5.2 Assessment of Significance The hospital was established in 1922 as a memorial")
    assert decide("added", "# 5.2 Assessment of Significance\nThe hospital was established in 1922", page) == "skip"


def test_a_colour_table_is_skipped_even_though_it_is_on_the_page():
    page = norm("Annexure B8-1 Colour name Olive Mist green G54")
    assert decide("added", "# 16.2 Colour name\nOlive | Mist green | G54", page) == "skip"


def test_cells_drop_the_heading_line():
    assert cells("# 7.2.6 Bicycle Parking\nA | Bcde") == ["Bcde"]
