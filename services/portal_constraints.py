"""
NSW Government portal constraint queries + empirical data fetchers.

Shared module — consumed by intelligence_brief.py and available for
compliance engine migration. Each function takes (lat, lng) and returns
a typed dict or None.

Most endpoints are public government ArcGIS REST services (no API keys).
NASA FIRMS requires NASA_FIRMS_MAP_KEY env var (free registration).
"""
import math
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

ARCGIS_TIMEOUT = 8  # seconds

# ---------------------------------------------------------------------------
# ePlanning layer registry — mirrors frontend EPLANNING_LAYERS
# ---------------------------------------------------------------------------

EPLANNING_BASE = (
    "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/ePlanning"
)

EPLANNING_LAYERS = {
    "lowMidRiseExclusion":    {"service": "Planning_Portal_SEPP",              "id": 776},
    "complyingExclusion":     {"service": "Planning_Portal_SEPP",              "id": 92},
    "exemptExclusion":        {"service": "Planning_Portal_SEPP",              "id": 93},
    "dualOccProhibition":     {"service": "Planning_Portal_Local_Provisions",  "id": 452},
    # Transport Oriented Development catchments (published government polygons —
    # authoritative point-in-polygon, no walking-distance computation needed).
    "todSites":               {"service": "Planning_Portal_SEPP",              "id": 752},
    "todAccelerated":         {"service": "Planning_Portal_SEPP",              "id": 759},
    # Town Centres Map — the LMR reforms' anchor polygons (LMR Amendment 2025).
    # These are the centre BOUNDARIES, not catchments: the s22 "low and mid rise
    # housing area" must be DERIVED as within 800 m of one (no inclusion layer
    # exists — layer list re-enumerated 2026-07-14).
    "townCentres":            {"service": "Planning_Portal_SEPP",              "id": 766},
}


# ---------------------------------------------------------------------------
# Low-level ArcGIS query helpers
# ---------------------------------------------------------------------------

