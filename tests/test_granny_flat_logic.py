"""
Adversarial unit tests for services/granny_flat.py — pure logic functions.

Covers untested areas beyond the 13 geometry tests:
  _compute_confidence  — 4 branches (low/medium/high + edge cases)
  _get_weekly_rent     — postcode lookup, fallback chain, null entry
  _compute_lot_area_m2 — empty rings (regression for IndexError bug)
"""

import sys
import os
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.granny_flat import (
    _compute_confidence,
    _review_state,
    _REVIEW_STATE_TEXT,
    _get_weekly_rent,
    _compute_lot_area_m2,
    _check_heritage_overlay,
    GrannyFlatDetectResponse,
)

# Test fixture bound only — mirrors the prod housing_sepp_standards row. The
# service itself carries no such constant (#817).
SEPP_MIN_LOT_M2 = 450.0


# ---------------------------------------------------------------------------
# _compute_confidence
# ---------------------------------------------------------------------------

def test_compute_confidence_low_when_not_validated():
    conf, reason = _compute_confidence(
        validated=False, confirmed_count=2, samgeo_count=2, rent_available=True
    )
    assert conf == "low"
    assert "pre-validation" in reason.lower()


def test_compute_confidence_high_when_validated_counts_agree_and_rent_available():
    """FLIPPED 2026-08-06 (calibration Lane 1, item 3).

    This test used to omit count_source and assert "high" on count equality
    alone. That was the 0%-drift trap: the count was seeded from the detector
    and the UI could not edit it, so equality was the detector agreeing with
    itself. "high" now requires count_source='secondary_detections_classified'.
    """
    conf, reason = _compute_confidence(
        validated=True, confirmed_count=3, samgeo_count=3, rent_available=True,
        count_source="secondary_detections_classified",
    )
    assert conf == "high"
    assert "3" in reason
    assert "structures" in reason.lower()


def test_compute_confidence_agreement_without_human_is_not_high():
    """The self-agreement case, pinned: same numbers, no human, never 'high'."""
    for source in ("unrecorded", "machine_default"):
        conf, reason = _compute_confidence(
            validated=True, confirmed_count=3, samgeo_count=3, rent_available=True,
            count_source=source,
        )
        assert conf == "medium", source
        assert "not reviewed structure by structure" in reason, source


def test_compute_confidence_default_count_source_is_not_high():
    """A caller that says nothing about provenance must not earn 'high'.

    Three states: absent is its own state, never folded into 'a human checked'.
    """
    conf, _ = _compute_confidence(
        validated=True, confirmed_count=3, samgeo_count=3, rent_available=True
    )
    assert conf == "medium"


def test_compute_confidence_high_single_structure():
    """Plural check: 1 structure should say 'structure' not 'structures'."""
    conf, reason = _compute_confidence(
        validated=True, confirmed_count=1, samgeo_count=1, rent_available=True,
        count_source="secondary_detections_classified",
    )
    assert conf == "high"
    # singular
    assert "structures" not in reason


def test_compute_confidence_medium_when_counts_disagree():
    conf, reason = _compute_confidence(
        validated=True, confirmed_count=2, samgeo_count=3, rent_available=True
    )
    assert conf == "medium"
    assert "2" in reason
    assert "3" in reason


def test_compute_confidence_medium_when_rent_missing():
    conf, reason = _compute_confidence(
        validated=True, confirmed_count=2, samgeo_count=2, rent_available=False
    )
    assert conf == "medium"
    assert "postcode" in reason.lower() or "rent" in reason.lower()


def test_compute_confidence_medium_counts_agree_but_rent_missing():
    """Counts agree but no rent data → medium, not high."""
    conf, _ = _compute_confidence(
        validated=True, confirmed_count=1, samgeo_count=1, rent_available=False
    )
    assert conf == "medium"


def test_compute_confidence_medium_when_samgeo_count_none():
    """samgeo_count=None means detection wasn't run → fallback to 'entered manually' path."""
    conf, reason = _compute_confidence(
        validated=True, confirmed_count=2, samgeo_count=None, rent_available=True
    )
    assert conf == "medium"
    assert "manually" in reason.lower()


def test_compute_confidence_zero_counts_agree():
    """confirmed=0, samgeo=0 — high only when a person reviewed it.

    FLIPPED 2026-08-06 (Lane 1, item 3): previously asserted "high" without
    count_source. An empty lot the detector reported and nobody looked at is
    not a higher-confidence result than any other unreviewed count.
    """
    conf, _ = _compute_confidence(
        validated=True, confirmed_count=0, samgeo_count=0, rent_available=True,
        count_source="secondary_detections_classified",
    )
    assert conf == "high"

    conf_unchecked, _ = _compute_confidence(
        validated=True, confirmed_count=0, samgeo_count=0, rent_available=True
    )
    assert conf_unchecked == "medium"


