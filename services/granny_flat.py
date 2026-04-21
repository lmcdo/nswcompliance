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

SEPP Housing 2021 rules applied:
  - Min lot area: 450 m²
  - Max granny flat floor area: 60 m²
  - Setbacks: SEPP Housing defaults (rear 3m, side 0.9m)
"""

import base64
import json
import logging
import math
import os
import uuid
from datetime import date
from typing import Optional

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

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

# SEPP Housing 2021 defaults
SEPP_MIN_LOT_M2 = 450.0
SEPP_MAX_GF_AREA_M2 = 60.0

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
            px = (lng - bbox["min_lng"]) / (bbox["max_lng"] - bbox["min_lng"]) * w
            py = (bbox["max_lat"] - lat) / (bbox["max_lat"] - bbox["min_lat"]) * h
            px_ring.append((int(px), int(py)))
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

    structures = []
    for s in raw_structures:
        x1, y1, x2, y2 = s["bbox_pixel"]
        cx, cy = (x1 + x2) // 2, (y1 + y2) // 2
        if lot_arr is not None:
            h_arr, w_arr = lot_arr.shape
            centre_in = (0 <= cy < h_arr and 0 <= cx < w_arr and lot_arr[cy, cx])
            if not centre_in:
                # Fallback: accept if ≥40% of bbox overlaps lot (handles small
                # structures near boundary whose centroid may miss by a pixel).
                bx1 = max(0, x1); by1 = max(0, y1)
                bx2 = min(w_arr, x2); by2 = min(h_arr, y2)
                if bx2 <= bx1 or by2 <= by1:
                    continue
                bbox_region = lot_arr[by1:by2, bx1:bx2]
                if bbox_region.size == 0 or bbox_region.sum() / bbox_region.size < 0.40:
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
    if not lot_geometry or "rings" not in lot_geometry:
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


def _load_rental_data() -> dict:
    if not os.path.exists(RENTAL_DATA_PATH):
        return {}
    with open(RENTAL_DATA_PATH) as f:
        return json.load(f)


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
            "AI detected N structures, you confirmed N — counts agree."
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
            f"AI detected {samgeo_count} structure{'s' if samgeo_count != 1 else ''}, "
            f"you confirmed {confirmed_count} — counts agree. "
            "Rent estimate sourced from NSW Fair Trading bond data."
        )

    if not counts_agree and samgeo_count is not None:
        reason = (
            f"AI detected {samgeo_count} structure{'s' if samgeo_count != 1 else ''} "
            f"but you confirmed {confirmed_count}. "
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

    sepp_eligible = True
    sepp_ineligible_reason = None
    if lot_area_m2 is not None and lot_area_m2 < SEPP_MIN_LOT_M2:
        sepp_eligible = False
        sepp_ineligible_reason = (
            f"Lot area {lot_area_m2:.0f} m² is below the SEPP Housing 2021 "
            f"minimum of {SEPP_MIN_LOT_M2:.0f} m²"
        )

    tile_path = f"/tmp/gf_{req.prop_id}.png"
    try:
        tile_path, licence, bbox = fetch_tile_to_file(
            req.lat, req.lng, output_path=tile_path, grid=3
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Tile fetch failed: {e}")

    # Encode tile as base64 for frontend canvas rendering
    tile_b64: Optional[str] = None
    tile_width: Optional[int] = None
    tile_height: Optional[int] = None
    try:
        from PIL import Image as _PILImage
        with _PILImage.open(tile_path) as _img:
            tile_width, tile_height = _img.size
        with open(tile_path, "rb") as _f:
            tile_b64 = base64.b64encode(_f.read()).decode()
    except Exception as e:
        logger.warning(f"Tile encode failed: {e}")

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
        detect_id=detect_id,
        warnings=detect_warnings,
    )

    # When called via Trigger.dev (async path), write detect result to DB so
    # the frontend can poll granny_flat_reports by report_id.
    if req.report_id:
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
    granny_flat_buildable = True
    max_floor_area_m2 = SEPP_MAX_GF_AREA_M2

    if lot_area_m2 is not None and lot_area_m2 < SEPP_MIN_LOT_M2:
        granny_flat_buildable = False
        warnings.append(
            f"Lot area {lot_area_m2:.0f} m² is below the SEPP Housing 2021 minimum "
            f"of {SEPP_MIN_LOT_M2:.0f} m²"
        )

    is_heritage = bool(req.is_heritage)
    if is_heritage:
        warnings.append(
            "Property is in a Heritage Conservation Area or has a heritage listing. "
            "Granny flat construction may require heritage approval — confirm with council."
        )

    weekly_rent = _get_weekly_rent(req.postcode)
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

    if req.confirmed_structure_count >= 2:
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

    report_id = req.report_id or str(uuid.uuid4())

    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO granny_flat_reports
                    (id, product, address, lat, lng, prop_id, run_date,
                     inputs, outputs, confidence, data_sources)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
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
                        "postcode": req.postcode,
                    }),
                    psycopg2.extras.Json({
                        "granny_flat_buildable": granny_flat_buildable,
                        "max_floor_area_m2": max_floor_area_m2,
                        "estimated_weekly_rent_aud": weekly_rent,
                        "rental_yield_annual_pct": rental_yield_pct,
                        "assumed_build_cost_aud": assumed_build_cost,
                        "is_heritage": is_heritage,
                        "confidence_reason": confidence_reason,
                        "warnings": warnings,
                    }),
                    confidence,
                    data_sources,
                ),
            )
        conn.commit()
    except Exception as e:
        logger.error(f"DB write failed: {e}")
        warnings.append("Report could not be saved to database.")
    finally:
        try:
            conn.close()
        except Exception:
            pass

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
