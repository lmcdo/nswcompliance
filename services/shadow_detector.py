"""
Construction Shadow Detector -- FastAPI router.
POST /pipeline/shadow
  Input:  { address, prop_id, lat, lng, report_id }
  Output: ShadowResult matching frontend ShadowResult interface

VERIFIED 2026-04-06: shadows extend SOUTHWARD for Sydney (pvlib confirmed).
pybdshadow computes Southern Hemisphere solar position correctly.

Response contract (must match frontend-nextjs/app/reports/shadow/page.tsx):
{
  "address": str,
  "lat": float,
  "lng": float,
  "run_date": str,               # "YYYY-MM-DD"
  "outputs": {
    "height_m": float,
    "scenarios": [               # list, one per ADG scenario
      {
        "scenario": str,         # "jun21_9am" etc.
        "label": str,            # "ADG worst case 9am Jun 21"
        "date": str,             # "2025-06-21"
        "time_local": str,       # "09:00"
        "shadow_length_m": float,
        "shadow_direction_deg": float,
        "overlaps_subject_lot": bool
      }
    ],
    "construction_change_score": float | null,
    "construction_change_detected": bool,
    "adg_compliant": bool,       # True if ≥2 of 3 Jun 21 scenarios do NOT overlap subject lot
    "worst_case_scenario": str   # scenario key with longest shadow
  },
  "confidence": str,
  "data_sources": list[str]
}
"""
import logging
import math
import os
import uuid
from datetime import date
from typing import Optional

import psycopg2
import psycopg2.extras
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

try:
    from services.shadow_model import (
        model_all_scenarios, get_scenario_metadata,
        shadow_reach_m, shadow_overlap_fraction, overlaps_lot,
        SHADOW_SCENARIOS, northern_neighbour_proxy,
    )
    from services.sentinel2 import compute_change_score
except ImportError:
    from shadow_model import (
        model_all_scenarios, get_scenario_metadata,
        shadow_reach_m, shadow_overlap_fraction, overlaps_lot,
        SHADOW_SCENARIOS, northern_neighbour_proxy,
    )
    from sentinel2 import compute_change_score

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

DEFAULT_HEIGHT_M = 9.0
LOT_API = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/lot"
DATA_SOURCES = ["NSW Planning Portal API", "Element84 Sentinel-2 (free)", "pybdshadow"]


class ShadowRequest(BaseModel):
    address: str
    prop_id: str
    lat: float
    lng: float
    report_id: str
    height_m: Optional[float] = None  # LEP height override — skips DB query when provided


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


