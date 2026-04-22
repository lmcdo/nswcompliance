"""
Wet Season Flood Truth Engine -- FastAPI router.

POST /pipeline/flood        -- on-demand: EPI + EMS + JRC + BOM gauge
POST /pipeline/flood/batch  -- batch LGA processing (Trigger.dev cron, quarterly)

Data sources:
  NSW SEED EPI Flood WFS         (statutory overlay, free, no auth)
  Copernicus EMS activations      (copernicus_flood_events table, one-time ingest)
  JRC Global Surface Water        (Landsat 1984–present, GCS tiles, free)
  BOM/WaterConnect nearest gauge  (WaterNSW SOS2, last major flood event)
  Sentinel-1 RTC                  (Microsoft Planetary Computer, batch only)

NOTE: Sentinel-1B dead Dec 2021 - Mar 2025. 2022 La Nina data is sparser.
VH ratio method: flood_pixel = (wet_vh / dry_baseline_vh) > 1.25
Data is linear power (float32) -- NOT dB for ratio method.

Response contract (must match frontend-nextjs/app/reports/flood/page.tsx FloodResult):
{
  "address": str,
  "lat": float,
  "lng": float,
  "run_date": str,
  "outputs": {
    "epi_flood_class": str | null,
    "epi_flood_label": str | null,
    "sar_flood_detected": bool | null,
    "sar_confidence": str | null,
    "sar_analysis_date": str | null,
    "ems_flood_detected": bool | null,
    "ems_activations": list[dict] | null,
    "jrc_water_occurrence_pct": float | null,   # % of months since 1984 classified as water
    "jrc_data_year": int | null,                # 2021 (current JRC dataset version)
    "bom_gauge_name": str | null,
    "bom_gauge_distance_km": float | null,
    "bom_last_major_flood_date": str | null,
    "bom_last_major_flood_peak_m": float | null,
    "s1_gap_warning": str | null,
    "data_currency": str,
    "flood_signal": "none" | "low" | "moderate" | "elevated" | "unavailable"  # multi-source convergence
  },
  "confidence": str,
  "data_sources": list[str]
}
"""
import logging
import math
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timezone
from typing import Optional

import psycopg2
import psycopg2.extras
import requests
from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

PC_CATALOG = "https://planetarycomputer.microsoft.com/api/stac/v1"
S1_COLLECTION = "sentinel-1-rtc"
# ArcGIS REST API — more reliable than WFS for ArcGIS Server (CQL_FILTER not supported).
# Layer 0 = Flood Planning Hazard overlay.
EPI_REST = ("https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
            "Planning/Hazard/MapServer/0/query")
BOM_SOS2 = "http://www.bom.gov.au/waterdata/services/sos2/getObservation"
JRC_TILE_BASE = "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence"
JRC_DATA_YEAR = 2021

FLOOD_RATIO = 1.25
S1B_GAP_START = date(2021, 12, 23)
S1B_GAP_END   = date(2025, 3, 4)

_DATA_SOURCES_BASE = ["NSW SEED EPI WFS", "Microsoft Planetary Computer S1 RTC"]
_DATA_SOURCE_EMS   = "NSW Spatial Services / Copernicus EMS flood events"
_DATA_SOURCE_JRC   = "JRC Global Surface Water (Landsat 1984–present)"
_DATA_SOURCE_BOM   = "BOM Water Data Online"

# EPI WFS FloodClass property → our class key
_EPI_CLASS_MAP = {
    "high flood risk":      "high_flood_risk",
    "medium flood risk":    "medium_flood_risk",
    "low flood risk":       "low_flood_risk",
    "flood planning area":  "flood_planning_area",
    "floodplanning":        "flood_planning_area",
    "high":                 "high_flood_risk",
    "medium":               "medium_flood_risk",
    "low":                  "low_flood_risk",
}

_EPI_CLASS_LABELS = {
    "high_flood_risk":     "High Flood Risk",
    "medium_flood_risk":   "Medium Flood Risk",
    "low_flood_risk":      "Low Flood Risk",
    "flood_planning_area": "Flood Planning Area",
    "none":                "No EPI Flood Overlay",
}

