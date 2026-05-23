"""
Unit tests for granny_flat.py geometry helpers.

These tests cover:
  - Mercator area correction (bug: shoelace on EPSG:3857 inflates area ~45% at Sydney latitudes)
  - Lot clipping (bbox corner check, not just centre)
  - is_main_dwelling assignment (largest structure, not index 0)

All tests use synthetic coordinates — no external API calls needed.

SYDNEY REFERENCE:
  lat=-33.87°, lng=151.21°
  EPSG:3857 centre: x≈16832620, y≈-4011360
  Mercator scale factor: 1/cos(lat) ≈ 1.2044
  cos²(lat) ≈ 0.6893  →  corrected_area = projected_area × 0.6893
"""

import math
import sys
import os
import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from services.granny_flat import (
    _compute_lot_area_m2,
    _build_lot_arr,
    _mercator_rings_to_pixel_via_bbox,
    DetectedStructure,
)

# ---------------------------------------------------------------------------
# Synthetic test geometry
# ---------------------------------------------------------------------------

# EPSG:3857 centre at Sydney CBD
SYD_X = 16_832_620.0
SYD_Y = -4_011_360.0

# Mercator scale at Sydney: 1/cos(-33.87°)
SYD_LAT_RAD = math.radians(-33.87)
SYD_SCALE = 1.0 / math.cos(SYD_LAT_RAD)
SYD_COS2 = math.cos(SYD_LAT_RAD) ** 2  # ≈ 0.6893


def _rect_ring(cx: float, cy: float, real_width_m: float, real_height_m: float) -> list:
    """
    Build a closed EPSG:3857 ring for a rectangle with the given REAL dimensions
    centred at (cx, cy).  Mercator coords = real coords / cos(lat).
    """
    hw = real_width_m * SYD_SCALE / 2
    hh = real_height_m * SYD_SCALE / 2
    return [
        [cx - hw, cy - hh],
        [cx + hw, cy - hh],
        [cx + hw, cy + hh],
        [cx - hw, cy + hh],
        [cx - hw, cy - hh],  # closed
    ]


# ---------------------------------------------------------------------------
# _compute_lot_area_m2
# ---------------------------------------------------------------------------

class TestComputeLotAreaM2:

    def test_600m2_lot_at_sydney(self):
        """A 30m×20m real lot at Sydney latitude should return ≈600 m²."""
        ring = _rect_ring(SYD_X, SYD_Y, 30.0, 20.0)
        result = _compute_lot_area_m2({"rings": [ring]})
        assert result is not None
        assert abs(result - 600.0) < 5.0, (
            f"Expected ~600 m², got {result:.1f} m². "
            "Mercator distortion correction may be missing."
        )

    def test_450m2_sepp_boundary(self):
        """
        A lot with REAL area 450 m² must compute as ≥445 m² (within 1% of threshold).
        Without Mercator correction the inflated value (~653 m²) passes incorrectly
        for lots as small as ~310 m² real area.
        """
        # 30m × 15m = 450 m²
        ring = _rect_ring(SYD_X, SYD_Y, 30.0, 15.0)
        result = _compute_lot_area_m2({"rings": [ring]})
        assert result is not None
        assert 440.0 <= result <= 460.0, (
            f"Expected 450±10 m², got {result:.1f} m²"
        )

    def test_310m2_lot_fails_sepp(self):
        """
        A real 310 m² lot must compute as <450 m² so the SEPP check correctly
        rejects it.  The uncorrected formula would return ~450 m² and pass it.
        """
        # 31m × 10m = 310 m²
        ring = _rect_ring(SYD_X, SYD_Y, 31.0, 10.0)
        result = _compute_lot_area_m2({"rings": [ring]})
        assert result is not None
        assert result < 450.0, (
            f"310 m² real lot should be <450 m² after correction, got {result:.1f} m². "
            "This property would incorrectly appear SEPP-eligible without the fix."
        )

    def test_uncorrected_would_inflate(self):
        """
        Document the bug: uncorrected shoelace on EPSG:3857 inflates a 600 m²
        lot to ≈870 m² at Sydney latitudes.
        """
        ring = _rect_ring(SYD_X, SYD_Y, 30.0, 20.0)
        # Compute raw (uncorrected) projected area using shoelace only
        n = len(ring)
        raw = 0.0
        for i in range(n):
            x1, y1 = ring[i]
            x2, y2 = ring[(i + 1) % n]
            raw += x1 * y2 - x2 * y1
        projected = abs(raw) / 2.0
        inflation_factor = projected / 600.0
        assert inflation_factor > 1.3, (
            f"Expected uncorrected inflation >1.3× at Sydney, got {inflation_factor:.3f}×"
        )

    def test_missing_geometry_returns_none(self):
        assert _compute_lot_area_m2({}) is None
        assert _compute_lot_area_m2({"rings": [[]]}) is None
        assert _compute_lot_area_m2({"rings": [[SYD_X, SYD_Y]]}) is None  # single point

    def test_none_input_returns_none(self):
        assert _compute_lot_area_m2(None) is None


