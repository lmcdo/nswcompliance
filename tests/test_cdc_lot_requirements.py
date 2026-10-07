"""CDC Housing Code lot-requirements screen: authority validation, evaluation,
input parsing and the API boundary.

Fixture note: the four cited regulatory_provisions texts below (ids 36996,
36997, 36184, 36185) are the full, real provision texts (not 400-char
previews) and are kept verbatim, including non-ASCII characters such as the
em dash (—) that appear inside them. Everything else in the base fixture
(standards rows, documents row) is test data built to the same shape as the
production rows.
"""

import copy
import math
import os
import sys
from typing import get_args

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.cdc_lot_authority import (
    AuthorityOutcome,
    REQUIRED_STANDARDS,
    ValidatedAuthority,
    load_authority,
    normalise_for_match,
    validate_authority,
)
from services.cdc_lot_requirements import (
    AREA_AGREEMENT_RATIO,
    WHOLE_LOT_FRACTION,
    AreaReading,
    LotInputs,
    Outcome,
    Result,
    evaluate,
    overall,
)
from services.cdc_lot_inputs import (
    PropertyNotIdentified,
    area_readings,
    combine_ass,
    parse_ass_blocks,
    parse_zone_blocks,
)
import services.cdc_lot_requirements_api as api_module
from services.cdc_lot_requirements_api import LotRequirementsRequest


# ---------------------------------------------------------------------------
# Fixture data
# ---------------------------------------------------------------------------
# The full, real provision texts (verbatim, including the em dash U+2014
# where it occurs in the source). Kept as module-level constants so every
# test starts from the same ground truth.

PROVISION_TEXT_36996 = '(3) Lot requirements Complying development specified for this code may only be carried out on a lot that meets the following requirements—'
PROVISION_TEXT_36997 = '(a) the lot must be in Zone R1, R2, R3, R4 or RU5, \n(b) the area of the lot must not be less than 200 m2 , \n(c) the width of the lot must be at least 6m measured at the building line, \n(d) there must only be 1 dwelling house on the lot at the completion of the development, \n(e) the lot must have lawful access to a public road at the completion of the development, \n(f) if the development is on a battle-axe lot—the lot must be at least 12 m by 12 m (not including the access laneway) and must have an access laneway that is at least 3 m wide, \n(g) if the development is on a corner lot—the width of the primary road boundary of the lot must be at least 6m.'  # noqa: zone-codes — test fixture rows, not a shared zone taxonomy
PROVISION_TEXT_36184 = 'Development Code, Rural Housing Code, Agritourism and Farm Stay Accommodation Code and Greenfield Housing Code To be complying development specified for the Housing Code, the Inland Code, the Low Rise Housing Diversity Code, the Pattern Book Development Code, the Rural Housing Code, the Agritourism and Farm Stay Accommodation Code or the Greenfield Housing Code, the development must not be carried out on (a) land within a heritage conservation area or a draft heritage conservation area, unless the development is a detached outbuilding, detached development (other than a detached studio) or swimming pool, or'
PROVISION_TEXT_36185 = '(b) land that is reserved for a public purpose by an environmental planning instrument, or (c) land identified on an Acid Sulfate Soils Map as being Class 1 or Class 2, or (c1) significantly contaminated land, or'

BASE_DOCUMENTS = [
    {
        "id": "DOC",
        "source_url": "https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572",
        "r2_pdf_url": "https://example.r2.dev/sepp.pdf",
    },
]

BASE_PROVISIONS = [
    {"id": 36996, "document_id": "DOC", "pdf_page": 112, "is_current": True, "provision_text": PROVISION_TEXT_36996},
    {"id": 36997, "document_id": "DOC", "pdf_page": 113, "is_current": True, "provision_text": PROVISION_TEXT_36997},
    {"id": 36184, "document_id": "DOC", "pdf_page": 23, "is_current": True, "provision_text": PROVISION_TEXT_36184},
    {"id": 36185, "document_id": "DOC", "pdf_page": 23, "is_current": True, "provision_text": PROVISION_TEXT_36185},
]