# ---------------------------------------------------------------------------
# _get_weekly_rent
# ---------------------------------------------------------------------------

def test_get_weekly_rent_none_postcode_returns_none():
    assert _get_weekly_rent(None) is None


def test_get_weekly_rent_empty_string_returns_none():
    assert _get_weekly_rent("") is None


def test_get_weekly_rent_unknown_postcode_returns_none():
    """Postcode not in rental data → None."""
    assert _get_weekly_rent("0000") is None


def test_get_weekly_rent_known_postcode_with_mock(monkeypatch):
    """Valid postcode in rental data → float."""
    import services.granny_flat as gf
    monkeypatch.setattr(gf, "_RENTAL_DATA_CACHE", {"2010": {"median_weekly_rent_1br_aud": 500.0}})
    result = _get_weekly_rent("2010")
    assert result == 500.0


def test_get_weekly_rent_postcode_present_but_rent_null(monkeypatch):
    """Entry exists but median_weekly_rent_1br_aud is null → None."""
    import services.granny_flat as gf
    monkeypatch.setattr(gf, "_RENTAL_DATA_CACHE", {"2010": {"median_weekly_rent_1br_aud": None}})
    result = _get_weekly_rent("2010")
    assert result is None


def test_get_weekly_rent_int_postcode_coerced(monkeypatch):
    """postcode='2010' must match data key '2010' — both are strings."""
    import services.granny_flat as gf
    monkeypatch.setattr(gf, "_RENTAL_DATA_CACHE", {"2010": {"median_weekly_rent_1br_aud": 450.0}})
    result = _get_weekly_rent("2010")
    assert result == 450.0


# ---------------------------------------------------------------------------
# _compute_lot_area_m2 — empty rings regression
# ---------------------------------------------------------------------------

def test_compute_lot_area_m2_empty_rings_returns_none():
    """{'rings': []} was raising IndexError on rings[0]. Fixed with `not lot_geometry['rings']` guard."""
    result = _compute_lot_area_m2({"rings": []})
    assert result is None


def test_compute_lot_area_m2_null_rings_returns_none():
    """rings=None is also guarded (falsy check)."""
    result = _compute_lot_area_m2({"rings": None})
    assert result is None


def test_compute_lot_area_m2_ring_too_short_returns_none():
    """Ring with < 3 points — not a polygon."""
    result = _compute_lot_area_m2({"rings": [[
        [16824000.0, -4020000.0],
        [16824100.0, -4020000.0],
    ]]})
    assert result is None


def test_compute_lot_area_m2_known_square_at_sydney():
    """200x200m tile in EPSG:3857 near Sydney (-33.87°).
    Mercator scale factor at lat=-33.87° is cos(33.87°) ≈ 0.8305.
    True area ≈ (200*0.8305)² ≈ 27,593 m². Verify within ±10%."""
    ring = [
        [16825000.0, -4012000.0],
        [16825200.0, -4012000.0],
        [16825200.0, -4012200.0],
        [16825000.0, -4012200.0],
        [16825000.0, -4012000.0],
    ]
    result = _compute_lot_area_m2({"rings": [ring]})
    assert result is not None
    assert result == pytest.approx(27_593, rel=0.10)


def test_compute_lot_area_m2_small_lot_below_sepp_minimum():
    """A 10x10m tile in EPSG:3857 near Sydney → ~69 m² true area.
    Must be well below SEPP_MIN_LOT_M2 (450)."""
    ring = [
        [16825000.0, -4012000.0],
        [16825010.0, -4012000.0],
        [16825010.0, -4012010.0],
        [16825000.0, -4012010.0],
        [16825000.0, -4012000.0],
    ]
    result = _compute_lot_area_m2({"rings": [ring]})
    assert result is not None
    assert result < SEPP_MIN_LOT_M2


# ---------------------------------------------------------------------------
# existing_secondary_dwelling — SEPP cl 53(1) gate + confidence cap
# These test the logic in confirm_and_calculate via direct field inspection.
# ---------------------------------------------------------------------------

from services.granny_flat import GrannyFlatConfirmRequest


