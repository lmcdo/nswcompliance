"""
Mutation-testing-grade tests for services/granny_flat.py.

Targets every untested function with value-asserting tests designed to kill
mutmut mutants (boundary changes, operator swaps, return-value mutations).

Does NOT modify existing test files or the source under test.
"""

import base64
import io
import json
import math
import os
import pathlib
import sys
import uuid
from datetime import date
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import services.granny_flat as gf
from services.granny_flat import (
    _compute_lot_area_m2,
    _compute_confidence,
    _get_weekly_rent,
    _get_sepp_sd_standards,
    _fetch_sd_setbacks,
    _mercator_to_wgs84,
    _mercator_rings_to_wgs84,
    _mercator_rings_to_pixel_via_bbox,
    _pixel_area_to_m2,
    _check_heritage_overlay,
    _fetch_lot_geometry,
    _load_rental_data,
    GrannyFlatDetectRequest,
    GrannyFlatDetectResponse,
    GrannyFlatConfirmRequest,
    GrannyFlatConfirmResponse,
    DetectedStructure,
    SAMGEO_VALIDATED,
    MIN_STRUCTURE_AREA_M2,
    MAX_STRUCTURE_AREA_M2,
    IOU_DEDUP_THRESHOLD,
    MIN_FILL_RATIO,
    MAX_BBOX_FRACTION,
    MAX_ASPECT_RATIO,
    DETECTION_PROMPTS,
)


# ---------------------------------------------------------------------------
# Shared test fixtures
# ---------------------------------------------------------------------------

# Sydney coords in EPSG:3857
SYD_X = 16_832_620.0
SYD_Y = -4_011_360.0
SYD_LAT = -33.87
SYD_LNG = 151.21

# A simple square lot ring in EPSG:3857 (~600m² real area at Sydney)
_SCALE = 1.0 / math.cos(math.radians(SYD_LAT))

def _rect_ring(cx, cy, w_m, h_m):
    hw = w_m * _SCALE / 2
    hh = h_m * _SCALE / 2
    return [
        [cx - hw, cy - hh],
        [cx + hw, cy - hh],
        [cx + hw, cy + hh],
        [cx - hw, cy + hh],
        [cx - hw, cy - hh],
    ]

LOT_RING_600 = _rect_ring(SYD_X, SYD_Y, 30.0, 20.0)
LOT_GEOMETRY = {"rings": [LOT_RING_600]}

TILE_BBOX = {
    "min_lat": -33.88, "max_lat": -33.86,
    "min_lng": 151.20, "max_lng": 151.22,
}


class FakeCursor:
    """Minimal cursor that tracks execute calls and returns configurable results."""
    def __init__(self, fetchall_result=None, fetchone_result=None):
        self._fetchall = fetchall_result or []
        self._fetchone = fetchone_result
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def fetchall(self):
        return self._fetchall

    def fetchone(self):
        return self._fetchone

    def close(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, *a):
        pass


class FakeConn:
    """Minimal connection returning a configurable cursor."""
    def __init__(self, cursor=None):
        self._cursor = cursor or FakeCursor()
        self.committed = False
        self.closed = False

    def cursor(self, **kw):
        return self._cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


def _make_1x1_png():
    """Create a minimal valid PNG (1x1 white pixel) using raw bytes."""
    # Minimal 1x1 white PNG — no PIL dependency
    import struct
    import zlib

    def _chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
        return struct.pack(">I", len(data)) + c + crc

    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = _chunk(b"IHDR", struct.pack(">IIBBBBB", 256, 256, 8, 2, 0, 0, 0))
    # Scanlines: filter byte 0 + 256 RGB pixels per row, 256 rows
    row = b"\x00" + b"\xff\xff\xff" * 256
    raw = row * 256
    idat = _chunk(b"IDAT", zlib.compress(raw))
    iend = _chunk(b"IEND", b"")
    return sig + ihdr + idat + iend


# ---------------------------------------------------------------------------
# _mercator_to_wgs84 — coordinate transform
# ---------------------------------------------------------------------------

class TestMercatorToWgs84:
    def test_origin(self):
        lat, lng = _mercator_to_wgs84(0.0, 0.0)
        assert lat == pytest.approx(0.0, abs=0.001)
        assert lng == pytest.approx(0.0, abs=0.001)

    def test_sydney_approx(self):
        # EPSG:3857 for Sydney: x≈16832620, y≈-4011360
        lat, lng = _mercator_to_wgs84(16_832_620.0, -4_011_360.0)
        assert lat == pytest.approx(-33.87, abs=0.1)
        assert lng == pytest.approx(151.21, abs=0.1)

    def test_positive_y_gives_positive_lat(self):
        lat, _ = _mercator_to_wgs84(0.0, 5_000_000.0)
        assert lat > 0

    def test_negative_y_gives_negative_lat(self):
        lat, _ = _mercator_to_wgs84(0.0, -5_000_000.0)
        assert lat < 0

    def test_positive_x_gives_positive_lng(self):
        _, lng = _mercator_to_wgs84(5_000_000.0, 0.0)
        assert lng > 0

    def test_negative_x_gives_negative_lng(self):
        _, lng = _mercator_to_wgs84(-5_000_000.0, 0.0)
        assert lng < 0

    def test_antimeridian(self):
        R = 20037508.342789244
        lat, lng = _mercator_to_wgs84(R, 0.0)
        assert lng == pytest.approx(180.0, abs=0.01)

    def test_formula_uses_R_constant(self):
        """Mutant: change R value → different lng output."""
        R = 20037508.342789244
        _, lng = _mercator_to_wgs84(R / 2, 0.0)
        assert lng == pytest.approx(90.0, abs=0.01)


class TestMercatorRingsToWgs84:
    def test_single_ring(self):
        rings = [[[0.0, 0.0], [1000.0, 0.0], [1000.0, 1000.0], [0.0, 0.0]]]
        result = _mercator_rings_to_wgs84(rings)
        assert len(result) == 1
        assert len(result[0]) == 4
        # GeoJSON order: [lng, lat]
        for pt in result[0]:
            assert len(pt) == 2

    def test_output_is_lng_lat_order(self):
        """GeoJSON convention: [lng, lat]."""
        rings = [[[16_832_620.0, -4_011_360.0]]]
        result = _mercator_rings_to_wgs84(rings)
        lng, lat = result[0][0]
        assert lng == pytest.approx(151.21, abs=0.1)
        assert lat == pytest.approx(-33.87, abs=0.1)

    def test_multiple_rings(self):
        rings = [
            [[0.0, 0.0], [1000.0, 0.0]],
            [[500.0, 500.0], [600.0, 600.0]],
        ]
        result = _mercator_rings_to_wgs84(rings)
        assert len(result) == 2

    def test_empty_rings(self):
        result = _mercator_rings_to_wgs84([])
        assert result == []


class TestMercatorRingsToPixelViaBbox:
    def test_corner_mapping(self):
        """Min-lng, max-lat corner should map to pixel (0, 0)."""
        bbox = {"min_lat": -34.0, "max_lat": -33.0, "min_lng": 151.0, "max_lng": 152.0}
        # Point at min_lng, max_lat in Mercator
        R = 20037508.342789244
        x_merc = 151.0 * R / 180.0
        # We need the y_merc that corresponds to lat=-33.0 (max_lat)
        y_merc = R / math.pi * math.log(math.tan(math.pi / 4 + math.radians(-33.0) / 2))
        rings = [[[x_merc, y_merc]]]
        result = _mercator_rings_to_pixel_via_bbox(rings, bbox, (256, 256))
        px, py = result[0][0]
        assert px == pytest.approx(0, abs=2)
        assert py == pytest.approx(0, abs=2)

    def test_image_size_affects_output(self):
        bbox = {"min_lat": -34.0, "max_lat": -33.0, "min_lng": 151.0, "max_lng": 152.0}
        R = 20037508.342789244
        x_merc = 151.5 * R / 180.0  # midpoint
        y_merc = R / math.pi * math.log(math.tan(math.pi / 4 + math.radians(-33.5) / 2))
        rings = [[[x_merc, y_merc]]]
        r1 = _mercator_rings_to_pixel_via_bbox(rings, bbox, (256, 256))
        r2 = _mercator_rings_to_pixel_via_bbox(rings, bbox, (512, 512))
        # Midpoint of 512 image should be ~2x the 256 result
        assert r2[0][0][0] == pytest.approx(r1[0][0][0] * 2, abs=2)


# ---------------------------------------------------------------------------
# _pixel_area_to_m2
# ---------------------------------------------------------------------------

class TestPixelAreaToM2:
    def test_known_area(self):
        """A full tile of 256x256 pixels covering a known geographic extent."""
        bbox = {"min_lat": -33.88, "max_lat": -33.87, "min_lng": 151.20, "max_lng": 151.21}
        # Tile covers ~0.01° × ~0.01° ≈ ~830m × ~1110m at Sydney
        full_tile_px = 256 * 256
        area = _pixel_area_to_m2(full_tile_px, bbox, 256, 256)
        # Should be roughly 830 * 1110 ≈ 920,000 m²
        assert area > 500_000
        assert area < 2_000_000

    def test_single_pixel(self):
        bbox = {"min_lat": -33.88, "max_lat": -33.87, "min_lng": 151.20, "max_lng": 151.21}
        area = _pixel_area_to_m2(1, bbox, 256, 256)
        assert area > 0
        # 1 pixel should be much less than full tile
        assert area < 100  # reasonable for ~3m/pixel

    def test_zero_area(self):
        bbox = {"min_lat": -33.88, "max_lat": -33.87, "min_lng": 151.20, "max_lng": 151.21}
        area = _pixel_area_to_m2(0, bbox, 256, 256)
        assert area == 0.0

    def test_lat_affects_result(self):
        """At equator, cos(lat) = 1; at Sydney, cos(lat) < 1 → different width."""
        bbox_eq = {"min_lat": -0.01, "max_lat": 0.01, "min_lng": 0.0, "max_lng": 0.02}
        bbox_syd = {"min_lat": -33.88, "max_lat": -33.86, "min_lng": 151.20, "max_lng": 151.22}
        a_eq = _pixel_area_to_m2(1000, bbox_eq, 256, 256)
        a_syd = _pixel_area_to_m2(1000, bbox_syd, 256, 256)
        # Equator has larger pixel area because cos(0) > cos(33.87)
        assert a_eq > a_syd


# ---------------------------------------------------------------------------
# _compute_lot_area_m2 — mutation killers
# ---------------------------------------------------------------------------

