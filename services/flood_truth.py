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
    "flood_signal": "none" | "low" | "moderate" | "elevated" | "unavailable",
    "ground_elevation_m_ahd": float | null,       # NSW 5m DEM (SIX Maps ImageServer)
    "in_100yr_flood_zone": bool | null,            # True/False/None — None = NOT ASSESSED,
                                                   # a source that could have said yes was
                                                   # unreachable. Never render None as "no".
    "in_100yr_flood_zone_unconsulted": list[str],  # which sources were unreachable
    "flood_studies": list[{study_key, study_name, source, design: {aep: {depth_m, level_m_ahd}}, historical: {year: {depth_m, level_m_ahd}}}]
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
from typing import Literal, Optional, Union

import psycopg2
import psycopg2.extras
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from pyproj import Transformer

from audit_trail import DataSourceQuery, log_audit_trail, get_current_disclaimer_version

# prior-art-checked: shared item-4 modules created this session — extending
# this pipeline's own envelope, not adding a parallel data source.
try:
    from services.execution_manifest import MANIFEST_KEY, build_manifest
    from services.geometry_checks import check_point_nsw
except ImportError:
    from execution_manifest import MANIFEST_KEY, build_manifest
    from geometry_checks import check_point_nsw

# icontract: runtime postcondition assertions for liability-critical functions.
# Declared in services/requirements.txt (what the container installs) and in
# requirements-test.txt since 2026-08-06. Before that it was declared only in
# scripts/requirements-maintenance.txt, so THIS FALLBACK is what ran in
# production, CI and local checkouts alike, and every contract below was a
# no-op from the day it was written.
# The fallback stays for genuinely minimal environments, but it is no longer
# the normal case — and tests/test_flood_truth.py now FAILS rather than skips
# when icontract is importable and a decorator has gone missing.
try:
    import icontract
except ImportError:
    # Provide no-op decorators so the module loads without icontract
    class _FakeIcontract:
        @staticmethod
        def ensure(condition, description="", **kwargs):
            def _decorator(fn):
                return fn
            return _decorator
        @staticmethod
        def require(condition, description="", **kwargs):
            def _decorator(fn):
                return fn
            return _decorator
    icontract = _FakeIcontract()  # type: ignore[assignment]

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

# Canonical signal enum — used by icontract postconditions AND Hypothesis invariants.
_VALID_FLOOD_SIGNALS = {"none", "low", "moderate", "elevated", "unavailable"}

# Sentinel-1 SAR is NOT implemented here. The Planetary Computer STAC catalogue
# address, the `sentinel-1-rtc` collection id and the VH change-detection
# threshold (FLOOD_RATIO = 1.25) used to sit in this file with ZERO call sites —
# no pystac_client/planetary_computer import, no query, no consumer. They were
# deleted 2026-08-06 (calibration Lane 1, decision D2) because a named
# threshold and endpoint that nothing executes reads as a shipped detector.
# The honest state is recorded where it is actually served: the on-demand path
# nulls every sar_* field and the execution manifest records
# sentinel1_sar.queried = False. When Phase 3B is built, take the constants from
# that build's own design — not from a stub that was never run.
# ArcGIS REST API — Layer 0 is broken server-side (returns 400 for all queries).
# Layer 1 ("Flood Planning") works but covers only ~11 LGAs that have uploaded polygon data.
# Addresses in uncovered LGAs return 0 features → epi_flood_class: "none" (correct, not an error).
EPI_REST = ("https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
            "Planning/Hazard/MapServer/1/query")
BOM_SOS2 = "https://www.bom.gov.au/waterdata/services"
JRC_TILE_BASE = "https://storage.googleapis.com/global-surface-water/downloads2021/occurrence"
JRC_DATA_YEAR = 2021

# Algorithm revision for execution manifests (campaign item 4): the
# multi-source screening method + signal fusion. Bump on method change, not
# per deploy (deploy identity = execution_manifest.deploy_sha).
ALGORITHM_VERSION = "flood-multisource-screen-1.0"

DEA_WCS_BASE = "https://ows.dea.ga.gov.au/wcs"
DEA_WOFS_LAYER = "ga_ls_wo_fq_myear_3"   # multi-year composite, 1987–present, no time param required
_DATA_SOURCE_DEA = "DEA Water Observations (WOfS, Landsat 1987–present)"

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
# NSW 5m DEM — ground elevation via SIX Maps ImageServer (full NSW coverage)
# ---------------------------------------------------------------------------

_DEM_IDENTIFY_URL = (
    "https://maps.six.nsw.gov.au/arcgis/rest/services/"
    "public/NSW_5M_Elevation/ImageServer/identify"
)
_DEM_TIMEOUT = 15  # seconds
_DATA_SOURCE_DEM = "NSW Spatial Services 5m DEM (SIX Maps ImageServer)"

# ---------------------------------------------------------------------------
# Generalised flood study raster config
# ---------------------------------------------------------------------------
# Each study has: name, directory, CRS (often missing from TIF metadata),
# nodata value, AEP design event files (depth + water level), and optionally
# historical calibration event files.
# File templates use {type} placeholder: "d" = depth, "h" = water level.

_FLOOD_STUDIES_BASE = os.path.join(os.path.dirname(__file__), "..", "data", "flood_studies")