BASE_STANDARDS = [
    {
        "id": 1,
        "standard_type": "eligible_zones",
        "applicable_zones": ["R1", "R2", "R3", "R4", "RU5"],  # noqa: zone-codes — test fixture rows, not a shared zone taxonomy
        "numeric_value": None,
        "ref_number": "cl 3.1(3)(a)",
        "source_provision_ids": [36996, 36997],
        "source_quote": "(3) Lot requirements — Complying development specified for this code may only be carried out on a lot that meets the following requirements — (a) the lot must be in Zone R1, R2, R3, R4 or RU5",  # noqa: zone-codes — test fixture rows, not a shared zone taxonomy
        "manual_verified": True,
        "stale_since": None,
        "stale_reason": None,
        "verified_by": "tester",
        "verified_at": "2026-09-01",
    },
    {
        "id": 2,
        "standard_type": "min_lot_size",
        "applicable_zones": None,
        "numeric_value": 200,
        "ref_number": "cl 3.1(3)(b)",
        "source_provision_ids": [36996, 36997],
        "source_quote": "(3) Lot requirements — ... (b) the area of the lot must not be less than 200 m2",
        "manual_verified": True,
        "stale_since": None,
        "stale_reason": None,
        "verified_by": "tester",
        "verified_at": "2026-09-01",
    },
    {
        "id": 4,
        "standard_type": "min_lot_width",
        "applicable_zones": None,
        "numeric_value": 6,
        "ref_number": "cl 3.1(3)(c)",
        "source_provision_ids": [36996, 36997],
        "source_quote": "(3) Lot requirements — Complying development specified for this code may only be carried out on a lot that meets the following requirements — ... (c) the width of the lot must be at least 6m measured at the building line",
        "manual_verified": True,
        "stale_since": None,
        "stale_reason": None,
        "verified_by": "tester",
        "verified_at": "2026-09-01",
    },
    {
        "id": 3,
        "standard_type": "acid_sulfate_max_class",
        "applicable_zones": None,
        "numeric_value": 2,
        "ref_number": "cl 1.19(1)(c)",
        "source_provision_ids": [36184, 36185],
        "source_quote": "To be complying development specified for the Housing Code ... the development must not be carried out on ... (c) land identified on an Acid Sulfate Soils Map as being Class 1 or Class 2",
        "manual_verified": True,
        "stale_since": None,
        "stale_reason": None,
        "verified_by": "tester",
        "verified_at": "2026-09-01",
    },
]


def make_fixture():
    """Fresh deep copies of (standards, provisions, documents) for one test."""
    return (
        copy.deepcopy(BASE_STANDARDS),
        copy.deepcopy(BASE_PROVISIONS),
        copy.deepcopy(BASE_DOCUMENTS),
    )


def _find(rows, key, value):
    for r in rows:
        if r.get(key) == value:
            return r
    raise KeyError(value)


# ===========================================================================
# AUTHORITY — validate_authority / load_authority
# ===========================================================================


def test_valid_fixture_authority_validates():
    """The baseline fixture must validate before any other test trusts it."""
    outcome = validate_authority(*make_fixture())
    assert outcome.failures == ()
    assert outcome.authority is not None
    assert isinstance(outcome.authority, ValidatedAuthority)
    assert set(outcome.authority.standards) == set(REQUIRED_STANDARDS)


def test_width_standard_absent_is_unavailable_naming_min_lot_width():
    standards, provisions, documents = make_fixture()
    standards[:] = [s for s in standards if s["standard_type"] != "min_lot_width"]
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("min_lot_width" in f for f in outcome.failures)


def test_duplicate_active_standard_fails():
    standards, provisions, documents = make_fixture()
    dup = copy.deepcopy(_find(standards, "standard_type", "eligible_zones"))
    dup["id"] = 999
    standards.append(dup)
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("eligible_zones" in f and "exactly one active standard" in f for f in outcome.failures)


def test_manual_verified_false_fails():
    standards, provisions, documents = make_fixture()
    _find(standards, "standard_type", "min_lot_size")["manual_verified"] = False
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("min_lot_size" in f and "not manually verified" in f for f in outcome.failures)


def test_stale_since_set_fails():
    standards, provisions, documents = make_fixture()
    _find(standards, "standard_type", "min_lot_size")["stale_since"] = "2026-01-01"
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("min_lot_size" in f and "stale" in f for f in outcome.failures)


def test_cited_provision_missing_fails():
    standards, provisions, documents = make_fixture()
    provisions[:] = [p for p in provisions if p["id"] != 36997]
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("36997" in f and "does not exist" in f for f in outcome.failures)


def test_cited_provision_not_current_fails():
    standards, provisions, documents = make_fixture()
    _find(provisions, "id", 36997)["is_current"] = False
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("36997" in f and "not current" in f for f in outcome.failures)


