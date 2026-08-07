"""
Construction Shadow Detector -- FastAPI router.
POST /pipeline/shadow
  Input:  { address, prop_id, lat, lng, report_id }
  Output: ShadowResult matching frontend ShadowResult interface

Shadow polygons come from pybdshadow, which derives sun position internally
from the modelled UTC instant via `suncalc`. The bearing reported beside each
polygon comes from `services.solar_position`, which calls that same `suncalc`
function -- so the Direction column and the drawn shadow cannot disagree.

The "shadows extend SOUTHWARD for Sydney" claim, open as an unverified caveat
since April, IS now closed by tests/test_shadow_calibration.py, which asserts it
across latitude, season and hour against pvlib's independent NREL SPA
implementation. pvlib is a TEST dependency only and must never be named as our
method on any customer surface (PR #878, migration 064).

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
    "adg_compliant": bool|null,  # noon-only gate; null = NOT ASSESSED (noon scenario
                                 # missing/errored/overlap unknown) — never a verdict
    "worst_case_scenario": str   # scenario key with longest shadow
  },
  "confidence": str,
  "data_sources": list[str]
}
"""
import concurrent.futures
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

from audit_trail import DataSourceQuery, log_audit_trail, get_current_disclaimer_version
from services.lga_lookup import lookup_lga

# prior-art-checked: the added imports pull the NEW shared item-4 modules
# (execution_manifest, geometry_checks) into this service's existing import
# block — extending this file's own pipeline, not adding a parallel one.
try:
    from services.shadow_model import (
        model_all_scenarios, get_scenario_metadata,
        shadow_reach_m, shadow_overlap_fraction, overlaps_lot,
        shadow_on_lot_geojson, lot_depth_m,
        SHADOW_SCENARIOS, SCENARIO_YEAR, northern_neighbour_proxy,
        scenario_shadow_bearing_deg,
    )
    from services.solar_position import sun_position, max_shadow_length_m
    from services.execution_manifest import MANIFEST_KEY, build_manifest
    from services.geometry_checks import (
        check_point_nsw, check_polygon_wgs84, check_rings_epsg3857,
    )
except ImportError:
    from shadow_model import (
        model_all_scenarios, get_scenario_metadata,
        shadow_reach_m, shadow_overlap_fraction, overlaps_lot,
        shadow_on_lot_geojson, lot_depth_m,
        SHADOW_SCENARIOS, SCENARIO_YEAR, northern_neighbour_proxy,
        scenario_shadow_bearing_deg,
    )
    from solar_position import sun_position, max_shadow_length_m
    from execution_manifest import MANIFEST_KEY, build_manifest
    from geometry_checks import (
        check_point_nsw, check_polygon_wgs84, check_rings_epsg3857,
    )

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

DEFAULT_HEIGHT_M = 9.0
LOT_API = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/lot"
DATA_SOURCES = ["NSW Planning Portal API", "pybdshadow"]

# Algorithm revision for execution manifests (campaign item 4): the scenario
# set + proxy model + ADG overlap rule. Bump on method change, not per deploy.
# 2.0: per-address bearing, DST-derived instants, reach plausibility ceiling.
ALGORITHM_VERSION = "shadow-adg-scenarios-2.0"

# How far past the physical maximum h/tan(altitude) a reported reach may sit
# before it is treated as impossible rather than measured.
#
# CHOSEN FROM THE DATA, not picked for roundness. Across all 2,690 scenario-rows
# in the 538 stored reports (measured 2026-08-07) the ratio reach/ceiling is
# sharply bimodal: p50 0.732, p90 1.003, p95 1.004 — the legitimate mass sits AT
# the ceiling, because the proxy building's south edge coincides with the lot's
# north bound, so reach is geometrically capped at h/tan(A). Above that there is
# an empty band and then a jump to p99 = 13.5. Thresholds of 1.1, 1.25 and 1.5
# all select the SAME 19 reports (95, 95 and 93 rows), so the exact value is not
# load-bearing; 1.25 sits in the middle of the gap and leaves 25% headroom for
# the 111,000 m/deg flat-earth approximation and pybdshadow's aeqd round-trip.
REACH_CEILING_TOLERANCE = 1.25


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
    for ring in geometry.get("rings") or []:
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


