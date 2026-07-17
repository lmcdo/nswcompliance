"""
Pre-DA Site History Report pipeline.

POST /pipeline/pre-da-history  — generate a full site history report for an address.

Layers (in order of execution):
  1. Geocode address → (lat, lon, council)
  2. Tessera embedding timeline 2017–2025 (neighbourhood-normalised)
  3. Sentinel-2 NDVI/NDBI delta timeline (change type disambiguation)
  4. NSW ePlanning DA/CC/OC event fetch
  5. Heritage flag (PostGIS spatial_overlays)
  6. Flood/fire event annotation
  7. Wayback SSIM comparison for small lots (<300 m²)
  8. Annotate + assemble timeline JSON
  9. Store to Supabase, generate PDF

Data sources: geotessera (Clay v1.5, free), Element84 Sentinel-2 (free),
NSW ePlanning Portal (free, no auth), PostGIS spatial_overlays (sunk cost),
Esri World Imagery Wayback (free, no auth).
"""
from __future__ import annotations

import io
import json
import logging
import math
import os
import re
import time
from datetime import date
from typing import Optional

import numpy as np
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from audit_trail import DataSourceQuery, log_audit_trail, get_current_disclaimer_version

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

YEARS = list(range(2017, 2026))  # 2017–2025 inclusive
# Tessera tile coverage notes (confirmed 2026-04-25, scripts/check3f_tile_lookup.py):
# - 2025 tiles are sparse globally (283K vs 308K+ for other years) — some tiles NaN.
# - Some inner Sydney tiles only exist from 2024 (e.g. Leichhardt/Balmain at lat=-33.85,lon=151.15).
#   Affected suburbs: Leichhardt, Rozelle, Annandale (approx lat -33.85 to -33.88, lon 151.10-151.20).
#   These addresses will return NaN for 2017-2023 and are reported as "data unavailable".
# - Marrickville, Newtown, Enmore, Dulwich Hill, Sydenham: full 2017-2024 coverage confirmed.

EPLANNING_BASE = "https://api.apps1.nsw.gov.au/eplanning/data/v0"
WAYBACK_META_URL = "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer"
WAYBACK_TILE_URL = (
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/"
    "World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/{release}/{z}/{y}/{x}"
)
NSW_PLANNING_BASE = "https://api.apps1.nsw.gov.au/planning"
NSW_PLANNING_HEADERS = {
    "Origin": "https://www.planningportal.nsw.gov.au",
    "Referer": "https://www.planningportal.nsw.gov.au/",
}
ELEMENT84_URL = "https://earth-search.aws.element84.com/v1"

# Change threshold constants
SIM_STABLE = 0.95
SIM_MINOR = 0.85
SIM_MODERATE = 0.70

# Lot area below which we also run Wayback SSIM (Tessera resolution is poor)
SMALL_LOT_THRESHOLD_M2 = 300

# Fail-closed coverage gate (issue #751): the year-on-year similarity timeline
# needs at least one (N-1, N) pair where BOTH years have a published Tessera
# tile. Below this, every timeline entry is no_data and the report is hollow.
MIN_CONSECUTIVE_COVERED_PAIRS = 1

# Max pages to fetch from ePlanning per application type (50 records/page).
# 10 pages = 500 DAs — covers all but the very largest councils.
EPLANNING_MAX_PAGES = 10

DATA_QUALITY_NOTE = (
    "Satellite analysis based on Tessera/Clay v1.5 annual embeddings (10m resolution). "
    "DA events sourced from NSW ePlanning Portal — complete from July 2021; "
    "pre-July 2021 events may not be captured. "
    "Flood/fire annotations are indicative based on known event bounding boxes."
)

# ---------------------------------------------------------------------------
# Hardcoded event tables (MVP; v2: replace with WFS polygon queries)
# ---------------------------------------------------------------------------

NSW_FLOOD_EVENTS = [
    {
        "year": 2021,
        "name": "March 2021 NSW Floods",
        "regions": ["Hawkesbury-Nepean", "Hunter Valley", "Mid-North Coast"],
        "bbox": (148.5, -34.5, 152.5, -30.5),
    },
    {
        "year": 2022,
        "name": "February–March 2022 Northern Rivers Floods",
        "regions": ["Lismore", "Ballina", "Byron Bay"],
        "bbox": (152.7, -29.0, 153.6, -28.0),
    },
    {
        "year": 2022,
        "name": "February–March 2022 Hawkesbury-Nepean Floods",
        "regions": ["Windsor", "Richmond", "Penrith"],
        "bbox": (150.5, -33.8, 151.0, -33.4),
    },
    {
        "year": 2022,
        "name": "July 2022 Central West NSW Floods",
        "regions": ["Forbes", "Eugowra", "Condobolin"],
        "bbox": (147.0, -34.0, 148.5, -32.5),
    },
    {
        "year": 2022,
        "name": "October–November 2022 Western NSW Floods",
        "regions": ["Wagga Wagga", "Forbes", "Griffith"],
        "bbox": (145.5, -35.5, 147.5, -33.5),
    },
    {
        "year": 2023,
        "name": "June–July 2023 NSW Floods",
        "regions": ["Hawkesbury", "Hunter Valley", "Mid-Coast"],
        "bbox": (150.5, -34.0, 152.5, -32.0),
    },
]

NSW_FIRE_EVENTS = [
    {
        "year": 2019,
        "name": "2019–20 Black Summer Bushfires",
        "regions": ["Blue Mountains", "South Coast", "Northern Tablelands"],
        "bbox": (148.0, -37.5, 153.0, -29.5),
    },
    {
        "year": 2020,
        "name": "2019–20 Black Summer Bushfires (recovery phase)",
        "regions": ["Blue Mountains", "South Coast", "Northern Tablelands"],
        "bbox": (148.0, -37.5, 153.0, -29.5),
    },
    {
        "year": 2022,
        "name": "2021–22 Summer Bushfire Season",
        "regions": ["Northern NSW", "New England"],
        "bbox": (149.0, -32.0, 152.5, -28.5),
    },
]

# ---------------------------------------------------------------------------
# DB connection (same pattern as threat_radar.py)
# ---------------------------------------------------------------------------

def _get_conn():
    dsn = os.environ.get("DATABASE_URL")
    if dsn:
        import psycopg2
        return psycopg2.connect(dsn)
    import psycopg2
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        database=os.environ.get("DB_NAME", "nsw_planning"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD") or "",
        port=int(os.environ.get("DB_PORT", 5432)),
    )

# ---------------------------------------------------------------------------
# Layer 1 — Geocoding
# ---------------------------------------------------------------------------