def test_provision_text_changed_breaks_the_quote_match():
    """200 -> 250 in 36997 means the min_lot_size quote no longer matches."""
    standards, provisions, documents = make_fixture()
    prov = _find(provisions, "id", 36997)
    assert "200 m2" in prov["provision_text"]
    prov["provision_text"] = prov["provision_text"].replace("200 m2", "250 m2")
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("min_lot_size" in f and "source quote not found" in f for f in outcome.failures)


def test_standard_value_not_in_its_quote_fails():
    """min_lot_size says 300 but the quote still says 200 m2."""
    standards, provisions, documents = make_fixture()
    _find(standards, "standard_type", "min_lot_size")["numeric_value"] = 300
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("min_lot_size" in f and "does not appear in the source quote" in f for f in outcome.failures)


def test_source_url_none_fails():
    standards, provisions, documents = make_fixture()
    documents[0]["source_url"] = None
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("no authoritative source URL" in f for f in outcome.failures)


def test_source_url_not_authoritative_fails():
    standards, provisions, documents = make_fixture()
    documents[0]["source_url"] = "https://example.com/x"
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("no authoritative source URL" in f for f in outcome.failures)


def test_r2_pdf_url_empty_fails():
    standards, provisions, documents = make_fixture()
    documents[0]["r2_pdf_url"] = ""
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("no PDF" in f for f in outcome.failures)


@pytest.mark.parametrize("bad_page", [None, 0])
def test_pdf_page_missing_or_zero_fails(bad_page):
    standards, provisions, documents = make_fixture()
    _find(provisions, "id", 36997)["pdf_page"] = bad_page
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("36997" in f and "no PDF page" in f for f in outcome.failures)


def test_provisions_spanning_two_documents_fails():
    standards, provisions, documents = make_fixture()
    _find(provisions, "id", 36997)["document_id"] = "DOC2"
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("span" in f and "2 documents" in f for f in outcome.failures)


def test_invalid_zone_code_in_standard_fails():
    standards, provisions, documents = make_fixture()
    _find(standards, "standard_type", "eligible_zones")["applicable_zones"] = ["R1", "r2 low"]
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("eligible_zones" in f and "invalid zone code" in f for f in outcome.failures)


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), -5])
def test_numeric_value_not_finite_positive_fails(bad_value):
    standards, provisions, documents = make_fixture()
    _find(standards, "standard_type", "min_lot_size")["numeric_value"] = bad_value
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("min_lot_size" in f and "not a finite positive number" in f for f in outcome.failures)


@pytest.mark.parametrize("bad_class", [7, 2.5])
def test_acid_sulfate_class_out_of_range_fails(bad_class):
    standards, provisions, documents = make_fixture()
    _find(standards, "standard_type", "acid_sulfate_max_class")["numeric_value"] = bad_class
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("acid_sulfate_max_class" in f and "not a class 1-5" in f for f in outcome.failures)


def test_empty_quote_fails():
    standards, provisions, documents = make_fixture()
    _find(standards, "standard_type", "min_lot_size")["source_quote"] = ""
    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is None
    assert any("min_lot_size" in f and "no source quote" in f for f in outcome.failures)


def test_load_authority_none_connection_is_a_failure():
    outcome = load_authority(None)
    assert outcome.authority is None
    assert outcome.failures == ("no database connection",)


def test_load_authority_db_error_is_reported_and_rolls_back():
    class _RaisingCursor:
        def execute(self, *a, **kw):
            raise RuntimeError("boom")

        def close(self):
            pass

    class _RaisingConn:
        def __init__(self):
            self.rolled_back = False

        def cursor(self):
            return _RaisingCursor()

        def rollback(self):
            self.rolled_back = True

    conn = _RaisingConn()
    outcome = load_authority(conn)
    assert outcome.authority is None
    assert outcome.failures == ("authority query failed: RuntimeError",)
    assert conn.rolled_back is True


def test_load_authority_swallows_a_failing_rollback_too():
    class _RaisingCursor:
        def execute(self, *a, **kw):
            raise RuntimeError("boom")

    class _BadRollbackConn:
        def cursor(self):
            return _RaisingCursor()

        def rollback(self):
            raise Exception("rollback also failed")

    outcome = load_authority(_BadRollbackConn())
    assert outcome.authority is None
    assert outcome.failures == ("authority query failed: RuntimeError",)


# ===========================================================================
# EVALUATION — evaluate() / overall()
# ===========================================================================


