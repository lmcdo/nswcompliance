"""Row data, source pin and quote matcher for scripts/insert_strathfield_general_residential.py (no DB, no PDF)."""
import importlib.util
import re
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
            "source_text", "section_ref", "pdf_page", "needs_review", "dcp_version", "source_chapter_key",
            "zones_include", "zones_exclude", "plain_summary"}
LIABILITY_WORDS = re.compile(r"\b(safe|feasible|compliant|should|recommend|suitable|adequate|sufficient|approved|"
                             r"guaranteed|certified|confirmed|verified|ensure|assure|accurate|definitive|"
                             r"comprehensive|reliable)\b", re.I)
ROWS = mod.ROWS


def printed(value, quote: str) -> bool:
    """The number stands alone in the quote: not part of a clause id (C3.1.1), a longer number (16) or a decimal."""
    forms = {f"{value:g}"} | ({f"{int(round(value * 1000))}mm"} if value < 100 else set())
    return any(re.search(rf"(?<![\w.,]){re.escape(f)}(?!\d|[.,]\d)", quote) for f in forms)


def test_row_count_and_types_served():
    assert len(ROWS) == 55
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


@pytest.mark.parametrize("r", ROWS, ids=lambda r: f"{r['dev_type']}-{r['control_type']}-{r['section_ref']}")
def test_every_stored_number_stands_alone_in_its_quote(r):
    for value in (r["value_min"], r["value_max"]):
        if value is not None:
            assert printed(value, r["source_text"]), (value, r["source_text"])


def test_number_check_rejects_clause_ids_and_longer_numbers():
    assert not printed(3, "C3.1.1 The minimum front building setback is 10m")
    assert not printed(6, "a setback of 16m")
    assert not printed(1.5, "Lots less than 1,500m² 25%")
    assert printed(1.2, "no higher than 1200mm.")
    assert printed(3, "the secondary street side setback is 3m.")


@pytest.mark.parametrize("r", ROWS, ids=lambda r: f"{r['dev_type']}-{r['control_type']}-{r['section_ref']}")
def test_condition_uses_no_unquoted_liability_word(r):
    assert not LIABILITY_WORDS.search(r["condition"]), r["condition"]


@pytest.mark.parametrize("dev_type", ["dwelling_house", "dual_occupancy", "multi_dwelling_housing"])
def test_r2_rear_setback_is_the_range_its_formula_can_produce(dev_type):
    rear = [r for r in ROWS if r["dev_type"] == dev_type and r["control_type"] == "rear_setback"]
    r2 = [r for r in rear if r["section_ref"].endswith("#C3.6.1")]
    other = [r for r in rear if r["section_ref"].endswith("#C3.6.2")]
    assert len(rear) == 2 and len(r2) == 1 and len(other) == 1
    assert (r2[0]["value_min"], r2[0]["value_max"], r2[0]["applicability"]) == (6, 10, "zone_specific")
    assert (other[0]["value_min"], other[0]["value_max"], other[0]["applicability"]) == (6, None, "zone_specific")
    assert "20% of the average length" in r2[0]["condition"] and "other than the low density" in other[0]["condition"]


# DQ-32b's pattern (scripts/dq_probe_live.py): a zone code in a condition.
ZONE_CODE = re.compile(r"\b(R[1-6]|E[1-4]|C[1-4]|MU1|RU[1-6]|B[1-8]|IN[1-4]|SP[1-3]|W[1-4])\b", re.I)


@pytest.mark.parametrize("r", ROWS, ids=lambda r: f"{r['dev_type']}-{r['control_type']}-{r['section_ref']}")
def test_zone_code_in_a_condition_only_on_zone_specific_rows(r):
    if r["applicability"] != "zone_specific":
        assert not ZONE_CODE.search(r["condition"]), r["condition"]


_CDB_SPEC = importlib.util.spec_from_file_location(
    "conveyancing_db", Path(__file__).parent.parent / "scripts" / "conveyancing_db.py")
cdb = importlib.util.module_from_spec(_CDB_SPEC)
_CDB_SPEC.loader.exec_module(cdb)


@pytest.mark.parametrize("zone", ["R2", "R3", "R4", "E1"])  # noqa: zone-codes (sample site zones)
@pytest.mark.parametrize("dev_type", ["dwelling_house", "dual_occupancy", "multi_dwelling_housing"])
def test_served_zone_filter_keeps_each_zone_its_own_rows(zone, dev_type):
    """The real filter (conveyancing_db.zone_row_applies) with each row's explicit zone scope: the R2 figures
    only for an R2 site, the other-zones figures for every zone except R2 - never both."""
    kept = [r for r in ROWS if r["dev_type"] == dev_type
            and cdb.zone_row_applies(r["applicability"], r["condition"], zone, r["zones_include"], r["zones_exclude"])]
    rear = {(r["value_min"], r["value_max"]) for r in kept if r["control_type"] == "rear_setback"}
    assert ((6, 10) in rear) == (zone == "R2")
    assert ((6, None) in rear) == (zone != "R2"), "the other-zones 6m rear row is not for an R2 site"
    assert len(rear) == 1
    if dev_type == "multi_dwelling_housing":
        side = {r["value_min"] for r in kept if r["control_type"] == "side_setback"}
        assert ({5, 3} <= side) == (zone == "R2")
        assert (4 in side) == (zone != "R2") and ({4, 2} <= side) == (zone != "R2")
        assert 5 not in side or zone == "R2"


@pytest.mark.parametrize("r", ROWS, ids=lambda r: f"{r['dev_type']}-{r['control_type']}-{r['section_ref']}")
def test_every_zone_specific_row_carries_exactly_one_explicit_scope(r):
    scoped = [bool(r["zones_include"]), bool(r["zones_exclude"])]
    if r["applicability"] == "zone_specific":
        assert scoped.count(True) == 1, r["condition"]
    else:
        assert scoped == [False, False], r["condition"]


@pytest.mark.parametrize("r", ROWS, ids=lambda r: f"{r['dev_type']}-{r['control_type']}-{r['section_ref']}")
def test_a_row_without_a_number_carries_plain_wording(r):
    if r["value_min"] is None and r["value_max"] is None:
        assert r["plain_summary"] and len(r["plain_summary"]) <= 40, r["condition"]
        assert not LIABILITY_WORDS.search(r["plain_summary"]), r["plain_summary"]
    else:
        assert r["plain_summary"] is None, "a row with a number shows the number"


def test_maximums_are_stored_as_ceilings():
    for r in ROWS:
        if r["control_type"] == "fencing_height_max":
            assert r["value_min"] is None and r["value_max"] is not None


def test_no_duplicate_live_keys():
    keys = [(r["dev_type"], r["control_type"], r["condition"]) for r in ROWS]
    assert len(keys) == len(set(keys))


def test_supersede_list_and_source_pin():
    assert len(mod.SUPERSEDE_IDS) == len(set(mod.SUPERSEDE_IDS)) == 23
    assert mod.EFFECTIVE_DATE == "2026-09-01" and mod.EFFECTIVE_DATE_BASIS == "stated_in_document"
    assert re.fullmatch(r"[0-9a-f]{64}", mod.SOURCE_SHA256)


def test_a_file_that_is_not_the_pinned_plan_is_rejected_before_reading_pages(tmp_path):
    other = tmp_path / "draft.pdf"
    other.write_bytes(b"%PDF-1.7 a draft that keeps the same wording")
    problems = mod.check_against_pdf(other)
    assert len(problems) == 1 and "not the pinned General Residential DCP" in problems[0]


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
