"""
Tests for services/vg_comparables.py — VG Comparable Analysis Service.

Tests: string parsing, comparable filtering, percentile calculation, sales.
"""
import pytest
from unittest.mock import patch

from services.vg_comparables import (
    ComparableAnalysis,
    ComparableProperty,
    PropertySale,
    parse_land_value,
    parse_area,
    parse_sale_date,
    _haversine_m,
    _webmercator_to_wgs84,
    get_comparable_values,
    get_recent_sales,
)


# ---------------------------------------------------------------------------
# String parsing
# ---------------------------------------------------------------------------

class TestParseLandValue:
    def test_normal(self):
        assert parse_land_value(" $2,660,000") == 2660000

    def test_no_spaces(self):
        assert parse_land_value("$1,000,000") == 1000000

    def test_zero(self):
        assert parse_land_value("$0") == 0

    def test_plain_number(self):
        assert parse_land_value("500000") == 500000

    def test_none(self):
        assert parse_land_value(None) is None

    def test_empty(self):
        assert parse_land_value("") is None

    def test_whitespace_only(self):
        assert parse_land_value("   ") is None

    def test_int_passthrough(self):
        assert parse_land_value(2660000) == 2660000

    def test_float_passthrough(self):
        assert parse_land_value(2660000.0) == 2660000

    def test_garbage(self):
        assert parse_land_value("not a value") is None

    def test_zero_int(self):
        # int 0 is falsy — should return None (no value)
        assert parse_land_value(0) is None


class TestParseArea:
    def test_normal(self):
        assert parse_area("651.3 square metres") == pytest.approx(651.3)

    def test_integer(self):
        assert parse_area("500 square metres") == pytest.approx(500.0)

    def test_zero(self):
        assert parse_area("0 square metres") == pytest.approx(0.0)

    def test_none(self):
        assert parse_area(None) is None

    def test_empty(self):
        assert parse_area("") is None

    def test_numeric_passthrough(self):
        assert parse_area(651.3) == pytest.approx(651.3)

    def test_garbage(self):
        assert parse_area("unknown") is None


class TestParseSaleDate:
    def test_normal(self):
        assert parse_sale_date("20 September 2017") == "2017-09-20"

    def test_single_digit_day(self):
        assert parse_sale_date("5 January 2020") == "2020-01-05"

    def test_none(self):
        assert parse_sale_date(None) is None

    def test_empty(self):
        assert parse_sale_date("") is None

    def test_unrecognised(self):
        # Returns as-is
        assert parse_sale_date("2020-01-15") == "2020-01-15"


# ---------------------------------------------------------------------------
# Web Mercator conversion
# ---------------------------------------------------------------------------

class TestWebMercatorToWgs84:
    def test_sydney(self):
        # Approximate Sydney coords in Web Mercator
        lat, lng = _webmercator_to_wgs84(16824650.0, -4012631.0)
        assert -34.5 < lat < -33.0
        assert 150.5 < lng < 152.0

    def test_origin(self):
        lat, lng = _webmercator_to_wgs84(0, 0)
        assert lat == pytest.approx(0.0, abs=0.01)
        assert lng == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# get_comparable_values (mocked)
# ---------------------------------------------------------------------------

def _make_vg_feature(propid, address, zone, area_str, value_str, val_date):
    """Create a mock VG feature. No geometry → skips Haversine filter (bbox already handled)."""
    return {
        "attributes": {
            "OBJECTID": propid,
            "propid": propid,
            "address": address,
            "zone_desc": zone,
            "prop_area": area_str,
            "val1_lv": value_str,
            "val1_bd": val_date,
        },
        "geometry": {},  # Empty geometry → Haversine filter skipped
    }


