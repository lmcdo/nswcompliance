"""
Portal constraints shared module tests.

Tests the 7 new fetcher functions added to services/portal_constraints.py.
The 3 original fetchers (mine subsidence, contaminated land, drinking water)
are tested in test_intelligence_brief_orchestrator.py.
"""
import pytest
from unittest.mock import patch, MagicMock

from services.portal_constraints import (
    fetch_anef,
    fetch_bushfire_bfpl,
    fetch_coastal,
    fetch_sepp_exclusions,
    fetch_dual_occ_prohibition,
    query_arcgis_point,
)


# ---------------------------------------------------------------------------
# ANEF (Aircraft Noise Exposure Forecast)
# ---------------------------------------------------------------------------

class TestFetchAnef:
    @patch("services.portal_constraints.requests.get")
    def test_in_anef_zone_range(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": [{"attributes": {
                "ANEF_CODE": "20-25", "EPI_NAME": "Sydney Airport", "LGA_NAME": "Bayside",
            }}]},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        result = fetch_anef(-33.94, 151.17)
        assert result["in_anef_zone"] is True
        assert result["anef_level"] == 20
        assert result["anef_code"] == "20-25"

    @patch("services.portal_constraints.requests.get")
    def test_in_anef_zone_above_40(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": [{"attributes": {
                "ANEF_CODE": ">40", "EPI_NAME": "Sydney Airport", "LGA_NAME": "Bayside",
            }}]},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        result = fetch_anef(-33.94, 151.17)
        assert result["anef_level"] == 40

    @patch("services.portal_constraints.requests.get")
    def test_outside_anef(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": []},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        assert fetch_anef(-33.87, 151.21) is None

    @patch("services.portal_constraints.requests.get")
    def test_malformed_anef_code(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": [{"attributes": {
                "ANEF_CODE": "abc", "EPI_NAME": "Test", "LGA_NAME": "Test",
            }}]},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        result = fetch_anef(-33.94, 151.17)
        assert result["in_anef_zone"] is True
        assert result["anef_level"] is None


# ---------------------------------------------------------------------------
# Bushfire BFPL
# ---------------------------------------------------------------------------

class TestFetchBushfireBfpl:
    @patch("services.portal_constraints.requests.get")
    def test_in_bushfire_zone(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": [{"attributes": {
                "Category": "Vegetation Category 1", "TYPE": "Category 1",
            }}]},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        result = fetch_bushfire_bfpl(-33.70, 150.30)
        assert result["category"] == "Vegetation Category 1"

    @patch("services.portal_constraints.requests.get")
    def test_not_bushfire_prone(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": []},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        assert fetch_bushfire_bfpl(-33.87, 151.21) is None

    @patch("services.portal_constraints.requests.get")
    def test_type_fallback_when_no_category(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": [{"attributes": {"TYPE": "Vegetation Buffer"}}]},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        result = fetch_bushfire_bfpl(-33.70, 150.30)
        assert result["category"] == "Vegetation Buffer"


# ---------------------------------------------------------------------------
# Coastal
# ---------------------------------------------------------------------------

class TestFetchCoastal:
    @patch("services.portal_constraints.requests.get")
    def test_in_coastal_wetlands(self, mock_get):
        def side_effect(url, **kwargs):
            m = MagicMock()
            m.raise_for_status = MagicMock()
            if "/1/query" in url:
                m.json = lambda: {"features": [{"attributes": {"LAY_CLASS": "Coastal Wetlands"}}]}
            else:
                m.json = lambda: {"features": []}
            return m
        mock_get.side_effect = side_effect
        result = fetch_coastal(-33.85, 151.25)
        assert result["in_coastal_area"] is True
        assert "Coastal Wetlands" in result["zones"]

    @patch("services.portal_constraints.requests.get")
    def test_multiple_zones(self, mock_get):
        def side_effect(url, **kwargs):
            m = MagicMock()
            m.raise_for_status = MagicMock()
            # All 3 layers return features
            m.json = lambda: {"features": [{"attributes": {"LAY_CLASS": "test"}}]}
            return m
        mock_get.side_effect = side_effect
        result = fetch_coastal(-33.85, 151.25)
        assert len(result["zones"]) == 3

    @patch("services.portal_constraints.requests.get")
    def test_not_coastal(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": []},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        assert fetch_coastal(-33.87, 151.21) is None

    @patch("services.portal_constraints.requests.get")
    def test_partial_failure_still_returns(self, mock_get):
        """One layer fails, others succeed — returns partial result."""
        call_count = 0
        def side_effect(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("timeout")
            m = MagicMock()
            m.raise_for_status = MagicMock()
            m.json = lambda: {"features": [{"attributes": {}}]}
            return m
        mock_get.side_effect = side_effect
        result = fetch_coastal(-33.85, 151.25)
        assert result is not None
        assert len(result["zones"]) == 2


# ---------------------------------------------------------------------------
# SEPP Exclusions
# ---------------------------------------------------------------------------

class TestFetchSeppExclusions:
    @patch("services.portal_constraints.requests.get")
    def test_all_excluded(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": [{"attributes": {"LAY_CLASS": "test"}}]},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        result = fetch_sepp_exclusions(-33.87, 151.21)
        assert result["low_mid_rise"] is True
        assert result["complying"] is True
        assert result["exempt"] is True

    @patch("services.portal_constraints.requests.get")
    def test_none_excluded(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": []},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        result = fetch_sepp_exclusions(-33.87, 151.21)
        assert result["low_mid_rise"] is False
        assert result["complying"] is False
        assert result["exempt"] is False

    @patch("services.portal_constraints.requests.get")
    def test_all_failed_returns_none(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        result = fetch_sepp_exclusions(-33.87, 151.21)
        assert result is None


# ---------------------------------------------------------------------------
# Dual Occ Prohibition
# ---------------------------------------------------------------------------

class TestFetchDualOccProhibition:
    @patch("services.portal_constraints.requests.get")
    def test_prohibited(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": [{"attributes": {
                "LAY_CLASS": "test", "EPI_NAME": "Canterbury LEP", "LGA_NAME": "Canterbury-Bankstown",
            }}]},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        result = fetch_dual_occ_prohibition(-33.92, 151.10)
        assert result["prohibited"] is True
        assert result["epi_name"] == "Canterbury LEP"

    @patch("services.portal_constraints.requests.get")
    def test_not_prohibited(self, mock_get):
        mock_get.return_value = MagicMock(
            json=lambda: {"features": []},
        )
        mock_get.return_value.raise_for_status = MagicMock()
        result = fetch_dual_occ_prohibition(-33.87, 151.21)
        assert result["prohibited"] is False

    @patch("services.portal_constraints.requests.get")
    def test_query_failure_returns_none(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        result = fetch_dual_occ_prohibition(-33.87, 151.21)
        assert result is None