def query_arcgis_point(
    url: str, lng: float, lat: float, out_fields: str = "*",
) -> list[dict]:
    """Query an ArcGIS REST service with a point geometry.

    Returns list of feature attribute dicts (empty list if no features).
    """
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": out_fields,
        "returnGeometry": "false",
        "f": "json",
        "inSR": "4283",
    }
    resp = requests.get(url, params=params, timeout=ARCGIS_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    features = data.get("features") or []
    return [(f.get("attributes") or {}) for f in features] if features else []


def query_arcgis_point_buffered(
    url: str, lng: float, lat: float, distance_m: int, out_fields: str = "*",
) -> list[dict]:
    """Query an ArcGIS REST service with a point + buffer distance.

    Returns list of feature dicts with geometry (empty list if no features).
    """
    params = {
        "geometry": f"{lng},{lat}",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "distance": str(distance_m),
        "units": "esriSRUnit_Meter",
        "outFields": out_fields,
        "returnGeometry": "true",
        "f": "json",
        "inSR": "4283",
        "orderByFields": "OBJECTID ASC",
    }
    resp = requests.get(url, params=params, timeout=ARCGIS_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    return data.get("features") or []


def _query_eplanning_point(
    layer_key: str, lng: float, lat: float, out_fields: str = "LAY_CLASS",
) -> list[dict]:
    """Query an ePlanning layer by key. Returns feature attribute dicts."""
    layer = EPLANNING_LAYERS[layer_key]
    url = f"{EPLANNING_BASE}/{layer['service']}/MapServer/{layer['id']}/query"
    return query_arcgis_point(url, lng, lat, out_fields=out_fields)


# ---------------------------------------------------------------------------
# Constraint fetchers — each returns a typed dict or None
# ---------------------------------------------------------------------------

def fetch_mine_subsidence(lat: float, lng: float) -> Optional[dict]:
    """NSW Mine Subsidence districts — FeatureServer/7 on portal.spatial.nsw.gov.au.

    Returns {"in_district": True, "district_name": str, "last_update": str} or None.
    """
    url = (
        "https://portal.spatial.nsw.gov.au/server/rest/services/"
        "NSW_Administrative_Boundaries_Theme/FeatureServer/7/query"
    )
    # This endpoint uses wkid 4326, not 4283 — matches TypeScript implementation
    params = {
        "f": "json",
        "geometry": f'{{"x":{lng},"y":{lat},"spatialReference":{{"wkid":4326}}}}',
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "districtname,lastupdate",
        "returnGeometry": "false",
    }
    resp = requests.get(url, params=params, timeout=ARCGIS_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()
    features = data.get("features") or []
    if not features:
        return None
    attrs = features[0].get("attributes", {})
    return {
        "in_district": True,
        "district_name": attrs.get("districtname"),
        "last_update": attrs.get("lastupdate"),
    }


def fetch_contaminated_land(lat: float, lng: float) -> Optional[dict]:
    """EPA contaminated land notified sites within 500m.

    Returns {"has_notified_sites": True, "site_count": int, "nearest_site": {...}} or None.
    """
    url = (
        "https://mapprod2.environment.nsw.gov.au/arcgis/rest/services/"
        "EPA/Contaminated_land_notified_sites/MapServer/0/query"
    )
    features = query_arcgis_point_buffered(
        url, lng, lat, distance_m=500,
        out_fields="SiteName,SiteStreet,Suburb,ManagementClass,ContaminationActivityType",
    )
    if not features:
        return None
    site = features[0]
    attrs = site.get("attributes") or {}
    geom = site.get("geometry") or {}
    distance_m = None
    if geom and "x" in geom and "y" in geom:
        dx = (geom["x"] - lng) * 111320 * math.cos(lat * math.pi / 180)
        dy = (geom["y"] - lat) * 110540
        distance_m = round(math.sqrt(dx * dx + dy * dy))
    return {
        "has_notified_sites": True,
        "site_count": len(features),
        "nearest_site": {
            "name": attrs.get("SiteName"),
            "street": attrs.get("SiteStreet"),
            "suburb": attrs.get("Suburb"),
            "management_class": attrs.get("ManagementClass"),
            "activity_type": attrs.get("ContaminationActivityType"),
            "distance_m": distance_m,
        },
    }


def fetch_drinking_water_catchment(lat: float, lng: float) -> Optional[dict]:
    """Drinking water catchment area — Protection/MapServer/3.

    Returns {"in_catchment": True, "epi_name": str, "lga_name": str} or None.
    """
    url = (
        "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
        "Planning/Protection/MapServer/3/query"
    )
    results = query_arcgis_point(url, lng, lat, out_fields="EPI_NAME,LGA_NAME")
    if not results:
        return None
    attrs = results[0]
    return {
        "in_catchment": True,
        "epi_name": attrs.get("EPI_NAME"),
        "lga_name": attrs.get("LGA_NAME"),
    }


def fetch_anef(lat: float, lng: float) -> Optional[dict]:
    """Aircraft Noise Exposure Forecast — Protection/MapServer/2.

    Returns {"in_anef_zone": True, "anef_level": int, "anef_code": str, ...} or None.
    """
    url = (
        "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
        "Planning/Protection/MapServer/2/query"
    )
    results = query_arcgis_point(url, lng, lat, out_fields="ANEF_CODE,EPI_NAME,LGA_NAME")
    if not results:
        return None
    attrs = results[0]
    anef_code = attrs.get("ANEF_CODE") or ""
    anef_level = None
    if ">" in anef_code:
        anef_level = 40
    elif "-" in anef_code:
        parts = anef_code.split("-")
        try:
            anef_level = int(parts[0])
        except (ValueError, IndexError):
            pass
    else:
        try:
            anef_level = int(anef_code) if anef_code else None
        except ValueError:
            pass
    return {
        "in_anef_zone": True,
        "anef_level": anef_level,
        "anef_code": anef_code,
        "epi_name": attrs.get("EPI_NAME"),
        "lga_name": attrs.get("LGA_NAME"),
    }


# prior-art-checked: LIFTED from intelligence_brief.fetch_anef_zone (not a fork —
# that function now delegates here) so the conveyancing PDF and the brief share
# ONE anef_zones implementation. Moved to this module because intelligence_brief
# imports fastapi (unavailable in the CLI report context) and already imports
# this module, so the reverse import would be circular.
def fetch_anef_zone_exact(lat: float, lng: float) -> Optional[dict]:
    """Sydney ANEF from the curated ``anef_zones`` table — the SAME source the
    verify app's /api/environmental/anef route uses. Exact point-in-polygon via
    PostGIS ST_Contains over the stored GeoJSON (bbox pre-filter for speed).

    Returns ``{"anef_level": int, "airport": str, "anef_version": str}`` or
    None when the point is in no stored contour. RAISES on DB unavailability
    or query failure — callers decide fail-open vs fail-closed.
    """
    import psycopg2
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise EnvironmentError("DATABASE_URL not set")
    conn = psycopg2.connect(db_url, options="-c statement_timeout=5000")
    try:
        conn.autocommit = True
        cur = conn.cursor()
        cur.execute(
            "SELECT anef_level, airport_name, anef_version FROM anef_zones "
            "WHERE bbox_min_lon <= %s AND bbox_max_lon >= %s "
            "AND bbox_min_lat <= %s AND bbox_max_lat >= %s "
            "AND ST_Contains("
            "  ST_SetSRID(ST_GeomFromGeoJSON(geometry_json::text), 4326), "
            "  ST_SetSRID(ST_MakePoint(%s, %s), 4326)) "
            "ORDER BY anef_level DESC LIMIT 1",
            (lng, lng, lat, lat, lng, lat),
        )
        row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        return None
    level, airport, version = row
    return {"anef_level": level, "airport": airport, "anef_version": version}


# prior-art-checked: no new source — this narrows resolve_anef_value to the
# EXISTING fetch_anef (same module, above) after measuring that the curated
# anef_zones geometries are too coarse for parcel-level value claims.
def resolve_anef_value(lat: float, lng: float) -> dict:
    """Resolve the ANEF contour value at a point — three-state, never silent.

    Queries the live ePlanning Protection ANEF layer ONLY (LEP/SEPP-mapped
    airport-noise contours: Bankstown/Liverpool, Upper Hunter, Western Sydney
    Airport precincts — 29 features, verified 2026-07-06). The curated
    ``anef_zones`` table (Sydney KSA) is deliberately NOT consulted here: its
    contours are 10-13-vertex digitisations whose ANEF-20 polygon covers
    ~789 km² (far beyond the published ANEF 2039 20-contour), so it cannot
    support parcel-level value claims in a legal document. Returns:

      {"status": "found", "anef_level": int | None, "anef_code": str | None,
       "epi_name": str | None, "source": "eplanning_protection_live"}
      {"status": "empty"}   -- the lookup ran; no mapped contour at this point
      {"status": "failed"}  -- the lookup errored; the value is unknown, not absent

    Callers must render "failed" as not-assessed wording, never as a clear/empty
    result (PR #674 bushfire-row precedent).
    """
    try:
        live = fetch_anef(lat, lng)
    except Exception:
        logger.warning("resolve_anef_value: live ePlanning ANEF query failed")
        return {"status": "failed"}
    if live and (live.get("anef_level") is not None or live.get("anef_code")):
        return {
            "status": "found",
            "anef_level": live.get("anef_level"),
            "anef_code": live.get("anef_code") or None,
            "epi_name": live.get("epi_name") or None,
            "source": "eplanning_protection_live",
        }
    return {"status": "empty"}


def fetch_protection_overlay(
    lat: float, lng: float, layer_id: int, value_field: str = "LAY_CLASS",
) -> Optional[dict]:
    """Live point-query a Planning/Protection overlay layer at one property.

    A per-lot fallback for when our ingested coverage is missing the layer, so we
    can report the real fact about THIS lot instead of an internal "not ingested"
    gap. Same service the ingest and other fetchers use — riparian = layer 7,
    wetlands = layer 11, biodiversity = layer 10.

    Returns:
      {"present": True, "value": <class>} — a feature intersects the point;
      {"present": False, "value": None}   — queried successfully, nothing intersects
                                            (a genuine "none here" for this lot);
      None                                — the query failed (caller falls back to a
                                            conservative "not assessed", never over-states).
    """
    url = (
        "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
        f"Planning/Protection/MapServer/{layer_id}/query"
    )
    try:
        results = query_arcgis_point(url, lng, lat, out_fields=value_field)
    except Exception:
        logger.warning("Protection overlay layer %s point query failed", layer_id)
        return None
    if not results:
        return {"present": False, "value": None}
    return {"present": True, "value": results[0].get(value_field)}


def fetch_bushfire_bfpl(lat: float, lng: float) -> Optional[dict]:
    """NSW RFS Bush Fire Prone Land Map — Fire/BFPL/MapServer/0.

    Returns {"category": str, "type": str} or None if not bushfire prone.
    """
    url = (
        "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
        "Fire/BFPL/MapServer/0/query"
    )
    results = query_arcgis_point(url, lng, lat)
    if not results:
        return None
    attrs = results[0]
    return {
        "category": attrs.get("Category") or attrs.get("TYPE"),
        "type": attrs.get("TYPE"),
    }


def fetch_coastal(lat: float, lng: float) -> Optional[dict]:
    """Coastal SEPP layers — Wetlands (1), Environment Area (6), Littoral Rainforests (3).

    Queries all 3 layers in parallel (matches frontend Promise.all pattern).
    Returns {"in_coastal_area": True, "zones": ["Coastal Wetlands", ...]} or None.
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    base = (
        "https://mapprod1.environment.nsw.gov.au/arcgis/rest/services/"
        "CoastalManagementSEPP/CoastalManagementSEPP/MapServer"
    )
    layers = [
        (1, "Coastal Wetlands"),
        (6, "Coastal Environment Area"),
        (3, "Littoral Rainforests"),
    ]

    def _check_layer(layer_id: int, zone_name: str) -> Optional[str]:
        url = f"{base}/{layer_id}/query"
        try:
            results = query_arcgis_point(url, lng, lat)
            return zone_name if results else None
        except Exception:
            logger.warning("Coastal layer %d query failed", layer_id)
            return None

    zones = []
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_check_layer, lid, zname): zname
            for lid, zname in layers
        }
        for fut in as_completed(futures):
            result = fut.result()
            if result:
                zones.append(result)
    if not zones:
        return None
    return {
        "in_coastal_area": True,
        "zones": sorted(zones),
    }


def fetch_sepp_exclusions(lat: float, lng: float) -> Optional[dict]:
    """SEPP exclusion gates — low/mid-rise (776), complying (92), exempt (93).

    Queries all 3 layers in parallel.
    Returns {"low_mid_rise": bool|None, "complying": bool|None, "exempt": bool|None}.
    Always returns a dict (None values mean query failed for that layer).
    """
    from concurrent.futures import ThreadPoolExecutor, as_completed

    layers = [
        ("lowMidRiseExclusion", "low_mid_rise"),
        ("complyingExclusion", "complying"),
        ("exemptExclusion", "exempt"),
    ]

    def _check_layer(key: str) -> Optional[bool]:
        try:
            features = _query_eplanning_point(key, lng, lat, out_fields="LAY_CLASS")
            return len(features) > 0
        except Exception:
            logger.warning("SEPP exclusion layer %s query failed", key)
            return None

    result = {}
    with ThreadPoolExecutor(max_workers=3) as pool:
        futures = {
            pool.submit(_check_layer, key): field_name
            for key, field_name in layers
        }
        for fut in as_completed(futures):
            field_name = futures[fut]
            result[field_name] = fut.result()

    # Only return None if all queries failed
    if all(v is None for v in result.values()):
        return None
    return result


def fetch_tod_catchment(lat: float, lng: float) -> Optional[dict]:
    """Transport Oriented Development catchment — published government polygons.

    Point-in-polygon against the TOD Sites (752) and Accelerated TOD Precincts (759)
    maps — authoritative, lot-specific, no walking-distance computation. A lot inside
    either is in a mid-rise (residential flat) catchment.

    Returns {"in_tod": bool, "epi_name": str|None, "lga_name": str|None} or None on
    total failure (both layer queries errored).
    """
    in_tod = False
    epi_name = None
    lga_name = None
    any_ok = False
    for key in ("todSites", "todAccelerated"):
        try:
            features = _query_eplanning_point(key, lng, lat, out_fields="EPI_NAME,LGA_NAME")
            any_ok = True
            if features:
                in_tod = True
                attrs = features[0]
                epi_name = epi_name or attrs.get("EPI_NAME")
                lga_name = lga_name or attrs.get("LGA_NAME")
        except Exception:
            logger.warning("TOD catchment layer %s query failed", key)
    if not any_ok:
        return None
    return {"in_tod": in_tod, "epi_name": epi_name, "lga_name": lga_name}


def fetch_town_centre_catchment(lat: float, lng: float, distance_m: int = 800) -> Optional[dict]:
    """Town Centres Map (766) within ``distance_m`` — the derived LMR-area anchor.

    prior-art-checked: reuses query_arcgis_point_buffered + EPLANNING_LAYERS; no
    existing fetcher touches layer 766 (only 752/759/776 are wired).

    SEPP (Housing) 2021 s22 defines the "low and mid rise housing area" via
    walking distance from nominated town centres / station precincts. No
    inclusion layer is published, so this approximates the test with a radial
    buffer from the 766 boundary polygons (radial ⊇ walking — slightly generous
    at the margin; the per-form standards still gate downstream).

    Returns {"within_catchment": bool, "label": str|None} or None on query
    failure (caller must treat None as NOT anchored — fail-closed).
    """
    layer = EPLANNING_LAYERS["townCentres"]
    url = f"{EPLANNING_BASE}/{layer['service']}/MapServer/{layer['id']}/query"
    try:
        feats = query_arcgis_point_buffered(
            url, lng, lat, distance_m, out_fields="LABEL,EPI_NAME",
        )
    except Exception:
        logger.warning("Town Centres layer (766) query failed")
        return None
    if not feats:
        return {"within_catchment": False, "label": None}
    attrs = feats[0].get("attributes") or {}
    return {"within_catchment": True, "label": attrs.get("LABEL")}


def fetch_dual_occ_prohibition(lat: float, lng: float) -> Optional[dict]:
    """Dual occupancy prohibition — ePlanning layer 452.

    Returns {"prohibited": True, "epi_name": str, "lga_name": str} or
    {"prohibited": False} if not in prohibition area, or None on failure.
    """
    try:
        features = _query_eplanning_point(
            "dualOccProhibition", lng, lat, out_fields="LAY_CLASS,EPI_NAME,LGA_NAME",
        )
    except Exception:
        logger.warning("Dual occ prohibition query failed")
        return None
    if not features:
        return {"prohibited": False}
    attrs = features[0]
    return {
        "prohibited": True,
        "epi_name": attrs.get("EPI_NAME"),
        "lga_name": attrs.get("LGA_NAME"),
    }


# ---------------------------------------------------------------------------
# Empirical data fetchers — Phase B (climate disclosure profile Layer 2)
# ---------------------------------------------------------------------------

def fetch_uhi(lat: float, lng: float) -> Optional[dict]:
    """NSW Urban Heat Island — UHGC/MapServer/0 (2016 data, meshblock level).

    Returns {"uhi_intensity": float, "lga": str, "region": str, "district": str} or None.
    """
    url = (
        "https://mapprod2.environment.nsw.gov.au/arcgis/rest/services/"
        "UHGC/UHGC/MapServer/0/query"
    )
    results = query_arcgis_point(
        url, lng, lat, out_fields="UHI_16_m,LGA,Region,District",
    )
    if not results:
        return None
    attrs = results[0]
    uhi_val = attrs.get("UHI_16_m")
    if uhi_val is None:
        return None
    return {
        "uhi_intensity": uhi_val,
        "lga": attrs.get("LGA"),
        "region": attrs.get("Region"),
        "district": attrs.get("District"),
        "data_year": 2016,
    }


def fetch_arr_ifd(lat: float, lng: float) -> Optional[dict]:
    """ARR Data Hub — BOM IFD rainfall depths by duration and AEP.

    Returns {"durations_min": [...], "aep_pct": [...], "depths_mm": [[...]], "ifd_1pct_60min_mm": float}
    or None on failure.
    """
    url = "https://data.arr-software.org/"
    params = {
        "lat_coord": str(lat),
        "lon_coord": str(lng),
        "type": "json",
        "BoMIFD": "1",
    }
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        logger.warning("ARR Data Hub query failed for (%.4f, %.4f)", lat, lng)
        return None

    layers = data.get("layers") or {}
    # Audit finding 2026-07-15 (issue #745 D2, live-reproduced): this endpoint
    # does NOT serve BOM IFD depths under any parameters. The previous code
    # consumed layers["BurstIL"] — ARR storm-burst INITIAL LOSS (mm), a design
    # loss parameter — and labelled it as the 1% AEP 60-min rainfall depth
    # (6.8 mm shown where Sydney's true value is ~90-100 mm). Fail closed:
    # only a layer explicitly keyed as IFD may be served; BurstIL never.
    # Wiring a genuine BOM IFD source is tracked in #745 (sourcing decision).
    ifd_layer = None
    for key, value in layers.items():
        if "ifd" in str(key).lower() and isinstance(value, dict):
            ifd_layer = value
            break
    if not ifd_layer:
        logger.warning(
            "ARR Data Hub returned no IFD layer for (%.4f, %.4f) — "
            "extreme_rainfall reported unavailable (never BurstIL)", lat, lng)
        return None

    durations = ifd_layer.get("index") or []
    aep_cols = ifd_layer.get("columns") or []
    depths = ifd_layer.get("data") or []

    # Extract the 1% AEP 60-minute depth for gap detection threshold
    # ARR may return AEP column as "1.0", "1", "1.00", or "1.0%" — normalize
    ifd_1pct_60min = None
    if durations and aep_cols and depths:
        try:
            dur_idx = durations.index(60)
            aep_idx = None
            for i in range(len(aep_cols)):
                raw_col = aep_cols[i]
                if raw_col is None:
                    continue
                clean = str(raw_col).strip().rstrip("%")
                if not clean:
                    continue
                parsed = 0.0
                if clean is not None:
                    try:
                        parsed = float(clean)
                    except (ValueError, TypeError):
                        continue
                if parsed == 1.0:
                    aep_idx = i
                    break
            if aep_idx is not None:
                ifd_1pct_60min = depths[dur_idx][aep_idx]
        except (ValueError, IndexError):
            pass

    return {
        "durations_min": durations,
        "aep_pct": aep_cols,
        "depths_mm": depths,
        "ifd_1pct_60min_mm": ifd_1pct_60min,
    }


_FIRMS_TIMEOUT = 15  # seconds — external API, allow more time

def fetch_firms_hotspots(
    lat: float, lng: float, buffer_km: float = 0.5, days: int = 10,
) -> Optional[dict]:
    """NASA FIRMS active fire detections within buffer of point.

    Uses VIIRS SNPP standard product (SP) for archive data.
    Requires NASA_FIRMS_MAP_KEY env var.

    Returns {"hotspot_count": int, "detections": [...], "search_days": int} or None.
    """
    import csv
    from io import StringIO
    from datetime import date as _date, timedelta as _timedelta

    map_key = os.environ.get("NASA_FIRMS_MAP_KEY")
    if not map_key:
        logger.info("NASA_FIRMS_MAP_KEY not set — FIRMS hotspot query skipped")
        return None

    # Build bounding box from point ± buffer
    # 1 degree lat ≈ 111km, 1 degree lng ≈ 111km * cos(lat)
    lat_offset = buffer_km / 111.0
    lng_offset = buffer_km / (111.0 * math.cos(lat * math.pi / 180))
    west = round(lng - lng_offset, 4)
    east = round(lng + lng_offset, 4)
    south = round(lat - lat_offset, 4)
    north = round(lat + lat_offset, 4)

    bbox = f"{west},{south},{east},{north}"
    # SP (Standard Product) has 1-2 day processing lag — query from yesterday
    query_date = (_date.today() - _timedelta(days=1)).isoformat()

    url = (
        f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/"
        f"{map_key}/VIIRS_SNPP_SP/{bbox}/{days}/{query_date}"
    )

    try:
        resp = requests.get(url, timeout=_FIRMS_TIMEOUT)
        resp.raise_for_status()
        text = resp.text.strip()
    except Exception:
        logger.warning("NASA FIRMS query failed for (%.4f, %.4f)", lat, lng)
        return None

    if not text or text.startswith("<!") or text.startswith("{"):
        # HTML error page or JSON error — not CSV
        logger.warning("NASA FIRMS returned non-CSV response")
        return None

    reader = csv.DictReader(StringIO(text))
    detections = []
    for row in reader:
        detections.append({
            "latitude": float(row.get("latitude", 0)),
            "longitude": float(row.get("longitude", 0)),
            "acq_date": row.get("acq_date"),
            "acq_time": row.get("acq_time"),
            "confidence": row.get("confidence"),
            "frp": float(row.get("frp", 0)) if row.get("frp") else None,
            "daynight": row.get("daynight"),
        })

    return {
        "hotspot_count": len(detections),
        "detections": detections,
        "search_days": days,
        "search_radius_km": buffer_km,
    }


# ---------------------------------------------------------------------------
# Conveyancing PDF — development contributions (/cp) and corridors /
# land-reservation-acquisition checks (LRA layer 24, SydneyTrain ISEPP, /warn).
#
# prior-art-checked: reuses services/arcgis_client.arcgis_get_with_retry
# (retry + circuit breaker) and the missing-`features` raise pattern from
# services/da_outcome.py (an ArcGIS error body returns {} from the client — a
# corridor check must never build a "clear" answer on a silently-zero result).
# The /cp response parse mirrors intelligence_brief._fetch_contributions
# (PR #460) but is re-wrapped with three-state semantics (found/empty/failed)
# because the brief fetcher collapses queried-empty and transport failure into
# one None — unacceptable in the Critical-tier conveyancing document. No
# existing module queries the LRA layer, the SydneyTrain_ISEPP layers, or the
# portal /warn endpoint (grep-verified 2026-07-07).
# ---------------------------------------------------------------------------

VIEWER_API_BASE = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi"
# The viewer API rejects requests without portal Origin/Referer headers.
VIEWER_API_HEADERS = {
    "Origin": "https://www.planningportal.nsw.gov.au",
    "Referer": "https://www.planningportal.nsw.gov.au/",
    "User-Agent": "Mozilla/5.0",
}
VIEWER_API_TIMEOUT = 15  # seconds

LRA_QUERY_URL = (
    f"{EPLANNING_BASE}/Planning_Portal_Principal_Planning/MapServer/24/query"
)
LRA_OUT_FIELDS = (
    "EPI_NAME,LGA_NAME,LRA_TYPE,LAY_CLASS,LABEL,AUTHORITY,"
    "CURRENCY_DATE,COMMENCED_DATE,AMENDMENT"
)
# Layer names verified live 2026-07-07 (825 / 800 polygons; fields agency,
# defining_legislation). The zone label is the layer itself.
RAIL_ISEPP_LAYERS = (
    ("Corridor Protection Zone",
     f"{EPLANNING_BASE}/SydneyTrain_ISEPP/MapServer/1/query"),
    ("Infrastructure Protection Zone",
     f"{EPLANNING_BASE}/SydneyTrain_ISEPP/MapServer/2/query"),
)

# Geometry-basis labels recorded in the corridors payload so renderers can
# state HOW the check was run (lot polygon vs point fallback).
CORRIDOR_BASIS_LOT = "lot_polygon"
CORRIDOR_BASIS_CENTROID = "centroid_30m"
_CORRIDOR_POINT_BUFFER_M = 30


def _wkt_polygon_rings(lot_wkt: Optional[str]) -> Optional[list]:
    """Parse an EPSG:4326 POLYGON WKT into esri-JSON rings.

    Returns None when the WKT is absent or unparseable — callers fall back to
    the centroid+buffer basis rather than guessing at geometry.
    """
    import re as _re

    if not lot_wkt:
        return None
    m = _re.match(r"\s*POLYGON\s*\((.*)\)\s*$", lot_wkt, _re.IGNORECASE | _re.DOTALL)
    if not m:
        return None
    rings = []
    for ring_str in _re.findall(r"\(([^()]*)\)", m.group(1)):
        pts = []
        for pair in ring_str.split(","):
            xy = pair.split()
            if len(xy) < 2:
                return None
            try:
                pts.append([float(xy[0]), float(xy[1])])
            except ValueError:
                return None
        if len(pts) >= 4:
            rings.append(pts)
    return rings or None


def _corridor_geometry_params(
    lat: float, lng: float, lot_wkt: Optional[str],
) -> tuple[dict, str]:
    """Build the ArcGIS geometry params: lot polygon when available, else
    centroid + 30 m buffer. Returns (params, basis)."""
    import json as _json

    rings = _wkt_polygon_rings(lot_wkt)
    if rings:
        return (
            {
                "geometry": _json.dumps(
                    {"rings": rings, "spatialReference": {"wkid": 4326}}
                ),
                "geometryType": "esriGeometryPolygon",
                "inSR": "4326",
                "spatialRel": "esriSpatialRelIntersects",
            },
            CORRIDOR_BASIS_LOT,
        )
    return (
        {
            "geometry": f"{lng},{lat}",
            "geometryType": "esriGeometryPoint",
            "inSR": "4326",
            "spatialRel": "esriSpatialRelIntersects",
            "distance": str(_CORRIDOR_POINT_BUFFER_M),
            "units": "esriSRUnit_Meter",
        },
        CORRIDOR_BASIS_CENTROID,
    )


def _query_corridor_layer(
    url: str, geometry_params: dict, out_fields: str,
) -> list[dict]:
    """Query one ArcGIS layer with the corridor geometry. RAISES on failure.

    arcgis_get_with_retry returns {} on transport failure or an HTTP-200
    ArcGIS error body — the missing-`features` raise below refuses to turn
    that into a silent zero (services/da_outcome.py pattern).
    """
    try:
        from services.arcgis_client import arcgis_get_with_retry
    except ImportError:  # CLI context: services/ itself is on sys.path
        from arcgis_client import arcgis_get_with_retry

    params = dict(geometry_params)
    params.update({
        "outFields": out_fields,
        "returnGeometry": "false",
        "f": "json",
    })
    data = arcgis_get_with_retry(url, params)
    if "features" not in data:
        raise RuntimeError(
            f"corridor layer query failed (transport or ArcGIS error): {url}"
        )
    return [(f.get("attributes") or {}) for f in (data.get("features") or [])]


def _esri_ms_to_date(ms) -> Optional[str]:
    """Esri epoch-milliseconds → ISO date string; None when absent/invalid."""
    from datetime import datetime as _dt, timezone as _tz

    if ms is None:
        return None
    try:
        return _dt.fromtimestamp(float(ms) / 1000.0, tz=_tz.utc).date().isoformat()
    except (ValueError, OverflowError, OSError, TypeError):
        return None


def fetch_portal_warnings(prop_id: int) -> list[dict]:
    """NSW Planning Portal /warn property warnings. RAISES on failure.

    Every returned item is captured verbatim (title + layerRef) — unknown
    layerRef values are rendered, never dropped (fail-open, SDWC precedent).
    """
    resp = requests.get(
        f"{VIEWER_API_BASE}/warn",
        params={"id": prop_id, "type": "property"},
        headers=VIEWER_API_HEADERS,
        timeout=VIEWER_API_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, list):
        raise RuntimeError(
            "portal /warn response was not a list (transport or API error)"
        )
    items = []
    for w in data:
        if not isinstance(w, dict):
            logger.warning("portal /warn returned a non-dict item %r — captured", w)
            items.append({"title": str(w), "layerRef": None})
            continue
        title = w.get("title") or w.get("layerRef")
        if not w.get("title"):
            logger.warning(
                "portal /warn item without title captured verbatim (layerRef=%r)",
                w.get("layerRef"),
            )
        items.append({
            "title": title or "Unnamed portal property warning",
            "layerRef": w.get("layerRef"),
        })
    return items


def fetch_corridors_reservations(
    lat: float,
    lng: float,
    lot_wkt: Optional[str] = None,
    prop_id: Optional[int] = None,
) -> dict:
    """Corridors & land-reservation-acquisition check — three-state per sub-check.

    Returns::

        {
          "query_basis": "lot_polygon" | "centroid_30m",
          "data_currency": str | None,          # max CURRENCY_DATE seen (ISO)
          "lra":            {"status": "found"|"empty"|"failed", "items": [...]},
          "rail_corridors": {"status": ..., "items": [...]},
          "warnings":       {"status": ..., "items": [...]},
        }

    A failed sub-check never reads as clear: its status is "failed" and the
    renderer states "Not assessed". Never raises.
    """
    geometry_params, basis = _corridor_geometry_params(lat, lng, lot_wkt)
    out: dict = {
        "query_basis": basis,
        "data_currency": None,
        "lra": {"status": "failed", "items": []},
        "rail_corridors": {"status": "failed", "items": []},
        "warnings": {"status": "failed", "items": []},
    }

    try:
        lra_items = _query_corridor_layer(LRA_QUERY_URL, geometry_params, LRA_OUT_FIELDS)
        for it in lra_items:
            it["currency_date"] = _esri_ms_to_date(it.get("CURRENCY_DATE"))
            it["commenced_date"] = _esri_ms_to_date(it.get("COMMENCED_DATE"))
        currency_dates = [it.get("currency_date") for it in lra_items if it.get("currency_date")]
        if currency_dates:
            out["data_currency"] = max(currency_dates)
        out["lra"] = {"status": "found" if lra_items else "empty", "items": lra_items}
    except Exception as e:
        logger.warning("LRA layer query failed: %s", e)

    try:
        rail_items = []
        for zone_name, url in RAIL_ISEPP_LAYERS:
            for attrs in _query_corridor_layer(url, geometry_params, "agency,defining_legislation"):
                rail_items.append({
                    "zone": zone_name,
                    "agency": attrs.get("agency"),
                    "defining_legislation": attrs.get("defining_legislation"),
                })
        out["rail_corridors"] = {
            "status": "found" if rail_items else "empty", "items": rail_items,
        }
    except Exception as e:
        logger.warning("rail corridor layer query failed: %s", e)

    if prop_id:
        try:
            warn_items = fetch_portal_warnings(int(prop_id))
            out["warnings"] = {
                "status": "found" if warn_items else "empty", "items": warn_items,
            }
        except Exception as e:
            logger.warning("portal /warn query failed: %s", e)
    else:
        # No propId — the warnings check cannot run; "failed" keeps the
        # renderer on "Not assessed" rather than an implied clear.
        logger.warning("portal /warn skipped — no propId resolved for this lot")

    return out


def _fetch_cp_payload(prop_id: int) -> dict:
    """GET the /cp contributions payload. RAISES on transport/malformed response.

    A bare {} (or any response missing both the cp and icdp blocks) is treated
    as a FAILURE, not as "no plans" — the queried-empty state requires the
    blocks to be present with empty results.
    """
    resp = requests.get(
        f"{VIEWER_API_BASE}/cp",
        params={"id": prop_id, "type": "property"},
        headers=VIEWER_API_HEADERS,
        timeout=VIEWER_API_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    if not isinstance(data, dict) or ("cp" not in data and "icdp" not in data):
        raise RuntimeError(
            "contributions /cp response missing cp/icdp blocks (transport or API error)"
        )
    return data


def fetch_contributions_plans(prop_id: int) -> dict:
    """Development contributions plans (/cp) — three-state, never raises.

    Returns::

        {"status": "found", "plans": [{"plan_name","plan_url"}], "hpc": {...}|None,
         "lga_name": str|None}
        {"status": "empty", "plans": [], "hpc": None, "lga_name": str|None}
        {"status": "failed"}

    Plan names and URLs are carried verbatim from the portal response.
    """
    try:
        data = _fetch_cp_payload(int(prop_id))
    except Exception as e:
        logger.warning("contributions /cp lookup failed for propId %s: %s", prop_id, e)
        return {"status": "failed"}

    plans: list[dict] = []
    lga_name: Optional[str] = None
    for entry in ((data.get("cp") or {}).get("results") or []):
        if not lga_name:
            lga_name = entry.get("lgaName")
        for cp in (entry.get("cpResults") or []):
            plans.append({
                "plan_name": cp.get("planName") or "",
                "plan_url": cp.get("planURL"),
            })

    hpc: Optional[dict] = None
    for entry in ((data.get("icdp") or {}).get("results") or []):
        for res in (entry.get("results") or []):
            hpc = {
                "name": res.get("Name"),
                "component": res.get("Component"),
                "commenced_date": res.get("Commenced Date"),
                "ministerial_order_url": res.get("Ministerial Order"),
            }
            break
        if hpc:
            break

    if not plans and not hpc:
        return {"status": "empty", "plans": [], "hpc": None, "lga_name": lga_name}
    return {"status": "found", "plans": plans, "hpc": hpc, "lga_name": lga_name}
