"""
NSW Government ArcGIS portal constraint queries.

Shared module — consumed by intelligence_brief.py and available for
compliance engine migration. Each function takes (lat, lng) and returns
a typed dict or None.

Endpoints are public government ArcGIS REST services (no API keys).
"""
import math
import logging
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

    Returns {"low_mid_rise": bool|None, "complying": bool|None, "exempt": bool|None}.
    Always returns a dict (None values mean query failed for that layer).
    """
    result = {}
    for key, field_name in [
        ("lowMidRiseExclusion", "low_mid_rise"),
        ("complyingExclusion", "complying"),
        ("exemptExclusion", "exempt"),
    ]:
        try:
            features = _query_eplanning_point(key, lng, lat, out_fields="LAY_CLASS")
            result[field_name] = len(features) > 0
        except Exception:
            logger.warning("SEPP exclusion layer %s query failed", key)
            result[field_name] = None
    # Only return None if all queries failed
    if all(v is None for v in result.values()):
        return None
    return result


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
