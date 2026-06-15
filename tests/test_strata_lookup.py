"""
Tests for services/strata_lookup.py — Strata Classification Service.

Tests: dwelling classification, epoch parsing, spatial queries, edge cases.
"""
import datetime
import pytest
from unittest.mock import patch

from services.strata_lookup import (
    StrataInfo,
    classify_dwelling_type,
    safe_epoch_to_datetime,
    query_strata_at_point,
    query_strata_near,
    _parse_strata_feature,
)


# ---------------------------------------------------------------------------
# Dwelling type classification
# ---------------------------------------------------------------------------

class TestClassifyDwellingType:
    def test_duplex(self):
        assert classify_dwelling_type(1) == "duplex"
        assert classify_dwelling_type(2) == "duplex"

    def test_townhouse(self):
        assert classify_dwelling_type(3) == "townhouse"
        assert classify_dwelling_type(4) == "townhouse"

    def test_small_apartment(self):
        assert classify_dwelling_type(5) == "small_apartment"
        assert classify_dwelling_type(8) == "small_apartment"

    def test_apartment(self):
        assert classify_dwelling_type(9) == "apartment"
        assert classify_dwelling_type(100) == "apartment"
        assert classify_dwelling_type(474) == "apartment"

    def test_zero_lots(self):
        # Edge: 0 lots shouldn't crash
        assert classify_dwelling_type(0) == "duplex"

    def test_boundary_values(self):
        # Exact boundaries
        assert classify_dwelling_type(2) == "duplex"
        assert classify_dwelling_type(3) == "townhouse"
        assert classify_dwelling_type(4) == "townhouse"
        assert classify_dwelling_type(5) == "small_apartment"
        assert classify_dwelling_type(8) == "small_apartment"
        assert classify_dwelling_type(9) == "apartment"


# ---------------------------------------------------------------------------
# Epoch date parsing (Windows-safe)
# ---------------------------------------------------------------------------

class TestSafeEpochToDatetime:
    def test_positive_epoch(self):
        # 2024-06-14 21:20:00 UTC
        dt = safe_epoch_to_datetime(1718400000000)
        assert dt is not None
        assert dt.year == 2024

    def test_zero_epoch(self):
        dt = safe_epoch_to_datetime(0)
        assert dt is not None
        assert dt.year == 1970
        assert dt.month == 1
        assert dt.day == 1

    def test_negative_epoch_1969(self):
        # Pre-1970 — would crash with datetime.fromtimestamp on Windows
        dt = safe_epoch_to_datetime(-31536000000)
        assert dt is not None
        assert dt.year == 1969

    def test_negative_epoch_1940(self):
        dt = safe_epoch_to_datetime(-946684800000)
        assert dt is not None
        assert dt.year == 1940

    def test_negative_epoch_1900(self):
        dt = safe_epoch_to_datetime(-2208988800000)
        assert dt is not None
        assert dt.year == 1900

    def test_none_input(self):
        assert safe_epoch_to_datetime(None) is None

    def test_string_input(self):
        # Epoch can come as string from some JSON responses
        dt = safe_epoch_to_datetime("1718400000000")
        assert dt is not None
        assert dt.year == 2024

    def test_garbage_input(self):
        assert safe_epoch_to_datetime("not-a-number") is None


# ---------------------------------------------------------------------------
# Feature parsing
# ---------------------------------------------------------------------------

class TestParseStrataFeature:
    def test_full_feature(self):
        attrs = {
            "plannumber": 1468,
            "planlabel": "SP1468",
            "registrationdate": 1718400000000,
            "address": "10 TEST STREET",
            "suburb": "HABERFIELD",
            "lga": "INNER WEST",
            "lottotal": 6,
            "Shape__Area": 450.5,
        }
        info = _parse_strata_feature(attrs)
        assert info.plan_number == 1468
        assert info.plan_label == "SP1468"
        assert info.lot_total == 6
        assert info.dwelling_type == "small_apartment"
        assert info.area_m2 == 450.5
        assert info.registration_date is not None

    def test_pre_1970_feature(self):
        # SP8 registered 1961 — negative epoch
        attrs = {
            "plannumber": 8,
            "planlabel": "SP8",
            "registrationdate": -283996800000,  # ~1961
            "address": "OLD BUILDING",
            "suburb": "SYDNEY",
            "lga": "CITY OF SYDNEY",
            "lottotal": 27,
            "Shape__Area": 1200.0,
        }
        info = _parse_strata_feature(attrs)
        assert info.plan_number == 8
        assert info.dwelling_type == "apartment"
        assert info.registration_date is not None
        assert info.registration_date.startswith("196")

    def test_missing_fields(self):
        attrs = {}
        info = _parse_strata_feature(attrs)
        assert info.plan_number == 0
        assert info.plan_label == ""
        assert info.lot_total == 0
        assert info.dwelling_type == "duplex"  # 0 lots → duplex
        assert info.registration_date is None

    def test_null_registration_date(self):
        attrs = {
            "plannumber": 999,
            "planlabel": "SP999",
            "registrationdate": None,
            "address": "TEST",
            "suburb": "TEST",
            "lga": "TEST",
            "lottotal": 4,
            "Shape__Area": 300.0,
        }
        info = _parse_strata_feature(attrs)
        assert info.registration_date is None
        assert info.dwelling_type == "townhouse"