def _mercator_to_wgs84(x: float, y: float) -> tuple[float, float]:
    """Convert EPSG:3857 (Web Mercator) x/y to WGS84 lat/lon."""
    R = 20037508.342789244
    lon = x / R * 180.0
    lat = math.degrees(2.0 * math.atan(math.exp(y * math.pi / R)) - math.pi / 2.0)
    return lat, lon


# Maps lowercase LGA names → exact council name string the NSW ePlanning API expects.
# Sourced from threat_radar.py._COUNCIL_NAME_MAP (keep in sync).
_LGA_TO_COUNCIL: dict[str, str] = {
    "inner west": "Inner West Council",
    "sydney": "Council of the City of Sydney",
    "city of sydney": "Council of the City of Sydney",
    "parramatta": "City of Parramatta Council",
    "city of parramatta": "City of Parramatta Council",
    "northern beaches": "Northern Beaches Council",
    "randwick": "Randwick City Council",
    "waverley": "Waverley Council",
    "woollahra": "Woollahra Municipal Council",
    "mosman": "Mosman Municipal Council",
    "north sydney": "North Sydney Council",
    "willoughby": "Willoughby City Council",
    "lane cove": "Lane Cove Municipal Council",
    "hunters hill": "Hunters Hill Council",
    "ryde": "Ryde City Council",
    "ku-ring-gai": "Ku-ring-gai Council",
    "hornsby": "Hornsby Shire Council",
    "the hills": "The Hills Shire Council",
    "blacktown": "Blacktown City Council",
    "penrith": "Penrith City Council",
    "blue mountains": "Blue Mountains City Council",
    "hawkesbury": "Hawkesbury City Council",
    "camden": "Camden Council",
    "campbelltown": "Campbelltown City Council",
    "wollondilly": "Wollondilly Shire Council",
    "liverpool": "Liverpool City Council",
    "fairfield": "Fairfield City Council",
    "canterbury-bankstown": "Canterbury-Bankstown Council",
    "georges river": "Georges River Council",
    "sutherland": "Sutherland Shire Council",
    "sutherland shire": "Sutherland Shire Council",
    "bayside": "Bayside Council",
    "strathfield": "Strathfield Municipal Council",
    "burwood": "Burwood Council",
    "cumberland": "Cumberland Council",
    "wollongong": "Wollongong City Council",
    "central coast": "Central Coast Council",
    "newcastle": "Newcastle City Council",
    "lake macquarie": "Lake Macquarie City Council",
    "maitland": "Maitland City Council",
    "gosford": "Central Coast Council",
    "wyong": "Central Coast Council",
}


def _lga_to_council(lga_name: str) -> str:
    key = lga_name.strip().lower()
    return _LGA_TO_COUNCIL.get(key, lga_name.strip())