@pytest.fixture
def authority():
    outcome = validate_authority(*make_fixture())
    assert outcome.authority is not None, outcome.failures
    return outcome.authority


def _passing_inputs(**overrides):
    base = dict(
        zones=frozenset({"R2"}),
        zone_source="test",
        zone_reason=None,
        areas=(AreaReading("test", 250.0),),
        area_reason=None,
        width_range_m=(10.0, 10.0),
        width_source="test",
        width_reason=None,
        ass_classes=frozenset(),
        ass_source="test",
        ass_reason=None,
        ass_excluded_fraction=None,
    )
    base.update(overrides)
    return LotInputs(**base)


def test_all_pass_is_not_excluded_by_checked_criteria(authority):
    inputs = _passing_inputs(width_range_m=(10.0, 10.0))
    criteria = evaluate(authority, inputs)
    assert [c.outcome for c in criteria] == ["PASS", "PASS", "PASS", "PASS"]
    assert overall(criteria) == "NOT_EXCLUDED_BY_CHECKED_CRITERIA"


def test_width_none_keeps_overall_unknown_never_not_excluded(authority):
    inputs = _passing_inputs(width_range_m=None)
    criteria = evaluate(authority, inputs)
    widths = [c for c in criteria if c.criterion == "lot_width"][0]
    assert widths.outcome == "UNKNOWN"
    assert overall(criteria) == "UNKNOWN"
    assert overall(criteria) != "NOT_EXCLUDED_BY_CHECKED_CRITERIA"


def test_area_exactly_at_minimum_passes(authority):
    inputs = _passing_inputs(areas=(AreaReading("test", 200.0),))
    criteria = evaluate(authority, inputs)
    area = [c for c in criteria if c.criterion == "lot_area"][0]
    assert area.outcome == "PASS"
    assert overall(criteria) == "NOT_EXCLUDED_BY_CHECKED_CRITERIA"


def test_area_just_below_minimum_fails_and_excludes(authority):
    inputs = _passing_inputs(areas=(AreaReading("test", 199.99),))
    criteria = evaluate(authority, inputs)
    area = [c for c in criteria if c.criterion == "lot_area"][0]
    assert area.outcome == "FAIL"
    assert overall(criteria) == "EXCLUDED"


def test_area_missing_is_unknown(authority):
    inputs = _passing_inputs(areas=(), area_reason=None)
    criteria = evaluate(authority, inputs)
    area = [c for c in criteria if c.criterion == "lot_area"][0]
    assert area.outcome == "UNKNOWN"
    assert "could not be established" in area.comparison


def test_area_conflicting_sources_is_unknown(authority):
    inputs = _passing_inputs(areas=(AreaReading("a", 300.0), AreaReading("b", 400.0)))
    criteria = evaluate(authority, inputs)
    area = [c for c in criteria if c.criterion == "lot_area"][0]
    assert area.outcome == "UNKNOWN"
    assert "disagree" in area.comparison


def test_area_straddling_threshold_within_agreement_is_unknown(authority):
    assert 201.0 / 199.0 <= AREA_AGREEMENT_RATIO
    inputs = _passing_inputs(areas=(AreaReading("a", 199.0), AreaReading("b", 201.0)))
    criteria = evaluate(authority, inputs)
    area = [c for c in criteria if c.criterion == "lot_area"][0]
    assert area.outcome == "UNKNOWN"
    assert "either side" in area.comparison


@pytest.mark.parametrize("bad_value", [float("nan"), float("inf"), 0, -1])
def test_area_reading_malformed_values_are_unknown(authority, bad_value):
    inputs = _passing_inputs(areas=(AreaReading("test", bad_value),))
    criteria = evaluate(authority, inputs)
    area = [c for c in criteria if c.criterion == "lot_area"][0]
    assert area.outcome == "UNKNOWN"
    assert "not a finite positive number" in area.comparison


def test_area_reason_forces_unknown_even_with_readings(authority):
    inputs = _passing_inputs(areas=(AreaReading("test", 300.0),), area_reason="a deliberate reason")
    criteria = evaluate(authority, inputs)
    area = [c for c in criteria if c.criterion == "lot_area"][0]
    assert area.outcome == "UNKNOWN"
    assert area.comparison == "a deliberate reason"


