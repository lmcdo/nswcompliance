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

Review state (what SERVED SURFACES show since 2026-08-06) — see ReviewState:
  Reports say what happened to the structure list, not how good they are.
  reviewed / scan_only_found / scan_only_none_found / scan_inconclusive /
  not_assessed. A scan that found nothing has been checked against nothing,
  so it is an unverified result, not a middling one — grading it "medium"
  was the defect (user ruling 2026-08-06).

`confidence` (high/medium/low) is now INTERNAL. It is still computed, still
stored, and still the job state machine for the column
(NULL -> pending_confirm -> high|medium|low|error), and
/api/reports/granny-flat/nearby still filters comparables on 'high'. It is no
longer rendered on any served surface. Its logic:
  "high"   — SAMGEO_VALIDATED + a PERSON classified every detected structure
             (inputs.confirmed_count_source = 'secondary_detections_classified'), the
             resulting total matches the detector, + rent data present.
             It does NOT mean the total was checked against the world: no
             surface lets anyone report a structure the detector MISSED, and
             detection recall is unmeasured until check GF-1 runs.
  "medium" — anything else that ran, including the detector agreeing with itself
  "low"    — SAMGEO_VALIDATED = False (pre-spike); unreachable while the
             module constant is True — 0 rows of 87 carry it.
  Before 2026-08-06 "high" needed only count equality, and the count was seeded
  from the detector and not editable — so "high" was self-agreement. See
  _compute_confidence for the measurement.

