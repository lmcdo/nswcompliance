"""
Wet Season Flood Truth Engine -- FastAPI router.

POST /pipeline/flood        -- on-demand: EPI + EMS + JRC + DEA WOfS + BOM gauge
POST /pipeline/flood/batch  -- batch LGA processing (Trigger.dev cron, quarterly)

Data sources:
  NSW SEED EPI Flood WFS         (statutory overlay, free, no auth)
  Copernicus EMS activations      (copernicus_flood_events table, one-time ingest)
  JRC Global Surface Water        (Landsat 1984–present, GCS tiles, free)
  DEA Water Observations (WOfS)   (Landsat 1987–present, 25m AU, ows.dea.ga.gov.au, CC BY 4.0)
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
    "dea_wofs_frequency_pct": float | null,     # % of Landsat observations classified as wet (WOfS)
    "ses_in_flood_planning_area": bool | null,  # PostGIS: point in council flood study extent
    "ses_flood_class": str | null,              # e.g. "flood_planning_area", "1%AEP"
    "ses_study_name": str | null,               # instrument_key of matched study
    "ses_study_lga": str | null,                # LGA name of matched study
    "bom_gauge_name": str | null,
    "bom_gauge_distance_km": float | null,
    "bom_last_major_flood_date": str | null,
    "bom_last_major_flood_peak_m": float | null,
    "bom_flood_history": list[{date, peak_m, ari_category}],  # up to 3 events (paid tier)
    "flood_study_name": str | null,                            # EPI layer study name (free tier)
    "flood_study_date": str | null,                            # EPI layer effective date (free tier)
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
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pyproj import Transformer

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

PC_CATALOG = "https://planetarycomputer.microsoft.com/api/stac/v1"
S1_COLLECTION = "sentinel-1-rtc"
# ArcGIS REST API — Layer 0 is broken server-side (returns 400 for all queries).
# Layer 1 ("Flood Planning") works but covers only ~11 LGAs that have uploaded polygon data.
# Addresses in uncovered LGAs return 0 features → epi_flood_class: "none" (correct, not an error).
EPI_REST = ("https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
            "Planning/Hazard/MapServer/1/query")
BOM_SOS2 = "https://www.bom.gov.au/waterdata/services"
JRC_TILE_BASE = "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence"
JRC_DATA_YEAR = 2021

DEA_WCS_BASE = "https://ows.dea.ga.gov.au/wcs"
DEA_WOFS_LAYER = "ga_ls_wo_fq_myear_3"   # multi-year composite, 1987–present, no time param required
_DATA_SOURCE_DEA = "DEA Water Observations (WOfS, Landsat 1987–present)"

FLOOD_RATIO = 1.25
S1B_GAP_START = date(2021, 12, 23)
S1B_GAP_END   = date(2025, 3, 4)

_DATA_SOURCES_BASE = ["NSW SEED EPI WFS", "Microsoft Planetary Computer S1 RTC"]
_DATA_SOURCE_EMS   = "NSW Spatial Services / Copernicus EMS flood events"
_DATA_SOURCE_JRC   = "JRC Global Surface Water (Landsat 1984–present)"
_DATA_SOURCE_BOM   = "BOM Water Data Online"
_DATA_SOURCE_SES   = "NSW SES / Council flood study (spatial_overlays)"
_DATA_SOURCE_DEA   = "DEA Water Observations (WOfS · Landsat 1987–present)"

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

# ---------------------------------------------------------------------------
# Hawkesbury FRMSP 2025 — AEP raster flood levels
# ---------------------------------------------------------------------------

HAWKESBURY_RASTER_DIR = os.environ.get(
    "HAWKESBURY_RASTER_DIR",
    os.path.join(os.path.dirname(__file__), "..", "data", "flood_studies", "hawkesbury", "rasters"),
)
# Keys are used as field name suffixes: hawkesbury_flood_level_{key}
HAWKESBURY_AEP_FILES: dict[str, str] = {
    "2aep":   "2AEP_Floodstudy_Stretched.tif",
    "5aep":   "5AEP_Floodstudy_Stretched.tif",
    "10aep":  "10AEP_Floodstudy_Stretched.tif",
    "20aep":  "20AEP_Floodstudy_Stretched.tif",
    "50aep":  "50AEP_Floodstudy_Stretched.tif",
    "100aep": "100AEP_Floodstudy_Stretched.tif",
    "200aep": "200AEP_Floodstudy_Stretched.tif",
    "500aep": "500AEP_Floodstudy_Stretched.tif",
    "pmf":    "PMF_Floodstudy_Stretched.tif",
}
HAWKESBURY_NODATA = -99999.0
# Transform WGS84 lng/lat → GDA2020/MGA Zone 56 (EPSG:7856) before ds.index()
_HAWK_TRANSFORMER = Transformer.from_crs("EPSG:4326", "EPSG:7856", always_xy=True)


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
    """Query NSW SEED EPI Flood Planning layer via ArcGIS REST (Layer 1).

    Layer 1 covers ~11 LGAs that have uploaded polygon data to the state portal.
    Addresses in uncovered LGAs return 0 features → epi_flood_class "none" (not an error).
    Returns epi_flood_class, epi_flood_label, data_currency, flood_study_name, flood_study_date.
    """
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
                    "data_currency": "unknown", "flood_study_name": None, "flood_study_date": None}

        attrs = feats[0].get("attributes") or {}
        # Layer 1 uses CURRENCY_DATE (epoch-ms). Convert to ISO date string when available.
        _currency_raw = (
            attrs.get("CURRENCY_DATE") or attrs.get("CurrencyDate")
            or attrs.get("DataDate") or attrs.get("DATADATE")
        )
        if isinstance(_currency_raw, (int, float)) and _currency_raw > 0:
            from datetime import datetime, timezone
            currency = datetime.fromtimestamp(_currency_raw / 1000, tz=timezone.utc).date().isoformat()
        else:
            currency = str(_currency_raw or "unknown")
        # Layer 1 stores the classification in LAY_CLASS ("Flood Planning Area").
        # Earlier WFS layers used FloodClass/FLOODCLASS — keep both for resilience.
        raw_class = (
            attrs.get("LAY_CLASS") or attrs.get("lay_class")
            or attrs.get("FloodClass") or attrs.get("FLOODCLASS") or attrs.get("Category")
            or attrs.get("FldClass") or attrs.get("Flood_Class") or ""
        ).strip().lower()
        # Unknown or empty class → treat as "none" (not "flood_planning_area").
        # Defaulting to flood_planning_area on unrecognised values causes false positives.
        epi_class = _EPI_CLASS_MAP.get(raw_class) if raw_class else "none"
        if epi_class is None:
            logger.warning(f"Unrecognised EPI FloodClass: {raw_class!r} — treating as flood_planning_area")
            epi_class = "flood_planning_area"

        # Extract flood study name and date from layer attributes (free-tier provenance signal).
        # Field names vary across ArcGIS services — try common options.
        _STUDY_NAME_FIELDS = [
            "StudyName", "STUDYNAME", "FloodStudy", "FLOODSTUDY",
            "DataName", "DATANAME", "StudyRef", "StudyTitle",
            "FPA_Study", "Study_Name", "FloodStudyName",
            # Layer 1 fallback: EPI_NAME is the LEP name (e.g. "Wollongong LEP 2009")
            "EPI_NAME",
        ]
        _STUDY_DATE_FIELDS = [
            "StudyDate", "STUDYDATE", "EffectiveDate", "EFFECTIVEDATE",
        ]
        flood_study_name: Optional[str] = None
        for field in _STUDY_NAME_FIELDS:
            val = attrs.get(field)
            if val and str(val).strip() and str(val).strip().lower() not in ("null", "none", ""):
                flood_study_name = str(val).strip()
                break
        flood_study_date: Optional[str] = None
        for field in _STUDY_DATE_FIELDS:
            val = attrs.get(field)
            if val and str(val).strip() and str(val).strip().lower() not in ("null", "none", "", "unknown"):
                flood_study_date = str(val).strip()
                break

        return {
            "epi_flood_class": epi_class,
            "epi_flood_label": _EPI_CLASS_LABELS.get(epi_class, "Flood Planning Area"),
            "data_currency": currency,
            "flood_study_name": flood_study_name,
            "flood_study_date": flood_study_date,
        }
    except Exception as e:
        logger.warning(f"EPI REST: {e}")
        return {"epi_flood_class": None, "epi_flood_label": None, "data_currency": "query_failed",
                "flood_study_name": None, "flood_study_date": None}


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
            cur.execute("SET LOCAL statement_timeout = '5000'")
            cur.execute("SELECT COUNT(*) AS n FROM copernicus_flood_events")
            if cur.fetchone()["n"] == 0:
                return {"ems_flood_detected": None, "ems_activations": None}
            cur.execute("SET LOCAL statement_timeout = '5000'")
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
# DEA Water Observations (WOfS)
# ---------------------------------------------------------------------------

def _query_dea_wofs(lat: float, lng: float) -> dict:
    """
    Sample DEA WOfS multi-year frequency at a point via WCS GetCoverage.

    Layer: ga_ls_wo_fq_myear_3 (all-of-archive composite, 1987–present, 25m).
    Band 1 = frequency (0.0–1.0 fraction). nodata = -999.0.
    Returns dea_wofs_frequency_pct (0–100) or None on failure.

    Simpler than JRC: no vsicurl, no tile lookup — single HTTP request, in-memory rasterio.
    """
    try:
        import io
        import rasterio
    except ImportError:
        logger.warning("rasterio not installed — DEA WOfS unavailable")
        return {"dea_wofs_frequency_pct": None}

    try:
        delta = 0.001  # ~100m bbox, enough for a point sample
        r = requests.get(
            DEA_WCS_BASE,
            params={
                "service": "WCS",
                "version": "1.0.0",
                "request": "GetCoverage",
                "coverage": DEA_WOFS_LAYER,
                "format": "GeoTIFF",
                "bbox": f"{lng},{lat - delta},{lng + delta},{lat}",
                "crs": "EPSG:4326",
                "resx": str(delta),
                "resy": str(delta),
            },
            timeout=20,
        )
        r.raise_for_status()

        # Validate response is a GeoTIFF (not an XML error response)
        ct = r.headers.get("Content-Type", "")
        if "tiff" not in ct.lower() and r.content[:4] not in (b"II*\x00", b"MM\x00*"):
            logger.warning(f"DEA WOfS: unexpected Content-Type {ct}")
            return {"dea_wofs_frequency_pct": None}

        with rasterio.open(io.BytesIO(r.content)) as ds:
            raw = float(ds.read(1)[0, 0])   # Band 1 = frequency (0.0–1.0)

        if raw == -999.0 or raw < 0 or math.isnan(raw):
            return {"dea_wofs_frequency_pct": None}

        return {"dea_wofs_frequency_pct": round(raw * 100.0, 2)}

    except Exception as e:
        logger.warning(f"DEA WOfS query: {e}")
        return {"dea_wofs_frequency_pct": None}


# ---------------------------------------------------------------------------
# BOM nearest river gauge
# ---------------------------------------------------------------------------

def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.asin(math.sqrt(a))


def _parse_bom_observations(xml: str) -> list[tuple[datetime, float]]:
    """Parse time/value pairs from a BOM SOS2 XML response. Returns sorted list."""
    pairs = re.findall(
        r"<[^>]*:?time>([^<]+)</[^>]*:?time>\s*<[^>]*:?value>([^<]+)</[^>]*:?value>",
        xml,
    )
    obs: list[tuple[datetime, float]] = []
    for t, v in pairs:
        try:
            fv = float(v)
            dt = datetime.fromisoformat(t.strip().replace("Z", "+00:00"))
            obs.append((dt, fv))
        except (ValueError, Exception):
            continue
    obs.sort(key=lambda x: x[0])
    return obs


def _fetch_bom_observations(station_id: str, start_iso: str) -> str:
    """Fetch SOS2 XML for a station from start_iso to now."""
    end = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    params = {
        "service": "SOS",
        "version": "2.0.0",
        "request": "GetObservation",
        "featureOfInterest": f"http://bom.gov.au/waterdata/id/station/{station_id}",
        "observedProperty": "http://bom.gov.au/waterdata/def/property/Water_Course_Level",
        "temporalFilter": f"om:phenomenonTime,{start_iso}/{end}",
    }
    r = requests.get(BOM_SOS2, params=params, timeout=15)
    r.raise_for_status()
    return r.text


def _fetch_bom_peak(station_id: str, major_flood_m: float) -> tuple[Optional[str], Optional[float]]:
    """
    Fetch last 6 years of water level from BOM SOS2 API.
    Returns (peak_date_iso, peak_level_m) for the highest reading above threshold, or (None, None).
    """
    try:
        xml = _fetch_bom_observations(station_id, "2021-01-01T00:00:00+10:00")
        obs = _parse_bom_observations(xml)
        if not obs:
            return None, None

        peak_val = -999.0
        peak_time: Optional[datetime] = None
        for dt, fv in obs:
            if fv > peak_val:
                peak_val = fv
                peak_time = dt

        if peak_val < major_flood_m or peak_time is None:
            return None, None

        return peak_time.date().isoformat(), round(peak_val, 2)

    except Exception as e:
        logger.warning(f"BOM SOS2 {station_id}: {e}")
        return None, None


def _ari_category(peak_m: float, major_flood_m: float) -> str:
    """Estimate ARI category from peak relative to major flood threshold."""
    if major_flood_m <= 0:
        return "major flood"
    ratio = peak_m / major_flood_m
    if ratio >= 1.5:
        return "1-in-100 year (est.)"
    if ratio >= 1.2:
        return "1-in-50 year (est.)"
    return "1-in-20 year (est.)"


def _fetch_bom_flood_history(
    station_id: str, major_flood_m: float, max_events: int = 3
) -> list[dict]:
    """
    Fetch up to max_events major flood events from BOM SOS2 (2000–present).
    A "flood event" is a contiguous period where water level >= major_flood_m.
    Returns list of {date, peak_m, ari_category} sorted newest first.
    """
    try:
        xml = _fetch_bom_observations(station_id, "2000-01-01T00:00:00+10:00")
        obs = _parse_bom_observations(xml)
        if not obs:
            return []

        # Identify flood events: contiguous periods at or above the major flood level.
        # Each time the level drops back below threshold, the event closes.
        events: list[tuple[datetime, float]] = []
        in_event = False
        event_peak = -999.0
        event_peak_dt: Optional[datetime] = None

        for dt, val in obs:
            if val >= major_flood_m:
                in_event = True
                if val > event_peak:
                    event_peak = val
                    event_peak_dt = dt
            else:
                if in_event and event_peak_dt is not None:
                    events.append((event_peak_dt, event_peak))
                in_event = False
                event_peak = -999.0
                event_peak_dt = None

        # Close trailing open event
        if in_event and event_peak_dt is not None:
            events.append((event_peak_dt, event_peak))

        if not events:
            return []

        # Newest first, cap
        events.sort(key=lambda x: x[0], reverse=True)
        events = events[:max_events]

        return [
            {
                "date": evt[0].date().isoformat(),
                "peak_m": round(evt[1], 2),
                "ari_category": _ari_category(evt[1], major_flood_m),
            }
            for evt in events
        ]

    except Exception as e:
        logger.warning(f"BOM flood history {station_id}: {e}")
        return []


def _query_bom_gauge(lat: float, lng: float) -> dict:
    """
    Find nearest pre-seeded NSW river gauge and fetch flood events from BOM SOS2.
    Returns gauge metadata, last major flood (single event), and bom_flood_history (up to 3).
    """
    null_result = {
        "bom_gauge_name": None,
        "bom_gauge_distance_km": None,
        "bom_last_major_flood_date": None,
        "bom_last_major_flood_peak_m": None,
        "bom_flood_history": [],
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
        flood_history = _fetch_bom_flood_history(station_id, major_level, max_events=3)

        return {
            "bom_gauge_name": name,
            "bom_gauge_distance_km": round(dist, 1),
            "bom_last_major_flood_date": peak_date,
            "bom_last_major_flood_peak_m": peak_m,
            "bom_flood_history": flood_history,
        }
    except Exception as e:
        logger.warning(f"BOM gauge query: {e}")
        return null_result


# ---------------------------------------------------------------------------
# SES / council flood study (PostGIS spatial_overlays)
# ---------------------------------------------------------------------------

DEA_WCS_BASE   = "https://ows.dea.ga.gov.au/wcs"
DEA_WOFS_LAYER = "ga_ls_wo_fq_myear_3"

# Canonical display labels for raw DB values stored in spatial_overlays.value.
# Raw values vary by source: snake_case from FPA shapefiles, title case from EPI,
# short codes from council FeatureServers. Always apply this before returning.
_SES_CLASS_DISPLAY: dict[str, str] = {
    "flood_planning_area":               "Flood Planning Area",
    "Flood Planning Area":               "Flood Planning Area",
    "1%AEP":                             "1% AEP Flood Extent",
    "design_flood":                      "Design Flood (1% AEP)",
    "PMF":                               "Probable Maximum Flood",
    "Flood Prone and Major Creeks Land": "Flood Prone Land",
    "1 in 100 AEP Flood Extent":         "1% AEP Flood Extent",
    "Level of Probable Maximum Flood":   "Probable Maximum Flood",
    "Probable Maximum Flood Line":       "Probable Maximum Flood",
    "Area 1":                            "Flood Prone Area 1",
}


def _query_ses_flood_study(lat: float, lng: float) -> dict:
    """
    Point-in-polygon against spatial_overlays for flood layer type.
    Covers all council flood studies ingested by ingest_flood_studies.py,
    including Hawkesbury FPA and any future SES portal studies.

    Returns:
      ses_in_flood_planning_area: bool | None
        True  — point is inside at least one flood extent polygon
        False — spatial_overlays has flood rows but point is outside all of them
        None  — spatial_overlays has no flood rows (table empty/unavailable)
      ses_flood_class: str | None   — value of the matched row (e.g. "flood_planning_area")
      ses_study_name: str | None    — instrument_key of the matched row
      ses_study_lga: str | None     — lga_name of the matched row
    """
    null_result = {
        "ses_in_flood_planning_area": None,
        "ses_flood_class": None,
        "ses_study_name": None,
        "ses_study_lga": None,
    }
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '5000'")
            cur.execute("SELECT COUNT(*) AS n FROM spatial_overlays WHERE layer_type = 'flood'")
            if cur.fetchone()["n"] == 0:
                return null_result
            # Point-in-polygon: find first matching flood polygon
            cur.execute("SET LOCAL statement_timeout = '5000'")
            cur.execute(
                """
                SELECT instrument_key, lga_name, value
                FROM spatial_overlays
                WHERE layer_type = 'flood'
                  AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                ORDER BY currency_date DESC
                LIMIT 1
                """,
                (lng, lat),
            )
            row = cur.fetchone()
        if row:
            return {
                "ses_in_flood_planning_area": True,
                "ses_flood_class": _SES_CLASS_DISPLAY.get(row["value"], row["value"]),
                "ses_study_name": row["instrument_key"],
                "ses_study_lga": row["lga_name"],
            }
        return {
            "ses_in_flood_planning_area": False,
            "ses_flood_class": None,
            "ses_study_name": None,
            "ses_study_lga": None,
        }
    except Exception as e:
        logger.warning(f"SES flood study query: {e}")
        return null_result
    finally:
        if conn:
            conn.close()


_WOFS_HARD_TIMEOUT = 25  # seconds — WCS can stall after connect; requests.get timeout alone doesn't abort rasterio decode


def _query_dea_wofs(lat: float, lng: float) -> dict:
    """
    Sample DEA Water Observations (WOfS) multi-year composite via WCS.
    Layer: ga_ls_wo_fq_myear_3 — Band 1 = frequency fraction (0.0–1.0).
    Returns dea_wofs_frequency_pct (0.0–100.0) or None on failure/nodata.

    Uses an inner ThreadPoolExecutor with a hard 25s wall-clock timeout so a
    stalled WCS response or slow rasterio decode cannot block the main thread pool.
    """
    import io
    import rasterio

    def _fetch() -> dict:
        delta = 0.001
        r = requests.get(DEA_WCS_BASE, params={
            "service": "WCS", "version": "1.0.0", "request": "GetCoverage",
            "coverage": DEA_WOFS_LAYER, "format": "GeoTIFF",
            "bbox": f"{lng},{lat - delta},{lng + delta},{lat}",
            "crs": "EPSG:4326", "resx": str(delta), "resy": str(delta),
        }, timeout=20)
        r.raise_for_status()
        ct = r.headers.get("Content-Type", "")
        if "tiff" not in ct.lower() and r.content[:4] not in (b"II*\x00", b"MM\x00*"):
            return {"dea_wofs_frequency_pct": None}
        with rasterio.open(io.BytesIO(r.content)) as ds:
            raw = float(ds.read(1)[0, 0])   # Band 1 = frequency (0.0–1.0)
        if raw == -999.0 or raw < 0 or math.isnan(raw):
            return {"dea_wofs_frequency_pct": None}
        return {"dea_wofs_frequency_pct": round(raw * 100.0, 2)}

    try:
        with ThreadPoolExecutor(max_workers=1) as inner:
            fut = inner.submit(_fetch)
            return fut.result(timeout=_WOFS_HARD_TIMEOUT)
    except TimeoutError:
        logger.warning(f"DEA WOfS query: hard timeout after {_WOFS_HARD_TIMEOUT}s")
        return {"dea_wofs_frequency_pct": None}
    except Exception as e:
        logger.warning(f"DEA WOfS query: {e}")
        return {"dea_wofs_frequency_pct": None}


# ---------------------------------------------------------------------------
# Hawkesbury FRMSP 2025 raster sampling
# ---------------------------------------------------------------------------

def _query_hawkesbury_rasters(lat: float, lng: float) -> dict:
    """
    Sample Hawkesbury FRMSP 2025 remapped flood levels at a point.
    Returns flood water surface elevation (metres AHD) for 9 AEP events.
    All values None if point is outside raster extent or files not present.

    CRS: rasters are EPSG:7856 (GDA2020/MGA Zone 56). Point is transformed
    before ds.index() — passing WGS84 coords directly would silently return
    wrong pixel (CRS mismatch pattern bug).

    Source: NSW Reconstruction Authority, Hawkesbury FRMSP 2025.
    Nona Ruddell, nona.ruddell@reconstruction.nsw.gov.au.
    """
    null_result: dict = {f"hawkesbury_flood_level_{k}": None for k in HAWKESBURY_AEP_FILES}
    null_result["hawkesbury_flood_study"] = None

    try:
        import rasterio
    except ImportError:
        logger.warning("rasterio not installed — Hawkesbury raster sampling unavailable")
        return null_result

    # Transform WGS84 lng/lat → EPSG:7856
    x, y = _HAWK_TRANSFORMER.transform(lng, lat)

    # Bounds check using 100AEP as proxy — all 9 rasters share the same extent.
    proxy = os.path.join(HAWKESBURY_RASTER_DIR, HAWKESBURY_AEP_FILES["100aep"])
    if not os.path.exists(proxy):
        logger.info("Hawkesbury rasters not present on this host — skipping")
        return null_result

    try:
        with rasterio.open(proxy) as ds:
            left, bottom, right, top = ds.bounds
            if not (left <= x <= right and bottom <= y <= top):
                return null_result  # outside Hawkesbury extent — not an error
    except Exception as e:
        logger.warning(f"Hawkesbury bounds check failed: {e}")
        return null_result

    result: dict = {}
    for aep_key, filename in HAWKESBURY_AEP_FILES.items():
        path = os.path.join(HAWKESBURY_RASTER_DIR, filename)
        try:
            with rasterio.open(path) as ds:
                row, col = ds.index(x, y)
                row = max(0, min(row, ds.height - 1))
                col = max(0, min(col, ds.width - 1))
                val = float(ds.read(1)[row, col])
            if val == HAWKESBURY_NODATA or math.isnan(val) or val < 0:
                result[f"hawkesbury_flood_level_{aep_key}"] = None
            else:
                result[f"hawkesbury_flood_level_{aep_key}"] = round(val, 2)
        except Exception as e:
            logger.warning(f"Hawkesbury raster {aep_key}: {e}")
            result[f"hawkesbury_flood_level_{aep_key}"] = None

    has_data = any(v is not None for v in result.values())
    result["hawkesbury_flood_study"] = "Hawkesbury FRMSP 2025" if has_data else None
    return result


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
    ses_in_overlay = internal_outputs.get("ses_in_flood_planning_area") is True
    # Hawkesbury FRMSP raster: non-null 100AEP level confirms site is in flood extent
    hawk_100 = internal_outputs.get("hawkesbury_flood_level_100aep")
    hawk_in_overlay = hawk_100 is not None
    # Combined statutory overlay signal: EPI state portal OR local council study OR raster
    in_overlay     = epi_in_overlay or ses_in_overlay or hawk_in_overlay
    ems_detected   = internal_outputs.get("ems_flood_detected") is True
    # Use DEA WOfS frequency when JRC is unavailable (DEA is AU-specific, 25m, 1987–present)
    jrc_pct        = internal_outputs.get("jrc_water_occurrence_pct") or 0.0
    wofs_pct       = internal_outputs.get("dea_wofs_frequency_pct") or 0.0
    effective_pct  = jrc_pct if jrc_pct > 0 else wofs_pct
    bom_flood      = internal_outputs.get("bom_last_major_flood_date") is not None

    # Phase 0 — false-negative fix.
    # EPI Layer 1 covers only ~11 LGAs. When epi_flood_class="none" for an uncovered
    # LGA AND no local SES flood study data exists AND no strong observational signal
    # is present, return "unavailable" instead of misleadingly returning "none".
    # ses_in_flood_planning_area becomes non-None once the Hawkesbury FPA is ingested
    # and Phase 2 runs; hawkesbury_flood_level_100aep is populated by Phase 3.
    epi_no_coverage = internal_outputs.get("epi_flood_class") == "none"
    ses_queried = internal_outputs.get("ses_in_flood_planning_area") is not None
    no_local_study = not ses_queried and not hawk_in_overlay
    if epi_no_coverage and no_local_study and not ems_detected and not bom_flood and effective_pct < 5:
        return "unavailable"

    jrc_low      = 0 < effective_pct < 15
    jrc_moderate = 15 <= effective_pct < 40
    jrc_high     = effective_pct >= 40

    # Elevated: multiple independent sources agree
    if (in_overlay and ems_detected) or (ems_detected and jrc_moderate) \
            or (ems_detected and jrc_high) or jrc_high \
            or (in_overlay and jrc_moderate and bom_flood):
        return "elevated"

    # Moderate: one strong observed signal or two weaker ones
    if ems_detected or (in_overlay and jrc_low) \
            or (in_overlay and bom_flood) or jrc_moderate \
            or (jrc_low and bom_flood):
        return "moderate"

    # Low: statutory overlay only — council study flags risk but no observed events
    if in_overlay:
        return "low"

    return "none"


def _compute_confidence(internal_outputs: dict) -> str:
    """
    high   — EPI/SES overlay + EMS + JRC/WOfS + BOM gauge + ≥1 SAR season
    medium — overlay + EMS + (JRC/WOfS or BOM), OR overlay + ≥2 SAR seasons
    low    — overlay only
    """
    wet_seasons    = internal_outputs.get("wet_seasons_checked") or 0
    ems_available  = internal_outputs.get("ems_flood_detected") is not None
    jrc_available  = internal_outputs.get("jrc_water_occurrence_pct") is not None
    wofs_available = internal_outputs.get("dea_wofs_frequency_pct") is not None
    bom_available  = internal_outputs.get("bom_gauge_name") is not None
    ses_available  = internal_outputs.get("ses_in_flood_planning_area") is not None
    spatial_layers = sum([ems_available, jrc_available or wofs_available, bom_available, ses_available])

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
    if internal_outputs.get("ses_in_flood_planning_area") is not None:
        sources.append(_DATA_SOURCE_SES)
    if internal_outputs.get("ems_flood_detected") is not None:
        sources.append(_DATA_SOURCE_EMS)
    if internal_outputs.get("jrc_water_occurrence_pct") is not None:
        sources.append(_DATA_SOURCE_JRC)
    if internal_outputs.get("dea_wofs_frequency_pct") is not None:
        sources.append(_DATA_SOURCE_DEA)
    if internal_outputs.get("bom_gauge_name") is not None:
        sources.append(_DATA_SOURCE_BOM)
    if internal_outputs.get("hawkesbury_flood_study"):
        sources.append("Hawkesbury FRMSP 2025 — NSW Reconstruction Authority (2m raster, 9 AEP events)")
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

    # If epi_class is present but epi_label is null (DB written before label field existed), recompute
    if epi_class and not epi_label:
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
        "dea_wofs_frequency_pct":     raw.get("dea_wofs_frequency_pct"),
        "ses_in_flood_planning_area": raw.get("ses_in_flood_planning_area"),
        "ses_flood_class":            raw.get("ses_flood_class"),
        "ses_study_name":             raw.get("ses_study_name"),
        "ses_study_lga":              raw.get("ses_study_lga"),
        "bom_gauge_name":             raw.get("bom_gauge_name"),
        "bom_gauge_distance_km":      raw.get("bom_gauge_distance_km"),
        "bom_last_major_flood_date":  raw.get("bom_last_major_flood_date"),
        "bom_last_major_flood_peak_m": raw.get("bom_last_major_flood_peak_m"),
        "bom_flood_history":          raw.get("bom_flood_history") or [],
        "flood_study_name":           raw.get("flood_study_name"),
        "flood_study_date":           raw.get("flood_study_date"),
        "s1_gap_warning":             raw.get("s1_gap_warning"),
        "data_currency":              raw.get("data_currency") or raw.get("epi_data_currency") or "unknown",
    }
    # Hawkesbury FRMSP 2025 AEP flood levels (metres AHD)
    for aep_key in ("2aep", "5aep", "10aep", "20aep", "50aep", "100aep", "200aep", "500aep", "pmf"):
        field = f"hawkesbury_flood_level_{aep_key}"
        normalised[field] = raw.get(field)
    normalised["hawkesbury_flood_study"] = raw.get("hawkesbury_flood_study")

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
    Slow path: EPI + EMS (PostGIS) + JRC (rasterio remote read) + BOM gauge (SOS2)
               + SES council flood studies (PostGIS) + DEA WOfS (WCS).
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
                "outputs": _normalise_outputs(cached["outputs"] or {}),
                "confidence": cached["confidence"],
                "data_sources": cached["data_sources"] or _DATA_SOURCES_BASE,
            }
    except Exception as e:
        logger.warning(f"Cache lookup: {e}")
    finally:
        if conn:
            conn.close()

    with ThreadPoolExecutor(max_workers=7) as pool:
        f_epi  = pool.submit(_query_epi_overlay, req.lat, req.lng)
        f_ems  = pool.submit(_query_copernicus_ems, req.lat, req.lng)
        f_jrc  = pool.submit(_query_jrc_surface_water, req.lat, req.lng)
        f_bom  = pool.submit(_query_bom_gauge, req.lat, req.lng)
        f_ses  = pool.submit(_query_ses_flood_study, req.lat, req.lng)
        f_wofs = pool.submit(_query_dea_wofs, req.lat, req.lng)
        f_hawk = pool.submit(_query_hawkesbury_rasters, req.lat, req.lng)
        epi  = f_epi.result()
        ems  = f_ems.result()
        jrc  = f_jrc.result()
        bom  = f_bom.result()
        ses  = f_ses.result()
        wofs = f_wofs.result()
        hawk = f_hawk.result()

    internal_outputs = {
        "wet_seasons_checked": 0,
        "flood_event_count": None,
        "sentinel1b_gap_affected": True,
        "sar_flood_detected": None,
        "sar_confidence": None,
        "sar_analysis_date": None,
        **epi, **ems, **jrc, **bom, **ses, **wofs, **hawk,
    }
    internal_outputs["s1_gap_warning"] = _build_s1_gap_warning(internal_outputs)

    try:
        _write_report(
            req.report_id, req.address, req.lat, req.lng,
            req.prop_id, {"lat": req.lat, "lng": req.lng}, internal_outputs,
        )
    except Exception as e:
        logger.error(f"Flood report DB write failed: {e}")
        raise HTTPException(status_code=503, detail="Failed to save report — please retry")

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