def _get_lep_label(lga_name: str) -> str:
    """Return the LEP instrument label for a given LGA name.

    Query instrument_registry first (populated as legislation_monitor runs).
    Fall back to a title-cased display name so any NSW LGA gets a reasonable label.
    """
    if not lga_name:
        return "Local Environmental Plan"
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT instrument_label FROM instrument_registry
                WHERE instrument_type = 'lep'
                  AND council ILIKE %s
                  AND is_active = TRUE
                LIMIT 1
                """,
                (lga_name.strip(),),
            )
            row = cur.fetchone()
            if row:
                return row[0]
    except Exception:
        pass
    finally:
        if conn:
            conn.close()
    return f"{lga_name.title()} Local Environmental Plan"




def _get_height_limit(lat: float, lng: float) -> tuple:
    """
    Returns (height_m: float, lep_name: str, height_source: str) for the lot at (lat, lng).

    Priority:
      1. spatial_overlays table, layer_type='height' — point-in-polygon, covers 75 LGAs.
      2. regulatory_provisions text extraction — Inner West only, kept as fallback.
      3. DEFAULT_HEIGHT_M (9.0 m) if both fail.

    height_source values: "spatial_overlays" | "regulatory_provisions" | "default"
    """
    import re
    conn = None
    try:
        conn = _get_conn()
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
                    lep_name = _get_lep_label(lga_name)
                    logger.info(f"Height from spatial_overlays: {height}m ({lga_name})")
                    return height, lep_name, "spatial_overlays"

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
                        h = float(m if m else "0")
                        if 4 <= h <= 30:
                            heights.append(h)
                if heights:
                    height = float(max(heights))
                    lep_name = _get_lep_label(former_council)
                    # regulatory_provisions query uses is_current = TRUE (line above)
                    logger.info(f"Height from provisions: {height}m ({former_council})")
                    return height, lep_name, "regulatory_provisions"

    except Exception as e:
        logger.warning(f"Height limit query: {e}")
    finally:
        if conn:
            conn.close()

    return DEFAULT_HEIGHT_M, "Local Environmental Plan", "default"


def _build_scenario_list(
    shadow_map: dict,
    lot_geojson: dict,
    lot_centroid_lng: float,
    lot_centroid_lat: float,
    height_m: Optional[float] = None,
) -> list:
    """Convert raw shadow GeoJSON dict → list of ShadowScenario objects.

    `lot_centroid_lng/lat` were passed in but never read: the bearing served as
    `shadow_direction_deg` was one of five constants identical for every
    address. They are now used, which is the whole of the per-address compass
    fix. The bearing comes from the same `suncalc` call pybdshadow makes to cast
    the polygon, so the reported direction and the drawn shadow agree by
    construction.
    """
    meta_by_key = {s.key: s for s in SHADOW_SCENARIOS}
    scenarios = []
    for scenario in SHADOW_SCENARIOS:
        key = scenario.key
        meta = meta_by_key[key]
        description, date_str, time_local = meta.description, meta.date_str, meta.time_local
        # None when the bearing is not meaningful (sun below horizon, or so near
        # the zenith it is ill-conditioned). Never a fabricated fallback.
        direction_deg = scenario_shadow_bearing_deg(
            key, lot_centroid_lat, lot_centroid_lng)
        shadow_geojson = shadow_map.get(key) or {}
        if "error" in shadow_geojson or not shadow_geojson:
            # Typed absence (output-grounding fix 1, 2026-08-03). An errored
            # scenario previously served shadow_length_m=0.0 and
            # overlaps_subject_lot=False — a crash rendered as a numeric
            # "no shadow" claim, which then fed adg_compliant=True. A failed
            # computation is UNAVAILABLE: every measurement field is None and
            # the status says why the numbers are missing.
            scenarios.append({
                "scenario": key,
                "label": description,
                "date": date_str,
                "time_local": time_local,
                "status": "unavailable",
                "error_note": str(shadow_geojson.get("error") or "no shadow output")[:160],
                "shadow_length_m": None,
                "shadow_overlap_fraction": None,
                "shadow_direction_deg": direction_deg,
                "overlaps_subject_lot": None,
                "shadow_on_lot": None,
                "shadow_polygon": None,
            })
            continue

        reach_m = shadow_reach_m(shadow_geojson, lot_geojson)

        # PHYSICAL CEILING. A vertical object of height h at solar altitude A
        # cannot cast a shadow longer than h/tan(A); `shadow_reach_m` measures
        # from the lot's northern bound to the southernmost intersection, so an
        # oversized or multi-part lot polygon yields a reach no sun could
        # produce. 10 of 538 stored reports exceeded it — one served 1,779 m
        # from a 9 m building (42 Audley St Petersham, measured 2026-08-07).
        # An impossible number is UNAVAILABLE, not a measurement: the same
        # typed-absence rule the errored branch above already applies.
        ceiling_m = None
        ceiling_failure = None
        if height_m is not None:
            try:
                alt_deg, _ = sun_position(
                    scenario.instant_utc(), lot_centroid_lat, lot_centroid_lng)
                ceiling_m = max_shadow_length_m(height_m, alt_deg)
            except Exception as e:
                # FAIL CLOSED (Sol pre-push round). A swallowed exception here
                # silently disabled the guard: the 1,779 m reach this check
                # exists to block would have been served as status='computed'
                # whenever sun_position raised. An unvalidatable reach is
                # UNAVAILABLE, exactly like an unavailable polygon. Distinct
                # from max_shadow_length_m returning None (altitude <= 0):
                # there no finite ceiling physically exists and the skip is
                # legitimate; here we simply do not know it.
                ceiling_failure = str(e)[:120]

        if ceiling_failure is not None:
            logger.warning(
                "reach ceiling could not be computed for %s: %s — reporting "
                "unavailable", key, ceiling_failure)
            scenarios.append({
                "scenario": key,
                "label": description,
                "date": date_str,
                "time_local": time_local,
                "status": "unavailable",
                "error_note": (
                    f"shadow reach could not be validated against the physical "
                    f"ceiling ({ceiling_failure})"),
                "shadow_length_m": None,
                "shadow_overlap_fraction": None,
                "shadow_direction_deg": direction_deg,
                "overlaps_subject_lot": None,
                "shadow_on_lot": None,
                "shadow_polygon": None,
            })
            continue

        if reach_m is not None and ceiling_m is not None and reach_m > ceiling_m * REACH_CEILING_TOLERANCE:
            logger.warning(
                "shadow reach %.1f m exceeds the physical ceiling %.1f m for a "
                "%.1f m building at solar altitude %.2f deg (%s) — reporting "
                "unavailable", reach_m, ceiling_m, height_m, alt_deg, key)
            scenarios.append({
                "scenario": key,
                "label": description,
                "date": date_str,
                "time_local": time_local,
                "status": "unavailable",
                "error_note": (
                    f"computed reach {reach_m:.0f} m exceeds the {ceiling_m:.0f} m "
                    f"physical maximum for a {height_m:.0f} m building at this sun "
                    f"altitude — lot geometry implausible"),
                "shadow_length_m": None,
                "shadow_overlap_fraction": None,
                "shadow_direction_deg": direction_deg,
                "overlaps_subject_lot": None,
                "shadow_on_lot": None,
                "shadow_polygon": None,
            })
            continue

        overlap_fraction = shadow_overlap_fraction(shadow_geojson, lot_geojson)
        overlaps = overlaps_lot(shadow_geojson, lot_geojson)

        # A scenario is only 'computed' if its claim-bearing measurements were
        # actually measured. shadow_reach_m / shadow_overlap_fraction return
        # None when the GEOS intersection could not be evaluated at all — a
        # self-touching or unclosed cadastral ring raises TopologyException,
        # which used to be swallowed and served as 0.0. Serving None fields
        # under status='computed' would just move that lie one level down: the
        # PDF prints an em dash for a null reach, which reads as "no shadow".
        if reach_m is None or overlap_fraction is None:
            logger.warning(
                "scenario %s has no computable overlap/reach (lot geometry "
                "could not be intersected) — reporting unavailable", key)
            scenarios.append({
                "scenario": key,
                "label": description,
                "date": date_str,
                "time_local": time_local,
                "status": "unavailable",
                "error_note": ("the shadow could not be intersected with this "
                               "lot's boundary — no overlap was measured"),
                "shadow_length_m": None,
                "shadow_overlap_fraction": None,
                "shadow_direction_deg": direction_deg,
                "overlaps_subject_lot": None,
                "shadow_on_lot": None,
                "shadow_polygon": None,
            })
            continue

        scenarios.append({
            "scenario": key,
            "label": description,
            "date": date_str,
            "time_local": time_local,
            "status": "computed",
            "shadow_length_m": reach_m,
            "shadow_overlap_fraction": overlap_fraction,
            "shadow_direction_deg": direction_deg,
            "overlaps_subject_lot": overlaps,
            "shadow_on_lot": shadow_on_lot_geojson(shadow_geojson, lot_geojson),
            "shadow_polygon": shadow_geojson,
        })
    return scenarios


def _adg_compliant(scenarios: list) -> Optional[bool]:
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

    THREE-STATE (output-grounding fix 1, 2026-08-03): returns None — "not
    assessed" — when the noon scenario is missing, its computation errored
    (status "unavailable"), or its overlap is unknown. The previous code
    returned True on every one of those paths ("can't assess — default to
    compliant"): a crash became a compliance pass, the DQ-36 class. A verdict
    is only issued from a computed noon scenario.
    """
    noon = next((s for s in scenarios if s["scenario"] == "jun21_12pm"), None)
    if noon is None:
        return None  # not assessed — no noon scenario to gate on
    if noon.get("status") == "unavailable":
        return None  # not assessed — noon computation failed
    overlaps = noon.get("overlaps_subject_lot")
    if overlaps is None:
        return None  # not assessed — overlap unknown is not overlap absent
    return not bool(overlaps)


