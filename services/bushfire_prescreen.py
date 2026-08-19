"""
NSW Bushfire Pre-Screen Pipeline -- FastAPI router.

POST /pipeline/bushfire  -- on-demand: RFS BFPL + PostGIS cross-overlays

Data sources:
  NSW RFS Bush Fire Prone Land Map   (ArcGIS REST, free, no auth)
  PostGIS spatial_overlays           (flood, heritage, zone cross-overlays)

Response contract (must match frontend BushfireResult):
{
  "address": str,
  "lat": float,
  "lng": float,
  "run_date": str,
  "outputs": {
    "is_bushfire_prone": bool | null,
    "designation_source": str | null,
    "designation_category": str | null,
    "designation_guideline": str | null,
    "estimated_bal_band": str | null,
    "bal_assessment_likely_required": bool | null,
    "bal_formal_assessment_cost_range": str | null,
    "bal_assessor_directory_url": str | null,
    "fire_signal": "none" | "low" | "moderate" | "elevated" | "unavailable",
    "compliance": {
      "state_legislation": str | null,
      "rfs_referral_required": bool | null,   # null on prone land = depends on the proposal (see triggers/note)
      "rfs_referral_note": str | null,        # conditional wording rendered alongside the triggers
      "rfs_referral_triggers": list[str] | null,  # always populated when bushfire prone
      "cdc_pathway_available": bool | null,
      "clearing_10_50_entitled": bool | null,  # null on prone land = depends on the RFS 10/50 entitlement area map
      "clearing_10_50_exceptions": str | null,
      "cross_overlays": list[dict] | null,
      "estimated_consultant_costs": str | null,
      "zone": str | null,
      "compliance_depth": str,
      "legislation_url": str | null
    },
    "data_currency": str
  },
  "confidence": "high" | "medium" | "low",
  "data_sources": list[str]
}
"""
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from typing import Optional

import psycopg2
import psycopg2.extras
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from audit_trail import DataSourceQuery, log_audit_trail, get_current_disclaimer_version

# prior-art-checked: reuses the shared item-4 module the other four satellite
# products already write through (services/execution_manifest.py, #876). This
# pipeline was simply never wired to it — the ratchet in
# scripts/check_satellite_manifests.py counted 0 of 65 bushfire reports
# carrying one, and the count rose by 4 between 2026-08-17 and 08-19 because
# new reports kept being written without provenance.
try:
    from services.execution_manifest import MANIFEST_KEY, build_manifest
except ImportError:
    from execution_manifest import MANIFEST_KEY, build_manifest

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/pipeline", tags=["satellite"])

# NSW RFS Bush Fire Prone Land Map — ArcGIS REST API
# Layer 0: Bush Fire Prone Land categories (Vegetation Category 1/2/3, Vegetation Buffer)
RFS_BFPL_REST = (
    "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
    "Fire/BFPL/MapServer/0/query"
)

_DATA_SOURCE_RFS = "NSW Rural Fire Service Bush Fire Prone Land Map"
_DATA_SOURCE_SPATIAL = "PostGIS spatial_overlays"

#: Bump when the screening logic changes what a given input produces, so a
#: stored manifest names the code that actually made that report.
ALGORITHM_VERSION = "bushfire-rfs-prescreen-1.0"

# NSW bounding box (rough) — reject obviously out-of-state coordinates
_NSW_BBOX = {"min_lat": -37.6, "max_lat": -28.0, "min_lng": 140.9, "max_lng": 154.0}

# Default outputs shape — used to fill gaps in cached blobs written by older code versions
_DEFAULT_OUTPUTS: dict = {
    "is_bushfire_prone": None,
    "designation_source": None,
    "designation_category": None,
    "designation_guideline": None,
    "estimated_bal_band": None,
    "bal_assessment_likely_required": None,
    "bal_formal_assessment_cost_range": None,
    "bal_assessor_directory_url": None,
    "fire_signal": "unavailable",
    "compliance": {
        "state_legislation": None,
        "rfs_referral_required": None,
        "rfs_referral_note": None,
        "rfs_referral_triggers": None,
        "cdc_pathway_available": None,
        "clearing_10_50_entitled": None,
        "clearing_10_50_exceptions": None,
        "cross_overlays": None,
        "estimated_consultant_costs": None,
        "zone": None,
        "compliance_depth": "state-level",
        "legislation_url": None,
    },
    "data_currency": "unknown",
}