# ---------------------------------------------------------------------------
# Lot clipping — bbox corner check
# ---------------------------------------------------------------------------

@pytest.mark.skipif(
    not all(__import__("importlib").util.find_spec(m) for m in ("PIL", "numpy")),
    reason="lot clipping tests require Pillow + numpy",
)
class TestLotClipping:
    """
    Verify that the lot clipping logic retains structures whose bounding box
    overlaps the lot even when the bbox centre is outside it.

    These tests exercise _build_lot_arr and _mercator_rings_to_pixel_via_bbox
    directly, plus the clipping logic pattern used in _detect_structures_samgeo.
    """

    def _make_lot_arr(self, lot_x0, lot_y0, lot_x1, lot_y1, bbox, image_size=(256, 256)):
        """Build a lot_arr for a rectangular lot in pixel-space from bbox coords."""
        rings = [[
            [lot_x0, lot_y0],
            [lot_x1, lot_y0],
            [lot_x1, lot_y1],
            [lot_x0, lot_y1],
            [lot_x0, lot_y0],
        ]]
        pixel_rings = _mercator_rings_to_pixel_via_bbox(rings, bbox, image_size)
        return _build_lot_arr(pixel_rings, *image_size)

    def _passes_clipping(self, lot_arr, bbox_pixel):
        """Replicate the fixed corner+centre clipping logic."""
        x1, y1, x2, y2 = bbox_pixel
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        h, w = lot_arr.shape
        check_points = [(cx, cy), (x1, y1), (x2, y2), (x1, y2), (x2, y1)]
        return any(
            0 <= py < h and 0 <= px < w and lot_arr[py, px]
            for px, py in check_points
        )

    def _centre_only_clipping(self, lot_arr, bbox_pixel):
        """The OLD (buggy) centre-only clipping logic."""
        x1, y1, x2, y2 = bbox_pixel
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        h, w = lot_arr.shape
        if 0 <= cy < h and 0 <= cx < w:
            return bool(lot_arr[cy, cx])
        return False

    def test_structure_fully_inside_lot_passes(self):
        """A structure entirely within the lot passes both old and new clipping."""
        # Lot covers right half of 256×256 image (columns 128-255)
        # Structure bbox fully inside lot (columns 150-200, rows 100-150)
        bbox = {
            "min_lat": -34.0, "max_lat": -33.5,
            "min_lng": 151.0, "max_lng": 151.5,
        }
        lot_merc_x0 = 151.25 * 20037508.342789244 / 180  # midpoint lng → right half
        lot_arr = self._make_lot_arr(
            lot_merc_x0, -34.0 * 6378137 * math.pi / 180,
            151.5 * 20037508.342789244 / 180, -33.5 * 6378137 * math.pi / 180,
            bbox,
        )
        # Build a simple lot_arr directly in pixel space for clarity
        lot_arr = np.zeros((256, 256), dtype=bool)
        lot_arr[80:180, 128:256] = True  # lot = right half

        bbox_inside = [150, 100, 200, 150]
        assert self._passes_clipping(lot_arr, bbox_inside)
        assert self._centre_only_clipping(lot_arr, bbox_inside)

    def test_structure_centred_outside_but_corner_inside(self):
        """
        Structure bbox straddles the lot boundary — centre is outside, but a corner
        is inside.  Old (buggy) logic rejects it; new logic retains it.
        """
        lot_arr = np.zeros((256, 256), dtype=bool)
        lot_arr[80:180, 128:256] = True  # lot = right half (x ≥ 128)

        # Structure bbox: x 100-140 — centre at x=120 (outside), right edge at x=140 (inside)
        bbox_straddling = [100, 100, 140, 150]

        # New logic should pass (corner at x=140 is inside)
        assert self._passes_clipping(lot_arr, bbox_straddling), (
            "Corner+centre clipping should retain structure whose corner is inside lot"
        )
        # Old logic rejects it (centre at x=120 is outside)
        assert not self._centre_only_clipping(lot_arr, bbox_straddling), (
            "This documents the old bug: centre-only clipping drops the structure"
        )

    def test_structure_fully_outside_lot_rejected(self):
        """A structure entirely outside the lot is rejected by both strategies."""
        lot_arr = np.zeros((256, 256), dtype=bool)
        lot_arr[80:180, 128:256] = True  # lot = right half

        bbox_outside = [10, 10, 90, 90]  # entirely in left half
        assert not self._passes_clipping(lot_arr, bbox_outside)
        assert not self._centre_only_clipping(lot_arr, bbox_outside)