def _worst_case(scenarios: list) -> str:
    """Scenario with the longest shadow throw."""
    if not scenarios:
        return "jun21_9am"
    return max(scenarios, key=lambda s: s.get("shadow_length_m") or 0.0)["scenario"]


def _write_report(report_id, address, lat, lng, prop_id, inputs, outputs, confidence):
    sql = """
        INSERT INTO property_reports
            (id, product, address, lat, lng, prop_id, run_date, inputs, outputs, confidence, data_sources)
        VALUES (%s, 'shadow', %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO UPDATE SET outputs = EXCLUDED.outputs
    """
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor() as cur:
            cur.execute(sql, (
                report_id, address, lat, lng, prop_id, date.today(),
                psycopg2.extras.Json(inputs),
                psycopg2.extras.Json(outputs),
                confidence,
                DATA_SOURCES,
            ))
        conn.commit()
    finally:
        if conn:
            conn.close()


@router.post("/shadow")
def run_shadow(request: ShadowRequest):
    """Shadow Detector: the 5 ADG solar-access scenarios."""
    # Units/CRS entry check (campaign item 4): a swapped or projected
    # coordinate reproduces identically on every recompute — this is the only
    # defence. Failure is typed unavailable (422 with the reason), never a
    # number computed from wrong-CRS input.
    coord_reason = check_point_nsw(request.lat, request.lng)
    if coord_reason:
        raise HTTPException(
            422, f"Shadow analysis could not be determined: {coord_reason}")

    # Civil-time supportability. Every scenario wall-clock label is resolved
    # in Australia/Sydney (services/solar_position.py NSW_TZ), but Lord Howe
    # Island keeps its own IANA zone (Australia/Lord_Howe: +10:30 outside
    # daylight saving), so a winter scenario there would be modelled 30
    # minutes early while displaying the Sydney label. Refusing east of
    # longitude 154.0 states a geographic fact, not an approximated civil
    # boundary: the NSW mainland ends at Cape Byron (153.64 E), so the only
    # land the accepted envelope admits past 154.0 is the Lord Howe group.
    # (The far-west Broken Hill zone has no such clean line — towns on both
    # civil times sit in the same longitude band — so it stays a documented
    # limitation in solar_position.py.) Exposure of this refusal, measured
    # 2026-08-07: 0 of 538 stored shadow reports lie east of 154.0
    # (easternmost 153.61).
    if request.lng > 154.0:
        raise HTTPException(
            422, "Shadow analysis could not be determined: this location is "
                 "in the Lord Howe Island region, which keeps a different "
                 "civil time from the rest of NSW. Shadow scenarios are "
                 "modelled in NSW mainland time only, so this address is "
                 "refused rather than modelled with mislabelled times.")

    # Audit trail: track lot geometry fetch
    ds_lot = DataSourceQuery("NSW Planning Portal lot API", LOT_API, {"propId": request.prop_id})
    lot_geometry = _fetch_lot_geometry(request.prop_id)
    if not lot_geometry:
        ds_lot.record_error("No geometry returned")
        raise HTTPException(422, f"Cannot fetch lot geometry for {request.prop_id}")
    ds_lot.record_response(lot_geometry, features_returned=1)

    # _arcgis_to_geojson ASSUMES EPSG:3857 — verify the response actually
    # says so before converting (it never checked; a CRS change upstream
    # would silently produce garbage coordinates).
    sr = (lot_geometry.get("spatialReference") or {})
    lot_wkid = sr.get("latestWkid") or sr.get("wkid")
    if lot_wkid is not None and lot_wkid not in (3857, 102100):
        ds_lot.record_error(f"unexpected lot CRS wkid={lot_wkid}")
        raise HTTPException(
            422, f"Shadow analysis could not be determined: lot geometry "
                 f"arrived in CRS wkid={lot_wkid}, expected Web Mercator")
    rings_reason = check_rings_epsg3857(lot_geometry.get("rings"))
    if rings_reason:
        ds_lot.record_error(f"implausible lot rings: {rings_reason}")
        raise HTTPException(
            422, f"Shadow analysis could not be determined: {rings_reason}")

    lot_geojson = _arcgis_to_geojson(lot_geometry)
    polygon_reason = check_polygon_wgs84(lot_geojson)
    if polygon_reason:
        raise HTTPException(
            422, f"Shadow analysis could not be determined: converted lot "
                 f"polygon failed plausibility — {polygon_reason}")
    if request.height_m:
        height_m = request.height_m
        height_source = "planning_portal"
        lep_name = "Local Environmental Plan"
        # Re-derive lep_name from DB without height query
        _lep_conn = None
        try:
            _lep_conn = _get_conn()
            with _lep_conn.cursor() as cur:
                cur.execute(
                    "SELECT lga_name FROM spatial_overlays WHERE layer_type = 'height' "
                    "AND ST_Contains(ST_SetSRID(ST_GeomFromGeoJSON(geom::text),4326), "
                    "ST_SetSRID(ST_MakePoint(%s,%s),4326)) LIMIT 1",
                    (request.lng, request.lat),
                )
                row = cur.fetchone()
                if row and row[0]:
                    lep_name = _get_lep_label(row[0])
        except Exception:
            pass
        finally:
            if _lep_conn:
                _lep_conn.close()
    else:
        height_m, lep_name, height_source = _get_height_limit(request.lat, request.lng)

    # Proxy building: max-height structure at the north lot boundary.
    # Models worst-case shadow — the closest a neighbour could build.
    # Road width is not accounted for: roads reduce real-world impact but
    # are not reflected here, keeping the model conservative.
    north_proxy = northern_neighbour_proxy(lot_geojson)

    # Audit trail: track the shadow model actually invoked. pvlib was named
    # here for 381 audit rows while never being imported anywhere in the repo
    # (Lane 1 / D1) — pybdshadow derives sun position itself.
    ds_shadow = DataSourceQuery(
        "pybdshadow shadow casting",
        "local:model_all_scenarios",
        {"height_m": height_m, "scenarios": len(SHADOW_SCENARIOS)},
    )
    try:
        shadow_map = model_all_scenarios(north_proxy, height_m)
        ds_shadow.record_response(
            {"scenarios_computed": len(shadow_map)},
            features_returned=len(shadow_map),
        )
    except Exception as e:
        ds_shadow.record_error(str(e))
        raise HTTPException(500, str(e))

    scenarios = _build_scenario_list(
        shadow_map, lot_geojson, request.lng, request.lat, height_m
    )

    # Resolve LGA for council name on report
    lga_info = {"lga_name": None, "lga_slug": None}
    _lga_conn = None
    try:
        _lga_conn = _get_conn()
        lga_info = lookup_lga(request.lat, request.lng, _lga_conn)
    except Exception:
        pass
    finally:
        if _lga_conn:
            _lga_conn.close()

    outputs = {
        "height_m": height_m,
        "height_source": height_source,
        "lep_name": lep_name,
        "lga_name": lga_info.get("lga_name"),
        "lga_slug": lga_info.get("lga_slug"),
        "lot_polygon": lot_geojson,
        "north_proxy_polygon": north_proxy,
        "scenarios": scenarios,
        "adg_compliant": _adg_compliant(scenarios),
        "worst_case_scenario": _worst_case(scenarios),
    }
    confidence = "medium" if height_m != DEFAULT_HEIGHT_M and lep_name != "Local Environmental Plan" else "low"
    # A run with any unavailable scenario must not out-claim its own data:
    # cap to "low" (the conveyancing _cap_confidence doctrine; fix 1).
    if any(s.get("status") == "unavailable" for s in scenarios):
        confidence = "low"

    # Execution manifest (campaign item 4): every identity below comes from
    # the objects this run actually consumed — lot_wkid is the CRS the lot API
    # actually declared, height names the control that was found.
    manifest = build_manifest(
        product="shadow",
        algorithm_version=ALGORITHM_VERSION,
        inputs={
            "lot_geometry": {"api": LOT_API, "prop_id": request.prop_id,
                             "wkid": lot_wkid},
            "height": {"value_m": height_m, "source": height_source,
                       "lep_name": lep_name},
            "scenario_year": SCENARIO_YEAR,
        },
        query_params={"lat": request.lat, "lng": request.lng,
                      "s2_radius_m": 200},
        parcel_identity={"prop_id": request.prop_id},
    )

    try:
        _write_report(
            request.report_id, request.address, request.lat, request.lng,
            request.prop_id,
            {"prop_id": request.prop_id, "lat": request.lat,
             "lng": request.lng, MANIFEST_KEY: manifest},
            outputs, confidence,
        )
    except Exception as e:
        logger.error(f"Shadow report DB write failed: {e}")
        raise HTTPException(status_code=503, detail="Failed to save report — please retry")

    # Audit trail (non-blocking — won't prevent report delivery on failure).
    # Every height_source has its own provenance label — a default must never
    # be logged as a regulatory_provisions lookup (D1 audit-trail fix).
    _HEIGHT_SOURCE_URLS = {
        "spatial_overlays": "local:spatial_overlays",
        "regulatory_provisions": "local:regulatory_provisions",
        "planning_portal": "portal:layerintersect_height",
        "default": "default:DEFAULT_HEIGHT_M",
    }
    ds_height = DataSourceQuery(
        "LEP height limit lookup",
        _HEIGHT_SOURCE_URLS.get(height_source, f"unknown:{height_source}"),
        {"lat": request.lat, "lng": request.lng},
    )
    ds_height.record_response({"height_m": height_m, "source": height_source}, features_returned=1)

    log_audit_trail(
        report_id=request.report_id,
        pipeline_name="shadow",
        input_params={
            "address": request.address,
            "prop_id": request.prop_id,
            "lat": request.lat,
            "lng": request.lng,
            "height_m_override": request.height_m,
        },
        data_sources=[ds_lot, ds_height, ds_shadow],
        output_summary=outputs,
        disclaimer_version=get_current_disclaimer_version("shadow"),
        intermediate_calculations={
            "height_m": height_m,
            "height_source": height_source,
            "adg_compliant": outputs["adg_compliant"],
            "worst_case_scenario": outputs["worst_case_scenario"],
            "shadow_overlap_fractions": {
                s["scenario"]: s.get("shadow_overlap_fraction", 0.0)
                for s in scenarios
            },
        },
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