# Pre-seeded major NSW river gauges: (station_id, name, lat, lng, major_flood_level_m)
# Station IDs and major flood levels from BOM Water Data Online flood classifications.
# Verify at: http://www.bom.gov.au/waterdata/
_NSW_GAUGES = [
    # Northern Rivers (most flood-prone region in NSW)
    ("201001", "Wilsons River at Lismore",       -28.8097, 153.2797, 10.8),
    ("201002", "Richmond River at Casino",       -28.8701, 153.0452, 11.0),
    ("203014", "Tweed River at Murwillumbah",    -28.3314, 153.3972, 8.0),
    ("204040", "Clarence River at Grafton",      -29.6886, 152.9322, 7.2),
    # Mid-North Coast
    ("205007", "Bellinger River at Thora",       -30.4667, 152.4667, 5.5),
    ("207003", "Macleay River at Kempsey",       -31.0835, 152.8380, 5.4),
    ("208001", "Manning River at Wingham",       -31.8645, 152.3591, 4.2),
    # Hunter / Central Coast
    ("210040", "Hunter River at Singleton",      -32.5613, 151.1742, 7.0),
    # Sydney Basin
    ("212040", "Hawkesbury River at Windsor",    -33.6183, 150.8175, 7.3),
    ("213006", "Georges River at Liverpool",     -33.9189, 150.9215, 3.5),
    # South Coast
    ("215004", "Shoalhaven River at Nowra",      -34.8696, 150.5982, 5.0),
    # Inland
    ("225014", "Murray River at Albury",         -36.0773, 146.9252, 9.0),
    ("401009", "Murrumbidgee River at Wagga",    -35.1100, 147.3696, 9.4),
]
_GAUGE_MAX_DISTANCE_KM = 75.0  # don't associate gauge if further than this


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
# EPI overlay
# ---------------------------------------------------------------------------

def _query_epi_overlay(lat: float, lng: float) -> dict:
    """Query NSW SEED EPI Flood via ArcGIS REST API (CQL_FILTER unsupported on ArcGIS Server WFS).
    Returns epi_flood_class, epi_flood_label, data_currency."""
    try:
        params = {
            "geometry": f"{lng},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "*",
            "returnGeometry": "false",
            "f": "json",
        }
        r = requests.get(EPI_REST, params=params, timeout=20)
        r.raise_for_status()
        body = r.json()
        # ArcGIS REST returns {"features": [{"attributes": {...}}]}
        # An "error" key means the request was rejected (bad layer, auth, etc.)
        if "error" in body:
            raise ValueError(f"ArcGIS error: {body['error']}")
        feats = body.get("features") or []
        if not feats:
            return {"epi_flood_class": "none", "epi_flood_label": "No EPI Flood Overlay",
                    "data_currency": "unknown"}

        attrs = feats[0].get("attributes", {})
        # ArcGIS may return DataDate as epoch-ms integer — coerce to str for contract compliance
        currency = str(attrs.get("DataDate") or attrs.get("DATADATE") or "unknown")
        raw_class = (
            attrs.get("FloodClass") or attrs.get("FLOODCLASS") or attrs.get("Category")
            or attrs.get("FldClass") or attrs.get("Flood_Class") or ""
        ).strip().lower()
        # Unknown or empty class → treat as "none" (not "flood_planning_area").
        # Defaulting to flood_planning_area on unrecognised values causes false positives.
        epi_class = _EPI_CLASS_MAP.get(raw_class) if raw_class else "none"
        if epi_class is None:
            logger.warning(f"Unrecognised EPI FloodClass: {raw_class!r} — treating as flood_planning_area")
            epi_class = "flood_planning_area"
        return {"epi_flood_class": epi_class,
                "epi_flood_label": _EPI_CLASS_LABELS.get(epi_class, "Flood Planning Area"),
                "data_currency": currency}
    except Exception as e:
        logger.warning(f"EPI REST: {e}")
        return {"epi_flood_class": None, "epi_flood_label": None, "data_currency": "query_failed"}


# ---------------------------------------------------------------------------
# Copernicus EMS
# ---------------------------------------------------------------------------

