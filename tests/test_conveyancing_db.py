"""Adversarial unit tests for conveyancing_db.py pure-logic functions.

Tests target boundary values, empty strings, None inputs, unknown classes,
and the zone filter / heritage classification logic introduced in PR #378.

No DB connections needed — tests exercise string parsing, classification,
and row-processing logic only.
"""

import importlib.util
import os
import pytest
from unittest.mock import MagicMock

# Load module
_spec = importlib.util.spec_from_file_location(
    "conveyancing_db",
    os.path.join(os.path.dirname(__file__), "..", "scripts", "conveyancing_db.py"),
)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

normalise_clauses = _mod.normalise_clauses
interpret_sepp = _mod.interpret_sepp
_HCA_VALUES = _mod._HCA_VALUES
_ITEM_VALUES = _mod._ITEM_VALUES
_CONTROL_TYPE_LABELS = _mod._CONTROL_TYPE_LABELS
_LGA_SLUG_TO_DCP_NAME = _mod._LGA_SLUG_TO_DCP_NAME
fetch_dcp_setbacks = _mod.fetch_dcp_setbacks
fetch_heritage_postgis = _mod.fetch_heritage_postgis
fetch_lep_clauses = _mod.fetch_lep_clauses


# ── normalise_clauses ──


class TestNormaliseClauses:
    def test_single_clause(self):
        assert normalise_clauses("Clause 4.3C") == ["4.3C"]

    def test_multiple_comma_separated(self):
        assert normalise_clauses("Clauses 4.3C, 4.4") == ["4.3C", "4.4"]

    def test_and_separator(self):
        assert normalise_clauses("Clauses 4.3C and 4.4") == ["4.3C", "4.4"]

    def test_cl_prefix(self):
        assert normalise_clauses("cl. 4.3C") == ["4.3C"]

    def test_semicolon_separator(self):
        assert normalise_clauses("Clause 6.14; 6.15") == ["6.14", "6.15"]

    def test_mixed_separators(self):
        result = normalise_clauses("Clauses 1.1, 2.2 and 3.3")
        assert result == ["1.1", "2.2", "3.3"]

    # --- Adversarial inputs ---

    def test_empty_string(self):
        assert normalise_clauses("") == []

    def test_none_input(self):
        assert normalise_clauses(None) == []

    def test_whitespace_only(self):
        assert normalise_clauses("   ") == []

    def test_just_prefix_no_number(self):
        assert normalise_clauses("Clause") == []

    def test_just_prefix_with_space(self):
        assert normalise_clauses("Clause ") == []

    def test_no_prefix_bare_number(self):
        assert normalise_clauses("4.3C") == ["4.3C"]

    def test_case_insensitive_prefix(self):
        assert normalise_clauses("CLAUSE 4.3C") == ["4.3C"]
        assert normalise_clauses("clause 4.3C") == ["4.3C"]

    def test_multiple_commas_no_content(self):
        assert normalise_clauses("Clause ,,,") == []

    def test_trailing_comma(self):
        assert normalise_clauses("Clause 4.3C,") == ["4.3C"]

    def test_leading_and(self):
        assert normalise_clauses("and 4.3C") == ["4.3C"]


# ── interpret_sepp ──