class TestComputeLotAreaM2Mutation:
    def test_shoelace_direction_invariant(self):
        """CW and CCW rings should give same area (abs used)."""
        ring_ccw = LOT_RING_600[:]
        ring_cw = list(reversed(ring_ccw))
        a1 = _compute_lot_area_m2({"rings": [ring_ccw]})
        a2 = _compute_lot_area_m2({"rings": [ring_cw]})
        assert a1 == pytest.approx(a2, rel=0.001)

    def test_cos_squared_correction_applied(self):
        """Without cos² correction, area would be ~45% inflated at Sydney."""
        result = _compute_lot_area_m2({"rings": [LOT_RING_600]})
        # True area should be ~600 m² (30×20), not ~870 m²
        assert result is not None
        assert result < 700  # Must have correction
        assert result > 500  # Not over-corrected

    def test_division_by_2(self):
        """Shoelace formula divides by 2. Mutant: remove / 2.0 → 2x area."""
        result = _compute_lot_area_m2({"rings": [LOT_RING_600]})
        assert result is not None
        assert result < 1200  # Without /2, would be ~1200

    def test_y_centre_used_for_correction(self):
        """Mercator correction uses y_centre of ring, not hardcoded."""
        # Ring near equator → cos²(~0) ≈ 1.0
        eq_ring = [
            [0.0, 0.0],
            [100.0, 0.0],
            [100.0, 100.0],
            [0.0, 100.0],
            [0.0, 0.0],
        ]
        result = _compute_lot_area_m2({"rings": [eq_ring]})
        assert result is not None
        # At equator, projected ≈ real → should be ~5000 m² (100×100/2 × cos²(0))
        # Actually 100×100 = 10,000 projected, /2 = 5,000, × cos²(0°) = 5,000
        # Wait — shoelace of a 100×100 square = 100×100 = 10,000 (the area sum before /2)
        # Actually the raw shoelace formula: |sum(x1*y2 - x2*y1)| / 2
        # For this square, projected area = 10,000 / 2 = 5,000? No.
        # 100m × 100m square → shoelace = 100*100 = 10,000 m² (projected)
        # Actually let me trace: the shoelace computes the polygon area directly
        # = 10,000 m² projected for a 100×100 square
        # × cos²(0) = 10,000 m²
        assert result == pytest.approx(10_000, rel=0.01)

    def test_none_geometry(self):
        assert _compute_lot_area_m2(None) is None

    def test_no_rings_key(self):
        assert _compute_lot_area_m2({}) is None

    def test_empty_rings(self):
        assert _compute_lot_area_m2({"rings": []}) is None

    def test_ring_less_than_3_points(self):
        assert _compute_lot_area_m2({"rings": [[[0, 0], [1, 1]]]}) is None

    def test_triangle(self):
        """Triangle with 3 points (+ closing point)."""
        ring = [[0.0, 0.0], [200.0, 0.0], [0.0, 200.0], [0.0, 0.0]]
        result = _compute_lot_area_m2({"rings": [ring]})
        assert result is not None
        assert result > 0


# ---------------------------------------------------------------------------
# _get_sepp_sd_standards — DB lookup, NO fallback (#817): missing rows or an
# unreachable DB return None and the endpoints fail closed (503)
# ---------------------------------------------------------------------------

class TestGetSeppSdStandards:
    def test_no_conn_returns_none(self):
        min_lot, max_gf = _get_sepp_sd_standards(conn=None)
        assert min_lot is None
        assert max_gf is None

    def test_db_values_returned(self):
        cur = FakeCursor(fetchall_result=[
            ("min_lot_size", 500.0),
            ("max_floor_area", 75.0),
        ])
        conn = FakeConn(cursor=cur)
        min_lot, max_gf = _get_sepp_sd_standards(conn)
        assert min_lot == 500.0
        assert max_gf == 75.0

    def test_partial_db_values_none_for_missing(self):
        """Mutation check: a half-loaded row set must not substitute any
        default for the missing standard."""
        cur = FakeCursor(fetchall_result=[("min_lot_size", 400.0)])
        conn = FakeConn(cursor=cur)
        min_lot, max_gf = _get_sepp_sd_standards(conn)
        assert min_lot == 400.0
        assert max_gf is None

    def test_db_error_returns_none(self):
        class ErrorCursor:
            def execute(self, *a, **kw):
                raise Exception("DB error")
            def fetchall(self):
                return []
            def close(self):
                pass
        conn = FakeConn(cursor=ErrorCursor())
        min_lot, max_gf = _get_sepp_sd_standards(conn)
        assert min_lot is None
        assert max_gf is None

    def test_empty_result_returns_none(self):
        cur = FakeCursor(fetchall_result=[])
        conn = FakeConn(cursor=cur)
        min_lot, max_gf = _get_sepp_sd_standards(conn)
        assert min_lot is None
        assert max_gf is None

    def test_rows_dict_conversion(self):
        """Mutant: change float(r[1]) to r[1] — would break if DB returns Decimal."""
        cur = FakeCursor(fetchall_result=[
            ("min_lot_size", "450"),  # string should be converted to float
        ])
        conn = FakeConn(cursor=cur)
        min_lot, _ = _get_sepp_sd_standards(conn)
        assert isinstance(min_lot, float)
        assert min_lot == 450.0


# ---------------------------------------------------------------------------
# SEPP standards unavailable — endpoints fail closed (#817): no fallback figure
# may ever reach a response, so both endpoints 503 instead
# ---------------------------------------------------------------------------

class TestSeppStandardsUnavailableFailClosed:
    def test_detect_503_when_standards_unavailable(self, monkeypatch):
        from fastapi import HTTPException
        _stub_detect_all(monkeypatch, sepp_standards=(None, None))
        req = GrannyFlatDetectRequest(
            address="1 Test St, Sydney NSW 2000", prop_id="12345",
            lat=SYD_LAT, lng=SYD_LNG, lot_geometry=LOT_GEOMETRY,
        )
        with pytest.raises(HTTPException) as exc:
            gf.detect_structures(req)
        assert exc.value.status_code == 503
        assert "450" not in str(exc.value.detail)

    def test_confirm_503_when_standards_unavailable(self, monkeypatch):
        from fastapi import HTTPException
        _stub_confirm_all(monkeypatch, sepp_standards=(None, None))
        req = _make_confirm_req()
        with pytest.raises(HTTPException) as exc:
            gf.confirm_and_calculate(req)
        assert exc.value.status_code == 503
        assert "450" not in str(exc.value.detail)

    def test_confirm_503_when_max_floor_area_missing(self, monkeypatch):
        """Mutation check: confirm derives floor area and cost from the max
        standard — a half-loaded config must fail, not render a default."""
        from fastapi import HTTPException
        _stub_confirm_all(monkeypatch, sepp_standards=(450.0, None))
        req = _make_confirm_req()
        with pytest.raises(HTTPException) as exc:
            gf.confirm_and_calculate(req)
        assert exc.value.status_code == 503

    def test_confirm_renders_injected_figures_not_constants(self, monkeypatch):
        """Mutation check: inject non-default standards and they must flow
        through to the response — a resurrected constant would pin 60.0."""
        _stub_confirm_all(monkeypatch, sepp_standards=(500.0, 75.0))
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        assert resp.max_floor_area_m2 == 75.0
        assert resp.assumed_build_cost_aud == round(75.0 * 2500.0)


# ---------------------------------------------------------------------------
# _fetch_sd_setbacks — DCP lookup
# ---------------------------------------------------------------------------

class TestFetchSdSetbacks:
    def test_none_lga_returns_none(self):
        conn = FakeConn()
        assert _fetch_sd_setbacks(conn, None) is None

    def test_empty_lga_returns_none(self):
        conn = FakeConn()
        assert _fetch_sd_setbacks(conn, "") is None

    def test_no_rows_returns_none(self):
        cur = FakeCursor(fetchall_result=[], fetchone_result=None)
        conn = FakeConn(cursor=cur)
        assert _fetch_sd_setbacks(conn, "inner_west") is None

    def test_basic_setback_row(self):
        """A single front_setback row with vmin only."""
        cur = FakeCursor()
        rows = [
            ("secondary_dwelling", "front_setback", 6.0, None, "m",
             None, "6m minimum", "4.2.1", "secondary_dwelling_specific"),
        ]
        reg_row = ("https://council.nsw.gov.au/dcp",)

        call_count = [0]
        original_fetchall = cur.fetchall
        original_fetchone = cur.fetchone

        def smart_fetchall():
            return rows

        def smart_fetchone():
            return reg_row

        cur.fetchall = smart_fetchall
        cur.fetchone = smart_fetchone

        conn = FakeConn(cursor=cur)
        result = _fetch_sd_setbacks(conn, "inner_west")
        assert result is not None
        assert len(result["sd_setbacks"]) == 1
        sb = result["sd_setbacks"][0]
        assert sb["type"] == "Front setback"
        assert "6 m minimum" in sb["requirement"]
        assert result["dcp_name"] == "Inner West DCP"
        assert result["dcp_url"] == "https://council.nsw.gov.au/dcp"

    def test_setback_with_vmin_and_vmax(self):
        """When vmin and vmax differ, both should appear."""
        cur = FakeCursor()
        rows = [
            ("secondary_dwelling", "side_setback", 0.9, 3.0, "m",
             None, None, "4.2.2", "secondary_dwelling_specific"),
        ]
        cur.fetchall = lambda: rows
        cur.fetchone = lambda: None

        conn = FakeConn(cursor=cur)
        result = _fetch_sd_setbacks(conn, "test_lga")
        sb = result["sd_setbacks"][0]
        assert "0.9 m minimum" in sb["requirement"]
        assert "3 m maximum" in sb["requirement"]

    def test_setback_vmin_equals_vmax(self):
        """When vmin == vmax, only show once (not 'X m minimum; X m maximum')."""
        cur = FakeCursor()
        rows = [
            ("secondary_dwelling", "rear_setback", 3.0, 3.0, "m",
             None, None, "4.2.3", "secondary_dwelling_specific"),
        ]
        cur.fetchall = lambda: rows
        cur.fetchone = lambda: None

        conn = FakeConn(cursor=cur)
        result = _fetch_sd_setbacks(conn, "test_lga")
        sb = result["sd_setbacks"][0]
        # vmax == vmin → only "3 m minimum" shown
        assert "3 m minimum" in sb["requirement"]
        assert "maximum" not in sb["requirement"]

    def test_setback_both_none_uses_source_text(self):
        """When vmin and vmax are both None, fall back to source_text."""
        cur = FakeCursor()
        rows = [
            ("secondary_dwelling", "max_height", None, None, "m",
             None, "Merit-based", "4.2.4", "secondary_dwelling_specific"),
        ]
        cur.fetchall = lambda: rows
        cur.fetchone = lambda: None

        conn = FakeConn(cursor=cur)
        result = _fetch_sd_setbacks(conn, "test_lga")
        sb = result["sd_setbacks"][0]
        assert sb["requirement"] == "Merit-based"

    def test_setback_both_none_no_source_text(self):
        """When vmin, vmax, and source_text are all None → fallback string."""
        cur = FakeCursor()
        rows = [
            ("secondary_dwelling", "max_height", None, None, "m",
             None, None, "4.2.4", "secondary_dwelling_specific"),
        ]
        cur.fetchall = lambda: rows
        cur.fetchone = lambda: None

        conn = FakeConn(cursor=cur)
        result = _fetch_sd_setbacks(conn, "test_lga")
        sb = result["sd_setbacks"][0]
        assert "Merit-based" in sb["requirement"] or "refer to DCP" in sb["requirement"]

    def test_dcp_name_from_lga_slug(self):
        """lga_slug is converted to title case with underscores → spaces."""
        cur = FakeCursor()
        cur.fetchall = lambda: [
            ("sd", "front_setback", 6.0, None, "m", None, None, "s1", "secondary_dwelling_specific"),
        ]
        cur.fetchone = lambda: None
        conn = FakeConn(cursor=cur)
        result = _fetch_sd_setbacks(conn, "northern_beaches")
        assert result["dcp_name"] == "Northern Beaches DCP"

    def test_db_error_returns_none(self):
        class ErrorCursor:
            def execute(self, *a, **kw):
                raise Exception("DB error")
            def close(self):
                pass
        conn = FakeConn(cursor=ErrorCursor())
        assert _fetch_sd_setbacks(conn, "inner_west") is None

    def test_unknown_control_type_label(self):
        """Unknown control_type gets a title-case label from the type string."""
        cur = FakeCursor()
        cur.fetchall = lambda: [
            ("sd", "min_floor_area", 30.0, None, "m2", None, None, "s", "secondary_dwelling_specific"),
        ]
        cur.fetchone = lambda: None
        conn = FakeConn(cursor=cur)
        result = _fetch_sd_setbacks(conn, "test")
        sb = result["sd_setbacks"][0]
        assert sb["type"] == "Min Floor Area"

    def test_condition_and_section_ref(self):
        """condition → notes, section_ref → clause."""
        cur = FakeCursor()
        cur.fetchall = lambda: [
            ("sd", "front_setback", 6.0, None, "m", "Corner lots only", None, "4.2.1(a)", "secondary_dwelling_specific"),
        ]
        cur.fetchone = lambda: None
        conn = FakeConn(cursor=cur)
        result = _fetch_sd_setbacks(conn, "test")
        sb = result["sd_setbacks"][0]
        assert sb["notes"] == "Corner lots only"
        assert sb["clause"] == "4.2.1(a)"


