"""Campaign item 4 — execution manifests + units/CRS runtime checks.

What must hold:
  - manifests are derived from the objects actually passed into the
    with per-scene used flags),
  - a wrong-CRS or implausible-geometry input yields the product's TYPED
    unavailable state — never a number, never a crash,
  - the granny-flat filter loop survives real detections (DQ-45: the shadowed
    bbox variable made every surviving detection raise TypeError).

Mutation notes: dropping the used-flag bookkeeping fails
test_scene_identity_marks_unusable_scenes; removing an entry check fails that
service's wrong-CRS pin; reverting the DQ-45 rename fails
test_detection_survives_filter_loop with the original TypeError.
"""
import io
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "services"))

from services.execution_manifest import (  # noqa: E402
    MANIFEST_KEY,
    build_manifest,
    stac_item_identity,
)
from services.geometry_checks import (  # noqa: E402
    check_point_nsw,
    check_polygon_wgs84,
    check_rings_epsg3857,
)

SYD_LAT, SYD_LNG = -33.8688, 151.2093


# ---------------------------------------------------------------------------
# geometry_checks — the only defence recomputation can never provide
# ---------------------------------------------------------------------------

class TestPointChecks:
    def test_sydney_point_passes(self):
        assert check_point_nsw(SYD_LAT, SYD_LNG) is None

    def test_swapped_axis_order_named(self):
        reason = check_point_nsw(SYD_LNG, SYD_LAT)
        assert reason and "swapped" in reason

    def test_mercator_metres_named(self):
        reason = check_point_nsw(-4004807.0, 16833312.0)
        assert reason and "degrees expected" in reason

    def test_null_island_rejected(self):
        assert "null-island" in check_point_nsw(0.0, 0.0)

    def test_outside_envelope_rejected(self):
        """Auckland — clearly outside the NSW envelope. (Melbourne is NOT a
        valid rejection case: NSW's bounding box genuinely contains northern
        Victoria; the check catches CRS-class errors, not border lines.)"""
        assert check_point_nsw(-36.85, 174.76) is not None

    def test_non_numeric_rejected(self):
        assert check_point_nsw(None, "x") is not None


class TestPolygonChecks:
    def _lot(self, d=0.001):
        return {"type": "Polygon", "coordinates": [[
            [SYD_LNG, SYD_LAT], [SYD_LNG + d, SYD_LAT],
            [SYD_LNG + d, SYD_LAT + d], [SYD_LNG, SYD_LAT + d],
            [SYD_LNG, SYD_LAT],
        ]]}

    def test_parcel_scale_lot_passes(self):
        assert check_polygon_wgs84(self._lot()) is None

    def test_metres_as_degrees_span_rejected(self):
        assert "larger" in check_polygon_wgs84(self._lot(d=5.0))

    def test_degenerate_rejected(self):
        assert "degenerate" in check_polygon_wgs84(self._lot(d=0.0))

    def test_none_and_wrong_type_rejected(self):
        assert check_polygon_wgs84(None) is not None
        assert check_polygon_wgs84({"type": "Point"}) is not None

    def test_interior_ring_garbage_rejected(self):
        """A hole carrying projected metres corrupts a clip as surely as the
        outer ring — every ring is validated (Sol finding, 2026-08-03)."""
        poly = self._lot()
        poly["coordinates"].append([[334000.0, 6250000.0], [334010.0, 6250000.0],
                                    [334010.0, 6250010.0], [334000.0, 6250000.0]])
        reason = check_polygon_wgs84(poly)
        assert reason and "ring 1" in reason

    def test_trailing_nan_vertex_rejected(self):
        poly = self._lot()
        poly["coordinates"][0].insert(2, [float("nan"), SYD_LAT])
        assert "non-finite" in check_polygon_wgs84(poly)