# BAL estimation from BFPL category (indicative only — formal BAL assessment required)
_BAL_LOOKUP = {
    "vegetation buffer":     ("BAL-12.5", True),
    "vegetation category 3": ("BAL-19", True),
    "vegetation category 2": ("BAL-29", True),
    "vegetation category 1": ("BAL-40 to BAL-FZ", True),
}

# Fire signal convergence from BFPL category
_FIRE_SIGNAL_MAP = {
    "vegetation buffer":     "low",
    "vegetation category 3": "low",
    "vegetation category 2": "moderate",
    "vegetation category 1": "elevated",
}

# s4.14 integrated development triggers — state-wide, not LGA-specific
# These determine when RFS referral is required
_S414_TRIGGERS = [
    "Subdivision of bushfire-prone land",
    "Development for special fire protection purpose (schools, hospitals, childcare, seniors housing)",
    "Residential infill development resulting in 3 or more lots",
]


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
# RFS BFPL overlay query
# ---------------------------------------------------------------------------

def _is_in_nsw(lat: float, lng: float) -> bool:
    """Rough bounding box check — rejects obviously out-of-state coordinates."""
    return (
        _NSW_BBOX["min_lat"] <= lat <= _NSW_BBOX["max_lat"]
        and _NSW_BBOX["min_lng"] <= lng <= _NSW_BBOX["max_lng"]
    )


def _query_rfs_bfpl(lat: float, lng: float) -> dict:
    """Query NSW RFS Bush Fire Prone Land Map via ArcGIS REST (Layer 0).

    Returns designation category, guideline, and BAL estimation.
    Empty features array = not bushfire prone (correct, not error).
    Out-of-NSW coordinates return null (unknown), not False (not prone).
    """
    if not _is_in_nsw(lat, lng):
        return {
            "is_bushfire_prone": None,
            "designation_source": None,
            "designation_category": None,
            "designation_guideline": None,
            "estimated_bal_band": None,
            "bal_assessment_likely_required": None,
            "fire_signal": "unavailable",
            "data_currency": "outside_nsw",
        }

    try:
        params = {
            "geometry": f"{lng},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "outFields": "d_Category,d_Guidelin",
            "returnGeometry": "false",
            "f": "json",
        }
        r = requests.get(RFS_BFPL_REST, params=params, timeout=20)
        r.raise_for_status()
        body = r.json()

        if "error" in body:
            raise ValueError(f"ArcGIS error: {body['error']}")

        feats = body.get("features") or []
        if not feats:
            return {
                "is_bushfire_prone": False,
                "designation_source": None,
                "designation_category": None,
                "designation_guideline": None,
                "estimated_bal_band": "BAL-LOW",
                "bal_assessment_likely_required": False,
                "fire_signal": "none",
                "data_currency": date.today().isoformat(),
            }

        # When a lot straddles multiple BFPL categories, use the highest-risk
        # category.  Risk order: Category 1 > 2 > 3 > Buffer > unknown.
        _RISK_ORDER = {
            "vegetation category 1": 4,
            "vegetation category 2": 3,
            "vegetation category 3": 2,
            "vegetation buffer": 1,
        }
        best_feat = max(
            feats,
            key=lambda f: _RISK_ORDER.get(
                ((f.get("attributes") or {}).get("d_Category") or "").strip().lower(), 0
            ),
        )

        attrs = best_feat.get("attributes") or {}
        raw_category = (attrs.get("d_Category") or "").strip()
        raw_guideline = (attrs.get("d_Guidelin") or "").strip()
        category_lower = raw_category.lower()

        bal_band, bal_required = _BAL_LOOKUP.get(
            category_lower, ("BAL-12.5", True)
        )
        fire_signal = _FIRE_SIGNAL_MAP.get(category_lower, "low")

        return {
            "is_bushfire_prone": True,
            "designation_source": _DATA_SOURCE_RFS,
            "designation_category": raw_category or None,
            "designation_guideline": raw_guideline or None,
            "estimated_bal_band": bal_band,
            "bal_assessment_likely_required": bal_required,
            "fire_signal": fire_signal,
            "data_currency": date.today().isoformat(),
        }
    except Exception as e:
        logger.warning(f"RFS BFPL query: {e}")
        return {
            "is_bushfire_prone": None,
            "designation_source": None,
            "designation_category": None,
            "designation_guideline": None,
            "estimated_bal_band": None,
            "bal_assessment_likely_required": None,
            "fire_signal": "unavailable",
            "data_currency": "query_failed",
        }


