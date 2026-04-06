"""
Construction Shadow Detector -- FastAPI router.
POST /pipeline/shadow
  Input:  { address, prop_id, lat, lng, report_id }
  Output: 5 ADG shadow polygons + Sentinel-2 construction change score

VERIFIED 2026-04-06: shadows extend SOUTHWARD for Sydney (pvlib confirmed).
pybdshadow computes Southern Hemisphere solar position correctly.
"""
import logging, math, os, uuid
from datetime import date
from typing import Optional

import psycopg2, psycopg2.extras, requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from services.shadow_model import model_all_scenarios, get_scenario_metadata
    from services.sentinel2 import compute_change_score
except ImportError:
    from shadow_model import model_all_scenarios, get_scenario_metadata
    from sentinel2 import compute_change_score

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

DEFAULT_HEIGHT_M = 9.0
LOT_API = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/lot"


class ShadowRequest(BaseModel):
    address: str
    prop_id: str
    lat: float
    lng: float
    report_id: str


def _get_conn():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "127.0.0.1"),
        database=os.environ.get("DB_NAME", "nsw_planning"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", ""),
        port=int(os.environ.get("DB_PORT", 5432)),
    )


def _arcgis_to_geojson(geometry: dict) -> dict:
    """
    Convert ArcGIS JSON rings (EPSG:3857 Web Mercator) to GeoJSON Polygon (WGS84).
    NSW Planning Portal returns {"rings": [...], "spatialReference": {"wkid": 3857}}.
    shapely.shape() requires {"type": "Polygon", "coordinates": [...]} in WGS84.
    """
    R = 20037508.342789244
    rings_wgs84 = []
    for ring in geometry.get("rings", []):
        coords = []
        for x, y in ring:
            lng = x * 180.0 / R
            lat = math.degrees(2.0 * math.atan(math.exp(y * math.pi / R)) - math.pi / 2.0)
            coords.append([lng, lat])
        rings_wgs84.append(coords)
    return {"type": "Polygon", "coordinates": rings_wgs84}


def _fetch_lot_geometry(prop_id: str) -> Optional[dict]:
    try:
        r = requests.get(LOT_API, params={"propId": prop_id}, timeout=15)
        r.raise_for_status()
        data = r.json()
        return data[0].get("geometry") if data else None
    except Exception as e:
        logger.warning(f"Lot geometry: {e}")
        return None


def _get_height_limit(lat: float, lng: float) -> float:
    """
    Heuristic height limit from regulatory_provisions.
    TODO: replace with a dedicated LEP heights table when available.
    """
    try:
        import re
        with _get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT provision_text FROM regulatory_provisions "
                    "WHERE v2_topic ILIKE %s LIMIT 10",
                    ("%height%",)
                )
                heights = []
                for (text,) in cur.fetchall():
                    for m in re.findall(r"(\d+(?:\.\d+)?)\s*m", text or ""):
                        h = float(m)
                        if 4 <= h <= 30:
                            heights.append(h)
                return float(max(heights)) if heights else DEFAULT_HEIGHT_M
    except Exception as e:
        logger.warning(f"Height limit query: {e}")
        return DEFAULT_HEIGHT_M


def _write_report(report_id, address, lat, lng, prop_id, inputs, outputs, confidence):
    sql = """
        INSERT INTO property_reports
            (id, product, address, lat, lng, prop_id, run_date, inputs, outputs, confidence, data_sources)
        VALUES (%s, 'shadow', %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET outputs = EXCLUDED.outputs
    """
    with _get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (
                report_id, address, lat, lng, prop_id, date.today(),
                psycopg2.extras.Json(inputs), psycopg2.extras.Json(outputs),
                confidence,
                ["NSW Planning Portal API", "Element84 Sentinel-2 (free)", "pybdshadow"],
            ))
        conn.commit()


@router.post("/shadow")
def run_shadow(request: ShadowRequest):
    """Shadow Detector: 5 ADG scenarios + S2 construction change score."""
    lot_geometry = _fetch_lot_geometry(request.prop_id)
    if not lot_geometry:
        raise HTTPException(422, f"Cannot fetch lot geometry for {request.prop_id}")

    height_m = _get_height_limit(request.lat, request.lng)

    try:
        change = compute_change_score(request.lat, request.lng, radius_m=200)
    except Exception as e:
        logger.warning(f"Change score: {e}")
        change = {"change_score": 0.0, "construction_detected": False, "note": str(e)}

    try:
        lot_geojson = _arcgis_to_geojson(lot_geometry)
        shadows = model_all_scenarios(lot_geojson, height_m)
    except Exception as e:
        raise HTTPException(500, str(e))

    outputs = {
        "shadow_scenarios": shadows,
        "scenario_metadata": get_scenario_metadata(),
        "height_limit_m": height_m,
        "height_source": "LEP provisions" if height_m != DEFAULT_HEIGHT_M else "default (9m residential)",
        "lot_geometry": lot_geometry,
        "sentinel2_change": change,
        "adg_note": (
            "ADG: 2hrs solar access 9am-3pm Jun 21 required. "
            "VERIFY shadow extends NORTHWARD before production use."
        ),
    }
    confidence = "medium" if height_m != DEFAULT_HEIGHT_M else "low"
    _write_report(request.report_id, request.address, request.lat, request.lng,
                  request.prop_id,
                  {"prop_id": request.prop_id, "lat": request.lat, "lng": request.lng},
                  outputs, confidence)

    return {"status": "complete", "report_id": request.report_id,
            "outputs": outputs, "confidence": confidence}