def _get_council_from_db(lat: float, lon: float) -> str:
    """
    Query spatial_overlays for the LGA name at a point, normalise to ePlanning council name.
    Prefers layer_type='height' rows (confirmed to have lga_name, covers 75 LGAs).
    Falls back to any layer type if height rows don't cover the point.
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            # Prefer height rows (broadest LGA coverage with lga_name populated)
            cur.execute(
                "SELECT lga_name FROM spatial_overlays "
                "WHERE layer_type = 'height' "
                "AND lga_name IS NOT NULL "
                "AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) "
                "LIMIT 1",
                (lon, lat),
            )
            row = cur.fetchone()
            if not row:
                # Fallback: any layer with lga_name
                cur.execute(
                    "SELECT lga_name FROM spatial_overlays "
                    "WHERE lga_name IS NOT NULL "
                    "AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326)) "
                    "LIMIT 1",
                    (lon, lat),
                )
                row = cur.fetchone()
        if row and row[0]:
            return _lga_to_council(row[0])
    except Exception as exc:
        logger.warning(f"Council DB lookup failed: {exc}")
    finally:
        if conn:
            conn.close()
    return ""


def geocode_address(address: str) -> tuple[float, float, str]:
    """
    Returns (lat, lon, council_name) for a NSW address.

    Step 1: NSW Planning Portal ePlanningApi/address → propId
    Step 2: ePlanningApi/lot → lot geometry (EPSG:3857) → centroid → WGS84
    Step 3: spatial_overlays DB query → lga_name → normalised council name

    Confirmed working endpoint pattern from spike_solar_samgeo.py and granny_flat.py.
    """
    # Step 1: address → propId
    # NSW Planning Portal is flaky — retry once on timeout
    for attempt in range(2):
        try:
            r = requests.get(
                f"{NSW_PLANNING_BASE}/viewersf/V1/ePlanningApi/address",
                params={"a": address, "noOfRecords": 1},
                headers=NSW_PLANNING_HEADERS,
                timeout=20,
            )
            r.raise_for_status()
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt == 1:
                raise ValueError("NSW Planning Portal timed out — try again in a few minutes")
            time.sleep(2)
    results = r.json()
    if not results:
        raise ValueError(f"Address not found: {address}")
    # GATE-0 (parcel identity): the Portal /address search is fuzzy — refuse to
    # geocode a parcel whose street number/name does not match the request.
    from services.address_identity import parcel_identity_match
    _resolved_label = results[0].get("address") or ""
    if not parcel_identity_match(address, _resolved_label):
        raise ValueError(
            f"Address could not be uniquely resolved: requested {address!r} "
            f"resolved to {_resolved_label!r}"
        )
    prop_id = results[0]["propId"]

    # Step 2: propId → lot geometry → WGS84 centroid
    for attempt in range(2):
        try:
            lot_r = requests.get(
                f"{NSW_PLANNING_BASE}/viewersf/V1/ePlanningApi/lot",
                params={"propId": prop_id},
                headers=NSW_PLANNING_HEADERS,
                timeout=20,
            )
            lot_r.raise_for_status()
            break
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if attempt == 1:
                raise ValueError("NSW Planning Portal timed out — try again in a few minutes")
            time.sleep(2)
    lots = lot_r.json()
    if not lots:
        raise ValueError(f"No lot geometry for propId={prop_id}")
    geom = lots[0].get("geometry") or {}
    rings = geom.get("rings") or []
    if not rings or not rings[0]:
        raise ValueError(f"Lot geometry has no rings for propId={prop_id}")
    ring = rings[0]
    cx = sum(pt[0] for pt in ring) / len(ring)
    cy = sum(pt[1] for pt in ring) / len(ring)
    lat, lon = _mercator_to_wgs84(cx, cy)

    # Step 3: council name from spatial_overlays
    council = _get_council_from_db(lat, lon)

    return lat, lon, council

# ---------------------------------------------------------------------------
# Layer 2 — Tessera embedding timeline (neighbourhood-normalised)
# ---------------------------------------------------------------------------

def _sample_embeddings(points: list[tuple[float, float]], years: list[int]) -> dict[int, np.ndarray | None]:
    """
    Sample Tessera embeddings for a list of (lon, lat) points and average them.
    Returns dict of year → averaged 128-dim embedding, or None if no valid points.
    """
    from geotessera import GeoTessera
    gt = GeoTessera()
    return _sample_embeddings_with_client(gt, points, years)


def _sample_embeddings_with_client(gt, points: list[tuple[float, float]], years: list[int]) -> dict[int, np.ndarray | None]:
    """Sample embeddings using a pre-existing GeoTessera client (avoids duplicate tile caches)."""
    result = {}
    for year in years:
        emb = gt.sample_embeddings_at_points(points, year=year)
        valid = emb[~np.isnan(emb).any(axis=1)]
        result[year] = valid.mean(axis=0).astype(np.float32) if len(valid) > 0 else None
    return result


def _lot_points(lat: float, lon: float) -> list[tuple[float, float]]:
    """5-point sampling: centroid + 4 interior corners at ~16m offset."""
    OFFSET = 0.00015  # ~16m at Sydney latitude
    return [
        (lon, lat),
        (lon + OFFSET, lat + OFFSET),
        (lon - OFFSET, lat + OFFSET),
        (lon + OFFSET, lat - OFFSET),
        (lon - OFFSET, lat - OFFSET),
    ]


def sample_lot_embeddings(lat: float, lon: float) -> dict[int, np.ndarray | None]:
    return _sample_embeddings(_lot_points(lat, lon), YEARS)


def _nbhd_points(lat: float, lon: float) -> list[tuple[float, float]]:
    """8-point ring at ~40m from lot centroid (reduced from 16 to cut memory)."""
    OFFSET_NEAR = 0.00025  # ~28m
    OFFSET_FAR = 0.00050   # ~55m
    r_avg = (OFFSET_NEAR + OFFSET_FAR) / 2
    return [
        (lon + r_avg * math.cos(math.radians(a)), lat + r_avg * math.sin(math.radians(a)))
        for a in range(0, 360, 45)  # 8 points
    ]


def sample_neighbourhood_embeddings(lat: float, lon: float) -> dict[int, np.ndarray | None]:
    return _sample_embeddings(_nbhd_points(lat, lon), YEARS)


def _consecutive_covered_pairs(covered_years: set[int], years: list[int]) -> int:
    """Count (N-1, N) pairs where BOTH years have published tile coverage.

    The similarity timeline is year-on-year cosine similarity, so a year only
    yields a data point when the previous year is covered too.
    """
    ordered = sorted(years)
    return sum(
        1 for i in range(1, len(ordered))
        if ordered[i - 1] in covered_years and ordered[i] in covered_years
    )


def check_tessera_coverage(gt, lat: float, lon: float, years: list[int]) -> set[int]:
    """Registry-only pre-flight: which years have a published Tessera tile
    intersecting the lot + neighbourhood sample points.

    Uses the registry manifest (no tile downloads). Sampling an uncovered tile
    returns NaN rows silently, so this is the only way to distinguish "no
    coverage published" from "download failed" before the heavy run.
    """
    pts = _lot_points(lat, lon) + _nbhd_points(lat, lon)
    lons = [p[0] for p in pts]
    lats = [p[1] for p in pts]
    bounds = (min(lons), min(lats), max(lons), max(lats))
    covered: set[int] = set()
    for year in years:
        if next(iter(gt.registry.iter_tiles_in_region(bounds, year)), None) is not None:
            covered.add(year)
    return covered


def compute_similarity_timeline(
    lot_embs: dict[int, np.ndarray | None],
) -> dict[int, float | None]:
    """
    Year-on-year cosine similarity. Key: year N. Value: sim(year N-1, year N).
    Returns None for years where embedding is missing.
    """
    timeline: dict[int, float | None] = {}
    sorted_years = sorted(lot_embs.keys())
    for i in range(1, len(sorted_years)):
        prev_y, curr_y = sorted_years[i - 1], sorted_years[i]
        e_prev, e_curr = lot_embs.get(prev_y), lot_embs.get(curr_y)
        if e_prev is None or e_curr is None:
            timeline[curr_y] = None
            continue
        norm_prev = np.linalg.norm(e_prev)
        norm_curr = np.linalg.norm(e_curr)
        if norm_prev == 0 or norm_curr == 0:
            timeline[curr_y] = None
            continue
        timeline[curr_y] = float(np.dot(e_prev, e_curr) / (norm_prev * norm_curr))
    return timeline

# ---------------------------------------------------------------------------
# Layer 3 — Sentinel-2 NDVI/NDBI timeline
# ---------------------------------------------------------------------------

# SCL clean pixel classes: 4=vegetation, 5=bare_soil, 6=water, 11=snow/ice
_SCL_CLEAN = {4, 5, 6, 11}
_MAX_SCENES_PER_YEAR = 3  # top-N least-cloudy scenes for median composite


def _sample_3x3_median(src, native_x: float, native_y: float) -> float | None:
    """Read a 3x3 window around the point and return the median non-zero value."""
    import rasterio as _rio
    row, col = src.index(native_x, native_y)
    # Clamp to raster bounds
    row = max(1, min(row, src.height - 2))
    col = max(1, min(col, src.width - 2))
    window = _rio.windows.Window(col - 1, row - 1, 3, 3)
    data = src.read(1, window=window).flatten().astype(float)
    valid = data[data > 0]
    if len(valid) == 0:
        return None
    return float(np.median(valid))


def _fetch_ndvi_ndbi_year(year: int, lat: float, lon: float, bbox: list) -> tuple[int, dict]:
    """
    Fetch Sentinel-2 NDVI + NDBI for a single year. Thread-safe — own STAC client.

    Noise reduction (3 layers):
      1. SCL cloud mask — skip scenes where the target pixel is cloud/shadow
      2. Multi-scene median — median across top-N clean scenes per year
      3. 3x3 spatial median — median of 9 pixels per scene (catches edge noise)
    """
    import pystac_client
    import rasterio
    from pyproj import Transformer

    null = {"ndvi": None, "ndbi": None}
    catalog = pystac_client.Client.open(ELEMENT84_URL)
    items = catalog.search(
        collections=["sentinel-2-l2a"],
        bbox=bbox,
        datetime=f"{year}-06-01/{year}-09-30",  # dry season — minimises cloud
        query={"eo:cloud_cover": {"lt": 20}},
    ).item_collection()

    if not items:
        return year, null

    # Sort by cloud cover, take top N
    items_sorted = sorted(items, key=lambda x: x.properties.get("eo:cloud_cover", 100))
    candidates = items_sorted[:_MAX_SCENES_PER_YEAR]

    ndvi_samples: list[float] = []
    ndbi_samples: list[float] = []

    for item in candidates:
        try:
            epsg = item.properties.get("proj:epsg", 32756)
            tx = Transformer.from_crs("EPSG:4326", f"EPSG:{epsg}", always_xy=True)
            native_x, native_y = tx.transform(lon, lat)

            # Fix 1: SCL cloud mask check — skip contaminated pixels
            if "scl" in item.assets:
                with rasterio.open(item.assets["scl"].href) as scl_src:
                    scl_val = list(scl_src.sample([(native_x, native_y)]))[0][0]
                    if scl_val is None or int(scl_val) not in _SCL_CLEAN:
                        continue  # cloud, shadow, or cirrus — skip this scene

            # Fix 3: 3x3 spatial median per band
            # Element84 asset names: B08 (NIR) → "nir", B04 (Red) → "red", B11 (SWIR) → "swir16"
            with (
                rasterio.open(item.assets["nir"].href) as nir_src,
                rasterio.open(item.assets["red"].href) as red_src,
                rasterio.open(item.assets["swir16"].href) as swir_src,
            ):
                b8_raw = _sample_3x3_median(nir_src, native_x, native_y)
                b4_raw = _sample_3x3_median(red_src, native_x, native_y)
                b11_raw = _sample_3x3_median(swir_src, native_x, native_y)

            if b8_raw is None or b4_raw is None or b11_raw is None:
                continue

            b8, b4, b11 = b8_raw / 10000.0, b4_raw / 10000.0, b11_raw / 10000.0

            if b8 + b4 > 0:
                ndvi_samples.append((b8 - b4) / (b8 + b4))
            if b11 + b8 > 0:
                ndbi_samples.append((b11 - b8) / (b11 + b8))
        except Exception as exc:
            logger.debug(f"Sentinel-2 {year} scene {item.id}: {exc}")
            continue

    # Fix 2: median across clean scenes
    ndvi = float(np.median(ndvi_samples)) if ndvi_samples else None
    ndbi = float(np.median(ndbi_samples)) if ndbi_samples else None

    return year, {"ndvi": ndvi, "ndbi": ndbi}


def get_ndvi_ndbi_timeline(lat: float, lon: float) -> dict[int, dict]:
    """
    For each year 2017–2025, fetch Sentinel-2 L2A and compute NDVI + NDBI at centroid.
    Uses Element84 Earth Search — free, no auth. Parallelised across years.

    CRS note: Element84 COGs are in native UTM. Must transform (lon, lat) from
    EPSG:4326 → raster CRS before rasterio.sample(). Pattern from flood_truth.py.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    try:
        import pystac_client  # noqa: F401
        import rasterio  # noqa: F401
        from pyproj import Transformer  # noqa: F401
    except ImportError:
        logger.warning("pystac_client, rasterio, or pyproj not installed — NDVI/NDBI skipped")
        return {y: {"ndvi": None, "ndbi": None} for y in YEARS}

    bbox = [lon - 0.001, lat - 0.001, lon + 0.001, lat + 0.001]
    results: dict[int, dict] = {}

    with ThreadPoolExecutor(max_workers=5) as pool:
        futures = {
            pool.submit(_fetch_ndvi_ndbi_year, y, lat, lon, bbox): y for y in YEARS
        }
        for fut in as_completed(futures):
            year = futures[fut]
            try:
                _, result = fut.result(timeout=45)
                results[year] = result
            except Exception as exc:
                logger.debug(f"Sentinel-2 {year}: {exc}")
                results[year] = {"ndvi": None, "ndbi": None}

    return results


