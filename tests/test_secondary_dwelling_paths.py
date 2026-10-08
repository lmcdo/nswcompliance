"""Fail-closed / falsifiability tests for services.secondary_dwelling_paths.

The fixture below copies the 9 rows inserted by
migrations/084_secondary_dwelling_rules_insert.sql verbatim (same
standard_type, pathway, numeric_value, band limits, applicable_zones, clause,
url and exact source_quote text). Every mutation test deep-copies this
fixture before breaking one thing, and asserts the specific failure text
validate_rules produces -- not just "it failed somehow". No database, no
network: load_rules is exercised with a fake connection object only.
"""
from __future__ import annotations

import ast
import copy
import math
import re
from pathlib import Path

import pytest

from services.secondary_dwelling_paths import (
    AUTHORITATIVE_URL_PREFIX,
    evaluate_cdc,
    evaluate_da,
    load_rules,
    validate_rules,
)

SERVICE_PATH = Path(__file__).resolve().parent.parent / "services" / "secondary_dwelling_paths.py"

# ---------------------------------------------------------------------------
# Fixture: the 9 real rows from migration 084, copied exactly.
# ---------------------------------------------------------------------------

BASE_ROWS: list[dict] = [
    {
        "id": 201,
        "standard_type": "cdc_min_road_frontage_lot_450_to_900",
        "approval_pathway": "cdc",
        "numeric_value": 12,
        "unit": "m",
        "lot_area_min_m2": 450,
        "lot_area_min_inclusive": True,
        "lot_area_max_m2": 900,
        "applicable_zones": ["R1", "R2", "R3", "R4"],  # noqa: zone-codes — fixture mirrors migration 084 rows
        "source_clause": "Schedule 1, cl 2(1)(b)(i)",
        "legislation_url": "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.2-ssec.1-para1.b-para2.i",
        "source_quote": "(b) for a lot other than a battle-axe lot—has a boundary with a primary road, measured at the building line, of at least the following— (i) if the lot has an area of at least 450m2 but not more than 900m2—12m,",
        "stale_since": None,
    },
    {
        "id": 202,
        "standard_type": "cdc_min_road_frontage_lot_900_to_1500",
        "approval_pathway": "cdc",
        "numeric_value": 15,
        "unit": "m",
        "lot_area_min_m2": 900,
        "lot_area_min_inclusive": False,
        "lot_area_max_m2": 1500,
        "applicable_zones": ["R1", "R2", "R3", "R4"],  # noqa: zone-codes — fixture mirrors migration 084 rows
        "source_clause": "Schedule 1, cl 2(1)(b)(ii)",
        "legislation_url": "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.2-ssec.1-para1.b-para2.ii",
        "source_quote": "(b) for a lot other than a battle-axe lot—has a boundary with a primary road, measured at the building line, of at least the following— ... (ii) if the lot has an area of more than 900m2 but not more than 1500m2—15m,",
        "stale_since": None,
    },
    {
        "id": 203,
        "standard_type": "cdc_min_road_frontage_lot_over_1500",
        "approval_pathway": "cdc",
        "numeric_value": 18,
        "unit": "m",
        "lot_area_min_m2": 1500,
        "lot_area_min_inclusive": False,
        "lot_area_max_m2": None,
        "applicable_zones": ["R1", "R2", "R3", "R4"],  # noqa: zone-codes — fixture mirrors migration 084 rows
        "source_clause": "Schedule 1, cl 2(1)(b)(iii)",
        "legislation_url": "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.2-ssec.1-para1.b-para2.iii",
        "source_quote": "(b) for a lot other than a battle-axe lot—has a boundary with a primary road, measured at the building line, of at least the following— ... (iii) if the lot has an area of more than 1500m2—18m,",
        "stale_since": None,
    },
    {
        "id": 204,
        "standard_type": "cdc_parking_rule",
        "approval_pathway": "cdc",
        "numeric_value": None,
        "unit": None,
        "lot_area_min_m2": None,
        "lot_area_min_inclusive": None,
        "lot_area_max_m2": None,
        "applicable_zones": ["R1", "R2", "R3", "R4"],  # noqa: zone-codes — fixture mirrors migration 084 rows
        "source_clause": "Schedule 1, cl 2(3)",
        "legislation_url": "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sch.1-sec.2-ssec.3",
        "source_quote": "(3) Nothing in this Schedule requires the provision of additional parking spaces for development for the purposes of a secondary dwelling.",
        "stale_since": None,
    },
    {
        "id": 205,
        "standard_type": "da_detached_min_site_area",
        "approval_pathway": "da",
        "numeric_value": 450,
        "unit": "m²",
        "lot_area_min_m2": None,
        "lot_area_min_inclusive": None,
        "lot_area_max_m2": None,
        "applicable_zones": ["R1", "R2", "R3", "R4", "R5"],  # noqa: zone-codes — fixture mirrors migration 084 rows
        "source_clause": "s 53(2)(a)",
        "legislation_url": "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sec.53-ssec.2-para1.a",
        "source_quote": "(2) The following are non-discretionary development standards in relation to the carrying out of development to which this Part applies— (a) for a detached secondary dwelling—a minimum site area of 450m2,",
        "stale_since": None,
    },
    {
        "id": 206,
        "standard_type": "da_non_discretionary_note",
        "approval_pathway": "da",
        "numeric_value": None,
        "unit": None,
        "lot_area_min_m2": None,
        "lot_area_min_inclusive": None,
        "lot_area_max_m2": None,
        "applicable_zones": ["R1", "R2", "R3", "R4", "R5"],  # noqa: zone-codes — fixture mirrors migration 084 rows
        "source_clause": "s 53(1), Note",
        "legislation_url": "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sec.53",
        "source_quote": "See the Act, section 4.15(3), which does not prevent development consent being granted if a non-discretionary development standard is not complied with.",
        "stale_since": None,
    },
    {
        "id": 207,
        "standard_type": "da_parking_rule",
        "approval_pathway": "da",
        "numeric_value": None,
        "unit": None,
        "lot_area_min_m2": None,
        "lot_area_min_inclusive": None,
        "lot_area_max_m2": None,
        "applicable_zones": ["R1", "R2", "R3", "R4", "R5"],  # noqa: zone-codes — fixture mirrors migration 084 rows
        "source_clause": "s 53(2)(b)",
        "legislation_url": "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sec.53-ssec.2-para1.b",
        "source_quote": "(b) the number of parking spaces provided on the site is the same as the number of parking spaces provided on the site immediately before the development is carried out.",
        "stale_since": None,
    },
    {
        "id": 208,
        "standard_type": "cdc_zone_scope",
        "approval_pathway": "cdc",
        "numeric_value": None,
        "unit": None,
        "lot_area_min_m2": None,
        "lot_area_min_inclusive": None,
        "lot_area_max_m2": None,
        "applicable_zones": ["R1", "R2", "R3", "R4"],  # noqa: zone-codes — fixture mirrors migration 084 rows
        "source_clause": "s 49 (residential zone); s 54(1)(a)",
        "legislation_url": "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sec.54-ssec.1-para1.a",
        "source_quote": "residential zone means the following land use zones or an equivalent land use zone— (a) Zone R1 General Residential, (b) Zone R2 Low Density Residential, (c) Zone R3 Medium Density Residential, (d) Zone R4 High Density Residential, (e) Zone R5 Large Lot Residential. ... (a) is on land in a residential zone other than Zone R5 Large Lot Residential, and",  # noqa: zone-codes — fixture mirrors migration 084 rows
        "stale_since": None,
    },
    {
        "id": 209,
        "standard_type": "da_zone_scope",
        "approval_pathway": "da",
        "numeric_value": None,
        "unit": None,
        "lot_area_min_m2": None,
        "lot_area_min_inclusive": None,
        "lot_area_max_m2": None,
        "applicable_zones": ["R1", "R2", "R3", "R4", "R5"],  # noqa: zone-codes — fixture mirrors migration 084 rows
        "source_clause": "s 49 (residential zone); s 50",
        "legislation_url": "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714#sec.50",
        "source_quote": "residential zone means the following land use zones or an equivalent land use zone— (a) Zone R1 General Residential, (b) Zone R2 Low Density Residential, (c) Zone R3 Medium Density Residential, (d) Zone R4 High Density Residential, (e) Zone R5 Large Lot Residential. ... This Part applies to development for the purposes of a secondary dwelling on land in a residential zone if development for the purposes of a dwelling house is permissible on the land under another environmental planning instrument.",  # noqa: zone-codes — fixture mirrors migration 084 rows
        "stale_since": None,
    },
]