def _make_confirm_req(**overrides) -> GrannyFlatConfirmRequest:
    defaults = dict(
        detect_id="test-id",
        address="1 Test St, Sydney NSW 2000",
        prop_id="12345",
        lat=-33.8688,
        lng=151.2093,
        lot_area_m2=600.0,
        confirmed_structure_count=1,
        samgeo_structure_count=1,
        postcode="2000",
        report_id=None,
        is_heritage=False,
        existing_secondary_dwelling=None,
    )
    defaults.update(overrides)
    return GrannyFlatConfirmRequest(**defaults)


def test_existing_secondary_dwelling_model_accepts_all_three_states():
    """existing_secondary_dwelling field accepts True, False, None."""
    for val, expected in [(True, True), (False, False), (None, None)]:
        req = _make_confirm_req(existing_secondary_dwelling=val)
        assert req.existing_secondary_dwelling is expected, f"Failed for {val}"


# ---------------------------------------------------------------------------
# _check_heritage_overlay — monkeypatched DB for real logic testing
# ---------------------------------------------------------------------------

def test_check_heritage_overlay_returns_true_when_row_found(monkeypatch):
    """Simulate DB returning a row → function must return True."""
    import services.granny_flat as gf

    class FakeCursor:
        def execute(self, *a, **kw): pass
        def fetchone(self): return (1,)  # row found
        def __enter__(self): return self
        def __exit__(self, *a): pass

    class FakeConn:
        def cursor(self, **kw): return FakeCursor()
        def close(self): pass

    monkeypatch.setattr(gf, "_get_conn", lambda: FakeConn())
    assert _check_heritage_overlay(-33.87, 151.21) is True


def test_check_heritage_overlay_returns_false_when_no_row(monkeypatch):
    """Simulate DB returning no rows → function must return False."""
    import services.granny_flat as gf

    class FakeCursor:
        def execute(self, *a, **kw): pass
        def fetchone(self): return None  # no row
        def __enter__(self): return self
        def __exit__(self, *a): pass

    class FakeConn:
        def cursor(self, **kw): return FakeCursor()
        def close(self): pass

    monkeypatch.setattr(gf, "_get_conn", lambda: FakeConn())
    assert _check_heritage_overlay(-33.87, 151.21) is False


def test_check_heritage_overlay_returns_none_on_db_error(monkeypatch):
    """DB connection failure → function must return None (not crash)."""
    import services.granny_flat as gf
    monkeypatch.setattr(gf, "_get_conn", lambda: (_ for _ in ()).throw(ConnectionError("no db")))
    assert _check_heritage_overlay(-33.87, 151.21) is None


def test_check_heritage_overlay_query_uses_correct_lng_lat_order(monkeypatch):
    """ST_MakePoint takes (lng, lat) — verify the order is correct."""
    import services.granny_flat as gf
    captured_params = []

    class FakeCursor:
        def execute(self, sql, params=None):
            if params:
                captured_params.append(params)
        def fetchone(self): return None
        def __enter__(self): return self
        def __exit__(self, *a): pass

    class FakeConn:
        def cursor(self, **kw): return FakeCursor()
        def close(self): pass

    monkeypatch.setattr(gf, "_get_conn", lambda: FakeConn())
    _check_heritage_overlay(-33.87, 151.21)
    # Second execute call is the actual query (first is SET LOCAL statement_timeout)
    assert len(captured_params) == 1
    lng_param, lat_param = captured_params[0]
    assert lng_param == 151.21, f"First param should be lng, got {lng_param}"
    assert lat_param == -33.87, f"Second param should be lat, got {lat_param}"


# ---------------------------------------------------------------------------
# GrannyFlatDetectResponse — is_heritage field contract
# ---------------------------------------------------------------------------

def test_detect_response_heritage_field_is_optional_bool():
    """is_heritage exists, defaults to None, accepts True/False/None."""
    assert "is_heritage" in GrannyFlatDetectResponse.model_fields
    resp = GrannyFlatDetectResponse(
        address="1 Test St", lat=-33.87, lng=151.21, prop_id="12345",
        lot_area_m2=600.0, sepp_eligible=True, sepp_ineligible_reason=None,
        detected_structures=[], samgeo_structure_count=0, samgeo_validated=True,
        confirmation_required=True, tile_licence="test", detect_id="test-id",
    )
    assert resp.is_heritage is None
    resp2 = GrannyFlatDetectResponse(
        address="1 Test St", lat=-33.87, lng=151.21, prop_id="12345",
        lot_area_m2=600.0, sepp_eligible=True, sepp_ineligible_reason=None,
        detected_structures=[], samgeo_structure_count=0, samgeo_validated=True,
        confirmation_required=True, tile_licence="test", detect_id="test-id",
        is_heritage=True,
    )
    assert resp2.is_heritage is True