def compute_ndvi_ndbi_deltas(timeline: dict[int, dict]) -> dict[int, dict]:
    """Year-on-year delta. Key: year N. Values: ndvi_delta, ndbi_delta (None if missing)."""
    deltas: dict[int, dict] = {}
    sorted_years = sorted(timeline.keys())
    for i in range(1, len(sorted_years)):
        prev, curr = sorted_years[i - 1], sorted_years[i]
        p, c = timeline.get(prev, {}), timeline.get(curr, {})
        ndvi_d = (
            c["ndvi"] - p["ndvi"]
            if c.get("ndvi") is not None and p.get("ndvi") is not None
            else None
        )
        ndbi_d = (
            c["ndbi"] - p["ndbi"]
            if c.get("ndbi") is not None and p.get("ndbi") is not None
            else None
        )
        deltas[curr] = {"ndvi_delta": ndvi_d, "ndbi_delta": ndbi_d}
    return deltas

# ---------------------------------------------------------------------------
# Layer 4 — NSW ePlanning DA/CC/OC events
# Filter format confirmed from threat_radar.py: {"filters": {"CouncilName": [council], ...}}
# Field paths confirmed from check2b_eplanning_fields.py:
#   Location[0].X (lon WGS84), Location[0].Y (lat WGS84), Location[0].FullAddress
#   DevelopmentType[0].DevelopmentType, Council.CouncilName, DateLastUpdated
# ---------------------------------------------------------------------------

def _extract_da_fields(rec: dict) -> dict:
    """Flatten a raw ePlanning response record to a standard dict."""
    loc = (rec.get("Location") or [{}])[0]
    dev_types = [(d.get("DevelopmentType") or "") for d in (rec.get("DevelopmentType") or [])]
    date_updated = rec.get("DateLastUpdated") or ""
    dev_type = "; ".join(t for t in dev_types if t)
    return {
        "pan": rec.get("PlanningPortalApplicationNumber"),
        "status": rec.get("ApplicationStatus"),
        "app_type": rec.get("ApplicationType"),
        "dev_type": dev_type,
        "date_updated": date_updated,
        "date": date_updated[:10],  # YYYY-MM-DD alias for consumers
        "description": dev_type or rec.get("ApplicationType", ""),
        "address": loc.get("FullAddress", ""),
        "suburb": loc.get("Suburb", ""),
        "lon": float(loc["X"]) if loc.get("X") else None,
        "lat": float(loc["Y"]) if loc.get("Y") else None,
    }


def _fetch_eplanning_page(endpoint: str, filters: dict, page: int) -> list[dict]:
    """
    Single paginated call to OnlineDA or OnlineCDC.
    Filters must be the inner dict — this function wraps them in the {"filters": ...} envelope.
    """
    r = requests.get(
        f"{EPLANNING_BASE}/{endpoint}",
        headers={
            "filters": json.dumps({"filters": filters}),
            "PageSize": "50",
            "PageNumber": str(page),
            "Cache-Control": "no-cache",
        },
        timeout=20,
    )
    r.raise_for_status()
    data = r.json()
    return data.get("Application") or data.get("ApplicationList") or []