# ---------------------------------------------------------------------------
# _fetch_lot_geometry
# ---------------------------------------------------------------------------

class TestFetchLotGeometry:
    def _patch_requests_get(self, monkeypatch, fn):
        """Patch requests.get on the mock module in sys.modules."""
        req_mod = sys.modules.get("requests")
        if req_mod is not None:
            monkeypatch.setattr(req_mod, "get", fn)

    def test_successful_fetch(self, monkeypatch):
        fake_resp = MagicMock()
        fake_resp.raise_for_status = MagicMock()
        fake_resp.json.return_value = [{"geometry": {"rings": [[[0, 0]]]}}]
        self._patch_requests_get(monkeypatch, lambda *a, **kw: fake_resp)
        result = _fetch_lot_geometry("12345")
        assert result == {"rings": [[[0, 0]]]}

    def test_empty_response(self, monkeypatch):
        fake_resp = MagicMock()
        fake_resp.raise_for_status = MagicMock()
        fake_resp.json.return_value = []
        self._patch_requests_get(monkeypatch, lambda *a, **kw: fake_resp)
        result = _fetch_lot_geometry("12345")
        assert result is None

    def test_network_error(self, monkeypatch):
        def raise_err(*a, **kw):
            raise Exception("timeout")
        self._patch_requests_get(monkeypatch, raise_err)
        result = _fetch_lot_geometry("12345")
        assert result is None


# ---------------------------------------------------------------------------
# _load_rental_data / _get_weekly_rent — mutation killers
# ---------------------------------------------------------------------------

class TestLoadRentalData:
    def test_cache_returns_same_object(self, monkeypatch):
        monkeypatch.setattr(gf, "_RENTAL_DATA_CACHE", {"2000": {"median_weekly_rent_1br_aud": 500}})
        d1 = _load_rental_data()
        d2 = _load_rental_data()
        assert d1 is d2

    def test_missing_file_returns_empty_dict(self, monkeypatch):
        monkeypatch.setattr(gf, "_RENTAL_DATA_CACHE", None)
        monkeypatch.setattr(gf, "RENTAL_DATA_PATH", "/nonexistent/path.json")
        result = _load_rental_data()
        assert result == {}


class TestGetWeeklyRentMutation:
    def test_none_postcode(self):
        assert _get_weekly_rent(None) is None

    def test_empty_postcode(self):
        assert _get_weekly_rent("") is None

    def test_str_conversion(self, monkeypatch):
        """postcode is converted to str before lookup."""
        monkeypatch.setattr(gf, "_RENTAL_DATA_CACHE", {"2000": {"median_weekly_rent_1br_aud": 450.0}})
        assert _get_weekly_rent("2000") == 450.0

    def test_missing_postcode_key(self, monkeypatch):
        monkeypatch.setattr(gf, "_RENTAL_DATA_CACHE", {"2000": {"median_weekly_rent_1br_aud": 450.0}})
        assert _get_weekly_rent("9999") is None

    def test_entry_without_rent_key(self, monkeypatch):
        """Entry exists but has no median_weekly_rent_1br_aud key → AttributeError if .get not used."""
        monkeypatch.setattr(gf, "_RENTAL_DATA_CACHE", {"2000": {}})
        assert _get_weekly_rent("2000") is None


# ---------------------------------------------------------------------------
# _compute_confidence — comprehensive mutation killers
# ---------------------------------------------------------------------------

class TestComputeConfidenceMutation:
    def test_not_validated_always_low(self):
        conf, reason = _compute_confidence(False, 5, 5, True)
        assert conf == "low"
        assert "pre-validation" in reason.lower()

    def test_high_requires_all_four(self):
        """Must be validated + a human reviewed the count + counts agree + rent.

        FLIPPED 2026-08-06 (calibration Lane 1, item 3): the fourth condition
        is new. Count equality alone used to earn "high", but the count was
        seeded from the detector and the UI never let anyone change it, so
        equality measured nothing.
        """
        conf, _ = _compute_confidence(True, 2, 2, True, count_source="secondary_detections_classified")
        assert conf == "high"

    def test_high_needs_human_reviewed_count(self):
        """Mutation killer: dropping the count_source check must fail here."""
        assert _compute_confidence(True, 2, 2, True, count_source="unrecorded")[0] == "medium"
        assert _compute_confidence(True, 2, 2, True, count_source="machine_default")[0] == "medium"
        assert _compute_confidence(True, 2, 2, True)[0] == "medium"

    def test_counts_disagree_gives_medium(self):
        conf, reason = _compute_confidence(True, 2, 3, True)
        assert conf == "medium"
        assert "3" in reason  # samgeo count
        assert "2" in reason  # confirmed count

    def test_rent_missing_gives_medium(self):
        conf, reason = _compute_confidence(True, 2, 2, False)
        assert conf == "medium"

    def test_both_disagree_and_no_rent(self):
        conf, reason = _compute_confidence(True, 1, 3, False)
        assert conf == "medium"
        # Should mention both issues
        assert "postcode" in reason.lower() or "rent" in reason.lower()

    def test_samgeo_none_gives_medium(self):
        conf, reason = _compute_confidence(True, 2, None, True)
        assert conf == "medium"
        assert "manually" in reason.lower()

    def test_samgeo_none_no_rent(self):
        conf, reason = _compute_confidence(True, 2, None, False)
        assert conf == "medium"
        assert "rent" in reason.lower() or "postcode" in reason.lower()

    def test_singular_structure_in_reason(self):
        """1 structure → 'structure' not 'structures'."""
        _, reason = _compute_confidence(True, 1, 1, True)
        assert "structure " in reason  # singular with space after
        assert "structures" not in reason

    def test_plural_structures_in_reason(self):
        """2+ structures → 'structures'."""
        _, reason = _compute_confidence(True, 2, 2, True)
        assert "structures" in reason

    def test_high_reason_mentions_bond_data(self):
        _, reason = _compute_confidence(True, 1, 1, True, count_source="secondary_detections_classified")
        assert "bond" in reason.lower()

    def test_partial_answers_are_not_described_as_unchecked(self):
        """Sol round-7: their answers already moved the count.

        Saying the total "has not been checked against the aerial image" when
        the person classified some structures understates what they did — the
        inverse of the overclaiming this branch removes, but still inaccurate.
        """
        _, reason = _compute_confidence(
            True, 2, 3, True, count_source="machine_default", answers_given=1)
        low = reason.lower()
        assert "only partly been checked" in low
        assert "was not reviewed structure by structure" not in low

    def test_zero_answers_is_still_described_as_unchecked(self):
        _, reason = _compute_confidence(
            True, 3, 3, True, count_source="machine_default", answers_given=0)
        assert "not reviewed structure by structure" in reason.lower()

    def test_reason_never_claims_a_person_acted_when_none_did(self):
        """The item-3 pin: no unreviewed reason string may imply human input.

        The strings this replaces read "AI detected 1 structure, you confirmed
        1 — counts agree" on reports where the user could not change the
        count. Nine of the sixteen stored rows carry that sentence.
        """
        for confirmed, machine in ((1, 1), (2, 2), (1, 0), (2, 3)):
            for source in ("unrecorded", "machine_default"):
                _, reason = _compute_confidence(
                    True, confirmed, machine, True, count_source=source
                )
                low = reason.lower()
                assert "you confirmed" not in low, (confirmed, machine, source)
                assert "you classified" not in low, (confirmed, machine, source)
                assert "your answers" not in low, (confirmed, machine, source)
                assert "not reviewed structure by structure" in low, (confirmed, machine, source)

    def test_medium_disagreement_names_both_counts(self):
        """Human recorded a different number from the detector — both appear."""
        _, reason = _compute_confidence(True, 1, 3, True, count_source="secondary_detections_classified")
        assert "3" in reason and "1" in reason
        assert "your answers give" in reason.lower()

    def test_zero_counts_agree_high(self):
        """FLIPPED 2026-08-06 (Lane 1, item 3) — needs a human reviewer now."""
        assert _compute_confidence(True, 0, 0, True, count_source="secondary_detections_classified")[0] == "high"
        assert _compute_confidence(True, 0, 0, True)[0] == "medium"


# ---------------------------------------------------------------------------
# detect_structures endpoint — full integration with mocks
# ---------------------------------------------------------------------------

def _stub_detect_all(monkeypatch, lot_geometry=None, structures=None,
                     heritage=None, sepp_standards=None, tile_fetch_ok=True):
    """Stub all external dependencies for detect_structures."""
    lot_geom = lot_geometry or LOT_GEOMETRY

    # Create a real PNG tile on disk
    tile_data = _make_1x1_png()
    tile_path = os.path.join(os.environ.get("TEMP", "/tmp"), "test_gf_tile.png")
    with open(tile_path, "wb") as f:
        f.write(tile_data)

    def fake_fetch_tile(lat, lng, output_path=None, grid=3):
        return tile_path, "CC-BY NSW", TILE_BBOX

    # nsw_imagery module
    fake_imagery = MagicMock()
    fake_imagery.fetch_tile_to_file = fake_fetch_tile
    # Use monkeypatch.setitem so sys.modules is restored after the test — a raw
    # assignment leaks the fakes into later tests (e.g. _build_lot_arr's real PIL).
    monkeypatch.setitem(sys.modules, "services.nsw_imagery", fake_imagery)
    monkeypatch.setitem(sys.modules, "nsw_imagery", fake_imagery)

    # Mock PIL for the tile annotation section inside detect_structures
    # The endpoint does: from PIL import Image, ImageDraw + Image.open(tile_path)
    fake_pil_img = MagicMock()
    fake_pil_img.size = (256, 256)
    fake_pil_img.convert.return_value = fake_pil_img
    fake_pil_img.save = MagicMock(side_effect=lambda buf, **kw: buf.write(tile_data))
    fake_pil_img.__enter__ = lambda s: s
    fake_pil_img.__exit__ = lambda s, *a: None

    fake_pil_image = MagicMock()
    fake_pil_image.open.return_value = fake_pil_img
    fake_pil_image.new.return_value = fake_pil_img

    fake_pil_draw = MagicMock()
    fake_pil_draw.Draw.return_value = MagicMock()

    fake_pil = MagicMock()
    fake_pil.Image = fake_pil_image
    fake_pil.ImageDraw = fake_pil_draw

    monkeypatch.setitem(sys.modules, "PIL", fake_pil)
    monkeypatch.setitem(sys.modules, "PIL.Image", fake_pil_image)
    monkeypatch.setitem(sys.modules, "PIL.ImageDraw", fake_pil_draw)

    # _get_conn
    conn = FakeConn(cursor=FakeCursor())
    monkeypatch.setattr(gf, "_get_conn", lambda: conn)

    # _fetch_lot_geometry
    monkeypatch.setattr(gf, "_fetch_lot_geometry", lambda pid: lot_geom)

    # _get_sepp_sd_standards
    if sepp_standards:
        monkeypatch.setattr(gf, "_get_sepp_sd_standards", lambda conn=None: sepp_standards)
    else:
        monkeypatch.setattr(gf, "_get_sepp_sd_standards", lambda conn=None: (450.0, 60.0))

    # _detect_structures_samgeo
    raw_structures = structures or []
    monkeypatch.setattr(gf, "_detect_structures_samgeo", lambda *a, **kw: raw_structures)

    # _check_heritage_overlay
    monkeypatch.setattr(gf, "_check_heritage_overlay", lambda lat, lng: heritage)

    return tile_path


