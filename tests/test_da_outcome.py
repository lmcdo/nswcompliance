"""
Tests for services/da_outcome.py — DA Outcome Enrichment Service.

Tests: parsing, date normalisation, refusal stats, edge cases.
"""
import pytest
from unittest.mock import patch

from services.da_outcome import (
    DAOutcome,
    RefusalStats,
    _parse_date_str,
    _parse_feature,
    _safe_float,
    _safe_int,
    _haversine_m,
    query_da_outcomes_near,
    query_da_by_pan,
    get_refusal_rate,
)


# ---------------------------------------------------------------------------
# Date parsing
# ---------------------------------------------------------------------------

class TestParseDateStr:
    def test_14_char_format(self):
        assert _parse_date_str("20210730000000") == "2021-07-30"

    def test_8_char_format(self):
        assert _parse_date_str("20211215") == "2021-12-15"

    def test_none(self):
        assert _parse_date_str(None) is None

    def test_empty_string(self):
        assert _parse_date_str("") is None

    def test_whitespace(self):
        assert _parse_date_str("  20211215  ") == "2021-12-15"

    def test_unrecognised_format(self):
        # Passes through unrecognised formats as-is
        assert _parse_date_str("2021/12/15") == "2021/12/15"


# ---------------------------------------------------------------------------
# Safe type conversions
# ---------------------------------------------------------------------------

class TestSafeConversions:
    def test_safe_float_string(self):
        assert _safe_float("151.15066812") == pytest.approx(151.15066812)

    def test_safe_float_none(self):
        assert _safe_float(None) is None

    def test_safe_float_garbage(self):
        assert _safe_float("not-a-number") is None

    def test_safe_float_int(self):
        assert _safe_float(42) == 42.0

    def test_safe_int_string(self):
        assert _safe_int("5") == 5

    def test_safe_int_none(self):
        assert _safe_int(None) is None

    def test_safe_int_float_string(self):
        assert _safe_int("5.5") is None  # int("5.5") raises ValueError


# ---------------------------------------------------------------------------
# Feature parsing
# ---------------------------------------------------------------------------

class TestParseFeature:
    def test_full_feature(self):
        attrs = {
            "PLANNING_PORTAL_APP_NUMBER": "PAN-123456",
            "DA_NUMBER": "DA/2021/1234",
            "STATUS": "Determined",
            "ASSESMENT_RESULT": "Approved",
            "DETERMINING_AUTHORITY": "Council",
            "DEVELOPMENT_TYPE": "Alterations & Additions",
            "DWELLINGS_TO_BE_CONSTRUCTED": 1,
            "COST_OF_DEVELOPMENT": 250000,
            "PRIMARY_ADDRESS": "7 Church Street",
            "SUBURBNAME": "MARRICKVILLE",
            "X": "151.15066812",
            "Y": "-33.914799707",
            "LODGEMENT_DATE": "20210730000000",
            "DETERMINED_DATE": "20211215",
        }
        da = _parse_feature(attrs)
        assert da.planning_portal_number == "PAN-123456"
        assert da.outcome == "Approved"
        assert da.x == pytest.approx(151.15066812)
        assert da.y == pytest.approx(-33.914799707)
        assert da.lodgement_date == "2021-07-30"
        assert da.determined_date == "2021-12-15"
        assert da.dwellings_constructed == 1
        assert da.cost == "250000"

    def test_null_outcome(self):
        attrs = {
            "PLANNING_PORTAL_APP_NUMBER": "PAN-999",
            "STATUS": "Under Assessment",
            "ASSESMENT_RESULT": None,
            "PRIMARY_ADDRESS": "1 Test St",
            "SUBURBNAME": "TESTVILLE",
        }
        da = _parse_feature(attrs)
        assert da.outcome is None
        assert da.status == "Under Assessment"

    def test_missing_fields(self):
        attrs = {}
        da = _parse_feature(attrs)
        assert da.planning_portal_number == ""
        assert da.address == ""
        assert da.x is None
        assert da.y is None
        assert da.outcome is None


# ---------------------------------------------------------------------------
# Haversine
# ---------------------------------------------------------------------------

class TestHaversine:
    def test_same_point(self):
        assert _haversine_m(-33.88, 151.15, -33.88, 151.15) == 0.0

    def test_known_distance(self):
        # ~111km per degree of latitude
        dist = _haversine_m(-33.0, 151.0, -34.0, 151.0)
        assert 110_000 < dist < 112_000

    def test_short_distance(self):
        # ~100m should be small
        dist = _haversine_m(-33.88, 151.15, -33.8809, 151.15)
        assert 50 < dist < 200


# ---------------------------------------------------------------------------
# query_da_outcomes_near (mocked)
# ---------------------------------------------------------------------------