# ---------------------------------------------------------------------------
# query_strata_at_point (mocked)
# ---------------------------------------------------------------------------

class TestQueryStrataAtPoint:
    @patch("services.strata_lookup.arcgis_get_with_retry")
    def test_returns_strata_info(self, mock_get):
        mock_get.return_value = {
            "features": [{"attributes": {
                "plannumber": 5436,
                "planlabel": "SP5436",
                "registrationdate": 1000000000000,
                "address": "5 TEST ST",
                "suburb": "HABERFIELD",
                "lga": "INNER WEST",
                "lottotal": 6,
                "Shape__Area": 500.0,
            }}],
        }
        result = query_strata_at_point(lng=151.14, lat=-33.88)
        assert result is not None
        assert result.plan_label == "SP5436"
        assert result.dwelling_type == "small_apartment"

    @patch("services.strata_lookup.arcgis_get_with_retry")
    def test_not_strata(self, mock_get):
        mock_get.return_value = {"features": []}
        result = query_strata_at_point(lng=151.14, lat=-33.88)
        assert result is None

    @patch("services.strata_lookup.arcgis_get_with_retry")
    def test_multiple_overlapping_returns_smallest(self, mock_get):
        mock_get.return_value = {
            "features": [
                {"attributes": {
                    "plannumber": 100, "planlabel": "SP100",
                    "registrationdate": None, "address": "BIG",
                    "suburb": "TEST", "lga": "TEST",
                    "lottotal": 50, "Shape__Area": 5000.0,
                }},
                {"attributes": {
                    "plannumber": 200, "planlabel": "SP200",
                    "registrationdate": None, "address": "SMALL",
                    "suburb": "TEST", "lga": "TEST",
                    "lottotal": 4, "Shape__Area": 300.0,
                }},
            ],
        }
        result = query_strata_at_point(lng=151.14, lat=-33.88)
        assert result is not None
        assert result.plan_label == "SP200"  # Smallest area wins
        assert result.area_m2 == 300.0

    @patch("services.strata_lookup.arcgis_get_with_retry")
    def test_api_failure(self, mock_get):
        mock_get.return_value = {}
        result = query_strata_at_point(lng=151.14, lat=-33.88)
        assert result is None


# ---------------------------------------------------------------------------
# query_strata_near (mocked)
# ---------------------------------------------------------------------------

class TestQueryStrataNear:
    @patch("services.strata_lookup.arcgis_get_with_retry")
    def test_returns_list(self, mock_get):
        mock_get.return_value = {
            "features": [
                {"attributes": {
                    "plannumber": 1, "planlabel": "SP1",
                    "registrationdate": None, "address": "A",
                    "suburb": "T", "lga": "T",
                    "lottotal": 2, "Shape__Area": 100.0,
                }},
                {"attributes": {
                    "plannumber": 2, "planlabel": "SP2",
                    "registrationdate": None, "address": "B",
                    "suburb": "T", "lga": "T",
                    "lottotal": 20, "Shape__Area": 2000.0,
                }},
            ],
        }
        results = query_strata_near(lng=151.14, lat=-33.88, radius_m=200)
        assert len(results) == 2
        assert results[0].dwelling_type == "duplex"
        assert results[1].dwelling_type == "apartment"

    @patch("services.strata_lookup.arcgis_get_with_retry")
    def test_empty(self, mock_get):
        mock_get.return_value = {"features": []}
        results = query_strata_near(lng=151.14, lat=-33.88)
        assert results == []