def get_da_events(council: str, address_fragment: str) -> list[dict]:
    """
    Fetch DA and CDC events for a council, fuzzy-filter to the target address.
    Uses DateLastUpdated as proxy for event year (LodgementDate not in API response).
    """
    from rapidfuzz import fuzz

    results = []
    for app_type in ["Development Application", "Complying Development Certificate"]:
        page = 1
        while page <= EPLANNING_MAX_PAGES:
            try:
                batch = _fetch_eplanning_page(
                    "OnlineDA",
                    {"CouncilName": [council], "ApplicationType": app_type},
                    page,
                )
            except Exception as exc:
                logger.warning(f"ePlanning OnlineDA page {page}: {exc}")
                break
            results.extend(batch)
            if len(batch) < 50:
                break
            page += 1
            time.sleep(0.4)

    matched = []
    for rec in results:
        flat = _extract_da_fields(rec)
        if fuzz.partial_ratio(address_fragment.lower(), flat["address"].lower()) > 75:
            matched.append(flat)
    return matched


def get_pcc_events(council: str, address_fragment: str) -> list[dict]:
    """Fetch CC/OC events for a council, fuzzy-filter to the target address."""
    from rapidfuzz import fuzz

    results = []
    for app_type in ["Construction Certificate", "Occupation Certificate"]:
        page = 1
        while page <= EPLANNING_MAX_PAGES:
            try:
                batch = _fetch_eplanning_page(
                    "OnlineCDC",
                    {"CouncilName": [council], "ApplicationType": app_type},
                    page,
                )
            except Exception as exc:
                logger.warning(f"ePlanning OnlineCDC page {page}: {exc}")
                break
            results.extend(batch)
            if len(batch) < 50:
                break
            page += 1
            time.sleep(0.4)

    matched = []
    for rec in results:
        flat = _extract_da_fields(rec)
        if fuzz.partial_ratio(address_fragment.lower(), flat["address"].lower()) > 75:
            matched.append(flat)
    return matched

# ---------------------------------------------------------------------------
# Layer 5 — Heritage flag (PostGIS spatial_overlays)
# ---------------------------------------------------------------------------

def check_heritage_flag(lat: float, lon: float) -> dict:
    """Query PostGIS for heritage overlay at point. Returns flag + note.
    Pattern matched to solar_yield.py:_check_heritage (confirmed working).
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT 1 FROM spatial_overlays
                WHERE layer_type = 'heritage'
                  AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                LIMIT 1
                """,
                (lon, lat),
            )
            found = cur.fetchone() is not None
        return {
            "flag": found,
            "note": "Within a heritage overlay — any works may require a Statement of Heritage Impact" if found else None,
        }
    except Exception as exc:
        logger.warning(f"Heritage flag query failed: {exc}")
        return {"flag": False, "note": None}
    finally:
        if conn:
            conn.close()

# ---------------------------------------------------------------------------
# Layer 6 — Flood/fire event annotation
# ---------------------------------------------------------------------------

def get_flood_annotations(lat: float, lon: float, change_year: int) -> list[str]:
    return [
        f"Known flood event: {e['name']}"
        for e in NSW_FLOOD_EVENTS
        if e["year"] == change_year
        and e["bbox"][0] <= lon <= e["bbox"][2]
        and e["bbox"][1] <= lat <= e["bbox"][3]
    ]


def get_fire_annotations(lat: float, lon: float, change_year: int) -> list[str]:
    return [
        f"Known bushfire event: {e['name']}"
        for e in NSW_FIRE_EVENTS
        if e["year"] == change_year
        and e["bbox"][0] <= lon <= e["bbox"][2]
        and e["bbox"][1] <= lat <= e["bbox"][3]
    ]

# ---------------------------------------------------------------------------
# Layer 7 — Wayback SSIM comparison (small lots <300 m²)
# ---------------------------------------------------------------------------

def get_wayback_releases() -> list[dict]:
    """
    Fetch all Wayback releases with dates.
    Confirmed endpoint and format (scripts/check1_wayback.py):
      - URL: {WAYBACK_META_URL}?f=json
      - Returns Selection array; release number = M field; date parsed from Name string.
    """
    r = requests.get(WAYBACK_META_URL, params={"f": "json"}, timeout=15)
    raw = r.json().get("Selection") or []
    releases = []
    for x in raw:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", x.get("Name") or "")
        date_str = m.group(1) if m else ""
        releases.append({
            "releaseNum": x["M"],
            "date": date_str,
            "name": x.get("Name", ""),
        })
    return sorted(releases, key=lambda x: x["date"])


def _tile_coords(lat: float, lon: float, zoom: int) -> tuple[int, int]:
    """Convert WGS84 to XYZ tile coordinates at given zoom."""
    n = 2 ** zoom
    tx = int((lon + 180.0) / 360.0 * n)
    lat_rad = math.radians(lat)
    ty = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
    return tx, ty


def fetch_wayback_tile(release_num: int, lat: float, lon: float, zoom: int = 19):
    """Fetch a single Wayback tile. Returns PIL.Image or None."""
    try:
        from PIL import Image
        tx, ty = _tile_coords(lat, lon, zoom)
        url = WAYBACK_TILE_URL.format(release=release_num, z=zoom, y=ty, x=tx)
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            return Image.open(io.BytesIO(r.content)).convert("RGB")
    except Exception as exc:
        logger.debug(f"Wayback tile {release_num}: {exc}")
    return None


def compute_wayback_ssim_timeline(
    lat: float, lon: float, releases: list[dict]
) -> dict[str, float]:
    """
    For each consecutive pair of Wayback releases (filtered to one-per-year),
    compute SSIM between greyscale tiles.
    Returns dict of "YYYY-YYYY" → ssim_score (1.0 = identical).
    """
    try:
        from skimage.metrics import structural_similarity as ssim
        import numpy as np
    except ImportError:
        logger.warning("scikit-image not installed — Wayback SSIM skipped")
        return {}

    # Pick one release per year (latest in each year)
    by_year: dict[str, dict] = {}
    for rel in releases:
        year = rel["date"][:4]
        if year >= "2017":
            by_year[year] = rel  # last entry per year wins (sorted ascending)

    sorted_years = sorted(by_year.keys())
    ssim_timeline = {}

    for i in range(1, len(sorted_years)):
        prev_y, curr_y = sorted_years[i - 1], sorted_years[i]
        img_prev = fetch_wayback_tile(by_year[prev_y]["releaseNum"], lat, lon)
        img_curr = fetch_wayback_tile(by_year[curr_y]["releaseNum"], lat, lon)
        if img_prev is None or img_curr is None:
            continue
        try:
            import numpy as np
            a = np.array(img_prev.convert("L"))
            b = np.array(img_curr.convert("L"))
            score, _ = ssim(a, b, full=True)
            ssim_timeline[f"{prev_y}-{curr_y}"] = float(score)
        except Exception as exc:
            logger.debug(f"SSIM {prev_y}→{curr_y}: {exc}")

    return ssim_timeline