@pytest.mark.parametrize(
    "zones,expected",
    [
        (frozenset({"B4"}), "FAIL"),
        (frozenset({"R2", "R3"}), "PASS"),  # noqa: zone-codes — test fixture rows, not a shared zone taxonomy
        (frozenset({"R2", "RE1"}), "UNKNOWN"),  # noqa: zone-codes — test fixture rows, not a shared zone taxonomy
        (None, "UNKNOWN"),
    ],
)
def test_zone_outcomes(authority, zones, expected):
    inputs = _passing_inputs(zones=zones)
    criteria = evaluate(authority, inputs)
    zone = [c for c in criteria if c.criterion == "zone"][0]
    assert zone.outcome == expected


@pytest.mark.parametrize(
    "classes,frac,expected",
    [
        (None, None, "UNKNOWN"),
        (frozenset(), None, "PASS"),
        (frozenset({3}), None, "PASS"),
        (frozenset({2}), 1.0, "FAIL"),
        (frozenset({1}), 0.996, "FAIL"),
        (frozenset({2}), 0.5, "UNKNOWN"),
        (frozenset({2}), None, "UNKNOWN"),
        (frozenset({2, 5}), 1.0, "UNKNOWN"),
        (frozenset({7}), None, "UNKNOWN"),
        (frozenset({2}), float("nan"), "UNKNOWN"),
    ],
)
def test_acid_sulfate_outcomes(authority, classes, frac, expected):
    inputs = _passing_inputs(ass_classes=classes, ass_excluded_fraction=frac)
    criteria = evaluate(authority, inputs)
    ass = [c for c in criteria if c.criterion == "acid_sulfate"][0]
    assert ass.outcome == expected


@pytest.mark.parametrize("width,expected", [(5.99, "FAIL"), (6.0, "PASS")])
def test_width_outcomes(authority, width, expected):
    inputs = _passing_inputs(width_range_m=(width, width))
    criteria = evaluate(authority, inputs)
    w = [c for c in criteria if c.criterion == "lot_width"][0]
    assert w.outcome == expected


def test_thresholds_come_from_the_authority_not_a_constant():
    """Rebuild the fixture with min_lot_size = 300 (quote and provision text
    both updated so the authority still validates). The same area (250) that
    PASSED against a 200 m2 minimum must now FAIL against a 300 m2 minimum —
    proving the threshold is read from the authority, not hardcoded."""
    standards, provisions, documents = make_fixture()
    std = _find(standards, "standard_type", "min_lot_size")
    assert "200 m2" in std["source_quote"]
    std["numeric_value"] = 300
    std["source_quote"] = std["source_quote"].replace("200 m2", "300 m2")
    prov = _find(provisions, "id", 36997)
    assert "200 m2" in prov["provision_text"]
    prov["provision_text"] = prov["provision_text"].replace("200 m2", "300 m2")

    outcome = validate_authority(standards, provisions, documents)
    assert outcome.authority is not None, outcome.failures

    inputs = _passing_inputs(areas=(AreaReading("test", 250.0),))
    criteria = evaluate(outcome.authority, inputs)
    area = [c for c in criteria if c.criterion == "lot_area"][0]
    assert area.outcome == "FAIL"
    assert overall(criteria) == "EXCLUDED"


def test_evaluate_requires_a_validated_authority_instance(authority):
    inputs = _passing_inputs()
    with pytest.raises(TypeError):
        evaluate(None, inputs)
    with pytest.raises(TypeError):
        evaluate({"eligible_zones": authority.get("eligible_zones")}, inputs)


def test_evaluate_is_deterministic(authority):
    inputs = _passing_inputs()
    first = [c.model_dump() for c in evaluate(authority, inputs)]
    second = [c.model_dump() for c in evaluate(authority, copy.deepcopy(inputs))]
    assert first == second


def test_every_criterion_carries_its_standards_authority_evidence(authority):
    inputs = _passing_inputs()
    criteria = evaluate(authority, inputs)
    by_criterion_standard = {
        "zone": "eligible_zones",
        "lot_area": "min_lot_size",
        "lot_width": "min_lot_width",
        "acid_sulfate": "acid_sulfate_max_class",
    }
    for c in criteria:
        sa = authority.get(by_criterion_standard[c.criterion])
        assert c.authority.provision_ids == [p.provision_id for p in sa.provisions]
        assert c.authority.pdf_pages == [p.pdf_page for p in sa.provisions]
        assert c.authority.source_url == sa.source_url
        assert c.authority.source_quote == sa.source_quote
        assert c.clause == sa.clause


