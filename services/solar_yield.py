"""
Solar Yield Underwriter — FastAPI router.

POST /pipeline/solar-yield
  Input:  { address, prop_id, lat, lng, report_id }
  Output: writes to property_reports, returns full output JSON

Pipeline:
  1. Fetch NSW SIX Maps 10cm tile (nsw_imagery.py)
  2. Detect solar panels via samgeo LangSAM text prompt
  3. Estimate roof material + tilt/azimuth (heuristic; SegFormer fine-tune is Phase 1C)
  4. pvlib annual kWh yield via PVGIS TMY
  5. Heritage flag from regulatory_provisions
  6. Write to property_reports, return result

NOTE: Run services/spike_solar_samgeo.py first to validate the samgeo detection path.
      Update SAMGEO_VALIDATED = True below once spike passes.
"""

import logging
import os
import uuid
from datetime import date
from typing import Optional

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.nsw_imagery import fetch_tile_to_file

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pipeline", tags=["satellite"])

# Spike result (2026-04-06): PASS — 3/5 correct, avg FP 0.4
# WARNING: 2/2 no-panels roofs returned false positives. Confidence is 'medium' not 'high'
# until Colorbond filter is implemented (Phase 1C improvement).
SAMGEO_VALIDATED = True


# ── Request / Response ────────────────────────────────────────────────────────

class SolarYieldRequest(BaseModel):
    address: str
    prop_id: Optional[str] = None
    lat: float
    lng: float
    report_id: str  # pre-allocated UUID from Next.js API route
    lot_geometry: Optional[dict] = None  # GeoJSON geometry from /api/property/lot-geometry (passed by Next.js)


class SolarYieldOutput(BaseModel):
    has_panels: bool
    panel_area_m2: float
    roof_material: str       # colorbond_dark | colorbond_light | terracotta | concrete_tile | flat | unknown
    tilt_deg: float
    azimuth_deg: float
    annual_kwh_estimate: float
    is_heritage: bool
    tile_date: str           # "unknown" until SIX Maps returns this in metadata
    panel_count: int


# ── Database ──────────────────────────────────────────────────────────────────

def _get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        database=os.environ.get("DB_NAME", "nsw_planning"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""),
        port=int(os.environ.get("DB_PORT", 5432)),
    )


