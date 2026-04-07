"""
Wet Season Flood Truth Engine -- FastAPI router.

POST /pipeline/flood        -- on-demand: return pre-computed result or EPI overlay only
POST /pipeline/flood/batch  -- batch LGA processing (Trigger.dev cron, quarterly)

Data sources:
  Sentinel-1 RTC via Microsoft Planetary Computer (no auth, confirmed April 2026)
  SEED EPI Flood WFS (free, no auth, confirmed live)

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
    "epi_flood_class": str | null,   # "high_flood_risk"|"medium_flood_risk"|"low_flood_risk"|"flood_planning_area"|"none"|null
    "epi_flood_label": str | null,
    "sar_flood_detected": bool | null,
    "sar_confidence": str | null,
    "sar_analysis_date": str | null,
    "s1_gap_warning": str | null,
    "data_currency": str
  },
  "confidence": str,
  "data_sources": list[str]
}
"""
import logging
import math
import os
from datetime import date, datetime
from typing import Optional

import psycopg2
import psycopg2.extras
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

PC_CATALOG = "https://planetarycomputer.microsoft.com/api/stac/v1"
S1_COLLECTION = "sentinel-1-rtc"
EPI_WFS = ("https://mapprod3.environment.nsw.gov.au/arcgis/services/"
           "Planning/Hazard/MapServer/WFSServer")
FLOOD_RATIO = 1.25
S1B_GAP_START = date(2021, 12, 23)
S1B_GAP_END   = date(2025, 3, 4)
DATA_SOURCES = ["NSW SEED EPI WFS", "Microsoft Planetary Computer S1 RTC"]

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


def _query_epi_overlay(lat: float, lng: float) -> dict:
    """
    Query NSW SEED EPI Flood WFS for the given point.
    Returns dict with epi_flood_class, epi_flood_label, data_currency.
    """
    try:
        params = {
            "SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature",
            "TYPENAMES": "Planning_Hazard:Flood", "SRSNAME": "EPSG:4326",
            "CQL_FILTER": f"INTERSECTS(Shape,POINT({lng} {lat}))",
            "outputFormat": "application/json",
        }
        r = requests.get(EPI_WFS, params=params, timeout=20)
        r.raise_for_status()
        feats = r.json().get("features") or []
        if not feats:
            return {
                "epi_flood_class": "none",
                "epi_flood_label": "No EPI Flood Overlay",
                "data_currency": "unknown",
            }

        props = feats[0].get("properties", {})
        currency = props.get("DataDate", "unknown")

        # Try common property names for flood class
        raw_class = (
            props.get("FloodClass")
            or props.get("Category")
            or props.get("FldClass")
            or props.get("Flood_Class")
            or ""
        ).strip().lower()

        epi_class = _EPI_CLASS_MAP.get(raw_class, "flood_planning_area")
        epi_label = _EPI_CLASS_LABELS.get(epi_class, "Flood Planning Area")

        return {
            "epi_flood_class": epi_class,
            "epi_flood_label": epi_label,
            "data_currency": currency,
        }
    except Exception as e:
        logger.warning(f"EPI WFS: {e}")
        return {
            "epi_flood_class": None,
            "epi_flood_label": None,
            "data_currency": "query_failed",
        }


def _normalise_outputs(raw: dict) -> dict:
    """
    Convert stored/internal outputs to frontend FloodOutputs contract.
    Handles both old-format (in_epi_overlay bool) and new-format outputs.
    """
    # EPI class — handle old bool format from early writes
    epi_class = raw.get("epi_flood_class")
    epi_label = raw.get("epi_flood_label")
    if epi_class is None:
        in_overlay = raw.get("in_epi_overlay")
        if isinstance(in_overlay, bool):
            epi_class = "flood_planning_area" if in_overlay else "none"
            epi_label = _EPI_CLASS_LABELS.get(epi_class)

    # SAR fields — not populated until batch runs
    sar_detected = raw.get("sar_flood_detected")
    if sar_detected is None:
        flood_events = raw.get("flood_event_count")
        if flood_events is not None:
            sar_detected = bool(flood_events)

    # S1B gap warning
    s1_gap_warning = raw.get("s1_gap_warning")
    if s1_gap_warning is None and raw.get("sentinel1b_gap_affected"):
        s1_gap_warning = (
            "Sentinel-1B was non-operational Dec 2021 – Mar 2025. "
            "Flood detection for 2022 La Niña season uses Sentinel-1A only (reduced coverage)."
        )

    data_currency = raw.get("data_currency") or raw.get("epi_data_currency", "unknown")

    return {
        "epi_flood_class": epi_class,
        "epi_flood_label": epi_label,
        "sar_flood_detected": sar_detected,
        "sar_confidence": raw.get("sar_confidence"),
        "sar_analysis_date": raw.get("sar_analysis_date"),
        "s1_gap_warning": s1_gap_warning,
        "data_currency": data_currency,
    }


