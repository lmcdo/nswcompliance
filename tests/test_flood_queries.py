"""
Mutation-testing-grade tests for flood_truth.py data source query functions.

Scope: _query_epi_overlay, _query_copernicus_ems, _jrc_tile_url,
       _query_jrc_surface_water, _haversine_km, _parse_bom_observations,
       _fetch_bom_observations, _fetch_bom_peak, _ari_category,
       _fetch_bom_flood_history, _query_bom_gauge, _query_ses_flood_study,
       _query_compound_risk_layers, _query_dea_wofs, _sample_raster,
       _query_flood_study_rasters, _query_ground_elevation.

All external calls (requests.get, DB, rasterio) are monkeypatched.
"""

import sys
import os
import math
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.flood_truth as ft


@pytest.fixture(autouse=True)
def _ensure_rasterio_mock(monkeypatch):
    """Ensure rasterio exists in sys.modules for the duration of each test.

    We use monkeypatch.setitem so it's cleaned up after each test — this avoids
    polluting sys.modules and causing other test files' `pytest.importorskip`
    guards to incorrectly pass.
    """
    if "rasterio" not in sys.modules:
        monkeypatch.setitem(sys.modules, "rasterio", MagicMock())
    if "rasterio.transform" not in sys.modules:
        monkeypatch.setitem(sys.modules, "rasterio.transform", MagicMock())
    if "rasterio.windows" not in sys.modules:
        monkeypatch.setitem(sys.modules, "rasterio.windows", MagicMock())


def _make_array(data):
    """Create a lightweight 2D array that behaves like np.array for indexing.

    numpy is mocked in the test env (conftest_mocks), so np.array() returns
    a MagicMock. float(MagicMock()) == 1.0, which breaks value assertions.
    This class provides correct [row, col] indexing and float() conversion.
    """
    class _Arr:
        def __init__(self, d):
            self._d = d
        def __getitem__(self, idx):
            if isinstance(idx, tuple):
                r, c = idx
                return self._d[r][c]
            return self._d[idx]
    return _Arr(data)