# ---------------------------------------------------------------------------
# Heritage user override vs auto-detect — confirm request logic
# ---------------------------------------------------------------------------

def test_confirm_req_heritage_user_override_takes_precedence():
    """When user provides is_heritage, their value wins over auto-detect."""
    req_true = _make_confirm_req(is_heritage=True)
    req_false = _make_confirm_req(is_heritage=False)
    req_none = _make_confirm_req(is_heritage=None)
    # User-provided values are preserved exactly
    assert req_true.is_heritage is True
    assert req_false.is_heritage is False
    # None triggers auto-detect path
    assert req_none.is_heritage is None


# ---------------------------------------------------------------------------
# _review_state — what happened to the structure list, not how good it is
#
# Break-it framing (/qa-break): every test below targets a SILENT WRONG
# RESULT, not a crash. The dangerous failure here is not an exception — it is
# a lot the scan never looked at being described to a buyer as checked.
# ---------------------------------------------------------------------------

def _s(area=40.0, main=False, index=0):
    """A detected structure as the detect endpoint stores it (plain dict)."""
    return {"index": index, "area_m2": area, "is_main_dwelling": main}


def test_review_state_unknown_count_is_never_read_as_zero():
    """None means the scan produced no count. It is NOT zero structures.

    This is the three-state contract the detect endpoint writes (#745 D4):
    `samgeo_structure_count=None if detection_failed else len(...)`. If this
    ever resolved to a 'nothing found' state, a failed scan would tell someone
    their lot is clear — the exact substitution this change exists to stop.
    19 of 60 stored detect runs are in this state.
    """
    state, label, detail = _review_state(
        validated=True, count_source="unrecorded",
        detected_structures=None, machine_count=None,
    )
    assert state == "not_assessed"
    assert "not" in detail.lower()


def test_review_state_unresolvable_detect_row_beats_a_claimed_review():
    """A review we cannot check is not a review.

    The caller can claim any provenance it likes; if the detect row could not
    be re-read there is nothing to check the claim against, and absent
    evidence is its own outcome, never a pass. Guards the D5 path.
    """
    state, _, _ = _review_state(
        validated=True,
        count_source="secondary_detections_classified",
        detected_structures=[_s(main=True), _s(index=1)],
        machine_count=2,
        detect_row_unavailable=True,
    )
    assert state == "not_assessed"


def test_review_state_empty_detection_is_inconclusive_not_a_clear_lot():
    """Zero structures of any kind means the scan could not see the house.

    Every lot this product runs on has a principal dwelling, so a scan
    returning nothing at all evidences a failed read, not an empty lot.
    Collapsing this into 'no secondary structures found' would report a clear
    lot on the strength of a scan that missed a house.
    """
    state, label, detail = _review_state(
        validated=True, count_source="machine_default",
        detected_structures=[], machine_count=0,
    )
    assert state == "scan_inconclusive"
    assert "unknown" in detail.lower()
    assert "no secondary structures found" not in label.lower()


def test_review_state_main_dwelling_only_is_none_found_not_found():
    """One structure, flagged main -> nothing secondary was detected."""
    state, _, detail = _review_state(
        validated=True, count_source="machine_default",
        detected_structures=[_s(main=True, area=180.0)], machine_count=1,
    )
    assert state == "scan_only_none_found"
    # The honest caveat the user ruling asked for, in the served text.
    assert "missed" in detail.lower()
    assert "never been measured" in detail.lower()


def test_review_state_secondary_present_is_found_not_reviewed():
    state, label, _ = _review_state(
        validated=True, count_source="machine_default",
        detected_structures=[_s(main=True, area=180.0), _s(area=30.0, index=1)],
        machine_count=2,
    )
    assert state == "scan_only_found"
    assert "not reviewed" in label.lower()


def test_review_state_reviewed_requires_the_resolved_provenance():
    """Only the value _resolve_count_source licenses can reach 'reviewed'."""
    detected = [_s(main=True, area=180.0), _s(area=30.0, index=1)]
    for source in ("unrecorded", "machine_default", "", "user_verified"):
        state, _, _ = _review_state(
            validated=True, count_source=source,
            detected_structures=detected, machine_count=2,
        )
        assert state != "reviewed", f"{source!r} must not buy 'reviewed'"
    state, _, _ = _review_state(
        validated=True, count_source="secondary_detections_classified",
        detected_structures=detected, machine_count=2,
    )
    assert state == "reviewed"