def test_result_vocabulary_is_exact_and_carries_no_liability_language():
    values = set(get_args(Result))
    assert values == {"EXCLUDED", "NOT_EXCLUDED_BY_CHECKED_CRITERIA", "UNKNOWN", "UNAVAILABLE"}
    forbidden = ("eligible", "compliant", "buildable", "permitted", "approved")
    for v in values:
        lowered = v.lower()
        for word in forbidden:
            assert word not in lowered, f"{v!r} contains forbidden word {word!r}"
    outcome_values = set(get_args(Outcome))
    assert outcome_values == {"FAIL", "PASS", "UNKNOWN"}


# ===========================================================================
# INPUT PARSING — services/cdc_lot_inputs.py pure helpers
# ===========================================================================


def test_parse_zone_blocks_empty_list():
    zones, reason = parse_zone_blocks([])
    assert zones is None
    assert reason


def test_parse_zone_blocks_no_zoning_layer():
    zones, reason = parse_zone_blocks([{"layerName": "Flood Planning Area", "results": [{"Class": "High"}]}])
    assert zones is None
    assert reason


def test_parse_zone_blocks_two_results():
    raw = [{"layerName": "Land Zoning Map", "results": [{"Zone": "R2"}, {"Zone": "RE1"}]}]  # noqa: zone-codes — test fixture rows, not a shared zone taxonomy
    zones, reason = parse_zone_blocks(raw)
    assert zones == frozenset({"R2", "RE1"})  # noqa: zone-codes — test fixture rows, not a shared zone taxonomy
    assert reason is None


def test_parse_zone_blocks_invalid_code():
    raw = [{"layerName": "Land Zoning Map", "results": [{"Zone": "r2 low"}]}]
    zones, reason = parse_zone_blocks(raw)
    assert zones is None
    assert reason


def test_parse_zone_blocks_empty_results():
    raw = [{"layerName": "Land Zoning Map", "results": []}]
    zones, reason = parse_zone_blocks(raw)
    assert zones is None
    assert reason


def test_parse_ass_blocks_raw_without_zoning_is_none():
    raw = [{"layerName": "Acid Sulfate Soils Map", "results": [{"Class": "Class 5"}]}]
    classes, reason = parse_ass_blocks(raw)
    assert classes is None
    assert reason


def test_parse_ass_blocks_zoning_present_no_ass_block_is_empty_set():
    raw = [{"layerName": "Land Zoning Map", "results": [{"Zone": "R2"}]}]
    classes, reason = parse_ass_blocks(raw)
    assert classes == frozenset()
    assert reason is None


def test_parse_ass_blocks_class_5():
    raw = [
        {"layerName": "Land Zoning Map", "results": [{"Zone": "R2"}]},
        {"layerName": "Acid Sulfate Soils Map", "results": [{"Class": "Class 5"}]},
    ]
    classes, reason = parse_ass_blocks(raw)
    assert classes == frozenset({5})
    assert reason is None


def test_parse_ass_blocks_class_2a_is_invalid():
    raw = [
        {"layerName": "Land Zoning Map", "results": [{"Zone": "R2"}]},
        {"layerName": "Acid Sulfate Soils Map", "results": [{"Class": "Class 2a"}]},
    ]
    classes, reason = parse_ass_blocks(raw)
    assert classes is None
    assert reason


def test_parse_ass_blocks_buffer_area_is_invalid():
    raw = [
        {"layerName": "Land Zoning Map", "results": [{"Zone": "R2"}]},
        {"layerName": "Acid Sulfate Soils Map", "results": [{"Class": "Buffer Area"}]},
    ]
    classes, reason = parse_ass_blocks(raw)
    assert classes is None
    assert reason


def test_parse_ass_blocks_two_results():
    raw = [
        {"layerName": "Land Zoning Map", "results": [{"Zone": "R2"}]},
        {"layerName": "Acid Sulfate Soils Map", "results": [{"Class": "Class 2"}, {"Class": "Class 5"}]},
    ]
    classes, reason = parse_ass_blocks(raw)
    assert classes == frozenset({2, 5})
    assert reason is None


def test_combine_ass_conflict():
    result, reason = combine_ass(frozenset(), None, frozenset({2}), 2)
    assert result is None
    assert "conflict" in reason


def test_combine_ass_agreement():
    result, reason = combine_ass(frozenset({5}), None, frozenset({5}), 2)
    assert result == frozenset({5})
    assert reason is None


