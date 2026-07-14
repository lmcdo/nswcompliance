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
# calculate_lot_dimensions — integration (frontage/depth via oriented bbox)
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
        assert result.irregular is False

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

    def test_rotated_rectangle(self):
        """OBB's key advantage: a 15x40 lot rotated 30deg off-axis still resolves
        to ~15 x ~40 (the old edge-order heuristic could not)."""
        import math as _m
        a = _m.radians(30)
        def _rot(x, y):
            return (x * _m.cos(a) - y * _m.sin(a), x * _m.sin(a) + y * _m.cos(a))
        corners = [_rot(0, 0), _rot(15, 0), _rot(15, 40), _rot(0, 40)]
        ring = [_to_3857(x, y) for x, y in corners] + [_to_3857(*corners[0])]
        result = calculate_lot_dimensions({"rings": [ring]})
        assert result is not None
        assert result.area_m2 == pytest.approx(600.0, abs=1.0)
        assert result.frontage_m == pytest.approx(15.0, abs=0.5)
        assert result.depth_m == pytest.approx(40.0, abs=0.5)

    def test_irregular_lot_defers_frontage(self):
        """An L-shaped lot fills <60% of its bounding box, so frontage/depth are
        left None (the engine then estimates) — but the area is still computed."""
        pts = [(0, 0), (20, 0), (20, 5), (5, 5), (5, 20), (0, 20)]
        ring = [_to_3857(x, y) for x, y in pts] + [_to_3857(*pts[0])]
        result = calculate_lot_dimensions({"rings": [ring]})
        assert result is not None
        assert result.area_m2 == pytest.approx(175.0, abs=1.0)
        assert result.frontage_m is None
        assert result.depth_m is None
        # flagged so the UI reads "can't be measured", not a broken lookup
        # (Bowral regression: fill ratio 0.594 just under the 0.6 gate)
        assert result.irregular is True

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


# ---------------------------------------------------------------------------
# Battleaxe (flag-lot) detection — port of lot-shape-analysis.ts.
# Golden fixture: 38 PARK ROAD BOWRAL 2576 (propId 1119594), real Portal
# cadastre geometry fetched 2026-07-14. Reference values are the frontend
# implementation's verified output (Verify UI): handle 16.31 m x 43.1 m,
# head 70.09 m wide, head area 3,710 m2, total lot 4,189 m2.
# ---------------------------------------------------------------------------

import json
import os

from services.lot_dimensions import eligibility_lot_width

_FIXTURE = os.path.join(os.path.dirname(__file__), "fixtures", "lot_geometry_38_park_rd_bowral.json")


class TestBattleaxeDetection:
    def _bowral_dims(self):
        with open(_FIXTURE) as f:
            fx = json.load(f)
        return calculate_lot_dimensions(fx.get("geometry"))

    def test_bowral_golden_classified_battleaxe(self):
        dims = self._bowral_dims()
        assert dims is not None
        assert dims.lot_type == "battleaxe"

    def test_bowral_golden_matches_frontend_reference_values(self):
        """The Python port must reproduce the TS implementation's verified output."""
        dims = self._bowral_dims()
        assert dims.battleaxe_access_way_width_m == pytest.approx(16.31, abs=0.05)
        assert dims.battleaxe_access_way_length_m == pytest.approx(43.1, abs=0.5)
        assert dims.battleaxe_main_lot_width_m == pytest.approx(70.09, abs=0.05)
        assert dims.battleaxe_main_lot_area_m2 == pytest.approx(3710, abs=10)
        assert dims.area_m2 == pytest.approx(4188.6, abs=1)

    def test_bowral_eligibility_width_is_head_not_handle(self):
        """The SEPP width tests must see the developable head (70 m), never the
        16 m access handle and never None — the exact defect that rendered every
        width-gated form 'unconfirmed' on the live tool."""
        dims = self._bowral_dims()
        assert eligibility_lot_width(dims) == pytest.approx(70.09, abs=0.05)

    def test_rectangular_lot_is_not_battleaxe_and_keeps_frontage(self):
        ring = _rect_ring(15.0, 40.0)
        dims = calculate_lot_dimensions({"rings": [ring]})
        assert dims.lot_type == "rectangular"
        assert dims.battleaxe_main_lot_width_m is None
        assert eligibility_lot_width(dims) == dims.frontage_m

    def test_eligibility_width_none_for_none_dims(self):
        assert eligibility_lot_width(None) is None

    def test_synthetic_flag_lot_detected(self):
        """L-shaped flag lot: 4m x 30m handle attached to a 20m x 25m head."""
        pts_m = [
            (0, 0), (4, 0),          # handle bottom
            (4, 30), (20, 30),       # handle up, step out to head
            (20, 55), (0, 55),       # head right side up, top
        ]
        ring = [_to_3857(x, y) for x, y in pts_m]
        ring.append(ring[0])
        dims = calculate_lot_dimensions({"rings": [ring]})
        assert dims.lot_type == "battleaxe"
        assert dims.battleaxe_access_way_width_m == pytest.approx(4.0, abs=0.5)
        assert dims.battleaxe_main_lot_width_m == pytest.approx(20.0, abs=0.5)
        assert eligibility_lot_width(dims) == pytest.approx(20.0, abs=0.5)