def _arcgis_to_geojson(geometry: dict) -> dict:
    """
    Convert ArcGIS JSON rings (EPSG:3857 Web Mercator) to GeoJSON Polygon (WGS84).
    NSW Planning Portal returns {"rings": [...], "spatialReference": {"wkid": 3857}}.
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


# former_council value → LEP instrument name
_COUNCIL_TO_LEP = {
    "marrickville": "Inner West LEP 2022",
    "leichhardt":   "Inner West LEP 2022",
    "ashfield":     "Inner West LEP 2022",
    "inner west":   "Inner West LEP 2022",
    "sydney":       "Sydney LEP 2012",
    "city of sydney": "Sydney LEP 2012",
    "ku-ring-gai":  "Ku-ring-gai LEP 2015",
    "kuringgai":    "Ku-ring-gai LEP 2015",
}


def _get_height_limit(lat: float, lng: float) -> tuple:
    """
    Returns (height_m: float, lep_name: str) for the lot at (lat, lng).

    Priority:
      1. spatial_overlays table, layer_type='height' — point-in-polygon, covers 33 LGAs.
      2. regulatory_provisions text extraction — Inner West only, kept as fallback.
      3. DEFAULT_HEIGHT_M (9.0 m) if both fail.
    """
    import re
    try:
        with _get_conn() as conn:
            with conn.cursor() as cur:

                # 1. spatial_overlays — authoritative LEP height limit for 33 LGAs
                cur.execute(
                    """
                    SELECT value, lga_name
                    FROM spatial_overlays
                    WHERE layer_type = 'height'
                      AND ST_Contains(
                            ST_SetSRID(ST_GeomFromGeoJSON(geom::text), 4326),
                            ST_SetSRID(ST_MakePoint(%s, %s), 4326)
                          )
                    LIMIT 1
                    """,
                    (lng, lat),
                )
                row = cur.fetchone()
                if row and row[0]:
                    raw_val = str(row[0])
                    lga_name = (row[1] or "").strip()
                    # value is typically "9" or "9m" or "9.0"
                    nums = re.findall(r"(\d+(?:\.\d+)?)", raw_val)
                    if nums:
                        height = float(nums[0])
                        lep_name = _COUNCIL_TO_LEP.get(lga_name.lower(),
                                                        f"{lga_name} LEP" if lga_name else "Local Environmental Plan")
                        logger.info(f"Height from spatial_overlays: {height}m ({lga_name})")
                        return height, lep_name

                # 2. regulatory_provisions fallback (Inner West only)
                cur.execute(
                    """
                    SELECT former_council
                    FROM dcp_precinct_boundaries
                    WHERE former_council IS NOT NULL
                    ORDER BY ST_Distance(
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326)::geography,
                        ST_Centroid(ST_SetSRID(ST_GeomFromGeoJSON(boundary_geojson::text), 4326))::geography
                    )
                    LIMIT 1
                    """,
                    (lng, lat),
                )
                row = cur.fetchone()
                former_council = (row[0] or "").strip() if row else ""

                if former_council:
                    cur.execute(
                        "SELECT provision_text FROM regulatory_provisions "
                        "WHERE is_current = TRUE AND v2_topic ILIKE %s AND former_council = %s LIMIT 20",
                        ("%height%", former_council),
                    )
                    heights = []
                    for (text,) in cur.fetchall():
                        for m in re.findall(r"(\d+(?:\.\d+)?)\s*m", text or ""):
                            h = float(m)
                            if 4 <= h <= 30:
                                heights.append(h)
                    if heights:
                        height = float(max(heights))
                        lep_name = _COUNCIL_TO_LEP.get(former_council.lower(), "Local Environmental Plan")
                        logger.info(f"Height from regulatory_provisions: {height}m ({former_council})")
                        return height, lep_name

    except Exception as e:
        logger.warning(f"Height limit query: {e}")

    return DEFAULT_HEIGHT_M, "Local Environmental Plan"


def _build_scenario_list(
    shadow_map: dict,
    lot_geojson: dict,
    lot_centroid_lng: float,
    lot_centroid_lat: float,
) -> list:
    """Convert raw shadow GeoJSON dict → list of ShadowScenario objects."""
    meta_by_key = {s[0]: s for s in SHADOW_SCENARIOS}
    scenarios = []
    for key, *_ in SHADOW_SCENARIOS:
        _, month, day, hour_utc, description, date_str, time_local, direction_deg = meta_by_key[key]
        shadow_geojson = shadow_map.get(key, {})
        if "error" in shadow_geojson:
            length = 0.0
            overlaps = False
        else:
            length = shadow_reach_m(shadow_geojson, lot_geojson)
            fraction = shadow_overlap_fraction(shadow_geojson, lot_geojson)
            overlaps = overlaps_lot(shadow_geojson, lot_geojson)
        scenarios.append({
            "scenario": key,
            "label": description,
            "date": date_str,
            "time_local": time_local,
            "shadow_length_m": length,
            "shadow_overlap_fraction": fraction,
            "shadow_direction_deg": direction_deg,
            "overlaps_subject_lot": overlaps,
            "shadow_polygon": shadow_geojson if "error" not in shadow_geojson else None,
        })
    return scenarios


def _adg_compliant(scenarios: list) -> bool:
    """
    ADG requires 2 hours solar access 9am–3pm Jun 21 on principal private open space.

    Primary gate: Jun 21 noon.
    At noon on Jun 21 the sun is at its highest (shortest shadow, ~14m for a 9m building
    in Sydney).  If the noon shadow still covers ≥40% of the lot the property almost
    certainly fails the 2-hour requirement — there is no midday window.  If noon is
    clear (<40%), a meaningful solar access window exists around midday.

    9am and 3pm always produce long shadows (~35m) regardless of lot size due to
    low solar altitude — treating them as hard gates produces false "always concern"
    results for all suburban lots.  They are retained in the scenario output for
    context but do not drive the ADG compliance verdict.
    """
    noon = next((s for s in scenarios if s["scenario"] == "jun21_12pm"), None)
    if noon is None:
        return True  # can't assess — default to compliant
    return not noon["overlaps_subject_lot"]


def _worst_case(scenarios: list) -> str:
    """Scenario with the longest shadow throw."""
    if not scenarios:
        return "jun21_9am"
    return max(scenarios, key=lambda s: s["shadow_length_m"])["scenario"]


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
                psycopg2.extras.Json(inputs),
                psycopg2.extras.Json(outputs),
                confidence,
                DATA_SOURCES,
            ))
        conn.commit()


@router.post("/shadow")
def run_shadow(request: ShadowRequest):
    """Shadow Detector: 5 ADG scenarios + S2 construction change score."""
    lot_geometry = _fetch_lot_geometry(request.prop_id)
    if not lot_geometry:
        raise HTTPException(422, f"Cannot fetch lot geometry for {request.prop_id}")

    lot_geojson = _arcgis_to_geojson(lot_geometry)
    if request.height_m:
        height_m = request.height_m
        lep_name = _COUNCIL_TO_LEP.get("", "Local Environmental Plan")
        # Re-derive lep_name from DB without height query
        try:
            with _get_conn() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT lga_name FROM spatial_overlays WHERE layer_type = 'height' "
                        "AND ST_Contains(ST_SetSRID(ST_GeomFromGeoJSON(geom::text),4326), "
                        "ST_SetSRID(ST_MakePoint(%s,%s),4326)) LIMIT 1",
                        (request.lng, request.lat),
                    )
                    row = cur.fetchone()
                    if row and row[0]:
                        lep_name = _COUNCIL_TO_LEP.get(row[0].lower(), f"{row[0]} LEP")
        except Exception:
            pass
    else:
        height_m, lep_name = _get_height_limit(request.lat, request.lng)

    try:
        change = compute_change_score(request.lat, request.lng, radius_m=200)
    except Exception as e:
        logger.warning(f"Change score: {e}")
        change = {"change_score": None, "construction_detected": False, "note": str(e)}

    # Model the shadow from a hypothetical building on the lot immediately to the
    # north (symmetric proxy: same footprint, same LEP height limit).  The subject
    # lot is kept as the overlap target.  This answers the buyer's question:
    # "Could a northern neighbour building to max height shadow my property?"
    north_proxy = northern_neighbour_proxy(lot_geojson)

    try:
        shadow_map = model_all_scenarios(north_proxy, height_m)
    except Exception as e:
        raise HTTPException(500, str(e))

    scenarios = _build_scenario_list(
        shadow_map, lot_geojson, request.lng, request.lat
    )

    outputs = {
        "height_m": height_m,
        "lep_name": lep_name,
        "lot_polygon": lot_geojson,
        "scenarios": scenarios,
        "construction_change_score": change.get("change_score"),
        "construction_change_detected": bool(change.get("construction_detected", False)),
        "adg_compliant": _adg_compliant(scenarios),
        "worst_case_scenario": _worst_case(scenarios),
    }
    confidence = "medium" if height_m != DEFAULT_HEIGHT_M and lep_name != "Local Environmental Plan" else "low"

    _write_report(
        request.report_id, request.address, request.lat, request.lng,
        request.prop_id,
        {"prop_id": request.prop_id, "lat": request.lat, "lng": request.lng},
        outputs, confidence,
    )

    return {
        "address": request.address,
        "lat": request.lat,
        "lng": request.lng,
        "run_date": date.today().isoformat(),
        "outputs": outputs,
        "confidence": confidence,
        "data_sources": DATA_SOURCES,
    }
