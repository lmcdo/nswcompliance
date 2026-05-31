"""
Granny Flat Yield Predictor -- FastAPI router.

POST /pipeline/granny-flat/detect
  Detect existing structures on lot, calculate buildable envelope.
  Returns detected footprints + yield estimate.
  Frontend shows footprints on aerial tile for user confirmation.

POST /pipeline/granny-flat/confirm
  User has confirmed/adjusted detected structures.
  Writes final report to granny_flat_reports.

Detection approach (3 improvements over baseline):
  1. Multi-prompt union: "building" + "shed" + "garage" — widens vocabulary so
     small outbuildings that "building" alone misses are still caught.
  2. IoU deduplication: two masks with IoU > 0.5 are the same structure; keep larger.
  3. Area filter: drop anything < MIN_STRUCTURE_AREA_M2 (15 m²) — removes pergolas,
     bins, paths. 15 m² = roughly a large carport. Configurable constant.

Confidence logic:
  "high"   — SAMGEO_VALIDATED + user confirmed same count as detection + rent data present
  "medium" — SAMGEO_VALIDATED + user adjusted count, OR rent data missing
  "low"    — SAMGEO_VALIDATED = False (pre-spike)

SEPP Housing 2021 rules applied (sourced from housing_sepp_standards table):
  - Min lot area: from DB (fallback 450 m²)
  - Max granny flat floor area: from DB (fallback 60 m²)
  - Setbacks: SEPP Housing defaults (rear 3m, side 0.9m)
"""

import base64
import json
import logging
import math
import os
import re
import uuid
from datetime import date
from typing import Optional

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from audit_trail import DataSourceQuery, log_audit_trail, get_current_disclaimer_version
from services.lga_lookup import lookup_lga

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# Spike result (2026-04-06): PASS — 7/11 correct, avg excess 0.27/lot
# Multi-prompt union brings expected improvement to ~9-10/11
SAMGEO_VALIDATED = True

# Prompts run in order; results unioned then deduplicated
DETECTION_PROMPTS = [
    ("building", 0.25, 0.20),  # (prompt, box_threshold, text_threshold)
    ("shed",     0.20, 0.18),  # lower thresholds for small structures
    ("garage",   0.20, 0.18),
]

# Drop any detected structure smaller than this after pixel→m² conversion.
# 15 m² ≈ a large carport. Filters out pergolas, bins, paths.
MIN_STRUCTURE_AREA_M2 = 15.0

# Upper bound: no single residential structure footprint exceeds this.
# Sydney's largest residential footprints are ~400–500 m². 600 gives headroom.
MAX_STRUCTURE_AREA_M2 = 600.0

# IoU threshold for deduplication: two masks covering >50% the same pixels = same structure
IOU_DEDUP_THRESHOLD = 0.5

# --- SAM quality filters (applied after lot clipping) ---
# Fill ratio: SAM mask pixels / bbox pixel area.
# A coherent building fills its bbox; a misfire (DINO returned whole-tile bbox,
# SAM found one small structure inside) has fill → 0.
# Backed by SpaceNet building detection, SAMGeo docs, Ecopia AI pipeline.
# Threshold: 0.15 (well below typical building fill of 0.40–0.85).
MIN_FILL_RATIO = 0.15

# Bbox fraction: bbox area / tile area.
# SpaceNet6 winners, Microsoft Building Footprints effective cap: 0.25–0.40.
# 0.35 allows for large houses while blocking tile-wide DINO misfires.
MAX_BBOX_FRACTION = 0.35

# Aspect ratio: longer side / shorter side of bbox.
# Buildings are roughly equidimensional. Values > 8 indicate fences, roads, errors.
MAX_ASPECT_RATIO = 8.0

# SEPP Housing 2021 fallbacks — used only when DB is unreachable.
# Authoritative source: housing_sepp_standards table (migration 045).
_SEPP_FALLBACK_MIN_LOT_M2 = 450.0
_SEPP_FALLBACK_MAX_GF_AREA_M2 = 60.0


