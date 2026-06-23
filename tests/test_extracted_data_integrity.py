"""Generic, reusable integrity checks for extracted-data tables.

These lock the domain-agnostic engine (fabricated_values / conflicting_values /
assert_clean_row) that the setback validator and any future table-specific check
build on. The point of generalising: the same "stored a guess" / "two clashing
values" bug class exists in every extracted table, so the engine is written once
and configured per table.
"""

import pytest

from services.extracted_data_integrity import (
    fabricated_values,
    conflicting_values,
    assert_clean_row,
)


# --- fabricated_values ------------------------------------------------------

class TestFabricatedValues:
    def test_value_with_assumed_marker_flagged(self):
        rows = [{"v": 24, "note": "Assumed standard NSW POS min — verify"}]
        assert len(fabricated_values(rows, value_field="v", marker_fields=["note"])) == 1

    def test_null_value_with_marker_is_clean(self):
        # The fixed state: unverified row records no value -> not a fabrication.
        rows = [{"v": None, "note": "Assumed standard NSW — verify"}]
        assert fabricated_values(rows, value_field="v", marker_fields=["note"]) == []

    def test_real_value_no_marker_is_clean(self):
        rows = [{"v": 6.0, "note": "Front setback 6m to street boundary (DCP s4.2)"}]
        assert fabricated_values(rows, value_field="v", marker_fields=["note"]) == []

    def test_scans_all_marker_fields(self):
        rows = [{"v": 3, "cond": "", "reason": "standard_pattern_assumed"}]
        assert len(fabricated_values(rows, value_field="v", marker_fields=["cond", "reason"])) == 1


# --- conflicting_values -----------------------------------------------------

class TestConflictingValues:
    def test_contradictory_values_flagged(self):
        rows = [
            {"lga": "x", "zone": "R2", "use": "dwelling", "perm": "Permitted"},
            {"lga": "x", "zone": "R2", "use": "dwelling", "perm": "Prohibited"},
        ]
        out = conflicting_values(rows, key_fields=["lga", "zone", "use"], value_field="perm")
        assert len(out) == 1 and out[0]["values"] == ["permitted", "prohibited"]

    def test_same_value_case_insensitive_not_conflict(self):
        rows = [{"k": 1, "perm": "Permitted"}, {"k": 1, "perm": "permitted"}]
        assert conflicting_values(rows, key_fields=["k"], value_field="perm") == []

    def test_condition_resolves_conflict(self):
        rows = [
            {"k": 1, "v": 3, "cond": "single storey"},
            {"k": 1, "v": 6, "cond": "two storey"},
        ]
        assert conflicting_values(rows, key_fields=["k"], value_field="v", condition_field="cond") == []

    def test_list_valued_key_is_hashable(self):
        # Array columns (e.g. applicable_zones text[]) must not crash the grouping.
        rows = [
            {"dt": "dual_occ", "st": "max_fsr", "zones": ["R2", "R3"], "v": 0.5},
            {"dt": "dual_occ", "st": "max_fsr", "zones": ["R2", "R3"], "v": 0.65},
        ]
        out = conflicting_values(rows, key_fields=["dt", "st", "zones"], value_field="v")
        assert len(out) == 1


# --- assert_clean_row (write-time gate) -------------------------------------

class TestWriteGate:
    def test_raises_on_fabricated_value(self):
        with pytest.raises(ValueError, match="fabricated"):
            assert_clean_row(
                {"v": 24, "note": "Assumed standard NSW POS min — verify"},
                value_field="v", marker_fields=["note"],
            )

    def test_passes_clean_value(self):
        assert_clean_row(
            {"v": 6.0, "note": "Front setback 6m (DCP s4.2)"},
            value_field="v", marker_fields=["note"],
        )  # no raise

    def test_passes_null_value_with_marker(self):
        # Honest unverified row (value NULL) is allowed.
        assert_clean_row(
            {"v": None, "note": "Assumed — verify against DCP"},
            value_field="v", marker_fields=["note"],
        )  # no raise
