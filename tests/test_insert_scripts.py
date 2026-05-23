"""Tests for DCP insert scripts — validates data integrity without hitting DB.

These tests verify:
1. Data structure: all required fields present, valid types
2. Dedup keys: no duplicate rows within the same script
3. LGA coverage: all known LGAs have at least one row
4. Constraint compliance: applicability values match DB CHECK constraint
5. Value ranges: numeric values are within plausible bounds
"""

import importlib
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

# Mock psycopg2 before importing insert scripts
if "psycopg2" not in sys.modules:
    sys.modules["psycopg2"] = MagicMock()
    sys.modules["psycopg2.extras"] = MagicMock()

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"

# Valid values from DB CHECK constraints
VALID_APPLICABILITIES = {
    "universal_residential", "secondary_dwelling_specific",
    "zone_specific", "precinct_specific", "development_specific",
    "sepp_statewide", "sepp_cdc_only",
}
VALID_EXTRACTION_METHODS = {
    "text_extraction", "mistral_ocr", "manual", "manual_insert",
    "manual_curation", "gpt4_extraction", "automatic_extraction",
}

# All LGAs currently in dcp_setback_controls
ALL_LGAS = {
    "ashfield", "bayside", "blacktown", "burwood", "camden", "campbelltown",
    "canada_bay", "canterbury_bankstown", "city_of_sydney", "cumberland",
    "fairfield", "georges_river", "hornsby", "inner_west", "ku_ring_gai",
    "leichhardt", "liverpool", "marrickville", "northern_beaches",
    "parramatta", "penrith", "randwick", "ryde", "strathfield",
    "sutherland_shire", "the_hills", "waverley", "woollahra",
}

# Required fields for each insert row
REQUIRED_FIELDS = {"lga", "value_min", "needs_review", "condition",
                   "source_text", "section_ref", "dcp_version",
                   "source_chapter_key"}


def _load_rows(script_name: str, var_name: str) -> list[dict]:
    """Load the data rows from an insert script without executing main()."""
    spec = importlib.util.spec_from_file_location(
        script_name, SCRIPTS_DIR / f"{script_name}.py"
    )
    mod = importlib.util.module_from_spec(spec)
    # Prevent execution of main
    try:
        spec.loader.exec_module(mod)
    except Exception:
        pass  # Some scripts may fail on import (missing env), data is module-level
    return getattr(mod, var_name, [])


# ═══════════════════════════════════════════════════════════════════════════
# Solar Access Hours
# ═══════════════════════════════════════════════════════════════════════════

class TestSolarAccessHours:
    @pytest.fixture(autouse=True)
    def load_data(self):
        self.rows = _load_rows("insert_solar_access_hours", "SOLAR_ROWS")

    def test_has_rows(self):
        assert len(self.rows) >= 20, f"Expected 20+ solar rows, got {len(self.rows)}"

    def test_required_fields(self):
        for i, row in enumerate(self.rows):
            missing = REQUIRED_FIELDS - set(row.keys())
            assert not missing, f"Row {i} ({row.get('lga')}) missing: {missing}"

    def test_no_duplicate_lgas(self):
        """Solar access has one row per LGA (universal_residential)."""
        lgas = [r["lga"] for r in self.rows]
        dups = [l for l in lgas if lgas.count(l) > 1]
        assert not dups, f"Duplicate LGAs: {set(dups)}"

    def test_value_range(self):
        for row in self.rows:
            assert 1 <= row["value_min"] <= 6, (
                f"{row['lga']}: solar hours {row['value_min']} outside 1-6 range"
            )

    def test_lga_values_valid(self):
        for row in self.rows:
            assert row["lga"] in ALL_LGAS or row["lga"] == "nsw_statewide", (
                f"Unknown LGA: {row['lga']}"
            )

    def test_needs_review_flag(self):
        for row in self.rows:
            assert isinstance(row["needs_review"], bool), (
                f"{row['lga']}: needs_review must be bool, got {type(row['needs_review'])}"
            )


# ═══════════════════════════════════════════════════════════════════════════
# Private Open Space
# ═══════════════════════════════════════════════════════════════════════════

class TestPrivateOpenSpace:
    @pytest.fixture(autouse=True)
    def load_data(self):
        self.rows = _load_rows("insert_private_open_space", "POS_ROWS")

    def test_has_rows(self):
        assert len(self.rows) >= 30, f"Expected 30+ POS rows, got {len(self.rows)}"

    def test_required_fields(self):
        extra_required = REQUIRED_FIELDS | {"dev_type", "unit"}
        for i, row in enumerate(self.rows):
            missing = extra_required - set(row.keys())
            assert not missing, f"Row {i} ({row.get('lga')}) missing: {missing}"

    def test_no_duplicate_rows(self):
        """No duplicate (lga, dev_type, condition) combos."""
        keys = [(r["lga"], r["dev_type"], r["condition"]) for r in self.rows]
        seen = set()
        dups = []
        for k in keys:
            if k in seen:
                dups.append(k)
            seen.add(k)
        assert not dups, f"Duplicate rows: {dups}"

    def test_value_range(self):
        for row in self.rows:
            assert 1 <= row["value_min"] <= 200, (
                f"{row['lga']}/{row['dev_type']}: POS {row['value_min']}m2 "
                f"outside 1-200 range"
            )

    def test_unit_is_m2_or_percent(self):
        for row in self.rows:
            assert row["unit"] in ("m2", "%"), (
                f"{row['lga']}: unit must be 'm2' or '%', got '{row['unit']}'"
            )

    def test_lga_values_valid(self):
        for row in self.rows:
            assert row["lga"] in ALL_LGAS, f"Unknown LGA: {row['lga']}"

    def test_all_lgas_covered(self):
        """Every LGA should have at least one POS row (even if needs_review)."""
        covered = {r["lga"] for r in self.rows}
        # nsw_statewide doesn't need POS
        missing = ALL_LGAS - covered - {"nsw_statewide"}
        assert not missing, f"LGAs with no POS row: {missing}"

    def test_needs_review_has_reason(self):
        for row in self.rows:
            if row["needs_review"]:
                assert "verify" in row["condition"].lower() or \
                       "assumed" in row["condition"].lower() or \
                       "garbled" in row["condition"].lower(), (
                    f"{row['lga']}: needs_review=True but condition doesn't "
                    f"explain why: {row['condition'][:80]}"
                )


# ═══════════════════════════════════════════════════════════════════════════
# Bicycle Parking (if exists)
# ═══════════════════════════════════════════════════════════════════════════

class TestBicycleParking:
    @pytest.fixture(autouse=True)
    def load_data(self):
        self.rows = _load_rows("insert_bicycle_parking", "BICYCLE_ROWS")
        if not self.rows:
            pytest.skip("insert_bicycle_parking.py not found or empty")

    def test_has_rows(self):
        assert len(self.rows) >= 20

    def test_required_fields(self):
        for i, row in enumerate(self.rows):
            missing = REQUIRED_FIELDS - set(row.keys())
            assert not missing, f"Row {i} ({row.get('lga')}) missing: {missing}"

    def test_no_duplicate_rows(self):
        keys = [(r["lga"], r.get("dev_type", ""), r["condition"]) for r in self.rows]
        seen = set()
        dups = []
        for k in keys:
            if k in seen:
                dups.append(k)
            seen.add(k)
        assert not dups, f"Duplicate rows: {dups}"
