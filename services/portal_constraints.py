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
    burst_il = layers.get("BurstIL") or {}
    if not burst_il:
        return None

    durations = burst_il.get("index") or []
    aep_cols = burst_il.get("columns") or []
    depths = burst_il.get("data") or []

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