# ---------------------------------------------------------------------------
# Layer 8 — Timeline annotation
# ---------------------------------------------------------------------------

def _classify_change(similarity: float) -> dict:
    if similarity >= SIM_STABLE:
        return {"level": "stable", "label": "No significant change detected", "color": "green"}
    if similarity >= SIM_MINOR:
        return {"level": "minor", "label": "Minor change detected", "color": "yellow"}
    if similarity >= SIM_MODERATE:
        return {"level": "moderate", "label": "Moderate physical change detected", "color": "orange"}
    return {"level": "major", "label": "Major physical change detected", "color": "red"}


def build_year_annotation(
    year: int,
    similarity: float,
    neighbourhood_similarity: float | None,
    ndvi_delta: float | None,
    ndbi_delta: float | None,
    da_events: list[dict],
    flood_annotations: list[str],
    fire_annotations: list[str],
) -> dict:
    """
    Produce a single annotated year entry for the timeline.
    Applies: neighbourhood suppression → NDVI/NDBI disambiguation → DA cross-reference.
    """
    # Step 1: neighbourhood-adjusted suppression
    # Only suppress if BOTH the Tessera delta is within noise AND the NDVI/NDBI
    # deltas are insignificant. Strong spectral signals (vegetation loss, built-up
    # increase) override Tessera neighbourhood similarity.
    if neighbourhood_similarity is not None:
        delta = similarity - neighbourhood_similarity
        ndvi_significant = ndvi_delta is not None and ndvi_delta < -0.10
        ndbi_significant = ndbi_delta is not None and ndbi_delta > 0.05
        if abs(delta) < 0.04 and not ndvi_significant and not ndbi_significant:
            return {
                "year": year,
                "level": "stable",
                "label": "No lot-specific change (systemic environmental event suppressed)",
                "color": "green",
                "suppressed": True,
                "ndvi_delta": round(ndvi_delta, 3) if ndvi_delta is not None else None,
                "ndbi_delta": round(ndbi_delta, 3) if ndbi_delta is not None else None,
                "da_events": [],
            }

    # Step 2: base Tessera classification
    classification = _classify_change(similarity)
    classification["similarity"] = round(similarity, 3)

    # Step 3: NDVI/NDBI disambiguation
    change_type = "unknown"
    if ndvi_delta is not None and ndbi_delta is not None:
        ndvi_drop = ndvi_delta < -0.05
        ndbi_rise = ndbi_delta > 0.03
        if ndvi_drop and ndbi_rise:
            change_type = "construction"
        elif ndvi_drop and not ndbi_rise:
            change_type = "vegetation"
        elif not ndvi_drop and ndbi_rise:
            change_type = "hardening"
        else:
            change_type = "noise"
            if classification["level"] in ("stable", "minor"):
                return {
                    "year": year,
                    "level": "stable",
                    "label": "No significant change detected",
                    "color": "green",
                    "similarity": round(similarity, 3),
                    "change_type": "noise",
                    "da_events": [],
                }

    # Step 3b: spectral escalation — strong NDVI/NDBI overrides Tessera "stable"
    # Tessera embeddings are 10m neighbourhood-scale features. A single tree removal
    # or driveway pour may not register in the embedding but shows clearly in NDVI/NDBI.
    if classification["level"] == "stable" and change_type in ("construction", "vegetation", "hardening"):
        strong_ndvi = ndvi_delta is not None and ndvi_delta < -0.15
        strong_ndbi = ndbi_delta is not None and ndbi_delta > 0.08
        if strong_ndvi or strong_ndbi:
            classification["level"] = "minor"
            classification["color"] = "yellow"
            classification["label"] = "Minor change detected"
            classification["spectral_escalation"] = True

    # Step 4: DA event cross-reference
    # Use date_updated year as proxy for event year (LodgementDate not in API response)
    das_this_year = [d for d in da_events if (d.get("date_updated") or "")[:4] == str(year)]
    ccs_this_year = [
        d for d in da_events
        if (d.get("date_updated") or "")[:4] == str(year)
        and "Certificate" in (d.get("app_type") or "")
    ]
    tree_removal_das = [d for d in das_this_year if "tree" in (d.get("dev_type") or "").lower()]

    explanation = []

    if das_this_year and not tree_removal_das:
        types = list({d.get("dev_type") for d in das_this_year if "tree" not in (d.get("dev_type") or "").lower()})
        if types:
            explanation.append(f"DA lodged: {', '.join(t for t in types if t)}")
    if ccs_this_year:
        explanation.append("Construction/occupation certificate issued")

    if tree_removal_das:
        explanation.append("Tree removal permit lodged")
        if change_type in ("vegetation", "unknown"):
            classification["label"] = "Vegetation removal — tree removal permit on record"
            classification["level"] = "minor"

    if not das_this_year and change_type != "unknown":
        if change_type == "vegetation" and classification["level"] in ("minor", "moderate"):
            classification["label"] = "Vegetation change — no DA on record (clearing, storm damage, or drought)"
        elif change_type == "construction":
            classification["label"] = "Physical change consistent with construction works"
        elif change_type == "hardening":
            classification["label"] = "Surface hardening detected — possible paving or minor structures"

    # Flood/fire annotations (moderate/major changes only)
    if classification["level"] in ("moderate", "major"):
        explanation.extend(flood_annotations)
        explanation.extend(fire_annotations)

    if explanation:
        classification["explanation"] = "; ".join(explanation)
    classification["change_type"] = change_type
    classification["da_events"] = [
        {
            "pan": d["pan"],
            "status": d.get("status"),
            "app_type": d.get("app_type"),
            "dev_type": d.get("dev_type"),
            "date": d.get("date"),
        }
        for d in das_this_year
    ]

    return {"year": year, **classification}


def annotate_timeline(
    similarity_timeline: dict[int, float | None],
    neighbourhood_timeline: dict[int, float | None],
    ndvi_ndbi_deltas: dict[int, dict],
    da_events: list[dict],
    lat: float,
    lon: float,
) -> list[dict]:
    result = []
    for year, similarity in sorted(similarity_timeline.items()):
        if similarity is None:
            result.append({"year": year, "level": "no_data", "label": "Satellite data unavailable"})
            continue

        annotation = build_year_annotation(
            year=year,
            similarity=similarity,
            neighbourhood_similarity=neighbourhood_timeline.get(year),
            ndvi_delta=ndvi_ndbi_deltas.get(year, {}).get("ndvi_delta"),
            ndbi_delta=ndvi_ndbi_deltas.get(year, {}).get("ndbi_delta"),
            da_events=da_events,
            flood_annotations=get_flood_annotations(lat, lon, year),
            fire_annotations=get_fire_annotations(lat, lon, year),
        )
        result.append(annotation)
    return result