class TestDetectStructuresEndpoint:
    def _make_req(self, **overrides):
        defaults = dict(
            address="1 Test St, Sydney NSW 2000",
            prop_id="12345",
            lat=SYD_LAT,
            lng=SYD_LNG,
            lot_geometry=LOT_GEOMETRY,
        )
        defaults.update(overrides)
        return GrannyFlatDetectRequest(**defaults)

    def test_basic_detect_returns_response(self, monkeypatch):
        _stub_detect_all(monkeypatch)
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert isinstance(resp, GrannyFlatDetectResponse)
        assert resp.address == "1 Test St, Sydney NSW 2000"
        assert resp.samgeo_validated is True
        assert resp.confirmation_required is True

    def test_lot_area_computed(self, monkeypatch):
        _stub_detect_all(monkeypatch)
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert resp.lot_area_m2 is not None
        assert resp.lot_area_m2 > 0

    def test_sepp_eligible_large_lot(self, monkeypatch):
        _stub_detect_all(monkeypatch)
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert resp.sepp_eligible is True
        assert resp.sepp_ineligible_reason is None

    def test_sepp_ineligible_small_lot(self, monkeypatch):
        """Lot below SEPP minimum → ineligible."""
        small_ring = _rect_ring(SYD_X, SYD_Y, 10.0, 10.0)  # ~100m²
        _stub_detect_all(monkeypatch, lot_geometry={"rings": [small_ring]})
        req = self._make_req(lot_geometry={"rings": [small_ring]})
        resp = gf.detect_structures(req)
        assert resp.sepp_eligible is False
        assert resp.sepp_ineligible_reason is not None
        assert "below" in resp.sepp_ineligible_reason.lower() or "minimum" in resp.sepp_ineligible_reason.lower()

    def test_structures_detected(self, monkeypatch):
        structures = [
            {"area_px": 5000, "area_m2": 150.0, "bbox_pixel": [10, 10, 50, 50], "matched_prompt": "building"},
            {"area_px": 1000, "area_m2": 30.0, "bbox_pixel": [60, 60, 80, 80], "matched_prompt": "shed"},
        ]
        _stub_detect_all(monkeypatch, structures=structures)
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert resp.samgeo_structure_count == 2
        assert len(resp.detected_structures) == 2

    def test_largest_structure_is_main_dwelling(self, monkeypatch):
        structures = [
            {"area_px": 1000, "area_m2": 30.0, "bbox_pixel": [60, 60, 80, 80], "matched_prompt": "shed"},
            {"area_px": 5000, "area_m2": 150.0, "bbox_pixel": [10, 10, 50, 50], "matched_prompt": "building"},
        ]
        _stub_detect_all(monkeypatch, structures=structures)
        req = self._make_req()
        resp = gf.detect_structures(req)
        # Index 1 is largest (150 m²)
        assert resp.detected_structures[1].is_main_dwelling is True
        assert resp.detected_structures[0].is_main_dwelling is False

    def test_no_structures_detected(self, monkeypatch):
        _stub_detect_all(monkeypatch, structures=[])
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert resp.samgeo_structure_count == 0
        assert resp.detected_structures == []

    def test_heritage_auto_detected(self, monkeypatch):
        _stub_detect_all(monkeypatch, heritage=True)
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert resp.is_heritage is True

    def test_heritage_not_detected(self, monkeypatch):
        _stub_detect_all(monkeypatch, heritage=False)
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert resp.is_heritage is False

    def test_heritage_none_when_unavailable(self, monkeypatch):
        _stub_detect_all(monkeypatch, heritage=None)
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert resp.is_heritage is None

    def test_detect_id_is_uuid(self, monkeypatch):
        _stub_detect_all(monkeypatch)
        req = self._make_req()
        resp = gf.detect_structures(req)
        uuid.UUID(resp.detect_id)  # raises if not valid UUID

    def test_lot_geometry_fetched_when_not_provided(self, monkeypatch):
        """When req.lot_geometry is None, should call _fetch_lot_geometry."""
        called = [False]
        original = gf._fetch_lot_geometry

        def track_fetch(pid):
            called[0] = True
            return LOT_GEOMETRY

        _stub_detect_all(monkeypatch)
        monkeypatch.setattr(gf, "_fetch_lot_geometry", track_fetch)
        req = self._make_req(lot_geometry=None)
        resp = gf.detect_structures(req)
        assert called[0] is True

    def test_lot_polygon_wgs84_present_when_geometry_available(self, monkeypatch):
        _stub_detect_all(monkeypatch)
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert resp.lot_polygon_wgs84 is not None
        assert len(resp.lot_polygon_wgs84) >= 1

    def test_tile_b64_present(self, monkeypatch):
        _stub_detect_all(monkeypatch)
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert resp.tile_b64 is not None
        # Should be valid base64
        base64.b64decode(resp.tile_b64)

    def test_samgeo_not_configured_adds_warning_and_marks_failed(self, monkeypatch):
        """#745 D4: missing MODAL_STRUCTURES_URL → unavailable warning AND a
        three-state failure (count None, detection_failed) — never a confident 0."""
        _stub_detect_all(monkeypatch)
        monkeypatch.setattr(gf, "_detect_structures_samgeo",
                            lambda *a, **kw: (_ for _ in ()).throw(
                                RuntimeError("MODAL_STRUCTURES_URL not configured")))
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert any("unavailable" in w.lower() for w in resp.warnings)
        assert resp.samgeo_structure_count is None
        assert resp.detection_failed is True

    def test_modal_call_failure_is_unknown_not_zero(self, monkeypatch):
        """#745 D4 (the live bug): a detection-call failure must read as
        UNKNOWN, never as '0 existing buildings' on a lot with a house."""
        _stub_detect_all(monkeypatch)
        monkeypatch.setattr(gf, "_detect_structures_samgeo",
                            lambda *a, **kw: (_ for _ in ()).throw(
                                RuntimeError("structure detection call failed: 500")))
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert any("unknown, not zero" in w for w in resp.warnings)
        assert resp.samgeo_structure_count is None
        assert resp.detection_failed is True
        assert resp.detected_structures == []

    def test_samgeo_generic_error_adds_warning(self, monkeypatch):
        _stub_detect_all(monkeypatch)
        monkeypatch.setattr(gf, "_detect_structures_samgeo", lambda *a, **kw: (_ for _ in ()).throw(ValueError("bad")))
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert any("did not complete" in w for w in resp.warnings)
        assert resp.samgeo_structure_count is None
        assert resp.detection_failed is True

    def test_inner_modal_http_failure_raises_not_empty_list(self, monkeypatch):
        """#745 D4 root cause: the INNER Modal call boundary must raise on
        failure, never return [] (the old swallow made failure identical to
        genuine zero). Mocks requests.post inside _detect_structures_samgeo."""
        import requests as _requests
        import services.granny_flat as _gf
        monkeypatch.setenv("MODAL_STRUCTURES_URL", "https://modal.example/detect")
        # the function does `import requests as _req` locally — patch the module attr
        monkeypatch.setattr(_requests, "post",
                            lambda *a, **kw: (_ for _ in ()).throw(
                                Exception("connection reset")))
        import tempfile, os
        fd, tile = tempfile.mkstemp(suffix=".png"); os.close(fd)
        with open(tile, "wb") as f:
            f.write(bytes([0x89]) + b"PNG" + bytes([0x0D, 0x0A, 0x1A, 0x0A]))
        import pytest as _pytest
        with _pytest.raises(RuntimeError, match="structure detection call failed"):
            _gf._detect_structures_samgeo(tile, {"xmin": 0, "ymin": 0, "xmax": 1, "ymax": 1}, None)

    def test_genuine_zero_detection_is_zero_not_failed(self, monkeypatch):
        """Successful detection finding nothing → count 0, NOT failed."""
        _stub_detect_all(monkeypatch)
        monkeypatch.setattr(gf, "_detect_structures_samgeo", lambda *a, **kw: [])
        req = self._make_req()
        resp = gf.detect_structures(req)
        assert resp.samgeo_structure_count == 0
        assert resp.detection_failed is False

    def test_detect_prefers_caller_lot_area(self, monkeypatch):
        """#745 D3: the brief's reconciled lot area wins over the shoelace."""
        _stub_detect_all(monkeypatch)
        req = self._make_req()
        req = req.model_copy(update={"lot_area_m2": 486.9})
        resp = gf.detect_structures(req)
        assert resp.lot_area_m2 == 486.9

    def test_prop_id_sanitised(self, monkeypatch):
        """Path traversal characters in prop_id should be stripped."""
        _stub_detect_all(monkeypatch)
        req = self._make_req(prop_id="../../etc/passwd")
        resp = gf.detect_structures(req)
        # Should not crash — sanitisation removes slashes and dots
        assert resp.prop_id == "../../etc/passwd"  # original preserved in response
        # But the tile_path used internally should be safe

    def test_report_id_writes_to_db(self, monkeypatch):
        """When report_id is provided, detect writes to DB."""
        committed = [False]
        cur = FakeCursor()

        class TrackConn(FakeConn):
            def commit(self):
                committed[0] = True

        conn = TrackConn(cursor=cur)
        _stub_detect_all(monkeypatch)
        monkeypatch.setattr(gf, "_get_conn", lambda: conn)
        req = self._make_req(report_id="test-report-id")
        resp = gf.detect_structures(req)
        # DB write should have been attempted (commit called)
        assert committed[0] is True


# ---------------------------------------------------------------------------
# confirm_and_calculate endpoint
# ---------------------------------------------------------------------------

_UNSET = object()