def test_review_state_reviewed_does_not_claim_the_list_is_complete():
    """'Reviewed by you' must say what it cannot cover, in the same breath.

    A person can only classify what the scan showed them. If the scan missed a
    structure, the review checks a wrong list and the report looks MORE
    trustworthy for it. That caveat is load-bearing, not decoration.
    """
    _, label, detail = _review_state(
        validated=True, count_source="secondary_detections_classified",
        detected_structures=[_s(main=True), _s(index=1)], machine_count=2,
    )
    assert "you" in label.lower()
    assert "missed" in detail.lower()
    assert "never been measured" in detail.lower()


def test_reviewed_never_claims_the_totals_agree():
    """`reviewed` is licensed by answer COVERAGE, not by count equality.

    Sol finding 2026-08-06. `_resolve_count_source` grants
    'secondary_detections_classified' when every detected secondary structure
    has an answer and the submitted count follows from those answers. But
    answering 'part_of_main' or 'rejected' legitimately moves the total away
    from the detector's own count — that row is still reviewed, and
    `_compute_confidence` separately declines to call it "high" and says the
    counts differ. The old detail asserted "your answers give the same total"
    on EVERY reviewed report, so in exactly that case the two halves of one
    report contradicted each other and the state text was the false one.
    """
    detail = _REVIEW_STATE_TEXT["reviewed"][1].lower()
    assert "same total" not in detail
    assert "counts agree" not in detail
    # It still says what was actually done.
    assert "classified each structure" in detail

    # The disagreeing case: 2 detected, the secondary answered 'part_of_main',
    # so the effective total is 1 while the detector counted 2.
    state, _, served = _review_state(
        validated=True, count_source="secondary_detections_classified",
        detected_structures=[_s(main=True, area=180.0), _s(area=25.0, index=1)],
        machine_count=2,
    )
    assert state == "reviewed"
    assert "same total" not in served.lower()


def test_review_state_legacy_row_counts_are_totals_not_secondary_counts():
    """samgeo_structure_count includes the principal dwelling.

    Verified against all 60 stored detect rows on 2026-08-06 (samgeo=3 -> 1
    main + 2 secondary; samgeo=1 -> main only). Reading it as a count of
    SECONDARY structures would report every ordinary single-house lot as
    already having one — and cl 53(1) blocks a second secondary dwelling.
    """
    assert _review_state(True, "unrecorded", None, 1)[0] == "scan_only_none_found"
    assert _review_state(True, "unrecorded", None, 2)[0] == "scan_only_found"
    assert _review_state(True, "unrecorded", None, 0)[0] == "scan_inconclusive"
    assert _review_state(True, "unrecorded", None, None)[0] == "not_assessed"


def test_review_state_malformed_count_is_unknown_not_a_finding():
    """A broken count must not become a statement about the lot.

    Sol finding 2026-08-06: `False <= 0` and `-1 <= 0` are both True in
    Python, so the old comparison served a boolean or a negative as
    "the scan ran and returned no structures". Mirrors strictCount() in
    lib/granny-flat-review-state.ts — the two implementations describe the
    same row identically or the parity of this module is meaningless.
    """
    for bad in (False, True, -1, -5, 2.5, "2", "", None, [], {}):
        assert _review_state(True, "unrecorded", None, bad)[0] == "not_assessed", (
            f"machine_count={bad!r} must be unknown, not a finding")


def test_confirm_treats_an_unmatched_detect_row_as_not_assessed():
    """An unmatched detect row is as blind as a failed read.

    The confirm endpoint warns on BOTH conditions together
    (`detect_row_unavailable or not isinstance(carry, list)`), because in
    either case the count falls back to the caller's own figure. The state
    must use the same condition, or an unmatched row would let
    `req.samgeo_structure_count` — a number supplied by the requester —
    decide how the report describes the scan.
    """
    # No structure list, but a caller-supplied count that would otherwise
    # resolve to a confident-sounding state.
    state, _, _ = _review_state(
        validated=True, count_source="machine_default",
        detected_structures=None, machine_count=2,
        detect_row_unavailable=True,
    )
    assert state == "not_assessed"


def test_review_state_legacy_row_can_never_be_reviewed():
    """No pre-2026-08-06 row carries human input; none may claim it.

    Measured: 0 of 20 completed rows carry `confirmed_count_source` at all.
    The standalone tool passed `onCountChange` to a component that never
    called it, so the count could only echo the detector.
    """
    state, _, _ = _review_state(
        validated=True, count_source="unrecorded",
        detected_structures=None, machine_count=2,
    )
    assert state != "reviewed"