SEPP Housing 2021 rules applied (sourced from housing_sepp_standards table):
  - Min lot area: from DB only — no fallback (#817); unavailable → 503
  - Max granny flat floor area: from DB only — no fallback (#817); unavailable → 503
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
from typing import Literal, Optional

import psycopg2
import psycopg2.extras
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, StrictInt, model_validator

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

# Algorithm revision for execution manifests (campaign item 4): tile fetch +
# LangSAM multi-prompt detection + SAM quality filters + SEPP screen. Bump on
# method change, not per deploy (deploy identity = manifest deploy_sha).
ALGORITHM_VERSION = "granny-langsam-detect-1.0"

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

# SEPP Housing 2021 fallback constants intentionally removed (#817) — same
# defect class as the conveyancing fallback removed in #684: a hardcoded
# regulatory figure must never render silently when the DB path fails.
# Authoritative source: housing_sepp_standards table (migration 045); when the
# standards cannot be loaded the endpoints fail closed (503).

_SEPP_UNAVAILABLE_DETAIL = (
    "The SEPP Housing 2021 secondary-dwelling standards could not be loaded "
    "from the database, so eligibility cannot be assessed. Retry later, or "
    "obtain the current Chapter 3 standards from the SEPP (Housing) 2021."
)


def _get_sepp_sd_standards(conn=None) -> tuple[Optional[float], Optional[float]]:
    """Load secondary dwelling SEPP standards from DB. NO fallback (#817).

    Returns (min_lot_m2, max_floor_area_m2); either element is None when its
    row is missing or the DB is unreachable — callers fail closed on None.
    """
    if conn is None:
        logger.warning("SEPP standards: no DB connection — standards unavailable, callers fail closed")
        return None, None
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
            rows.get("min_lot_size"),
            rows.get("max_floor_area"),
        )
    except Exception as e:
        logger.warning("Failed to load SEPP standards from DB — standards unavailable, callers fail closed: %s", e)
        return None, None

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
    # #745 D3: the brief's VG-reconciled lot area. When supplied it is used
    # verbatim (single source of truth across the report); the geometry
    # shoelace below is only a fallback — mirrors GrannyFlatConfirmRequest.
    lot_area_m2: Optional[float] = None
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
    # None = detection FAILED (three-state, #745 D4); 0 = genuinely none found.
    samgeo_structure_count: Optional[int]
    detection_failed: bool = False
    samgeo_validated: bool
    confirmation_required: bool
    tile_licence: str
    tile_b64: Optional[str] = None      # base64-encoded PNG aerial tile for frontend canvas
    tile_width: Optional[int] = None    # tile pixel dimensions for bbox_pixel scaling
    tile_height: Optional[int] = None
    tile_bbox: Optional[dict] = None    # geographic bounds: {min_lat, max_lat, min_lng, max_lng}
    lot_polygon_wgs84: Optional[list[list[list[float]]]] = None  # [[lng, lat], ...] rings in WGS84
    detect_id: str          # UUID for subsequent /confirm call
    is_heritage: Optional[bool] = None  # auto-detected from spatial_overlays
    warnings: list[str] = []
    # Campaign item 4: identity of the tile/detection inputs this run actually
    # consumed; carried forward to the confirm write like tile_b64 is.
    execution_manifest: Optional[dict] = None


# What a human said about ONE detected structure.
#   part_of_main / garage / existing_gf / unsure — the standalone tool's
#     four-option per-structure question.
#   rejected / kept — the brief card, which only asks keep-or-reject. 'kept'
#     deliberately carries NO building type: that card never asks, and
#     recording one would invent a classification nobody gave.
StructureAnswer = Literal[
    "part_of_main", "garage", "existing_gf", "unsure", "rejected", "kept",
]


class StructureConfirmation(BaseModel):
    """A human answer bound to the structure it refers to.

    `index` is the detect response's `detected_structures[].index`, so the
    answer can be joined back to the bbox/area the person was actually
    looking at. Before this existed the four-option answers were computed in
    the browser and discarded, and the confirm write overwrote the detect
    row's `detected_structures` — so no row anywhere held a structure and a
    judgement about it together.
    """
    # StrictInt, not int: pydantic coerces `true` to 1, which would silently
    # attach an answer to structure 1 and could move the cl 53(1) verdict.
    index: StrictInt
    answer: StructureAnswer


# How `confirmed_structure_count` came to hold the value it holds. THREE
# states, and the absent case is its own state — a caller that says nothing
# is 'unrecorded', never silently counted as a human confirmation. Every
# granny-flat row written before 2026-08-06 is retrospectively 'unrecorded':
# the standalone tool passed `onCountChange` to a component that never called
# it, so the count could only ever echo the detector.
#
# 'secondary_detections_classified' is named for exactly what it records: a person gave
# an answer for every structure the DETECTOR FOUND. It is deliberately NOT
# called 'user_reviewed' or 'user_verified'. Neither surface lets anyone add a
# structure the detector missed, so this state says nothing about false
# negatives — and detection recall is itself unmeasured until check GF-1 in
# ~/.claude/plans/ce-calibration-execution-plan-2026-08.md runs. The label must
# not imply the total was confirmed against the world.
CountSource = Literal["secondary_detections_classified", "machine_default", "unrecorded"]


class GrannyFlatConfirmRequest(BaseModel):
    detect_id: str
    address: str
    prop_id: str
    lat: float
    lng: float
    lot_area_m2: Optional[float]
    confirmed_structure_count: int      # count as submitted — see confirmed_count_source
    confirmed_count_source: Optional[CountSource] = None
    structure_types: Optional[list[StructureConfirmation]] = None
    samgeo_structure_count: Optional[int] = None  # echoed from detect response
    postcode: Optional[str] = None
    report_id: Optional[str] = None     # pre-allocated by Next.js
    is_heritage: Optional[bool] = None  # from NSW Planning Portal via Next.js
    existing_secondary_dwelling: Optional[bool] = None  # user self-report: is there already a granny flat on this lot?
    main_dwelling_area_m2: Optional[float] = None  # SAM-detected footprint of principal dwelling (is_main_dwelling=True)


    @model_validator(mode="after")
    def _reviewed_requires_answers(self):
        """'secondary_detections_classified' is only meaningful with the answers behind it.

        Without this a caller could assert the provenance and buy "high"
        confidence with nothing recorded — the same unfalsifiable claim in a
        new place. The server still cannot observe a click, but it can refuse
        a row whose own fields contradict each other, and it can refuse
        duplicate indexes that would make the answer set ambiguous.
        """
        if self.confirmed_count_source == "secondary_detections_classified" and not self.structure_types:
            raise ValueError(
                "confirmed_count_source='secondary_detections_classified' requires a non-empty "
                "structure_types — a review with no recorded answers is not a review"
            )
        # Shape checks apply to ANY answer list, whatever provenance is
        # claimed. Two conflicting answers for the same structure are
        # ambiguous no matter who is said to have given them, and the Next
        # route already refuses both — a direct caller should not be able to
        # store what the route would reject.
        if self.structure_types:
            seen = [s.index for s in self.structure_types]
            if len(seen) != len(set(seen)):
                raise ValueError("structure_types contains duplicate index values")
            if any(i < 0 or i > 100 for i in seen):
                raise ValueError("structure_types index values must be between 0 and 100")
            if len(seen) > 40:
                raise ValueError("structure_types accepts at most 40 entries")
        return self


class GrannyFlatConfirmResponse(BaseModel):
    report_id: str
    address: str
    granny_flat_buildable: bool
    max_floor_area_m2: float
    estimated_weekly_rent_aud: Optional[float]
    rental_yield_annual_pct: Optional[float]
    assumed_build_cost_aud: Optional[float]
    # `confidence` stays on the wire because the stored column is also the
    # job state machine (NULL -> pending_confirm -> high/medium/low|error) and
    # /api/reports/granny-flat/nearby still filters on it. It is no longer
    # RENDERED anywhere: served surfaces show review_state_* instead.
    confidence: str
    confidence_reason: str              # human-readable explanation shown in UI
    # What actually happened to the structure list — replaces the grade on
    # every served surface. See ReviewState.
    review_state: str
    review_state_label: str
    review_state_detail: str
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
        # #745 D4: a Modal HTTP failure must NOT be byte-identical to a
        # genuine zero-structure result — re-raise so the caller records a
        # real warning and marks detection failed (three-state contract).
        logger.error(f"Modal detect-structures failed: {e}")
        raise RuntimeError(f"structure detection call failed: {e}") from e

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
        # DQ-45: this loop variable was named `bbox`, SHADOWING the tile-bbox
        # dict parameter — the WGS84 conversions below then string-indexed a
        # pixel LIST, so every detection that reached them raised TypeError
        # and the whole run collapsed to detection_failed. The tile bbox
        # (dict) and the structure's pixel bbox (list) are now distinct names.
        bbox_px = s.get("bbox_pixel")
        if not bbox_px or len(bbox_px) != 4:
            logger.warning(f"Skipping structure with missing/malformed bbox_pixel: {s}")
            continue
        x1, y1, x2, y2 = bbox_px
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

def _check_heritage_overlay(lat: float, lng: float) -> Optional[bool]:
    """
    Spatial heritage check via PostGIS spatial_overlays.

    Returns:
      True  — point is inside a heritage conservation area or individually listed
      False — spatial_overlays has heritage rows but point is outside all of them
      None  — spatial_overlays has no heritage rows or DB unavailable
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute("SET LOCAL statement_timeout = '5000'")
            cur.execute(
                """
                SELECT 1 FROM spatial_overlays
                WHERE layer_type = 'heritage'
                  AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                LIMIT 1
                """,
                (lng, lat),
            )
            return cur.fetchone() is not None
    except Exception as e:
        logger.warning(f"Heritage overlay lookup: {e}")
        return None
    finally:
        if conn:
            conn.close()


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


# An answer that says "this is not a separate building on the lot".
_NON_STRUCTURE_ANSWERS = {"part_of_main", "rejected"}


def _structure_identity(detected_structures: list) -> list[tuple]:
    """(identity, structure) for each detected structure.

    Identity is the stored `index` when present, otherwise the array position
    — which is exactly the fallback GrannyFlatBriefCard uses when a row
    predates the field. Keying on `s.get("index")` alone made every answer
    look unknown against a row of None identities: the answers were then all
    dropped and the note fired, while the submitted count sailed on. Verified
    2026-08-06 that all 33 production rows with structures carry `index`, so
    this is a guard against a shape we do not currently hold, not a repair.
    """
    out = []
    for pos, s in enumerate(detected_structures):
        if not isinstance(s, dict):
            continue
        ident = s.get("index")
        out.append((pos if ident is None else ident, s))
    return out


def _storable_answers(
    structure_types: Optional[list],
    detected_structures: Optional[list],
) -> Optional[list]:
    """The answers worth persisting: those that name a real detected structure.

    An answer whose index the detect run never produced points at nothing. It
    is still recorded in the provenance note, but it must not sit in
    `inputs.structure_types`, where a calibration consumer would read it as a
    human label with a referent. When the detect row is unavailable we cannot
    tell, so nothing is dropped — three states, and "unknown" is not "invalid".
    """
    if structure_types is None:
        return None
    if not isinstance(detected_structures, list) or not detected_structures:
        # No detect row, so NOTHING here can be joined to a building. Writing
        # these into `structure_types` would hand a calibration consumer a
        # plausible-looking human classification with no referent — the exact
        # shape of unusable label data this lane exists to stop producing.
        # They are kept, but under a name that says what they are.
        return []
    known = {ident for ident, _ in _structure_identity(detected_structures)}
    return [s.model_dump() for s in structure_types if s.index in known]


def _effective_structure_count(
    structure_types: Optional[list],
    detected_structures: Optional[list],
    submitted_count: int,
) -> int:
    """The structure count the eligibility gate should use.

    When the detect run's structures and per-structure answers are both
    available they settle it between them: every detected structure, less the
    ones answered 'part_of_main' or 'rejected'. The caller's figure is used
    only when there is nothing better to go on. Before this the SEPP cl 53(1)
    multi-structure block keyed on whatever number the request supplied.
    """
    if not isinstance(detected_structures, list) or not detected_structures:
        return submitted_count
    detected_total = sum(1 for s in detected_structures if isinstance(s, dict))
    if not structure_types:
        # We have the detect run but nobody classified anything, so there is no
        # basis for departing from what the detector found. Returning the
        # caller's figure here let a request submit 1 against a three-structure
        # run and skip the cl 53(1) block entirely.
        return detected_total
    # Only answers that name a real detected structure may move the count. An
    # answer for an index the detect run never produced excludes nothing, and
    # counting it would let {index: 99, answer: 'rejected'} reduce the total
    # and clear the cl 53(1) block on the strength of a structure that does
    # not exist.
    known = {ident for ident, _ in _structure_identity(detected_structures)}
    not_separate = sum(
        1 for s in structure_types
        if s.index in known and s.answer in _NON_STRUCTURE_ANSWERS
    )
    return max(0, detected_total - not_separate)


def _effective_secondary_count(
    structure_types: Optional[list],
    detected_structures: Optional[list],
) -> Optional[int]:
    """How many SECONDARY structures survive the answers, or None if unknowable.

    SEPP cl 53(1) is about secondary dwellings, and the block downstream was
    phrased as "total >= 3" on the assumption that a total always includes one
    principal dwelling. Answers can now remove structures, including the
    detector-designated main one, at which point that arithmetic stops
    describing the rule. Counting the secondaries directly says what is meant
    and cannot be shifted by a judgement about the principal dwelling.
    Returns None when there is no detect row — then the caller falls back to
    the total-based test, because nothing here can tell main from secondary.
    """
    if not isinstance(detected_structures, list) or not detected_structures:
        return None
    excluded = {
        s.index for s in (structure_types or [])
        if s.answer in _NON_STRUCTURE_ANSWERS
    }
    return sum(
        1 for ident, st in _structure_identity(detected_structures)
        if not st.get("is_main_dwelling") and ident not in excluded
    )


def _fetch_detect_row(conn, req) -> tuple:
    """(tile_b64, execution_manifest, detected_structures) for this confirm's detect run.

    Scoped to the detect run AND the parcel AND its coordinates: detect_id,
    report_id and prop_id are all caller-supplied, so any one of them alone
    could pair one property's evidence with another's address. The ~50m bound
    matches the flood cache read. Returns (None, None, None) when no row
    resolves — absent evidence, which downstream treats as its own state.
    """
    cols = ("SELECT outputs->>'tile_b64', outputs->'execution_manifest', "
            "       outputs->'detected_structures' FROM granny_flat_reports ")
    coord = " AND abs(lat - %s) < 0.0005 AND abs(lng - %s) < 0.0005 "
    row = None
    with conn.cursor() as cur:
        if req.report_id:
            cur.execute(
                cols + "WHERE id = %s AND prop_id = %s "
                       "AND outputs->>'detect_id' = %s" + coord,
                (req.report_id, req.prop_id, req.detect_id, req.lat, req.lng))
            row = cur.fetchone()
        if row is None and req.detect_id:
            cur.execute(
                cols + "WHERE outputs->>'detect_id' = %s AND prop_id = %s" + coord
                     + "ORDER BY created_at DESC LIMIT 1",
                (req.detect_id, req.prop_id, req.lat, req.lng))
            row = cur.fetchone()
    return (row[0], row[1], row[2]) if row else (None, None, None)


def _count_mismatch_note(
    structure_types: Optional[list],
    detected_structures: list,
    submitted_count: int,
) -> Optional[str]:
    """Describe a submitted count that its own answers do not support.

    The count the answers imply is every structure the DETECT run found, less
    those answered 'part_of_main' or 'rejected'. Returns None when they agree.
    """
    not_separate = sum(
        1 for s in (structure_types or []) if s.answer in _NON_STRUCTURE_ANSWERS
    )
    detected_total = sum(1 for s in detected_structures if isinstance(s, dict))
    implied = max(0, detected_total - not_separate)
    if implied == submitted_count:
        return None
    return (
        f"the answers imply {implied} structure(s) while {submitted_count} was "
        "submitted — the count does not follow from the answers"
    )


def _resolve_count_source(
    claimed: Optional[str],
    structure_types: Optional[list],
    detected_structures: Optional[list],
    submitted_count: Optional[int] = None,
) -> tuple[str, Optional[str]]:
    """Decide the count provenance from evidence, not from the caller's word.

    Returns (resolved_source, downgrade_note).

    'secondary_detections_classified' is the only value that can buy "high" confidence, so it
    cannot be a flag a caller sets. It stands only when the submitted answers
    actually reconcile with what the DETECT run recorded:
      * every non-main structure the detector found has an answer,
      * no answer names an index that run never produced, and
      * the submitted count equals the count those answers imply
        (every detected structure, less the ones answered 'part_of_main' or
        'rejected' — the two answers that mean "not a separate building").

    That last check is what stops a stale or crafted request pairing genuine
    answers with a count they do not support. Index coverage alone would let
    answers implying 2 structures ride along with a submitted 3.

    Anything else is 'machine_default'. That includes the case where the
    detect row could not be re-read: absent evidence is its own outcome and
    never a pass, so a review we cannot check is a review we do not credit.
    A downgrade is recorded rather than silent — the note is stored alongside
    the claim so a row can be audited later.
    """
    have_row = isinstance(detected_structures, list) and bool(detected_structures)
    fallback = claimed or "unrecorded"

    # --- Checks that apply whatever provenance is claimed -------------------
    # An answer that names no structure in the detect run, or a count its own
    # answers do not support, is wrong regardless of who is said to have
    # produced it. Gating these on the claim let a 'machine_default' request
    # store an answer for a structure that does not exist — silently, as
    # human-labelled calibration data with no referent.
    if have_row and structure_types:
        all_indexes = {ident for ident, _ in _structure_identity(detected_structures)}
        answered = {s.index for s in structure_types}
        unknown = answered - all_indexes
        if unknown:
            note = (
                "answers reference structure indexes the detect run never "
                f"produced: {sorted(str(i) for i in unknown)}"
            )
            return ("machine_default" if claimed == "secondary_detections_classified" else fallback), (
                ("claimed secondary_detections_classified, but " + note)
                if claimed == "secondary_detections_classified" else note
            )
        if submitted_count is not None:
            mismatch = _count_mismatch_note(
                structure_types, detected_structures, submitted_count)
            if mismatch:
                return ("machine_default" if claimed == "secondary_detections_classified" else fallback), (
                    ("claimed secondary_detections_classified, but " + mismatch)
                    if claimed == "secondary_detections_classified" else mismatch
                )

    if claimed != "secondary_detections_classified":
        return fallback, None

    # --- The coverage check that licenses the claim -------------------------
    if not have_row:
        return "machine_default", (
            "claimed secondary_detections_classified, but the detect run's structures "
            "could not be re-read, so the answers could not be checked against them"
        )

    expected = {
        ident for ident, st in _structure_identity(detected_structures)
        if not st.get("is_main_dwelling")
    }
    if not expected:
        # The detector found no secondary structure, so there was nothing for
        # anyone to classify and the claim is vacuously true. Granting it would
        # let a lot with only a principal dwelling reach "high" on the strength
        # of a review that could not have happened — the self-agreement trap
        # wearing the new field's clothes.
        return "machine_default", (
            "claimed secondary_detections_classified, but the detect run found no "
            "secondary structure, so there was nothing to classify"
        )

    answered = {s.index for s in (structure_types or [])}
    missing = expected - answered
    if missing:
        return "machine_default", (
            f"claimed secondary_detections_classified, but {len(missing)} of "
            f"{len(expected)} detected secondary structures have no answer"
        )
    return "secondary_detections_classified", None


# What actually happened to the structure list on this report. NOT a grade.
#
# The high/medium/low ladder it replaces on served surfaces graded every lot
# that was not human-reviewed as "medium", which reads as a middling amount of
# confidence. A lot whose scan found nothing has been checked against nothing:
# that is an unverified result, not a middling one. User ruling 2026-08-06:
# "if there is no dwelling found that is also not medium confidence."
#
# Every state below is decided by evidence stored on the row, and each is
# distinguishable from the others in production data (measured 2026-08-06,
# scripts/measure_granny_confidence_states.py over all 87 rows). No state is
# invented that the data cannot support.
ReviewState = Literal[
    "reviewed",             # a person classified every DETECTED secondary structure
    "scan_only_found",      # scan ran, >=1 secondary structure, nobody classified them
    "scan_only_none_found", # scan ran, principal dwelling only, no secondary structure
    "scan_inconclusive",    # scan ran and returned NO structures at all
    "not_assessed",         # scan did not run, failed, or its record could not be re-read
]

# Wording is the served surface. Two rules hold across all five:
#   1. No state claims the list is COMPLETE. A person can only classify what
#      the scan showed them; a missed structure could not be classified at all,
#      and detection recall has never been measured (check GF-1, still unrun).
#   2. Absence is never phrased as a clear result. "Nothing found" carries the
#      reason it might be wrong, in the same sentence a customer reads.
_REVIEW_STATE_TEXT: dict[str, tuple[str, str]] = {
    "reviewed": (
        "Reviewed by you",
        # NO claim that the totals agree. `reviewed` is licensed by answer
        # COVERAGE, not by count equality: answering 'part_of_main' or
        # 'rejected' for a detected structure legitimately moves the total
        # away from the detector's own count, and that row still earns
        # `reviewed`. The old wording asserted "your answers give the same
        # total" on every reviewed report, which is false in exactly that
        # case (Sol finding, 2026-08-06). What was actually done — every
        # detected structure was classified — is true in both.
        "You classified each structure the scan found on this lot. This "
        "covers only structures the scan detected — one it missed could not "
        "be classified, and detection accuracy has never been measured.",
    ),
    "scan_only_found": (
        "Scan only — structures found, not reviewed",
        "The scan found structures on this lot. Nobody has classified what "
        "they are, so the count in this report has not been checked against "
        "the aerial image. Detection accuracy has never been measured.",
    ),
    "scan_only_none_found": (
        "Scan only — no secondary structures found",
        "The scan found the principal dwelling and no other structures. "
        "Nothing has been checked against the aerial image. Small, shaded or "
        "tree-covered structures can be missed, and detection accuracy has "
        "never been measured.",
    ),
    "scan_inconclusive": (
        "Scan inconclusive — no structures found",
        "The scan returned no structures at all on this lot, not even a "
        "principal dwelling. That more likely means the scan could not read "
        "this image than that the lot is empty. Treat the structure count on "
        "this report as unknown.",
    ),
    "not_assessed": (
        "Not assessed",
        "The structure scan did not run, or its result could not be read back. "
        "The structure count on this report has not been checked against the "
        "aerial image, and the number of buildings on this lot is unknown.",
    ),
}


def _review_state(
    validated: bool,
    count_source: str,
    detected_structures: Optional[list],
    machine_count: Optional[int],
    detect_row_unavailable: bool = False,
) -> tuple[str, str, str]:
    """What happened to this report's structure list. Returns (state, label, detail).

    Decided from evidence, in this order, because each earlier condition makes
    the later ones unknowable rather than false:

      1. detection disabled, failed, or its record could not be re-read
         -> `not_assessed`. A count we cannot check is not a weak result, it is
         no result. This is the same rule `_resolve_count_source` applies to
         provenance: absent evidence is its own outcome and never a pass.
      2. a person classified every detected secondary structure -> `reviewed`.
         Only `_resolve_count_source` can license this; it is never taken from
         a caller's word.
      3. otherwise the detector's own output decides, and the empty case is
         SPLIT. Zero structures of any kind is not the same finding as a
         principal dwelling with nothing beside it: every lot this product
         runs on has a house, so a scan that found no house did not find an
         empty lot — it failed to see. Collapsing the two would tell someone
         their lot is clear on the strength of a scan that could not see their
         home, which is the defect this whole change exists to remove.
    """
    if not validated or detect_row_unavailable:
        state = "not_assessed"
    elif detected_structures is None and machine_count is None:
        # Detection failed: `samgeo_structure_count` is None, never 0, by the
        # three-state contract at the detect endpoint (#745 D4).
        state = "not_assessed"
    elif count_source == "secondary_detections_classified":
        state = "reviewed"
    elif isinstance(detected_structures, list):
        # The detect run marks exactly one structure (the largest) as the main
        # dwelling, and only when it found any at all.
        secondary = [
            s for s in detected_structures
            if not (s.get("is_main_dwelling") if isinstance(s, dict)
                    else getattr(s, "is_main_dwelling", False))
        ]
        if not detected_structures:
            state = "scan_inconclusive"
        elif secondary:
            state = "scan_only_found"
        else:
            state = "scan_only_none_found"
    # A bare count, with no structure list behind it. Strictly validated:
    # `False <= 0` is True in Python and `-1 <= 0` is True, so a malformed
    # value would otherwise be served as "the scan ran and returned no
    # structures" — a claim about the lot manufactured from a broken field.
    # Mirrors strictCount() in lib/granny-flat-review-state.ts so the two
    # implementations cannot disagree about the same row.
    elif not isinstance(machine_count, int) or isinstance(machine_count, bool) \
            or machine_count < 0:
        state = "not_assessed"
    elif machine_count == 0:
        state = "scan_inconclusive"
    elif machine_count == 1:
        # One structure detected is the principal dwelling — nothing secondary.
        state = "scan_only_none_found"
    else:
        state = "scan_only_found"

    label, detail = _REVIEW_STATE_TEXT[state]
    return state, label, detail


def _compute_confidence(
    validated: bool,
    confirmed_count: int,
    samgeo_count: Optional[int],
    rent_available: bool,
    count_source: str = "unrecorded",
    answers_given: Optional[int] = None,
) -> tuple[str, str]:
    """
    Returns (confidence, reason) tuple.

    high:   a PERSON classified every structure the DETECTOR FOUND, the total
            those answers imply matches the detector's own count, AND rent
            data is present. Silent about structures the detector missed —
            see the CountSource note.
    medium: anything else that ran — including the detector agreeing with
            itself, which is what "counts agree" meant before 2026-08-06.
    low:    samgeo not validated (pre-spike).

    `count_source` is the three-state provenance of `confirmed_count`
    (`CountSource`). It exists because agreement between the detector and a
    number seeded FROM the detector is not evidence about the world.

    Until 2026-08-06 the standalone tool passed `onCountChange` to a component
    that never invoked it, so `confirmed_structure_count` could only ever echo
    `samgeo_structure_count`. The served reason nonetheless read
    "AI detected 1 structure, you confirmed 1 — counts agree", and that
    self-agreement promoted the report to "high". Measured on the 16 rows
    carrying both counts: 13 "agreed", and every one of those agreements was
    the echo. The 2 apparent disagreements were both confirmed=1 / detected=0
    — the frontend's fallback default when detection found nothing, also not a
    human. Zero of 16 carried a human judgement about the count.

    So: `unrecorded` and `machine_default` can no longer reach "high", and no
    reason string may say a person confirmed anything unless one did.
    """
    if not validated:
        return (
            "low",
            "Aerial structure detection is in pre-validation mode. "
            "Manually verify structure count on SIX Maps before relying on this report."
        )

    counts_agree = (samgeo_count is not None and confirmed_count == samgeo_count)
    human_checked = (count_source == "secondary_detections_classified")
    plural = 's' if samgeo_count != 1 else ''
    # Some answers were given, just not enough to license the claim. Saying
    # nothing was checked would understate what the person actually did — and
    # on this path their answers have already MOVED the count.
    # `confirmed_count` is the count the report USED, and since 2026-08-06 the
    # endpoint derives that from the detected structures and these answers —
    # so when answers exist the count follows from them by construction. The
    # earlier "count does not follow from your answers" branch described the
    # SUBMITTED figure, which now has its own warning and never reaches here.
    partly_answered = answers_given is not None and answers_given > 0

    if human_checked and counts_agree and rent_available:
        return (
            "high",
            f"Aerial detection found {samgeo_count} structure{plural} on this lot and "
            "you classified each secondary structure among them, giving the same total. "
            "The principal dwelling is identified by the detection, not by you, and a "
            "structure the detection did not find could not be classified at all — "
            "both are outside this check. "
            "Rent estimate sourced from NSW Fair Trading bond data."
        )

    if samgeo_count is None:
        reason = "Structure count entered manually (aerial detection not available). "
    elif not human_checked and partly_answered:
        # Some structures were classified and the count reflects those answers,
        # but not every detected secondary structure was covered. Saying it was
        # not checked at all would understate what the person did.
        reason = (
            f"Aerial detection found {samgeo_count} structure{plural} on this lot. "
            f"The report used {confirmed_count}, reflecting the {answers_given} "
            "structure(s) you classified. "
            "The rest were not classified, so the total has only partly been "
            "checked against the aerial image. "
        )
    elif not human_checked:
        # Nobody touched anything — the honest description of the old
        # "counts agree" case.
        reason = (
            f"Aerial detection found {samgeo_count} structure{plural} on this lot. "
            f"The report used {confirmed_count}. "
            "This count was not reviewed structure by structure, so it has not "
            "been checked against the aerial image. "
        )
    elif counts_agree:
        # Human agreed, but rent data is the missing piece.
        reason = (
            f"Aerial detection found {samgeo_count} structure{plural} and you "
            "classified each secondary structure among them, giving the same total. "
        )
    else:
        reason = (
            f"Aerial detection found {samgeo_count} structure{plural} "
            f"but your answers give {confirmed_count}. "
        )

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
        from services.execution_manifest import MANIFEST_KEY, build_manifest
        from services.geometry_checks import check_point_nsw, check_rings_epsg3857
    except ImportError:
        from nsw_imagery import fetch_tile_to_file
        from execution_manifest import MANIFEST_KEY, build_manifest
        from geometry_checks import check_point_nsw, check_rings_epsg3857

    # Units/CRS entry check (campaign item 4): typed 422, never a detection
    # run over the wrong place from a swapped/projected coordinate.
    coord_reason = check_point_nsw(req.lat, req.lng)
    if coord_reason:
        raise HTTPException(
            422, f"Structure detection could not be determined: {coord_reason}")

    lot_geometry = req.lot_geometry or _fetch_lot_geometry(req.prop_id)
    lot_geometry_provided = lot_geometry is not None
    # Lot rings must actually be the EPSG:3857 metres the pipeline assumes —
    # degree-scale rings convert into garbage silently. Implausible rings are
    # DEMOTED to no-geometry (detection proceeds unclipped, recorded below).
    lot_rings_reason = None
    if lot_geometry is not None:
        # EVERY non-null geometry is validated — a rings-less dict used to
        # slip past and the manifest then claimed used_for_clipping=True for
        # geometry no clip could use (Sol finding, 2026-08-03).
        lot_rings_reason = check_rings_epsg3857(lot_geometry.get("rings"))
        if lot_rings_reason:
            logger.warning(f"Lot rings failed CRS plausibility — proceeding "
                           f"without lot clipping: {lot_rings_reason}")
            lot_geometry = None
    # #745 D3: prefer the caller's reconciled lot area (one figure per brief);
    # compute from geometry only when the caller has none.
    lot_area_m2 = req.lot_area_m2 if req.lot_area_m2 is not None else (
        _compute_lot_area_m2(lot_geometry) if lot_geometry else None)

    # Load SEPP standards from DB — no fallback (#817): unavailable standards
    # fail the request rather than screen eligibility against a hardcoded figure.
    _detect_conn = None
    try:
        _detect_conn = _get_conn()
        sepp_min_lot, _sepp_max_gf = _get_sepp_sd_standards(_detect_conn)
    except Exception:
        sepp_min_lot, _sepp_max_gf = _get_sepp_sd_standards()
    finally:
        if _detect_conn:
            _detect_conn.close()
    if sepp_min_lot is None:
        raise HTTPException(status_code=503, detail=_SEPP_UNAVAILABLE_DETAIL)

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
        # 4th element (tile identity meta) is optional so older fakes/spikes
        # returning 3-tuples keep working.
        _tile_result = fetch_tile_to_file(
            req.lat, req.lng, output_path=tile_path, grid=3
        )
        tile_path, licence, bbox = _tile_result[:3]
        tile_meta = _tile_result[3] if len(_tile_result) > 3 else None
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
    detection_failed = False
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
        except RuntimeError as e:
            detection_failed = True
            if "not configured" in str(e):
                detect_warnings.append(
                    "Aerial structure detection unavailable (MODAL_STRUCTURES_URL not configured). "
                    "Enter structure count manually."
                )
            else:
                detect_warnings.append(
                    "Aerial structure detection did not complete — the building "
                    "count is unknown, not zero. Enter the structure count manually."
                )
        except Exception as e:
            logger.error(f"samgeo detection failed: {e}")
            detection_failed = True
            detect_warnings.append(
                "Aerial structure detection did not complete — the building "
                "count is unknown, not zero. Enter the structure count manually."
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

    # Auto-detect heritage from spatial_overlays (replaces user self-report)
    heritage_auto = _check_heritage_overlay(req.lat, req.lng)

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
        samgeo_structure_count=None if detection_failed else len(detected_structures),
        detection_failed=detection_failed,
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
        is_heritage=heritage_auto,
        warnings=detect_warnings,
        # Built from the objects this run actually consumed: the tile fetch's
        # own meta, the geometry state after the CRS demotion above, and the
        # detection outcome (campaign item 4 — never a parallel lookup).
        execution_manifest=build_manifest(
            product="granny-flat",
            algorithm_version=ALGORITHM_VERSION,
            inputs={
                "aerial_tile": tile_meta,
                "tile_licence": licence,
                "lot_geometry": {
                    "provided": lot_geometry_provided,
                    "used_for_clipping": lot_geometry is not None,
                    "rejected_reason": lot_rings_reason,
                },
                "detection": {
                    "failed": detection_failed,
                    "structure_count": (None if detection_failed
                                        else len(detected_structures)),
                },
            },
            query_params={"lat": req.lat, "lng": req.lng, "grid": 3},
            parcel_identity={"prop_id": req.prop_id},
        ),
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

    # Load SEPP standards from DB — no fallback (#817): the buildable verdict,
    # floor-area cap, and cost figures all derive from these standards, so an
    # unavailable config fails the request instead of rendering hardcoded figures.
    # The DETECT row rides along on this connection rather than opening
    # another. It has to be read HERE, before the eligibility gate below,
    # because the gate keys on the structure count: reading it later meant the
    # count driving a served verdict was whatever the caller sent, while the
    # provenance machinery downstream could only complain about it afterwards.
    tile_b64: Optional[str] = None
    detect_manifest = None
    detected_structures_carry = None
    # The detect-row read has its OWN try. Sharing the SEPP fallback's
    # `except` swallowed a failed read into a silent None, and the count then
    # fell back to whatever the caller sent with nothing said about it — a
    # transient SQL error would have quietly restored the exact behaviour this
    # change removes. A failure here is recorded and surfaced instead.
    detect_row_unavailable = False
    _confirm_conn = None
    try:
        _confirm_conn = _get_conn()
        try:
            sepp_min_lot, sepp_max_gf = _get_sepp_sd_standards(_confirm_conn)
        except Exception:
            sepp_min_lot, sepp_max_gf = _get_sepp_sd_standards()
        try:
            tile_b64, detect_manifest, detected_structures_carry = _fetch_detect_row(
                _confirm_conn, req)
        except Exception as e:
            detect_row_unavailable = True
            logger.error(f"Detect-row read failed for detect_id={req.detect_id}: {e}")
    except Exception:
        detect_row_unavailable = True
        sepp_min_lot, sepp_max_gf = _get_sepp_sd_standards()
    finally:
        if _confirm_conn:
            try:
                _confirm_conn.close()
            except Exception:
                pass
    # A row that simply did not match (expired, superseded, or a mismatched
    # detect_id/prop_id/coordinate triple) is just as blind as a failed read:
    # the count falls back to the caller's figure either way. Warn on the
    # OUTCOME, not on the exception, or an unmatched row clears the cl 53(1)
    # block in silence.
    if detect_row_unavailable or not isinstance(detected_structures_carry, list):
        warnings.append(
            "The structure detection for this address could not be re-read, so "
            "the structure count could not be checked against it. The count "
            "supplied with the request was used."
        )
    if sepp_min_lot is None or sepp_max_gf is None:
        raise HTTPException(status_code=503, detail=_SEPP_UNAVAILABLE_DETAIL)

    count_source, provenance_note = _resolve_count_source(
        req.confirmed_count_source,
        req.structure_types,
        detected_structures_carry,
        submitted_count=req.confirmed_structure_count,
    )

    # The detector's count comes from the DETECT ROW when we have it.
    # `req.samgeo_structure_count` is echoed back by the client
    # (page.tsx -> route.ts -> here), so comparing the submitted count against
    # it was comparing two caller-supplied numbers. Census finding, closed.
    if isinstance(detected_structures_carry, list):
        machine_count = len(detected_structures_carry)
    else:
        machine_count = req.samgeo_structure_count

    # The count the SEPP gate actually uses. When the detect row and the
    # answers are both present they determine it between them; the submitted
    # figure is only trusted when there is nothing better. Previously a
    # request could submit any number and clear the cl 53(1) block with it.
    effective_count = _effective_structure_count(
        req.structure_types, detected_structures_carry,
        req.confirmed_structure_count)
    # None when there is no detect row — the gates below then fall back to the
    # total-based test, which is all that is knowable without one.
    effective_secondary = _effective_secondary_count(
        req.structure_types, detected_structures_carry)

    if provenance_note:
        warnings.append(
            "Structure count not treated as reviewed: "
            + provenance_note.replace("claimed secondary_detections_classified, but ", "")
            + ". The structure count in this report has not been "
              "checked against the aerial image."
        )
    if effective_count != req.confirmed_structure_count:
        warnings.append(
            f"Structure count taken from the aerial detection and your answers "
            f"({effective_count}), not the {req.confirmed_structure_count} submitted "
            "with the request."
        )

    # An answer naming an existing granny flat outranks a request field saying
    # there is none: the answer is the specific evidence, and SEPP cl 53(1) is
    # the clause it bears on. Trusting the boolean meant a report could record
    # 'existing_gf' for a structure and still compute eligibility as if the lot
    # had none.
    existing_secondary_dwelling = req.existing_secondary_dwelling
    _kept_answers = _storable_answers(req.structure_types, detected_structures_carry) or []
    if any(a.get("answer") == "existing_gf" for a in _kept_answers):
        if existing_secondary_dwelling is not True:
            warnings.append(
                "One of the structures was identified as an existing secondary "
                "dwelling, so the lot is assessed on that basis."
            )
        existing_secondary_dwelling = True

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

    # Heritage: use user-provided value if set, otherwise auto-detect from spatial_overlays
    if req.is_heritage is not None:
        is_heritage = bool(req.is_heritage)
    else:
        heritage_auto = _check_heritage_overlay(req.lat, req.lng)
        is_heritage = bool(heritage_auto)  # None → False (safe default)
    if is_heritage:
        heritage_source = "user-provided" if req.is_heritage is not None else "spatial_overlays auto-detect"
        warnings.append(
            "Property is in a Heritage Conservation Area or has a heritage listing "
            f"(source: {heritage_source}). "
            "Granny flat construction may require heritage approval — confirm with council."
        )

    # SEPP Housing 2021 cl 53(1): only one secondary dwelling per lot.
    if existing_secondary_dwelling is True:
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
        # Two or more secondary structures. Counted directly when the detect
        # row tells us which are secondary; otherwise inferred from the total
        # on the old "1 main + 2 secondary = 3" assumption.
        and (effective_secondary >= 2 if effective_secondary is not None
             else effective_count >= 3)
        and existing_secondary_dwelling is None
    ):
        granny_flat_buildable = False
        # PROVENANCE, not phrasing. In production MODAL_STRUCTURES_URL is unset,
        # so _detect_structures_samgeo never runs, there is no detect row, and
        # this gate fires on req.confirmed_structure_count -- a number the
        # CUSTOMER confirmed against the aerial tile. Saying "were detected"
        # there tells them a scan found something when nothing ran.
        # docs/FEATURES_CAPABILITIES.md already records that structure detection
        # is NOT a capability (recall 0.368 on 56 lots against a pre-committed
        # 0.70 floor, failing in all four councils tested); this was the served
        # sentence that still claimed it, and it reaches the customer in the PDF.
        # The MULTIPLE_SECONDARY_STRUCTURES: prefix is load-bearing --
        # lib/pdf/granny-flat-report.tsx matches it with startsWith in three
        # places -- so it stays exactly as it is.
        _counted_by_scan = bool(
            isinstance(detected_structures_carry, list) and detected_structures_carry
        )
        # The no-scan branch must not claim SECONDARY structures either. Without
        # a detect row effective_secondary is None and the gate fires on
        # effective_count >= 3, a TOTAL. "You confirmed two or more secondary
        # structures" asserts a classification the customer never made -- they
        # gave a count, and the "1 main + 2 secondary" split is this code's
        # inference, not their statement. Saying the count back to them and
        # naming the inference separately is the only version that is true.
        # (Cross-review finding, 2026-08-25 — the same defect as the one above,
        # one step further in.)
        warnings.append(
            "MULTIPLE_SECONDARY_STRUCTURES: "
            + ("Two or more secondary structures were detected on this lot. "
               if _counted_by_scan else
               f"You reported {effective_count} structures on this lot. "
               "Counting the principal dwelling, that leaves two or more others. ")
            + "SEPP Housing 2021 (cl 53(1)) permits only one secondary dwelling per lot. "
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
        # Exactly one secondary structure — ambiguous but not blocked.
        (effective_secondary == 1 if effective_secondary is not None
         else effective_count == 2)
        and existing_secondary_dwelling is None
    ):
        warnings.append(
            "Existing outbuilding detected. Granny flat approval depends on whether "
            "the existing structure is already an ancillary dwelling — verify with council."
        )

    # Confidence is computed further down, once the DETECT row has been re-read
    # — the count provenance is resolved against that row rather than taken
    # from the caller. See _resolve_count_source.
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
            # prior-art-checked: reuse not viable because this IS the
            # existing implementation, relocated. The detect-row read now
            # happens on the SEPP-standards connection higher up, because
            # the eligibility gate needs the count it produces; nothing
            # here re-queries it. tile_b64, detect_manifest,
            # detected_structures_carry, count_source, provenance_note,
            # machine_count and effective_count are all already resolved.
            confidence, confidence_reason = _compute_confidence(
                validated=SAMGEO_VALIDATED,
                confirmed_count=effective_count,
                samgeo_count=machine_count,
                rent_available=weekly_rent is not None,
                count_source=count_source,
                # Only answers that were KEPT — a discarded
                # referent-less answer must not make the report say
                # the count reflects a structure nobody classified.
                answers_given=len(_storable_answers(
                    req.structure_types, detected_structures_carry) or []),
            )

            # Cap confidence to medium when key eligibility inputs are unknown.
            # Both conditions are checked independently against "high" (not
            # sequentially) so that both warnings are surfaced even if both apply.
            cap_reasons = []
            if lot_area_m2 is None:
                cap_reasons.append("Lot area could not be verified — eligibility is unconfirmed.")
            if existing_secondary_dwelling is None and (
                    effective_secondary >= 1 if effective_secondary is not None
                    else effective_count >= 2):
                cap_reasons.append(
                    "Eligibility is capped because the status of one or more existing secondary "
                    "structures on this lot could not be confirmed. NSW planning rules only allow one "
                    "secondary dwelling per lot."
                )
            if cap_reasons and confidence == "high":
                confidence = "medium"
                confidence_reason += " " + " ".join(cap_reasons)

            # What happened to the structure list, as opposed to how good the
            # report is. Deliberately NOT affected by cap_reasons above: an
            # unknown lot area or an unconfirmed existing-dwelling status says
            # nothing about whether a person classified the structures, and
            # folding them together is what made one word carry two meanings.
            review_state, review_state_label, review_state_detail = _review_state(
                validated=SAMGEO_VALIDATED,
                count_source=count_source,
                detected_structures=detected_structures_carry,
                machine_count=machine_count,
                # A row that simply did not match is as blind as a failed
                # read — the SAME condition the warning above is raised on.
                # Passing only the exception flag left the unmatched case
                # deciding the state from `req.samgeo_structure_count`, which
                # is the caller's own echoed number: the report would have
                # described a scan using a figure supplied by the requester.
                detect_row_unavailable=(
                    detect_row_unavailable
                    or not isinstance(detected_structures_carry, list)
                ),
            )

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
                        "confirmed_structure_count": effective_count,
                        "confirmed_structure_count_submitted": req.confirmed_structure_count,
                        # Whether a human touched that count, as a FIELD — a
                        # comment cannot be queried, and the 16 historical
                        # rows are indistinguishable from human-confirmed
                        # precisely because nothing recorded this. This is the
                        # RESOLVED value (checked against the detect row), not
                        # the caller's claim; the claim and the reason for any
                        # downgrade are kept beside it so the decision is
                        # auditable rather than silent.
                        "confirmed_count_source": count_source,
                        "confirmed_count_source_claimed": req.confirmed_count_source,
                        "confirmed_count_source_note": provenance_note,
                        # The per-structure answers, bound to the structure
                        # index they refer to. Previously browser-local and
                        # discarded.
                        # Only answers with a referent are stored. An index
                        # the detect run never produced is a label pointing at
                        # nothing, and a calibration consumer reading this
                        # column would have no way to tell — the note above
                        # records that some were dropped.
                        "structure_types": _storable_answers(
                            req.structure_types, detected_structures_carry),
                        # Answers we could not bind to a detected building.
                        # Retained (the person did give them) but kept out of
                        # the column calibration reads, so an unjoinable label
                        # is never mistaken for a usable one.
                        "structure_types_unjoinable": (
                            [s.model_dump() for s in req.structure_types]
                            if req.structure_types and
                               not isinstance(detected_structures_carry, list)
                            else None),
                        # The join key back to the detect run. Accepted by this
                        # endpoint since it existed, never stored until now.
                        "detect_id": req.detect_id,
                        "samgeo_structure_count": req.samgeo_structure_count,
                        "postcode": postcode,
                        "existing_secondary_dwelling": existing_secondary_dwelling,
                        "existing_secondary_dwelling_submitted": req.existing_secondary_dwelling,
                        "main_dwelling_area_m2": req.main_dwelling_area_m2,
                        "execution_manifest": detect_manifest,
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
                        # Stored so a re-pulled PDF renders the state the run
                        # actually produced, rather than re-deriving it from
                        # whatever fields happen to survive. Rows written
                        # before 2026-08-06 have no such key and are derived
                        # by the reader — see lib/granny-flat-review-state.ts.
                        "review_state": review_state,
                        "review_state_label": review_state_label,
                        "review_state_detail": review_state_detail,
                        "warnings": warnings,
                        "data_sources": data_sources,
                        "tile_b64": tile_b64,
                        # Carried forward so the confirmation above keeps its
                        # referent — see the SELECT note.
                        "detected_structures": detected_structures_carry,
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
    # Record what SAM returned, not what the report ended up using. Logging the
    # confirmed count here attributed the human/echoed figure to the detector
    # and made the audit trail unable to tell them apart.
    ds_samgeo.record_response(
        {
            # The detector's OWN count, read back from the detect row. Logging
            # req.samgeo_structure_count here recorded a number the client
            # handed us as SAM's response — the audit trail would have said
            # SAM returned 99 structures because a request said so.
            "structure_count": machine_count,
            "structure_count_client_echo": req.samgeo_structure_count,
            "count_used_in_report": effective_count,
            "count_source": count_source,
        },
        features_returned=machine_count,
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

    heritage_source_name = (
        "User-provided heritage flag"
        if req.is_heritage is not None
        else "PostGIS heritage overlay (spatial_overlays)"
    )
    ds_heritage = DataSourceQuery(
        heritage_source_name,
        "local:spatial_overlays" if req.is_heritage is None else "user-input",
        {"lat": req.lat, "lng": req.lng, "is_heritage": is_heritage},
    )
    ds_heritage.record_response(
        {"is_heritage": is_heritage},
        features_returned=1 if is_heritage else 0,
    )

    audit_data_sources = [ds_samgeo, ds_aerial, ds_sepp, ds_heritage]

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
            "confirmed_structure_count": effective_count,
            "confirmed_count_source": count_source,
            # The audit trail keeps what the caller SENT, including any
            # referent-less answers the stored column drops — the record of
            # the request should not be quietly tidier than the request was.
            "structure_types_submitted": (
                [s.model_dump() for s in req.structure_types]
                if req.structure_types is not None else None
            ),
            "structure_types_stored": _storable_answers(
                req.structure_types, detected_structures_carry),
            "detect_id": req.detect_id,
            "samgeo_structure_count": req.samgeo_structure_count,
            "postcode": postcode,
            "existing_secondary_dwelling": existing_secondary_dwelling,
        },
        data_sources=audit_data_sources,
        output_summary=outputs_for_audit,
        disclaimer_version=get_current_disclaimer_version("granny-flat"),
        intermediate_calculations={
            "lot_area_m2": lot_area_m2,
            "max_buildable_m2": max_floor_area_m2,
            "structure_count": effective_count,
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
        review_state=review_state,
        review_state_label=review_state_label,
        review_state_detail=review_state_detail,
        data_sources=data_sources,
        warnings=warnings,
    )
