"""Tests for numeric_control_review — cell parsing, header classification, diff engine."""

import sys
from pathlib import Path

# Add scripts/ to path so we can import the module
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from numeric_control_review import (
    parse_cell_value,
    classify_header,
    classify_dev_type,
    diff_controls,
    _values_match,
    _extract_condition,
)


# ---------------------------------------------------------------------------
# Cell value parsing
# ---------------------------------------------------------------------------

class TestParseCellValue:
    def test_plain_integer(self):
        result = parse_cell_value("2")
        assert result is not None
        assert result["value_min"] == 2.0

    def test_plain_float(self):
        result = parse_cell_value("1.5")
        assert result is not None
        assert result["value_min"] == 1.5

    def test_percentage(self):
        result = parse_cell_value("30%")
        assert result is not None
        assert result["value_min"] == 30.0
        assert result["unit"] == "%"

    def test_percentage_with_space(self):
        result = parse_cell_value("30 %")
        assert result is not None
        assert result["value_min"] == 30.0
        assert result["unit"] == "%"

    def test_dimension_metres(self):
        result = parse_cell_value("6m")
        assert result is not None
        assert result["value_min"] == 6.0
        assert result["unit"] == "m"

    def test_dimension_metres_spaced(self):
        result = parse_cell_value("6 metres")
        assert result is not None
        assert result["value_min"] == 6.0
        assert result["unit"] == "m"

    def test_range(self):
        result = parse_cell_value("1.5-2.0")
        assert result is not None
        assert result["value_min"] == 1.5
        assert result["value_max"] == 2.0

    def test_range_with_to(self):
        result = parse_cell_value("3 to 6")
        assert result is not None
        assert result["value_min"] == 3.0
        assert result["value_max"] == 6.0

    def test_rate_spaces(self):
        result = parse_cell_value("2 spaces per dwelling")
        assert result is not None
        assert result["value_min"] == 2.0

    def test_empty_cell(self):
        assert parse_cell_value("") is None
        assert parse_cell_value(None) is None

    def test_text_only(self):
        assert parse_cell_value("Not applicable") is None
        assert parse_cell_value("N/A") is None
        assert parse_cell_value("—") is None

    def test_zero_value(self):
        result = parse_cell_value("0")
        assert result is not None
        assert result["value_min"] == 0.0

    def test_decimal_percentage(self):
        result = parse_cell_value("7.5%")
        assert result is not None
        assert result["value_min"] == 7.5
        assert result["unit"] == "%"


# ---------------------------------------------------------------------------
# Header classification
# ---------------------------------------------------------------------------

class TestClassifyHeader:
    def test_parking(self):
        assert classify_header("Car Parking Spaces") == "car_parking"
        assert classify_header("Parking Rate") == "car_parking"

    def test_bicycle(self):
        assert classify_header("Bicycle Parking") == "bicycle_parking"

    def test_setback(self):
        assert classify_header("Front Setback (m)") == "front_setback"
        assert classify_header("Side Setback") == "side_setback"
        assert classify_header("Rear Setback (m)") == "rear_setback"

    def test_coverage(self):
        assert classify_header("Max Site Coverage") == "max_site_coverage"

    def test_landscaping(self):
        assert classify_header("Landscaping %") == "landscaping_min"

    def test_height(self):
        assert classify_header("Building Height") == "max_building_height"

    def test_unknown(self):
        assert classify_header("Notes") is None
        assert classify_header("Reference") is None


# ---------------------------------------------------------------------------
# Dev type classification
# ---------------------------------------------------------------------------

class TestClassifyDevType:
    def test_dwelling_house(self):
        assert classify_dev_type("Dwelling House") == "dwelling_house"
        assert classify_dev_type("Detached Dwelling") == "dwelling_house"

    def test_secondary_dwelling(self):
        assert classify_dev_type("Secondary Dwelling") == "secondary_dwelling"

    def test_rfb(self):
        assert classify_dev_type("Residential Flat Building") == "residential_flat_building"
        assert classify_dev_type("Apartments") == "residential_flat_building"

    def test_dual_occ(self):
        assert classify_dev_type("Dual Occupancy") == "dual_occupancy"
        assert classify_dev_type("Semi-detached Housing") == "dual_occupancy"

    def test_unknown(self):
        assert classify_dev_type("Total") is None
        assert classify_dev_type("Minimum") is None