class TestInterpretSepp:
    def test_normal_overlay(self):
        result = interpret_sepp("SEPP 65", "Design Quality", "Apartment", "https://example.com")
        assert result is not None
        assert "Design Quality" in result
        assert "Apartment" in result
        assert "https://example.com" in result

    def test_same_type_and_label(self):
        result = interpret_sepp("SEPP", "Flood", "Flood", "")
        assert result is not None
        assert result.count("Flood") == 1

    def test_case_insensitive_dedup(self):
        result = interpret_sepp("SEPP", "flood", "Flood", "")
        assert result is not None
        # Should not duplicate — "flood" and "Flood" match case-insensitively
        assert "flood" in result.lower()

    def test_no_url(self):
        result = interpret_sepp("SEPP", "Noise", "Aircraft", "")
        assert result is not None
        assert "See" not in result

    # --- Suppress types ---

    def test_suppresses_bushfire(self):
        assert interpret_sepp("SEPP", "Bushfire Prone Land", "Category 1", "") is None

    def test_suppresses_tod(self):
        assert interpret_sepp("SEPP", "Transport Oriented Development", "", "") is None

    def test_suppresses_anef(self):
        assert interpret_sepp("SEPP", "ANEF Contour", "25+", "") is None

    def test_suppresses_case_insensitive(self):
        assert interpret_sepp("SEPP", "BUSHFIRE", "Cat 1", "") is None

    def test_suppresses_substring_match(self):
        assert interpret_sepp("SEPP", "Aircraft Noise Exposure", "30+", "") is None

    # --- Adversarial inputs ---

    def test_empty_type_and_label(self):
        result = interpret_sepp("My SEPP", "", "", "")
        assert result is not None
        assert "My SEPP" in result

    def test_all_empty(self):
        result = interpret_sepp("", "", "", "")
        assert result is not None
        assert "SEPP overlay" in result

    def test_none_type(self):
        result = interpret_sepp("SEPP", None, "Label", "")
        assert result is not None
        assert "Label" in result

    def test_none_label(self):
        result = interpret_sepp("SEPP", "Type", None, "")
        assert result is not None
        assert "Type" in result

    def test_none_type_and_label(self):
        result = interpret_sepp("SEPP", None, None, "")
        assert result is not None


# ── Zone filter logic (fetch_dcp_setbacks internals) ──


def _mock_conn(rows, reg_row=None):
    """Create a mock psycopg2 connection returning given rows."""
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    cursor.fetchone.return_value = reg_row
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


def _make_row(
    dev_type="dwelling_house",
    ctrl_type="front_setback",
    vmin=6.0, vmax=None, unit="m",
    condition=None, source_text=None,
    section_ref="C2.1", applicability="universal_residential",
    # Added 2026-08-09. fetch_dcp_setbacks gained four columns —
    # needs_review, source_chapter_key, pdf_page, dcp_version — and this
    # fixture still returned the old 9-tuple, so every test using it died on
    # "not enough values to unpack (expected 13, got 9)". The fixture drifted
    # behind the query it stands in for; the production code was never wrong.
    needs_review=False,
    source_chapter_key="woollahra-dcp-2015-part-c2",
    pdf_page=None,
    dcp_version="DCP 2015",
    # Added 2026-09-14 with migration 072: explicit zone scope and plain wording.
    zones_include=None,
    zones_exclude=None,
    plain_summary=None,
):
    # needs_review defaults to False deliberately. fetch_dcp_setbacks applies a
    # fail-closed per-row guard that drops flagged controls, so defaulting to
    # True would silently empty every result and the tests would "pass" by
    # asserting on nothing.
    return (dev_type, ctrl_type, vmin, vmax, unit, condition, source_text,
            section_ref, applicability, needs_review, source_chapter_key,
            pdf_page, dcp_version, zones_include, zones_exclude, plain_summary)