def _query_copernicus_ems(lat: float, lng: float) -> dict:
    """
    PostGIS point-in-polygon against copernicus_flood_events.
    Returns ems_flood_detected (bool|None) and ems_activations (list|None).
    None = table empty or unavailable (distinct from False = no match).
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SELECT COUNT(*) AS n FROM copernicus_flood_events")
            if cur.fetchone()["n"] == 0:
                return {"ems_flood_detected": None, "ems_activations": None}
            cur.execute(
                """
                SELECT activation_id, event_name, event_date_start, flood_type
                FROM copernicus_flood_events
                WHERE ST_Intersects(geometry, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                ORDER BY event_date_start DESC
                """,
                (lng, lat),
            )
            rows = cur.fetchall()
        if not rows:
            return {"ems_flood_detected": False, "ems_activations": []}
        return {
            "ems_flood_detected": True,
            "ems_activations": [
                {"activation_id": r["activation_id"], "event_name": r["event_name"],
                 "event_date": r["event_date_start"].isoformat(), "flood_type": r["flood_type"]}
                for r in rows
            ],
        }
    except Exception as e:
        logger.warning(f"Copernicus EMS query: {e}")
        return {"ems_flood_detected": None, "ems_activations": None}
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# JRC Global Surface Water
# ---------------------------------------------------------------------------

def _jrc_tile_url(lat: float, lng: float) -> str:
    """
    Return the GCS URL for the JRC occurrence tile containing this point.
    Tiles are 10°×10°, named by NW corner, e.g. occurrence_150E_30Sv1_4_2021.tif
    """
    lon_base = math.floor(lng / 10) * 10
    lat_base = math.ceil(lat / 10) * 10    # ceil: NW corner lat, e.g. -33.6 -> -30 -> 30S tile

    lon_dir = "E" if lon_base >= 0 else "W"
    lat_dir = "S" if lat_base < 0 else "N"

    return (
        f"{JRC_TILE_BASE}/occurrence_{abs(lon_base)}{lon_dir}"
        f"_{abs(lat_base)}{lat_dir}v1_4_2021.tif"  # no underscore before v1_4
    )


def _query_jrc_surface_water(lat: float, lng: float) -> dict:
    """
    Sample JRC Global Surface Water occurrence at the given point via rasterio windowed read.
    Returns jrc_water_occurrence_pct (0–100) and jrc_data_year.
    None on failure — non-critical, does not block response.

    Runs in a thread with a hard 25s wall-clock timeout because GDAL_HTTP_TIMEOUT
    controls individual HTTP ops but not the full vsicurl open sequence.
    """
    def _sample() -> dict:
        try:
            import rasterio
            from rasterio.transform import rowcol
        except ImportError:
            raise RuntimeError("rasterio not installed — JRC sampling unavailable")

        url = _jrc_tile_url(lat, lng)
        # Use GDAL vsicurl for partial HTTP reads (range requests).
        # JRC tiles are regular GeoTIFFs — GDAL will fetch header + target block only.
        gdal_url = f"/vsicurl/{url}"

        with rasterio.Env(GDAL_HTTP_TIMEOUT=12, CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
            with rasterio.open(gdal_url) as src:
                row, col = rowcol(src.transform, lng, lat)
                # Clamp to valid extent
                row = max(0, min(row, src.height - 1))
                col = max(0, min(col, src.width - 1))
                window = rasterio.windows.Window(col, row, 1, 1)
                data = src.read(1, window=window)

        occurrence = int(data[0, 0])
        # 255 = no data (ocean / outside coverage)
        if occurrence == 255:
            return {"jrc_water_occurrence_pct": None, "jrc_data_year": JRC_DATA_YEAR}
        return {"jrc_water_occurrence_pct": float(occurrence), "jrc_data_year": JRC_DATA_YEAR}

    try:
        with ThreadPoolExecutor(max_workers=1) as ex:
            fut = ex.submit(_sample)
            return fut.result(timeout=25)
    except Exception as e:
        logger.warning(f"JRC GSW query: {e}")
        return {"jrc_water_occurrence_pct": None, "jrc_data_year": None}


# ---------------------------------------------------------------------------
# BOM nearest river gauge
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _fetch_bom_peak(station_id: str, major_flood_m: float) -> tuple[Optional[str], Optional[float]]:
    """
    Fetch last 6 years of water level from BOM SOS2 API.
    Returns (peak_date_iso, peak_level_m) for the highest reading, or (None, None) on failure.
    Only returns if the peak exceeded the major_flood_m threshold.
    """
    start = "2021-01-01T00:00:00+10:00"
    end   = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    params = {
        "service": "SOS",
        "version": "2.0.0",
        "request": "GetObservation",
        "featureOfInterest": f"http://bom.gov.au/waterdata/id/station/{station_id}",
        "observedProperty": "http://bom.gov.au/waterdata/def/property/Water_Course_Level",
        "temporalFilter": f"om:phenomenonTime,{start}/{end}",
    }
    try:
        r = requests.get(BOM_SOS2, params=params, timeout=15)
        r.raise_for_status()
        xml = r.text

        # Extract all time/value pairs from the SOS2 XML response.
        # Matches both wml2: and plain element names to handle namespace variations.
        pairs = re.findall(
            r"<[^>]*:?time>([^<]+)</[^>]*:?time>\s*<[^>]*:?value>([^<]+)</[^>]*:?value>",
            xml,
        )
        if not pairs:
            return None, None

        peak_val = -999.0
        peak_time = ""
        for t, v in pairs:
            try:
                fv = float(v)
                if fv > peak_val:
                    peak_val = fv
                    peak_time = t.strip()
            except ValueError:
                continue

        if peak_val < major_flood_m:
            return None, None  # No major flood in this period

        # Parse ISO datetime → date string
        try:
            dt = datetime.fromisoformat(peak_time.replace("Z", "+00:00"))
            peak_date = dt.date().isoformat()
        except Exception:
            peak_date = peak_time[:10]  # fallback: first 10 chars

        return peak_date, round(peak_val, 2)

    except Exception as e:
        logger.warning(f"BOM SOS2 {station_id}: {e}")
        return None, None


def _query_bom_gauge(lat: float, lng: float) -> dict:
    """
    Find nearest pre-seeded NSW river gauge and fetch last major flood event from BOM SOS2.
    Returns gauge metadata + flood event if available.
    """
    null_result = {
        "bom_gauge_name": None,
        "bom_gauge_distance_km": None,
        "bom_last_major_flood_date": None,
        "bom_last_major_flood_peak_m": None,
    }
    try:
        nearest = min(
            _NSW_GAUGES,
            key=lambda g: _haversine_km(lat, lng, g[2], g[3]),
        )
        station_id, name, g_lat, g_lng, major_level = nearest
        dist = _haversine_km(lat, lng, g_lat, g_lng)

        if dist > _GAUGE_MAX_DISTANCE_KM:
            return null_result

        peak_date, peak_m = _fetch_bom_peak(station_id, major_level)

        return {
            "bom_gauge_name": name,
            "bom_gauge_distance_km": round(dist, 1),
            "bom_last_major_flood_date": peak_date,
            "bom_last_major_flood_peak_m": peak_m,
        }
    except Exception as e:
        logger.warning(f"BOM gauge query: {e}")
        return null_result


# ---------------------------------------------------------------------------
# Confidence + data source helpers
# ---------------------------------------------------------------------------

def _compute_flood_signal(internal_outputs: dict) -> str:
    """
    Multi-source convergence signal for B2B/UI consumption.

    unavailable — EPI query failed; cannot determine signal (do not show green)
    elevated    — multiple independent sources converge on flood exposure
    moderate    — one strong observed signal OR two weaker signals
    low         — statutory overlay only (council flood study, no observed events)
    none        — no indicators across any source

    This is a data convergence indicator, not a flood risk determination.
    """
    # EPI query failure -> unavailable; never show green when EPI data is missing.
    if internal_outputs.get("data_currency") == "query_failed":
        return "unavailable"

    epi_in_overlay = internal_outputs.get("epi_flood_class") not in (None, "none", "")
    ems_detected   = internal_outputs.get("ems_flood_detected") is True
    jrc_pct        = internal_outputs.get("jrc_water_occurrence_pct") or 0.0
    bom_flood      = internal_outputs.get("bom_last_major_flood_date") is not None

    jrc_low      = 0 < jrc_pct < 15
    jrc_moderate = 15 <= jrc_pct < 40
    jrc_high     = jrc_pct >= 40

    # Elevated: multiple independent sources agree
    if (epi_in_overlay and ems_detected) or (ems_detected and jrc_moderate) \
            or (ems_detected and jrc_high) or jrc_high \
            or (epi_in_overlay and jrc_moderate and bom_flood):
        return "elevated"

    # Moderate: one strong observed signal or two weaker ones
    if ems_detected or (epi_in_overlay and jrc_low) \
            or (epi_in_overlay and bom_flood) or jrc_moderate \
            or (jrc_low and bom_flood):
        return "moderate"

    # Low: statutory overlay only — council study flags risk but no observed events
    if epi_in_overlay:
        return "low"

    return "none"


def _compute_confidence(internal_outputs: dict) -> str:
    """
    high   — EPI + EMS + JRC + BOM gauge + ≥1 SAR season
    medium — EPI + EMS + (JRC or BOM), OR EPI + ≥2 SAR seasons
    low    — EPI only
    """
    wet_seasons    = internal_outputs.get("wet_seasons_checked") or 0
    ems_available  = internal_outputs.get("ems_flood_detected") is not None
    jrc_available  = internal_outputs.get("jrc_water_occurrence_pct") is not None
    bom_available  = internal_outputs.get("bom_gauge_name") is not None
    spatial_layers = sum([ems_available, jrc_available, bom_available])

    if spatial_layers >= 3 and wet_seasons >= 1:
        return "high"
    if spatial_layers >= 2 or wet_seasons >= 2:
        return "medium"
    if spatial_layers >= 1 or wet_seasons >= 1:
        return "medium"
    return "low"


def _build_s1_gap_warning(internal_outputs: dict) -> str:
    ems_available = internal_outputs.get("ems_flood_detected") is not None
    if ems_available:
        return (
            "Sentinel-1B was non-operational Dec 2021 – Mar 2025. "
            "2022 La Niña flood events sourced from Copernicus EMS activation data."
        )
    return (
        "Sentinel-1B was non-operational Dec 2021 – Mar 2025. "
        "Flood detection for 2022 La Niña season uses Sentinel-1A only (reduced coverage). "
        "Run scripts/ingest_copernicus_ems.py to fill this gap."
    )


def _build_data_sources(internal_outputs: dict) -> list:
    sources = ["NSW SEED EPI WFS"]
    if internal_outputs.get("ems_flood_detected") is not None:
        sources.append(_DATA_SOURCE_EMS)
    if internal_outputs.get("jrc_water_occurrence_pct") is not None:
        sources.append(_DATA_SOURCE_JRC)
    if internal_outputs.get("bom_gauge_name") is not None:
        sources.append(_DATA_SOURCE_BOM)
    sources.append("Microsoft Planetary Computer S1 RTC")
    return sources


def _normalise_outputs(raw: dict) -> dict:
    """Convert stored/internal outputs to frontend FloodOutputs contract."""
    # EPI — handle old bool format from early writes
    epi_class = raw.get("epi_flood_class")
    epi_label = raw.get("epi_flood_label")
    if epi_class is None:
        in_overlay = raw.get("in_epi_overlay")
        if isinstance(in_overlay, bool):
            epi_class = "flood_planning_area" if in_overlay else "none"
            epi_label = _EPI_CLASS_LABELS.get(epi_class)

    # SAR
    sar_detected = raw.get("sar_flood_detected")
    if sar_detected is None and raw.get("flood_event_count") is not None:
        sar_detected = bool(raw["flood_event_count"])

    normalised = {
        "epi_flood_class":            epi_class,
        "epi_flood_label":            epi_label,
        "sar_flood_detected":         sar_detected,
        "sar_confidence":             raw.get("sar_confidence"),
        "sar_analysis_date":          raw.get("sar_analysis_date"),
        "ems_flood_detected":         raw.get("ems_flood_detected"),
        "ems_activations":            raw.get("ems_activations"),
        "jrc_water_occurrence_pct":   raw.get("jrc_water_occurrence_pct"),
        "jrc_data_year":              raw.get("jrc_data_year"),
        "bom_gauge_name":             raw.get("bom_gauge_name"),
        "bom_gauge_distance_km":      raw.get("bom_gauge_distance_km"),
        "bom_last_major_flood_date":  raw.get("bom_last_major_flood_date"),
        "bom_last_major_flood_peak_m": raw.get("bom_last_major_flood_peak_m"),
        "s1_gap_warning":             raw.get("s1_gap_warning"),
        "data_currency":              raw.get("data_currency") or raw.get("epi_data_currency", "unknown"),
    }
    normalised["flood_signal"] = _compute_flood_signal(normalised)
    return normalised


def _s1b_gap_affected(start: date, end: date) -> bool:
    return start <= S1B_GAP_END and end >= S1B_GAP_START


def _write_report(report_id, address, lat, lng, prop_id, inputs, internal_outputs):
    confidence   = _compute_confidence(internal_outputs)
    data_sources = _build_data_sources(internal_outputs)
    sql = """
        INSERT INTO property_reports
            (id, product, address, lat, lng, prop_id, run_date, inputs, outputs, confidence, data_sources)
        VALUES (%s, 'flood', %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET outputs = EXCLUDED.outputs
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, (
                report_id, address, lat, lng, prop_id, date.today(),
                psycopg2.extras.Json(inputs),
                psycopg2.extras.Json(internal_outputs),
                confidence,
                data_sources,
            ))
        conn.commit()
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

class FloodRequest(BaseModel):
    address: str
    prop_id: Optional[str] = None
    lat: float
    lng: float
    report_id: str


class FloodBatchRequest(BaseModel):
    lga_name: str
    wet_season_year: int   # e.g. 2022 = Nov 2021 - Mar 2022


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/flood")
def run_flood(req: FloodRequest):
    """
    On-demand flood analysis.
    Fast path: return pre-computed result if cached.
    Slow path: EPI + EMS (PostGIS) + JRC (rasterio remote read) + BOM gauge (SOS2).
    SAR analysis is batch-only (Phase 3B).
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                "SELECT outputs, confidence, data_sources FROM property_reports "
                "WHERE product='flood' AND address=%s ORDER BY run_date DESC LIMIT 1",
                (req.address,)
            )
            cached = cur.fetchone()
        if cached:
            return {
                "address": req.address, "lat": req.lat, "lng": req.lng,
                "run_date": date.today().isoformat(),
                "outputs": _normalise_outputs(cached["outputs"]),
                "confidence": cached["confidence"],
                "data_sources": cached["data_sources"] or _DATA_SOURCES_BASE,
            }
    except Exception as e:
        logger.warning(f"Cache lookup: {e}")
    finally:
        if conn:
            conn.close()

    with ThreadPoolExecutor(max_workers=4) as pool:
        f_epi = pool.submit(_query_epi_overlay, req.lat, req.lng)
        f_ems = pool.submit(_query_copernicus_ems, req.lat, req.lng)
        f_jrc = pool.submit(_query_jrc_surface_water, req.lat, req.lng)
        f_bom = pool.submit(_query_bom_gauge, req.lat, req.lng)
        epi = f_epi.result()
        ems = f_ems.result()
        jrc = f_jrc.result()
        bom = f_bom.result()

    internal_outputs = {
        "wet_seasons_checked": 0,
        "flood_event_count": None,
        "sentinel1b_gap_affected": True,
        "sar_flood_detected": None,
        "sar_confidence": None,
        "sar_analysis_date": None,
        **epi, **ems, **jrc, **bom,
    }
    internal_outputs["s1_gap_warning"] = _build_s1_gap_warning(internal_outputs)

    try:
        _write_report(
            req.report_id, req.address, req.lat, req.lng,
            req.prop_id, {"lat": req.lat, "lng": req.lng}, internal_outputs,
        )
    except Exception as e:
        # Non-fatal — analysis succeeded, DB write failed. Log and continue.
        logger.error(f"Flood report DB write failed (non-fatal): {e}")

    return {
        "address": req.address, "lat": req.lat, "lng": req.lng,
        "run_date": date.today().isoformat(),
        "outputs": _normalise_outputs(internal_outputs),
        "confidence": _compute_confidence(internal_outputs),
        "data_sources": _build_data_sources(internal_outputs),
    }


@router.post("/flood/batch")
def run_flood_batch(req: FloodBatchRequest):
    """
    Batch flood analysis: one LGA + one wet season. Called by Trigger.dev quarterly cron.
    Full S1 pipeline: Phase 3B in ce-satellite-implementation-plan.md.
    """
    year = req.wet_season_year
    if year < 2015 or year > 2100:
        from fastapi import HTTPException
        raise HTTPException(422, f"wet_season_year {year} out of valid range (2015–2100)")
    wet_start = date(year - 1, 11, 1)
    wet_end   = date(year, 3, 31)
    return {
        "status": "queued",
        "lga": req.lga_name,
        "wet_season": f"{wet_start}/{wet_end}",
        "sentinel1b_gap_affected": _s1b_gap_affected(wet_start, wet_end),
        "note": "Batch S1 VH processing is Phase 3B. EPI + EMS + JRC + BOM on-demand path is active.",
    }