# ---------------------------------------------------------------------------
# Diff engine
# ---------------------------------------------------------------------------

class TestDiffControls:
    def test_matched_values(self):
        existing = [
            {"id": 1, "dev_type": "dwelling_house", "control_type": "car_parking",
             "value_min": 2, "value_max": None, "unit": "spaces/dwelling",
             "condition": None, "source_text": "2 spaces", "section_ref": "s1",
             "needs_review": False},
        ]
        extracted = [
            {"dev_type": "dwelling_house", "control_type": "car_parking",
             "value_min": 2.0, "value_max": None, "unit": "spaces/dwelling",
             "source_text": "2", "condition": None},
        ]
        result = diff_controls(existing, extracted)
        assert len(result["matched"]) == 1
        assert len(result["changed"]) == 0

    def test_changed_value(self):
        existing = [
            {"id": 1, "dev_type": "dwelling_house", "control_type": "car_parking",
             "value_min": 2, "value_max": None, "unit": "spaces/dwelling",
             "condition": None, "source_text": "2 spaces", "section_ref": "s1",
             "needs_review": False},
        ]
        extracted = [
            {"dev_type": "dwelling_house", "control_type": "car_parking",
             "value_min": 3.0, "value_max": None, "unit": "spaces/dwelling",
             "source_text": "3", "condition": None},
        ]
        result = diff_controls(existing, extracted)
        assert len(result["matched"]) == 0
        assert len(result["changed"]) == 1
        assert result["changed"][0]["db"]["value_min"] == 2
        assert result["changed"][0]["pdf"]["value_min"] == 3.0

    def test_new_row(self):
        existing = []
        extracted = [
            {"dev_type": "boarding_house", "control_type": "car_parking",
             "value_min": 1.0, "value_max": None, "unit": "spaces/dwelling",
             "source_text": "1", "condition": None},
        ]
        result = diff_controls(existing, extracted)
        assert len(result["new"]) == 1
        assert len(result["matched"]) == 0

    def test_missing_row(self):
        existing = [
            {"id": 1, "dev_type": "dwelling_house", "control_type": "car_parking",
             "value_min": 2, "value_max": None, "unit": "spaces/dwelling",
             "condition": None, "source_text": "2 spaces", "section_ref": "s1",
             "needs_review": False},
        ]
        extracted = []
        result = diff_controls(existing, extracted)
        assert len(result["missing"]) == 1
        assert len(result["matched"]) == 0

    def test_no_dev_type_skipped(self):
        """Extracted rows without dev_type should be skipped in diff."""
        existing = []
        extracted = [
            {"dev_type": None, "control_type": "car_parking",
             "value_min": 1.0, "value_max": None},
        ]
        result = diff_controls(existing, extracted)
        assert len(result["new"]) == 0

    def test_zero_matches_zero(self):
        """value_min=0 must match correctly (not treated as None)."""
        existing = [
            {"id": 1, "dev_type": "dwelling_house", "control_type": "front_setback",
             "value_min": 0, "value_max": None, "unit": "m",
             "condition": None, "source_text": "0m", "section_ref": "s1",
             "needs_review": False},
        ]
        extracted = [
            {"dev_type": "dwelling_house", "control_type": "front_setback",
             "value_min": 0.0, "value_max": None, "condition": None},
        ]
        result = diff_controls(existing, extracted)
        assert len(result["matched"]) == 1
        assert len(result["changed"]) == 0


class TestValuesMatch:
    def test_both_none(self):
        assert _values_match(
            {"value_min": None, "value_max": None},
            {"value_min": None, "value_max": None},
        )

    def test_min_mismatch(self):
        assert not _values_match(
            {"value_min": 2, "value_max": None},
            {"value_min": 3, "value_max": None},
        )

    def test_zero_vs_none(self):
        """0 and None must NOT match."""
        assert not _values_match(
            {"value_min": 0, "value_max": None},
            {"value_min": None, "value_max": None},
        )


class TestExtractCondition:
    def test_bedroom_count(self):
        result = _extract_condition(["2 or more bedrooms", "2"], 1, "2 or more bedrooms")
        assert result is not None
        assert "2 or more bed" in result.lower()

    def test_studio(self):
        result = _extract_condition(["Studio", "1"], 1, "Studio")
        assert result is not None
        assert "studio" in result.lower()

    def test_no_condition(self):
        result = _extract_condition(["Dwelling House", "2"], 1, "Dwelling House")
        assert result is None