def test_review_state_detection_disabled_is_not_assessed():
    """SAMGEO_VALIDATED=False skips the detection block entirely.

    The block that sets detection_failed never runs, so the row would carry
    detection_failed=False with an empty structure list — 'did not run'
    wearing 'found nothing' as a costume. Latent while the module constant is
    True; pinned so flipping it cannot ship a silent lie.
    """
    state, _, _ = _review_state(
        validated=False, count_source="machine_default",
        detected_structures=[], machine_count=0,
    )
    assert state == "not_assessed"


def test_review_state_every_state_has_distinct_served_text():
    """A mutant returning one constant state must not pass.

    If any two states shared a label, the badge would stop distinguishing the
    thing it exists to distinguish.
    """
    labels = {k: v[0] for k, v in _REVIEW_STATE_TEXT.items()}
    assert len(set(labels.values())) == len(labels), labels
    details = {k: v[1] for k, v in _REVIEW_STATE_TEXT.items()}
    assert len(set(details.values())) == len(details)


def test_review_state_no_state_uses_banned_grade_or_assurance_words():
    """Served wording gate: no grade language, no umbrella 'verified'.

    'verified' is banned outright (output-grounding campaign language ladder).
    'high/medium/low confidence' is the ladder this change removes — it must
    not survive in the replacement text.
    """
    banned = ("verified", "guaranteed", "certified", "reliable",
              "high confidence", "medium confidence", "low confidence")
    for state, (label, detail) in _REVIEW_STATE_TEXT.items():
        blob = f"{label} {detail}".lower()
        for word in banned:
            assert word not in blob, f"{state} says {word!r}: {blob}"


def test_review_state_text_matches_typescript():
    """The Python and TypeScript copies of the served wording must be identical.

    The PDF route and the report pages are TypeScript and cannot call this
    module, so the text exists twice. Two copies of served wording drifting
    apart is how a surface ends up making a claim the backend retired —
    exactly the DQ-50 shape. This test is the reason the duplication is safe.
    """
    import re
    ts_path = os.path.join(
        os.path.dirname(__file__), "..", "frontend-nextjs", "lib",
        "granny-flat-review-state.ts")
    if not os.path.exists(ts_path):
        pytest.skip("frontend-nextjs not present in this checkout")
    src = open(ts_path, encoding="utf-8").read()

    block = re.search(
        r"const TEXT: Record<GrannyReviewState[^=]*=\s*\{(.*?)\n\};",
        src, re.S)
    assert block, "TEXT map not found in granny-flat-review-state.ts"

    entry_re = re.compile(
        r"(\w+):\s*\{\s*label:\s*'((?:[^'\\]|\\.)*)',\s*"
        r"detail:\s*((?:'(?:[^'\\]|\\.)*'\s*\+?\s*)+),\s*\},",
        re.S)
    ts_text = {}
    for state, label, detail_expr in entry_re.findall(block.group(1)):
        parts = re.findall(r"'((?:[^'\\]|\\.)*)'", detail_expr)
        ts_text[state] = (
            label.replace("\\'", "'"),
            "".join(parts).replace("\\'", "'"),
        )

    assert set(ts_text) == set(_REVIEW_STATE_TEXT), (
        f"state sets differ: ts={sorted(ts_text)} py={sorted(_REVIEW_STATE_TEXT)}")
    for state, (py_label, py_detail) in _REVIEW_STATE_TEXT.items():
        assert ts_text[state][0] == py_label, (
            f"{state} label drifted:\n  py: {py_label!r}\n  ts: {ts_text[state][0]!r}")
        assert ts_text[state][1] == py_detail, (
            f"{state} detail drifted:\n  py: {py_detail!r}\n  ts: {ts_text[state][1]!r}")


def test_review_state_non_reviewed_states_all_disclose_the_gap():
    """Every state that is not a human review says so in its own text.

    Without this, 'Scan only — no secondary structures found' could be
    softened into something that reads like a clean result, which is how the
    'medium' grade misled in the first place.
    """
    for state in ("scan_only_found", "scan_only_none_found",
                  "scan_inconclusive", "not_assessed"):
        detail = _REVIEW_STATE_TEXT[state][1].lower()
        assert ("not been checked" in detail
                or "never been measured" in detail
                or "unknown" in detail), f"{state}: {detail}"