# ---------------------------------------------------------------------------
# PostGIS cross-overlay queries
# ---------------------------------------------------------------------------

def _query_flood_overlay(lat: float, lng: float) -> Optional[dict]:
    """Query spatial_overlays for flood layers at this point."""
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT value, layer_type FROM spatial_overlays
                WHERE layer_type = 'flood'
                AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                LIMIT 1
                """,
                (lng, lat),
            )
            row = cur.fetchone()
        if row:
            return {"type": "flood", "value": row["value"], "source": "spatial_overlays"}
        return None
    except Exception as e:
        logger.warning(f"Flood overlay query: {e}")
        return None
    finally:
        if conn:
            conn.close()


def _query_heritage_overlay(lat: float, lng: float) -> Optional[dict]:
    """Query spatial_overlays for heritage layers at this point."""
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT value, layer_type FROM spatial_overlays
                WHERE layer_type = 'heritage'
                AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                LIMIT 1
                """,
                (lng, lat),
            )
            row = cur.fetchone()
        if row:
            return {"type": "heritage", "value": row["value"], "source": "spatial_overlays"}
        return None
    except Exception as e:
        logger.warning(f"Heritage overlay query: {e}")
        return None
    finally:
        if conn:
            conn.close()


def _query_zone_overlay(lat: float, lng: float) -> Optional[str]:
    """Query spatial_overlays for zone at this point."""
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT value FROM spatial_overlays
                WHERE layer_type = 'zone'
                AND ST_Intersects(geom, ST_SetSRID(ST_MakePoint(%s, %s), 4326))
                LIMIT 1
                """,
                (lng, lat),
            )
            row = cur.fetchone()
        if row:
            return row["value"]
        return None
    except Exception as e:
        logger.warning(f"Zone overlay query: {e}")
        return None
    finally:
        if conn:
            conn.close()


# ---------------------------------------------------------------------------
# Confidence + compliance helpers
# ---------------------------------------------------------------------------

def _compute_confidence(rfs_result: dict, cross_overlays: list, zone: Optional[str]) -> str:
    """
    high   — RFS BFPL + zone + at least one cross-overlay
    medium — RFS BFPL + (zone or cross-overlay)
    low    — RFS BFPL query failed or only partial data
    """
    rfs_ok = rfs_result.get("is_bushfire_prone") is not None
    has_zone = zone is not None
    has_overlays = len(cross_overlays) > 0

    if rfs_ok and has_zone and has_overlays:
        return "high"
    if rfs_ok and (has_zone or has_overlays):
        return "medium"
    if rfs_ok:
        return "medium"
    return "low"


def _build_compliance(
    rfs_result: dict,
    cross_overlays: list,
    zone: Optional[str],
) -> dict:
    """Build the compliance sub-object from RFS + overlay results."""
    is_prone = rfs_result.get("is_bushfire_prone")
    bal_band = rfs_result.get("estimated_bal_band")

    # RFS referral (s100B Rural Fires Act, via s4.14 EP&A Act context): a standard
    # dwelling DA on bush fire prone land is assessed by the COUNCIL against
    # Planning for Bush Fire Protection — formal RFS referral applies only to the
    # trigger developments (subdivision, Special Fire Protection Purpose). Without
    # a specific proposal the answer is unknown, so a prone lot carries None (three-
    # state) plus the trigger list and a conditional note — never a blanket True.
    rfs_referral_required = False if is_prone is False else None
    rfs_referral_note = (
        "Referral to the NSW Rural Fire Service applies only if the proposal "
        "matches a trigger below. Other development on bush fire prone land is "
        "assessed by the council against Planning for Bush Fire Protection."
        if is_prone else None
    )

    # CDC pathway: available if estimated BAL <= 29 for some dev types under Codes SEPP
    # BAL-40 or BAL-FZ -> DA pathway mandatory
    cdc_available = None
    if bal_band is not None:
        cdc_available = bal_band not in ("BAL-40 to BAL-FZ",)

    # 10/50 vegetation clearing: the entitlement follows the RFS 10/50 entitlement-
    # area map, not bare BFPL status — a prone lot is unknown (None) until checked
    # against that map, so the exceptions text carries the conditional wording.
    clearing_entitled = False if is_prone is False else None
    # Exceptions depend on what overlays actually intersect the property
    has_heritage = any(o.get("type") == "heritage" for o in cross_overlays)
    clearing_exceptions = None
    if is_prone:
        if has_heritage:
            clearing_exceptions = (
                "Whether the 10/50 vegetation clearing scheme applies here depends "
                "on the RFS 10/50 entitlement area map — check the address in the "
                "RFS online 10/50 tool. A heritage conservation area intersects "
                "this property, which can restrict 10/50 clearing — check with "
                "council before clearing. Entitlements do not apply within "
                "threatened species habitat or 40m of a waterway."
            )
        else:
            clearing_exceptions = (
                "Whether the 10/50 vegetation clearing scheme applies here depends "
                "on the RFS 10/50 entitlement area map — check the address in the "
                "RFS online 10/50 tool. Entitlements do not apply within "
                "threatened species habitat or 40m of a waterway."
            )

    return {
        "state_legislation": (
            "Environmental Planning and Assessment Act 1979 s4.14; "
            "Rural Fires Act 1997; Planning for Bush Fire Protection 2019"
            if is_prone else None
        ),
        "rfs_referral_required": rfs_referral_required,
        "rfs_referral_note": rfs_referral_note,
        "rfs_referral_triggers": _S414_TRIGGERS if is_prone else None,
        "cdc_pathway_available": cdc_available,
        "clearing_10_50_entitled": clearing_entitled,
        "clearing_10_50_exceptions": clearing_exceptions,
        "cross_overlays": cross_overlays if cross_overlays else None,
        "estimated_consultant_costs": (
            "$500-$2,000 (formal BAL assessment) + $2,000-$5,000 (bushfire report if required)"
            if rfs_result.get("bal_assessment_likely_required") else None
        ),
        "zone": zone,
        "compliance_depth": "state-level",
        "legislation_url": (
            "https://legislation.nsw.gov.au/view/html/inforce/current/act-1979-203/part-4/div-4.8/sec-4.14"
            if is_prone else None
        ),
    }


def build_live_manifest(rfs_result: dict, flood_overlay, heritage_overlay,
                        zone, lat: float, lng: float, prop_id) -> dict:
    """Manifest for a report whose sources were actually queried this run.

    Every identity is read from the dict the source query ITSELF returned —
    never re-fetched here. A parallel lookup would describe a different call
    than the one that produced the numbers, which is the exact failure the
    execution manifest exists to prevent.
    """
    return build_manifest(
        product="bushfire",
        algorithm_version=ALGORITHM_VERSION,
        inputs={
            "rfs_bfpl": {
                "endpoint": RFS_BFPL_REST,
                "designation_source": rfs_result.get("designation_source"),
                "designation_category": rfs_result.get("designation_category"),
                "designation_guideline": rfs_result.get("designation_guideline"),
                "data_currency": rfs_result.get("data_currency", "unknown"),
                "fire_signal": rfs_result.get("fire_signal", "unavailable"),
            },
            "spatial_overlays": {
                "source": _DATA_SOURCE_SPATIAL,
                "flood": (flood_overlay or {}).get("overlay_type"),
                "heritage": (heritage_overlay or {}).get("overlay_type"),
                "zone_code": (zone or {}).get("zone_code"),
            },
            "provenance": {
                "served_from": "live_query",
                "note": "RFS BFPL and the PostGIS overlays were queried for this report",
            },
        },
        query_params={"lat": lat, "lng": lng},
        parcel_identity={"prop_id": prop_id},
    )


def build_cache_manifest(cached: dict, lat: float, lng: float, prop_id) -> dict:
    """Manifest for a report served from an earlier run's stored outputs.

    A cache hit still writes a NEW report row, so it still needs a manifest —
    but it must not claim a query that never happened. What is honest is the
    copy: nothing was fetched, and these numbers were produced on an earlier
    date. Recording it as ``live_query`` would be false provenance, which is
    worse than no manifest because it reads as evidence.
    """
    run_date = (cached or {}).get("run_date")
    return build_manifest(
        product="bushfire",
        algorithm_version=ALGORITHM_VERSION,
        inputs={
            "provenance": {
                "served_from": "cache",
                "note": "No source was queried for this report. The outputs were "
                        "copied from the most recent valid stored bushfire report "
                        "for this address.",
                "source_run_date": (
                    run_date.isoformat() if hasattr(run_date, "isoformat") else run_date
                ),
                # NOT defaulted to the RFS source. A legacy row with a NULL
                # data_sources genuinely does not record what it queried, and
                # filling that gap with the likeliest answer would invent a
                # fact inside the one structure whose whole job is to record
                # what actually happened. Unknown is recorded as unknown.
                "source_data_sources": (cached or {}).get("data_sources") or None,
            },
        },
        query_params={"lat": lat, "lng": lng},
        parcel_identity={"prop_id": prop_id},
    )


def _build_data_sources(rfs_result: dict, cross_overlays: list) -> list:
    sources = [_DATA_SOURCE_RFS]
    if cross_overlays:
        sources.append(_DATA_SOURCE_SPATIAL)
    return sources


# ---------------------------------------------------------------------------
# DB write
# ---------------------------------------------------------------------------

# Sentinel key that every genuine bushfire outputs blob carries (present even
# when its value is None). Rows written before the #762 fix can hold flood or
# shadow outputs under product='bushfire' — the shared-report_id clobber —
# and serving one renders an all-null bushfire section with
# fire_signal='unavailable'. Any cached row missing this key is skipped.
_CACHE_SENTINEL_KEYS = ("is_bushfire_prone",)


def _first_valid_cached_row(rows):
    """Return the newest cached row whose outputs are bushfire-shaped.

    Defence in depth for issue #762: a row whose ``outputs`` lacks every
    sentinel key is poisoned (another product's outputs clobbered it) and is
    skipped, falling through to the next row or to live compute. Never serve
    a poisoned row.
    """
    for row in rows or []:
        outputs = row.get("outputs") if isinstance(row, dict) else None
        if isinstance(outputs, dict) and any(k in outputs for k in _CACHE_SENTINEL_KEYS):
            return row
    return None


def _write_report(report_id, address, lat, lng, prop_id, inputs, internal_outputs, confidence, data_sources):
    sql = """
        INSERT INTO property_reports
            (id, product, address, lat, lng, prop_id, run_date, inputs, outputs, confidence, data_sources)
        VALUES (%s, 'bushfire', %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
# Request model
# ---------------------------------------------------------------------------

class BushfireRequest(BaseModel):
    address: str
    prop_id: Optional[str] = None
    lat: float
    lng: float
    report_id: str
    lot_geometry: Optional[dict] = None


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/bushfire")
def run_bushfire(req: BushfireRequest):
    """
    On-demand bushfire pre-screen.
    Fast path: return pre-computed result if cached.
    Slow path: RFS BFPL (ArcGIS REST) + PostGIS cross-overlays (flood, heritage, zone).
    """
    # Cache check
    conn = None
    try:
        conn = _get_conn()
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                # run_date is selected so the cache manifest can name WHEN the
                # numbers it copies were actually produced. Without it the
                # manifest would say "from cache" and be unable to say how old.
                "SELECT outputs, confidence, data_sources, run_date FROM property_reports "
                "WHERE product='bushfire' AND address=%s ORDER BY run_date DESC LIMIT 5",
                (req.address,)
            )
            # #762 (prior-art-checked: same cache read being hardened in
            # place, no new source): newest row can be poisoned — another
            # product's outputs clobbered under product='bushfire' — so skip
            # rows missing the bushfire sentinel key instead of blindly
            # serving the newest.
            cached = _first_valid_cached_row(cur.fetchall())
        if cached:
            raw = cached["outputs"] or {}
            # Merge with defaults so cached blobs from older code versions still have all fields
            compliance_merged = {**_DEFAULT_OUTPUTS["compliance"], **(raw.get("compliance") or {})}
            merged = {**_DEFAULT_OUTPUTS, **raw, "compliance": compliance_merged}
            # A cached row is still a NEW report row, so it needs a manifest —
            # but it must not claim a live query that did not happen. What is
            # honest here is the copy itself: nothing was queried, and these
            # numbers came from an earlier run. Recording it as though it were
            # fresh would be the false-provenance failure the manifest exists
            # to prevent, and it is the likelier source of the four
            # unprovenanced rows added since 2026-08-17, because the cache path
            # runs whenever an address has been screened before.
            cache_manifest = build_cache_manifest(cached, req.lat, req.lng, req.prop_id)
            # Write a row for the new report_id so PDF generation can find it
            _write_report(
                req.report_id, req.address, req.lat, req.lng,
                req.prop_id,
                {"lat": req.lat, "lng": req.lng, MANIFEST_KEY: cache_manifest},
                raw, cached["confidence"],
                cached["data_sources"] or [_DATA_SOURCE_RFS],
            )
            log_audit_trail(
                report_id=req.report_id,
                pipeline_name="bushfire",
                input_params={"address": req.address, "lat": req.lat, "lng": req.lng},
                data_sources=[],
                output_summary=raw,
                disclaimer_version=get_current_disclaimer_version("bushfire"),
                intermediate_calculations={"cache_hit": True},
            )
            return {
                "address": req.address, "lat": req.lat, "lng": req.lng,
                "run_date": date.today().isoformat(),
                "outputs": merged,
                "confidence": cached["confidence"],
                "data_sources": cached["data_sources"] or [_DATA_SOURCE_RFS],
            }
    except Exception as e:
        logger.warning(f"Cache lookup: {e}")
    finally:
        if conn:
            conn.close()

    # Run queries in parallel (with audit trail tracking)
    ds_rfs = DataSourceQuery("NSW RFS BFPL", RFS_BFPL_REST, {"lat": req.lat, "lng": req.lng})
    ds_flood = DataSourceQuery("PostGIS flood overlay", "local:spatial_overlays", {"lat": req.lat, "lng": req.lng})
    ds_heritage = DataSourceQuery("PostGIS heritage overlay", "local:spatial_overlays", {"lat": req.lat, "lng": req.lng})

    with ThreadPoolExecutor(max_workers=3) as pool:
        f_rfs = pool.submit(_query_rfs_bfpl, req.lat, req.lng)
        f_flood = pool.submit(_query_flood_overlay, req.lat, req.lng)
        f_heritage = pool.submit(_query_heritage_overlay, req.lat, req.lng)

        rfs_result = f_rfs.result(timeout=15)
        flood_overlay = f_flood.result(timeout=15)
        heritage_overlay = f_heritage.result(timeout=15)

    ds_rfs.record_response(rfs_result, features_returned=1 if rfs_result.get("is_bushfire_prone") else 0)
    ds_flood.record_response(flood_overlay, features_returned=1 if flood_overlay else 0)
    ds_heritage.record_response(heritage_overlay, features_returned=1 if heritage_overlay else 0)

    # Zone query (separate — quick)
    zone = _query_zone_overlay(req.lat, req.lng)

    # Build cross-overlays list
    cross_overlays = []
    if flood_overlay:
        cross_overlays.append(flood_overlay)
    if heritage_overlay:
        cross_overlays.append(heritage_overlay)

    # Build compliance
    compliance = _build_compliance(rfs_result, cross_overlays, zone)

    # Build full outputs
    confidence = _compute_confidence(rfs_result, cross_overlays, zone)
    data_sources = _build_data_sources(rfs_result, cross_overlays)

    internal_outputs = {
        "is_bushfire_prone": rfs_result.get("is_bushfire_prone"),
        "designation_source": rfs_result.get("designation_source"),
        "designation_category": rfs_result.get("designation_category"),
        "designation_guideline": rfs_result.get("designation_guideline"),
        "estimated_bal_band": rfs_result.get("estimated_bal_band"),
        "bal_assessment_likely_required": rfs_result.get("bal_assessment_likely_required"),
        "bal_formal_assessment_cost_range": (
            "$500-$2,000" if rfs_result.get("bal_assessment_likely_required") else None
        ),
        "bal_assessor_directory_url": (
            "https://www.rfs.nsw.gov.au/plan-and-prepare/building-in-a-bush-fire-area/find-a-practitioner"
            if rfs_result.get("bal_assessment_likely_required") else None
        ),
        "fire_signal": rfs_result.get("fire_signal", "unavailable"),
        "compliance": compliance,
        "data_currency": rfs_result.get("data_currency", "unknown"),
    }

    # Execution manifest: every identity below is read from the dicts the
    # source queries THEMSELVES returned on this run — never a parallel lookup,
    # which is the anti-pattern the campaign's item 4 exists to prevent.
    manifest = build_live_manifest(
        rfs_result, flood_overlay, heritage_overlay, zone,
        req.lat, req.lng, req.prop_id,
    )

    # Write to DB
    inputs = {"lat": req.lat, "lng": req.lng, MANIFEST_KEY: manifest}
    if req.lot_geometry:
        inputs["lot_geometry"] = req.lot_geometry
    try:
        _write_report(
            req.report_id, req.address, req.lat, req.lng,
            req.prop_id, inputs,
            internal_outputs, confidence, data_sources,
        )
    except Exception as e:
        logger.error(f"Bushfire report DB write failed: {e}")
        raise HTTPException(status_code=503, detail="Failed to save report — please retry")

    # Audit trail (non-blocking — won't prevent report delivery on failure)
    ds_zone = DataSourceQuery("PostGIS zone overlay", "local:spatial_overlays", {"lat": req.lat, "lng": req.lng})
    ds_zone.record_response(zone, features_returned=1 if zone else 0)
    log_audit_trail(
        report_id=req.report_id,
        pipeline_name="bushfire",
        input_params=inputs,
        data_sources=[ds_rfs, ds_flood, ds_heritage, ds_zone],
        output_summary=internal_outputs,
        disclaimer_version=get_current_disclaimer_version("bushfire"),
        intermediate_calculations={
            "bal_band": internal_outputs.get("estimated_bal_band"),
            "fire_signal": internal_outputs.get("fire_signal"),
            "cross_overlays_count": len(cross_overlays),
        },
    )

    return {
        "address": req.address, "lat": req.lat, "lng": req.lng,
        "run_date": date.today().isoformat(),
        "outputs": internal_outputs,
        "confidence": confidence,
        "data_sources": data_sources,
    }