# ═══════════════════════════════════════════════════════════════════════════
# _query_epi_overlay
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryEpiOverlay:
    """Tests for _query_epi_overlay (lines 276–365)."""

    def _mock_response(self, json_body, status_code=200):
        m = MagicMock()
        m.json.return_value = json_body
        m.raise_for_status = MagicMock()
        m.status_code = status_code
        return m

    def test_happy_path_flood_planning_area(self, monkeypatch):
        resp = self._mock_response({
            "features": [{"attributes": {
                "LAY_CLASS": "Flood Planning Area",
                "CURRENCY_DATE": 1609459200000,  # 2021-01-01 UTC
                "EPI_NAME": "Wollongong LEP 2009",
            }}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-34.42, 150.89)
        assert result["epi_flood_class"] == "flood_planning_area"
        assert result["epi_flood_label"] == "Flood Planning Area"
        assert result["data_currency"] == "2021-01-01"
        assert result["flood_study_name"] == "Wollongong LEP 2009"

    def test_no_features_returns_none_class(self, monkeypatch):
        resp = self._mock_response({"features": []})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] == "none"
        assert result["epi_flood_label"] == "No EPI Flood Overlay"
        assert result["data_currency"] == "unknown"
        assert result["flood_study_name"] is None
        assert result["flood_study_date"] is None

    def test_null_features_returns_none_class(self, monkeypatch):
        """features key present but null → same as empty."""
        resp = self._mock_response({"features": None})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] == "none"

    def test_arcgis_error_key_raises(self, monkeypatch):
        """ArcGIS error object → caught by except → query_failed."""
        resp = self._mock_response({"error": {"code": 400, "message": "Invalid layer"}})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] is None
        assert result["data_currency"] == "query_failed"

    def test_http_error_returns_none(self, monkeypatch):
        def raise_err(*a, **kw):
            raise Exception("timeout")
        monkeypatch.setattr("requests.get", raise_err)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] is None
        assert result["epi_flood_label"] is None
        assert result["data_currency"] == "query_failed"
        assert result["flood_study_name"] is None
        assert result["flood_study_date"] is None

    def test_high_flood_risk_mapping(self, monkeypatch):
        resp = self._mock_response({
            "features": [{"attributes": {"LAY_CLASS": "High Flood Risk"}}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] == "high_flood_risk"
        assert result["epi_flood_label"] == "High Flood Risk"

    def test_medium_flood_risk_mapping(self, monkeypatch):
        resp = self._mock_response({
            "features": [{"attributes": {"FLOODCLASS": "Medium Flood Risk"}}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] == "medium_flood_risk"

    def test_low_flood_risk_mapping(self, monkeypatch):
        resp = self._mock_response({
            "features": [{"attributes": {"FloodClass": "Low Flood Risk"}}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] == "low_flood_risk"

    def test_unrecognised_class_defaults_to_flood_planning_area(self, monkeypatch):
        """Unknown class value → flood_planning_area (not crash, not 'none')."""
        resp = self._mock_response({
            "features": [{"attributes": {"LAY_CLASS": "SomethingNew"}}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] == "flood_planning_area"

    def test_empty_class_string_returns_none(self, monkeypatch):
        """Empty string after strip → raw_class is falsy → 'none'."""
        resp = self._mock_response({
            "features": [{"attributes": {"LAY_CLASS": "  "}}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] == "none"

    def test_currency_date_epoch_conversion(self, monkeypatch):
        """Epoch ms → ISO date string."""
        epoch = 1672531200000  # 2023-01-01 UTC
        resp = self._mock_response({
            "features": [{"attributes": {
                "LAY_CLASS": "Flood Planning Area",
                "CURRENCY_DATE": epoch,
            }}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["data_currency"] == "2023-01-01"

    def test_currency_date_string_fallback(self, monkeypatch):
        """Non-epoch currency value → str() of the value."""
        resp = self._mock_response({
            "features": [{"attributes": {
                "LAY_CLASS": "Flood Planning Area",
                "CurrencyDate": "2023-Q1",
            }}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["data_currency"] == "2023-Q1"

    def test_currency_date_zero_is_unknown(self, monkeypatch):
        """CURRENCY_DATE=0 → not > 0 → falls to str fallback → '0' or 'unknown'."""
        resp = self._mock_response({
            "features": [{"attributes": {
                "LAY_CLASS": "Flood Planning Area",
                "CURRENCY_DATE": 0,
            }}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        # 0 is falsy in `or` chain, falls through to "unknown"
        assert result["data_currency"] == "unknown"

    def test_currency_date_missing_is_unknown(self, monkeypatch):
        """No currency field at all → unknown."""
        resp = self._mock_response({
            "features": [{"attributes": {"LAY_CLASS": "Flood Planning Area"}}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["data_currency"] == "unknown"

    def test_study_name_from_StudyName_field(self, monkeypatch):
        resp = self._mock_response({
            "features": [{"attributes": {
                "LAY_CLASS": "Flood Planning Area",
                "StudyName": "Hawkesbury FRMSP",
            }}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["flood_study_name"] == "Hawkesbury FRMSP"

    def test_study_name_skips_null_string(self, monkeypatch):
        """Field value 'null' (string) is skipped."""
        resp = self._mock_response({
            "features": [{"attributes": {
                "LAY_CLASS": "Flood Planning Area",
                "StudyName": "null",
                "FLOODSTUDY": "Real Study",
            }}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["flood_study_name"] == "Real Study"

    def test_study_date_extracted(self, monkeypatch):
        resp = self._mock_response({
            "features": [{"attributes": {
                "LAY_CLASS": "Flood Planning Area",
                "StudyDate": "2024-06-15",
            }}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["flood_study_date"] == "2024-06-15"

    def test_study_date_skips_unknown(self, monkeypatch):
        """Study date 'unknown' is skipped."""
        resp = self._mock_response({
            "features": [{"attributes": {
                "LAY_CLASS": "Flood Planning Area",
                "StudyDate": "unknown",
                "EFFECTIVEDATE": "2023-01-01",
            }}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["flood_study_date"] == "2023-01-01"

    def test_null_attributes_returns_defaults(self, monkeypatch):
        """Feature with null attributes → empty attrs."""
        resp = self._mock_response({
            "features": [{"attributes": None}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] == "none"

    def test_category_field_used_as_fallback(self, monkeypatch):
        """Category field in attributes → used when LAY_CLASS missing."""
        resp = self._mock_response({
            "features": [{"attributes": {"Category": "High Flood Risk"}}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] == "high_flood_risk"

    def test_case_insensitive_class_mapping(self, monkeypatch):
        """FloodClass values are lowercased before lookup."""
        resp = self._mock_response({
            "features": [{"attributes": {"LAY_CLASS": "HIGH FLOOD RISK"}}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["epi_flood_class"] == "high_flood_risk"

    def test_params_contain_correct_geometry(self, monkeypatch):
        """Verify lng,lat order in params (not lat,lng)."""
        captured = {}
        def capture_get(*a, **kw):
            captured["params"] = kw.get("params")
            return self._mock_response({"features": []})
        monkeypatch.setattr("requests.get", capture_get)
        ft._query_epi_overlay(-33.87, 151.21)
        assert captured["params"]["geometry"] == "151.21,-33.87"

    def test_raise_for_status_called(self, monkeypatch):
        resp = self._mock_response({"features": []})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        ft._query_epi_overlay(-33.87, 151.21)
        resp.raise_for_status.assert_called_once()

    def test_negative_currency_date_treated_as_string(self, monkeypatch):
        """Negative epoch → not > 0 → str fallback."""
        resp = self._mock_response({
            "features": [{"attributes": {
                "LAY_CLASS": "Flood Planning Area",
                "CURRENCY_DATE": -1,
            }}]
        })
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_epi_overlay(-33.87, 151.21)
        assert result["data_currency"] == "-1"


# ═══════════════════════════════════════════════════════════════════════════
# _query_copernicus_ems
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryCopernicusEms:
    """Tests for _query_copernicus_ems (lines 372–413)."""

    def _make_conn(self, count_result, query_rows=None):
        mock_cur = MagicMock()
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        # fetchone returns count, then fetchall returns rows
        mock_cur.fetchone.return_value = {"n": count_result}
        mock_cur.fetchall.return_value = query_rows or []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        return mock_conn

    def test_table_empty_returns_none(self, monkeypatch):
        conn = self._make_conn(count_result=0)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_copernicus_ems(-33.87, 151.21)
        assert result["ems_flood_detected"] is None
        assert result["ems_activations"] is None

    def test_no_matching_rows_returns_false(self, monkeypatch):
        conn = self._make_conn(count_result=5, query_rows=[])
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_copernicus_ems(-33.87, 151.21)
        assert result["ems_flood_detected"] is False
        assert result["ems_activations"] == []

    def test_matching_rows_returns_activations(self, monkeypatch):
        mock_date = MagicMock()
        mock_date.isoformat.return_value = "2022-02-28"
        rows = [{
            "activation_id": "EMSR123",
            "event_name": "NSW Floods",
            "event_date_start": mock_date,
            "flood_type": "Riverine",
        }]
        conn = self._make_conn(count_result=1, query_rows=rows)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_copernicus_ems(-28.8, 153.3)
        assert result["ems_flood_detected"] is True
        assert len(result["ems_activations"]) == 1
        assert result["ems_activations"][0]["activation_id"] == "EMSR123"
        assert result["ems_activations"][0]["event_date"] == "2022-02-28"
        assert result["ems_activations"][0]["flood_type"] == "Riverine"

    def test_db_error_returns_none(self, monkeypatch):
        monkeypatch.setattr(ft, "_get_conn", lambda: (_ for _ in ()).throw(Exception("db down")))
        result = ft._query_copernicus_ems(-33.87, 151.21)
        assert result["ems_flood_detected"] is None
        assert result["ems_activations"] is None

    def test_conn_closed_on_success(self, monkeypatch):
        conn = self._make_conn(count_result=0)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        ft._query_copernicus_ems(-33.87, 151.21)
        conn.close.assert_called_once()

    def test_conn_closed_on_error(self, monkeypatch):
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("cursor fail")
        monkeypatch.setattr(ft, "_get_conn", lambda: mock_conn)
        ft._query_copernicus_ems(-33.87, 151.21)
        mock_conn.close.assert_called_once()

    def test_multiple_activations(self, monkeypatch):
        d1 = MagicMock(); d1.isoformat.return_value = "2022-02-28"
        d2 = MagicMock(); d2.isoformat.return_value = "2021-03-20"
        rows = [
            {"activation_id": "E1", "event_name": "Flood A", "event_date_start": d1, "flood_type": "Riverine"},
            {"activation_id": "E2", "event_name": "Flood B", "event_date_start": d2, "flood_type": "Flash"},
        ]
        conn = self._make_conn(count_result=2, query_rows=rows)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_copernicus_ems(-33.87, 151.21)
        assert result["ems_flood_detected"] is True
        assert len(result["ems_activations"]) == 2


# ═══════════════════════════════════════════════════════════════════════════
# _jrc_tile_url
# ═══════════════════════════════════════════════════════════════════════════

class TestJrcTileUrl:
    """Tests for _jrc_tile_url (lines 419–433)."""

    def test_sydney(self):
        url = ft._jrc_tile_url(-33.87, 151.21)
        assert "150E" in url
        assert "30S" in url
        assert url.endswith("v1_4_2021.tif")

    def test_northern_hemisphere(self):
        url = ft._jrc_tile_url(51.5, -0.1)
        assert "10W" in url
        assert "60N" in url

    def test_equator(self):
        url = ft._jrc_tile_url(0.0, 0.0)
        assert "0E" in url
        assert "0N" in url

    def test_southern_equator(self):
        """Lat just below 0 → ceil(lat/10)*10 = 0 → lat_base=0 → 'N' (not S)."""
        url = ft._jrc_tile_url(-0.1, 0.0)
        assert "0N" in url

    def test_negative_longitude(self):
        url = ft._jrc_tile_url(40.0, -75.0)
        assert "80W" in url

    def test_url_has_occurrence_prefix(self):
        url = ft._jrc_tile_url(-33.87, 151.21)
        assert "/occurrence_" in url

    def test_base_url_used(self):
        url = ft._jrc_tile_url(-33.87, 151.21)
        assert url.startswith(ft.JRC_TILE_BASE)

    def test_exact_boundary_lat(self):
        """lat=-30.0 → ceil(-30/10)*10 = -30 → 30S."""
        url = ft._jrc_tile_url(-30.0, 150.0)
        assert "30S" in url

    def test_exact_boundary_lng(self):
        """lng=150.0 → floor(150/10)*10 = 150 → 150E."""
        url = ft._jrc_tile_url(-33.0, 150.0)
        assert "150E" in url


# ═══════════════════════════════════════════════════════════════════════════
# _haversine_km
# ═══════════════════════════════════════════════════════════════════════════

class TestHaversineKm:
    """Tests for _haversine_km (lines 486–491)."""

    def test_same_point_is_zero(self):
        assert ft._haversine_km(-33.87, 151.21, -33.87, 151.21) == 0.0

    def test_sydney_to_melbourne(self):
        d = ft._haversine_km(-33.87, 151.21, -37.81, 144.96)
        assert 700 < d < 900  # ~714 km

    def test_sydney_to_brisbane(self):
        d = ft._haversine_km(-33.87, 151.21, -27.47, 153.03)
        assert 600 < d < 800  # ~732 km

    def test_symmetry(self):
        d1 = ft._haversine_km(-33.87, 151.21, -28.81, 153.28)
        d2 = ft._haversine_km(-28.81, 153.28, -33.87, 151.21)
        assert abs(d1 - d2) < 1e-10

    def test_equator_short_distance(self):
        d = ft._haversine_km(0.0, 0.0, 0.0, 1.0)
        assert 110 < d < 112  # ~111.2 km

    def test_returns_float(self):
        result = ft._haversine_km(-33.0, 151.0, -34.0, 151.0)
        assert isinstance(result, float)

    def test_uses_correct_radius(self):
        """Earth radius ≈ 6371 km used in calculation."""
        # 90 degrees along a great circle = pi/2 * R ≈ 10007.5 km
        d = ft._haversine_km(0.0, 0.0, 90.0, 0.0)
        assert 10000 < d < 10020


# ═══════════════════════════════════════════════════════════════════════════
# _parse_bom_observations
# ═══════════════════════════════════════════════════════════════════════════

class TestParseBomObservations:
    """Tests for _parse_bom_observations (lines 494–511)."""

    def test_parses_valid_xml_pairs(self):
        xml = """
        <om:time>2022-02-28T00:00:00+00:00</om:time>
        <om:value>5.4</om:value>
        <om:time>2022-03-01T00:00:00+00:00</om:time>
        <om:value>6.1</om:value>
        """
        result = ft._parse_bom_observations(xml)
        assert len(result) == 2
        assert result[0][1] == 5.4
        assert result[1][1] == 6.1

    def test_sorted_by_time(self):
        xml = """
        <time>2022-03-01T00:00:00+00:00</time>
        <value>6.1</value>
        <time>2022-02-28T00:00:00+00:00</time>
        <value>5.4</value>
        """
        result = ft._parse_bom_observations(xml)
        assert result[0][0] < result[1][0]

    def test_empty_xml_returns_empty(self):
        result = ft._parse_bom_observations("")
        assert result == []

    def test_non_numeric_value_skipped(self):
        xml = """
        <time>2022-02-28T00:00:00+00:00</time>
        <value>NaN_text</value>
        <time>2022-03-01T00:00:00+00:00</time>
        <value>5.4</value>
        """
        result = ft._parse_bom_observations(xml)
        assert len(result) == 1
        assert result[0][1] == 5.4

    def test_z_suffix_handled(self):
        xml = """
        <time>2022-02-28T12:00:00Z</time>
        <value>3.2</value>
        """
        result = ft._parse_bom_observations(xml)
        assert len(result) == 1
        assert result[0][0].tzinfo is not None

    def test_returns_datetime_float_tuples(self):
        xml = """
        <time>2022-02-28T00:00:00+00:00</time>
        <value>5.4</value>
        """
        result = ft._parse_bom_observations(xml)
        assert isinstance(result[0][0], datetime)
        assert isinstance(result[0][1], float)

    def test_namespaced_tags(self):
        """Tags with XML namespaces should match."""
        xml = """
        <wml2:time>2022-02-28T00:00:00+00:00</wml2:time>
        <wml2:value>7.5</wml2:value>
        """
        result = ft._parse_bom_observations(xml)
        assert len(result) == 1


# ═══════════════════════════════════════════════════════════════════════════
# _fetch_bom_observations
# ═══════════════════════════════════════════════════════════════════════════

class TestFetchBomObservations:
    """Tests for _fetch_bom_observations (lines 514–527)."""

    def test_returns_response_text(self, monkeypatch):
        resp = MagicMock()
        resp.text = "<xml>data</xml>"
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._fetch_bom_observations("201001", "2021-01-01T00:00:00+10:00")
        assert result == "<xml>data</xml>"

    def test_correct_params_sent(self, monkeypatch):
        captured = {}
        resp = MagicMock()
        resp.text = ""
        resp.raise_for_status = MagicMock()
        def capture(*a, **kw):
            captured.update(kw)
            return resp
        monkeypatch.setattr("requests.get", capture)
        ft._fetch_bom_observations("201001", "2021-01-01T00:00:00+10:00")
        params = captured["params"]
        assert params["service"] == "SOS"
        assert params["version"] == "2.0.0"
        assert "201001" in params["featureOfInterest"]
        assert captured.get("timeout") == 15

    def test_raise_for_status_called(self, monkeypatch):
        resp = MagicMock()
        resp.text = ""
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        ft._fetch_bom_observations("201001", "2021-01-01T00:00:00+10:00")
        resp.raise_for_status.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# _fetch_bom_peak
# ═══════════════════════════════════════════════════════════════════════════

class TestFetchBomPeak:
    """Tests for _fetch_bom_peak (lines 530–555)."""

    def test_peak_above_threshold_returned(self, monkeypatch):
        xml = """
        <time>2022-02-28T00:00:00+00:00</time>
        <value>8.5</value>
        <time>2022-03-01T00:00:00+00:00</time>
        <value>12.3</value>
        <time>2022-03-02T00:00:00+00:00</time>
        <value>9.0</value>
        """
        resp = MagicMock()
        resp.text = xml
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        date_str, peak = ft._fetch_bom_peak("201001", 10.0)
        assert date_str == "2022-03-01"
        assert peak == 12.3

    def test_peak_below_threshold_returns_none(self, monkeypatch):
        xml = """
        <time>2022-02-28T00:00:00+00:00</time>
        <value>4.0</value>
        """
        resp = MagicMock()
        resp.text = xml
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        date_str, peak = ft._fetch_bom_peak("201001", 10.0)
        assert date_str is None
        assert peak is None

    def test_empty_observations_returns_none(self, monkeypatch):
        resp = MagicMock()
        resp.text = "<empty/>"
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        date_str, peak = ft._fetch_bom_peak("201001", 5.0)
        assert date_str is None
        assert peak is None

    def test_exception_returns_none(self, monkeypatch):
        monkeypatch.setattr("requests.get", lambda *a, **kw: (_ for _ in ()).throw(Exception("err")))
        date_str, peak = ft._fetch_bom_peak("201001", 5.0)
        assert date_str is None
        assert peak is None

    def test_peak_rounded_to_2dp(self, monkeypatch):
        xml = """
        <time>2022-02-28T00:00:00+00:00</time>
        <value>12.3456</value>
        """
        resp = MagicMock()
        resp.text = xml
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        _, peak = ft._fetch_bom_peak("201001", 10.0)
        assert peak == 12.35


# ═══════════════════════════════════════════════════════════════════════════
# _ari_category
# ═══════════════════════════════════════════════════════════════════════════

class TestAriCategory:
    """Tests for _ari_category (lines 558–567)."""

    def test_ratio_above_1_5_is_100yr(self):
        assert ft._ari_category(15.0, 10.0) == "1-in-100 year (est.)"

    def test_ratio_exactly_1_5_is_100yr(self):
        assert ft._ari_category(15.0, 10.0) == "1-in-100 year (est.)"

    def test_ratio_1_2_to_1_5_is_50yr(self):
        assert ft._ari_category(13.0, 10.0) == "1-in-50 year (est.)"

    def test_ratio_exactly_1_2_is_50yr(self):
        assert ft._ari_category(12.0, 10.0) == "1-in-50 year (est.)"

    def test_ratio_below_1_2_is_20yr(self):
        assert ft._ari_category(11.0, 10.0) == "1-in-20 year (est.)"

    def test_ratio_exactly_1_0_is_20yr(self):
        assert ft._ari_category(10.0, 10.0) == "1-in-20 year (est.)"

    def test_zero_major_flood_returns_major(self):
        assert ft._ari_category(5.0, 0.0) == "major flood"

    def test_negative_major_flood_returns_major(self):
        assert ft._ari_category(5.0, -1.0) == "major flood"

    def test_ratio_just_below_1_5(self):
        """1.499... ratio → 50yr, not 100yr."""
        assert ft._ari_category(14.99, 10.0) == "1-in-50 year (est.)"

    def test_ratio_just_below_1_2(self):
        """1.199... ratio → 20yr, not 50yr."""
        assert ft._ari_category(11.99, 10.0) == "1-in-20 year (est.)"


# ═══════════════════════════════════════════════════════════════════════════
# _fetch_bom_flood_history
# ═══════════════════════════════════════════════════════════════════════════

class TestFetchBomFloodHistory:
    """Tests for _fetch_bom_flood_history (lines 570–626)."""

    def _make_obs_xml(self, readings):
        """Build XML with time/value pairs. readings: [(iso_str, float), ...]"""
        parts = []
        for t, v in readings:
            parts.append(f"<time>{t}</time>\n<value>{v}</value>")
        return "\n".join(parts)

    def test_single_flood_event(self, monkeypatch):
        xml = self._make_obs_xml([
            ("2022-02-28T00:00:00+00:00", 12.0),
            ("2022-02-28T01:00:00+00:00", 14.0),
            ("2022-02-28T02:00:00+00:00", 11.0),
            ("2022-02-28T03:00:00+00:00", 4.0),  # below threshold
        ])
        resp = MagicMock()
        resp.text = xml
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._fetch_bom_flood_history("201001", 10.0, max_events=3)
        assert len(result) == 1
        assert result[0]["peak_m"] == 14.0

    def test_two_separate_events(self, monkeypatch):
        xml = self._make_obs_xml([
            ("2022-02-01T00:00:00+00:00", 12.0),
            ("2022-02-01T01:00:00+00:00", 5.0),   # drops below
            ("2022-03-01T00:00:00+00:00", 15.0),
            ("2022-03-01T01:00:00+00:00", 5.0),   # drops below
        ])
        resp = MagicMock()
        resp.text = xml
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._fetch_bom_flood_history("201001", 10.0, max_events=3)
        assert len(result) == 2

    def test_max_events_cap(self, monkeypatch):
        readings = []
        for i in range(5):
            readings.append((f"2022-0{i+1}-01T00:00:00+00:00", 15.0))
            readings.append((f"2022-0{i+1}-02T00:00:00+00:00", 3.0))
        xml = self._make_obs_xml(readings)
        resp = MagicMock()
        resp.text = xml
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._fetch_bom_flood_history("201001", 10.0, max_events=2)
        assert len(result) == 2

    def test_no_events_above_threshold(self, monkeypatch):
        xml = self._make_obs_xml([
            ("2022-02-01T00:00:00+00:00", 5.0),
            ("2022-03-01T00:00:00+00:00", 3.0),
        ])
        resp = MagicMock()
        resp.text = xml
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._fetch_bom_flood_history("201001", 10.0)
        assert result == []

    def test_empty_observations(self, monkeypatch):
        resp = MagicMock()
        resp.text = "<empty/>"
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._fetch_bom_flood_history("201001", 10.0)
        assert result == []

    def test_exception_returns_empty_list(self, monkeypatch):
        monkeypatch.setattr("requests.get", lambda *a, **kw: (_ for _ in ()).throw(Exception("err")))
        result = ft._fetch_bom_flood_history("201001", 10.0)
        assert result == []

    def test_trailing_open_event_closed(self, monkeypatch):
        """Event still above threshold at end of data → still captured."""
        xml = self._make_obs_xml([
            ("2022-02-28T00:00:00+00:00", 12.0),
            ("2022-02-28T01:00:00+00:00", 14.0),
            # no drop below threshold
        ])
        resp = MagicMock()
        resp.text = xml
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._fetch_bom_flood_history("201001", 10.0)
        assert len(result) == 1
        assert result[0]["peak_m"] == 14.0

    def test_newest_first_ordering(self, monkeypatch):
        xml = self._make_obs_xml([
            ("2020-02-01T00:00:00+00:00", 12.0),
            ("2020-02-02T00:00:00+00:00", 3.0),
            ("2023-06-01T00:00:00+00:00", 15.0),
            ("2023-06-02T00:00:00+00:00", 3.0),
        ])
        resp = MagicMock()
        resp.text = xml
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._fetch_bom_flood_history("201001", 10.0)
        assert result[0]["date"] > result[1]["date"]

    def test_ari_category_in_result(self, monkeypatch):
        xml = self._make_obs_xml([
            ("2022-02-28T00:00:00+00:00", 16.0),
            ("2022-03-01T00:00:00+00:00", 3.0),
        ])
        resp = MagicMock()
        resp.text = xml
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._fetch_bom_flood_history("201001", 10.0)
        assert "ari_category" in result[0]
        assert "year" in result[0]["ari_category"]

    def test_peak_m_rounded(self, monkeypatch):
        xml = self._make_obs_xml([
            ("2022-02-28T00:00:00+00:00", 12.3456),
            ("2022-03-01T00:00:00+00:00", 3.0),
        ])
        resp = MagicMock()
        resp.text = xml
        resp.raise_for_status = MagicMock()
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._fetch_bom_flood_history("201001", 10.0)
        assert result[0]["peak_m"] == 12.35


# ═══════════════════════════════════════════════════════════════════════════
# _query_bom_gauge
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryBomGauge:
    """Tests for _query_bom_gauge (lines 629–664)."""

    def test_near_lismore_finds_gauge(self, monkeypatch):
        """Point near Lismore should find Wilsons River gauge."""
        # Mock _fetch_bom_peak and _fetch_bom_flood_history
        monkeypatch.setattr(ft, "_fetch_bom_peak", lambda sid, ml: ("2022-02-28", 12.5))
        monkeypatch.setattr(ft, "_fetch_bom_flood_history", lambda sid, ml, max_events=3: [])
        result = ft._query_bom_gauge(-28.81, 153.28)
        assert result["bom_gauge_name"] == "Wilsons River at Lismore"
        assert result["bom_gauge_distance_km"] is not None
        assert result["bom_gauge_distance_km"] < 75.0

    def test_far_away_returns_null(self, monkeypatch):
        """Point far from any gauge → null result."""
        monkeypatch.setattr(ft, "_fetch_bom_peak", lambda sid, ml: (None, None))
        monkeypatch.setattr(ft, "_fetch_bom_flood_history", lambda sid, ml, max_events=3: [])
        result = ft._query_bom_gauge(-10.0, 130.0)  # Darwin area, no NSW gauges nearby
        assert result["bom_gauge_name"] is None
        assert result["bom_gauge_distance_km"] is None
        assert result["bom_last_major_flood_date"] is None

    def test_returns_peak_data(self, monkeypatch):
        monkeypatch.setattr(ft, "_fetch_bom_peak", lambda sid, ml: ("2022-02-28", 12.5))
        monkeypatch.setattr(ft, "_fetch_bom_flood_history", lambda sid, ml, max_events=3: [
            {"date": "2022-02-28", "peak_m": 12.5, "ari_category": "1-in-100 year (est.)"}
        ])
        result = ft._query_bom_gauge(-28.81, 153.28)
        assert result["bom_last_major_flood_date"] == "2022-02-28"
        assert result["bom_last_major_flood_peak_m"] == 12.5
        assert len(result["bom_flood_history"]) == 1

    def test_distance_rounded_to_1dp(self, monkeypatch):
        monkeypatch.setattr(ft, "_fetch_bom_peak", lambda sid, ml: (None, None))
        monkeypatch.setattr(ft, "_fetch_bom_flood_history", lambda sid, ml, max_events=3: [])
        result = ft._query_bom_gauge(-28.81, 153.28)
        if result["bom_gauge_distance_km"] is not None:
            # Should be rounded to 1 decimal
            assert result["bom_gauge_distance_km"] == round(result["bom_gauge_distance_km"], 1)

    def test_exception_returns_null_result(self, monkeypatch):
        monkeypatch.setattr(ft, "_fetch_bom_peak", lambda sid, ml: (_ for _ in ()).throw(Exception("boom")))
        result = ft._query_bom_gauge(-28.81, 153.28)
        assert result["bom_gauge_name"] is None
        assert result["bom_flood_history"] == []

    def test_null_result_keys(self, monkeypatch):
        """Null result has all expected keys."""
        monkeypatch.setattr(ft, "_fetch_bom_peak", lambda sid, ml: (None, None))
        monkeypatch.setattr(ft, "_fetch_bom_flood_history", lambda sid, ml, max_events=3: [])
        result = ft._query_bom_gauge(-10.0, 130.0)
        assert "bom_gauge_name" in result
        assert "bom_gauge_distance_km" in result
        assert "bom_last_major_flood_date" in result
        assert "bom_last_major_flood_peak_m" in result
        assert "bom_flood_history" in result


# ═══════════════════════════════════════════════════════════════════════════
# _query_ses_flood_study
# ═══════════════════════════════════════════════════════════════════════════

class TestQuerySesFloodStudy:
    """Tests for _query_ses_flood_study (lines 715–787)."""

    def _make_conn(self, count, rows=None):
        mock_cur = MagicMock()
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_cur.fetchone.return_value = {"n": count}
        mock_cur.fetchall.return_value = rows or []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        return mock_conn

    def test_no_flood_rows_returns_null(self, monkeypatch):
        conn = self._make_conn(count=0)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_ses_flood_study(-33.87, 151.21)
        assert result["ses_in_flood_planning_area"] is None
        assert result["ses_flood_class"] is None

    def test_no_intersecting_rows_returns_false(self, monkeypatch):
        conn = self._make_conn(count=5, rows=[])
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_ses_flood_study(-33.87, 151.21)
        assert result["ses_in_flood_planning_area"] is False
        assert result["ses_flood_class"] is None
        assert result["ses_aep_tiers"] == []

    def test_single_match_returns_true(self, monkeypatch):
        rows = [{"value": "flood_planning_area", "instrument_key": "LEP2009", "lga_name": "Wollongong"}]
        conn = self._make_conn(count=1, rows=rows)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_ses_flood_study(-34.42, 150.89)
        assert result["ses_in_flood_planning_area"] is True
        assert result["ses_flood_class"] == "Flood Planning Area"
        assert result["ses_study_name"] == "LEP2009"
        assert result["ses_study_lga"] == "Wollongong"

    def test_multiple_aep_tiers_sorted(self, monkeypatch):
        rows = [
            {"value": "PMF", "instrument_key": "Study1", "lga_name": "LGA1"},
            {"value": "1%AEP", "instrument_key": "Study1", "lga_name": "LGA1"},
            {"value": "flood_planning_area", "instrument_key": "Study1", "lga_name": "LGA1"},
        ]
        conn = self._make_conn(count=3, rows=rows)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_ses_flood_study(-33.87, 151.21)
        assert result["ses_in_flood_planning_area"] is True
        # Primary should be the most frequent tier (1% AEP)
        assert "1% AEP" in result["ses_flood_class"]
        # All tiers present
        assert len(result["ses_aep_tiers"]) == 3

    def test_db_error_returns_null(self, monkeypatch):
        monkeypatch.setattr(ft, "_get_conn", lambda: (_ for _ in ()).throw(Exception("db err")))
        result = ft._query_ses_flood_study(-33.87, 151.21)
        assert result["ses_in_flood_planning_area"] is None

    def test_conn_closed_on_success(self, monkeypatch):
        conn = self._make_conn(count=0)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        ft._query_ses_flood_study(-33.87, 151.21)
        conn.close.assert_called_once()

    def test_conn_closed_on_error(self, monkeypatch):
        mock_conn = MagicMock()
        mock_conn.cursor.side_effect = Exception("cursor fail")
        monkeypatch.setattr(ft, "_get_conn", lambda: mock_conn)
        ft._query_ses_flood_study(-33.87, 151.21)
        mock_conn.close.assert_called_once()

    def test_unknown_value_passed_through(self, monkeypatch):
        """Unknown value not in _SES_CLASS_DISPLAY is used as-is."""
        rows = [{"value": "SomeCustomZone", "instrument_key": "LEP", "lga_name": "LGA"}]
        conn = self._make_conn(count=1, rows=rows)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_ses_flood_study(-33.87, 151.21)
        assert result["ses_in_flood_planning_area"] is True
        assert result["ses_flood_class"] == "SomeCustomZone"

    def test_campbelltown_aep_tiers(self, monkeypatch):
        """Campbelltown-specific AEP values should map correctly."""
        rows = [
            {"value": "0.2%AEP", "instrument_key": "Study", "lga_name": "Campbelltown"},
            {"value": "1.0%AEP", "instrument_key": "Study", "lga_name": "Campbelltown"},
        ]
        conn = self._make_conn(count=2, rows=rows)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_ses_flood_study(-33.87, 151.21)
        assert result["ses_in_flood_planning_area"] is True
        # 1.0%AEP is more frequent than 0.2%AEP
        assert "1% AEP" in result["ses_flood_class"]


# ═══════════════════════════════════════════════════════════════════════════
# _query_compound_risk_layers
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryCompoundRiskLayers:
    """Tests for _query_compound_risk_layers (lines 793–824)."""

    def _make_conn(self, rows=None):
        mock_cur = MagicMock()
        mock_cur.__enter__ = MagicMock(return_value=mock_cur)
        mock_cur.__exit__ = MagicMock(return_value=False)
        mock_cur.fetchall.return_value = rows or []
        mock_conn = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        return mock_conn

    def test_no_matches_all_none(self, monkeypatch):
        conn = self._make_conn(rows=[])
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_compound_risk_layers(-33.87, 151.21)
        assert result["compound_heritage"] is None
        assert result["compound_riparian"] is None
        assert result["compound_wetlands"] is None
        assert result["compound_landslide"] is None

    def test_heritage_match(self, monkeypatch):
        rows = [{"layer_type": "heritage", "value": "State Heritage", "instrument_key": "LEP"}]
        conn = self._make_conn(rows=rows)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_compound_risk_layers(-33.87, 151.21)
        assert result["compound_heritage"] == "State Heritage"
        assert result["compound_riparian"] is None

    def test_empty_value_returns_true(self, monkeypatch):
        """Empty string value → falsy → True used instead."""
        rows = [{"layer_type": "riparian", "value": "", "instrument_key": "DCP"}]
        conn = self._make_conn(rows=rows)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_compound_risk_layers(-33.87, 151.21)
        assert result["compound_riparian"] is True

    def test_none_value_returns_true(self, monkeypatch):
        """None value → falsy → True used instead."""
        rows = [{"layer_type": "wetlands", "value": None, "instrument_key": "DCP"}]
        conn = self._make_conn(rows=rows)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_compound_risk_layers(-33.87, 151.21)
        assert result["compound_wetlands"] is True

    def test_multiple_layers(self, monkeypatch):
        rows = [
            {"layer_type": "heritage", "value": "State", "instrument_key": "LEP"},
            {"layer_type": "landslide", "value": "High", "instrument_key": "DCP"},
        ]
        conn = self._make_conn(rows=rows)
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_compound_risk_layers(-33.87, 151.21)
        assert result["compound_heritage"] == "State"
        assert result["compound_landslide"] == "High"
        assert result["compound_riparian"] is None
        assert result["compound_wetlands"] is None

    def test_db_error_returns_none_dict(self, monkeypatch):
        monkeypatch.setattr(ft, "_get_conn", lambda: (_ for _ in ()).throw(Exception("db err")))
        result = ft._query_compound_risk_layers(-33.87, 151.21)
        for lt in ft._COMPOUND_LAYER_TYPES:
            assert result[f"compound_{lt}"] is None

    def test_conn_closed(self, monkeypatch):
        conn = self._make_conn(rows=[])
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        ft._query_compound_risk_layers(-33.87, 151.21)
        conn.close.assert_called_once()

    def test_all_four_layer_types_present(self, monkeypatch):
        conn = self._make_conn(rows=[])
        monkeypatch.setattr(ft, "_get_conn", lambda: conn)
        result = ft._query_compound_risk_layers(-33.87, 151.21)
        assert set(result.keys()) == {
            "compound_heritage", "compound_riparian",
            "compound_wetlands", "compound_landslide",
        }


# ═══════════════════════════════════════════════════════════════════════════
# _query_dea_wofs
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryDeaWofs:
    """Tests for _query_dea_wofs (lines 830–878)."""

    def _mock_rasterio_open(self, band_count, pixel_value):
        """Create mock rasterio dataset for BytesIO usage."""
        mock_ds = MagicMock()
        mock_ds.count = band_count
        import numpy as np
        mock_ds.read.return_value = np.array([[pixel_value]])
        mock_ds.__enter__ = MagicMock(return_value=mock_ds)
        mock_ds.__exit__ = MagicMock(return_value=False)
        return mock_ds

    def _setup_wofs_mocks(self, monkeypatch, pixel_value, band_count=3,
                          content_type="image/tiff", content=b"II*\x00"):
        """Common setup for WOfS tests: mock requests + rasterio.

        _query_dea_wofs does `import io; import rasterio` inside the function,
        then `rasterio.open(io.BytesIO(r.content))`. We patch the rasterio mock
        already in sys.modules from conftest_mocks.
        """
        resp = MagicMock()
        resp.raise_for_status = MagicMock()
        resp.headers = {"Content-Type": content_type}
        resp.content = content
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)

        mock_ds = MagicMock()
        mock_ds.count = band_count
        # Post-#745-D1, bands are selected by NAME: give the mock a
        # descriptions tuple with 'frequency' LAST and return pixel_value
        # for that band (other bands return a count-like value).
        mock_ds.descriptions = tuple(
            (["count_wet", "count_clear"][:band_count - 1]) + ["frequency"]
        )
        mock_ds.read.side_effect = lambda idx: _make_array(
            [[pixel_value if idx == band_count else 635.0]])
        mock_ds.__enter__ = MagicMock(return_value=mock_ds)
        mock_ds.__exit__ = MagicMock(return_value=False)

        # Replace rasterio in sys.modules with a fresh mock that has .open configured
        rasterio_mod = MagicMock()
        rasterio_mod.open = MagicMock(return_value=mock_ds)
        monkeypatch.setitem(sys.modules, "rasterio", rasterio_mod)

        # The function runs _fetch inside a ThreadPoolExecutor. Python's
        # `import rasterio` inside the inner function captures the local from the
        # outer function scope. Monkeypatching sys.modules affects the `import`
        # statement. But to be safe, also bypass the thread pool:
        class _SyncExecutor:
            def __init__(self, **kw): pass
            def __enter__(self): return self
            def __exit__(self, *a): pass
            def submit(self, fn, *a, **kw):
                f = MagicMock()
                try:
                    f.result = MagicMock(return_value=fn(*a, **kw))
                except Exception as e:
                    f.result = MagicMock(side_effect=e)
                return f
        monkeypatch.setattr(ft, "ThreadPoolExecutor", _SyncExecutor)
        return mock_ds, resp

    def test_happy_path_frequency_band(self, monkeypatch):
        """3-band TIFF → selects the band NAMED frequency, 0.45 → 45.0%."""
        mock_ds, _ = self._setup_wofs_mocks(monkeypatch, 0.45, band_count=3)
        result = ft._query_dea_wofs(-33.87, 151.21)
        assert result["dea_wofs_frequency_pct"] == 45.0

    def test_single_band_named_frequency(self, monkeypatch):
        """Single band works ONLY when named frequency (no positional read)."""
        mock_ds, _ = self._setup_wofs_mocks(monkeypatch, 0.3, band_count=1)
        result = ft._query_dea_wofs(-33.87, 151.21)
        assert result["dea_wofs_frequency_pct"] == 30.0

    def test_nodata_neg999_returns_none(self, monkeypatch):
        self._setup_wofs_mocks(monkeypatch, -999.0)
        result = ft._query_dea_wofs(-33.87, 151.21)
        assert result["dea_wofs_frequency_pct"] is None

    def test_negative_value_returns_none(self, monkeypatch):
        self._setup_wofs_mocks(monkeypatch, -1.0)
        result = ft._query_dea_wofs(-33.87, 151.21)
        assert result["dea_wofs_frequency_pct"] is None

    def test_non_tiff_content_returns_none(self, monkeypatch):
        self._setup_wofs_mocks(monkeypatch, 0.5,
                               content_type="application/xml",
                               content=b"<error>service unavailable</error>")
        result = ft._query_dea_wofs(-33.87, 151.21)
        assert result["dea_wofs_frequency_pct"] is None

    def test_out_of_range_value_fails_closed(self, monkeypatch):
        """#745 D1: a frequency can never exceed 1.0 — the old clamp turned a
        stray count into a fake 100% flood signal. Out-of-range → None."""
        self._setup_wofs_mocks(monkeypatch, 55.5)
        result = ft._query_dea_wofs(-33.87, 151.21)
        assert result["dea_wofs_frequency_pct"] is None

    def test_count_magnitude_value_fails_closed(self, monkeypatch):
        """#745 D1: the live bug value class (count_clear ~635) → None, not 100."""
        self._setup_wofs_mocks(monkeypatch, 635.0)
        result = ft._query_dea_wofs(-33.87, 151.21)
        assert result["dea_wofs_frequency_pct"] is None

    def test_http_error_returns_none(self, monkeypatch):
        monkeypatch.setattr("requests.get", lambda *a, **kw: (_ for _ in ()).throw(Exception("timeout")))
        result = ft._query_dea_wofs(-33.87, 151.21)
        assert result["dea_wofs_frequency_pct"] is None

    def test_result_rounded_to_2dp(self, monkeypatch):
        self._setup_wofs_mocks(monkeypatch, 0.12345)
        result = ft._query_dea_wofs(-33.87, 151.21)
        assert result["dea_wofs_frequency_pct"] == 12.35

    def test_zero_value_returns_zero(self, monkeypatch):
        """Value 0.0 → not nodata, should return 0.0."""
        self._setup_wofs_mocks(monkeypatch, 0.0)
        result = ft._query_dea_wofs(-33.87, 151.21)
        assert result["dea_wofs_frequency_pct"] == 0.0

    def test_tiff_magic_bytes_detected(self, monkeypatch):
        """Content-Type wrong but TIFF magic bytes present → still processed."""
        self._setup_wofs_mocks(monkeypatch, 0.5,
                               content_type="application/octet-stream",
                               content=b"II*\x00" + b"\x00" * 100)
        result = ft._query_dea_wofs(-33.87, 151.21)
        assert result["dea_wofs_frequency_pct"] == 50.0


# ═══════════════════════════════════════════════════════════════════════════
# _sample_raster
# ═══════════════════════════════════════════════════════════════════════════

class TestSampleRaster:
    """Tests for _sample_raster (lines 885–907)."""

    def test_file_not_exists_returns_none(self, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        result = ft._sample_raster("/fake/path.tif", 100.0, 200.0, -999.0)
        assert result is None

    def test_point_outside_bounds_returns_none(self, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda p: True)
        mock_ds = MagicMock()
        mock_ds.bounds = (0, 0, 50, 50)  # left, bottom, right, top
        mock_ds.__enter__ = MagicMock(return_value=mock_ds)
        mock_ds.__exit__ = MagicMock(return_value=False)
        rasterio_mod = sys.modules.get("rasterio") or MagicMock()
        # setattr (not direct assignment) so the real module's open is restored
        monkeypatch.setattr(rasterio_mod, "open", lambda p, *a, **kw: mock_ds, raising=False)
        monkeypatch.setitem(sys.modules, "rasterio", rasterio_mod)
        result = ft._sample_raster("/fake/path.tif", 100.0, 200.0, -999.0)
        assert result is None

    def _mock_raster_ds(self, monkeypatch, bounds, index_ret, pixel_value):
        """Helper to set up a mocked rasterio dataset for _sample_raster tests."""
        monkeypatch.setattr(os.path, "exists", lambda p: True)
        mock_ds = MagicMock()
        mock_ds.bounds = bounds
        mock_ds.index.return_value = index_ret
        mock_ds.height = 100
        mock_ds.width = 100
        # _sample_raster does ds.read(1)[row, col] — build a 2D-indexable object
        mock_ds.read.return_value = _make_array([[pixel_value] * 100] * 100)
        mock_ds.__enter__ = MagicMock(return_value=mock_ds)
        mock_ds.__exit__ = MagicMock(return_value=False)
        rasterio_mod = sys.modules.get("rasterio") or MagicMock()
        # setattr (not direct assignment) so the real module's open is restored
        monkeypatch.setattr(rasterio_mod, "open", lambda p, *a, **kw: mock_ds, raising=False)
        monkeypatch.setitem(sys.modules, "rasterio", rasterio_mod)
        return mock_ds

    def test_nodata_value_returns_none(self, monkeypatch):
        self._mock_raster_ds(monkeypatch, (0, 0, 200, 200), (5, 5), -999.0)
        result = ft._sample_raster("/fake/path.tif", 100.0, 100.0, -999.0)
        assert result is None

    def test_valid_value_returned(self, monkeypatch):
        self._mock_raster_ds(monkeypatch, (0, 0, 200, 200), (5, 5), 42.5)
        result = ft._sample_raster("/fake/path.tif", 100.0, 100.0, -999.0)
        assert result == 42.5

    def test_nan_value_returns_none(self, monkeypatch):
        self._mock_raster_ds(monkeypatch, (0, 0, 200, 200), (5, 5), float('nan'))
        result = ft._sample_raster("/fake/path.tif", 100.0, 100.0, -999.0)
        assert result is None

    def test_rasterio_error_returns_none(self, monkeypatch):
        monkeypatch.setattr(os.path, "exists", lambda p: True)
        rasterio_mod = sys.modules.get("rasterio") or MagicMock()
        monkeypatch.setattr(
            rasterio_mod, "open",
            lambda p, *a, **kw: (_ for _ in ()).throw(Exception("corrupt")),
            raising=False,
        )
        monkeypatch.setitem(sys.modules, "rasterio", rasterio_mod)
        result = ft._sample_raster("/fake/path.tif", 100.0, 100.0, -999.0)
        assert result is None

    def test_row_col_clamped(self, monkeypatch):
        """Row/col outside raster extent are clamped to valid range."""
        self._mock_raster_ds(monkeypatch, (0, 0, 200, 200), (-1, 150), 10.0)
        result = ft._sample_raster("/fake/path.tif", 100.0, 100.0, -999.0)
        assert result == 10.0

    def test_bounds_check_inclusive(self, monkeypatch):
        """Point exactly on boundary should be accepted."""
        self._mock_raster_ds(monkeypatch, (100, 100, 200, 200), (0, 0), 5.0)
        result = ft._sample_raster("/fake/path.tif", 100.0, 100.0, -999.0)
        assert result == 5.0


# ═══════════════════════════════════════════════════════════════════════════
# _query_flood_study_rasters
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryFloodStudyRasters:
    """Tests for _query_flood_study_rasters (lines 910–1028)."""

    def test_rasterio_not_installed_returns_empty(self, monkeypatch):
        """When rasterio import fails, return empty studies list."""
        import builtins
        real_import = builtins.__import__
        def mock_import(name, *a, **kw):
            if name == "rasterio":
                raise ImportError("no rasterio")
            return real_import(name, *a, **kw)
        monkeypatch.setattr(builtins, "__import__", mock_import)
        result = ft._query_flood_study_rasters(-33.87, 151.21)
        assert result["flood_studies"] == []

    def _mock_transformers(self, monkeypatch):
        """Set up transformer mocks for all CRS types used by FLOOD_STUDIES."""
        mock_transformer = MagicMock()
        mock_transformer.transform.return_value = (200000, 6500000)
        monkeypatch.setattr(ft, "_STUDY_TRANSFORMERS", {
            crs: mock_transformer for crs in set(s["crs"] for s in ft.FLOOD_STUDIES.values())
        })

    def test_no_study_dirs_exist_returns_empty(self, monkeypatch):
        """All study proxy files don't exist → no studies matched."""
        self._mock_transformers(monkeypatch)
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        result = ft._query_flood_study_rasters(-33.87, 151.21)
        assert result["flood_studies"] == []
        # Backward-compat hawkesbury fields still present
        assert "hawkesbury_flood_study" in result
        assert result["hawkesbury_flood_study"] is None

    def test_hawkesbury_backward_compat_fields(self, monkeypatch):
        """Even with no data, all hawkesbury_flood_level_* keys present."""
        self._mock_transformers(monkeypatch)
        monkeypatch.setattr(os.path, "exists", lambda p: False)
        result = ft._query_flood_study_rasters(-33.87, 151.21)
        expected_keys = [
            "hawkesbury_flood_level_2aep", "hawkesbury_flood_level_5aep",
            "hawkesbury_flood_level_10aep", "hawkesbury_flood_level_20aep",
            "hawkesbury_flood_level_50aep", "hawkesbury_flood_level_100aep",
            "hawkesbury_flood_level_200aep", "hawkesbury_flood_level_500aep",
            "hawkesbury_flood_level_pmf",
        ]
        for key in expected_keys:
            assert key in result
            assert result[key] is None

    def test_matched_study_structure(self, monkeypatch):
        """When a study matches, the dict has expected keys."""
        self._mock_transformers(monkeypatch)

        # Only hawkesbury proxy exists
        monkeypatch.setattr(os.path, "exists", lambda p: "hawkesbury" in p)

        # Mock rasterio to return valid data for bounds check
        mock_ds = MagicMock()
        mock_ds.bounds = (100000, 6000000, 400000, 7000000)
        mock_ds.__enter__ = MagicMock(return_value=mock_ds)
        mock_ds.__exit__ = MagicMock(return_value=False)

        rasterio_mod = sys.modules.get("rasterio") or MagicMock()
        # setattr (not direct assignment) so the real module's open is restored
        monkeypatch.setattr(rasterio_mod, "open", lambda p, *a, **kw: mock_ds, raising=False)
        monkeypatch.setitem(sys.modules, "rasterio", rasterio_mod)

        # Mock _sample_raster to return a value for hawkesbury
        monkeypatch.setattr(
            ft, "_sample_raster",
            lambda path, x, y, nodata, valid_range=None: 15.5 if "hawkesbury" in path else None,
        )

        result = ft._query_flood_study_rasters(-33.62, 150.82)
        assert len(result["flood_studies"]) >= 1
        study = result["flood_studies"][0]
        assert "study_key" in study
        assert "study_name" in study
        assert "source" in study
        assert "design" in study
        assert "historical" in study


# ═══════════════════════════════════════════════════════════════════════════
# _query_ground_elevation
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryGroundElevation:
    """Tests for _query_ground_elevation (lines 1031–1064)."""

    def _mock_response(self, json_body):
        m = MagicMock()
        m.json.return_value = json_body
        m.raise_for_status = MagicMock()
        return m

    def test_happy_path(self, monkeypatch):
        resp = self._mock_response({"value": "42.5"})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_ground_elevation(-33.87, 151.21)
        assert result["ground_elevation_m_ahd"] == 42.5

    def test_nodata_string_returns_none(self, monkeypatch):
        resp = self._mock_response({"value": "NoData"})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_ground_elevation(-33.87, 151.21)
        assert result["ground_elevation_m_ahd"] is None

    def test_null_value_returns_none(self, monkeypatch):
        resp = self._mock_response({"value": None})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_ground_elevation(-33.87, 151.21)
        assert result["ground_elevation_m_ahd"] is None

    def test_non_numeric_value_returns_none(self, monkeypatch):
        resp = self._mock_response({"value": "error_text"})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_ground_elevation(-33.87, 151.21)
        assert result["ground_elevation_m_ahd"] is None

    def test_http_error_returns_none(self, monkeypatch):
        monkeypatch.setattr("requests.get", lambda *a, **kw: (_ for _ in ()).throw(Exception("timeout")))
        result = ft._query_ground_elevation(-33.87, 151.21)
        assert result["ground_elevation_m_ahd"] is None

    def test_value_rounded_to_2dp(self, monkeypatch):
        resp = self._mock_response({"value": "42.5678"})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_ground_elevation(-33.87, 151.21)
        assert result["ground_elevation_m_ahd"] == 42.57

    def test_geometry_params_correct(self, monkeypatch):
        captured = {}
        def capture(*a, **kw):
            captured["params"] = kw.get("params")
            return self._mock_response({"value": "10.0"})
        monkeypatch.setattr("requests.get", capture)
        ft._query_ground_elevation(-33.87, 151.21)
        geom = captured["params"]["geometry"]
        assert "151.21" in geom  # lng
        assert "-33.87" in geom  # lat

    def test_zero_elevation_valid(self, monkeypatch):
        """Elevation 0.0 is valid (sea level)."""
        resp = self._mock_response({"value": "0.0"})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_ground_elevation(-33.87, 151.21)
        assert result["ground_elevation_m_ahd"] == 0.0

    def test_negative_elevation_valid(self, monkeypatch):
        """Negative elevation is valid (below sea level)."""
        resp = self._mock_response({"value": "-5.0"})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_ground_elevation(-33.87, 151.21)
        assert result["ground_elevation_m_ahd"] == -5.0

    def test_missing_value_key_returns_none(self, monkeypatch):
        """Response with no 'value' key → None."""
        resp = self._mock_response({"result": "ok"})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_ground_elevation(-33.87, 151.21)
        assert result["ground_elevation_m_ahd"] is None

    def test_integer_value_works(self, monkeypatch):
        """Integer value string → parsed as float."""
        resp = self._mock_response({"value": "100"})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        result = ft._query_ground_elevation(-33.87, 151.21)
        assert result["ground_elevation_m_ahd"] == 100.0

    def test_raise_for_status_called(self, monkeypatch):
        resp = self._mock_response({"value": "10.0"})
        monkeypatch.setattr("requests.get", lambda *a, **kw: resp)
        ft._query_ground_elevation(-33.87, 151.21)
        resp.raise_for_status.assert_called_once()


# ═══════════════════════════════════════════════════════════════════════════
# _query_jrc_surface_water (ThreadPoolExecutor + rasterio)
# ═══════════════════════════════════════════════════════════════════════════

class TestQueryJrcSurfaceWater:
    """Tests for _query_jrc_surface_water (lines 436–478)."""

    def test_exception_returns_none(self, monkeypatch):
        """Any exception → jrc_water_occurrence_pct=None, jrc_data_year=None."""
        # Force the inner _sample to raise
        monkeypatch.setattr(ft, "_jrc_tile_url", lambda lat, lng: (_ for _ in ()).throw(Exception("err")))
        result = ft._query_jrc_surface_water(-33.87, 151.21)
        assert result["jrc_water_occurrence_pct"] is None
        assert result["jrc_data_year"] is None

    def _setup_jrc_mocks(self, monkeypatch, pixel_value):
        """Common setup for JRC tests: mock rasterio env, open, rowcol."""
        mock_ds = MagicMock()
        mock_ds.transform = MagicMock()
        mock_ds.height = 100
        mock_ds.width = 100
        mock_ds.read.return_value = _make_array([[pixel_value]])
        mock_ds.__enter__ = MagicMock(return_value=mock_ds)
        mock_ds.__exit__ = MagicMock(return_value=False)

        mock_env = MagicMock()
        mock_env.__enter__ = MagicMock(return_value=mock_env)
        mock_env.__exit__ = MagicMock(return_value=False)

        rasterio_mod = sys.modules.get("rasterio") or MagicMock()
        # setattr (not direct assignment) so the real module's attrs are restored
        monkeypatch.setattr(rasterio_mod, "open", lambda *a, **kw: mock_ds, raising=False)
        monkeypatch.setattr(rasterio_mod, "Env", lambda **kw: mock_env, raising=False)
        # Ensure rasterio.windows exists (for windowed read)
        windows_mod = MagicMock()
        windows_mod.Window = MagicMock()
        monkeypatch.setattr(rasterio_mod, "windows", windows_mod, raising=False)
        # Mock rasterio.transform.rowcol
        transform_mod = MagicMock()
        transform_mod.rowcol = lambda t, x, y: (50, 50)
        monkeypatch.setattr(rasterio_mod, "transform", transform_mod, raising=False)
        monkeypatch.setitem(sys.modules, "rasterio", rasterio_mod)
        monkeypatch.setitem(sys.modules, "rasterio.windows", windows_mod)
        monkeypatch.setitem(sys.modules, "rasterio.transform", transform_mod)
        return mock_ds

    def test_nodata_255_returns_none_occurrence(self, monkeypatch):
        """Pixel value 255 = nodata → occurrence is None, year still returned."""
        self._setup_jrc_mocks(monkeypatch, 255)
        result = ft._query_jrc_surface_water(-33.87, 151.21)
        assert result["jrc_water_occurrence_pct"] is None
        assert result["jrc_data_year"] == ft.JRC_DATA_YEAR

    def test_valid_occurrence_returned(self, monkeypatch):
        """Valid pixel value → returned as float percentage."""
        self._setup_jrc_mocks(monkeypatch, 75)
        result = ft._query_jrc_surface_water(-33.87, 151.21)
        assert result["jrc_water_occurrence_pct"] == 75.0
        assert result["jrc_data_year"] == ft.JRC_DATA_YEAR

    def test_zero_occurrence_is_valid(self, monkeypatch):
        """Pixel value 0 → 0.0 percent (not nodata)."""
        self._setup_jrc_mocks(monkeypatch, 0)
        result = ft._query_jrc_surface_water(-33.87, 151.21)
        assert result["jrc_water_occurrence_pct"] == 0.0