# WHY ONLY FOUR, when data/flood_studies/ holds ELEVEN directories.
#
# Asked and answered 2026-08-24 by inventorying every directory, because "a
# study on disk that nothing reads" is the same waste that put 1.6 GB per cold
# start into a directory nothing read. None of the other seven is a wireable
# study: this table wants per-AEP raster grids, and they do not have any.
#
#   greendale, narellan, south_creek, south_creek_hc  -- EMPTY. 0 files, 0 bytes.
#   campbelltown   -- 57 files, 0 rasters, 52 MB: ESRI shapefiles of flood
#                     EXTENT polygons (.shp/.dbf/.prj/.MAP). An extent answers
#                     "in or out", not the depth/level question this samples.
#   cooks_river    -- 5 files, 0 rasters, 743 KB: one study-database shapefile.
#   georges_river  -- 2 files, 0 rasters, 653 MB: two UNEXTRACTED .zip payloads.
#
# So there is nothing to wire without first extracting, converting and
# validating grids that may not exist inside those packages at all. Wiring any
# of them as-is would DECLARE a capability that cannot be delivered, which is
# exactly what flood_study_raster_availability() below exists to catch, and it
# would report the study absent on every host forever.
#
# The shapefile sets are a different product shape (extent polygons) and belong
# in spatial_overlays with the rest of the flood extents, not here.
FLOOD_STUDIES: dict[str, dict] = {
    "hawkesbury": {
        "name": "Hawkesbury FRMSP 2025",
        # Which council area this study covers. Used ONLY to decide whether
        # its ABSENCE is relevant to a given address — never to answer the
        # flood question itself.
        "lga": "Hawkesbury",
        "source": "NSW Reconstruction Authority",
        "dir": os.environ.get(
            "HAWKESBURY_RASTER_DIR",
            os.path.join(_FLOOD_STUDIES_BASE, "hawkesbury", "rasters"),
        ),
        "crs": "EPSG:7856",
        "nodata": -99999.0,
        # Hawkesbury rasters are water level only (h), no pre-computed depth (d)
        "has_depth": False,
        # Hawkesbury files use ARI naming: 2AEP=2yr ARI=50%AEP, 100AEP=100yr ARI=1%AEP
        "design": {
            "50pct":  "2AEP_Floodstudy_Stretched.tif",   # 2yr ARI = 50% AEP
            "20pct":  "5AEP_Floodstudy_Stretched.tif",   # 5yr ARI = 20% AEP
            "10pct":  "10AEP_Floodstudy_Stretched.tif",  # 10yr ARI = 10% AEP
            "5pct":   "20AEP_Floodstudy_Stretched.tif",  # 20yr ARI = 5% AEP
            "2pct":   "50AEP_Floodstudy_Stretched.tif",  # 50yr ARI = 2% AEP
            "1pct":   "100AEP_Floodstudy_Stretched.tif", # 100yr ARI = 1% AEP
            "0_5pct": "200AEP_Floodstudy_Stretched.tif", # 200yr ARI = 0.5% AEP
            "0_2pct": "500AEP_Floodstudy_Stretched.tif", # 500yr ARI = 0.2% AEP
            "pmf":    "PMF_Floodstudy_Stretched.tif",
        },
        "historical": {},
    },
    "tweed": {
        "name": "Tweed Valley Flood Study Update 2024",
        # Which council area this study covers. Used ONLY to decide whether
        # its ABSENCE is relevant to a given address — never to answer the
        # flood question itself.
        "lga": "Tweed",
        "source": "Tweed Shire Council / BMT",
        "dir": os.environ.get(
            "TWEED_RASTER_DIR",
            os.path.join(_FLOOD_STUDIES_BASE, "tweed"),
        ),
        "crs": "EPSG:28356",  # GDA94 MGA56 — missing from TIF metadata
        "nodata": -999.0,
        "has_depth": True,
        "design": {
            "20pct":  "design/Tweed_001_20p_{type}_Max.tif",
            "5pct":   "design/Tweed_001_5p_{type}_Max.tif",
            "1pct":   "design/Tweed_001_1p_{type}_Max.tif",
            "0_2pct": "design/Tweed_001_1in500_{type}_Max.tif",
            "pmf":    "design/Tweed_001_PMP_{type}_Max.tif",
        },
        "historical": {
            "1989": "calibration/Tweed_001_1989_{type}_Max.tif",
            "2017": "calibration/Tweed_001_2017_{type}_Max.tif",
            "2020": "calibration/Tweed_001_2020_{type}_Max.tif",
            "2022": "calibration/Tweed_001_2022_{type}_Max.tif",
        },
    },
    "wollongong": {
        "name": "Wollongong City Flood Study 2024",
        # Which council area this study covers. Used ONLY to decide whether
        # its ABSENCE is relevant to a given address — never to answer the
        # flood question itself.
        "lga": "Wollongong",
        "source": "Wollongong City Council / Jacobs",
        "dir": os.environ.get(
            "WOLLONGONG_RASTER_DIR",
            os.path.join(_FLOOD_STUDIES_BASE, "wollongong"),
        ),
        "crs": "EPSG:7856",  # GDA2020 MGA56 — missing from ASC metadata
        "nodata": -999.0,
        "has_depth": True,
        # Envelope files (critical-duration max across all storm durations)
        "design": {
            "20pct":  "design/Wollongong_20pct_{type}_Max.asc",
            "10pct":  "design/Wollongong_10pct_{type}_Max.asc",
            "5pct":   "design/Wollongong_5pct_{type}_Max.asc",
            "2pct":   "design/Wollongong_2pct_{type}_Max.asc",
            "1pct":   "design/Wollongong_1pct_{type}_Max.asc",
            # PMF, not pmf. R2 holds design/Wollongong_PMF_{d,h}_Max.asc and
            # download_tweed_wollongong_rasters.py writes that name verbatim
            # (verified against the live bucket 2026-08-24: 12 of 12 objects
            # present, uppercase). This read lowercase, which opens fine on the
            # Windows filesystem this repo is developed on and does not exist on
            # the Linux container -- so Wollongong's PMF grid could never be
            # sampled in production. Neither guard covered it:
            # flood_study_raster_availability() checks the 1% AEP file
            # specifically, and the import-time warning is built from that same
            # 1%-only signal, so the study reported PRESENT throughout.
            # Now pinned by tests/test_flood_study_filenames.py, which compares
            # these templates against the downloader's key list in both
            # directions.
            "pmf":    "design/Wollongong_PMF_{type}_Max.asc",
        },
        "historical": {},
    },
    "redbank": {
        "name": "Redbank Creek Flood Study 2025",
        # Which council area this study covers. Used ONLY to decide whether
        # its ABSENCE is relevant to a given address — never to answer the
        # flood question itself.
        "lga": "Redbank",
        "source": "Hawkesbury City Council",
        "dir": os.environ.get(
            "REDBANK_RASTER_DIR",
            os.path.join(_FLOOD_STUDIES_BASE, "redbank"),
        ),
        "crs": "EPSG:7856",  # GDA2020 MGA56 — from shapefile .prj in the source package
        "nodata": -999.0,
        "has_depth": True,
        # 1 m grids, losslessly recompressed from the portal's raw BIL payloads to
        # tiled DEFLATE GeoTIFF (3.6 GB → 224 MB; pixel-identical verified) with
        # CRS + nodata embedded. Source zip retained in data/redbank_flood/.
        # Peak enveloped + filtered (source READ ME: depth>0.10m OR d>0.05 & V*d>0.025 OR V>2m/s).
        # Each event carries 3–685 TUFLOW glitch cells (depth up to 1140 m, levels to -642 m AHD);
        # valid ranges below reject those at sample time. Catchment terrain tops out ~187 m AHD.
        "valid_depth_range": (0.0, 100.0),
        "valid_level_range": (-10.0, 250.0),
        "design": {
            "20pct":   "design/RedbankCk_DES_20pcAEP_{type}_Max_ProcessedOutput.tif",
            "10pct":   "design/RedbankCk_DES_10pcAEP_{type}_Max_ProcessedOutput.tif",
            "5pct":    "design/RedbankCk_DES_5pcAEP_{type}_Max_ProcessedOutput.tif",
            "2pct":    "design/RedbankCk_DES_2pcAEP_{type}_Max_ProcessedOutput.tif",
            "1pct":    "design/RedbankCk_DES_1pcAEP_{type}_Max_ProcessedOutput.tif",
            "0_5pct":  "design/RedbankCk_DES_1in200AEP_{type}_Max_ProcessedOutput.tif",
            "0_2pct":  "design/RedbankCk_DES_1in500AEP_{type}_Max_ProcessedOutput.tif",
            "0_1pct":  "design/RedbankCk_DES_1in1000AEP_{type}_Max_ProcessedOutput.tif",
            "0_05pct": "design/RedbankCk_DES_1in2000AEP_{type}_Max_ProcessedOutput.tif",
            "0_02pct": "design/RedbankCk_DES_1in5000AEP_{type}_Max_ProcessedOutput.tif",
            "pmf":     "design/RedbankCk_DES_PMF_{type}_Max_ProcessedOutput.tif",
        },
        "historical": {
            "2022": "historical/RedBank_DES_Hist_March2022_{type}_Max_ProcessedOutput.tif",
        },
    },
}

def flood_study_raster_availability() -> dict[str, bool]:
    """study_key -> whether this host actually holds that study's rasters.

    A study in FLOOD_STUDIES is a DECLARATION that this service can answer the
    flood question for that area. Tweed and Wollongong were declared and their
    files can never be present in the container: data/flood_studies is
    untracked, Dockerfile.python does not copy data/, and unlike Hawkesbury and
    Redbank there is no download script for them. The runtime noticed and wrote
    a log line nobody reads.

    Same class as #880 — a capability declared where it cannot be delivered,
    degrading silently. Reported loudly at import (see below) and consulted per
    run so the served verdict says "not assessed" rather than "no".
    """
    status: dict[str, bool] = {}
    for study_key, cfg in FLOOD_STUDIES.items():
        study_dir = cfg["dir"]  # noqa: bracket-access — internal FLOOD_STUDIES config
        design = cfg["design"]  # noqa: bracket-access — internal FLOOD_STUDIES config
        has_depth = cfg["has_depth"]  # noqa: bracket-access — internal FLOOD_STUDIES config
        # The 1% AEP grid SPECIFICALLY, not "any design grid". A study holding
        # its 5% file but not its 1% file cannot answer the question this field
        # asks, and counting it as present would let a half-delivered study
        # produce a confident negative — the same defect one level down.
        template = design.get("1pct")
        if template is None:
            status[study_key] = False
            continue
        if "{type}" in template:
            candidate = os.path.join(
                study_dir, template.format(type="d" if has_depth else "h")
            )
        else:
            candidate = os.path.join(study_dir, template)
        status[study_key] = os.path.exists(candidate)
    return status


def _warn_on_absent_flood_studies() -> list[str]:
    """Announce configured-but-undeliverable studies at import. Never silent."""
    absent = [k for k, present in flood_study_raster_availability().items() if not present]
    if absent:
        logger.warning(
            "FLOOD STUDY CONFIG/DATA MISMATCH: %s configured but their rasters are "
            "not on this host: %s. Every 1%% AEP answer for those areas is 'not "
            "assessed', never 'no'. Ship the rasters (R2 + a download script, the "
            "Hawkesbury/Redbank pattern) or remove them from FLOOD_STUDIES.",
            len(absent), ", ".join(sorted(absent)),
        )
    return absent


_ABSENT_FLOOD_STUDIES_AT_IMPORT = _warn_on_absent_flood_studies()

# Pre-build CRS transformers (WGS84 → study CRS) — one per unique CRS
_STUDY_TRANSFORMERS: dict[str, Transformer] = {}
for _study in FLOOD_STUDIES.values():
    _crs = _study["crs"]
    if _crs not in _STUDY_TRANSFORMERS:
        _STUDY_TRANSFORMERS[_crs] = Transformer.from_crs("EPSG:4326", _crs, always_xy=True)