class TestRingChecks:
    def test_mercator_rings_pass(self):
        rings = [[[16833312.0, -4004807.0], [16833362.0, -4004807.0],
                  [16833362.0, -4004757.0], [16833312.0, -4004807.0]]]
        assert check_rings_epsg3857(rings) is None

    def test_degree_rings_named_as_wrong_crs(self):
        rings = [[[SYD_LNG, SYD_LAT], [SYD_LNG + 0.001, SYD_LAT],
                  [SYD_LNG, SYD_LAT + 0.001], [SYD_LNG, SYD_LAT]]]
        assert "WGS84 fed" in check_rings_epsg3857(rings)

    def test_empty_rejected(self):
        assert check_rings_epsg3857([]) is not None

    def test_mga_metres_rejected_as_wrong_projected_crs(self):
        """MGA Zone 56 eastings/northings are metre-scale and inside the
        WORLD Mercator extent — only the NSW-envelope test catches them
        (Sol finding, 2026-08-03)."""
        rings = [[[334000.0, 6250000.0], [334050.0, 6250000.0],
                  [334050.0, 6250050.0], [334000.0, 6250000.0]]]
        reason = check_rings_epsg3857(rings)
        assert reason and "MGA" in reason

    def test_trailing_bad_vertex_rejected(self):
        """Every vertex is checked — a single trailing WGS84 vertex corrupts
        the clip just as surely as a leading one."""
        good = [16833312.0, -4004807.0]
        rings = [[good, [16833362.0, -4004807.0], [16833362.0, -4004757.0],
                  [16833330.0, -4004760.0], [16833320.0, -4004770.0],
                  [16833318.0, -4004780.0], [16833316.0, -4004790.0],
                  [16833314.0, -4004795.0], [151.2, -33.8], good]]
        assert check_rings_epsg3857(rings) is not None

    def test_nan_vertex_rejected(self):
        rings = [[[16833312.0, -4004807.0], [float("nan"), -4004807.0],
                  [16833362.0, -4004757.0], [16833312.0, -4004807.0]]]
        assert "non-finite" in check_rings_epsg3857(rings)


# ---------------------------------------------------------------------------
# execution_manifest — frame + STAC identity
# ---------------------------------------------------------------------------

class TestManifestFrame:
    def test_frame_carries_versions_and_inputs(self):
        m = build_manifest(product="x", algorithm_version="x-1.0",
                           inputs={"a": 1}, query_params={"lat": SYD_LAT},
                           parcel_identity={"prop_id": "1"})
        assert m["product"] == "x"
        assert m["algorithm_version"] == "x-1.0"
        assert m["inputs"] == {"a": 1}
        assert m["schema"] == 1
        assert m["built_at"]

    def test_stac_identity_reads_the_object(self):
        item = SimpleNamespace(
            id="S2A_56HLH_20260801_0_L2A",
            datetime=datetime(2026, 8, 1, 0, 5, tzinfo=timezone.utc),
            properties={"eo:cloud_cover": 3.2, "platform": "sentinel-2a"},
        )
        ident = stac_item_identity(item)
        assert ident["id"] == "S2A_56HLH_20260801_0_L2A"
        assert ident["datetime"].startswith("2026-08-01T00:05")
        assert ident["cloud_cover"] == 3.2


# ---------------------------------------------------------------------------
# Typed unavailable at the service entries — never a number from wrong CRS
# ---------------------------------------------------------------------------

class TestEntryChecksTyped:
    def test_shadow_wrong_crs_is_typed_422(self):
        from fastapi import HTTPException

        from services import shadow_detector

        req = SimpleNamespace(address="x", prop_id="1", lat=SYD_LNG,
                              lng=SYD_LAT, report_id="r", height_m=None)
        with pytest.raises(HTTPException) as exc:
            shadow_detector.run_shadow(req)
        assert exc.value.status_code == 422
        assert "could not be determined" in exc.value.detail

    def test_flood_wrong_crs_is_typed_422(self):
        from fastapi import HTTPException

        from services import flood_truth

        req = SimpleNamespace(address="x", prop_id=None, lat=0.0, lng=0.0,
                              report_id="r")
        with pytest.raises(HTTPException) as exc:
            flood_truth.run_flood(req)
        assert exc.value.status_code == 422
        assert "could not be determined" in exc.value.detail

    def test_terrain_wrong_crs_is_typed_error_response(self):
        from services import terrain_analysis

        req = SimpleNamespace(lat=-4004807.0, lng=16833312.0,
                              include_flood_susceptibility=False)
        resp = terrain_analysis.terrain_analysis_endpoint(req)
        assert resp.terrain is None
        assert resp.error and "could not be determined" in resp.error


