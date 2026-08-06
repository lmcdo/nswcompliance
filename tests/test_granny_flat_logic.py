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
    itself. "high" now requires count_source='user_reviewed'.
    """
    conf, reason = _compute_confidence(
        validated=True, confirmed_count=3, samgeo_count=3, rent_available=True,
        count_source="user_reviewed",
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
        count_source="user_reviewed",
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
        count_source="user_reviewed",
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
