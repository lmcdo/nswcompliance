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
"""
import logging, math, os
from datetime import date, datetime
from typing import Optional

import psycopg2, psycopg2.extras, requests
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


def _get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST","127.0.0.1"),
        database=os.environ.get("DB_NAME","nsw_planning"),
        user=os.environ.get("DB_USER","postgres"),
        password=os.environ.get("DB_PASSWORD",""),
        port=int(os.environ.get("DB_PORT",5432)),
    )


def _query_epi_overlay(lat: float, lng: float) -> dict:
    try:
        params = {
            "SERVICE":"WFS","VERSION":"2.0.0","REQUEST":"GetFeature",
            "TYPENAMES":"Planning_Hazard:Flood","SRSNAME":"EPSG:4326",
            "CQL_FILTER":f"INTERSECTS(Shape,POINT({lng} {lat}))",
            "outputFormat":"application/json",
        }
        r = requests.get(EPI_WFS, params=params, timeout=20)
        r.raise_for_status()
        feats = r.json().get("features") or []
        currency = feats[0].get("properties",{}).get("DataDate","unknown") if feats else "unknown"
        return {"in_epi_overlay": len(feats) > 0, "epi_data_currency": currency}
    except Exception as e:
        logger.warning(f"EPI WFS: {e}")
        return {"in_epi_overlay": None, "epi_data_currency": "query_failed"}


def _s1b_gap_affected(start: date, end: date) -> bool:
    return start <= S1B_GAP_END and end >= S1B_GAP_START


def _write_report(report_id, address, lat, lng, prop_id, inputs, outputs):
    confidence = "high" if outputs.get("wet_seasons_checked",0) >= 4 else "low"
    sql = """
        INSERT INTO property_reports
            (id,product,address,lat,lng,prop_id,run_date,inputs,outputs,confidence,data_sources)
        VALUES (%s,'flood',%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO UPDATE SET outputs=EXCLUDED.outputs
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (
                report_id, address, lat, lng, prop_id, date.today(),
                psycopg2.extras.Json(inputs), psycopg2.extras.Json(outputs),
                confidence, ["Microsoft Planetary Computer S1 RTC","NSW SEED EPI WFS"],
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
                    "SELECT outputs,confidence FROM property_reports "
                    "WHERE product='flood' AND address=%s ORDER BY run_date DESC LIMIT 1",
                    (req.address,)
                )
                cached = cur.fetchone()
        if cached:
            return {"status":"complete","report_id":req.report_id,
                    "outputs":cached["outputs"],"confidence":cached["confidence"],"source":"cached"}
    except Exception as e:
        logger.warning(f"Cache lookup: {e}")

    epi = _query_epi_overlay(req.lat, req.lng)
    outputs = {
        "flood_event_count": None, "wet_seasons_checked": 0,
        "sentinel1b_gap_affected": True,
        "note": "S1 batch not yet run for this property. EPI overlay check only.",
        **epi,
    }
    _write_report(req.report_id, req.address, req.lat, req.lng,
                  req.prop_id, {"lat":req.lat,"lng":req.lng}, outputs)
    return {"status":"complete","report_id":req.report_id,"outputs":outputs,"confidence":"low"}


@router.post("/flood/batch")
def run_flood_batch(req: FloodBatchRequest):
    """
    Batch flood analysis: one LGA + one wet season. Called by Trigger.dev quarterly cron.
    Processes one season at a time to stay within Railway 8GB RAM.
    Full S1 pipeline implementation: Phase 3B in ce-satellite-implementation-plan.md.
    """
    year = req.wet_season_year
    wet_start = date(year-1, 11, 1); wet_end = date(year, 3, 31)
    gap = _s1b_gap_affected(wet_start, wet_end)
    return {
        "status": "queued",
        "lga": req.lga_name,
        "wet_season": f"{wet_start}/{wet_end}",
        "sentinel1b_gap_affected": gap,
        "note": "Batch S1 VH processing is Phase 3B. EPI on-demand path is active.",
    }