# ---------------------------------------------------------------------------
# FastAPI endpoint
# ---------------------------------------------------------------------------

class PreDAHistoryRequest(BaseModel):
    address: str
    lot_area_m2: Optional[float] = None  # If known; drives Wayback SSIM decision
    report_id: Optional[str] = None      # Pre-allocated row UUID from Next.js (async flow)


def _build_refusal(
    req: "PreDAHistoryRequest",
    lat: float,
    lon: float,
    council: str,
    reason_code: str,
    reason: str,
    covered_years: Optional[set[int]],
) -> dict:
    """Fail-closed refusal (mirrors flood_truth's ``refused`` pattern).

    Marks the pre-allocated async row as errored so the frontend poll surfaces
    a failure instead of hanging or presenting an empty report as complete.
    """
    _mark_error(req.report_id, reason)
    return {
        "address": req.address,
        "lat": lat,
        "lon": lon,
        "council": council,
        "run_date": date.today().isoformat(),
        "refused": True,
        "reason_code": reason_code,
        "reason": reason,
        "covered_years": sorted(covered_years) if covered_years is not None else None,
        "years_requested": YEARS,
    }


@router.post("/pre-da-history")
def run_pre_da_history(req: PreDAHistoryRequest):
    """
    Generate a Pre-DA Site History Report for a NSW property address.

    When report_id is provided (async Trigger.dev flow), the pre-allocated row is
    UPDATEd with status='complete'. Otherwise a new row is INSERTed (dev / direct call).
    """
    try:
        return _run_pre_da_history_inner(req)
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Pipeline crashed: {exc}", exc_info=True)
        _mark_error(req.report_id, f"Pipeline crashed: {exc}")
        raise HTTPException(status_code=500, detail=f"Pipeline failed: {exc}")


