"""
Solar Yield Underwriter — FastAPI router.

POST /pipeline/solar-yield
  Input:  { address, prop_id, lat, lng, report_id }
  Output: writes to property_reports, returns full output JSON

Pipeline:
  1. Google Solar API buildingInsights — roof segments, max panels, annual kWh
  2. Heritage flag from regulatory_provisions
  3. Write to property_reports, return result

Data sources:
  Google Solar API (requires GOOGLE_MAPS_API_KEY with Solar API enabled)

Response contract (must match frontend-nextjs/app/reports/solar-yield/page.tsx):
{
  "max_panels": int,
  "max_panel_area_m2": float,
  "annual_kwh_estimate": float,
  "sunshine_hours_per_year": float,
  "best_pitch_deg": float,
  "best_azimuth_deg": float,   # compass bearing: 0=N, 90=E, 180=S, 270=W
  "roof_area_m2": float,
  "is_heritage": bool,
  "imagery_date": str,         # "YYYY-MM" or "unknown"
  "coverage_available": bool
}
"""
import logging
import os
from datetime import date
from typing import Optional

import psycopg2
import psycopg2.extras
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

GOOGLE_SOLAR_API = "https://solar.googleapis.com/v1/buildingInsights:findClosest"
DATA_SOURCES = ["Google Solar API"]


class SolarYieldRequest(BaseModel):
    address: str
    prop_id: Optional[str] = None
    lat: float
    lng: float
    report_id: str
    lot_geometry: Optional[dict] = None  # unused now, kept for API compat


class SolarYieldOutput(BaseModel):
    max_panels: int
    max_panel_area_m2: float
    annual_kwh_estimate: float
    sunshine_hours_per_year: float
    best_pitch_deg: float
    best_azimuth_deg: float
    roof_area_m2: float
    is_heritage: bool
    imagery_date: str
    coverage_available: bool


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


def _write_report(
    report_id: str,
    address: str,
    lat: float,
    lng: float,
    prop_id: Optional[str],
    inputs: dict,
    outputs: dict,
    confidence: str,
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
                DATA_SOURCES,
            ))
        conn.commit()


def _query_google_solar(lat: float, lng: float) -> dict:
    """
    Call Google Solar API buildingInsights endpoint.
    Returns the raw API response dict, or {"coverage_available": False} on 404.
    Raises on other HTTP errors.
    """
    api_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not api_key:
        raise ValueError("GOOGLE_MAPS_API_KEY env var not set")

    r = requests.get(
        GOOGLE_SOLAR_API,
        params={
            "location.latitude": lat,
            "location.longitude": lng,
            "requiredQuality": "MEDIUM",
            "key": api_key,
        },
        timeout=15,
    )

    if r.status_code == 404:
        logger.warning(f"Google Solar API: no coverage at ({lat}, {lng})")
        return {"coverage_available": False}

    r.raise_for_status()
    return r.json()


def _parse_solar_response(data: dict) -> SolarYieldOutput:
    """
    Extract the fields we need from the Google Solar API buildingInsights response.

    Best segment: the roof segment with the largest area (most solar-viable).
    Annual yield: taken from the max-panel solarPanelConfigs entry.
    Azimuth convention: Google uses standard compass bearing (0=N, 90=E, 180=S, 270=W).
    """
    if not data.get("coverage_available", True):
        return SolarYieldOutput(
            max_panels=0,
            max_panel_area_m2=0.0,
            annual_kwh_estimate=0.0,
            sunshine_hours_per_year=0.0,
            best_pitch_deg=0.0,
            best_azimuth_deg=0.0,
            roof_area_m2=0.0,
            is_heritage=False,
            imagery_date="unknown",
            coverage_available=False,
        )

    sp = data.get("solarPotential", {})

    # Imagery date
    img_date = data.get("imageryDate", {})
    if img_date.get("year") and img_date.get("month"):
        imagery_date = f"{img_date['year']}-{img_date['month']:02d}"
    else:
        imagery_date = "unknown"

    # Roof area
    roof_area = sp.get("wholeRoofStats", {}).get("areaMeters2", 0.0)

    # Best segment: highest median sunshine hours (index 4 of sunshineQuantiles).
    # This picks the sunniest face of the roof, not just the largest.
    # Tiebreak: prefer segments closer to north-facing (azimuth near 0/360).
    segments = sp.get("roofSegmentStats", [])

    def _segment_score(seg: dict) -> float:
        quantiles = seg.get("stats", {}).get("sunshineQuantiles", [])
        median_sun = float(quantiles[4]) if len(quantiles) > 4 else 0.0
        az = seg.get("azimuthDegrees", 180.0)
        # Small bonus for north-facing (az near 0 or 360) in Southern Hemisphere
        north_bonus = (1.0 - min(az, 360 - az) / 180.0) * 10
        return median_sun + north_bonus

    best_seg = max(segments, key=_segment_score) if segments else {}
    best_pitch = best_seg.get("pitchDegrees", 0.0)
    best_azimuth = best_seg.get("azimuthDegrees", 0.0)

    # Max panel config (last entry = maximum panels)
    configs = sp.get("solarPanelConfigs", [])
    max_config = configs[-1] if configs else {}
    annual_kwh = max_config.get("yearlyEnergyDcKwh", 0.0)

    return SolarYieldOutput(
        max_panels=int(sp.get("maxArrayPanelsCount", 0)),
        max_panel_area_m2=round(float(sp.get("maxArrayAreaMeters2", 0.0)), 1),
        annual_kwh_estimate=round(float(annual_kwh), 0),
        sunshine_hours_per_year=round(float(sp.get("maxSunshineHoursPerYear", 0.0)), 0),
        best_pitch_deg=round(float(best_pitch), 1),
        best_azimuth_deg=round(float(best_azimuth), 1),
        roof_area_m2=round(float(roof_area), 1),
        is_heritage=False,  # populated below
        imagery_date=imagery_date,
        coverage_available=True,
    )


def _check_heritage(prop_id: Optional[str]) -> bool:
    if not prop_id:
        return False
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM regulatory_provisions "
                    "WHERE v2_topic = 'Heritage' AND v2_structural_category != 'structural' LIMIT 1"
                )
                return cur.fetchone()[0] > 0
    except Exception as e:
        logger.warning(f"Heritage flag lookup failed: {e}")
        return False


@router.post("/solar-yield")
async def run_solar_yield(request: SolarYieldRequest):
    logger.info(f"Solar yield: {request.address} ({request.lat}, {request.lng})")

    try:
        raw = _query_google_solar(request.lat, request.lng)
    except Exception as e:
        logger.exception(f"Google Solar API failed: {e}")
        raise HTTPException(status_code=502, detail=f"Google Solar API error: {e}")

    outputs = _parse_solar_response(raw)
    outputs.is_heritage = _check_heritage(request.prop_id)

    confidence = "high" if outputs.coverage_available else "low"

    _write_report(
        report_id=request.report_id,
        address=request.address,
        lat=request.lat,
        lng=request.lng,
        prop_id=request.prop_id,
        inputs={"lat": request.lat, "lng": request.lng},
        outputs=outputs.model_dump(),
        confidence=confidence,
    )

    logger.info(
        f"Solar yield complete: {request.report_id} — "
        f"{outputs.annual_kwh_estimate:.0f} kWh/yr potential, {outputs.max_panels} max panels"
    )
    return {
        "status": "complete",
        "report_id": request.report_id,
        "outputs": outputs.model_dump(),
        "confidence": confidence,
        "data_sources": DATA_SOURCES,
    }
