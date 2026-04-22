"""
Adversarial unit tests for services/threat_radar.py.

Pure-logic functions only — no DB, no network.

Covers:
  _haversine            — known distances
  _normalise_council    — key exhaustiveness + strip/case handling
  _filter_nearby        — null location, null coordinates, string "0", mixed apps
  SubscribeRequest.validate_email — edge cases
"""

import sys
import os
import pytest
import math

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.threat_radar import (
    _haversine,
    _normalise_council,
    _filter_nearby,
    _COUNCIL_NAME_MAP,
    ALERT_RADIUS_M,
)


# ---------------------------------------------------------------------------
# _haversine
# ---------------------------------------------------------------------------

def test_haversine_same_point_is_zero():
    assert _haversine(-33.87, 151.21, -33.87, 151.21) == pytest.approx(0.0, abs=1e-6)


def test_haversine_is_symmetric():
    a = _haversine(-33.87, 151.21, -28.8, 153.28)
    b = _haversine(-28.8, 153.28, -33.87, 151.21)
    assert a == pytest.approx(b, rel=1e-9)


def test_haversine_sydney_to_newcastle_approx():
    """Great-circle Sydney CBD → Newcastle ~117 km."""
    d = _haversine(-33.87, 151.21, -32.93, 151.78)
    assert 110_000 < d < 130_000


def test_haversine_sydney_to_wollongong_approx():
    """Great-circle Sydney CBD → Wollongong ~75 km."""
    d = _haversine(-33.87, 151.21, -34.42, 150.89)
    assert 65_000 < d < 85_000


def test_haversine_returns_metres():
    """Result is in metres, not km."""
    d = _haversine(-33.87, 151.21, -33.87, 151.22)  # ~1 degree lng ≈ ~98m at Sydney
    assert d == pytest.approx(98 * 10, abs=500)  # rough sanity, not exact


# ---------------------------------------------------------------------------
# _normalise_council
# ---------------------------------------------------------------------------

def test_normalise_council_exact_match():
    assert _normalise_council("inner west") == "Inner West Council"


def test_normalise_council_case_insensitive():
    assert _normalise_council("Inner West") == "Inner West Council"
    assert _normalise_council("INNER WEST") == "Inner West Council"


def test_normalise_council_strips_leading_trailing_spaces():
    assert _normalise_council("  inner west  ") == "Inner West Council"


def test_normalise_council_unknown_returns_stripped_input():
    """Unknown council name returns the stripped original — not a crash."""
    result = _normalise_council("  Some Unknown LGA  ")
    assert result == "Some Unknown LGA"


def test_normalise_council_sydney_ambiguity():
    """'sydney' alone maps correctly."""
    assert _normalise_council("sydney") == "Council of the City of Sydney"
    assert _normalise_council("Sydney") == "Council of the City of Sydney"


def test_normalise_council_former_council_gosford_maps_to_central_coast():
    assert _normalise_council("gosford") == "Central Coast Council"
    assert _normalise_council("wyong") == "Central Coast Council"


def test_normalise_council_map_has_no_duplicate_values_for_same_key():
    """All lowercase keys in _COUNCIL_NAME_MAP are unique."""
    keys = list(_COUNCIL_NAME_MAP.keys())
    assert len(keys) == len(set(keys))


# ---------------------------------------------------------------------------
# _filter_nearby
# ---------------------------------------------------------------------------

_SYDNEY_LAT = -33.87
_SYDNEY_LNG = 151.21


def _app(lat, lng, num="APP001", **extra) -> dict:
    """Build a minimal ePlanning Application dict."""
    return {
        "PlanningPortalApplicationNumber": num,
        "Latitude": str(lat),
        "Longitude": str(lng),
        "Location": [{"Y": str(lat), "X": str(lng)}],
        **extra,
    }


def test_filter_nearby_app_within_radius_is_included():
    # 5m away from subject — definitely inside 200m radius
    apps = [_app(_SYDNEY_LAT, _SYDNEY_LNG + 0.00005)]
    result = _filter_nearby(apps, _SYDNEY_LAT, _SYDNEY_LNG)
    assert len(result) == 1
    assert result[0]["_distance_m"] < ALERT_RADIUS_M