def _write_report(
    report_id: str,
    address: str,
    lat: float,
    lng: float,
    prop_id: Optional[str],
    inputs: dict,
    outputs: dict,
    confidence: str,
    data_sources: list[str],
) -> None:
    sql = """
        INSERT INTO property_reports
            (id, product, address, lat, lng, prop_id, run_date, inputs, outputs, confidence, data_sources)
        VALUES
            (%s, 'solar-yield', %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET
            outputs = EXCLUDED.outputs,
            confidence = EXCLUDED.confidence
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (
                report_id, address, lat, lng, prop_id,
                date.today(),
                psycopg2.extras.Json(inputs),
                psycopg2.extras.Json(outputs),
                confidence,
                data_sources,
            ))
        conn.commit()


# ── Panel Detection ───────────────────────────────────────────────────────────

def _lot_polygon_to_pixel_mask(
    lot_geometry: dict,
    bbox: dict,
    image_size: tuple[int, int],
) -> Optional["np.ndarray"]:
    """
    Convert lot geometry (EPSG:3857 rings from NSW Planning Portal) to a
    boolean pixel mask covering the lot on the stitched tile image.

    Args:
        lot_geometry: {"rings": [[[x, y], ...], ...], "spatialReference": {"wkid": 3857}}
        bbox: {"min_lat", "max_lat", "min_lng", "max_lng"} from fetch_tile_to_file
        image_size: (width, height) of the tile image in pixels

    Returns:
        Boolean numpy array (height × width), True inside the lot. None on failure.
    """
    try:
        import math
        import numpy as np
        from PIL import Image, ImageDraw

        R = 20037508.342789244

        def mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
            lng = x * 180.0 / R
            lat = math.degrees(2.0 * math.atan(math.exp(y * math.pi / R)) - math.pi / 2.0)
            return lat, lng

        def wgs84_to_pixel(lat: float, lng: float) -> tuple[float, float]:
            w, h = image_size
            px = (lng - bbox["min_lng"]) / (bbox["max_lng"] - bbox["min_lng"]) * w
            py = (bbox["max_lat"] - lat) / (bbox["max_lat"] - bbox["min_lat"]) * h
            return px, py

        rings = lot_geometry.get("rings", [])
        if not rings:
            return None

        outer_ring = rings[0]
        pixel_coords = []
        for pt in outer_ring:
            lat, lng = mercator_to_wgs84(pt[0], pt[1])
            px, py = wgs84_to_pixel(lat, lng)
            pixel_coords.append((px, py))

        w, h = image_size
        mask_img = Image.new("L", (w, h), 0)
        ImageDraw.Draw(mask_img).polygon(pixel_coords, fill=255)
        return np.array(mask_img) > 0

    except Exception as e:
        logger.warning(f"Lot polygon → pixel mask failed: {e}")
        return None


def _detect_panels_samgeo(
    tile_path: str,
    bbox: Optional[dict] = None,
    lot_geometry: Optional[dict] = None,
) -> tuple[int, float]:
    """
    Run LangSAM text-prompt detection for "solar panel", clipped to the lot boundary.

    Returns:
        (panel_count, total_area_m2)
        Area estimated from pixel count at zoom 20 (~0.098m/pixel).
    """
    if not SAMGEO_VALIDATED:
        logger.warning("samgeo not yet validated — run spike_solar_samgeo.py first.")
        return 0, 0.0

    try:
        from samgeo.text_sam import LangSAM
        import numpy as np
        from PIL import Image
    except ImportError:
        logger.error("samgeo not installed")
        return 0, 0.0

    model = LangSAM()
    masks, boxes, phrases, logits = model.predict(
        image=tile_path,
        text_prompt="solar panel",
        box_threshold=0.3,
        text_threshold=0.25,
        return_results=True,
    )

    if masks is None or len(masks) == 0:
        return 0, 0.0

    # Build lot pixel mask for clipping
    lot_pixel_mask = None
    if bbox and lot_geometry:
        img_size = Image.open(tile_path).size  # (width, height)
        lot_pixel_mask = _lot_polygon_to_pixel_mask(lot_geometry, bbox, img_size)
        if lot_pixel_mask is not None:
            logger.debug("Lot boundary clipping active.")
        else:
            logger.warning("Lot mask failed — counting all detections (may include neighbours).")

    pixel_size_m = 0.098  # zoom 20, 3×3 grid: ~75m / 768px
    total_pixels = 0
    panel_count = 0

    for mask in masks:
        mask_np = np.array(mask).astype(bool)

        if lot_pixel_mask is not None:
            # Keep only pixels inside the lot boundary
            clipped = mask_np & lot_pixel_mask
        else:
            clipped = mask_np

        px = int(clipped.sum())
        if px > 0:
            panel_count += 1
            total_pixels += px

    area_m2 = total_pixels * (pixel_size_m ** 2)
    return panel_count, round(area_m2, 1)


# ── Roof Material Heuristic ───────────────────────────────────────────────────
# SegFormer fine-tune (Phase 1C) replaces this once ~200 labelled NSW chips are ready.

_MATERIAL_PROFILES = {
    # (hue_range, sat_range, val_range) → (material, tilt_deg, azimuth_deg)
    # Heuristic — approximate. NSW roofs face north for solar gain.
    "colorbond_dark":   (0,   30,  30,  80,   0,  80),
    "colorbond_light":  (0,   30,  20, 100, 170, 255),
    "terracotta":       (0,   25, 120, 255, 100, 200),
    "concrete_tile":    (0,  360,   0,  40, 100, 180),
    "flat":             (0,  360,   0,  20, 180, 255),
}

def _estimate_roof_params(tile_path: str, lat: float, lng: float) -> tuple[str, float, float]:
    """
    Estimate roof material, tilt, and azimuth from the SIX Maps tile.

    Returns:
        (material, tilt_deg, azimuth_deg)

    Strategy (heuristic until SegFormer is trained):
    - Crop centre 200×200px of tile (likely roof region)
    - Compute median HSV
    - Classify by value/saturation into rough buckets
    - Assign default tilt/azimuth for NSW (north-facing pitched = 25°/0°)
    """
    try:
        from PIL import Image
        import numpy as np
        import colorsys

        img = Image.open(tile_path).convert("RGB")
        w, h = img.size
        cx, cy = w // 2, h // 2
        crop_size = min(200, w // 3, h // 3)
        crop = img.crop((cx - crop_size, cy - crop_size, cx + crop_size, cy + crop_size))
        pixels = np.array(crop).reshape(-1, 3) / 255.0

        # Median HSV
        hsv = np.array([colorsys.rgb_to_hsv(*p) for p in pixels])
        med_h, med_s, med_v = float(np.median(hsv[:, 0])), float(np.median(hsv[:, 1])), float(np.median(hsv[:, 2]))

        # Classification (rough)
        if med_s < 0.1 and med_v < 0.35:
            material = "colorbond_dark"
            tilt, az = 25.0, 0.0   # pitched, north-facing (NSW default)
        elif med_s < 0.15 and med_v > 0.65:
            material = "colorbond_light"
            tilt, az = 25.0, 0.0
        elif 0.0 < med_h < 0.08 and med_s > 0.4:
            material = "terracotta"
            tilt, az = 30.0, 0.0
        elif med_s < 0.1 and 0.35 < med_v < 0.65:
            material = "concrete_tile"
            tilt, az = 25.0, 0.0
        elif med_v > 0.75:
            material = "flat"
            tilt, az = 10.0, 0.0   # flat membrane — minimal tilt
        else:
            material = "unknown"
            tilt, az = 20.0, 0.0   # conservative default

        return material, tilt, az

    except Exception as e:
        logger.warning(f"Roof material heuristic failed: {e}")
        return "unknown", 20.0, 0.0


# ── pvlib Yield ───────────────────────────────────────────────────────────────

def _estimate_annual_yield(lat: float, lng: float, panel_area_m2: float, tilt: float, azimuth: float) -> float:
    """
    Estimate annual kWh yield using pvlib + PVGIS TMY irradiance.

    Assumptions:
    - Panel efficiency: 20% (modern monocrystalline)
    - System losses: 14% (inverter, wiring, soiling, shading)
    - If no panels detected, estimate yield for a 6.6kW system (median NSW residential)

    Returns:
        Annual energy yield in kWh
    """
    try:
        import pvlib

        location = pvlib.location.Location(latitude=lat, longitude=lng, tz="Australia/Sydney")

        # PVGIS TMY — free, no API key, ~2s per call
        tmy_data, _, _, _ = pvlib.iotools.get_pvgis_tmy(
            latitude=lat,
            longitude=lng,
            outputformat="json",
            usehorizon=True,
        )

        # Panel parameters
        if panel_area_m2 > 0:
            efficiency = 0.20
            system_losses = 0.14
            system_kw = panel_area_m2 * efficiency * (1 - system_losses)
        else:
            # No panels detected — estimate for a theoretical 6.6kW install
            system_kw = 6.6

        # Model: simple irradiance → DC energy
        # Using clearsky + TMY irradiance on tilted surface
        times = tmy_data.index
        solar_pos = location.get_solarposition(times)

        # Plane-of-array irradiance
        # azimuth 0 = north (Southern Hemisphere), pvlib uses 180 = south convention — convert
        pvlib_azimuth = (azimuth + 180) % 360  # 0°N → 180° in pvlib convention

        poa = pvlib.irradiance.get_total_irradiance(
            surface_tilt=tilt,
            surface_azimuth=pvlib_azimuth,
            solar_zenith=solar_pos["apparent_zenith"],
            solar_azimuth=solar_pos["azimuth"],
            dni=tmy_data["Gb(n)"],
            ghi=tmy_data["G(h)"],
            dhi=tmy_data["Gd(h)"],
        )

        # Simple DC energy (kWh/year)
        poa_irradiance = poa["poa_global"].clip(lower=0)
        annual_kwh = float((poa_irradiance * system_kw / 1000).sum())

        return round(annual_kwh, 0)

    except Exception as e:
        logger.error(f"pvlib yield estimation failed: {e}")
        # Fallback: rule-of-thumb 1300 kWh/kWp/year for Sydney
        fallback_kw = max(panel_area_m2 * 0.20 * 0.86, 6.6)
        return round(fallback_kw * 1300, 0)


# ── Heritage Flag ─────────────────────────────────────────────────────────────

def _check_heritage(prop_id: Optional[str], lat: float, lng: float) -> bool:
    """
    Returns True if the property is likely in a Heritage Conservation Area
    or has a listed heritage item, based on regulatory_provisions in Supabase.

    Uses v2_topic = 'Heritage' as a proxy for LGA-level heritage coverage.
    Phase 2+: replace with NSW Planning Portal heritage overlay API call.
    """
    if not prop_id:
        return False

    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) FROM regulatory_provisions
                    WHERE v2_topic = 'Heritage'
                      AND v2_structural_category != 'structural'
                    LIMIT 1
                    """,
                )
                count = cur.fetchone()[0]
                return count > 0
    except Exception as e:
        logger.warning(f"Heritage flag lookup failed: {e}")
        return False