def _run_pre_da_history_inner(req: PreDAHistoryRequest):
    # --- Audit trail: data source query objects ---
    ds_geocode = DataSourceQuery(
        "NSW Planning Portal geocode",
        f"{NSW_PLANNING_BASE}/viewersf/V1/ePlanningApi/address",
        {"address": req.address},
    )
    ds_tessera = DataSourceQuery(
        "GeoTessera Clay v1.5 embeddings",
        "local:geotessera",
        {"years": f"{YEARS[0]}-{YEARS[-1]}"},
    )
    ds_sentinel2 = DataSourceQuery(
        "Element84 Sentinel-2 L2A (NDVI/NDBI)",
        ELEMENT84_URL,
        {"collections": "sentinel-2-l2a"},
    )
    ds_eplanning = DataSourceQuery(
        "NSW ePlanning DA/CC/OC",
        f"{EPLANNING_BASE}/OnlineDA",
        {"address": req.address},
    )
    ds_heritage = DataSourceQuery(
        "PostGIS heritage overlay",
        "local:spatial_overlays",
        {"layer_type": "heritage"},
    )

    # --- Geocode ---
    try:
        lat, lon, council = geocode_address(req.address)
        ds_geocode.record_response({"lat": lat, "lon": lon, "council": council}, features_returned=1)
    except ValueError as exc:
        ds_geocode.record_error(str(exc))
        _mark_error(req.report_id, str(exc))
        raise HTTPException(status_code=422, detail=str(exc))

    # Update query params now that we have coordinates
    ds_sentinel2.query_params.update({"lat": lat, "lon": lon})
    ds_eplanning.query_params.update({"council": council})
    ds_heritage.query_params.update({"lat": lat, "lon": lon})

    # --- Fail-closed pre-flight: published Tessera coverage (issue #751) ---
    # Sampling an uncovered tile returns NaN rows with only a stderr warning,
    # which collapses the whole timeline to no_data AFTER ~130s of work. The
    # registry manifest knows coverage up front — refuse before the heavy run.
    # A failure of the check itself is NOT a coverage gap: proceed, and the
    # all-no_data backstop below still fails the run closed.
    from geotessera import GeoTessera

    gt = None
    covered_years: Optional[set[int]] = None
    try:
        gt = GeoTessera()
        covered_years = check_tessera_coverage(gt, lat, lon, YEARS)
    except Exception as exc:
        logger.warning(
            f"Tessera coverage pre-flight failed ({exc}) — proceeding to sampling"
        )

    if covered_years is not None:
        ds_tessera.query_params.update({"covered_years": sorted(covered_years)})
        if _consecutive_covered_pairs(covered_years, YEARS) < MIN_CONSECUTIVE_COVERED_PAIRS:
            ds_tessera.record_response(
                {"covered_years": sorted(covered_years), "consecutive_pairs": 0},
                features_returned=0,
            )
            logger.warning(
                f"Pre-DA refused (no Tessera coverage): {req.address} "
                f"covered_years={sorted(covered_years)}"
            )
            return _build_refusal(
                req, lat, lon, council,
                reason_code="satellite_coverage_unavailable",
                reason=(
                    "Satellite embedding coverage is not published for this "
                    "location for two consecutive years, so the year-on-year "
                    "change timeline cannot be computed. No report was generated."
                ),
                covered_years=covered_years,
            )

    # --- Parallel pipeline ---
    # Tessera runs sequentially (single GeoTessera instance to avoid OOM from
    # duplicate tile caches). NDVI/NDBI, DA events, and heritage run in parallel
    # alongside tessera since they don't use geotessera.
    from concurrent.futures import ThreadPoolExecutor

    def _ndvi_ndbi():
        raw = get_ndvi_ndbi_timeline(lat, lon)
        return compute_ndvi_ndbi_deltas(raw)

    def _da_events():
        if council:
            return get_da_events(council, req.address) + get_pcc_events(council, req.address)
        logger.warning(f"Council not resolved for {req.address} — DA events skipped")
        return []

    # Start non-tessera work in background
    with ThreadPoolExecutor(max_workers=3) as pool:
        fut_ndvi = pool.submit(_ndvi_ndbi)
        fut_da = pool.submit(_da_events)
        fut_heritage = pool.submit(check_heritage_flag, lat, lon)

        # Tessera runs in main thread — single GeoTessera instance shared
        # between lot and neighbourhood to avoid duplicate tile downloads.
        # GC between passes to release numpy arrays from lot embeddings.
        import gc
        if gt is None:  # pre-flight construction failed — surface the error here
            gt = GeoTessera()

        lot_embs = _sample_embeddings_with_client(gt, _lot_points(lat, lon), YEARS)
        similarity_timeline = compute_similarity_timeline(lot_embs)
        del lot_embs
        gc.collect()

        nbhd_embs = _sample_embeddings_with_client(gt, _nbhd_points(lat, lon), YEARS)
        neighbourhood_sim_timeline = compute_similarity_timeline(nbhd_embs)
        del nbhd_embs, gt
        gc.collect()

        # Collect background results
        ndvi_ndbi_deltas = fut_ndvi.result()
        all_da = fut_da.result()
        heritage = fut_heritage.result()

    # Record audit trail responses for parallel queries
    tessera_years_available = sum(1 for v in similarity_timeline.values() if v is not None)
    ds_tessera.record_response(
        {"years_with_data": tessera_years_available},
        features_returned=tessera_years_available,
    )

    ndvi_years_available = sum(
        1 for v in ndvi_ndbi_deltas.values()
        if v.get("ndvi_delta") is not None
    )
    ds_sentinel2.record_response(
        {"years_with_deltas": ndvi_years_available},
        features_returned=ndvi_years_available,
    )

    ds_eplanning.record_response(
        {"da_count": len(all_da)},
        features_returned=len(all_da),
    )

    ds_heritage.record_response(
        heritage,
        features_returned=1 if heritage.get("flag") else 0,
    )

    # --- Wayback SSIM (small lots only) ---
    ds_wayback: DataSourceQuery | None = None
    wayback_ssim: dict[str, float] = {}
    if req.lot_area_m2 is not None and req.lot_area_m2 < SMALL_LOT_THRESHOLD_M2:
        ds_wayback = DataSourceQuery(
            "Esri World Imagery Wayback",
            WAYBACK_META_URL,
            {"lat": lat, "lon": lon, "lot_area_m2": req.lot_area_m2},
        )
        try:
            releases = get_wayback_releases()
            wayback_ssim = compute_wayback_ssim_timeline(lat, lon, releases)
            ds_wayback.record_response(
                {"pairs_compared": len(wayback_ssim)},
                features_returned=len(wayback_ssim),
            )
        except Exception as exc:
            ds_wayback.record_error(str(exc))
            logger.warning(f"Wayback SSIM skipped: {exc}")

    # --- Annotate ---
    timeline = annotate_timeline(
        similarity_timeline, neighbourhood_sim_timeline, ndvi_ndbi_deltas, all_da, lat, lon
    )

    # --- Backstop gate (issue #751): an all-no_data timeline is not a report ---
    # Catches whatever the registry pre-flight could not see up front (tile
    # download failures, NaN tiles, a pre-flight that errored and was skipped).
    if timeline and all(entry.get("level") == "no_data" for entry in timeline):
        return _build_refusal(
            req, lat, lon, council,
            reason_code="satellite_timeline_empty",
            reason=(
                "Satellite sampling returned no usable data for any year at "
                "this location, so the change timeline cannot be computed. "
                "No report was generated."
            ),
            covered_years=covered_years,
        )

    result = {
        "address": req.address,
        "lat": lat,
        "lon": lon,
        "council": council,
        "heritage_flag": heritage["flag"],
        "heritage_note": heritage.get("note"),
        "timeline": timeline,
        "wayback_ssim": wayback_ssim,
        "run_date": date.today().isoformat(),
        "data_quality_note": DATA_QUALITY_NOTE,
    }

    # --- Store to Supabase ---
    # DB write MUST succeed — if it fails, the frontend poll will hang on 'pending' forever.
    # Raise so Trigger.dev retries or the error propagates to the caller.
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            if req.report_id:
                # Async flow — UPDATE the pre-allocated row
                cur.execute(
                    """
                    UPDATE pre_da_history_reports
                    SET lat=%s, lon=%s, council=%s, report_json=%s,
                        status='complete', run_date=%s
                    WHERE id=%s
                    """,
                    (lat, lon, council, json.dumps(result), date.today(), req.report_id),
                )
                result["id"] = req.report_id
            else:
                # Direct / dev flow — INSERT new row and return id
                cur.execute(
                    """
                    INSERT INTO pre_da_history_reports
                        (address, lat, lon, council, report_json, status, run_date)
                    VALUES (%s, %s, %s, %s, %s, 'complete', %s)
                    RETURNING id
                    """,
                    (req.address, lat, lon, council, json.dumps(result), date.today()),
                )
                row = cur.fetchone()
                if row:
                    result["id"] = str(row[0])
        conn.commit()
    except Exception as exc:
        logger.error(f"Supabase write failed: {exc}")
        _mark_error(req.report_id, f"DB write failed: {exc}")
        raise HTTPException(status_code=503, detail="Report storage failed — please retry")
    finally:
        if conn:
            conn.close()

    # --- Audit trail (non-blocking — won't prevent report delivery on failure) ---
    notable_years = [
        entry["year"] for entry in timeline
        if entry.get("level") in ("minor", "moderate", "major")
    ]
    audit_data_sources = [ds_geocode, ds_tessera, ds_sentinel2, ds_eplanning, ds_heritage]
    if ds_wayback is not None:
        audit_data_sources.append(ds_wayback)

    log_audit_trail(
        report_id=result.get("id", req.report_id or "unknown"),
        pipeline_name="pre-da-history",
        input_params={
            "address": req.address,
            "lot_area_m2": req.lot_area_m2,
            "lat": lat,
            "lon": lon,
            "council": council,
        },
        data_sources=audit_data_sources,
        output_summary=result,
        disclaimer_version=get_current_disclaimer_version("pre-da-history"),
        intermediate_calculations={
            "notable_years_count": len(notable_years),
            "notable_years": notable_years,
            "da_count": len(all_da),
            "heritage_flag": heritage.get("flag", False),
            "wayback_ssim_pairs": len(wayback_ssim),
            "tessera_years_available": sum(1 for v in similarity_timeline.values() if v is not None),
            "ndvi_years_available": sum(
                1 for v in ndvi_ndbi_deltas.values()
                if v.get("ndvi_delta") is not None
            ),
        },
    )

    return result


def _mark_error(report_id: Optional[str], msg: str) -> None:
    """Mark a pre-allocated row as errored. Best-effort — never raises."""
    if not report_id:
        return
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE pre_da_history_reports SET status='error', error_msg=%s WHERE id=%s",
                (msg[:500], report_id),
            )
        conn.commit()
    except Exception as exc:
        logger.debug(f"_mark_error failed: {exc}")
    finally:
        if conn:
            conn.close()
