"""Tests for services/lot_dimensions.py — Python port of lot-dimensions.ts.

Covers: shoelace area, boundary extraction, boundary classification,
        scale correction, edge cases (degenerate polygons, closing-point
        dedup, irregular lots).
"""
from __future__ import annotations

import math
from unittest.mock import patch, MagicMock

import pytest

from services.lot_dimensions import (
    _shoelace_area,
    _extract_boundaries,
    _classify_boundaries,
    calculate_lot_dimensions,
    fetch_lot_geometry,
    _SCALE_FACTOR,
)


# ---------------------------------------------------------------------------
# Helpers — build EPSG:3857 rings from real-world metre coordinates
# ---------------------------------------------------------------------------

def _to_3857(x_m: float, y_m: float) -> tuple[float, float]:
    """Convert real-world metres to EPSG:3857 (apply scale factor)."""
    return (x_m * _SCALE_FACTOR, y_m * _SCALE_FACTOR)


def _rect_ring(width: float, depth: float, origin: tuple[float, float] = (0.0, 0.0)):
    """Build a closed rectangular ring in EPSG:3857.

    Ring order matches Portal convention: bottom-left → bottom-right → top-right → top-left → close.
    After classification: bottom = front, right = side_right, top = rear, left = side_left.
    """
    ox, oy = origin
    pts = [
        _to_3857(ox, oy),
        _to_3857(ox + width, oy),
        _to_3857(ox + width, oy + depth),
        _to_3857(ox, oy + depth),
        _to_3857(ox, oy),  # closing point
    ]
    return pts


# ---------------------------------------------------------------------------
# _shoelace_area
# ---------------------------------------------------------------------------

class TestShoelaceArea:
    def test_unit_square(self):
        pts = [(0, 0), (1, 0), (1, 1), (0, 1)]
        assert _shoelace_area(pts) == pytest.approx(1.0)

    def test_rectangle(self):
        pts = [(0, 0), (15, 0), (15, 40), (0, 40)]
        assert _shoelace_area(pts) == pytest.approx(600.0)

    def test_triangle(self):
        pts = [(0, 0), (10, 0), (5, 8)]
        assert _shoelace_area(pts) == pytest.approx(40.0)

    def test_winding_order_invariant(self):
        """CW and CCW produce same area."""
        cw = [(0, 0), (0, 10), (10, 10), (10, 0)]
        ccw = list(reversed(cw))
        assert _shoelace_area(cw) == pytest.approx(_shoelace_area(ccw))


# ---------------------------------------------------------------------------
# _extract_boundaries
# ---------------------------------------------------------------------------

class TestExtractBoundaries:
    def test_four_edges_from_rectangle(self):
        pts = [(0, 0), (15, 0), (15, 40), (0, 40)]
        boundaries = _extract_boundaries(pts)
        assert len(boundaries) == 4

    def test_lengths_correct(self):
        pts = [(0, 0), (15, 0), (15, 40), (0, 40)]
        boundaries = _extract_boundaries(pts)
        lengths = [b["length"] for b in boundaries]
        assert lengths[0] == pytest.approx(15.0)  # bottom
        assert lengths[1] == pytest.approx(40.0)  # right side
        assert lengths[2] == pytest.approx(15.0)  # top
        assert lengths[3] == pytest.approx(40.0)  # left side

    def test_bearing_range(self):
        pts = [(0, 0), (15, 0), (15, 40), (0, 40)]
        boundaries = _extract_boundaries(pts)
        for b in boundaries:
            assert 0 <= b["bearing"] < 360


# ---------------------------------------------------------------------------
# _classify_boundaries
# ---------------------------------------------------------------------------

class TestClassifyBoundaries:
    def test_four_edge_classification(self):
        pts = [(0, 0), (15, 0), (15, 40), (0, 40)]
        boundaries = _extract_boundaries(pts)
        _classify_boundaries(boundaries)
        types = [b["type"] for b in boundaries]
        assert types == ["front", "side_right", "rear", "side_left"]

    def test_irregular_lot_all_classified(self):
        """5-sided lot — all boundaries get a type."""
        pts = [(0, 0), (15, 0), (18, 20), (15, 40), (0, 40)]
        boundaries = _extract_boundaries(pts)
        _classify_boundaries(boundaries)
        for b in boundaries:
            assert b["type"] in ("front", "rear", "side_left", "side_right")


# ---------------------------------------------------------------------------
# calculate_lot_dimensions — integration
# ---------------------------------------------------------------------------