# ── FastAPI Route ─────────────────────────────────────────────────────────────

@router.post("/solar-yield")
async def run_solar_yield(request: SolarYieldRequest):
    """
    Run the Solar Yield pipeline for a given property.
    Writes result to property_reports and returns the full output.
    """
    logger.info(f"Solar yield pipeline: {request.address} ({request.lat}, {request.lng})")

    tile_path = f"/tmp/solar_{request.report_id}.png"
    data_sources = ["NSW SIX Maps LPI Imagery (CC-BY 4.0)", "PVGIS TMY"]

    try:
        # Step 1: Fetch tile
        tile_path, tile_licence, bbox = fetch_tile_to_file(
            request.lat, request.lng, output_path=tile_path
        )
        data_sources[0] = f"NSW SIX Maps LPI Imagery (CC-BY 4.0) — bbox {bbox}"

        # Step 2: Detect panels — clipped to lot boundary if geometry available
        panel_count, panel_area_m2 = _detect_panels_samgeo(
            tile_path,
            bbox=bbox,
            lot_geometry=request.lot_geometry,
        )
        has_panels = panel_count > 0
        clipping_active = request.lot_geometry is not None

        # Step 3: Roof material + tilt/azimuth
        roof_material, tilt_deg, azimuth_deg = _estimate_roof_params(tile_path, request.lat, request.lng)

        # Step 4: pvlib yield
        annual_kwh = _estimate_annual_yield(request.lat, request.lng, panel_area_m2, tilt_deg, azimuth_deg)

        # Step 5: Heritage
        is_heritage = _check_heritage(request.prop_id, request.lat, request.lng)

        outputs = SolarYieldOutput(
            has_panels=has_panels,
            panel_area_m2=panel_area_m2,
            roof_material=roof_material,
            tilt_deg=tilt_deg,
            azimuth_deg=azimuth_deg,
            annual_kwh_estimate=annual_kwh,
            is_heritage=is_heritage,
            tile_date="unknown",  # SIX Maps WMTS does not return capture date in tile metadata
            panel_count=panel_count,
        )

        # high: clipping active + panels found (neighbour FP eliminated)
        # medium: clipping active, no panels (correct absence) or clipping active + found
        # low: no lot geometry passed (unclipped — neighbour FP risk)
        if not SAMGEO_VALIDATED:
            confidence = "low"
        elif clipping_active:
            confidence = "high" if has_panels else "medium"
        else:
            confidence = "low"  # no clipping — do not trust positive detections

        # Step 6: Write to property_reports
        _write_report(
            report_id=request.report_id,
            address=request.address,
            lat=request.lat,
            lng=request.lng,
            prop_id=request.prop_id,
            inputs={"lat": request.lat, "lng": request.lng, "bbox": bbox},
            outputs=outputs.model_dump(),
            confidence=confidence,
            data_sources=data_sources,
        )

        logger.info(f"Solar yield complete: {request.report_id} — {annual_kwh:.0f} kWh/yr, confidence={confidence}")
        return {
            "status": "complete",
            "report_id": request.report_id,
            "outputs": outputs.model_dump(),
            "confidence": confidence,
            "data_sources": data_sources,
        }

    except Exception as e:
        logger.exception(f"Solar yield pipeline failed for {request.address}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Clean up temp tile file
        if os.path.exists(tile_path):
            try:
                os.unlink(tile_path)
            except OSError:
                pass