def _s1b_gap_affected(start: date, end: date) -> bool:
    return start <= S1B_GAP_END and end >= S1B_GAP_START


def _write_report(report_id, address, lat, lng, prop_id, inputs, internal_outputs):
    """Write internal outputs (full detail) to DB for batch enrichment later."""
    confidence = "high" if internal_outputs.get("wet_seasons_checked", 0) >= 4 else "low"
    sql = """
        INSERT INTO property_reports
            (id, product, address, lat, lng, prop_id, run_date, inputs, outputs, confidence, data_sources)
        VALUES (%s, 'flood', %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET outputs = EXCLUDED.outputs
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (
                report_id, address, lat, lng, prop_id, date.today(),
                psycopg2.extras.Json(inputs),
                psycopg2.extras.Json(internal_outputs),
                confidence,
                DATA_SOURCES,
            ))
        conn.commit()


class FloodRequest(BaseModel):
    address: str
    prop_id: Optional[str] = None
    lat: float
    lng: float
    report_id: str


class FloodBatchRequest(BaseModel):
    lga_name: str
    wet_season_year: int   # e.g. 2022 = Nov 2021 - Mar 2022


@router.post("/flood")
def run_flood(req: FloodRequest):
    """
    On-demand: check pre-computed result first (fast path), else EPI-only query.
    Full S1 analysis happens via batch job.
    """
    try:
        with _get_conn() as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute(
                    "SELECT outputs, confidence FROM property_reports "
                    "WHERE product='flood' AND address=%s ORDER BY run_date DESC LIMIT 1",
                    (req.address,)
                )
                cached = cur.fetchone()
        if cached:
            return {
                "address": req.address,
                "lat": req.lat,
                "lng": req.lng,
                "run_date": date.today().isoformat(),
                "outputs": _normalise_outputs(cached["outputs"]),
                "confidence": cached["confidence"],
                "data_sources": DATA_SOURCES,
            }
    except Exception as e:
        logger.warning(f"Cache lookup: {e}")

    epi = _query_epi_overlay(req.lat, req.lng)
    internal_outputs = {
        "wet_seasons_checked": 0,
        "flood_event_count": None,
        "sentinel1b_gap_affected": True,
        "sar_flood_detected": None,
        "sar_confidence": None,
        "sar_analysis_date": None,
        "s1_gap_warning": (
            "Sentinel-1B was non-operational Dec 2021 – Mar 2025. "
            "Flood detection for 2022 La Niña season uses Sentinel-1A only (reduced coverage)."
        ),
        **epi,
    }
    _write_report(req.report_id, req.address, req.lat, req.lng,
                  req.prop_id, {"lat": req.lat, "lng": req.lng}, internal_outputs)

    return {
        "address": req.address,
        "lat": req.lat,
        "lng": req.lng,
        "run_date": date.today().isoformat(),
        "outputs": _normalise_outputs(internal_outputs),
        "confidence": "low",
        "data_sources": DATA_SOURCES,
    }


@router.post("/flood/batch")
def run_flood_batch(req: FloodBatchRequest):
    """
    Batch flood analysis: one LGA + one wet season. Called by Trigger.dev quarterly cron.
    Processes one season at a time to stay within Railway 8GB RAM.
    Full S1 pipeline implementation: Phase 3B in ce-satellite-implementation-plan.md.
    """
    year = req.wet_season_year
    wet_start = date(year - 1, 11, 1)
    wet_end = date(year, 3, 31)
    gap = _s1b_gap_affected(wet_start, wet_end)
    return {
        "status": "queued",
        "lga": req.lga_name,
        "wet_season": f"{wet_start}/{wet_end}",
        "sentinel1b_gap_affected": gap,
        "note": "Batch S1 VH processing is Phase 3B. EPI on-demand path is active.",
    }