# Canonical AEP display labels
_AEP_LABELS: dict[str, str] = {
    "20pct": "20% AEP (1-in-5 yr)",
    "10pct": "10% AEP (1-in-10 yr)",
    "5pct":  "5% AEP (1-in-20 yr)",
    "2pct":  "2% AEP (1-in-50 yr)",
    "1pct":  "1% AEP (1-in-100 yr)",
    "0_5pct": "0.5% AEP (1-in-200 yr)",
    "0_2pct": "0.2% AEP (1-in-500 yr)",
    "0_1pct": "0.1% AEP (1-in-1000 yr)",
    "0_05pct": "0.05% AEP (1-in-2000 yr)",
    "0_02pct": "0.02% AEP (1-in-5000 yr)",
    "50pct": "50% AEP (1-in-2 yr)",
    "pmf":   "PMF (Probable Maximum Flood)",
}


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
        # prior-art-checked: timeout bump only on the existing EPI flood query, no new source
        r = requests.get(EPI_REST, params=params, timeout=30)
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

        with rasterio.Env(GDAL_HTTP_TIMEOUT=30, CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif"):
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
            return fut.result(timeout=60)
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


def _parse_bom_observations(xml: str) -> list[tuple[datetime, float]]:
    """Parse time/value pairs from a BOM SOS2 XML response. Returns sorted list."""
    pairs = re.findall(
        r"<[^>]*:?time>([^<]+)</[^>]*:?time>\s*<[^>]*:?value>([^<]+)</[^>]*:?value>",
        xml,
    )
    obs: list[tuple[datetime, float]] = []
    for t, v in pairs:
        try:
            if v is None:
                continue
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
# short codes from council FeatureServers, and AEP% from filename-parsed studies.
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
    # Campbelltown AEP tiers (parsed from filename by ingest script)
    "0.2%AEP":  "0.2% AEP (1-in-500 yr)",
    "0.5%AEP":  "0.5% AEP (1-in-200 yr)",
    "1.0%AEP":  "1% AEP (1-in-100 yr)",
    "2.0%AEP":  "2% AEP (1-in-50 yr)",
    "5.0%AEP":  "5% AEP (1-in-20 yr)",
    "20.0%AEP": "20% AEP (1-in-5 yr)",
}

# Lower rank = more frequent flood = more informative for day-to-day risk.
# Used to pick the primary ses_flood_class when multiple AEP tiers match.
_AEP_FREQUENCY_RANK: dict[str, int] = {
    "20% AEP (1-in-5 yr)":       1,
    "5% AEP (1-in-20 yr)":       2,
    "2% AEP (1-in-50 yr)":       3,
    "1% AEP (1-in-100 yr)":      4,
    "Design Flood (1% AEP)":     4,
    "1% AEP Flood Extent":       4,
    "0.5% AEP (1-in-200 yr)":    5,
    "0.2% AEP (1-in-500 yr)":    6,
    "Flood Planning Area":        7,
    "Flood Prone Land":           7,
    "Flood Prone Area 1":         7,
    "Probable Maximum Flood":     8,
}


def _query_address_council(lat: float, lng: float) -> str | None:
    """The council this address sits in, for scoping an absent flood study.

    NOT ses_study_lga, which #892 used and which measurement showed is the
    wrong signal: it is the LGA of a MATCHED flood study, so it is null in 80%
    of stored reports and null in 100% of the rows that were queried and fell
    outside every study extent — exactly the case where a missing study
    matters. Scoping on it made the check close to inert.

    This resolves the council itself, from the same spatial_overlays table the
    rest of the module already queries. Returns None when the lookup cannot
    answer, and None means unknown, never "no council".
    """
    conn = None
    try:
        # Imported here, not at module scope: services/ import each other by bare
        # name (the container's working dir) and the test suite resolves those
        # with explicit sys.modules stubs. A local import keeps this module
        # importable without stubbing the very function being wired in.
        from lga_lookup import lookup_lga

        conn = _get_conn()
        result = lookup_lga(lat, lng, conn)
        return result.get("lga_name")
    except Exception as e:  # noqa: BLE001 — a failed lookup is unknown, not fatal
        logger.warning(f"Council lookup for flood study scoping failed: {e}")
        return None
    finally:
        if conn:
            conn.close()