def test_filter_nearby_app_outside_radius_excluded():
    # 300m away (well beyond 200m)
    apps = [_app(_SYDNEY_LAT + 0.003, _SYDNEY_LNG)]  # ~333m north
    result = _filter_nearby(apps, _SYDNEY_LAT, _SYDNEY_LNG)
    assert result == []


def test_filter_nearby_zero_coordinates_skipped():
    """App with lat=0, lng=0 must be skipped — not a real location."""
    apps = [{"PlanningPortalApplicationNumber": "X", "Latitude": "0", "Longitude": "0",
             "Location": [{"Y": "0", "X": "0"}]}]
    result = _filter_nearby(apps, _SYDNEY_LAT, _SYDNEY_LNG)
    assert result == []


def test_filter_nearby_string_zero_coordinates_skipped():
    """Latitude="0" and Longitude="0" as strings must still be treated as missing."""
    apps = [{"PlanningPortalApplicationNumber": "X", "Latitude": "0", "Longitude": "0"}]
    result = _filter_nearby(apps, _SYDNEY_LAT, _SYDNEY_LNG)
    assert result == []


def test_filter_nearby_missing_lat_lng_falls_back_to_location():
    """No Latitude/Longitude key — should fall back to Location[0].X/Y."""
    app = {
        "PlanningPortalApplicationNumber": "Y",
        "Location": [{"Y": str(_SYDNEY_LAT), "X": str(_SYDNEY_LNG)}],
    }
    result = _filter_nearby([app], _SYDNEY_LAT, _SYDNEY_LNG)
    assert len(result) == 1


def test_filter_nearby_null_location_entry_does_not_crash():
    """Location=[None] — was raising AttributeError on None.get('Y').
    Fixed by broadening except to Exception."""
    app = {
        "PlanningPortalApplicationNumber": "Z",
        "Latitude": None,
        "Longitude": None,
        "Location": [None],
    }
    result = _filter_nearby([app], _SYDNEY_LAT, _SYDNEY_LNG)
    # Should not raise; app is skipped (lat/lng resolve to 0)
    assert result == []


def test_filter_nearby_missing_location_key_does_not_crash():
    """No Location key at all — app.get("Location") or [{}] gives {}."""
    app = {"PlanningPortalApplicationNumber": "W"}
    result = _filter_nearby([app], _SYDNEY_LAT, _SYDNEY_LNG)
    assert result == []


def test_filter_nearby_distance_appended_to_result():
    apps = [_app(_SYDNEY_LAT, _SYDNEY_LNG)]
    result = _filter_nearby(apps, _SYDNEY_LAT, _SYDNEY_LNG)
    assert "_distance_m" in result[0]
    assert result[0]["_distance_m"] == pytest.approx(0.0, abs=1.0)


def test_filter_nearby_mixed_apps_only_close_returned():
    apps = [
        _app(_SYDNEY_LAT, _SYDNEY_LNG, num="CLOSE"),          # 0m
        _app(_SYDNEY_LAT + 0.003, _SYDNEY_LNG, num="FAR"),    # ~333m
    ]
    result = _filter_nearby(apps, _SYDNEY_LAT, _SYDNEY_LNG)
    assert len(result) == 1
    assert result[0]["PlanningPortalApplicationNumber"] == "CLOSE"


# ---------------------------------------------------------------------------
# SubscribeRequest.validate_email
# ---------------------------------------------------------------------------

from services.threat_radar import SubscribeRequest


def _make_req(**kwargs) -> SubscribeRequest:
    defaults = {
        "address": "1 Test St", "lat": -33.87, "lng": 151.21,
        "email": "a@b.com", "council_name": "inner west",
    }
    defaults.update(kwargs)
    return SubscribeRequest(**defaults)


def test_validate_email_valid_passes():
    req = _make_req(email="user@example.com")
    req.validate_email()  # must not raise


def test_validate_email_no_at_raises():
    req = _make_req(email="notanemail.com")
    with pytest.raises(ValueError):
        req.validate_email()


def test_validate_email_no_dot_in_domain_raises():
    req = _make_req(email="user@nodot")
    with pytest.raises(ValueError):
        req.validate_email()


def test_validate_email_empty_raises():
    req = _make_req(email="@")
    with pytest.raises(ValueError):
        req.validate_email()