def test_combine_ass_portal_none_passes_reason_through():
    result, reason = combine_ass(None, "portal failed", frozenset({2}), 2)
    assert result is None
    assert reason == "portal failed"


def test_area_readings_two_valid():
    readings, reason = area_readings(480.0, 486.9)
    assert reason is None
    assert len(readings) == 2
    assert {r.value_m2 for r in readings} == {480.0, 486.9}


def test_area_readings_one_absent():
    readings, reason = area_readings(None, 486.9)
    assert reason is None
    assert len(readings) == 1
    assert readings[0].value_m2 == 486.9


def test_area_readings_nan_is_a_reason_not_a_drop():
    readings, reason = area_readings(float("nan"), 486.9)
    assert readings == ()
    assert reason


def test_area_readings_zero_is_invalid():
    readings, reason = area_readings(0, None)
    assert readings == ()
    assert reason


def test_area_readings_non_numeric_is_invalid():
    readings, reason = area_readings("abc", None)
    assert readings == ()
    assert reason


# ===========================================================================
# API / BOUNDARY — services/cdc_lot_requirements_api.py
# ===========================================================================


def test_run_lot_requirements_authority_failure_short_circuits(monkeypatch):
    def fake_load_authority(conn):
        return AuthorityOutcome(None, ("x",))

    def fail_if_called(*a, **kw):
        raise AssertionError("load_lot_inputs must not be called when authority is unavailable")

    monkeypatch.setattr(api_module, "load_authority", fake_load_authority)
    monkeypatch.setattr(api_module, "load_lot_inputs", fail_if_called)

    result = api_module.run_lot_requirements("1 Coward Street, Mascot", object())
    assert result.result == "UNAVAILABLE"
    assert result.criteria == []
    assert result.authority_failures == ["x"]


def test_run_lot_requirements_property_not_identified_is_unknown(monkeypatch, authority):
    monkeypatch.setattr(api_module, "load_authority", lambda conn: AuthorityOutcome(authority, ()))

    def raise_not_identified(address, conn, excluded_ass_max):
        raise PropertyNotIdentified(address)

    monkeypatch.setattr(api_module, "load_lot_inputs", raise_not_identified)
    result = api_module.run_lot_requirements("nowhere", object())
    assert result.result == "UNKNOWN"
    assert len(result.criteria) == 4
    assert all(c.outcome == "UNKNOWN" for c in result.criteria)


def test_run_lot_requirements_upstream_error_is_unknown(monkeypatch, authority):
    monkeypatch.setattr(api_module, "load_authority", lambda conn: AuthorityOutcome(authority, ()))

    def raise_runtime_error(address, conn, excluded_ass_max):
        raise RuntimeError("portal is down")

    monkeypatch.setattr(api_module, "load_lot_inputs", raise_runtime_error)
    result = api_module.run_lot_requirements("1 Coward Street, Mascot", object())
    assert result.result == "UNKNOWN"
    assert len(result.criteria) == 4
    assert all(c.outcome == "UNKNOWN" for c in result.criteria)


def test_lot_requirements_request_rejects_extra_zone_field():
    with pytest.raises(ValidationError):
        LotRequirementsRequest(address="1 Coward Street, Mascot", zone="R2")


def test_lot_requirements_request_rejects_extra_eligible_field():
    with pytest.raises(ValidationError):
        LotRequirementsRequest(address="1 Coward Street, Mascot", eligible=True)


def _client():
    app = FastAPI()
    app.include_router(api_module.router)
    return TestClient(app)


def test_endpoint_rejects_body_with_extra_field():
    resp = _client().post(
        "/pipeline/cdc/lot-requirements",
        json={"address": "1 Coward Street, Mascot NSW", "zone": "R2"},
    )
    assert resp.status_code == 422


def test_endpoint_returns_503_when_authority_unavailable(monkeypatch):
    monkeypatch.setattr(api_module, "_connect", lambda: None)
    monkeypatch.setattr(api_module, "load_authority", lambda conn: AuthorityOutcome(None, ("no authority",)))
    resp = _client().post(
        "/pipeline/cdc/lot-requirements",
        json={"address": "1 Coward Street, Mascot NSW"},
    )
    assert resp.status_code == 503
    body = resp.json()
    assert body["result"] == "UNAVAILABLE"


# ===========================================================================
# STATIC — no LLM/AI-provider names anywhere in the four modules under test
# ===========================================================================