class TestZoneFilter:
    def test_universal_row_always_included(self):
        rows = [_make_row(applicability="universal_residential", condition="Applies to all zones")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra", zone_code="R2")
        assert len(result["setbacks"]) == 1

    def test_zone_specific_matching_zone_included(self):
        rows = [_make_row(applicability="zone_specific", condition="Applies to R2 Low Density")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra", zone_code="R2 Low Density Residential")
        assert len(result["setbacks"]) == 1

    def test_zone_specific_different_zone_excluded(self):
        rows = [_make_row(applicability="zone_specific", condition="Applies to R4 High Density only")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra", zone_code="R2 Low Density Residential")
        assert len(result["setbacks"]) == 0

    def test_zone_specific_no_condition_text_included(self):
        rows = [_make_row(applicability="zone_specific", condition=None)]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra", zone_code="R2")
        assert len(result["setbacks"]) == 1

    def test_zone_specific_condition_no_known_zones_included(self):
        rows = [_make_row(applicability="zone_specific", condition="Only for corner lots")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra", zone_code="R2")
        assert len(result["setbacks"]) == 1

    def test_no_zone_code_includes_all(self):
        rows = [
            _make_row(applicability="zone_specific", condition="Applies to R4 only"),
            _make_row(applicability="universal_residential"),
        ]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra", zone_code=None)
        assert len(result["setbacks"]) == 2

    # --- Adversarial zone_code inputs ---

    def test_empty_string_zone_code(self):
        rows = [_make_row(applicability="zone_specific", condition="R4 only")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra", zone_code="")
        assert len(result["setbacks"]) == 1  # empty = no filter

    def test_whitespace_only_zone_code(self):
        rows = [_make_row(applicability="zone_specific", condition="R4 only")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra", zone_code="   ")
        assert len(result["setbacks"]) == 1  # whitespace = no filter, no crash

    def test_zone_code_case_insensitive(self):
        rows = [_make_row(applicability="zone_specific", condition="Applies to R2")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra", zone_code="r2 low density")
        assert len(result["setbacks"]) == 1

    # --- Zone codes of every family; exclusion wording is never guessed (zone_row_applies) ---

    def test_every_zone_family_limits_a_row_to_its_zone(self):
        # The old 10-code list missed SP, RU, RE, IN, W and most E/B codes: an "SP2 only" row reached R2 sites.
        pairs = (("SP2", "R2"), ("RU5", "R2"), ("IN2", "R3"), ("W1", "R2"), ("RE1", "R4"), ("E3", "R2"), ("B4", "R3"))  # noqa: zone-codes (test zones)
        for code, other in pairs:
            only = f"{code} zone only"
            assert _mod.zone_row_applies("zone_specific", only, code), (only, code)
            assert not _mod.zone_row_applies("zone_specific", only, other), (only, other)

    def test_exclusion_wording_keeps_the_row_for_every_zone(self):
        # A zone named beside exclusion wording may be the zone the row does NOT apply to. Each parser tried was
        # inverted by a new wording, so the row is kept for every zone with its condition shown - never served
        # only to the excluded zone, never dropped where it applies.
        wordings = (
            "zones other than the R2 zone", "all zones except for R2", "all zones with the exception of R2",
            "other than R2 Foreshore and R3 zones", "other than R2. R3 zone only", "excluding land zoned R2",  # noqa: zone-codes (test condition text)
            "not in the R2 Low Density zone", "apart from R2", "outside the R2 zone", "R2 zone, except corner lots",
        )
        for cond in wordings:
            for zone in ("R2", "R3", "R4", "SP2"):  # noqa: zone-codes (sample site zones)
                assert _mod.zone_row_applies("zone_specific", cond, zone), (cond, zone)
        rows = [_make_row(applicability="zone_specific", condition="zones other than R2 Low Density Residential")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "strathfield", zone_code="R2 Low Density Residential")
        assert len(result["setbacks"]) == 1

    def test_plain_zone_limits_are_unchanged(self):
        assert not _mod.zone_row_applies("zone_specific", "R2 Low Density zone", "R3")  # noqa: zone-codes (test condition text)
        assert _mod.zone_row_applies("zone_specific", "R2 Low Density zone", "R2")
        assert not _mod.zone_row_applies("zone_specific", "R2 zone; not less than 6m", "R3")  # noqa: zone-codes (a loose "not" is not an exclusion)
        assert _mod.zone_row_applies("zone_specific", "corner lots other than battle-axe lots", "R2")
        assert _mod.zone_row_applies("universal_residential", "R4 zone only", "R2")  # noqa: zone-codes (test condition text)
        assert _mod.zone_row_applies("zone_specific", "R4 zone only", "")

    def test_clause_ids_are_not_zone_codes(self):
        assert _mod.zone_row_applies("zone_specific", "additional setbacks apply (C3.3.2)", "R2")  # noqa: zone-codes (C3.3.2 is a clause id, the point of the test)
        assert _mod.zone_row_applies("zone_specific", "see Part B2.1 for corner sites", "R3")  # noqa: zone-codes (B2.1 is a DCP part id, the point of the test)
        assert _mod.zone_row_applies("zone_specific", "See Part B2 for corner-site controls", "R3")  # noqa: zone-codes (Part B2 is a DCP part, the point of the test)
        assert _mod.zone_row_applies("zone_specific", "Clause C3 applies", "R2")  # noqa: zone-codes (Clause C3 is a clause, the point of the test)
        assert not _mod.zone_row_applies("zone_specific", "R2 zone; see Part B2", "R3")  # noqa: zone-codes (a real zone still limits the row)

    def test_secondary_dwelling_routed_to_sd(self):
        rows = [_make_row(dev_type="secondary_dwelling")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        assert len(result["setbacks"]) == 0
        assert len(result["sd_setbacks"]) == 1

    def test_sd_applicability_routed_to_sd(self):
        rows = [_make_row(applicability="secondary_dwelling_specific")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        assert len(result["setbacks"]) == 0
        assert len(result["sd_setbacks"]) == 1

    def test_multiple_zones_in_condition_user_matches_one(self):
        rows = [_make_row(applicability="zone_specific", condition="Applies to R2 and R3 zones")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra", zone_code="R2")
        assert len(result["setbacks"]) == 1

    def test_canterbury_bankstown_caveat(self):
        rows = [_make_row()]
        result = fetch_dcp_setbacks(_mock_conn(rows), "canterbury_bankstown")
        assert result["caveat"] is not None
        assert "Canterbury-Bankstown" in result["caveat"]

    def test_non_canterbury_no_caveat(self):
        rows = [_make_row()]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        assert result["caveat"] is None


# ── Explicit zone scope (migration 072) ──


class TestExplicitZoneScope:
    """zones_include / zones_exclude decide before the condition text is read."""

    def _kept(self, rows, zone):
        result = fetch_dcp_setbacks(_mock_conn(rows), "strathfield", zone_code=zone)
        return [(s["value_min"], s["value_max"]) for s in result["setbacks"]]

    def test_exclude_drops_the_row_for_that_zone_only(self):
        # The Strathfield case: "zones other than the low density residential zone" names no zone code, so
        # the text rule keeps it everywhere. The explicit scope removes it for an R2 site alone.
        rows = [_make_row(ctrl_type="rear_setback", vmin=6.0, applicability="zone_specific",
                          condition="zones other than the low density residential zone",
                          zones_exclude=["R2"])]  # noqa: zone-codes (fixture scope)
        assert self._kept(rows, "R2") == []  # noqa: zone-codes (fixture zone)
        assert self._kept(rows, "R3") == [(6.0, None)]  # noqa: zone-codes (fixture zone)

    def test_include_keeps_the_row_for_that_zone_only(self):
        rows = [_make_row(ctrl_type="rear_setback", vmin=6.0, vmax=10.0, applicability="zone_specific",
                          condition="low density residential zone", zones_include=["R2"])]  # noqa: zone-codes (fixture scope)
        assert self._kept(rows, "R2") == [(6.0, 10.0)]  # noqa: zone-codes (fixture zone)
        assert self._kept(rows, "R3") == []  # noqa: zone-codes (fixture zone)

    def test_explicit_scope_overrides_condition_text_and_applicability(self):
        # The condition names R3, and the row is not even tagged zone_specific: the stored scope still wins.
        rows = [_make_row(applicability="universal_residential", condition="R3 Medium Density",  # noqa: zone-codes (fixture text)
                          zones_include=["R2"])]  # noqa: zone-codes (fixture scope)
        assert len(self._kept(rows, "R2")) == 1  # noqa: zone-codes (fixture zone)
        assert self._kept(rows, "R3") == []  # noqa: zone-codes (fixture zone)

    def test_scope_codes_are_compared_trimmed_and_upper_case(self):
        rows = [_make_row(zones_exclude=[" r2 "])]  # noqa: zone-codes (fixture scope)
        assert self._kept(rows, "R2") == []  # noqa: zone-codes (fixture zone)

    def test_unknown_zone_keeps_every_scoped_row(self):
        rows = [_make_row(zones_include=["R2"]), _make_row(ctrl_type="rear_setback", zones_exclude=["R2"])]  # noqa: zone-codes (fixture scope)
        result = fetch_dcp_setbacks(_mock_conn(rows), "strathfield")
        assert len(result["setbacks"]) == 2

    def test_null_or_blank_elements_never_exclude_a_real_zone(self):
        # ARRAY[NULL] reaches Python as [None]; read as the string "NONE" it would hide the row for every zone.
        only_null = [_make_row(zones_include=[None])]
        assert len(self._kept(only_null, "R2")) == 1  # noqa: zone-codes (fixture zone)
        assert len(self._kept(only_null, "R3")) == 1  # noqa: zone-codes (fixture zone)
        blank = [_make_row(zones_include=["", "  "])]
        assert len(self._kept(blank, "R3")) == 1  # noqa: zone-codes (fixture zone)
        mixed = [_make_row(zones_exclude=[None, "R2"])]  # noqa: zone-codes (fixture scope)
        assert self._kept(mixed, "R2") == []  # noqa: zone-codes (fixture zone)
        assert len(self._kept(mixed, "R3")) == 1  # noqa: zone-codes (fixture zone)

    def test_empty_arrays_fall_back_to_the_text_rule(self):
        rows = [_make_row(applicability="zone_specific", condition="R3 Medium Density",  # noqa: zone-codes (fixture text)
                          zones_include=[], zones_exclude=[])]
        assert self._kept(rows, "R2") == []  # noqa: zone-codes (fixture zone)
        assert len(self._kept(rows, "R3")) == 1  # noqa: zone-codes (fixture zone)


# ── Setback value formatting ──


class TestSetbackFormatting:
    def test_prescribed_min_only(self):
        rows = [_make_row(vmin=6.0, vmax=None)]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        entry = result["setbacks"][0]
        assert entry["control_type"] == "prescribed"
        assert "6 m minimum" in entry["requirement"]

    def test_semantic_type_and_numeric_values(self):
        rows = [_make_row(ctrl_type="front_setback", vmin=6.0, vmax=9.0)]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        entry = result["setbacks"][0]
        assert entry["semantic_type"] == "front_setback"
        assert entry["value_min"] == 6.0
        assert entry["value_max"] == 9.0
        assert entry["unit"] == "m"

    def test_semantic_type_site_derived(self):
        rows = [_make_row(ctrl_type="rear_setback", vmin=None, vmax=None)]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        entry = result["setbacks"][0]
        assert entry["semantic_type"] == "rear_setback"
        assert entry["value_min"] is None
        assert entry["value_max"] is None

    def test_a_range_the_plan_does_not_call_a_maximum_prints_as_a_range(self):
        # A rear setback of 3-9 m by lot width is not a 9 m maximum (2026-09-14: burwood rear 3-6 m read that way).
        rows = [_make_row(vmin=3.0, vmax=9.0, source_text="Rear setback 3m to 9m depending on lot depth")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        entry = result["setbacks"][0]
        assert entry["requirement"] == "3–9 m"
        assert "maximum" not in entry["requirement"]

    def test_a_range_the_plan_states_as_minimum_and_maximum_keeps_both(self):
        rows = [_make_row(ctrl_type="car_parking", vmin=1.0, vmax=2.0, unit="spaces/dwelling",
                          source_text="Minimum 1, maximum 2 car parking spaces (Table C-B)")]
        entry = fetch_dcp_setbacks(_mock_conn(rows), "canada_bay")["setbacks"][0]
        assert entry["requirement"] == "1 spaces/dwelling minimum; 2 spaces/dwelling maximum"

    def test_a_number_prints_in_its_own_unit(self):
        # Every number used to print as metres: "1 m minimum" for a parking rate.
        rows = [_make_row(ctrl_type="car_parking", vmin=1.0, vmax=None, unit="spaces/dwelling")]
        entry = fetch_dcp_setbacks(_mock_conn(rows), "fairfield")["setbacks"][0]
        assert entry["requirement"] == "1 spaces/dwelling minimum"
        rows = [_make_row(ctrl_type="landscaping_min", vmin=30.0, vmax=None, unit="%")]
        entry = fetch_dcp_setbacks(_mock_conn(rows), "fairfield")["setbacks"][0]
        assert entry["requirement"] == "30% minimum"

    def test_a_maximum_control_reads_as_a_maximum(self):
        # A ceiling stored in value_min read "60 m minimum".
        rows = [_make_row(ctrl_type="max_site_coverage", vmin=60.0, vmax=None, unit="%")]
        entry = fetch_dcp_setbacks(_mock_conn(rows), "blacktown")["setbacks"][0]
        assert entry["requirement"] == "60% maximum"
        rows = [_make_row(ctrl_type="car_parking", vmin=None, vmax=2.0, unit="spaces/dwelling")]
        entry = fetch_dcp_setbacks(_mock_conn(rows), "waverley")["setbacks"][0]
        assert entry["requirement"] == "2 spaces/dwelling maximum"

    def test_a_precinct_rule_is_not_served_council_wide(self):
        # DQ-99: leichhardt served a 1.0 m Birchgrove neighbourhood minimum to every house in the council.
        rows = [_make_row(vmin=1.0, applicability="precinct_specific",
                          condition="Birchgrove neighbourhood minimum"),
                _make_row(vmin=6.0, applicability="universal_residential")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "leichhardt")
        assert [e["value_min"] for e in result["setbacks"]] == [6.0]

    def test_prescribed_min_equals_max(self):
        rows = [_make_row(vmin=6.0, vmax=6.0)]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        entry = result["setbacks"][0]
        assert entry["requirement"] == "6 m minimum"

    def test_site_derived_with_source_text(self):
        rows = [_make_row(vmin=None, vmax=None, source_text="Average of adjoining setbacks")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        entry = result["setbacks"][0]
        assert entry["control_type"] == "site_derived"
        assert "Average of adjoining" in entry["requirement"]

    def test_site_derived_no_source_text(self):
        # A rule with no number is not a merit assessment; the fallback names neither.
        rows = [_make_row(vmin=None, vmax=None, source_text=None)]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        entry = result["setbacks"][0]
        assert entry["requirement"] == "No set number — see the plan"
        assert "merit" not in entry["requirement"].lower()
        assert entry["plain_summary"] is None

    def test_site_derived_uses_plain_summary_when_no_source_text(self):
        rows = [_make_row(vmin=None, vmax=None, source_text=None,
                          plain_summary="Worked out from neighbours' setbacks")]
        entry = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")["setbacks"][0]
        assert entry["requirement"] == "Worked out from neighbours' setbacks"
        assert entry["plain_summary"] == "Worked out from neighbours' setbacks"

    def test_plain_summary_passes_through_beside_the_quote(self):
        rows = [_make_row(vmin=None, vmax=None, source_text="Average of adjoining setbacks",
                          plain_summary="Worked out from neighbours' setbacks")]
        entry = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")["setbacks"][0]
        assert entry["requirement"] == "Average of adjoining setbacks"
        assert entry["plain_summary"] == "Worked out from neighbours' setbacks"

    def test_zero_minimum(self):
        rows = [_make_row(vmin=0, vmax=None)]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        entry = result["setbacks"][0]
        assert entry["control_type"] == "prescribed"
        assert "0 m minimum" in entry["requirement"]

    def test_unknown_control_type_label(self):
        rows = [_make_row(ctrl_type="floor_space_ratio")]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        entry = result["setbacks"][0]
        assert entry["type"] == "Floor Space Ratio"

    def test_known_lga_slug_dcp_name(self):
        rows = [_make_row()]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        assert result["dcp_name"] == "Woollahra DCP"

    def test_unknown_lga_slug_dcp_name(self):
        rows = [_make_row()]
        result = fetch_dcp_setbacks(_mock_conn(rows), "some_new_council")
        assert result["dcp_name"] == "Some New Council DCP"


# ── fetch_dcp_setbacks guard paths ──


class TestFetchDcpSetbacksGuards:
    def test_null_lga_returns_none(self):
        assert fetch_dcp_setbacks(MagicMock(), None) is None

    def test_empty_lga_returns_none(self):
        assert fetch_dcp_setbacks(MagicMock(), "") is None

    def test_no_rows_returns_none(self):
        assert fetch_dcp_setbacks(_mock_conn([]), "woollahra") is None

    def test_db_exception_returns_none(self):
        conn = MagicMock()
        conn.cursor.side_effect = Exception("connection lost")
        assert fetch_dcp_setbacks(conn, "woollahra") is None

    def test_zone_filter_applied_field(self):
        rows = [_make_row()]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra", zone_code="R2 Low")
        assert result["zone_filter_applied"] == "R2"

    def test_zone_filter_applied_none_when_no_zone(self):
        rows = [_make_row()]
        result = fetch_dcp_setbacks(_mock_conn(rows), "woollahra")
        assert result["zone_filter_applied"] is None


# ── Heritage classification ──


def _mock_heritage_conn(rows):
    cursor = MagicMock()
    cursor.fetchall.return_value = rows
    conn = MagicMock()
    conn.cursor.return_value = cursor
    return conn


class TestHeritageClassification:
    def test_hca_general(self):
        rows = [("Conservation Area - General", "LEP 2022 C86")]
        result = fetch_heritage_postgis(_mock_heritage_conn(rows), -33.9, 151.1)
        assert len(result["hca"]) == 1
        assert "Heritage Conservation Area" in result["hca"][0]
        assert result["has_heritage"] is True

    def test_item_general(self):
        rows = [("Item - General", "I123")]
        result = fetch_heritage_postgis(_mock_heritage_conn(rows), -33.9, 151.1)
        assert len(result["items"]) == 1
        assert "Heritage Item" in result["items"][0]

    def test_mixed_hca_and_item(self):
        rows = [
            ("Conservation Area - General", "C86"),
            ("Item - General", "I123"),
        ]
        result = fetch_heritage_postgis(_mock_heritage_conn(rows), -33.9, 151.1)
        assert len(result["hca"]) == 1
        assert len(result["items"]) == 1
        assert result["has_heritage"] is True

    def test_duplicate_dedup(self):
        rows = [
            ("Conservation Area - General", "C86"),
            ("Conservation Area - General", "C86"),
        ]
        result = fetch_heritage_postgis(_mock_heritage_conn(rows), -33.9, 151.1)
        assert len(result["hca"]) == 1

    def test_no_rows_empty_result(self):
        result = fetch_heritage_postgis(_mock_heritage_conn([]), -33.9, 151.1)
        assert result["hca"] == []
        assert result["items"] == []
        assert result["has_heritage"] is False

    # --- Adversarial inputs ---

    def test_null_value(self):
        rows = [(None, "I123")]
        result = fetch_heritage_postgis(_mock_heritage_conn(rows), -33.9, 151.1)
        assert len(result["hca"]) == 0
        assert len(result["items"]) == 0
        assert result["has_heritage"] is False
        assert len(result["raw"]) == 1

    def test_null_instrument_key(self):
        rows = [("Conservation Area - General", None)]
        result = fetch_heritage_postgis(_mock_heritage_conn(rows), -33.9, 151.1)
        assert "refer to council heritage maps" in result["hca"][0]

    def test_unknown_value_type(self):
        rows = [("Some Unknown Type", "X99")]
        result = fetch_heritage_postgis(_mock_heritage_conn(rows), -33.9, 151.1)
        assert len(result["hca"]) == 0
        assert len(result["items"]) == 0
        assert result["has_heritage"] is False
        assert len(result["raw"]) == 1

    def test_case_insensitive_classification(self):
        rows = [("CONSERVATION AREA - GENERAL", "C86")]
        result = fetch_heritage_postgis(_mock_heritage_conn(rows), -33.9, 151.1)
        assert len(result["hca"]) == 1

    def test_aboriginal_heritage(self):
        rows = [("Conservation Area - Aboriginal", "AH1")]
        result = fetch_heritage_postgis(_mock_heritage_conn(rows), -33.9, 151.1)
        assert len(result["hca"]) == 1

    def test_aboriginal_place(self):
        rows = [("Aboriginal Place of Heritage Significance", "AP1")]
        result = fetch_heritage_postgis(_mock_heritage_conn(rows), -33.9, 151.1)
        assert len(result["items"]) == 1

    def test_db_exception_raises_rather_than_saying_not_heritage(self):
        """DQ-82. This test previously asserted the opposite, and that is the
        point of the rename: it locked in the defect. The old empty return
        carries has_heritage: False, which renders as "not heritage listed" --
        a statement about the property made without looking at anything."""
        conn = MagicMock()
        conn.cursor.side_effect = Exception("timeout")
        with pytest.raises(Exception, match="timeout"):
            fetch_heritage_postgis(conn, -33.9, 151.1)


# ── fetch_lep_clauses guard paths ──


class TestFetchLepClausesGuards:
    def test_null_clause_returns_empty(self):
        assert fetch_lep_clauses(MagicMock(), None, "LEP 2022") == []

    def test_null_epi_returns_empty(self):
        assert fetch_lep_clauses(MagicMock(), "Clause 4.3", None) == []

    def test_empty_clause_returns_empty(self):
        assert fetch_lep_clauses(MagicMock(), "", "LEP 2022") == []

    def test_db_exception_raises_rather_than_returning_no_clauses(self):
        """DQ-82. [] is indistinguishable from "this property has no key sites
        clauses", so the caller cannot tell a real answer from a dead query."""
        conn = MagicMock()
        conn.cursor.side_effect = Exception("connection refused")
        with pytest.raises(Exception, match="connection refused"):
            fetch_lep_clauses(conn, "Clause 4.3", "LEP 2022")
