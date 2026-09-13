"""Row data and quote matcher for scripts/insert_strathfield_general_residential.py (no DB, no PDF)."""
import importlib.util
from pathlib import Path

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "insert_strathfield_general_residential.py"
_spec = importlib.util.spec_from_file_location("insert_strathfield_general_residential", SCRIPT)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

# Live CHECK constraints on dcp_setback_controls (read 2026-09-13).
CANONICAL_CONTROL_TYPES = {
    "front_setback", "secondary_street_setback", "side_setback", "rear_setback", "separation_from_dwelling",
    "privacy_separation", "car_parking", "bicycle_parking", "driveway_width", "driveway_gradient",
    "max_site_coverage", "max_height", "max_floor_area", "dwelling_size_min", "fencing_height_max",
    "landscaping_min", "front_setback_landscaping", "deep_soil_min", "tree_canopy_min",
    "communal_open_space_min", "private_open_space", "solar_access_hours",
}
APPLICABILITIES = {"universal_residential", "secondary_dwelling_specific", "zone_specific", "precinct_specific",
                   "development_specific", "sepp_statewide", "sepp_cdc_only"}
SERVED_DEV_TYPES = {"dwelling_house", "dual_occupancy", "multi_dwelling_housing", "secondary_dwelling"}
REQUIRED = {"lga", "dev_type", "control_type", "value_min", "value_max", "unit", "condition", "applicability",
            "source_text", "section_ref", "pdf_page", "needs_review", "dcp_version", "source_chapter_key"}
ROWS = mod.ROWS


def test_row_count_and_types_served():
    assert len(ROWS) >= 50
    assert {r["dev_type"] for r in ROWS} == SERVED_DEV_TYPES


@pytest.mark.parametrize("r", ROWS, ids=lambda r: f"{r['dev_type']}-{r['control_type']}-{r['section_ref']}")
def test_row_fields_and_constraints(r):
    assert REQUIRED <= set(r)
    assert r["lga"] == "strathfield" and r["needs_review"] is False
    assert r["control_type"] in CANONICAL_CONTROL_TYPES
    assert r["applicability"] in APPLICABILITIES
    assert isinstance(r["pdf_page"], int) and 1 <= r["pdf_page"] <= mod.PDF_PAGES
    assert r["section_ref"].startswith(mod.SOURCE_CHAPTER_KEY + "#C")
    assert r["source_text"].strip() and r["condition"]
    assert "max_height" != r["control_type"], "storeys rows are held by the DQ rule; none are inserted"


@pytest.mark.parametrize("r", [r for r in ROWS if r["value_min"] is not None or r["value_max"] is not None],
                         ids=lambda r: f"{r['dev_type']}-{r['control_type']}-{r['section_ref']}")
def test_stored_number_is_printed_in_its_quote(r):
    value = r["value_min"] if r["value_min"] is not None else r["value_max"]
    printed = {f"{value:g}", f"{int(round(value * 1000))}mm"}
    assert any(p in r["source_text"] for p in printed), (value, r["source_text"])


def test_maximums_are_stored_as_ceilings():
    for r in ROWS:
        if r["control_type"] == "fencing_height_max":
            assert r["value_min"] is None and r["value_max"] is not None


def test_no_duplicate_live_keys():
    keys = [(r["dev_type"], r["control_type"], r["condition"]) for r in ROWS]
    assert len(keys) == len(set(keys))


def test_supersede_list_is_the_23_hidden_rows():
    assert len(mod.SUPERSEDE_IDS) == len(set(mod.SUPERSEDE_IDS)) == 23
    assert mod.EFFECTIVE_DATE == "2026-09-01" and mod.EFFECTIVE_DATE_BASIS == "stated_in_document"


PAGE = ("12 Strathfield Development Control Plan – General Residential Development C3.3 Side setbacks – "
        "Dwellings and Dual Occupancies C3.3.1 The minimum side setback for two (2)\nstorey developments is 1.2m. "
        "Lots less than or equal to 750m² 30%")


def test_quote_found_across_line_breaks_dashes_and_superscripts():
    assert mod.quote_on_page("C3.3 Side setbacks - Dwellings and Dual Occupancies C3.3.1 The minimum side "
                             "setback for two (2) storey developments is 1.2m.", PAGE)
    assert mod.quote_on_page("C3.3.1 The minimum" + mod.SEGMENT + "less than or equal to 750m2 30%", PAGE)


def test_quote_with_a_changed_number_is_rejected():
    assert not mod.quote_on_page("C3.3.1 The minimum side setback for two (2) storey developments is 1.5m.", PAGE)


def test_segments_out_of_order_are_rejected():
    assert not mod.quote_on_page("Lots less than or equal to 750m² 30%" + mod.SEGMENT + "C3.3.1 The minimum", PAGE)


def test_empty_segment_is_rejected():
    assert not mod.quote_on_page("C3.3.1" + mod.SEGMENT + "   ", PAGE)


def test_apply_without_pdf_refuses_before_touching_the_database():
    assert mod.main(["--apply"]) == 2