@pytest.mark.parametrize(
    "relpath",
    [
        "services/cdc_lot_authority.py",
        "services/cdc_lot_requirements.py",
        "services/cdc_lot_inputs.py",
        "services/cdc_lot_requirements_api.py",
    ],
)
def test_module_contains_no_ai_provider_names(relpath):
    repo_root = os.path.join(os.path.dirname(__file__), "..")
    path = os.path.join(repo_root, relpath)
    with open(path, "r", encoding="utf-8") as f:
        text = f.read().lower()
    forbidden = ("anthropic", "openai", "gemini", "generatetext", "google.generativeai", "langextract")
    for word in forbidden:
        assert word not in text, f"{relpath} contains forbidden term {word!r}"


# ---------------------------------------------------------------------------
# Width at the building line: exact only for rectangular lots
# ---------------------------------------------------------------------------
import math as _math

from services.cdc_lot_inputs import rectangle_width_range

# EPSG:3857 metres near Sydney (lat ~ -33.9): local metres x scale = mercator metres.
_Y0 = -4_018_000.0
_SCALE = 1.0 / _math.cos(_math.radians(33.9))


def _ring(local_pts):
    """Local metre coordinates -> a closed EPSG:3857 ring at Sydney's latitude."""
    pts = [[16_820_000.0 + x * _SCALE, _Y0 + y * _SCALE] for x, y in local_pts]
    return {"rings": [pts + [pts[0]]]}


def _rotate(pts, deg):
    r = _math.radians(deg)
    return [(x * _math.cos(r) - y * _math.sin(r), x * _math.sin(r) + y * _math.cos(r)) for x, y in pts]


def test_rectangle_gives_exact_side_range():
    rng, why = rectangle_width_range(_ring([(0, 0), (12, 0), (12, 40), (0, 40)]))
    assert why is None
    assert rng[0] == pytest.approx(12.0, abs=0.05) and rng[1] == pytest.approx(40.0, abs=0.05)


def test_rotated_rectangle_with_points_on_straight_boundaries():
    pts = _rotate([(0, 0), (6, 0), (12, 0), (12, 20), (12, 40), (0, 40)], 33)
    rng, why = rectangle_width_range(_ring(pts))
    assert why is None and rng[0] == pytest.approx(12.0, abs=0.05)


@pytest.mark.parametrize("pts", [
    [(0, 0), (12, 0), (14, 40), (0, 40)],               # trapezoid: width varies with depth
    [(0, 0), (20, 0), (20, 20), (8, 20), (8, 40), (0, 40)],  # L-shape / battle-axe like
    [(0, 0), (12, 0), (6, 30)],                          # triangle
])
def test_non_rectangle_is_unknown(pts):
    rng, why = rectangle_width_range(_ring(pts))
    assert rng is None and "not a rectangle" in why


@pytest.mark.parametrize("geom", [None, {}, {"rings": []}, {"rings": [[[0, 0], [1, float("nan")], [2, 2], [0, 0]]]},
                                  {"rings": [[[0, 0], [1, 0], [1, 1], [0, 0]], [[0, 0], [1, 0], [1, 1], [0, 0]]]}])
def test_malformed_geometry_is_unknown(geom):
    rng, why = rectangle_width_range(geom)
    assert rng is None and why


def test_narrow_rectangle_width_criterion_unknown_not_fail(authority):
    # 5 m x 40 m: if the 40 m side faced the road the width would be 40 m, so the
    # building-line width is not determinable -> UNKNOWN, never FAIL.
    rng, _ = rectangle_width_range(_ring([(0, 0), (5, 0), (5, 40), (0, 40)]))
    crit = evaluate(authority, _passing_inputs(width_range_m=rng))
    width = [c for c in crit if c.criterion == "lot_width"][0]
    assert width.outcome == "UNKNOWN"


def test_tiny_rectangle_fails_width_both_ways(authority):
    rng, _ = rectangle_width_range(_ring([(0, 0), (5, 0), (5, 5.5), (0, 5.5)]))
    crit = evaluate(authority, _passing_inputs(width_range_m=rng))
    assert [c for c in crit if c.criterion == "lot_width"][0].outcome == "FAIL"


@pytest.mark.parametrize("rng", [(float("nan"), 10.0), (0.0, 10.0), (10.0, 5.0), (5.0,), "12"])
def test_invalid_width_range_is_unknown(rng, authority):
    crit = evaluate(authority, _passing_inputs(width_range_m=rng))
    assert [c for c in crit if c.criterion == "lot_width"][0].outcome == "UNKNOWN"