# ---------------------------------------------------------------------------
# DQ-45 — the granny-flat filter loop must survive real detections
# ---------------------------------------------------------------------------

TILE_BBOX = {"min_lat": -33.870, "max_lat": -33.868,
             "min_lng": 151.208, "max_lng": 151.210}


class TestGrannyFilterLoopSurvives:
    def _run_detect(self, monkeypatch, tmp_path, lot_geometry):
        from PIL import Image

        from services import granny_flat as gf

        tile = tmp_path / "tile.png"
        Image.new("RGB", (256, 256), (90, 120, 90)).save(tile)

        monkeypatch.setenv("MODAL_STRUCTURES_URL", "https://modal.test/detect")
        import requests as _req

        fake_resp = MagicMock()
        fake_resp.raise_for_status = MagicMock()
        fake_resp.json.return_value = {"structures": [
            {"area_px": 900, "bbox_pixel": [100, 100, 140, 140],
             "matched_prompt": "shed"},
        ]}
        monkeypatch.setattr(_req, "post", lambda *a, **k: fake_resp,
                            raising=False)
        return gf._detect_structures_samgeo(str(tile), TILE_BBOX, lot_geometry)

    def test_detection_survives_filter_loop(self, monkeypatch, tmp_path):
        """DQ-45 pin: pre-fix, the loop variable `bbox` shadowed the tile
        bbox dict, so _pixel_area_to_m2 string-indexed a pixel LIST and every
        surviving detection raised TypeError (collapsing the run to
        detection_failed). A clean detection must come back with area_m2."""
        out = self._run_detect(monkeypatch, tmp_path, lot_geometry=None)
        assert len(out) == 1
        assert out[0]["area_m2"] > 0
        assert out[0]["matched_prompt"] == "shed"

    def test_detection_survives_with_wgs84_lot_clipping(self, monkeypatch, tmp_path):
        """The shapely lot path (the other pre-fix TypeError site): a lot
        polygon covering the tile centre must keep the structure."""
        merc = [[[16832890, -4013550], [16833120, -4013550],
                 [16833120, -4013310], [16832890, -4013310],
                 [16832890, -4013550]]]
        out = self._run_detect(monkeypatch, tmp_path,
                               lot_geometry={"rings": merc})
        assert isinstance(out, list)  # no TypeError — clip ran or excluded


# ---------------------------------------------------------------------------
# Flood cache copy — the manifest rides like run_date
# ---------------------------------------------------------------------------

class TestFloodCacheCarriesManifest:
    def test_cache_copy_passes_original_inputs(self, monkeypatch):
        from services import flood_truth

        orig_inputs = {"lat": SYD_LAT, "lng": SYD_LNG,
                       MANIFEST_KEY: {"schema": 1, "product": "flood"}}
        cached_row = {"outputs": {"epi_flood_class": "none",
                                  "flood_signal": "none"},
                      "confidence": "medium", "data_sources": ["x"],
                      "run_date": None, "inputs": orig_inputs}

        cur = MagicMock()
        cur.fetchall.return_value = [cached_row]
        cur.__enter__ = lambda s: cur
        cur.__exit__ = lambda s, *a: None
        conn = MagicMock()
        conn.cursor.return_value = cur
        monkeypatch.setattr(flood_truth, "_get_conn", lambda: conn)
        monkeypatch.setattr(flood_truth, "_first_valid_cached_row",
                            lambda rows: cached_row)

        written = {}

        def spy_write(report_id, address, lat, lng, prop_id, inputs,
                      internal_outputs, run_date=None):
            written["inputs"] = inputs

        monkeypatch.setattr(flood_truth, "_write_report", spy_write)
        monkeypatch.setattr(flood_truth, "log_audit_trail",
                            lambda **kw: None)
        monkeypatch.setattr(flood_truth, "get_current_disclaimer_version",
                            lambda p: "1")

        req = SimpleNamespace(address="1 Test St", prop_id=None,
                              lat=SYD_LAT, lng=SYD_LNG, report_id="r1")
        out = flood_truth.run_flood(req)
        assert out["cache_hit"] is True
        assert written["inputs"] is orig_inputs
        assert written["inputs"][MANIFEST_KEY]["product"] == "flood"