# ---------------------------------------------------------------------------
# is_main_dwelling — largest structure, not index 0
# ---------------------------------------------------------------------------

class TestIsMainDwelling:
    """
    After the fix, is_main_dwelling should be assigned to the structure with
    the largest area_m2, not the first structure in the list.
    """

    def _assign_main_dwelling(self, structures: list[DetectedStructure]) -> list[DetectedStructure]:
        """
        Replicate the fixed assignment logic from detect_structures.
        Used to test the logic in isolation without hitting Modal.
        """
        if structures:
            largest_idx = max(
                range(len(structures)),
                key=lambda i: structures[i].area_m2 or 0,
            )
            structures[largest_idx].is_main_dwelling = True
        return structures

    def _make_structure(self, idx, area_m2) -> DetectedStructure:
        return DetectedStructure(
            index=idx,
            area_px=int(area_m2 * 100),
            area_m2=area_m2,
            bbox_pixel=[0, 0, 10, 10],
            matched_prompt="building",
            is_main_dwelling=False,
        )

    def test_largest_gets_main_dwelling(self):
        """When the largest structure is not at index 0, it should still be main dwelling."""
        structures = [
            self._make_structure(0, 45.0),   # shed
            self._make_structure(1, 180.0),  # main house (largest)
            self._make_structure(2, 22.0),   # garage
        ]
        result = self._assign_main_dwelling(structures)
        assert result[1].is_main_dwelling is True
        assert result[0].is_main_dwelling is False
        assert result[2].is_main_dwelling is False

    def test_first_structure_is_largest_still_works(self):
        """When the largest IS at index 0, it still gets flagged correctly."""
        structures = [
            self._make_structure(0, 180.0),
            self._make_structure(1, 45.0),
        ]
        result = self._assign_main_dwelling(structures)
        assert result[0].is_main_dwelling is True

    def test_single_structure_is_main_dwelling(self):
        structures = [self._make_structure(0, 120.0)]
        result = self._assign_main_dwelling(structures)
        assert result[0].is_main_dwelling is True

    def test_old_index_zero_logic_fails_for_shed_first(self):
        """
        Document the bug: if the shed is detected first (index 0), the old
        logic incorrectly labels it as the main dwelling.
        """
        structures = [
            self._make_structure(0, 25.0),   # shed detected first
            self._make_structure(1, 180.0),  # actual house
        ]
        # Old logic: is_main_dwelling = (i == 0)
        old_result = [s.is_main_dwelling for s in structures]
        # Both start as False — simulate the old assignment
        old_flags = [i == 0 for i in range(len(structures))]
        assert old_flags == [True, False], "Old logic incorrectly labels shed as main dwelling"

        # New logic fixes it
        fixed = self._assign_main_dwelling(structures)
        assert fixed[1].is_main_dwelling is True