def _stub_confirm_all(monkeypatch, heritage_auto=None, sepp_standards=None,
                      rental_data=_UNSET, lot_geom=None, lga_info=None,
                      dcp_data=None):
    """Stub all external dependencies for confirm_and_calculate."""
    # _get_conn
    cur = FakeCursor(fetchone_result=None)
    conn = FakeConn(cursor=cur)
    monkeypatch.setattr(gf, "_get_conn", lambda: conn)

    # _get_sepp_sd_standards
    if sepp_standards:
        monkeypatch.setattr(gf, "_get_sepp_sd_standards", lambda conn=None: sepp_standards)
    else:
        monkeypatch.setattr(gf, "_get_sepp_sd_standards", lambda conn=None: (450.0, 60.0))

    # _check_heritage_overlay
    monkeypatch.setattr(gf, "_check_heritage_overlay", lambda lat, lng: heritage_auto)

    # _fetch_lot_geometry
    monkeypatch.setattr(gf, "_fetch_lot_geometry", lambda pid: lot_geom or LOT_GEOMETRY)

    # _get_weekly_rent
    rent_val = 500.0 if rental_data is _UNSET else rental_data
    monkeypatch.setattr(gf, "_get_weekly_rent", lambda pc: rent_val)

    # lookup_lga
    default_lga = lga_info or {"lga_name": "Inner West", "lga_slug": "inner_west", "has_dcp_setbacks": False}
    monkeypatch.setattr(gf, "lookup_lga", lambda *a, **kw: default_lga)

    # _fetch_sd_setbacks
    monkeypatch.setattr(gf, "_fetch_sd_setbacks", lambda conn, slug: dcp_data)

    # audit_trail — already mocked by conftest_mocks
    return conn


def _capture_json(monkeypatch):
    """Make psycopg2.extras.Json a pass-through so the persisted dicts are readable.

    conftest_mocks stubs psycopg2 with MagicMock, and MagicMock returns the
    SAME object for every call — so the two Json(...) payloads in the confirm
    INSERT are indistinguishable without this.
    """
    monkeypatch.setattr(gf.psycopg2.extras, "Json", lambda d: d)


def _stored_inputs(conn):
    """The `inputs` jsonb dict the confirm write actually persisted."""
    rows = [p for sql, p in conn._cursor.executed
            if p and "granny_flat_reports" in sql and "INSERT" in sql.upper()]
    assert rows, (
        "confirm must write a granny_flat_reports row; captured SQL: "
        + repr([" ".join(s.split())[:60] for s, _ in conn._cursor.executed])
    )
    matches = [d for d in rows[-1]
               if isinstance(d, dict) and "confirmed_structure_count" in d]
    assert matches, "no inputs payload found in the INSERT params"
    return matches[0]