def _get_sepp_sd_standards(conn=None) -> tuple[float, float]:
    """Load secondary dwelling SEPP standards from DB; fall back to hardcoded values.

    Returns (min_lot_m2, max_floor_area_m2).
    """
    if conn is None:
        logger.warning("SEPP standards: no DB connection, using fallback values (min_lot=%.0f, max_gf=%.0f)",
                        _SEPP_FALLBACK_MIN_LOT_M2, _SEPP_FALLBACK_MAX_GF_AREA_M2)
        return _SEPP_FALLBACK_MIN_LOT_M2, _SEPP_FALLBACK_MAX_GF_AREA_M2
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT standard_type, numeric_value
            FROM housing_sepp_standards
            WHERE development_type = 'secondary_dwelling'
              AND standard_type IN ('min_lot_size', 'max_floor_area')
            """,
        )
        rows = {r[0]: float(r[1]) for r in cur.fetchall()}
        cur.close()
        return (
            rows.get("min_lot_size", _SEPP_FALLBACK_MIN_LOT_M2),
            rows.get("max_floor_area", _SEPP_FALLBACK_MAX_GF_AREA_M2),
        )
    except Exception as e:
        logger.warning("Failed to load SEPP standards from DB, using fallback: %s", e)
        return _SEPP_FALLBACK_MIN_LOT_M2, _SEPP_FALLBACK_MAX_GF_AREA_M2

# NSW Planning Portal
NSW_API_BASE = "https://api.apps1.nsw.gov.au/planning"
NSW_HEADERS = {
    "Origin": "https://www.planningportal.nsw.gov.au",
    "Referer": "https://www.planningportal.nsw.gov.au/",
}

RENTAL_DATA_PATH = os.path.join(
    os.path.dirname(__file__), "data", "nsw_rental_by_postcode.json"
)


# ---------------------------------------------------------------------------
# DB
# ---------------------------------------------------------------------------

def _get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        return psycopg2.connect(dsn)
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        database=os.environ.get("DB_NAME", "nsw_planning"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""),
        port=int(os.environ.get("DB_PORT", 5432)),
    )


# ---------------------------------------------------------------------------
# DCP secondary dwelling setbacks
# ---------------------------------------------------------------------------

def _fetch_sd_setbacks(conn, lga_slug: Optional[str]) -> Optional[dict]:
    """
    Query dcp_setback_controls for secondary dwelling setbacks.
    Returns {sd_setbacks, dcp_name, dcp_url} or None.
    """
    if not lga_slug:
        return None
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT dev_type, control_type, value_min, value_max, unit,
                   condition, source_text, section_ref, applicability
            FROM dcp_setback_controls
            WHERE lga = %s AND is_current = TRUE
              AND (applicability = 'secondary_dwelling_specific'
                   OR dev_type = 'secondary_dwelling')
            ORDER BY
                CASE control_type
                    WHEN 'front_setback' THEN 0
                    WHEN 'side_setback'  THEN 1
                    WHEN 'rear_setback'  THEN 2
                    WHEN 'max_height'    THEN 3
                    ELSE 4
                END,
                value_min NULLS LAST
            """,
            (lga_slug,),
        )
        rows = cur.fetchall()

        cur.execute(
            """
            SELECT COALESCE(council_url, council_page_url)
            FROM dcp_chapter_registry
            WHERE council = %s AND is_active = TRUE
            ORDER BY updated_at DESC NULLS LAST
            LIMIT 1
            """,
            (lga_slug,),
        )
        reg = cur.fetchone()
    except Exception as e:
        logger.warning(f"DCP setback lookup failed: {e}")
        return None
    finally:
        if cur:
            cur.close()

    if not rows:
        return None

    _CONTROL_LABELS = {
        "front_setback": "Front setback",
        "side_setback": "Side setback",
        "rear_setback": "Rear setback",
        "max_height": "Max height",
        "wall_height": "Wall height",
        "max_site_coverage": "Max site coverage",
        "min_landscaped_area": "Min landscaped area",
    }

    sd_setbacks = []
    for dev_type, ctrl_type, vmin, vmax, unit, condition, source_text, section_ref, applicability in rows:
        label = _CONTROL_LABELS.get(ctrl_type, ctrl_type.replace("_", " ").title())
        if vmin is not None or vmax is not None:
            parts = []
            if vmin is not None:
                parts.append(f"{vmin:g} m minimum")
            if vmax is not None and vmax != vmin:
                parts.append(f"{vmax:g} m maximum")
            requirement = "; ".join(parts) if parts else f"{vmin or vmax:g} m"
        else:
            requirement = source_text or "Merit-based assessment — refer to DCP"

        sd_setbacks.append({
            "type": label,
            "requirement": requirement,
            "clause": section_ref or "",
            "notes": condition or "",
        })

    dcp_name = lga_slug.replace("_", " ").title() + " DCP"
    dcp_url = reg[0] if reg else None

    return {
        "sd_setbacks": sd_setbacks,
        "dcp_name": dcp_name,
        "dcp_url": dcp_url,
    }


# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class GrannyFlatDetectRequest(BaseModel):
    address: str
    prop_id: str
    lat: float
    lng: float
    lot_geometry: Optional[dict] = None  # EPSG:3857 rings from NSW Planning Portal
    report_id: Optional[str] = None      # pre-allocated UUID; when set, writes detect result to DB for async polling


class DetectedStructure(BaseModel):
    index: int
    area_px: int
    area_m2: Optional[float] = None
    bbox_pixel: list[int]   # [x0, y0, x1, y1]
    matched_prompt: str     # which prompt detected it: "building" | "shed" | "garage"
    is_main_dwelling: bool = False


class GrannyFlatDetectResponse(BaseModel):
    address: str
    lat: float
    lng: float
    prop_id: str
    lot_area_m2: Optional[float]
    sepp_eligible: bool
    sepp_ineligible_reason: Optional[str]
    detected_structures: list[DetectedStructure]
    samgeo_structure_count: int         # number detected by AI (used for confidence later)
    samgeo_validated: bool
    confirmation_required: bool
    tile_licence: str
    tile_b64: Optional[str] = None      # base64-encoded PNG aerial tile for frontend canvas
    tile_width: Optional[int] = None    # tile pixel dimensions for bbox_pixel scaling
    tile_height: Optional[int] = None
    tile_bbox: Optional[dict] = None    # geographic bounds: {min_lat, max_lat, min_lng, max_lng}
    lot_polygon_wgs84: Optional[list[list[list[float]]]] = None  # [[lng, lat], ...] rings in WGS84
    detect_id: str          # UUID for subsequent /confirm call
    warnings: list[str] = []


class GrannyFlatConfirmRequest(BaseModel):
    detect_id: str
    address: str
    prop_id: str
    lat: float
    lng: float
    lot_area_m2: Optional[float]
    confirmed_structure_count: int      # user-confirmed count
    samgeo_structure_count: Optional[int] = None  # echoed from detect response
    postcode: Optional[str] = None
    report_id: Optional[str] = None     # pre-allocated by Next.js
    is_heritage: Optional[bool] = None  # from NSW Planning Portal via Next.js
    existing_secondary_dwelling: Optional[bool] = None  # user self-report: is there already a granny flat on this lot?
    main_dwelling_area_m2: Optional[float] = None  # SAM-detected footprint of principal dwelling (is_main_dwelling=True)


class GrannyFlatConfirmResponse(BaseModel):
    report_id: str
    address: str
    granny_flat_buildable: bool
    max_floor_area_m2: float
    estimated_weekly_rent_aud: Optional[float]
    rental_yield_annual_pct: Optional[float]
    assumed_build_cost_aud: Optional[float]
    confidence: str
    confidence_reason: str              # human-readable explanation shown in UI
    data_sources: list[str]
    warnings: list[str]


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    R = 20037508.342789244
    lng = x * 180.0 / R
    lat = math.degrees(2.0 * math.atan(math.exp(y * math.pi / R)) - math.pi / 2.0)
    return lat, lng


def _mercator_rings_to_wgs84(rings: list) -> list[list[list[float]]]:
    """Convert Web Mercator polygon rings to WGS84 [[lng, lat], ...] rings (GeoJSON order)."""
    out = []
    for ring in rings:
        wgs_ring = []
        for x_merc, y_merc in ring:
            lat, lng = _mercator_to_wgs84(x_merc, y_merc)
            wgs_ring.append([lng, lat])
        out.append(wgs_ring)
    return out