def _all_string_values(obj):
    """Recursively yield every string value nested inside obj."""
    if isinstance(obj, str):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from _all_string_values(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            yield from _all_string_values(v)


@pytest.fixture
def rows():
    """A fresh deep copy of the valid fixture for each mutation test."""
    return copy.deepcopy(BASE_ROWS)


@pytest.fixture(scope="module")
def valid_rules():
    """The validated Rules object, built once, reused by CDC/DA tests."""
    outcome = validate_rules(copy.deepcopy(BASE_ROWS))
    assert outcome.failures == (), outcome.failures
    assert outcome.rules is not None
    return outcome.rules


# ---------------------------------------------------------------------------
# Fixture sanity: must be VALID before anything else is trusted.
# ---------------------------------------------------------------------------


def test_fixture_is_valid():
    outcome = validate_rules(copy.deepcopy(BASE_ROWS))
    assert outcome.failures == (), f"fixture does not validate: {outcome.failures}"
    assert outcome.rules is not None


# ---------------------------------------------------------------------------
# VALIDATION — each of the 9 rows missing.
# ---------------------------------------------------------------------------

REMOVAL_CASES = [
    ("cdc_min_road_frontage_lot_450_to_900", "the lowest band must include its lower limit"),
    ("cdc_min_road_frontage_lot_900_to_1500", "lot-area bands leave a gap or overlap"),
    ("cdc_min_road_frontage_lot_over_1500", "the top band must be open-ended"),
    ("cdc_parking_rule", "cdc_parking_rule: rule missing"),
    ("da_detached_min_site_area", "da_detached_min_site_area: rule missing"),
    ("da_non_discretionary_note", "da_non_discretionary_note: rule missing"),
    ("da_parking_rule", "da_parking_rule: rule missing"),
    ("cdc_zone_scope", "cdc_zone_scope: rule missing"),
    ("da_zone_scope", "da_zone_scope: rule missing"),
]


@pytest.mark.parametrize("standard_type,expected_substring", REMOVAL_CASES)
def test_removing_a_row_fails_closed(standard_type, expected_substring):
    fixture = [r for r in copy.deepcopy(BASE_ROWS) if r["standard_type"] != standard_type]
    outcome = validate_rules(fixture)
    assert outcome.rules is None
    assert any(expected_substring in f for f in outcome.failures), outcome.failures


def test_stale_since_fails_marked_stale(rows):
    rows[0]["stale_since"] = "2026-01-01"
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("marked stale" in f for f in outcome.failures), outcome.failures


def test_empty_quote_fails(rows):
    rows[0]["source_quote"] = ""
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("no quote of the law" in f for f in outcome.failures), outcome.failures


def test_empty_clause_fails(rows):
    rows[0]["source_clause"] = ""
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("no clause reference" in f for f in outcome.failures), outcome.failures


@pytest.mark.parametrize("bad_url", [None, "https://example.com/x"])
def test_legislation_url_must_be_authoritative(rows, bad_url):
    rows[0]["legislation_url"] = bad_url
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any(
        "legislation link missing, not legislation.nsw.gov.au, or broken by whitespace" in f
        for f in outcome.failures
    ), outcome.failures


def test_legislation_url_broken_by_whitespace_fails(rows):
    url = rows[0]["legislation_url"]
    assert url.startswith(AUTHORITATIVE_URL_PREFIX)
    rows[0]["legislation_url"] = (
        url[: len(AUTHORITATIVE_URL_PREFIX)] + "\r\n  " + url[len(AUTHORITATIVE_URL_PREFIX):]
    )
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any(
        "legislation link missing, not legislation.nsw.gov.au, or broken by whitespace" in f
        for f in outcome.failures
    ), outcome.failures


def test_approval_pathway_other_fails(rows):
    rows[0]["approval_pathway"] = "other"
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("approval path is not cdc or da" in f for f in outcome.failures), outcome.failures


def test_frontage_value_not_in_quote_fails(rows):
    for row in rows:
        if row["standard_type"] == "cdc_min_road_frontage_lot_450_to_900":
            row["numeric_value"] = 13  # quote still says 12m
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("does not appear in its quote" in f for f in outcome.failures), outcome.failures


def test_da_numeric_value_not_in_quote_fails(rows):
    for row in rows:
        if row["standard_type"] == "da_detached_min_site_area":
            row["numeric_value"] = 500  # quote still says 450m2
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("does not appear in its quote" in f for f in outcome.failures), outcome.failures


def test_wording_rule_with_numeric_value_fails(rows):
    for row in rows:
        if row["standard_type"] == "cdc_parking_rule":
            row["numeric_value"] = 0
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("a wording rule must not carry a number" in f for f in outcome.failures), outcome.failures


def test_band_upper_limit_mismatch_fails(rows):
    for row in rows:
        if row["standard_type"] == "cdc_min_road_frontage_lot_450_to_900":
            row["lot_area_max_m2"] = 800  # quote still says "not more than 900m2"
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("not in its quote" in f for f in outcome.failures), outcome.failures


def test_band_lower_inclusive_flip_fails(rows):
    for row in rows:
        if row["standard_type"] == "cdc_min_road_frontage_lot_900_to_1500":
            row["lot_area_min_inclusive"] = True  # quote still says "more than 900m2"
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("not in its quote" in f for f in outcome.failures), outcome.failures


def test_band_gap_when_row_itself_is_internally_consistent(rows):
    for row in rows:
        if row["standard_type"] == "cdc_min_road_frontage_lot_450_to_900":
            row["lot_area_max_m2"] = 850
            row["source_quote"] = row["source_quote"].replace("not more than 900m2", "not more than 850m2")
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("gap or overlap" in f for f in outcome.failures), outcome.failures


def test_top_band_with_a_max_fails(rows):
    for row in rows:
        if row["standard_type"] == "cdc_min_road_frontage_lot_over_1500":
            row["lot_area_max_m2"] = 2000
            row["source_quote"] = row["source_quote"].replace(
                "1500m2—18m,", "1500m2 but not more than 2000m2—18m,"
            )
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("top band must be open-ended" in f for f in outcome.failures), outcome.failures


def test_lowest_band_not_inclusive_fails(rows):
    for row in rows:
        if row["standard_type"] == "cdc_min_road_frontage_lot_450_to_900":
            row["lot_area_min_inclusive"] = False
            row["source_quote"] = row["source_quote"].replace("at least 450m2", "more than 450m2")
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("lowest band must include its lower limit" in f for f in outcome.failures), outcome.failures


def test_load_rules_none_connection_fails(rows):
    outcome = load_rules(None)
    assert outcome.rules is None
    assert outcome.failures == ("no database connection",)


def test_load_rules_query_error_fails_and_rolls_back():
    class _FakeCursor:
        def execute(self, *a, **kw):
            raise RuntimeError("boom")

        def close(self):
            pass

    class _FakeConn:
        def __init__(self):
            self.rolled_back = False

        def cursor(self):
            return _FakeCursor()

        def rollback(self):
            self.rolled_back = True

    conn = _FakeConn()
    outcome = load_rules(conn)
    assert outcome.rules is None
    assert len(outcome.failures) == 1
    assert "rules query failed" in outcome.failures[0]
    assert conn.rolled_back is True


# ---------------------------------------------------------------------------
# NEW VALIDATION (post cross-review):
#   - a frontage value must not satisfy an m2 (area) notation
#   - a site-area value must not satisfy a bare-metres notation
#   - the row's unit must match what the rule actually measures
#   - a row's approval_pathway must match its own name prefix
#   - zone-scope rows: zones must be listed, each must appear in the quote,
#     and a zone the quote itself excludes must not be listed
# ---------------------------------------------------------------------------


def test_frontage_value_matching_an_m2_figure_is_rejected(rows):
    """Cross-review finding #1: a frontage (metres) value must not be satisfied
    by the row's own m2 area figure. numeric_value=900 and the quote contains
    "900m2" (the band's upper limit, in square metres) -- not "900m"."""
    for row in rows:
        if row["standard_type"] == "cdc_min_road_frontage_lot_450_to_900":
            row["numeric_value"] = 900
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any(
        "900" in f and "does not appear in its quote" in f for f in outcome.failures
    ), outcome.failures


def test_site_area_value_matching_a_metres_figure_is_rejected(rows):
    """A site-area (m2) rule must not be satisfied by a bare-metres mention."""
    for row in rows:
        if row["standard_type"] == "da_detached_min_site_area":
            row["numeric_value"] = 12
            row["source_quote"] = row["source_quote"] + " A separate 12m boundary setback note."
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any(
        "12" in f and "does not appear in its quote" in f for f in outcome.failures
    ), outcome.failures


def test_frontage_unit_m2_is_rejected(rows):
    for row in rows:
        if row["standard_type"] == "cdc_min_road_frontage_lot_450_to_900":
            row["unit"] = "m²"
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("is wrong for this rule" in f for f in outcome.failures), outcome.failures


def test_site_area_unit_m_is_rejected(rows):
    for row in rows:
        if row["standard_type"] == "da_detached_min_site_area":
            row["unit"] = "m"
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("is wrong for this rule" in f for f in outcome.failures), outcome.failures


def test_cdc_row_tagged_da_is_rejected(rows):
    for row in rows:
        if row["standard_type"] == "cdc_min_road_frontage_lot_450_to_900":
            row["approval_pathway"] = "da"
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("name says another path" in f for f in outcome.failures), outcome.failures


def test_da_parking_rule_tagged_cdc_is_rejected(rows):
    for row in rows:
        if row["standard_type"] == "da_parking_rule":
            row["approval_pathway"] = "cdc"
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("name says another path" in f for f in outcome.failures), outcome.failures


def test_cdc_zone_scope_listing_r5_is_rejected(rows):
    """The cdc_zone_scope quote itself excludes Zone R5 ("other than Zone R5
    Large Lot Residential"), so listing R5 as in-scope must be rejected."""
    for row in rows:
        if row["standard_type"] == "cdc_zone_scope":
            row["applicable_zones"] = ["R1", "R2", "R3", "R4", "R5"]  # noqa: zone-codes — fixture mirrors migration 084 rows
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("R5" in f and "excludes it" in f for f in outcome.failures), outcome.failures


def test_cdc_zone_scope_listing_ru1_is_rejected(rows):
    """RU1 is never mentioned in the cdc_zone_scope quote at all."""
    for row in rows:
        if row["standard_type"] == "cdc_zone_scope":
            row["applicable_zones"] = ["R1", "R2", "R3", "R4", "RU1"]  # noqa: zone-codes — fixture mirrors migration 084 rows
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any(
        "RU1" in f and "does not appear in its quote" in f for f in outcome.failures
    ), outcome.failures


def test_zone_scope_with_empty_zones_is_rejected(rows):
    for row in rows:
        if row["standard_type"] == "cdc_zone_scope":
            row["applicable_zones"] = []
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("no zones listed" in f for f in outcome.failures), outcome.failures


# ---------------------------------------------------------------------------
# CDC — Schedule 1 cl 2(1)(b) road frontage test.
# evaluate_cdc(rules, zone, lot_area_m2, frontage_range_m, battle_axe)
# ---------------------------------------------------------------------------


def test_cdc_battle_axe_none_is_unknown(valid_rules):
    result = evaluate_cdc(valid_rules, "R2", 600, (12.0, 30.0), None)
    assert result["outcome"] == "UNKNOWN"
    assert "battle-axe lot is not known" in result["reason"]


def test_cdc_battle_axe_true_is_unknown_and_mentions_2_1_c(valid_rules):
    result = evaluate_cdc(valid_rules, "R2", 600, (12.0, 30.0), True)
    assert result["outcome"] == "UNKNOWN"
    assert "2(1)(c)" in result["reason"]


@pytest.mark.parametrize("lot_area", [None, math.nan, 0, -5])
def test_cdc_invalid_lot_area_is_unknown(valid_rules, lot_area):
    result = evaluate_cdc(valid_rules, "R2", lot_area, (12.0, 30.0), False)
    assert result["outcome"] == "UNKNOWN"
    assert result["reason"] == "lot area not established"


def test_cdc_lot_area_below_first_band_is_unknown(valid_rules):
    result = evaluate_cdc(valid_rules, "R2", 449.9, None, False)
    assert result["outcome"] == "UNKNOWN"
    assert "sets no frontage" in result["reason"]


@pytest.mark.parametrize(
    "lot_area,expected_required_m",
    [
        (450, 12),
        (900, 12),
        (900.1, 15),
        (1500, 15),
        (1500.1, 18),
    ],
)
def test_cdc_band_thresholds_from_data(valid_rules, lot_area, expected_required_m):
    result = evaluate_cdc(valid_rules, "R2", lot_area, None, False)
    assert result["required_m"] == expected_required_m


@pytest.mark.parametrize(
    "frontage_range,expected_outcome",
    [
        ((12.0, 30.0), "PASS"),
        ((11.99, 11.99), "FAIL"),
        ((10, 20), "UNKNOWN"),
        (None, "UNKNOWN"),
        ((20, 10), "UNKNOWN"),
    ],
)
def test_cdc_frontage_outcomes_at_600_m2(valid_rules, frontage_range, expected_outcome):
    result = evaluate_cdc(valid_rules, "R2", 600, frontage_range, False)
    assert result["outcome"] == expected_outcome


def test_cdc_always_carries_parking_evidence(valid_rules):
    for battle_axe in (None, True, False):
        result = evaluate_cdc(valid_rules, "R2", 600, (12.0, 30.0), battle_axe)
        assert result["parking"]["clause"] == "Schedule 1, cl 2(3)"


def test_cdc_band_evidence_clause_matches_the_applied_band(valid_rules):
    result = evaluate_cdc(valid_rules, "R2", 600, (12.0, 30.0), False)
    assert result["evidence"]["clause"] == "Schedule 1, cl 2(1)(b)(i)"


def test_cdc_is_deterministic(valid_rules):
    a = evaluate_cdc(valid_rules, "R2", 600, (12.0, 30.0), False)
    b = evaluate_cdc(valid_rules, "R2", 600, (12.0, 30.0), False)
    assert a == b


# ---------------------------------------------------------------------------
# DA — s 53(2)(a) non-discretionary site-area standard.
# evaluate_da(rules, zone, lot_area_m2, detached, True)
# ---------------------------------------------------------------------------


def test_da_detached_none_is_unknown(valid_rules):
    result = evaluate_da(valid_rules, "R2", 600, None, True)
    assert result["outcome"] == "UNKNOWN"
    assert "detached" in result["reason"]


def test_da_detached_false_is_not_applicable(valid_rules):
    result = evaluate_da(valid_rules, "R2", 600, False, True)
    assert result["outcome"] == "NOT_APPLICABLE"
    assert "s 53(2)(a)" in result["reason"]


def test_da_lot_area_none_is_unknown(valid_rules):
    result = evaluate_da(valid_rules, "R2", None, True, True)
    assert result["outcome"] == "UNKNOWN"
    assert result["reason"] == "lot area not established"


def test_da_lot_area_450_meets(valid_rules):
    result = evaluate_da(valid_rules, "R2", 450, True, True)
    assert result["outcome"] == "MEETS"


def test_da_lot_area_449_99_is_below_with_note(valid_rules):
    result = evaluate_da(valid_rules, "R2", 449.99, True, True)
    assert result["outcome"] == "BELOW"
    assert "note" in result
    assert "4.15(3)" in result["note"]["quote"]


@pytest.mark.parametrize(
    "detached,lot_area",
    [(None, 600), (False, 600), (True, None), (True, 450), (True, 449.99)],
)
def test_da_outcome_vocabulary_never_leaks_pass_fail_language(valid_rules, detached, lot_area):
    result = evaluate_da(valid_rules, "R2", lot_area, detached, True)
    assert result["outcome"] in ("MEETS", "BELOW", "NOT_APPLICABLE", "UNKNOWN")
    forbidden = re.compile(r"\bPASS\b|\bFAIL\b|eligible|buildable", re.IGNORECASE)
    for value in _all_string_values(result):
        assert not forbidden.search(value), f"forbidden word in: {value!r}"


def test_da_always_carries_parking_evidence(valid_rules):
    for detached, lot_area in [(None, 600), (False, 600), (True, 450), (True, 449.99)]:
        result = evaluate_da(valid_rules, "R2", lot_area, detached, True)
        assert result["parking"]["clause"] == "s 53(2)(b)"


def test_da_is_deterministic(valid_rules):
    a = evaluate_da(valid_rules, "R2", 449.99, True, True)
    b = evaluate_da(valid_rules, "R2", 449.99, True, True)
    assert a == b


# ---------------------------------------------------------------------------
# Zone gate — s 49 residential-zone scope, read per path from cdc_zone_scope /
# da_zone_scope. Zone is the 2nd positional argument on both evaluators.
# ---------------------------------------------------------------------------


def test_zone_r2_evaluates_normally_for_both_paths(valid_rules):
    cdc = evaluate_cdc(valid_rules, "R2", 600, (12.0, 30.0), False)
    assert cdc["outcome"] == "PASS"
    assert "scope" not in cdc
    da = evaluate_da(valid_rules, "R2", 450, True, True)
    assert da["outcome"] == "MEETS"


def test_zone_r5_is_not_applicable_for_cdc_but_da_still_evaluates(valid_rules):
    cdc = evaluate_cdc(valid_rules, "R5", 600, (12.0, 30.0), False)
    assert cdc["outcome"] == "NOT_APPLICABLE"
    assert "R5" in cdc["reason"]
    da = evaluate_da(valid_rules, "R5", 600, True, True)
    assert da["outcome"] == "MEETS"


def test_zone_outside_scope_standard_code_is_not_applicable_for_both(valid_rules):
    cdc = evaluate_cdc(valid_rules, "E4", 600, (12.0, 30.0), False)
    assert cdc["outcome"] == "NOT_APPLICABLE"
    da = evaluate_da(valid_rules, "E4", 600, True, True)
    assert da["outcome"] == "NOT_APPLICABLE"


def test_zone_non_standard_code_is_unknown_for_both(valid_rules):
    cdc = evaluate_cdc(valid_rules, "2(a)", 600, (12.0, 30.0), False)
    assert cdc["outcome"] == "UNKNOWN"
    assert "equivalent land use zone" in cdc["reason"]
    da = evaluate_da(valid_rules, "2(a)", 600, True, True)
    assert da["outcome"] == "UNKNOWN"
    assert "equivalent land use zone" in da["reason"]


def test_zone_none_is_unknown_for_both(valid_rules):
    cdc = evaluate_cdc(valid_rules, None, 600, (12.0, 30.0), False)
    assert cdc["outcome"] == "UNKNOWN"
    assert cdc["reason"] == "zone not established"
    da = evaluate_da(valid_rules, None, 600, True, True)
    assert da["outcome"] == "UNKNOWN"
    assert da["reason"] == "zone not established"


def test_zone_full_title_is_treated_as_its_code(valid_rules):
    cdc = evaluate_cdc(valid_rules, "R2 Low Density Residential", 600, (12.0, 30.0), False)
    assert cdc["outcome"] == "PASS"
    da = evaluate_da(valid_rules, "R2 Low Density Residential", 450, True, True)
    assert da["outcome"] == "MEETS"


# ---------------------------------------------------------------------------
# Falsifiability: the frontage threshold comes from the DATA, not from a
# hardcoded constant in the evaluator. Rebuild the rules with a different
# number in the 450-900 row (and a quote edited to match) and show the
# evaluator's PASS/FAIL flips with it.
# ---------------------------------------------------------------------------


def test_cdc_threshold_comes_from_the_row_not_a_constant():
    original_outcome = validate_rules(copy.deepcopy(BASE_ROWS))
    assert original_outcome.failures == ()
    original_result = evaluate_cdc(original_outcome.rules, "R2", 600, (13, 13), False)
    assert original_result["outcome"] == "PASS"

    mutated = copy.deepcopy(BASE_ROWS)
    for row in mutated:
        if row["standard_type"] == "cdc_min_road_frontage_lot_450_to_900":
            row["numeric_value"] = 14
            row["source_quote"] = row["source_quote"].replace("—12m,", "—14m,")

    rebuilt_outcome = validate_rules(mutated)
    assert rebuilt_outcome.failures == (), rebuilt_outcome.failures
    rebuilt_result = evaluate_cdc(rebuilt_outcome.rules, "R2", 600, (13, 13), False)
    assert rebuilt_result["outcome"] == "FAIL"


# ---------------------------------------------------------------------------
# STATIC: no regulatory number is hardcoded in the module itself — every
# threshold must come from the database row. Strip the module docstring and
# comment-only lines, then check for word-bounded occurrences of each number.
# ---------------------------------------------------------------------------


def test_module_contains_no_hardcoded_regulatory_numbers():
    source = SERVICE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    docstring = ast.get_docstring(tree)
    if docstring:
        source = source.replace(docstring, "", 1)
    code_lines = [ln for ln in source.splitlines() if not ln.lstrip().startswith("#")]
    stripped = "\n".join(code_lines)

    forbidden = ["450", "900", "1500", "12", "15", "18"]
    hits = {n: re.findall(rf"\b{n}\b", stripped) for n in forbidden}
    hits = {n: v for n, v in hits.items() if v}
    assert not hits, f"hardcoded regulatory number(s) found outside comments/docstring: {hits}"


def test_decimal_lot_area_and_frontage_are_numbers_not_unknown():
    # Round-3 cross-review: PostgreSQL numeric arrives as Decimal.
    from decimal import Decimal
    rules = validate_rules(copy.deepcopy(BASE_ROWS)).rules
    cdc = evaluate_cdc(rules, "R2", Decimal("600"), (Decimal("12"), Decimal("30")), False)
    da = evaluate_da(rules, "R2", Decimal("600"), True, True)
    assert cdc["outcome"] == "PASS" and da["outcome"] == "MEETS"
    assert evaluate_cdc(rules, "R2", True, (12.0, 30.0), False)["outcome"] == "UNKNOWN"  # bool is not a number



def test_da_requires_dwelling_house_permissibility_s50():
    # Round-4 cross-review: s 50 applies the Part only where a dwelling house is permissible.
    rules = validate_rules(copy.deepcopy(BASE_ROWS)).rules
    assert evaluate_da(rules, "R2", 600, True, None)["outcome"] == "UNKNOWN"
    assert "s 50" in evaluate_da(rules, "R2", 600, True, None)["reason"]
    assert evaluate_da(rules, "R2", 600, True, False)["outcome"] == "NOT_APPLICABLE"
    assert evaluate_da(rules, "R2", 600, True, True)["outcome"] == "MEETS"


def test_zone_scope_must_list_every_zone_its_quote_covers():
    # Round-4 cross-review: dropping R4 while the quote still covers it must be rejected.
    rows = copy.deepcopy(BASE_ROWS)
    for r in rows:
        if r["standard_type"] == "cdc_zone_scope":
            r["applicable_zones"] = ["R1", "R2", "R3"]  # noqa: zone-codes — deliberately shrunken fixture
    outcome = validate_rules(rows)
    assert outcome.rules is None
    assert any("covers zone R4 but the rule does not list it" in f for f in outcome.failures)


@pytest.mark.parametrize("bad", [("12", "30"), (b"12", b"30"), ("x", 30.0)])
def test_frontage_given_as_text_is_not_a_measurement(bad):
    rules = validate_rules(copy.deepcopy(BASE_ROWS)).rules
    assert evaluate_cdc(rules, "R2", 600.0, bad, False)["outcome"] == "UNKNOWN"