class TestGetComparableValues:
    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_basic_comparables(self, mock_get):
        mock_get.return_value = {
            "features": [
                _make_vg_feature(1, "10 A St", "R2 - Low Density", "600 square metres", " $2,000,000", "1 July 2025"),
                _make_vg_feature(2, "12 A St", "R2 - Low Density", "650 square metres", " $2,200,000", "1 July 2025"),
                _make_vg_feature(3, "14 A St", "R2 - Low Density", "700 square metres", " $2,400,000", "1 July 2025"),
            ],
        }
        result = get_comparable_values(
            lng=151.15, lat=-33.88, zone="R2", lot_area_m2=650, radius_m=500,
        )
        assert result.comparable_count == 3
        assert result.median_value == 2200000
        assert result.mean_value == 2200000

    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_zone_filtering(self, mock_get):
        mock_get.return_value = {
            "features": [
                _make_vg_feature(1, "10 A St", "R2 - Low Density", "600 square metres", " $2,000,000", "2025"),
                _make_vg_feature(2, "12 B St", "E1 - Local Centre", "600 square metres", " $3,000,000", "2025"),
            ],
        }
        result = get_comparable_values(
            lng=151.15, lat=-33.88, zone="R2", lot_area_m2=600,
        )
        assert result.comparable_count == 1
        assert result.comparables[0].zone == "R2 - Low Density"

    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_area_tolerance_filtering(self, mock_get):
        mock_get.return_value = {
            "features": [
                _make_vg_feature(1, "Similar", "R2 - Low", "630 square metres", " $2,000,000", "2025"),
                _make_vg_feature(2, "Too big", "R2 - Low", "2000 square metres", " $5,000,000", "2025"),
                _make_vg_feature(3, "Too small", "R2 - Low", "100 square metres", " $500,000", "2025"),
            ],
        }
        result = get_comparable_values(
            lng=151.15, lat=-33.88, zone="R2", lot_area_m2=650, area_tolerance=0.3,
        )
        # 650 * 0.7 = 455, 650 * 1.3 = 845 → only "Similar" (630) passes
        assert result.comparable_count == 1

    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_excludes_subject(self, mock_get):
        mock_get.return_value = {
            "features": [
                _make_vg_feature(99, "Subject", "R2 - Low", "650 square metres", " $2,500,000", "2025"),
                _make_vg_feature(1, "Comp", "R2 - Low", "650 square metres", " $2,000,000", "2025"),
            ],
        }
        result = get_comparable_values(
            lng=151.15, lat=-33.88, zone="R2", lot_area_m2=650, subject_propid=99,
        )
        assert result.comparable_count == 1
        assert result.subject_value == 2500000
        assert result.comparables[0].propid == 1

    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_empty_response(self, mock_get):
        mock_get.return_value = {"features": []}
        result = get_comparable_values(
            lng=151.15, lat=-33.88, zone="R2", lot_area_m2=650,
        )
        assert result.comparable_count == 0
        assert result.comparables == []

    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_api_failure_raises_not_silent_zero(self, mock_get):
        # arcgis_get_with_retry returns {} on ANY failure. That must RAISE —
        # returning comparable_count=0 made a failed query indistinguishable
        # from "no comparable lots nearby" (the da_outcome silent-zero class).
        mock_get.return_value = {}
        import pytest
        with pytest.raises(RuntimeError, match="failed"):
            get_comparable_values(lng=151.15, lat=-33.88, zone="R2", lot_area_m2=650)

    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_null_values_skipped(self, mock_get):
        mock_get.return_value = {
            "features": [
                _make_vg_feature(1, "Good", "R2 - Low", "650 square metres", " $2,000,000", "2025"),
                {"attributes": {"OBJECTID": 2, "propid": 2, "address": "No val",
                                "zone_desc": "R2 - Low", "prop_area": "650 square metres",
                                "val1_lv": None, "val1_bd": None}, "geometry": {}},
            ],
        }
        result = get_comparable_values(
            lng=151.15, lat=-33.88, zone="R2", lot_area_m2=650,
        )
        assert result.comparable_count == 1

    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_assessment_signal_over(self, mock_get):
        # Subject at $5M, all comps at $2M → potentially_over
        mock_get.return_value = {
            "features": [
                _make_vg_feature(99, "Subject", "R2", "650 square metres", " $5,000,000", "2025"),
                _make_vg_feature(1, "C1", "R2", "650 square metres", " $2,000,000", "2025"),
                _make_vg_feature(2, "C2", "R2", "650 square metres", " $2,100,000", "2025"),
                _make_vg_feature(3, "C3", "R2", "650 square metres", " $2,200,000", "2025"),
                _make_vg_feature(4, "C4", "R2", "650 square metres", " $2,300,000", "2025"),
            ],
        }
        result = get_comparable_values(
            lng=151.15, lat=-33.88, zone="R2", lot_area_m2=650, subject_propid=99,
        )
        assert result.assessment_signal == "potentially_over"