class TestQueryDAOutcomesNear:
    @patch("services.da_outcome.arcgis_get_with_retry")
    def test_returns_parsed_results(self, mock_get):
        mock_get.return_value = {
            "features": [
                {"attributes": {
                    "PLANNING_PORTAL_APP_NUMBER": "PAN-111",
                    "STATUS": "Determined",
                    "ASSESMENT_RESULT": "Approved",
                    "PRIMARY_ADDRESS": "10 Test St",
                    "SUBURBNAME": "TESTVILLE",
                    "X": "151.1550",
                    "Y": "-33.9110",
                    "LODGEMENT_DATE": "20220101000000",
                    "DETERMINED_DATE": "20220615",
                }},
                {"attributes": {
                    "PLANNING_PORTAL_APP_NUMBER": "PAN-222",
                    "STATUS": "Determined",
                    "ASSESMENT_RESULT": "Refused",
                    "PRIMARY_ADDRESS": "12 Test St",
                    "SUBURBNAME": "TESTVILLE",
                    "X": "151.1551",
                    "Y": "-33.9111",
                    "LODGEMENT_DATE": "20220201000000",
                    "DETERMINED_DATE": "20220701",
                }},
            ],
        }
        results = query_da_outcomes_near(lng=151.1553, lat=-33.9113)
        assert len(results) == 2
        assert results[0].outcome == "Approved"
        assert results[1].outcome == "Refused"
        assert results[0].lodgement_date == "2022-01-01"

    @patch("services.da_outcome.arcgis_get_with_retry")
    def test_empty_response(self, mock_get):
        mock_get.return_value = {"features": []}
        results = query_da_outcomes_near(lng=151.0, lat=-33.0)
        assert results == []

    @patch("services.da_outcome.arcgis_get_with_retry")
    def test_api_failure(self, mock_get):
        mock_get.return_value = {}  # Circuit breaker or timeout
        results = query_da_outcomes_near(lng=151.0, lat=-33.0)
        assert results == []

    @patch("services.da_outcome.arcgis_get_with_retry")
    def test_filters_by_haversine(self, mock_get):
        # One DA within radius, one far away
        mock_get.return_value = {
            "features": [
                {"attributes": {
                    "PLANNING_PORTAL_APP_NUMBER": "PAN-NEAR",
                    "STATUS": "Determined",
                    "PRIMARY_ADDRESS": "Near",
                    "SUBURBNAME": "TEST",
                    "X": "151.1553",  # Same as query point
                    "Y": "-33.9113",
                }},
                {"attributes": {
                    "PLANNING_PORTAL_APP_NUMBER": "PAN-FAR",
                    "STATUS": "Determined",
                    "PRIMARY_ADDRESS": "Far",
                    "SUBURBNAME": "TEST",
                    "X": "151.2000",  # ~4km away
                    "Y": "-33.9500",
                }},
            ],
        }
        results = query_da_outcomes_near(lng=151.1553, lat=-33.9113, radius_m=200)
        pans = [r.planning_portal_number for r in results]
        assert "PAN-NEAR" in pans
        assert "PAN-FAR" not in pans


# ---------------------------------------------------------------------------
# query_da_by_pan (mocked)
# ---------------------------------------------------------------------------

class TestQueryDAByPan:
    @patch("services.da_outcome.arcgis_get_with_retry")
    def test_found(self, mock_get):
        mock_get.return_value = {
            "features": [{"attributes": {
                "PLANNING_PORTAL_APP_NUMBER": "PAN-123",
                "STATUS": "Determined",
                "ASSESMENT_RESULT": "Refused",
                "PRIMARY_ADDRESS": "7 Church St",
                "SUBURBNAME": "MARRICKVILLE",
            }}],
        }
        result = query_da_by_pan("PAN-123")
        assert result is not None
        assert result.outcome == "Refused"

    @patch("services.da_outcome.arcgis_get_with_retry")
    def test_not_found(self, mock_get):
        mock_get.return_value = {"features": []}
        assert query_da_by_pan("PAN-NONEXISTENT") is None

    @patch("services.da_outcome.arcgis_get_with_retry")
    def test_api_failure(self, mock_get):
        mock_get.return_value = {}
        assert query_da_by_pan("PAN-123") is None


# ---------------------------------------------------------------------------
# get_refusal_rate (mocked)
# ---------------------------------------------------------------------------

class TestGetRefusalRate:
    @patch("services.da_outcome.arcgis_get_with_retry")
    def test_calculates_rate(self, mock_get):
        mock_get.return_value = {
            "features": [
                {"attributes": {"ASSESMENT_RESULT": "Approved", "count": 2491}},
                {"attributes": {"ASSESMENT_RESULT": "Refused", "count": 177}},
                {"attributes": {"ASSESMENT_RESULT": "Deferred Commencement Consent", "count": 75}},
            ],
        }
        stats = get_refusal_rate("Inner West")
        assert stats is not None
        assert stats.approved == 2491
        assert stats.refused == 177
        assert stats.deferred_commencement == 75
        assert stats.total_determined == 2491 + 177 + 75
        assert stats.refusal_rate == pytest.approx(177 / (2491 + 177 + 75), abs=0.001)

    @patch("services.da_outcome.arcgis_get_with_retry")
    def test_empty_results(self, mock_get):
        mock_get.return_value = {"features": []}
        assert get_refusal_rate("Nonexistent LGA") is None

    @patch("services.da_outcome.arcgis_get_with_retry")
    def test_all_approved(self, mock_get):
        mock_get.return_value = {
            "features": [
                {"attributes": {"ASSESMENT_RESULT": "Approved", "count": 100}},
            ],
        }
        stats = get_refusal_rate("Test LGA")
        assert stats is not None
        assert stats.refusal_rate == 0.0

    @patch("services.da_outcome.arcgis_get_with_retry")
    def test_api_failure(self, mock_get):
        mock_get.return_value = {}
        assert get_refusal_rate("Inner West") is None