def _query_ses_flood_study(lat: float, lng: float) -> dict:
    """
    Point-in-polygon against spatial_overlays for flood layer type.
    Returns all matching AEP tiers for the point (not just the first).

    Returns:
      ses_in_flood_planning_area: bool | None
        True  — point is inside at least one flood extent polygon
        False — spatial_overlays has flood rows but point is outside all of them
        None  — spatial_overlays has no flood rows (table empty/unavailable)
      ses_flood_class: str | None   — most frequent (highest AEP%) tier matched
      ses_aep_tiers: list[str]      — all matched tier display labels
      ses_study_name: str | None    — instrument_key of the primary matched row
      ses_study_lga: str | None     — lga_name of the primary matched row
    """
    null_result = {
        "ses_in_flood_planning_area": None,
        "ses_flood_class": None,
        "ses_aep_tiers": [],
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
            # Fetch ALL matching flood polygons — no LIMIT so multi-AEP studies return all tiers.
            cur.execute("SET LOCAL statement_timeout = '5000'")
            cur.execute(
                """
                SELECT DISTINCT ON (value) instrument_key, lga_name, value
                FROM spatial_overlays
                WHERE layer_type = 'flood'
                  AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                ORDER BY value, currency_date DESC
                """,
                (lng, lat),
            )
            rows = cur.fetchall()
        if not rows:
            return {
                "ses_in_flood_planning_area": False,
                "ses_flood_class": None,
                "ses_aep_tiers": [],
                "ses_study_name": None,
                "ses_study_lga": None,
            }
        # Map all raw values to display labels
        tiers = [_SES_CLASS_DISPLAY.get(r["value"], r["value"]) for r in rows]
        # Primary class = most frequent tier (lowest _AEP_FREQUENCY_RANK value)
        primary_tier = min(tiers, key=lambda t: _AEP_FREQUENCY_RANK.get(t, 99))
        # Use the row matching the primary tier for study provenance
        primary_row = next(
            r for r in rows
            if _SES_CLASS_DISPLAY.get(r["value"], r["value"]) == primary_tier
        )
        return {
            "ses_in_flood_planning_area": True,
            "ses_flood_class": primary_tier,
            "ses_aep_tiers": sorted(tiers, key=lambda t: _AEP_FREQUENCY_RANK.get(t, 99)),
            "ses_study_name": primary_row["instrument_key"],
            "ses_study_lga": primary_row["lga_name"],
        }
    except Exception as e:
        logger.warning(f"SES flood study query: {e}")
        return null_result
    finally:
        if conn:
            conn.close()


_COMPOUND_LAYER_TYPES = ("heritage", "riparian", "wetlands", "landslide")


def _query_compound_risk_layers(lat: float, lng: float) -> dict:
    """
    Query spatial_overlays for layers that compound flood risk:
    - heritage: mitigation options constrained by heritage controls
    - riparian: flood pathway + setback complexity
    - wetlands: flood storage areas — misidentifying as buildable underestimates risk
    - landslide: flood + slope = debris flow risk
    """
    result = {f"compound_{lt}": None for lt in _COMPOUND_LAYER_TYPES}
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET LOCAL statement_timeout = '5000'")
            cur.execute(
                """
                SELECT DISTINCT layer_type, value, instrument_key
                FROM spatial_overlays
                WHERE layer_type = ANY(%s)
                  AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                """,
                (list(_COMPOUND_LAYER_TYPES), lng, lat),
            )
            for row in cur.fetchall():
                lt = row["layer_type"]
                result[f"compound_{lt}"] = row["value"] or True
    except Exception as e:
        logger.warning(f"Compound risk layer query: {e}")
    finally:
        if conn:
            conn.close()
    return result


_WOFS_HARD_TIMEOUT = 60  # seconds — WCS can stall after connect; requests.get timeout alone doesn't abort rasterio decode


def _wofs_frequency_from_bands(
    descriptions: list, values: list
) -> Optional[float]:
    """Select the WOfS frequency (0.0-1.0) from a GetCoverage response by
    band NAME, never by position.

    Audit finding 2026-07-15 (issue #745 D1, live-reproduced at 9 NSW points):
    the DEA WCS returns the three measurement bands (count_wet, count_clear,
    frequency) in an UNSTABLE order that varies by location — at Concord and
    at a bone-dry Dubbo paddock, positional band 3 was count_clear (~635),
    which the old >1.0 clamp converted into a fake 100% flood frequency and a
    false user-facing flood constraint.

    Fail-closed rules: no band named "frequency" → None (no positional
    fallback); value outside [0, 1], nodata, or NaN → None. A frequency can
    never legitimately exceed 1.0 — clamping masks band-identity bugs.
    """
    band_idx = next(
        (i for i, d in enumerate(descriptions)
         if isinstance(d, str) and d.strip().lower() == "frequency"),
        None,
    )
    if band_idx is None or band_idx >= len(values):
        logger.warning(
            "DEA WOfS: no band named 'frequency' in response "
            "(descriptions=%s) — failing closed", descriptions)
        return None
    raw = values[band_idx]
    if raw == -999.0 or math.isnan(raw) or raw < 0.0 or raw > 1.0:
        logger.warning(
            "DEA WOfS: frequency band value %r outside [0,1] — failing closed",
            raw)
        return None
    return raw


def _query_dea_wofs(lat: float, lng: float) -> dict:
    """
    Sample DEA Water Observations (WOfS) multi-year composite via WCS.
    Layer: ga_ls_wo_fq_myear_3 — Band 3 = frequency fraction (0.0–1.0).
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
        }, timeout=30)
        r.raise_for_status()
        ct = r.headers.get("Content-Type") or ""
        if "tiff" not in ct.lower() and r.content[:4] not in (b"II*\x00", b"MM\x00*"):
            return {"dea_wofs_frequency_pct": None}
        with rasterio.open(io.BytesIO(r.content)) as ds:
            descriptions = list(ds.descriptions or [])
            values = [float(ds.read(i + 1)[0, 0]) for i in range(ds.count)]
        raw = _wofs_frequency_from_bands(descriptions, values)
        if raw is None:
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

def _sample_raster(
    path: str,
    x: float,
    y: float,
    nodata: float,
    valid_range: Optional[tuple[float, float]] = None,
) -> Optional[float]:
    """Read a single pixel value from a raster at projected coordinates.

    Windowed 1x1 read — never loads the full band (Redbank grids are 150 MB each).
    valid_range rejects hydraulic-model glitch cells (e.g. depth 1140 m) as nodata.
    Returns None if file missing, point outside bounds, nodata, implausible, or error.
    """
    import rasterio
    import rasterio.windows
    if not os.path.exists(path):
        return None
    try:
        with rasterio.open(path) as ds:
            left, bottom, right, top = ds.bounds
            if not (left <= x <= right and bottom <= y <= top):
                return None
            row, col = ds.index(x, y)
            row = max(0, min(row, ds.height - 1))
            col = max(0, min(col, ds.width - 1))
            window = rasterio.windows.Window(col, row, 1, 1)
            val = float(ds.read(1, window=window)[0, 0])
        if val == nodata or math.isnan(val):
            return None
        if valid_range is not None and not (valid_range[0] <= val <= valid_range[1]):
            logger.warning(
                f"Raster sample {os.path.basename(path)}: value {val} outside "
                f"plausible range {valid_range} — model artifact, treating as nodata"
            )
            return None
        return val
    except Exception as e:
        logger.warning(f"Raster sample {os.path.basename(path)}: {e}")
        return None


def _query_flood_study_rasters(lat: float, lng: float) -> dict:
    """Sample all configured flood study rasters at a point.

    Iterates FLOOD_STUDIES config. For each study whose raster directory exists
    and whose extent contains the point, returns depth/level per AEP event plus
    historical event depths where available.

    Returns flat dict merged into internal_outputs:
      flood_studies: list of matched study dicts
      hawkesbury_flood_level_*: backward-compat aliases for Hawkesbury
    """
    try:
        import rasterio  # noqa: F401
    except ImportError:
        logger.warning("rasterio not installed — flood study raster sampling unavailable")
        # Every configured study is unconsultable, not "no study covers this
        # point". Without this the missing library reads as a clean negative.
        return {
            "flood_studies": [],
            "flood_studies_absent": sorted(FLOOD_STUDIES.keys()),
        }

    matched_studies: list[dict] = []
    # Studies this host CANNOT consult because their rasters are not on disk.
    # Distinct from "the point falls outside the study extent", which is a real
    # answer. Collapsing the two is what let a configured-but-absent study
    # produce a confident "not in a flood zone".
    absent_studies: list[str] = []

    for study_key, cfg in FLOOD_STUDIES.items():
        study_dir = cfg["dir"]
        nodata = cfg["nodata"]
        has_depth = cfg["has_depth"]
        transformer = _STUDY_TRANSFORMERS[cfg["crs"]]
        x, y = transformer.transform(lng, lat)

        # Bounds-check proxy: prefer the PMF grid — the maximal flood envelope.
        # Event grids can differ in extent (Redbank's PMF grid extends ~86 m past
        # its 1% grid); proxying on a smaller grid silently drops fringe points.
        # Fall back to 1pct if the PMF file is absent on this host.
        proxy_candidates = [k for k in ("pmf", "1pct") if k in cfg["design"]]  # noqa: bracket-access — internal FLOOD_STUDIES config
        if not proxy_candidates:
            proxy_candidates = [next(iter(cfg["design"]))]  # noqa: bracket-access — internal FLOOD_STUDIES config
        proxy_path = None
        for proxy_aep in proxy_candidates:
            proxy_template = cfg["design"][proxy_aep]  # noqa: bracket-access — internal FLOOD_STUDIES config
            # Resolve file path — Hawkesbury uses plain filenames, Tweed uses {type} templates
            if "{type}" in proxy_template:
                candidate = os.path.join(study_dir, proxy_template.format(type="d" if has_depth else "h"))
            else:
                candidate = os.path.join(study_dir, proxy_template)
            if os.path.exists(candidate):
                proxy_path = candidate
                break

        # The 1% grid SPECIFICALLY decides whether this study can answer the
        # question the verdict asks. The proxy above is a BOUNDS proxy and
        # prefers the PMF grid, so a study holding its PMF but not its 1% file
        # would pass the proxy check, sample None for 1pct, and be read as
        # "outside the extent" — a confident negative from a file that does not
        # exist. Closes the gap Sol found between this loop and
        # flood_study_raster_availability(), which was already 1%-specific.
        if not flood_study_raster_availability().get(study_key, False):
            logger.warning(
                f"Flood study {study_key}: its 1% AEP grid is not readable on "
                f"this host — the 1% question cannot be answered from it"
            )
            absent_studies.append(study_key)
            continue

        if proxy_path is None:
            # NOT a silent skip. The study is configured, so this host is
            # supposed to be able to answer for it; it cannot. Recorded so the
            # verdict downstream can say "not assessed" instead of "no".
            # Recorded unscoped here on purpose: this is a FACT about the host
            # ("these studies cannot be read"), not yet a judgement about this
            # address. Whether the absence matters is decided in
            # _unconsulted_1pct_sources, where the council IS known.
            logger.warning(
                f"Flood study {study_key} is configured but its rasters are not "
                f"on this host ({study_dir}) — the 1% AEP question cannot be "
                f"answered from this study"
            )
            absent_studies.append(study_key)
            continue

        # Quick bounds check
        try:
            with rasterio.open(proxy_path) as ds:
                left, bottom, right, top = ds.bounds
                if not (left <= x <= right and bottom <= y <= top):
                    continue
        except Exception as e:
            logger.warning(f"Flood study {study_key} bounds check: {e}")
            continue

        depth_range = cfg.get("valid_depth_range")
        level_range = cfg.get("valid_level_range")

        # Sample design events
        design_results: dict[str, dict] = {}
        for aep_key, template in cfg["design"].items():
            entry: dict = {"depth_m": None, "level_m_ahd": None}
            if "{type}" in template:
                if has_depth:
                    d_path = os.path.join(study_dir, template.format(type="d"))
                    entry["depth_m"] = _sample_raster(d_path, x, y, nodata, depth_range)
                    if entry["depth_m"] is not None:
                        entry["depth_m"] = round(max(0.0, entry["depth_m"]), 2)
                h_path = os.path.join(study_dir, template.format(type="h"))
                entry["level_m_ahd"] = _sample_raster(h_path, x, y, nodata, level_range)
                if entry["level_m_ahd"] is not None:
                    entry["level_m_ahd"] = round(entry["level_m_ahd"], 2)
            else:
                # Hawkesbury-style: single file is water level (h)
                val = _sample_raster(os.path.join(study_dir, template), x, y, nodata, level_range)
                if val is not None:
                    entry["level_m_ahd"] = round(val, 2)

            if entry["depth_m"] is not None or entry["level_m_ahd"] is not None:
                design_results[aep_key] = entry

        # Sample historical events
        historical_results: dict[str, dict] = {}
        for event_year, template in cfg.get("historical", {}).items():
            entry = {"depth_m": None, "level_m_ahd": None}
            if "{type}" in template:
                if has_depth:
                    d_path = os.path.join(study_dir, template.format(type="d"))
                    entry["depth_m"] = _sample_raster(d_path, x, y, nodata, depth_range)
                    if entry["depth_m"] is not None:
                        entry["depth_m"] = round(max(0.0, entry["depth_m"]), 2)
                h_path = os.path.join(study_dir, template.format(type="h"))
                entry["level_m_ahd"] = _sample_raster(h_path, x, y, nodata, level_range)
                if entry["level_m_ahd"] is not None:
                    entry["level_m_ahd"] = round(entry["level_m_ahd"], 2)
            if entry["depth_m"] is not None or entry["level_m_ahd"] is not None:
                historical_results[event_year] = entry

        if design_results or historical_results:
            matched_studies.append({
                "study_key": study_key,
                "study_name": cfg["name"],
                "source": cfg["source"],
                "design": design_results,
                "historical": historical_results,
            })

    # Build result dict
    result: dict = {
        "flood_studies": matched_studies,
        "flood_studies_absent": absent_studies,
    }

    # Backward-compat: flat hawkesbury_flood_level_* fields
    hawk = next((s for s in matched_studies if s["study_key"] == "hawkesbury"), None)
    # Map new canonical AEP keys → old flat field suffixes.
    # Old naming used ARI (years): 2aep=2yr ARI=50%AEP, 100aep=100yr ARI=1%AEP.
    _HAWK_AEP_MAP = {
        "50pct": "2aep", "20pct": "5aep", "10pct": "10aep", "5pct": "20aep",
        "2pct": "50aep", "1pct": "100aep", "0_5pct": "200aep", "0_2pct": "500aep", "pmf": "pmf",
    }
    for new_key, old_suffix in _HAWK_AEP_MAP.items():
        val = None
        if hawk:
            entry = hawk["design"].get(new_key)
            if entry:
                val = entry.get("level_m_ahd")
        result[f"hawkesbury_flood_level_{old_suffix}"] = val
    result["hawkesbury_flood_study"] = hawk["study_name"] if hawk else None

    return result


def _query_ground_elevation(lat: float, lng: float) -> dict:
    """Query NSW 5m DEM via SIX Maps ImageServer identify endpoint.

    Returns ground_elevation_m_ahd (float) or None if unavailable.
    No auth required. Full NSW coverage at 5m resolution.
    """
    body = None
    try:
        geometry = f'{{"x":{lng},"y":{lat},"spatialReference":{{"wkid":4326}}}}'
        r = requests.get(
            _DEM_IDENTIFY_URL,
            params={
                "geometry": geometry,
                "geometryType": "esriGeometryPoint",
                "returnGeometry": "false",
                "returnCatalogItems": "false",
                "f": "json",
            },
            timeout=_DEM_TIMEOUT,
        )
        r.raise_for_status()
        body = r.json()
        raw_value = body.get("value")
        if raw_value is None or raw_value == "NoData":
            return {"ground_elevation_m_ahd": None}
        elevation = float(raw_value)
        return {"ground_elevation_m_ahd": round(elevation, 2)}
    except (ValueError, TypeError):
        _raw = body.get("value") if body is not None else "N/A"
        logger.warning(f"DEM identify: non-numeric value {_raw!r}")
        return {"ground_elevation_m_ahd": None}
    except Exception as e:
        logger.warning(f"DEM identify: {e}")
        return {"ground_elevation_m_ahd": None}

@icontract.ensure(
    lambda result: result in _VALID_FLOOD_SIGNALS,
    description="Flood signal must be one of none/low/moderate/elevated/unavailable — "
                "the frontend and PDF both render a badge straight from this value, so an "
                "unrecognised string shows as blank rather than as an error.",
)
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
    # Any flood study raster with a 1pct design result confirms site is in flood extent
    flood_studies = internal_outputs.get("flood_studies") or []
    study_in_overlay = any(
        (s.get("design") or {}).get("1pct") is not None for s in flood_studies
    )
    # Backward-compat check for Hawkesbury flat field (from cached reports)
    hawk_100 = internal_outputs.get("hawkesbury_flood_level_100aep")
    if hawk_100 is not None:
        study_in_overlay = True
    # Combined statutory overlay signal: EPI state portal OR local council study OR raster
    in_overlay     = epi_in_overlay or ses_in_overlay or study_in_overlay
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
    no_local_study = not ses_queried and not study_in_overlay
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


@icontract.ensure(
    lambda result: result in {"low", "medium", "high"},
    description="Confidence must be low/medium/high — invalid value breaks frontend badge rendering.",
)
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


_COMPOUND_RISK_DESCRIPTIONS = {
    "heritage": (
        "Property is within a heritage conservation area or is individually heritage-listed. "
        "Flood mitigation options (raising, barriers, demolition) may be constrained by heritage controls."
    ),
    "riparian": (
        "Property is on or adjacent to mapped riparian land. "
        "Riparian corridors are natural flood pathways with additional setback requirements."
    ),
    "wetlands": (
        "Property is within or adjacent to a mapped wetland area. "
        "Wetlands function as natural flood storage — development may increase flood risk to neighbouring properties."
    ),
    "landslide": (
        "Property is within a mapped landslide-prone area. "
        "Flood saturation on slopes creates compound debris-flow risk beyond standard flood modelling."
    ),
}


def _build_compound_risk_notes(compound_risks: list) -> list:
    """Return factual notes for each active compound risk layer."""
    return [_COMPOUND_RISK_DESCRIPTIONS[lt] for lt in compound_risks if lt in _COMPOUND_RISK_DESCRIPTIONS]


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
    for study in (internal_outputs.get("flood_studies") or []):
        name = study.get("study_name") or "Unknown"
        source = study.get("source") or ""
        sources.append(f"{name} — {source} (flood study raster)")
    if internal_outputs.get("ground_elevation_m_ahd") is not None:
        sources.append(_DATA_SOURCE_DEM)
    for lt in _COMPOUND_LAYER_TYPES:
        if internal_outputs.get(f"compound_{lt}") is not None:
            sources.append(f"NSW ePlanning spatial_overlays ({lt})")
    # Only claim the S1 source when a SAR result actually exists. The
    # unconditional append served "Microsoft Planetary Computer S1 RTC" on
    # every report while no S1 query has ever run (sar_flood_detected is
    # hard-nulled; batch is a Phase-3B stub) — a named source that was never
    # queried (DQ-44, campaign item 4 census).
    if internal_outputs.get("sar_flood_detected") is not None:
        sources.append("Microsoft Planetary Computer S1 RTC")
    return sources


# ---------------------------------------------------------------------------
# Data gap disclosure + minimum viable screening
# ---------------------------------------------------------------------------

_MIN_SOURCES_FOR_SCREENING = 3  # of 9 — refuse if fewer respond

_SOURCE_AVAILABILITY_CHECKS: list[tuple[str, object]] = [
    ("epi",      lambda d: d.get("epi_flood_class") not in (None, "none")),
    ("ems",      lambda d: d.get("ems_flood_detected") is not None),
    ("jrc",      lambda d: d.get("jrc_water_occurrence_pct") is not None),
    ("wofs",     lambda d: d.get("dea_wofs_frequency_pct") is not None),
    ("bom",      lambda d: d.get("bom_gauge_name") is not None),
    ("ses",      lambda d: d.get("ses_in_flood_planning_area") is not None),
    ("studies",  lambda d: bool(d.get("flood_studies"))),
    ("dem",      lambda d: d.get("ground_elevation_m_ahd") is not None),
    ("compound", lambda d: any(
        v is not None
        for k, v in d.items()
        if k.startswith("compound_") and k not in ("compound_risk_layers", "compound_risk_notes")
    )),
]


@icontract.ensure(
    lambda result: 0 <= result <= 9,
    description="Source count must be 0-9 — out-of-range would corrupt refuse-to-serve threshold check.",
)
def _count_available_sources(internal_outputs: dict) -> int:
    """Count how many of the 9 data source groups returned usable data."""
    return sum(1 for _, check in _SOURCE_AVAILABILITY_CHECKS if check(internal_outputs))


def _unconsulted_1pct_sources(normalised: dict, raw: dict) -> list[str]:
    """Sources that could have answered the 1% AEP question and were not asked.

    Only sources that can produce a POSITIVE 1% finding count. The DEM, the
    satellite water history and the BOM gauges cannot place a point inside a
    1% AEP extent, so their absence does not make the answer unknown — it just
    makes the report thinner.

    Returned as customer-neutral source names because they are rendered.
    """
    unconsulted: list[str] = []

    # EPI. `data_currency == "query_failed"` is the module's existing marker for
    # a service that did not respond (see _build_data_gap_reasons). A genuine
    # "none" is an answer; a failure is not.
    if raw.get("data_currency") == "query_failed" or normalised.get("epi_flood_class") is None:
        unconsulted.append("NSW EPI flood overlay")

    # SES / council flood study extent in spatial_overlays. The module already
    # documents None as "table empty or unavailable (distinct from False = no
    # match)" — so None here is precisely "not asked".
    if normalised.get("ses_in_flood_planning_area") is None:
        unconsulted.append("Council/SES flood study extent")

    # Flood study rasters configured for this deployment but absent from it.
    # This is the Tweed and Wollongong case: declared available in code, the
    # files can never be in the container, and the run used to skip silently.
    #
    # LIMIT, stated because it bounds the retroactive fix: a row written
    # BEFORE this key existed carries no marker, and FLOOD_STUDIES has no LGA
    # or bounds field, so we cannot tell whether an absent study would have
    # covered that point without the raster we do not have. Such rows keep
    # whatever EPI and SES established. Re-running the report resolves it;
    # the census reports them separately rather than counting them as clean.
    # SCOPED to this address's council. A missing Tweed raster says nothing
    # about a Sydney property, and reporting it there would turn a correct,
    # established negative into a shrug — the opposite failure, and just as bad
    # for the reader. When the council is unknown the absence is NOT reported:
    # this under-reports rather than over-reports, deliberately, because a
    # false "not assessed" on every address in the state destroys the signal.
    council = str(
        raw.get("address_council")
        or normalised.get("ses_study_lga")
        or raw.get("lga_name")
        or ""
    ).lower()
    absent = list(raw.get("flood_studies_absent") or [])
    if absent and not council:
        # A study is missing AND we could not work out whose council this is,
        # so we cannot tell whether it covered this point. That is unknown, not
        # clear. Treating it as clear was the previous behaviour and it is the
        # same fail-open the three-state change exists to remove — the scoping
        # must not become a new way to reach a confident "no".
        unconsulted.append(
            "A council flood study is unavailable and the council for this "
            "address could not be resolved"
        )
    for study_key in absent:
        cfg = FLOOD_STUDIES.get(study_key) or {}
        study_lga = str(cfg.get("lga") or "").lower()
        if council and study_lga and study_lga in council:
            unconsulted.append(str(cfg.get("name") or study_key))

    return unconsulted


@icontract.ensure(
    lambda result: all(
        isinstance(g, dict) and "source" in g and "reason" in g
        and isinstance(g["source"], str) and isinstance(g["reason"], str)  # noqa: bracket-access
        and len(g["reason"]) > 10  # noqa: bracket-access
        for g in result
    ),
    description="Every gap must have non-empty 'source' and 'reason' strings — malformed gaps render blank in PDF.",
)
def _build_data_gap_reasons(internal_outputs: dict) -> list[dict]:
    """Return structured reasons explaining WHY each data source is unavailable.

    Reasons cite regulatory context (EPI revocation, council IP restrictions)
    rather than generic "no data" messages. This is a defensibility requirement:
    the user and their solicitor need to understand the structural data gap,
    not just see a blank field.
    """
    gaps: list[dict] = []

    # EPI — two distinct failure modes
    epi_class = internal_outputs.get("epi_flood_class")
    data_currency = internal_outputs.get("data_currency")
    ses_queried = internal_outputs.get("ses_in_flood_planning_area") is not None
    has_studies = bool(internal_outputs.get("flood_studies"))

    if data_currency == "query_failed":
        gaps.append({
            "source": "NSW EPI Flood Overlay",
            "reason": "NSW EPI flood mapping service did not respond.",
        })
    elif epi_class is None:
        # EPI query returned no data at all (source never responded or not queried)
        gaps.append({
            "source": "NSW EPI Flood Overlay",
            "reason": "NSW EPI flood mapping data not available for this address.",
        })
    elif epi_class == "none" and not ses_queried and not has_studies:
        # Only show revocation reason when EPI returned "none" AND no local
        # flood study data exists — mirrors _compute_flood_signal line 1113-1117.
        # If SES or study data exists, the "none" from EPI is genuinely "not in
        # a flood zone", not "no coverage".
        gaps.append({
            "source": "NSW EPI Flood Overlay",
            "reason": (
                "NSW EPI flood mapping does not cover this council area. "
                "Most councils revoked EPI flood layers in late 2023 "
                "(SEPP Resilience and Hazards 2021 Flood Planning Amendment)."
            ),
        })

    # Remaining sources — simple null checks
    _SIMPLE_GAPS = [
        ("ses_in_flood_planning_area", "Council flood study",
         "No council flood study data available for this area."),
        ("ground_elevation_m_ahd", "NSW 5m DEM",
         "Ground elevation data not available from NSW 5m DEM service."),
        ("jrc_water_occurrence_pct", "JRC Global Surface Water",
         "JRC Global Surface Water data not available for this location."),
        ("dea_wofs_frequency_pct", "DEA Water Observations",
         "DEA Water Observations data not available for this location."),
        ("bom_gauge_name", "BOM flood gauge",
         "No BOM flood gauge within 75km of this address."),
        ("ems_flood_detected", "Copernicus EMS",
         "Copernicus EMS flood activation data not available."),
    ]
    for field, source, reason in _SIMPLE_GAPS:
        if internal_outputs.get(field) is None:
            gaps.append({"source": source, "reason": reason})

    # Flood study rasters. Two DIFFERENT reasons, and they were previously
    # collapsed into the consultant-IP one — which is a false explanation when
    # the truth is that the file is missing from the host we are running on.
    absent = internal_outputs.get("flood_studies_absent") or []
    if absent:
        names = ", ".join(
            str((FLOOD_STUDIES.get(k) or {}).get("name") or k) for k in absent
        )
        gaps.append({
            "source": "Council flood study rasters",
            "reason": (
                f"A council flood study is configured for this service "
                f"({names}) but its data is not available to it, so the "
                f"1% AEP question could not be answered from that study."
            ),
        })
    elif not has_studies:
        gaps.append({
            "source": "Council flood study rasters",
            "reason": (
                "No council-published flood study raster data available. "
                "Some councils restrict access citing consultant intellectual property."
            ),
        })

    return gaps


@icontract.ensure(
    lambda result: result.get("flood_signal") in _VALID_FLOOD_SIGNALS,
    description="Normalised output must contain a valid flood_signal — frontend renders badge from this value.",
)
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
    # Hawkesbury FRMSP 2025 AEP flood levels — backward-compat flat fields
    for aep_key in ("2aep", "5aep", "10aep", "20aep", "50aep", "100aep", "200aep", "500aep", "pmf"):
        field = f"hawkesbury_flood_level_{aep_key}"
        normalised[field] = raw.get(field)
    normalised["hawkesbury_flood_study"] = raw.get("hawkesbury_flood_study")

    # New generalised fields
    normalised["flood_studies"] = raw.get("flood_studies") or []
    normalised["ground_elevation_m_ahd"] = raw.get("ground_elevation_m_ahd")

    # Derive in_100yr_flood_zone. THREE states, never two.
    #
    # This field is the single most consequential sentence in the report — it
    # drives insurance, price and whether a buyer proceeds. It used to start at
    # False and only four positive signals could move it, so a source that
    # could not be consulted produced a confident "not in a flood zone". That
    # is an active statement in the direction that causes harm, which is worse
    # than the absences this campaign has been deleting.
    #
    #   True  — at least one source places the point inside a 1% AEP extent
    #   False — no source did, AND every source that could have said yes was
    #           actually consulted
    #   None  — no source did, AND at least one was unreachable, so we do not
    #           know. Rendered as "not assessed": not a pass and not a fail.
    #
    # Mirrors flood_signal in this module, which has had an explicit
    # "unavailable" member since #872. This field was missed in that pass.
    in_100yr = False
    # 1. EPI flood planning area = 1% AEP extent by NSW planning definition
    if epi_class and epi_class not in ("none", ""):
        in_100yr = True
    # 2. SES/council flood class contains 1%AEP
    ses_class = normalised.get("ses_flood_class") or ""
    if "1%" in ses_class or "1AEP" in ses_class.upper() or "100" in ses_class:
        in_100yr = True
    # 3. Any flood study raster returned a 1pct design result
    for study in normalised["flood_studies"]:
        if (study.get("design") or {}).get("1pct") is not None:
            in_100yr = True
            break
    # 4. Hawkesbury backward-compat
    if normalised.get("hawkesbury_flood_level_100aep") is not None:
        in_100yr = True

    unconsulted = _unconsulted_1pct_sources(normalised, raw)
    normalised["in_100yr_flood_zone_unconsulted"] = unconsulted
    # A positive finding stands on its own: one source saying "inside the 1%
    # extent" is not weakened by another source being unreachable. Only the
    # NEGATIVE needs every source to have been asked.
    normalised["in_100yr_flood_zone"] = True if in_100yr else (None if unconsulted else False)

    # Compute flood depth from study raster + DEM where both available
    ground_elev = normalised["ground_elevation_m_ahd"]
    for study in normalised["flood_studies"]:
        for aep_key, entry in (study.get("design") or {}).items():
            if entry.get("depth_m") is None and entry.get("level_m_ahd") is not None and ground_elev is not None:
                computed_depth = entry["level_m_ahd"] - ground_elev
                entry["depth_m"] = round(max(0.0, computed_depth), 2)
        for event_year, entry in (study.get("historical") or {}).items():
            if entry.get("depth_m") is None and entry.get("level_m_ahd") is not None and ground_elev is not None:
                computed_depth = entry["level_m_ahd"] - ground_elev
                entry["depth_m"] = round(max(0.0, computed_depth), 2)

    # Compound risk layers — heritage, riparian, wetlands, landslide
    compound_risks = []
    for lt in _COMPOUND_LAYER_TYPES:
        val = raw.get(f"compound_{lt}")
        normalised[f"compound_{lt}"] = val
        if val is not None:
            compound_risks.append(lt)
    normalised["compound_risk_layers"] = compound_risks
    normalised["compound_risk_notes"] = _build_compound_risk_notes(compound_risks)

    normalised["flood_signal"] = _compute_flood_signal(normalised)
    return normalised


def _s1b_gap_affected(start: date, end: date) -> bool:
    return start <= S1B_GAP_END and end >= S1B_GAP_START


# Sentinel keys that genuine flood outputs carry (any one suffices). Rows
# written before the #762 fix can hold bushfire or shadow outputs under
# product='flood' — the shared-report_id clobber. A cached row missing every
# sentinel key is poisoned and must be skipped, never served.
_CACHE_SENTINEL_KEYS = ("epi_flood_class", "flood_signal")


def _first_valid_cached_row(rows):
    """Return the newest cached row whose outputs are flood-shaped.

    Defence in depth for issue #762 (prior-art-checked: hardening of this
    module's own existing cache read, no new source): skip poisoned rows and
    fall through to the next row or to live compute.
    """
    for row in rows or []:
        outputs = row.get("outputs") if isinstance(row, dict) else None
        if isinstance(outputs, dict) and any(k in outputs for k in _CACHE_SENTINEL_KEYS):
            return row
    return None


def _write_report(report_id, address, lat, lng, prop_id, inputs, internal_outputs,
                  run_date=None):
    """run_date: the date the analysis was actually COMPUTED. Defaults to today
    for fresh runs; the cache-hit path passes the original row's run_date so a
    stale result never wears today's date (output-grounding fix 2 — re-stamping
    was a freshness lie)."""
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
                report_id, address, lat, lng, prop_id, run_date or date.today(),
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
    #: Write the run to `property_reports` and `report_audit_trail`, or not.
    #:
    #: DEFAULTS TO TRUE so every existing caller — the API route, the batch
    #: path, the PDF flow — is unchanged. Only a caller that opts out skips.
    #:
    #: Exists for calibration. scripts/run_flood_calibration_2022.py runs the
    #: real pipeline over N=150 sampled points to measure recall, and each run
    #: was landing TWO synthetic production rows: a property_reports row
    #: addressed "calibration EMSR567/AOI03" and a report_audit_trail row. 300
    #: rows per run, and they move the denominators the DQ-57, DQ-85 and DQ-86
    #: probes count flood reports with — so measuring the product would have
    #: corrupted the measurements OF the product.
    #:
    #: It suppresses PERSISTENCE ONLY. Every source is still queried and the
    #: full answer still computed and returned, so a calibration run scores
    #: exactly what a customer would have been served. A flag that changed the
    #: computation would make the calibration measure something else.
    persist: bool = True


class FloodBatchRequest(BaseModel):
    lga_name: str
    wet_season_year: int   # e.g. 2022 = Nov 2021 - Mar 2022


class DataGap(BaseModel):
    source: str
    reason: str


class FloodOutputs(BaseModel):
    """Validated output contract — must match frontend FloodReportData interface."""
    model_config = {"extra": "allow"}  # allow hawkesbury_flood_level_* dynamic keys

    epi_flood_class: Optional[str] = None
    epi_flood_label: Optional[str] = None
    sar_flood_detected: Optional[bool] = None
    sar_confidence: Optional[str] = None
    sar_analysis_date: Optional[str] = None
    ems_flood_detected: Optional[bool] = None
    ems_activations: Optional[list] = None
    jrc_water_occurrence_pct: Optional[float] = None
    jrc_data_year: Optional[int] = None
    dea_wofs_frequency_pct: Optional[float] = None
    ses_in_flood_planning_area: Optional[bool] = None
    ses_flood_class: Optional[str] = None
    ses_study_name: Optional[str] = None
    ses_study_lga: Optional[str] = None
    bom_gauge_name: Optional[str] = None
    bom_gauge_distance_km: Optional[float] = None
    bom_last_major_flood_date: Optional[str] = None
    bom_last_major_flood_peak_m: Optional[float] = None
    bom_flood_history: list = []
    flood_study_name: Optional[str] = None
    flood_study_date: Optional[str] = None
    s1_gap_warning: Optional[str] = None
    data_currency: str = "unknown"
    flood_signal: Literal["none", "low", "moderate", "elevated", "unavailable"]
    ground_elevation_m_ahd: Optional[float] = None
    # None = not assessed. NOT the same as False, and the default is None
    # because a response object that was never populated has not established
    # that a property is outside the 1% AEP extent.
    in_100yr_flood_zone: Optional[bool] = None
    # Must be declared here too. Without it pydantic drops the list at this
    # boundary and the frontend gets an absence it cannot explain — the
    # 'what we tried' half of the no-result standard, silently deleted.
    in_100yr_flood_zone_unconsulted: list = []
    flood_studies: list = []
    compound_heritage: Optional[bool] = None
    compound_riparian: Optional[bool] = None
    compound_wetlands: Optional[bool] = None
    compound_landslide: Optional[bool] = None
    compound_risk_layers: list = []
    compound_risk_notes: list = []


class FloodResponse(BaseModel):
    """Runtime-validated flood screening response."""
    address: str
    lat: float
    lng: float
    run_date: str
    outputs: FloodOutputs
    confidence: str
    data_sources: list[str]
    data_gaps: list[DataGap] = []


class FloodRefusedResponse(BaseModel):
    """Returned when too few data sources responded to produce a screening."""
    address: str
    lat: float
    lng: float
    run_date: str
    refused: Literal[True]
    reason: str
    available_count: int
    total_count: int
    data_gaps: list[DataGap] = []


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/flood", response_model=Union[FloodResponse, FloodRefusedResponse])
def run_flood(req: FloodRequest):
    """
    On-demand flood analysis.
    Fast path: return pre-computed result if cached.
    Slow path: EPI + EMS (PostGIS) + JRC (rasterio remote read) + BOM gauge (SOS2)
               + SES council flood studies (PostGIS) + DEA WOfS (WCS).
    SAR analysis is batch-only (Phase 3B).
    """
    # PERSISTENCE, bound once (see FloodRequest.persist). Every write in this
    # function goes through these two names instead of _write_report and
    # log_audit_trail directly, so persist=False suppresses all of them —
    # including the cache-copy write and the "still write for audit trail"
    # write on the refuse-to-serve branch, which a happy-path-only guard would
    # have missed. A write added here later inherits the flag by using the
    # same names, rather than needing its own `if`.
    #
    # Bound rather than wrapped in `if` blocks on purpose: wrapping re-indents
    # the existing call bodies, and the bracket-access lint reads re-indented
    # lines as newly added unsafe dict access. The guard should not force a
    # cosmetic rewrite of code it is not changing.
    # getattr with a True default, NOT req.persist. run_flood is called with
    # duck-typed request objects as well as real FloodRequests — a
    # types.SimpleNamespace in tests/test_execution_manifests.py, and anything
    # else that grew a request shape without this field. Reading the attribute
    # directly raised AttributeError there, which the pre-push suite caught:
    # a flag meant to suppress a side effect had become a hard requirement on
    # every caller's type.
    #
    # The default is True, which is the safe direction twice over: an object
    # that does not know about persistence gets the behaviour it had before
    # this change, and the failure mode of a typo in the field name is
    # "writes anyway", never "silently stops recording customer reports".
    _noop = lambda *a, **kw: None                      # noqa: E731
    _persist = getattr(req, "persist", True)
    write_report = _write_report if _persist else _noop
    audit_trail = log_audit_trail if _persist else _noop

    # Units/CRS entry check (campaign item 4): a swapped or projected
    # coordinate reproduces identically on every recompute — this is the only
    # defence. Typed unavailable, never a screening from wrong-CRS input.
    coord_reason = check_point_nsw(req.lat, req.lng)
    if coord_reason:
        raise HTTPException(
            422, f"Flood screening could not be determined: {coord_reason}")

    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Max age 90 days (output-grounding fix 2): flood inputs move on
            # seasonal/quarterly cadences (EPI overlay refreshes, wet-season
            # SAR batches, BOM history), so a quarter bounds staleness while
            # keeping the cache's point — skipping a ~60s recompute on repeat
            # lookups. Older rows are recomputed, not served.
            # prior-art-checked: this module's own cache read gains the
            # stored `inputs` column (so the original execution manifest can
            # ride the cache-copy like run_date) and a ~50m coordinate
            # proximity bound — address text alone could hand parcel A's
            # outputs to a same-address request that geocoded to parcel B
            # (Sol finding, 2026-08-03). No new source.
            cur.execute(
                "SELECT outputs, confidence, data_sources, run_date, inputs "
                "FROM property_reports "
                "WHERE product='flood' AND address=%s "
                "  AND abs(lat - %s) < 0.0005 AND abs(lng - %s) < 0.0005 "
                "  AND run_date > CURRENT_DATE - INTERVAL '90 days' "
                "ORDER BY run_date DESC LIMIT 5",
                (req.address, req.lat, req.lng)
            )
            # #762 (prior-art-checked: same cache read hardened in place, no
            # new source): skip poisoned rows — another product's outputs
            # clobbered under product='flood' — instead of blindly serving
            # the newest.
            cached = _first_valid_cached_row(cur.fetchall())
        if cached:
            # Write a row for the new report_id so PDF generation can find it.
            # The ORIGINAL run_date is carried over — this row is a copy of an
            # older computation, and stamping it with today would relabel a
            # stale result as fresh (fix 2).
            # The ORIGINAL inputs (incl. the execution manifest) ride along
            # exactly like run_date: this row is a COPY of an older
            # computation, and a re-derived manifest would claim inputs the
            # cached numbers never came from (campaign item 4 cache rule).
            write_report(
                req.report_id, req.address, req.lat, req.lng,
                req.prop_id,
                cached.get("inputs") or {
                    "lat": req.lat, "lng": req.lng,
                    # A pre-manifest row recorded no inputs — say so rather
                    # than presenting the new request's coordinates as the
                    # original computation's record (they are proximity-
                    # bounded to ~50m by the cache SELECT).
                    "inputs_provenance": "original inputs not recorded "
                                         "(pre-manifest report)",
                },
                cached["outputs"] or {},
                run_date=cached.get("run_date"),
            )
            audit_trail(
                report_id=req.report_id,
                pipeline_name="flood",
                input_params={"address": req.address, "lat": req.lat, "lng": req.lng},
                data_sources=[],
                output_summary=cached["outputs"] or {},
                disclaimer_version=get_current_disclaimer_version("flood"),
                intermediate_calculations={"cache_hit": True},
            )
            _orig_run_date = cached.get("run_date")
            return {
                "address": req.address, "lat": req.lat, "lng": req.lng,
                # The date the analysis was COMPUTED, not the date it was
                # re-served — a cached result wearing today's date was a
                # freshness lie (output-grounding fix 2).
                "run_date": (_orig_run_date.isoformat() if _orig_run_date
                             else date.today().isoformat()),
                "cache_hit": True,
                "outputs": _normalise_outputs(cached["outputs"] or {}),
                "confidence": cached["confidence"],
                "data_sources": cached["data_sources"] or _DATA_SOURCES_BASE,
                "data_gaps": _build_data_gap_reasons(cached.get("outputs") or {}),
            }
    except Exception as e:
        logger.warning(f"Cache lookup: {e}")
    finally:
        if conn:
            conn.close()

    # Audit trail: create DataSourceQuery objects before queries run
    coord_params = {"lat": req.lat, "lng": req.lng}
    ds_epi = DataSourceQuery("NSW SEED EPI WFS", EPI_REST, coord_params)
    ds_ems = DataSourceQuery("Copernicus EMS flood events", "local:copernicus_flood_events", coord_params)
    ds_jrc = DataSourceQuery("JRC Global Surface Water", _jrc_tile_url(req.lat, req.lng), coord_params)
    ds_wofs = DataSourceQuery("DEA Water Observations (WOfS)", DEA_WCS_BASE, coord_params)
    ds_bom = DataSourceQuery("BOM Water Data Online", BOM_SOS2, coord_params)
    ds_ses = DataSourceQuery("SES / Council flood study", "local:spatial_overlays", coord_params)
    ds_studies = DataSourceQuery("Flood study rasters", "local:flood_study_rasters", coord_params)
    ds_dem = DataSourceQuery("NSW 5m DEM", _DEM_IDENTIFY_URL, coord_params)
    ds_compound = DataSourceQuery("Compound risk layers", "local:spatial_overlays", coord_params)

    with ThreadPoolExecutor(max_workers=10) as pool:
        f_epi  = pool.submit(_query_epi_overlay, req.lat, req.lng)
        f_ems  = pool.submit(_query_copernicus_ems, req.lat, req.lng)
        f_jrc  = pool.submit(_query_jrc_surface_water, req.lat, req.lng)
        f_bom  = pool.submit(_query_bom_gauge, req.lat, req.lng)
        f_ses  = pool.submit(_query_ses_flood_study, req.lat, req.lng)
        f_wofs = pool.submit(_query_dea_wofs, req.lat, req.lng)
        f_studies = pool.submit(_query_flood_study_rasters, req.lat, req.lng)
        f_council = pool.submit(_query_address_council, req.lat, req.lng)
        f_dem  = pool.submit(_query_ground_elevation, req.lat, req.lng)
        f_compound = pool.submit(_query_compound_risk_layers, req.lat, req.lng)
        epi  = f_epi.result()
        ems  = f_ems.result()
        jrc  = f_jrc.result()
        bom  = f_bom.result()
        ses  = f_ses.result()
        wofs = f_wofs.result()
        studies = f_studies.result()
        # The council this address is IN, for scoping an absent study.
        # ses_study_lga is the council of a MATCHED study and is null in
        # 80% of reports — null exactly when a missing study matters.
        studies["address_council"] = f_council.result()
        dem  = f_dem.result()
        compound = f_compound.result()

    # Audit trail: record responses
    ds_epi.record_response(epi, features_returned=0 if epi.get("epi_flood_class") in (None, "none") else 1)
    ds_ems.record_response(ems, features_returned=len(ems.get("ems_activations") or []))
    ds_jrc.record_response(jrc, features_returned=1 if jrc.get("jrc_water_occurrence_pct") is not None else 0)
    ds_wofs.record_response(wofs, features_returned=1 if wofs.get("dea_wofs_frequency_pct") is not None else 0)
    ds_bom.record_response(bom, features_returned=1 if bom.get("bom_gauge_name") is not None else 0)
    ds_ses.record_response(ses, features_returned=1 if ses.get("ses_in_flood_planning_area") else 0)
    ds_studies.record_response(studies, features_returned=len(studies.get("flood_studies") or []))
    ds_dem.record_response(dem, features_returned=1 if dem.get("ground_elevation_m_ahd") is not None else 0)
    compound_count = sum(1 for v in compound.values() if v is not None)
    ds_compound.record_response(compound, features_returned=compound_count)

    internal_outputs = {
        "wet_seasons_checked": 0,
        "flood_event_count": None,
        "sentinel1b_gap_affected": True,
        "sar_flood_detected": None,
        "sar_confidence": None,
        "sar_analysis_date": None,
        **epi, **ems, **jrc, **bom, **ses, **wofs, **studies, **dem, **compound,
    }
    internal_outputs["s1_gap_warning"] = _build_s1_gap_warning(internal_outputs)

    # Execution manifest (campaign item 4): every identity below is read from
    # the dicts the source queries THEMSELVES returned this run (epi/ems/...),
    # never a parallel lookup. SAR is recorded as not-queried — the honest
    # state until Phase 3B exists.
    manifest = build_manifest(
        product="flood",
        algorithm_version=ALGORITHM_VERSION,
        inputs={
            "epi_overlay": {"flood_class": epi.get("epi_flood_class"),
                            "data_currency": epi.get("data_currency"),
                            "study_name": epi.get("flood_study_name"),
                            "study_date": epi.get("flood_study_date")},
            "copernicus_ems": {"activations": [
                a.get("activation_id") if isinstance(a, dict) else a
                for a in (ems.get("ems_activations") or [])]},
            "jrc_surface_water": {"tile_url": _jrc_tile_url(req.lat, req.lng),
                                  "dataset_year": jrc.get("jrc_data_year")},
            "dea_wofs": {"layer": DEA_WOFS_LAYER,
                         "value_pct": wofs.get("dea_wofs_frequency_pct")},
            "bom_gauge": {"name": bom.get("bom_gauge_name"),
                          "distance_km": bom.get("bom_gauge_distance_km")},
            "ses_study": {"name": ses.get("ses_study_name"),
                          "lga": ses.get("ses_study_lga")},
            "flood_study_rasters": [
                {"key": s.get("study_key"), "name": s.get("study_name")}
                for s in (studies.get("flood_studies") or [])
                if isinstance(s, dict)],
            "dem": {"ground_elevation_m_ahd": dem.get("ground_elevation_m_ahd")},
            "sentinel1_sar": {"queried": False,
                              "note": "S1 VH analysis is batch-only (Phase 3B); "
                                      "no SAR observation feeds this report"},
        },
        query_params={"lat": req.lat, "lng": req.lng},
        parcel_identity={"prop_id": req.prop_id},
    )

    inputs = {"lat": req.lat, "lng": req.lng, MANIFEST_KEY: manifest}

    # --- Minimum viable screening: refuse if too few sources responded ---
    available_count = _count_available_sources(internal_outputs)
    if available_count < _MIN_SOURCES_FOR_SCREENING:
        # Still write report for audit trail
        try:
            write_report(
                req.report_id, req.address, req.lat, req.lng,
                req.prop_id, inputs, internal_outputs,
            )
        except Exception as e:
            logger.error(f"Flood report DB write failed (refused): {e}")
        return {
            "address": req.address, "lat": req.lat, "lng": req.lng,
            "run_date": date.today().isoformat(),
            "refused": True,
            "reason": (
                f"Insufficient flood data sources to produce a screening. "
                f"{available_count} of {len(_SOURCE_AVAILABILITY_CHECKS)} sources "
                f"returned data (minimum {_MIN_SOURCES_FOR_SCREENING} required)."
            ),
            "available_count": available_count,
            "total_count": len(_SOURCE_AVAILABILITY_CHECKS),
            "data_gaps": _build_data_gap_reasons(internal_outputs),
        }

    try:
        write_report(
            req.report_id, req.address, req.lat, req.lng,
            req.prop_id, inputs, internal_outputs,
        )
    except Exception as e:
        logger.error(f"Flood report DB write failed: {e}")
        raise HTTPException(status_code=503, detail="Failed to save report — please retry")

    # Audit trail (non-blocking — won't prevent report delivery on failure)
    outputs = _normalise_outputs(internal_outputs)
    audit_trail(
        report_id=req.report_id,
        pipeline_name="flood",
        input_params=inputs,
        data_sources=[ds_epi, ds_ems, ds_jrc, ds_wofs, ds_bom, ds_ses, ds_studies, ds_dem, ds_compound],
        output_summary=outputs,
        disclaimer_version=get_current_disclaimer_version("flood"),
        intermediate_calculations={
            "flood_signal": outputs.get("flood_signal"),
            "in_100yr_flood_zone": outputs.get("in_100yr_flood_zone"),
            "epi_had_data": epi.get("epi_flood_class") not in (None, "none"),
            "ems_had_data": ems.get("ems_flood_detected") is not None,
            "jrc_had_data": jrc.get("jrc_water_occurrence_pct") is not None,
            "wofs_had_data": wofs.get("dea_wofs_frequency_pct") is not None,
            "bom_had_data": bom.get("bom_gauge_name") is not None,
            "ses_had_data": ses.get("ses_in_flood_planning_area") is not None,
            "flood_studies_matched": len(studies.get("flood_studies") or []),
            "ground_elevation_m_ahd": dem.get("ground_elevation_m_ahd"),
        },
    )

    return {
        "address": req.address, "lat": req.lat, "lng": req.lng,
        "run_date": date.today().isoformat(),
        "outputs": _normalise_outputs(internal_outputs),
        "confidence": _compute_confidence(internal_outputs),
        "data_sources": _build_data_sources(internal_outputs),
        "data_gaps": _build_data_gap_reasons(internal_outputs),
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