def _mercator_rings_to_pixel_via_bbox(
    rings: list,
    bbox: dict,
    image_size: tuple[int, int],
) -> list[list[tuple[int, int]]]:
    """
    Convert Web Mercator polygon rings to pixel coords using tile bbox.
    Linear interpolation: more reliable than tile-index math.
    bbox keys: min_lat, max_lat, min_lng, max_lng (WGS84)
    """
    w, h = image_size
    pixel_rings = []
    for ring in rings:
        px_ring = []
        for x_merc, y_merc in ring:
            lat, lng = _mercator_to_wgs84(x_merc, y_merc)
            px_f = (lng - bbox["min_lng"]) / (bbox["max_lng"] - bbox["min_lng"]) * w
            py_f = (bbox["max_lat"] - lat) / (bbox["max_lat"] - bbox["min_lat"]) * h
            px_ring.append((round(px_f), round(py_f)))
        pixel_rings.append(px_ring)
    return pixel_rings


def _build_lot_arr(lot_pixel_rings, w: int, h: int):
    """Rasterise lot polygon rings into a boolean numpy array."""
    from PIL import Image, ImageDraw
    import numpy as np
    lot_img = Image.new("L", (w, h), 0)
    draw = ImageDraw.Draw(lot_img)
    for ring in lot_pixel_rings:
        if len(ring) >= 3:
            draw.polygon(ring, fill=255)
    return np.array(lot_img) > 0


def _pixel_area_to_m2(area_px: int, bbox: dict, image_w: int, image_h: int) -> float:
    """Convert pixel count to m² using tile bbox dimensions."""
    import math as _math
    # Approximate tile width/height in metres using Haversine
    lat_centre = (bbox["min_lat"] + bbox["max_lat"]) / 2
    R = 6371000.0
    lat_rad = _math.radians(lat_centre)
    lng_span = bbox["max_lng"] - bbox["min_lng"]
    lat_span = bbox["max_lat"] - bbox["min_lat"]
    width_m = _math.radians(lng_span) * R * _math.cos(lat_rad)
    height_m = _math.radians(lat_span) * R
    pixel_area_m2 = (width_m / image_w) * (height_m / image_h)
    return area_px * pixel_area_m2


# ---------------------------------------------------------------------------
# Multi-prompt detection
# ---------------------------------------------------------------------------