class TestCalculateLotDimensions:
    def test_rectangular_15x40(self):
        """Golden test: 15m × 40m rectangular lot."""
        geometry = {"rings": [_rect_ring(15, 40)]}
        result = calculate_lot_dimensions(geometry)
        assert result is not None
        assert result.area_m2 == pytest.approx(600.0, abs=0.5)
        assert result.frontage_m == pytest.approx(15.0, abs=0.5)
        assert result.depth_m == pytest.approx(40.0, abs=0.5)
        assert result.is_corner is False

    def test_square_20x20(self):
        geometry = {"rings": [_rect_ring(20, 20)]}
        result = calculate_lot_dimensions(geometry)
        assert result is not None
        assert result.area_m2 == pytest.approx(400.0, abs=0.5)
        assert result.frontage_m == pytest.approx(20.0, abs=0.5)
        assert result.depth_m == pytest.approx(20.0, abs=0.5)

    def test_narrow_lot(self):
        """7.5m × 30m — typical narrow inner-city lot."""
        geometry = {"rings": [_rect_ring(7.5, 30)]}
        result = calculate_lot_dimensions(geometry)
        assert result is not None
        assert result.area_m2 == pytest.approx(225.0, abs=0.5)
        assert result.frontage_m == pytest.approx(7.5, abs=0.5)
        assert result.depth_m == pytest.approx(30.0, abs=0.5)

    def test_large_lot(self):
        """50m × 80m — large suburban lot."""
        geometry = {"rings": [_rect_ring(50, 80)]}
        result = calculate_lot_dimensions(geometry)
        assert result is not None
        assert result.area_m2 == pytest.approx(4000.0, abs=1.0)
        assert result.frontage_m == pytest.approx(50.0, abs=0.5)
        assert result.depth_m == pytest.approx(80.0, abs=0.5)

    def test_closing_point_dedup(self):
        """Ring with duplicate closing point is handled."""
        ring = _rect_ring(15, 40)
        assert ring[0] == ring[-1]  # closing point present
        geometry = {"rings": [ring]}
        result = calculate_lot_dimensions(geometry)
        assert result is not None
        assert result.area_m2 == pytest.approx(600.0, abs=0.5)


# ---------------------------------------------------------------------------
# Edge cases / None handling
# ---------------------------------------------------------------------------

class TestEdgeCases:
    def test_none_geometry(self):
        assert calculate_lot_dimensions(None) is None

    def test_empty_rings(self):
        assert calculate_lot_dimensions({"rings": []}) is None

    def test_empty_first_ring(self):
        assert calculate_lot_dimensions({"rings": [[]]}) is None

    def test_too_few_points(self):
        ring = [_to_3857(0, 0), _to_3857(1, 0), _to_3857(1, 0)]  # 3 pts but closing = degenerate
        assert calculate_lot_dimensions({"rings": [ring]}) is None

    def test_missing_rings_key(self):
        assert calculate_lot_dimensions({"spatialReference": {}}) is None

    def test_three_points_triangle(self):
        """Triangle with closing point = 4 points in ring, valid."""
        ring = [
            _to_3857(0, 0),
            _to_3857(10, 0),
            _to_3857(5, 8),
            _to_3857(0, 0),
        ]
        result = calculate_lot_dimensions({"rings": [ring]})
        assert result is not None
        assert result.area_m2 == pytest.approx(40.0, abs=0.5)


# ---------------------------------------------------------------------------
# fetch_lot_geometry — mocked HTTP
# ---------------------------------------------------------------------------

class TestFetchLotGeometry:
    @patch("requests.get")
    def test_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"geometry": {"rings": [[]]}}]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        result = fetch_lot_geometry("12345")
        assert result == {"rings": [[]]}
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_empty_response(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = []
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        assert fetch_lot_geometry("12345") is None

    @patch("requests.get")
    def test_network_error(self, mock_get):
        mock_get.side_effect = Exception("timeout")
        assert fetch_lot_geometry("12345") is None

    @patch("requests.get")
    def test_no_geometry_key(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.json.return_value = [{"other": "data"}]
        mock_resp.raise_for_status = MagicMock()
        mock_get.return_value = mock_resp

        assert fetch_lot_geometry("12345") is None


# ---------------------------------------------------------------------------
# Scale factor sanity
# ---------------------------------------------------------------------------

class TestScaleFactor:
    def test_scale_factor_reasonable(self):
        """Scale factor for NSW latitude should be ~1.2."""
        assert 1.15 < _SCALE_FACTOR < 1.25

    def test_scale_correction_applied(self):
        """Raw EPSG:3857 coords are larger than real-world metres."""
        raw_x = 100.0 * _SCALE_FACTOR
        corrected = raw_x / _SCALE_FACTOR
        assert corrected == pytest.approx(100.0)