# ---------------------------------------------------------------------------
# get_recent_sales (mocked)
# ---------------------------------------------------------------------------

class TestGetRecentSales:
    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_returns_sales(self, mock_get):
        mock_get.return_value = {
            "features": [
                {"attributes": {
                    "OBJECTID": 1, "propid": 100, "house_no": "38",
                    "street": "CONNECTICUT AVE", "suburb": "FIVE DOCK",
                    "postcode": 2046, "price": 1600000,
                    "sale_date": "20 September 2017", "area": 550.0, "strata": 0,
                }},
            ],
        }
        results = get_recent_sales(lng=151.13, lat=-33.87, years_back=10)
        assert len(results) == 1
        assert results[0].price == 1600000
        assert results[0].sale_date == "2017-09-20"
        assert results[0].is_strata is False
        assert results[0].price_per_m2 == pytest.approx(1600000 / 550.0, rel=0.01)

    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_excludes_strata(self, mock_get):
        mock_get.return_value = {
            "features": [
                {"attributes": {"OBJECTID": 1, "propid": 1, "house_no": "1",
                                "street": "A", "suburb": "B", "postcode": 2000,
                                "price": 1000000, "sale_date": "1 January 2025",
                                "area": 100, "strata": 1}},
                {"attributes": {"OBJECTID": 2, "propid": 2, "house_no": "2",
                                "street": "A", "suburb": "B", "postcode": 2000,
                                "price": 2000000, "sale_date": "1 January 2025",
                                "area": 500, "strata": 0}},
            ],
        }
        results = get_recent_sales(lng=151.0, lat=-33.8, exclude_strata=True)
        assert len(results) == 1
        assert results[0].propid == 2

    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_filters_old_sales(self, mock_get):
        mock_get.return_value = {
            "features": [
                {"attributes": {"OBJECTID": 1, "propid": 1, "house_no": "1",
                                "street": "A", "suburb": "B", "postcode": 2000,
                                "price": 500000, "sale_date": "1 January 2015",
                                "area": 300, "strata": 0}},
                {"attributes": {"OBJECTID": 2, "propid": 2, "house_no": "2",
                                "street": "A", "suburb": "B", "postcode": 2000,
                                "price": 1000000, "sale_date": "1 January 2025",
                                "area": 300, "strata": 0}},
            ],
        }
        results = get_recent_sales(lng=151.0, lat=-33.8, years_back=3)
        assert len(results) == 1
        assert results[0].sale_date == "2025-01-01"

    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_empty_response(self, mock_get):
        mock_get.return_value = {"features": []}
        assert get_recent_sales(lng=151.0, lat=-33.0) == []

    @patch("services.vg_comparables.arcgis_get_with_retry")
    def test_zero_price_skipped(self, mock_get):
        mock_get.return_value = {
            "features": [
                {"attributes": {"OBJECTID": 1, "propid": 1, "house_no": "1",
                                "street": "A", "suburb": "B", "postcode": 2000,
                                "price": 0, "sale_date": "1 January 2025",
                                "area": 300, "strata": 0}},
            ],
        }
        assert get_recent_sales(lng=151.0, lat=-33.8) == []