def _detect_structures_samgeo(
    tile_path: str,
    bbox: dict,
    lot_geometry: Optional[dict],
) -> list[dict]:
    """
    Detect buildings/sheds/garages via Modal GPU inference (LangSAM).

    Sends aerial tile as base64 to Modal endpoint. Modal runs multi-prompt
    LangSAM, IoU dedup, and area filter — returns clean structure list.

    Lot clipping: applied here after Modal returns, using bbox → pixel mapping.

    Returns list of dicts: {area_px, area_m2, bbox_pixel, matched_prompt}
    """
    import base64
    import requests as _req
    from PIL import Image

    modal_url = os.environ.get("MODAL_STRUCTURES_URL", "").strip()
    if not modal_url:
        raise RuntimeError("MODAL_STRUCTURES_URL not configured")

    try:
        with open(tile_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        resp = _req.post(
            modal_url,
            json={"image_b64": image_b64},
            timeout=150,
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception as e:
        logger.error(f"Modal detect-structures failed: {e}")
        return []

    raw_structures = result.get("structures", [])
    if not raw_structures:
        return []

    # Lot clipping: filter by bbox centre inside lot pixel mask
    img = Image.open(tile_path)
    w, h = img.size
    lot_arr = None
    if lot_geometry and "rings" in lot_geometry:
        rings_px = _mercator_rings_to_pixel_via_bbox(
            lot_geometry["rings"], bbox, (w, h)
        )
        lot_arr = _build_lot_arr(rings_px, w, h)

    # Build a Shapely lot polygon in WGS84 for geographic containment checks.
    # This is more reliable than pixel-space rasterisation, which can produce
    # a lot mask that is slightly offset from the visually rendered boundary.
    lot_shape_wgs84 = None
    if lot_geometry and "rings" in lot_geometry and lot_geometry["rings"]:
        try:
            from shapely.geometry import Polygon as _Polygon, MultiPolygon as _MultiPolygon
            wgs84_rings = _mercator_rings_to_wgs84(lot_geometry["rings"])
            if wgs84_rings:
                exterior = [(lng, lat) for lng, lat in wgs84_rings[0]]
                holes = [[(lng, lat) for lng, lat in r] for r in wgs84_rings[1:]]
                lot_shape_wgs84 = _Polygon(exterior, holes)
                if not lot_shape_wgs84.is_valid:
                    lot_shape_wgs84 = lot_shape_wgs84.buffer(0)
        except Exception as _e:
            logger.warning(f"Could not build lot Shapely polygon: {_e}")

    structures = []
    for s in raw_structures:
        bbox = s.get("bbox_pixel")
        if not bbox or len(bbox) != 4:
            logger.warning(f"Skipping structure with missing/malformed bbox_pixel: {s}")
            continue
        x1, y1, x2, y2 = bbox
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2

        if lot_shape_wgs84 is not None:
            # Convert structure bbox from pixel → WGS84 and compute the fraction
            # of its area that falls inside the lot polygon.
            # Accept if ≥50% of bbox area is inside the lot.
            # This correctly rejects neighbouring structures that merely clip
            # the lot boundary on one edge (e.g. 10-20% overlap), while
            # accepting genuine boundary-straddling sheds/garages (>50% inside).
            from shapely.geometry import Polygon as _BboxPoly
            lng1 = bbox["min_lng"] + (x1 / w) * (bbox["max_lng"] - bbox["min_lng"])
            lat1 = bbox["max_lat"] - (y1 / h) * (bbox["max_lat"] - bbox["min_lat"])
            lng2 = bbox["min_lng"] + (x2 / w) * (bbox["max_lng"] - bbox["min_lng"])
            lat2 = bbox["max_lat"] - (y2 / h) * (bbox["max_lat"] - bbox["min_lat"])
            struct_poly = _BboxPoly([(lng1, lat1), (lng2, lat1), (lng2, lat2), (lng1, lat2)])
            try:
                intersection_area = lot_shape_wgs84.intersection(struct_poly).area
                fraction_inside = intersection_area / struct_poly.area if struct_poly.area > 0 else 0.0
            except Exception:
                fraction_inside = 0.0
            if fraction_inside < 0.50:
                continue
        elif lot_arr is not None:
            # Pixel-space fallback if Shapely polygon failed to build.
            h_arr, w_arr = lot_arr.shape
            centre_in = (0 <= cy < h_arr and 0 <= cx < w_arr and lot_arr[cy, cx])
            if not centre_in:
                bx1 = max(0, x1); by1 = max(0, y1)
                bx2 = min(w_arr, x2); by2 = min(h_arr, y2)
                if bx2 <= bx1 or by2 <= by1:
                    continue
                bbox_region = lot_arr[by1:by2, bx1:bx2]
                if bbox_region.size == 0 or bbox_region.sum() / bbox_region.size < 0.60:
                    continue
        # --- SAM quality filters ---
        bw, bh = x2 - x1, y2 - y1

        # 1. Bbox fraction: DINO sometimes returns a whole-tile bbox for a
        #    low-confidence detection. Cap at 35% of tile area.
        #    (SpaceNet6 / Microsoft Building Footprints precedent: 0.25–0.40)
        bbox_fraction = (bw * bh) / (w * h)
        if bbox_fraction > MAX_BBOX_FRACTION:
            logger.warning(
                "Dropping detection: bbox covers %.1f%% of tile (max %.0f%%)",
                bbox_fraction * 100, MAX_BBOX_FRACTION * 100,
            )
            continue

        # 2. Fill ratio: mask pixels / bbox pixels.
        #    A real building fills its bbox coherently (typically 0.40–0.85).
        #    A misfire where DINO returned a huge bbox but SAM found one small
        #    structure inside will have fill → 0.
        #    Threshold: 0.15 (SpaceNet, SAMGeo, Ecopia AI precedent).
        bbox_area_px = max(bw * bh, 1)
        fill_ratio = s["area_px"] / bbox_area_px
        if fill_ratio < MIN_FILL_RATIO:
            logger.warning(
                "Dropping detection: fill ratio %.3f < %.2f (prompt=%s)",
                fill_ratio, MIN_FILL_RATIO, s["matched_prompt"],
            )
            continue

        # 3. Aspect ratio: elongated detections are fences/roads, not buildings.
        aspect_ratio = max(bw, bh) / max(min(bw, bh), 1)
        if aspect_ratio > MAX_ASPECT_RATIO:
            logger.warning(
                "Dropping detection: aspect ratio %.1f > %.0f",
                aspect_ratio, MAX_ASPECT_RATIO,
            )
            continue

        area_m2 = _pixel_area_to_m2(s["area_px"], bbox, w, h)
        if area_m2 < MIN_STRUCTURE_AREA_M2:
            continue
        if area_m2 > MAX_STRUCTURE_AREA_M2:
            logger.warning(
                "Dropping detection: area %.0f m² exceeds max %.0f m²",
                area_m2, MAX_STRUCTURE_AREA_M2,
            )
            continue
        structures.append({
            "area_px": s["area_px"],
            "area_m2": round(area_m2, 1),
            "bbox_pixel": s["bbox_pixel"],
            "matched_prompt": s["matched_prompt"],
        })

    return structures


# ---------------------------------------------------------------------------
# Other helpers
# ---------------------------------------------------------------------------

def _compute_lot_area_m2(lot_geometry: dict) -> Optional[float]:
    """Shoelace on EPSG:3857 rings, corrected for Mercator distortion (~1.45x at Sydney)."""
    if not lot_geometry or "rings" not in lot_geometry or not lot_geometry["rings"]:
        return None
    ring = lot_geometry["rings"][0]
    if len(ring) < 3:
        return None
    n = len(ring)
    area = 0.0
    for i in range(n):
        x1, y1 = ring[i][0], ring[i][1]
        x2, y2 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        area += x1 * y2 - x2 * y1
    projected = abs(area) / 2.0
    y_centre = sum(r[1] for r in ring) / n
    R = 20037508.342789244
    lat_rad = 2.0 * math.atan(math.exp(y_centre * math.pi / R)) - math.pi / 2.0
    return projected * (math.cos(lat_rad) ** 2)


def _fetch_lot_geometry(prop_id: str) -> Optional[dict]:
    import requests as _req
    try:
        resp = _req.get(
            f"{NSW_API_BASE}/viewersf/V1/ePlanningApi/lot",
            params={"propId": prop_id},
            headers=NSW_HEADERS,
            timeout=10,
        )
        resp.raise_for_status()
        lots = resp.json()
        if lots:
            return lots[0]["geometry"]
    except Exception as e:
        logger.warning(f"Lot geometry fetch failed for propId={prop_id}: {e}")
    return None


_RENTAL_DATA_CACHE: Optional[dict] = None


def _load_rental_data() -> dict:
    global _RENTAL_DATA_CACHE
    if _RENTAL_DATA_CACHE is not None:
        return _RENTAL_DATA_CACHE
    if not os.path.exists(RENTAL_DATA_PATH):
        _RENTAL_DATA_CACHE = {}
        return _RENTAL_DATA_CACHE
    with open(RENTAL_DATA_PATH) as f:
        _RENTAL_DATA_CACHE = json.load(f)
    return _RENTAL_DATA_CACHE


def _get_weekly_rent(postcode: Optional[str]) -> Optional[float]:
    if not postcode:
        return None
    entry = _load_rental_data().get(str(postcode))
    return entry.get("median_weekly_rent_1br_aud") if entry else None


def _compute_confidence(
    validated: bool,
    confirmed_count: int,
    samgeo_count: Optional[int],
    rent_available: bool,
) -> tuple[str, str]:
    """
    Returns (confidence, reason) tuple.

    high:   AI and user agree on structure count AND rent data present.
            "AI detected N structures on this lot."
    medium: AI and user disagree on count, OR rent data missing.
    low:    samgeo not validated (pre-spike).
    """
    if not validated:
        return (
            "low",
            "Aerial structure detection is in pre-validation mode. "
            "Manually verify structure count on SIX Maps before relying on this report."
        )

    counts_agree = (samgeo_count is not None and confirmed_count == samgeo_count)

    if counts_agree and rent_available:
        return (
            "high",
            f"AI detected {samgeo_count} structure{'s' if samgeo_count != 1 else ''} on this lot. "
            "Rent estimate sourced from NSW Fair Trading bond data."
        )

    if not counts_agree and samgeo_count is not None:
        reason = (
            f"AI detected {samgeo_count} structure{'s' if samgeo_count != 1 else ''} "
            f"but {confirmed_count} {'was' if confirmed_count == 1 else 'were'} confirmed. "
        )
    else:
        reason = "Structure count entered manually (aerial detection not available). "

    if not rent_available:
        reason += "Rent estimate unavailable for this postcode."

    return "medium", reason.strip()


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/granny-flat/detect", response_model=GrannyFlatDetectResponse)
def detect_structures(req: GrannyFlatDetectRequest):
    """
    Step 1: detect structures on lot via multi-prompt LangSAM, return for user confirmation.
    """
    try:
        from services.nsw_imagery import fetch_tile_to_file
    except ImportError:
        from nsw_imagery import fetch_tile_to_file

    lot_geometry = req.lot_geometry or _fetch_lot_geometry(req.prop_id)
    lot_area_m2 = _compute_lot_area_m2(lot_geometry) if lot_geometry else None

    # Load SEPP standards from DB (with fallback)
    _detect_conn = None
    try:
        _detect_conn = _get_conn()
        sepp_min_lot, _sepp_max_gf = _get_sepp_sd_standards(_detect_conn)
    except Exception:
        sepp_min_lot, _sepp_max_gf = _get_sepp_sd_standards()
    finally:
        if _detect_conn:
            _detect_conn.close()

    sepp_eligible = True
    sepp_ineligible_reason = None
    if lot_area_m2 is not None and lot_area_m2 < sepp_min_lot:
        sepp_eligible = False
        sepp_ineligible_reason = (
            f"Lot area {lot_area_m2:.0f} m² is below the SEPP Housing 2021 "
            f"minimum of {sepp_min_lot:.0f} m²"
        )

    # Sanitize prop_id to prevent path traversal (prop_ids are numeric, but be defensive)
    safe_prop_id = "".join(c for c in req.prop_id if c.isalnum() or c in ("-", "_"))
    tile_path = f"/tmp/gf_{safe_prop_id}.png"
    try:
        tile_path, licence, bbox = fetch_tile_to_file(
            req.lat, req.lng, output_path=tile_path, grid=3
        )
    except Exception as e:
        # Write error state to DB so the frontend poll resolves immediately
        if req.report_id:
            _err_conn = None
            try:
                _err_conn = _get_conn()
                with _err_conn.cursor() as _cur:
                    _cur.execute(
                        """
                        INSERT INTO granny_flat_reports
                            (id, product, address, lat, lng, prop_id, run_date, confidence, outputs)
                        VALUES (%s, 'granny-flat', %s, %s, %s, %s, %s, 'error', %s)
                        ON CONFLICT (id) DO UPDATE SET
                            confidence = 'error',
                            outputs = EXCLUDED.outputs
                        """,
                        (
                            req.report_id,
                            req.address,
                            req.lat,
                            req.lng,
                            req.prop_id,
                            date.today().isoformat(),
                            psycopg2.extras.Json({"error": f"Tile fetch failed: {e}"}),
                        ),
                    )
                _err_conn.commit()
            except Exception:
                pass
            finally:
                try:
                    _err_conn.close()
                except Exception:
                    pass
        raise HTTPException(status_code=502, detail=f"Tile fetch failed: {e}")

    tile_b64: Optional[str] = None
    tile_width: Optional[int] = None
    tile_height: Optional[int] = None
    try:
        from PIL import Image as _PILImage
        with _PILImage.open(tile_path) as _img:
            tile_width, tile_height = _img.size
    except Exception as e:
        logger.warning(f"Tile size read failed: {e}")

    detect_warnings: list[str] = []
    detected_structures: list[DetectedStructure] = []
    if SAMGEO_VALIDATED:
        try:
            raw = _detect_structures_samgeo(tile_path, bbox, lot_geometry)
            for i, s in enumerate(raw):
                detected_structures.append(DetectedStructure(
                    index=i,
                    area_px=s["area_px"],
                    area_m2=s["area_m2"],
                    bbox_pixel=s["bbox_pixel"],
                    matched_prompt=s["matched_prompt"],
                    is_main_dwelling=False,
                ))
            if detected_structures:
                largest = max(range(len(detected_structures)), key=lambda i: detected_structures[i].area_m2 or 0)
                detected_structures[largest].is_main_dwelling = True
        except RuntimeError:
            detect_warnings.append(
                "Aerial structure detection unavailable (MODAL_STRUCTURES_URL not configured). "
                "Enter structure count manually."
            )
        except Exception as e:
            logger.error(f"samgeo detection failed: {e}")
            detect_warnings.append(
                "Aerial structure detection failed — enter structure count manually."
            )

    # Annotate tile with lot boundary + structure boxes, then encode as base64.
    # Uses the same bbox_pixel values the frontend canvas draws — no re-projection needed
    # for structures. Lot polygon uses linear WGS84 → pixel projection via tile_bbox.
    try:
        from PIL import Image as _PILImage, ImageDraw as _ImageDraw
        import io as _io

        with _PILImage.open(tile_path) as _img:
            _img = _img.convert("RGBA")
            _draw = _ImageDraw.Draw(_img, "RGBA")
            tw, th = _img.size

            def _wgs84_to_px(lat: float, lng: float) -> tuple[int, int]:
                px = int((lng - bbox["min_lng"]) / (bbox["max_lng"] - bbox["min_lng"]) * tw)
                py = int((bbox["max_lat"] - lat) / (bbox["max_lat"] - bbox["min_lat"]) * th)
                return px, py

            # Draw lot boundary (teal outline)
            # _mercator_rings_to_wgs84 returns list of rings [[lng, lat], ...]
            lot_rings = (
                _mercator_rings_to_wgs84(lot_geometry["rings"])
                if lot_geometry and "rings" in lot_geometry and lot_geometry["rings"]
                else None
            )
            if lot_rings:
                ring = lot_rings[0]  # exterior boundary
                pts = [_wgs84_to_px(lat, lng) for lng, lat in ring]
                _draw.line(pts + [pts[0]], fill=(15, 118, 110, 220), width=3)

            # Draw structure bounding boxes
            MAIN_COL = (239, 68, 68, 200)    # red — main dwelling
            OTHER_COL = (250, 204, 21, 200)  # yellow — outbuildings
            for s in detected_structures:
                x0, y0, x1, y1 = s.bbox_pixel
                col = MAIN_COL if s.is_main_dwelling else OTHER_COL
                _draw.rectangle([x0, y0, x1, y1], outline=col, width=2)

            # Re-encode as PNG bytes → base64
            _buf = _io.BytesIO()
            _img.convert("RGB").save(_buf, format="PNG")
            tile_b64 = base64.b64encode(_buf.getvalue()).decode()
    except Exception as e:
        logger.warning(f"Tile annotation failed, falling back to raw tile: {e}")
        try:
            with open(tile_path, "rb") as _f:
                tile_b64 = base64.b64encode(_f.read()).decode()
        except Exception:
            pass

    detect_id = str(uuid.uuid4())
    response = GrannyFlatDetectResponse(
        address=req.address,
        lat=req.lat,
        lng=req.lng,
        prop_id=req.prop_id,
        lot_area_m2=round(lot_area_m2, 1) if lot_area_m2 else None,
        sepp_eligible=sepp_eligible,
        sepp_ineligible_reason=sepp_ineligible_reason,
        detected_structures=detected_structures,
        samgeo_structure_count=len(detected_structures),
        samgeo_validated=SAMGEO_VALIDATED,
        confirmation_required=True,
        tile_licence=licence,
        tile_b64=tile_b64,
        tile_width=tile_width,
        tile_height=tile_height,
        tile_bbox=bbox if bbox else None,
        lot_polygon_wgs84=(
            _mercator_rings_to_wgs84(lot_geometry["rings"])
            if lot_geometry and "rings" in lot_geometry and lot_geometry["rings"]
            else None
        ),
        detect_id=detect_id,
        warnings=detect_warnings,
    )

    # When called via Trigger.dev (async path), write detect result to DB so
    # the frontend can poll granny_flat_reports by report_id.
    if req.report_id:
        conn = None
        try:
            conn = _get_conn()
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO granny_flat_reports
                        (id, product, address, lat, lng, prop_id, run_date, confidence, outputs)
                    VALUES (%s, 'granny-flat', %s, %s, %s, %s, %s, 'pending_confirm', %s)
                    ON CONFLICT (id) DO UPDATE SET
                        outputs = EXCLUDED.outputs,
                        confidence = EXCLUDED.confidence
                    """,
                    (
                        req.report_id,
                        req.address,
                        req.lat,
                        req.lng,
                        req.prop_id,
                        date.today().isoformat(),
                        psycopg2.extras.Json(response.model_dump()),
                    ),
                )
            conn.commit()
        except Exception as e:
            logger.error(f"Detect DB write failed: {e}")
        finally:
            try:
                conn.close()
            except Exception:
                pass

    return response


@router.post("/granny-flat/confirm", response_model=GrannyFlatConfirmResponse)
def confirm_and_calculate(req: GrannyFlatConfirmRequest):
    """
    Step 2: user confirmed structure count. Calculate yield, assign confidence, write report.
    """
    warnings: list[str] = []
    data_sources = [
        "CC-BY 4.0 NSW Government — Six Maps LPI Imagery",
        "SEPP Housing 2021",
    ]

    lot_area_m2 = req.lot_area_m2
    # If Next.js couldn't compute lot area (lot geometry unavailable during confirm call),
    # fall back to fetching it directly from the NSW Planning Portal here.
    if lot_area_m2 is None and req.prop_id:
        _fallback_geom = _fetch_lot_geometry(req.prop_id)
        if _fallback_geom:
            lot_area_m2 = _compute_lot_area_m2(_fallback_geom)

    # Load SEPP standards from DB (with fallback)
    _confirm_conn = None
    try:
        _confirm_conn = _get_conn()
        sepp_min_lot, sepp_max_gf = _get_sepp_sd_standards(_confirm_conn)
    except Exception:
        sepp_min_lot, sepp_max_gf = _get_sepp_sd_standards()
    finally:
        if _confirm_conn:
            _confirm_conn.close()

    granny_flat_buildable = True
    max_floor_area_m2 = sepp_max_gf

    if lot_area_m2 is None:
        warnings.append(
            f"Lot area could not be calculated for this property — lot geometry was unavailable. "
            f"The {sepp_min_lot:.0f} m² minimum under SEPP Housing 2021 (cl 53) could not be verified. "
            f"Confirm lot area on NSW Planning Portal before proceeding."
        )
    elif lot_area_m2 < sepp_min_lot:
        granny_flat_buildable = False
        warnings.append(
            f"Lot area {lot_area_m2:.0f} m² is below the SEPP Housing 2021 minimum "
            f"of {sepp_min_lot:.0f} m²"
        )

    # Residual area proxy check — simple heuristic pending full geometric envelope computation.
    # Rationale: a CDC granny flat needs ≥60 m² floor area (SEPP Housing 2021 cl 4.18) plus
    # clearances: 3 m rear setback + 0.9 m each side + 3 m separation from principal dwelling.
    # For a typical 10 m-wide lot rear yard that buffer alone consumes ~50–60 m² of ground.
    # Threshold 120 m² = 60 m² GF footprint + ~60 m² setback/circulation buffer.
    # Only fires when SAM returned a reliable main dwelling area.
    #
    # TODO — full geometric envelope check (v2):
    #   1. Reproject lot_polygon_wgs84 to a local UTM zone (e.g. GDA2020 / MGA Zone 55 for Sydney).
    #   2. Identify street frontage edge = longest polygon side within 20 m of nearest road centreline
    #      (use OSM road layer or lot centroid + bearing heuristic as fallback).
    #   3. Rear boundary = opposite edge to frontage.
    #   4. Apply inward offsets: rear −3 m, each side −0.9 m → buildable lot polygon.
    #   5. Subtract principal dwelling polygon (from SAM mask contour, not bbox) buffered 3 m.
    #   6. Compute area of remaining buildable polygon.
    #   7. If area < 60 m²: not buildable. If 60–80 m²: buildable but tight (warn).
    #   8. For the 12 LGAs in dcp_setback_controls: query table for council-specific rear/side
    #      setbacks and substitute SEPP defaults above.
    #   Data needed: lot polygon in UTM, SAM mask contour (not bbox), road centreline layer.
    if (
        granny_flat_buildable
        and lot_area_m2 is not None
        and req.main_dwelling_area_m2 is not None
        and req.main_dwelling_area_m2 > 0
    ):
        if req.main_dwelling_area_m2 >= lot_area_m2:
            granny_flat_buildable = False
            warnings.append(
                f"Detected dwelling footprint (~{req.main_dwelling_area_m2:.0f} m²) exceeds "
                f"lot area ({lot_area_m2:.0f} m²) — likely a detection error. "
                f"Confirm dwelling footprint manually and re-run."
            )
            residual_area_m2 = 0.0
        else:
            residual_area_m2 = lot_area_m2 - req.main_dwelling_area_m2
        if residual_area_m2 < 120:
            granny_flat_buildable = False
            warnings.append(
                f"Insufficient space for a complying development granny flat. "
                f"After the principal dwelling footprint (~{req.main_dwelling_area_m2:.0f} m²), "
                f"approximately {residual_area_m2:.0f} m² remains — less than the ~120 m² "
                f"needed for a 60 m² secondary dwelling plus SEPP Housing 2021 setbacks "
                f"(3 m rear, 0.9 m sides, 3 m from dwelling). "
                f"A DA pathway may allow a smaller or differently positioned structure — "
                f"consult a town planner."
            )

    is_heritage = bool(req.is_heritage)
    if is_heritage:
        warnings.append(
            "Property is in a Heritage Conservation Area or has a heritage listing. "
            "Granny flat construction may require heritage approval — confirm with council."
        )

    # SEPP Housing 2021 cl 53(1): only one secondary dwelling per lot.
    if req.existing_secondary_dwelling is True:
        granny_flat_buildable = False
        warnings.append(
            "A secondary dwelling already exists on this lot. SEPP Housing 2021 (cl 53(1)) "
            "permits only one secondary dwelling per lot — a second granny flat cannot be approved."
        )

    # Conservative gate: when ≥2 secondary structures are detected and the user has not
    # confirmed whether any of them is an existing secondary dwelling, we cannot safely
    # assert eligibility. With 2 secondary structures the probability that at least one is
    # already a secondary dwelling is high. Block and require human verification.
    if (
        granny_flat_buildable
        and req.confirmed_structure_count >= 3  # 1 main + 2 secondary = 3 total
        and req.existing_secondary_dwelling is None
    ):
        granny_flat_buildable = False
        warnings.append(
            "MULTIPLE_SECONDARY_STRUCTURES: Two or more secondary structures were detected on "
            "this lot. SEPP Housing 2021 (cl 53(1)) permits only one secondary dwelling per lot. "
            "Eligibility cannot be confirmed without knowing whether either existing structure is "
            "already classified as a secondary dwelling. A town planner or private certifier can "
            "confirm the current status before you proceed."
        )

    # Resolve postcode — prefer explicit field, fall back to last 4 digits of address
    postcode = req.postcode
    if not postcode and req.address:
        m = re.search(r'\b(\d{4})\s*$', req.address.strip())
        if m:
            postcode = m.group(1)

    weekly_rent = _get_weekly_rent(postcode)
    annual_rent = weekly_rent * 52 if weekly_rent else None

    build_cost_per_m2 = 2500.0
    assumed_build_cost = round(max_floor_area_m2 * build_cost_per_m2) if granny_flat_buildable else None
    if assumed_build_cost:
        data_sources.append("Build cost estimate: $2,500/m² (conservative NSW residential, 2026)")

    rental_yield_pct = None
    if annual_rent and assumed_build_cost:
        rental_yield_pct = round((annual_rent / assumed_build_cost) * 100, 2)
        data_sources.append("NSW Fair Trading Rental Bond Data (2025 annual)")

    if not weekly_rent:
        warnings.append(
            "Rental data not available for this postcode. "
            "Run services/scripts/update_rental_data.py to populate."
        )

    # Only show generic "verify outbuilding" warning if user hasn't already answered
    # the secondary dwelling question, and we haven't already blocked above.
    # If they said True, we've already blocked buildability.
    # If they said False, no ambiguity. Only warn when None (not asked / not answered).
    if (
        req.confirmed_structure_count == 2  # exactly 1 secondary structure — ambiguous but not blocked
        and req.existing_secondary_dwelling is None
    ):
        warnings.append(
            "Existing outbuilding detected. Granny flat approval depends on whether "
            "the existing structure is already an ancillary dwelling — verify with council."
        )

    confidence, confidence_reason = _compute_confidence(
        validated=SAMGEO_VALIDATED,
        confirmed_count=req.confirmed_structure_count,
        samgeo_count=req.samgeo_structure_count,
        rent_available=weekly_rent is not None,
    )

    # Cap confidence to medium when key eligibility inputs are unknown.
    # Both conditions are checked independently against "high" (not sequentially)
    # so that both warnings are surfaced even if both apply.
    cap_reasons = []
    if lot_area_m2 is None:
        cap_reasons.append("Lot area could not be verified — eligibility is unconfirmed.")
    if req.existing_secondary_dwelling is None and req.confirmed_structure_count >= 2:
        cap_reasons.append(
            "Eligibility is capped because the status of one or more existing secondary "
            "structures on this lot could not be confirmed. NSW planning rules only allow one "
            "secondary dwelling per lot."
        )
    if cap_reasons and confidence == "high":
        confidence = "medium"
        confidence_reason += " " + " ".join(cap_reasons)

    report_id = req.report_id or str(uuid.uuid4())

    # --- LGA lookup + DCP secondary dwelling setbacks ---
    lga_info = {"lga_name": None, "lga_slug": None, "has_dcp_setbacks": False}
    dcp_sd_data: Optional[dict] = None

    conn = None
    try:
        conn = _get_conn()

        # Resolve LGA from coordinates
        lga_info = lookup_lga(req.lat, req.lng, conn, address=req.address)
        if lga_info["has_dcp_setbacks"]:
            dcp_sd_data = _fetch_sd_setbacks(conn, lga_info["lga_slug"])
            if dcp_sd_data and dcp_sd_data["sd_setbacks"]:
                data_sources.append(
                    f"DCP secondary dwelling setbacks: {dcp_sd_data['dcp_name']}"
                )

        with conn.cursor() as cur:
            # Carry tile_b64 forward from the detect outputs so the PDF can render
            # the aerial image. The detect step stores it in outputs JSONB; the
            # confirm step overwrites outputs, so we must read it before writing.
            tile_b64: Optional[str] = None
            if req.report_id:
                cur.execute(
                    "SELECT outputs->>'tile_b64' FROM granny_flat_reports WHERE id = %s",
                    (req.report_id,),
                )
                row = cur.fetchone()
                if row:
                    tile_b64 = row[0]  # None if key absent or value null

            cur.execute(
                """
                INSERT INTO granny_flat_reports
                    (id, product, address, lat, lng, prop_id, run_date,
                     inputs, outputs, confidence, data_sources)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    inputs = EXCLUDED.inputs,
                    outputs = EXCLUDED.outputs,
                    confidence = EXCLUDED.confidence,
                    data_sources = EXCLUDED.data_sources
                """,
                (
                    report_id,
                    "granny-flat",
                    req.address,
                    req.lat,
                    req.lng,
                    req.prop_id,
                    date.today().isoformat(),
                    psycopg2.extras.Json({
                        "lot_area_m2": lot_area_m2,
                        "confirmed_structure_count": req.confirmed_structure_count,
                        "samgeo_structure_count": req.samgeo_structure_count,
                        "postcode": postcode,
                        "existing_secondary_dwelling": req.existing_secondary_dwelling,
                        "main_dwelling_area_m2": req.main_dwelling_area_m2,
                    }),
                    psycopg2.extras.Json({
                        "granny_flat_buildable": granny_flat_buildable,
                        "max_floor_area_m2": max_floor_area_m2,
                        "estimated_weekly_rent_aud": weekly_rent,
                        "rental_yield_annual_pct": rental_yield_pct,
                        "assumed_build_cost_aud": assumed_build_cost,
                        "is_heritage": is_heritage,
                        "confidence": confidence,
                        "confidence_reason": confidence_reason,
                        "warnings": warnings,
                        "data_sources": data_sources,
                        "tile_b64": tile_b64,
                        "lga_name": lga_info["lga_name"],
                        "lga_slug": lga_info["lga_slug"],
                        "dcp_sd_setbacks": dcp_sd_data["sd_setbacks"] if dcp_sd_data else None,
                        "dcp_name": dcp_sd_data["dcp_name"] if dcp_sd_data else None,
                        "dcp_url": dcp_sd_data["dcp_url"] if dcp_sd_data else None,
                    }),
                    confidence,
                    data_sources,
                ),
            )
        conn.commit()
    except Exception as e:
        logger.error(f"DB write failed: {e}")
        raise HTTPException(status_code=503, detail="Failed to save report — please retry")
    finally:
        try:
            conn.close()
        except Exception:
            pass

    # Audit trail (non-blocking — won't prevent report delivery on failure)
    ds_samgeo = DataSourceQuery(
        "SAM segmentation (LangSAM via Modal)",
        os.environ.get("MODAL_STRUCTURES_URL", "modal:detect-structures"),
        {"lat": req.lat, "lng": req.lng, "prop_id": req.prop_id},
    )
    ds_samgeo.record_response(
        {"structure_count": req.confirmed_structure_count},
        features_returned=req.confirmed_structure_count,
    )

    ds_aerial = DataSourceQuery(
        "NSW SIX Maps LPI Imagery",
        "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Imagery/MapServer",
        {"lat": req.lat, "lng": req.lng},
    )
    ds_aerial.record_response({"tile": "fetched"}, features_returned=1)

    ds_sepp = DataSourceQuery(
        "SEPP Housing 2021 rules",
        "db:housing_sepp_standards",
        {"min_lot_m2": sepp_min_lot, "max_gf_area_m2": sepp_max_gf},
    )
    ds_sepp.record_response(
        {"eligible": granny_flat_buildable, "max_floor_area_m2": max_floor_area_m2},
        features_returned=1,
    )

    ds_zone_heritage = DataSourceQuery(
        "NSW Planning Portal zone/heritage lookup",
        f"{NSW_API_BASE}/viewersf/V1/ePlanningApi/lot",
        {"prop_id": req.prop_id, "is_heritage": is_heritage},
    )
    ds_zone_heritage.record_response(
        {"is_heritage": is_heritage},
        features_returned=1 if req.prop_id else 0,
    )

    audit_data_sources = [ds_samgeo, ds_aerial, ds_sepp, ds_zone_heritage]

    outputs_for_audit = {
        "granny_flat_buildable": granny_flat_buildable,
        "max_floor_area_m2": max_floor_area_m2,
        "estimated_weekly_rent_aud": weekly_rent,
        "rental_yield_annual_pct": rental_yield_pct,
        "assumed_build_cost_aud": assumed_build_cost,
        "confidence": confidence,
    }

    log_audit_trail(
        report_id=report_id,
        pipeline_name="granny-flat",
        input_params={
            "address": req.address,
            "lat": req.lat,
            "lng": req.lng,
            "prop_id": req.prop_id,
            "lot_area_m2": lot_area_m2,
            "confirmed_structure_count": req.confirmed_structure_count,
            "samgeo_structure_count": req.samgeo_structure_count,
            "postcode": postcode,
            "existing_secondary_dwelling": req.existing_secondary_dwelling,
        },
        data_sources=audit_data_sources,
        output_summary=outputs_for_audit,
        disclaimer_version=get_current_disclaimer_version("granny-flat"),
        intermediate_calculations={
            "lot_area_m2": lot_area_m2,
            "max_buildable_m2": max_floor_area_m2,
            "structure_count": req.confirmed_structure_count,
            "eligible": granny_flat_buildable,
            "is_heritage": is_heritage,
            "residual_area_m2": (
                round(lot_area_m2 - req.main_dwelling_area_m2, 1)
                if lot_area_m2 is not None and req.main_dwelling_area_m2 is not None
                else None
            ),
            "weekly_rent": weekly_rent,
        },
    )

    return GrannyFlatConfirmResponse(
        report_id=report_id,
        address=req.address,
        granny_flat_buildable=granny_flat_buildable,
        max_floor_area_m2=max_floor_area_m2,
        estimated_weekly_rent_aud=weekly_rent,
        rental_yield_annual_pct=rental_yield_pct,
        assumed_build_cost_aud=assumed_build_cost,
        confidence=confidence,
        confidence_reason=confidence_reason,
        data_sources=data_sources,
        warnings=warnings,
    )