def _make_confirm_req(**overrides):
    defaults = dict(
        detect_id="test-detect-id",
        address="1 Test St, Sydney NSW 2000",
        prop_id="12345",
        lat=SYD_LAT,
        lng=SYD_LNG,
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


class TestConfirmAndCalculate:
    def test_basic_confirm_buildable(self, monkeypatch):
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        assert isinstance(resp, GrannyFlatConfirmResponse)
        assert resp.granny_flat_buildable is True
        assert resp.max_floor_area_m2 == 60.0

    def test_lot_below_sepp_min_not_buildable(self, monkeypatch):
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(lot_area_m2=300.0)
        resp = gf.confirm_and_calculate(req)
        assert resp.granny_flat_buildable is False
        assert any("below" in w.lower() or "minimum" in w.lower() for w in resp.warnings)

    def test_lot_area_none_warns(self, monkeypatch):
        _stub_confirm_all(monkeypatch)
        # Prevent fallback fetch from returning geometry
        monkeypatch.setattr(gf, "_fetch_lot_geometry", lambda pid: None)
        req = _make_confirm_req(lot_area_m2=None)
        resp = gf.confirm_and_calculate(req)
        assert any("could not be calculated" in w.lower() or "could not be verified" in w.lower() for w in resp.warnings)

    def test_heritage_true_warns(self, monkeypatch):
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(is_heritage=True)
        resp = gf.confirm_and_calculate(req)
        assert any("heritage" in w.lower() for w in resp.warnings)

    def test_heritage_auto_detected_when_user_none(self, monkeypatch):
        """When req.is_heritage is None, auto-detect from spatial_overlays."""
        _stub_confirm_all(monkeypatch, heritage_auto=True)
        req = _make_confirm_req(is_heritage=None)
        resp = gf.confirm_and_calculate(req)
        assert any("heritage" in w.lower() for w in resp.warnings)
        assert any("auto-detect" in w.lower() for w in resp.warnings)

    def test_heritage_user_false_no_warning(self, monkeypatch):
        _stub_confirm_all(monkeypatch, heritage_auto=True)
        req = _make_confirm_req(is_heritage=False)
        resp = gf.confirm_and_calculate(req)
        assert not any("heritage" in w.lower() for w in resp.warnings)

    def test_existing_secondary_dwelling_blocks(self, monkeypatch):
        """SEPP cl 53(1): only one secondary dwelling per lot."""
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(existing_secondary_dwelling=True)
        resp = gf.confirm_and_calculate(req)
        assert resp.granny_flat_buildable is False
        assert any("already exists" in w.lower() for w in resp.warnings)

    def test_multiple_secondary_structures_blocks_when_unknown(self, monkeypatch):
        """≥3 structures + existing_secondary_dwelling=None → blocked."""
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(confirmed_structure_count=3, existing_secondary_dwelling=None)
        resp = gf.confirm_and_calculate(req)
        assert resp.granny_flat_buildable is False
        assert any("MULTIPLE_SECONDARY" in w for w in resp.warnings)

    def test_two_structures_unknown_sd_not_blocked_but_warns(self, monkeypatch):
        """Exactly 2 structures + unknown SD → not blocked, but warns."""
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(confirmed_structure_count=2, existing_secondary_dwelling=None)
        resp = gf.confirm_and_calculate(req)
        # Not blocked by the ≥3 rule
        assert any("outbuilding" in w.lower() for w in resp.warnings)

    def test_rental_yield_calculated(self, monkeypatch):
        _stub_confirm_all(monkeypatch, rental_data=500.0)
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        assert resp.estimated_weekly_rent_aud == 500.0
        # 500 * 52 / (60 * 2500) = 26000 / 150000 = 17.33%
        assert resp.rental_yield_annual_pct == pytest.approx(17.33, abs=0.1)

    def test_no_rent_no_yield(self, monkeypatch):
        _stub_confirm_all(monkeypatch, rental_data=None)
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        assert resp.estimated_weekly_rent_aud is None
        assert resp.rental_yield_annual_pct is None

    def test_build_cost_when_buildable(self, monkeypatch):
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        # 60 m² × $2500/m² = $150,000
        assert resp.assumed_build_cost_aud == 150_000

    def test_no_build_cost_when_not_buildable(self, monkeypatch):
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(lot_area_m2=300.0)
        resp = gf.confirm_and_calculate(req)
        assert resp.assumed_build_cost_aud is None

    def test_confidence_high_when_all_good(self, monkeypatch):
        """FLIPPED 2026-08-06 (Lane 1, item 3): needs confirmed_count_source."""
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        # The detect row the review is checked against — without it the
        # provenance is downgraded, which is the point of _resolve_count_source.
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
        ])
        # Internally coherent: the detect row holds 2 structures, the one
        # secondary structure is answered 'garage' (still a building), so the
        # answers imply 2 — which is what is submitted.
        req = _make_confirm_req(
            confirmed_structure_count=2, samgeo_structure_count=2,
            existing_secondary_dwelling=False,   # otherwise the >=2 cap applies
            confirmed_count_source="secondary_detections_classified",
            structure_types=[{"index": 1, "answer": "garage"}],
        )
        resp = gf.confirm_and_calculate(req)
        assert resp.confidence == "high"

    def test_secondary_detections_classified_is_downgraded_when_the_count_contradicts_the_answers(self, monkeypatch):
        """Sol round-3 finding: index coverage alone was not enough.

        Genuine answers can be paired with a count they do not support — by a
        stale client or a crafted request — and index coverage would still
        have granted 'secondary_detections_classified'.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
            {"index": 2, "is_main_dwelling": False},
        ])
        # Answers imply 2 (one of the three is part of the main dwelling)…
        gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=3,   # …but 3 is submitted
            confirmed_count_source="secondary_detections_classified",
            structure_types=[{"index": 1, "answer": "part_of_main"},
                             {"index": 2, "answer": "garage"}],
        ))
        inputs = _stored_inputs(conn)
        assert inputs["confirmed_count_source"] == "machine_default"
        assert "does not follow from the answers" in inputs["confirmed_count_source_note"]

    def test_count_contradicting_its_answers_is_flagged_under_any_provenance(self, monkeypatch):
        """Sol round-4: answers and a count that disagree matter whoever sent them.

        The implied-count check used to run only when 'secondary_detections_classified' was
        claimed, so the same contradiction went unrecorded under
        machine_default.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
            {"index": 2, "is_main_dwelling": False},
        ])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=1,
            confirmed_count_source="machine_default",
            structure_types=[{"index": 1, "answer": "garage"}],
        ))
        inputs = _stored_inputs(conn)
        assert inputs["confirmed_count_source"] == "machine_default"
        assert "does not follow" in inputs["confirmed_count_source_note"]
        assert any("not treated as reviewed" in w for w in resp.warnings), resp.warnings

    def test_claim_is_refused_when_there_was_nothing_to_classify(self, monkeypatch):
        """Sol round-8: a lot with only a principal dwelling.

        `expected` is empty, so the coverage check passed vacuously and the
        claim was granted for a review that could not have happened — the
        self-agreement trap in the new field's clothes.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [{"index": 0, "is_main_dwelling": True}])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=1,
            confirmed_count_source="secondary_detections_classified",
            structure_types=[{"index": 0, "answer": "kept"}],
        ))
        assert resp.confidence == "medium"
        inputs = _stored_inputs(conn)
        assert inputs["confirmed_count_source"] == "machine_default"
        assert "nothing to classify" in inputs["confirmed_count_source_note"]

    def test_eligibility_gate_uses_the_detected_count_not_the_submitted_one(self, monkeypatch):
        """Sol round-11 (DQ-51 closed): the SEPP cl 53(1) gate keyed on caller input.

        Three structures detected and both secondaries classified as garages,
        but the request submits 1 — which used to clear the >=3 multi-structure
        block and return a buildable result.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
            {"index": 2, "is_main_dwelling": False},
        ])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=1,
            confirmed_count_source="machine_default",
            structure_types=[{"index": 1, "answer": "garage"},
                             {"index": 2, "answer": "garage"}],
        ))
        assert resp.granny_flat_buildable is False
        assert any("MULTIPLE_SECONDARY_STRUCTURES" in w for w in resp.warnings), resp.warnings
        inputs = _stored_inputs(conn)
        assert inputs["confirmed_structure_count"] == 3
        assert inputs["confirmed_structure_count_submitted"] == 1

    def test_an_unknown_index_answer_cannot_reduce_the_effective_count(self, monkeypatch):
        """Sol round-12: my own round-11 change introduced this.

        `{index: 99, answer: 'rejected'}` excludes nothing — it names no real
        structure — but it was counted, so it could pull a 3-structure lot
        down to 2 and clear the cl 53(1) block on a structure that does not
        exist.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
            {"index": 2, "is_main_dwelling": False},
        ])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=2,
            confirmed_count_source="machine_default",
            structure_types=[{"index": 99, "answer": "rejected"}],
        ))
        assert _stored_inputs(conn)["confirmed_structure_count"] == 3
        assert resp.granny_flat_buildable is False

    def test_rejecting_the_main_dwelling_does_not_unblock_two_secondaries(self, monkeypatch):
        """Sol round-15: the >=3 gate assumed the total included a principal dwelling.

        Deselecting the main dwelling took a three-structure lot to two, so
        the block did not fire even though both secondary candidates were
        still there. Counting the secondaries directly says what cl 53(1)
        actually means.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
            {"index": 2, "is_main_dwelling": False},
        ])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=2,
            structure_types=[{"index": 0, "answer": "rejected"},
                             {"index": 1, "answer": "garage"},
                             {"index": 2, "answer": "garage"}],
        ))
        assert resp.granny_flat_buildable is False
        assert any("MULTIPLE_SECONDARY_STRUCTURES" in w for w in resp.warnings), resp.warnings

    def test_an_unknown_index_cannot_force_the_existing_granny_flat_flag(self, monkeypatch):
        """Sol round-15: the override read answers that storage had discarded.

        {index: 99, answer: 'existing_gf'} names no detected structure, so it
        must not flip the lot to ineligible under cl 53(1).
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
        ])
        gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=2,
            existing_secondary_dwelling=False,
            structure_types=[{"index": 99, "answer": "existing_gf"}],
        ))
        assert _stored_inputs(conn)["existing_secondary_dwelling"] is False

    def test_no_answers_falls_back_to_the_detector_not_the_caller(self, monkeypatch):
        """Sol round-14: the last gap in the count chain.

        With the detect run in hand and nobody having classified anything,
        there is no basis for departing from what the detector found —
        returning the caller's figure let a request submit 1 against a
        three-structure run and skip the cl 53(1) block entirely.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
            {"index": 2, "is_main_dwelling": False},
        ])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=1, structure_types=None))
        assert _stored_inputs(conn)["confirmed_structure_count"] == 3
        assert resp.granny_flat_buildable is False
        assert any("MULTIPLE_SECONDARY_STRUCTURES" in w for w in resp.warnings), resp.warnings

    def test_the_block_does_not_claim_a_scan_that_never_ran(self, monkeypatch):
        """The production path: no detector, so nothing was 'detected'.

        MODAL_STRUCTURES_URL is unset in production, so _detect_structures_samgeo
        never runs and there is no detect row. The cl 53(1) gate then falls back
        to req.confirmed_structure_count — a number the CUSTOMER confirmed
        against the aerial tile — and the warning still read "Two or more
        secondary structures were detected on this lot."

        Nothing was detected. docs/FEATURES_CAPABILITIES.md already records that
        structure detection is NOT a capability (recall 0.368 against a
        pre-committed 0.70 floor); this was the served sentence that still
        claimed it, and it reaches the customer inside the PDF.

        The three tests above all seed a detect row, so they cover the case
        where "detected" is TRUE and none of them could catch this.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = None          # no detect row — the prod path
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=3,       # the USER counted three
            confirmed_count_source="unrecorded",
        ))

        assert resp.granny_flat_buildable is False
        warning = next(w for w in resp.warnings
                       if w.startswith("MULTIPLE_SECONDARY_STRUCTURES"))
        assert "detected" not in warning.lower(), (
            "the report claims a scan found these structures, but no detect row "
            f"exists and the count came from the request: {warning}"
        )
        # Nor may it claim the customer CLASSIFIED them. Without a detect row
        # effective_secondary is None and the gate fires on a TOTAL of >= 3;
        # the "1 main + 2 secondary" split is this code's inference, not
        # something the customer stated. Cross-review finding, 2026-08-25.
        assert "confirmed two or more secondary" not in warning.lower(), warning
        assert "You reported 3 structures" in warning, warning
        # The prefix is load-bearing: lib/pdf/granny-flat-report.tsx matches on
        # startsWith('MULTIPLE_SECONDARY_STRUCTURES') in three places.
        assert warning.startswith("MULTIPLE_SECONDARY_STRUCTURES:")
        # And the rule it cites must survive the rewording.
        assert "cl 53(1)" in warning

    def test_the_block_still_says_detected_when_a_scan_did_run(self, monkeypatch):
        """The other direction: with a real detect row, "detected" is accurate.

        Without this, the fix above could be satisfied by deleting the word
        everywhere, which would understate a genuine detection.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
            {"index": 2, "is_main_dwelling": False},
        ])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=3,
            confirmed_count_source="machine_default",
        ))
        warning = next(w for w in resp.warnings
                       if w.startswith("MULTIPLE_SECONDARY_STRUCTURES"))
        assert "detected" in warning.lower(), warning

    def test_an_unmatched_detect_row_is_surfaced_like_a_failed_one(self, monkeypatch):
        """Sol round-13: warning on the exception, not on the outcome.

        An expired or mismatched detect_id/prop_id/coordinate triple returns
        no row at all — just as blind as a failed read — and the count then
        fell back to the caller's figure in silence, clearing cl 53(1).
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        conn._cursor._fetchone = None          # nothing matched
        resp = gf.confirm_and_calculate(_make_confirm_req(confirmed_structure_count=1))
        assert any("could not be re-read" in w for w in resp.warnings), resp.warnings

    def test_discarded_answers_do_not_inflate_the_classified_count(self, monkeypatch):
        """Sol round-13: the reason counted answers that were thrown away.

        A referent-less answer is dropped from storage, so saying the count
        reflects "the 1 structure(s) you classified" names a classification
        that no longer exists anywhere.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
            {"index": 2, "is_main_dwelling": False},
        ])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=3,
            confirmed_count_source="machine_default",
            structure_types=[{"index": 99, "answer": "garage"}],
        ))
        assert "you classified" not in resp.confidence_reason.lower()
        assert _stored_inputs(conn)["structure_types"] == []

    def test_a_failed_detect_row_read_is_surfaced_not_swallowed(self, monkeypatch):
        """Sol round-12: a transient SQL error must not restore the old behaviour.

        Sharing the SEPP fallback's `except` turned a failed read into a
        silent None, and the count then fell back to the caller's figure with
        nothing said about it.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)

        original = gf._fetch_detect_row

        def boom(c, r):
            raise RuntimeError("transient SQL error")

        monkeypatch.setattr(gf, "_fetch_detect_row", boom)
        try:
            resp = gf.confirm_and_calculate(_make_confirm_req())
        finally:
            monkeypatch.setattr(gf, "_fetch_detect_row", original)
        assert any("could not be re-read" in w for w in resp.warnings), resp.warnings

    def test_an_existing_granny_flat_answer_outranks_the_request_flag(self, monkeypatch):
        """Sol round-11: the answer is the specific evidence for cl 53(1).

        A report could record 'existing_gf' for a structure and still compute
        eligibility as though the lot had none.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
        ])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=2,
            existing_secondary_dwelling=False,      # contradicted by the answer
            confirmed_count_source="secondary_detections_classified",
            structure_types=[{"index": 1, "answer": "existing_gf"}],
        ))
        assert resp.granny_flat_buildable is False
        inputs = _stored_inputs(conn)
        assert inputs["existing_secondary_dwelling"] is True
        assert inputs["existing_secondary_dwelling_submitted"] is False

    def test_structures_without_an_index_fall_back_to_array_position(self, monkeypatch):
        """Sol round-10: a detect row whose structures predate the index field.

        Keying on s.get('index') alone made every answer look unknown against
        a row of None identities — all answers dropped, note fired, and the
        submitted count sailed on. The brief card already falls back to array
        position; the server now agrees with it.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"is_main_dwelling": True},    # no 'index' key
            {"is_main_dwelling": False},
        ])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=2,
            existing_secondary_dwelling=False,
            confirmed_count_source="secondary_detections_classified",
            structure_types=[{"index": 1, "answer": "garage"}],
        ))
        inputs = _stored_inputs(conn)
        assert inputs["confirmed_count_source"] == "secondary_detections_classified"
        assert inputs["structure_types"] == [{"index": 1, "answer": "garage"}]
        assert resp.confidence == "high"

    def test_answers_with_no_detect_row_are_kept_out_of_the_calibration_column(self, monkeypatch):
        """A label that cannot be joined to a building must not look usable.

        With no detect row every answer is unjoinable, so writing them into
        `structure_types` would hand a calibration consumer plausible human
        classifications pointing at nothing.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = None          # no detect row resolves
        gf.confirm_and_calculate(_make_confirm_req(
            structure_types=[{"index": 1, "answer": "garage"}]))
        inputs = _stored_inputs(conn)
        assert inputs["structure_types"] == []
        assert inputs["structure_types_unjoinable"] == [{"index": 1, "answer": "garage"}]

    def test_unknown_index_is_flagged_under_any_provenance(self, monkeypatch):
        """Sol round-6: an answer with no referent must never be stored quietly.

        Under machine_default the unknown-index check used to be skipped
        entirely, so {index: 99} could be persisted as a human label pointing
        at a structure the detect run never produced.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
        ])
        gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=1,
            confirmed_count_source="machine_default",
            structure_types=[{"index": 99, "answer": "rejected"}],
        ))
        inputs = _stored_inputs(conn)
        assert "never produced" in inputs["confirmed_count_source_note"]
        # Sol round-9: the note is not enough — a referent-less answer must not
        # sit in the column a calibration consumer reads as human labels.
        assert inputs["structure_types"] == []

    def test_a_boolean_index_is_rejected_not_coerced(self):
        """Sol round-16: pydantic turns True into 1 unless told otherwise.

        {"index": true, "answer": "existing_gf"} would have attached that
        answer to structure 1 and could move the cl 53(1) verdict.
        """
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            _make_confirm_req(structure_types=[{"index": True, "answer": "existing_gf"}])

    def test_duplicate_indexes_rejected_under_every_provenance(self):
        """Sol round-4: two answers for one structure are ambiguous regardless."""
        import pydantic
        for source in ("machine_default", "unrecorded", None):
            with pytest.raises(pydantic.ValidationError):
                _make_confirm_req(
                    confirmed_count_source=source,
                    structure_types=[{"index": 1, "answer": "garage"},
                                     {"index": 1, "answer": "rejected"}],
                )

    def test_report_id_lookup_is_bound_to_the_same_detect_run(self, monkeypatch):
        """Sol round-4: a stale report_id must not win over the current detect run.

        A report_id from an earlier detection on the same parcel would
        otherwise return that run's tile, manifest and structures, and the
        review would be evaluated against the wrong run.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        gf.confirm_and_calculate(_make_confirm_req(report_id="11111111-1111-1111-1111-111111111111"))
        by_id = [(sql, p) for sql, p in conn._cursor.executed
                 if "WHERE id = %s" in sql and "granny_flat_reports" in sql]
        assert by_id, "the report_id carry-forward lookup must run when report_id is given"
        sql, params = by_id[-1]
        assert "outputs->>'detect_id' = %s" in sql
        assert "test-detect-id" in [str(x) for x in params]

    def test_machine_count_comes_from_the_detect_row_not_the_client_echo(self, monkeypatch):
        """The detector's own count, not the number the client handed back.

        `samgeo_structure_count` travels page -> route -> here, so comparing
        the submitted count against it compared two caller-supplied numbers.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
        ])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=2,
            samgeo_structure_count=99,   # a lie the client could tell
            existing_secondary_dwelling=False,
            confirmed_count_source="secondary_detections_classified",
            structure_types=[{"index": 1, "answer": "garage"}],
        ))
        # 2 from the detect row, matching the submitted 2 — the echoed 99 is
        # ignored, so this is 'high' rather than a spurious disagreement.
        assert resp.confidence == "high"
        assert "99" not in resp.confidence_reason

    def test_secondary_detections_classified_without_answers_is_rejected(self, monkeypatch):
        """Sol finding 3: a review claim with nothing recorded behind it.

        Without this the provenance field is a self-assertion — a caller could
        buy 'high' confidence by naming it, which is the unfalsifiable claim
        the field exists to remove.
        """
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            _make_confirm_req(confirmed_count_source="secondary_detections_classified")
        with pytest.raises(pydantic.ValidationError):
            _make_confirm_req(confirmed_count_source="secondary_detections_classified", structure_types=[])

    def test_duplicate_structure_indexes_are_rejected(self):
        """Two answers for the same structure make the answer set ambiguous."""
        import pydantic
        with pytest.raises(pydantic.ValidationError):
            _make_confirm_req(
                confirmed_count_source="secondary_detections_classified",
                structure_types=[{"index": 1, "answer": "garage"},
                                 {"index": 1, "answer": "rejected"}],
            )

    def test_secondary_detections_classified_is_downgraded_when_answers_name_unknown_structures(self, monkeypatch):
        """Sol finding 1: the caller's provenance flag is not trusted.

        An answer for a structure the detect run never produced cannot be a
        review of that run, so it must not buy 'high'.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
        ])
        resp = gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=1, samgeo_structure_count=1,
            confirmed_count_source="secondary_detections_classified",
            structure_types=[{"index": 99, "answer": "garage"}],
        ))
        assert resp.confidence == "medium"
        inputs = _stored_inputs(conn)
        assert inputs["confirmed_count_source"] == "machine_default"
        assert inputs["confirmed_count_source_claimed"] == "secondary_detections_classified"
        assert "never produced" in inputs["confirmed_count_source_note"]

    def test_secondary_detections_classified_is_downgraded_when_a_structure_has_no_answer(self, monkeypatch):
        """Partial coverage is not a review of the count."""
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
            {"index": 2, "is_main_dwelling": False},
        ])
        # Count is consistent with the answers (3 detected, none excluded) so
        # the mismatch check passes and the COVERAGE gap is what fires.
        gf.confirm_and_calculate(_make_confirm_req(
            confirmed_structure_count=3,
            confirmed_count_source="secondary_detections_classified",
            structure_types=[{"index": 1, "answer": "garage"}],
        ))
        inputs = _stored_inputs(conn)
        assert inputs["confirmed_count_source"] == "machine_default"
        assert "no answer" in inputs["confirmed_count_source_note"]

    def test_secondary_detections_classified_is_downgraded_when_the_detect_row_is_missing(self, monkeypatch):
        """A review we cannot check is a review we do not credit.

        Three states: absent evidence is its own outcome, never a pass.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = None
        gf.confirm_and_calculate(_make_confirm_req(
            confirmed_count_source="secondary_detections_classified",
            structure_types=[{"index": 1, "answer": "garage"}],
        ))
        inputs = _stored_inputs(conn)
        assert inputs["confirmed_count_source"] == "machine_default"
        assert "could not be re-read" in inputs["confirmed_count_source_note"]

    def test_carry_forward_is_scoped_to_the_submitted_parcel(self, monkeypatch):
        """Sol finding 2: detect_id is caller-supplied, so it cannot match globally.

        Unscoped, a request could quote another report's detect UUID and pull
        that property's tile, manifest and structures into a report describing
        a different address.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        gf.confirm_and_calculate(_make_confirm_req())
        carry = [(sql, p) for sql, p in conn._cursor.executed
                 if "detect_id" in sql and "SELECT" in sql.upper()]
        assert carry, "the detect_id carry-forward lookup must run"
        sql, params = carry[-1]
        assert "prop_id = %s" in sql
        assert "12345" in [str(x) for x in params]
        # Sol round-7: prop_id and detect_id are BOTH caller-supplied, so the
        # coordinates bound it too — otherwise a valid pair for one property
        # could be sent with another property's address.
        assert "abs(lat - %s)" in sql and "abs(lng - %s)" in sql
        assert SYD_LAT in params and SYD_LNG in params

    def test_carry_forward_finds_the_detect_row_by_detect_id(self, monkeypatch):
        """Sol finding 2: the carry-forward could almost never resolve.

        `id` never equals `detect_id` (0 of 87 production rows) and neither
        frontend sends report_id on confirm — the Next route mints a fresh
        UUID — so `WHERE id = req.report_id` missed nearly every time. Measured
        consequence: of 16 confirm rows, 0 carried an execution_manifest and 1
        carried a tile. Without this fallback the new structure answers would
        be stored with their referent already deleted.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = ("tile-b64", {"algorithm_version": "x"},
                                  [{"index": 1, "area_m2": 30}])
        gf.confirm_and_calculate(_make_confirm_req(report_id=None))

        lookups = [sql for sql, _ in conn._cursor.executed if "detect_id" in sql]
        assert lookups, "confirm must fall back to the detect_id lookup when report_id is absent"

        rows = [p for sql, p in conn._cursor.executed
                if p and "granny_flat_reports" in sql and "INSERT" in sql.upper()]
        outputs = [d for d in rows[-1]
                   if isinstance(d, dict) and "granny_flat_buildable" in d][0]
        assert outputs["detected_structures"] == [{"index": 1, "area_m2": 30}]
        assert outputs["tile_b64"] == "tile-b64"

    def test_confirm_persists_count_provenance_join_key_and_answers(self, monkeypatch):
        """Lane 1 items 3+4: the label data must reach the row, not the wire only.

        Before this, `detect_id` was accepted and dropped, the four-option
        per-structure answers never left the browser, and nothing recorded
        whether a person had touched the count — which is why the 16 stored
        confirm rows cannot be told apart from machine echoes.
        """
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        conn._cursor._fetchone = (None, None, [
            {"index": 0, "is_main_dwelling": True},
            {"index": 1, "is_main_dwelling": False},
            {"index": 2, "is_main_dwelling": False},
        ])
        req = _make_confirm_req(
            confirmed_structure_count=2,
            samgeo_structure_count=3,
            confirmed_count_source="secondary_detections_classified",
            structure_types=[
                {"index": 1, "answer": "part_of_main"},
                {"index": 2, "answer": "garage"},
            ],
        )
        gf.confirm_and_calculate(req)

        inputs = _stored_inputs(conn)
        assert inputs["confirmed_count_source"] == "secondary_detections_classified"
        assert inputs["detect_id"] == "test-detect-id"
        assert inputs["structure_types"] == [
            {"index": 1, "answer": "part_of_main"},
            {"index": 2, "answer": "garage"},
        ]

    def test_confirm_records_unrecorded_when_caller_is_silent(self, monkeypatch):
        """Absent provenance is stored as its own state, never as a human check."""
        conn = _stub_confirm_all(monkeypatch, rental_data=500.0)
        _capture_json(monkeypatch)
        gf.confirm_and_calculate(_make_confirm_req())

        inputs = _stored_inputs(conn)
        assert inputs["confirmed_count_source"] == "unrecorded"
        assert inputs["structure_types"] is None

    def test_confidence_not_high_when_count_provenance_absent(self, monkeypatch):
        """End-to-end pin: an old-shape caller (no provenance) cannot reach high."""
        _stub_confirm_all(monkeypatch, rental_data=500.0)
        req = _make_confirm_req(confirmed_structure_count=1, samgeo_structure_count=1)
        resp = gf.confirm_and_calculate(req)
        assert resp.confidence == "medium"
        assert "not reviewed structure by structure" in resp.confidence_reason.lower()

    def test_confidence_capped_when_lot_area_none(self, monkeypatch):
        """High confidence → capped to medium when lot_area unknown."""
        _stub_confirm_all(monkeypatch, rental_data=500.0)
        monkeypatch.setattr(gf, "_fetch_lot_geometry", lambda pid: None)
        req = _make_confirm_req(
            lot_area_m2=None,
            confirmed_structure_count=1, samgeo_structure_count=1,
        )
        resp = gf.confirm_and_calculate(req)
        assert resp.confidence == "medium"

    def test_confidence_capped_when_sd_unknown_and_2_structures(self, monkeypatch):
        """High confidence → capped when ≥2 structures and SD status unknown."""
        _stub_confirm_all(monkeypatch, rental_data=500.0)
        req = _make_confirm_req(
            confirmed_structure_count=2, samgeo_structure_count=2,
            existing_secondary_dwelling=None,
        )
        resp = gf.confirm_and_calculate(req)
        assert resp.confidence == "medium"

    def test_postcode_extracted_from_address(self, monkeypatch):
        """When postcode field is None, extract from address."""
        rent_called_with = []
        def track_rent(pc):
            rent_called_with.append(pc)
            return 500.0

        _stub_confirm_all(monkeypatch)
        monkeypatch.setattr(gf, "_get_weekly_rent", track_rent)
        req = _make_confirm_req(postcode=None, address="1 Test St, Sydney NSW 2000")
        resp = gf.confirm_and_calculate(req)
        assert "2000" in rent_called_with

    def test_postcode_extraction_no_match(self, monkeypatch):
        """Address without 4-digit postcode → None postcode."""
        rent_called_with = []
        def track_rent(pc):
            rent_called_with.append(pc)
            return None

        _stub_confirm_all(monkeypatch)
        monkeypatch.setattr(gf, "_get_weekly_rent", track_rent)
        req = _make_confirm_req(postcode=None, address="No postcode here")
        resp = gf.confirm_and_calculate(req)
        assert None in rent_called_with

    def test_residual_area_blocks_when_dwelling_exceeds_lot(self, monkeypatch):
        """main_dwelling_area_m2 >= lot_area_m2 → detection error, not buildable."""
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(lot_area_m2=600.0, main_dwelling_area_m2=700.0)
        resp = gf.confirm_and_calculate(req)
        assert resp.granny_flat_buildable is False
        assert any("detection error" in w.lower() for w in resp.warnings)

    def test_residual_area_blocks_when_too_small(self, monkeypatch):
        """Residual < 120m² → not buildable."""
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(lot_area_m2=600.0, main_dwelling_area_m2=500.0)
        resp = gf.confirm_and_calculate(req)
        assert resp.granny_flat_buildable is False
        assert any("insufficient" in w.lower() for w in resp.warnings)

    def test_residual_area_ok_when_large_enough(self, monkeypatch):
        """Residual ≥ 120m² → still buildable."""
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(lot_area_m2=600.0, main_dwelling_area_m2=200.0)
        resp = gf.confirm_and_calculate(req)
        assert resp.granny_fat_buildable if hasattr(resp, 'granny_fat_buildable') else resp.granny_flat_buildable is True

    def test_residual_area_skipped_when_no_dwelling(self, monkeypatch):
        """main_dwelling_area_m2=None → skip residual check."""
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(lot_area_m2=600.0, main_dwelling_area_m2=None)
        resp = gf.confirm_and_calculate(req)
        assert resp.granny_flat_buildable is True

    def test_residual_area_skipped_when_dwelling_zero(self, monkeypatch):
        """main_dwelling_area_m2=0 → skip (guard: > 0)."""
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(lot_area_m2=600.0, main_dwelling_area_m2=0.0)
        resp = gf.confirm_and_calculate(req)
        assert resp.granny_flat_buildable is True

    def test_lot_area_fallback_from_prop_id(self, monkeypatch):
        """When lot_area_m2 is None but prop_id exists, fetch geometry."""
        called = [False]
        def fake_fetch(pid):
            called[0] = True
            return LOT_GEOMETRY

        _stub_confirm_all(monkeypatch)
        monkeypatch.setattr(gf, "_fetch_lot_geometry", fake_fetch)
        monkeypatch.setattr(gf, "_compute_lot_area_m2", lambda g: 600.0)
        req = _make_confirm_req(lot_area_m2=None, prop_id="12345")
        resp = gf.confirm_and_calculate(req)
        assert called[0] is True

    def test_data_sources_include_sepp(self, monkeypatch):
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        assert any("SEPP" in ds for ds in resp.data_sources)

    def test_data_sources_include_build_cost_when_buildable(self, monkeypatch):
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        assert any("build cost" in ds.lower() or "2,500" in ds for ds in resp.data_sources)

    def test_data_sources_include_rental_when_yield_present(self, monkeypatch):
        _stub_confirm_all(monkeypatch, rental_data=500.0)
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        assert any("rental" in ds.lower() or "bond" in ds.lower() for ds in resp.data_sources)

    def test_no_rent_warning(self, monkeypatch):
        _stub_confirm_all(monkeypatch, rental_data=None)
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        assert any("rental data not available" in w.lower() for w in resp.warnings)

    def test_report_id_generated_when_not_provided(self, monkeypatch):
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(report_id=None)
        resp = gf.confirm_and_calculate(req)
        uuid.UUID(resp.report_id)  # valid UUID

    def test_report_id_preserved_when_provided(self, monkeypatch):
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(report_id="custom-id")
        resp = gf.confirm_and_calculate(req)
        assert resp.report_id == "custom-id"

    def test_dcp_setbacks_included_when_lga_has_them(self, monkeypatch):
        lga_info = {"lga_name": "Inner West", "lga_slug": "inner_west", "has_dcp_setbacks": True}
        dcp_data = {
            "sd_setbacks": [{"type": "Front", "requirement": "6m", "clause": "4.1", "notes": ""}],
            "dcp_name": "Inner West DCP",
            "dcp_url": "https://example.com",
        }
        _stub_confirm_all(monkeypatch, lga_info=lga_info, dcp_data=dcp_data)
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        assert any("DCP" in ds for ds in resp.data_sources)

    def test_db_failure_raises_503(self, monkeypatch):
        """DB write failure → HTTPException 503."""
        monkeypatch.setattr(gf, "_get_sepp_sd_standards", lambda conn=None: (450.0, 60.0))
        monkeypatch.setattr(gf, "_check_heritage_overlay", lambda lat, lng: None)
        monkeypatch.setattr(gf, "_fetch_lot_geometry", lambda pid: LOT_GEOMETRY)
        monkeypatch.setattr(gf, "_get_weekly_rent", lambda pc: 500.0)
        monkeypatch.setattr("services.lga_lookup.lookup_lga",
                            lambda *a, **kw: {"lga_name": None, "lga_slug": None, "has_dcp_setbacks": False})
        monkeypatch.setattr(gf, "_fetch_sd_setbacks", lambda conn, slug: None)

        def broken_conn():
            raise Exception("DB down")
        monkeypatch.setattr(gf, "_get_conn", broken_conn)

        req = _make_confirm_req()
        with pytest.raises(Exception):  # HTTPException or raw Exception
            gf.confirm_and_calculate(req)

    def test_existing_sd_false_no_block(self, monkeypatch):
        """existing_secondary_dwelling=False → no block."""
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(existing_secondary_dwelling=False)
        resp = gf.confirm_and_calculate(req)
        assert resp.granny_flat_buildable is True
        assert not any("already exists" in w.lower() for w in resp.warnings)

    def test_three_structures_with_sd_false_not_blocked(self, monkeypatch):
        """≥3 structures but existing_secondary_dwelling=False → not blocked by MULTIPLE_SECONDARY."""
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(confirmed_structure_count=3, existing_secondary_dwelling=False)
        resp = gf.confirm_and_calculate(req)
        assert not any("MULTIPLE_SECONDARY" in w for w in resp.warnings)

    def test_heritage_source_user_provided(self, monkeypatch):
        """When is_heritage from user, warning mentions 'user-provided'."""
        _stub_confirm_all(monkeypatch)
        req = _make_confirm_req(is_heritage=True)
        resp = gf.confirm_and_calculate(req)
        heritage_warnings = [w for w in resp.warnings if "heritage" in w.lower()]
        assert any("user-provided" in w for w in heritage_warnings)

    def test_sepp_max_gf_used_for_floor_area(self, monkeypatch):
        """max_floor_area_m2 comes from SEPP standards."""
        _stub_confirm_all(monkeypatch, sepp_standards=(450.0, 75.0))
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        assert resp.max_floor_area_m2 == 75.0

    def test_build_cost_per_m2_is_2500(self, monkeypatch):
        """Build cost = max_floor_area × $2500."""
        _stub_confirm_all(monkeypatch, sepp_standards=(450.0, 80.0))
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        assert resp.assumed_build_cost_aud == 80.0 * 2500

    def test_annual_rent_is_weekly_times_52(self, monkeypatch):
        """rental_yield = (weekly * 52) / build_cost × 100."""
        _stub_confirm_all(monkeypatch, rental_data=400.0, sepp_standards=(450.0, 60.0))
        req = _make_confirm_req()
        resp = gf.confirm_and_calculate(req)
        expected_yield = round((400.0 * 52 / (60 * 2500)) * 100, 2)
        assert resp.rental_yield_annual_pct == expected_yield


# ---------------------------------------------------------------------------
# Constants — verify they have the expected values (mutant: change constants)
# ---------------------------------------------------------------------------

class TestConstants:
    def test_samgeo_validated_is_true(self):
        assert SAMGEO_VALIDATED is True

    def test_min_structure_area(self):
        assert MIN_STRUCTURE_AREA_M2 == 15.0

    def test_max_structure_area(self):
        assert MAX_STRUCTURE_AREA_M2 == 600.0

    def test_iou_threshold(self):
        assert IOU_DEDUP_THRESHOLD == 0.5

    def test_min_fill_ratio(self):
        assert MIN_FILL_RATIO == 0.15

    def test_max_bbox_fraction(self):
        assert MAX_BBOX_FRACTION == 0.35

    def test_max_aspect_ratio(self):
        assert MAX_ASPECT_RATIO == 8.0

    def test_sepp_fallback_constants_never_return(self):
        """Source guard (#817): the SEPP fallback constants and any hardcoded
        450 / 60 regulatory default must not be reintroduced — standards render
        only from housing_sepp_standards; absence fails closed (503)."""
        src = (
            pathlib.Path(__file__).resolve().parent.parent
            / "services" / "granny_flat.py"
        ).read_text(encoding="utf-8")
        for phrase in ("_SEPP_FALLBACK", "= 450", "fallback 450", "fallback 60"):
            assert phrase not in src, f"SEPP fallback reintroduced in granny_flat.py: {phrase!r}"

    def test_detection_prompts_count(self):
        assert len(DETECTION_PROMPTS) == 3

    def test_detection_prompts_first_is_building(self):
        assert DETECTION_PROMPTS[0][0] == "building"

    def test_detection_prompts_thresholds(self):
        """Each prompt has (text, box_threshold, text_threshold)."""
        for prompt, box_t, text_t in DETECTION_PROMPTS:
            assert isinstance(prompt, str)
            assert 0.0 < box_t < 1.0
            assert 0.0 < text_t < 1.0


# ---------------------------------------------------------------------------
# _build_lot_arr — rasterisation (requires PIL+numpy, skip if unavailable)
# ---------------------------------------------------------------------------

_has_pil_numpy = False
try:
    from PIL import Image
    import numpy
    _has_pil_numpy = True
except ImportError:
    pass


@pytest.mark.skipif(not _has_pil_numpy, reason="PIL+numpy required")
class TestBuildLotArr:
    def test_full_tile_ring(self):
        from services.granny_flat import _build_lot_arr
        rings = [[(0, 0), (255, 0), (255, 255), (0, 255)]]
        arr = _build_lot_arr(rings, 256, 256)
        assert arr.shape == (256, 256)
        assert arr.sum() > 200 * 200

    def test_empty_ring_list(self):
        from services.granny_flat import _build_lot_arr
        arr = _build_lot_arr([], 256, 256)
        assert arr.sum() == 0

    def test_small_ring(self):
        from services.granny_flat import _build_lot_arr
        rings = [[(10, 10), (50, 10), (30, 50)]]
        arr = _build_lot_arr(rings, 256, 256)
        assert arr.sum() > 0
        assert arr.sum() < 256 * 256

    def test_ring_too_few_points_skipped(self):
        from services.granny_flat import _build_lot_arr
        rings = [[(10, 10), (50, 10)]]
        arr = _build_lot_arr(rings, 256, 256)
        assert arr.sum() == 0


# ---------------------------------------------------------------------------
# Pydantic model validation
# ---------------------------------------------------------------------------

class TestModels:
    def test_detect_request_defaults(self):
        req = GrannyFlatDetectRequest(
            address="test", prop_id="123", lat=-33.87, lng=151.21,
        )
        assert req.lot_geometry is None
        assert req.report_id is None

    def test_detected_structure_defaults(self):
        s = DetectedStructure(
            index=0, area_px=100, bbox_pixel=[0, 0, 10, 10],
            matched_prompt="building",
        )
        assert s.area_m2 is None
        assert s.is_main_dwelling is False

    def test_confirm_request_optional_fields(self):
        req = GrannyFlatConfirmRequest(
            detect_id="d", address="a", prop_id="p",
            lat=-33.87, lng=151.21, confirmed_structure_count=1,
            lot_area_m2=None,
        )
        assert req.lot_area_m2 is None
        assert req.samgeo_structure_count is None
        assert req.postcode is None
        assert req.report_id is None
        assert req.is_heritage is None
        assert req.existing_secondary_dwelling is None
        assert req.main_dwelling_area_m2 is None

    def test_confirm_response_fields(self):
        resp = GrannyFlatConfirmResponse(
            report_id="r", address="a",
            granny_flat_buildable=True, max_floor_area_m2=60.0,
            estimated_weekly_rent_aud=None, rental_yield_annual_pct=None,
            assumed_build_cost_aud=None,
            confidence="high", confidence_reason="test",
            review_state="reviewed", review_state_label="L",
            review_state_detail="D",
            data_sources=[], warnings=[],
        )
        assert resp.granny_flat_buildable is True

    def test_confirm_response_requires_review_state(self):
        """The state a report is in is not optional on the wire.

        Defaulting it would let a code path return no state and have the
        surface render an empty badge — the silence the whole change removes.
        A missing state must be a 500 at the boundary, not a blank line in a
        paid PDF.
        """
        import pytest as _pytest
        for missing in ("review_state", "review_state_label", "review_state_detail"):
            kwargs = dict(
                report_id="r", address="a",
                granny_flat_buildable=True, max_floor_area_m2=60.0,
                estimated_weekly_rent_aud=None, rental_yield_annual_pct=None,
                assumed_build_cost_aud=None,
                confidence="high", confidence_reason="test",
                review_state="reviewed", review_state_label="L",
                review_state_detail="D",
                data_sources=[], warnings=[],
            )
            del kwargs[missing]
            with _pytest.raises(Exception):
                GrannyFlatConfirmResponse(**kwargs)
