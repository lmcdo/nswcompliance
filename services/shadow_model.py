"""
Shadow modelling -- geometric pybdshadow + pvlib solar position.

5 ADG-standard scenarios for any lot+height combination.

VERIFIED 2026-04-06 via pvlib: shadows extend SOUTHWARD for Sydney June 21.
  9am:  sun at NE 42.6° → shadow SW 222.6°
  noon: sun at N  359.2° → shadow S  179.2°
  3pm:  sun at NW 316.3° → shadow SE 136.3°
Sep/Dec direction_deg values are approximate (pvlib not yet run for those dates).
pybdshadow uses suncalc-py which computes correct solar position for Southern Hemisphere.
No special Southern Hemisphere handling needed.
"""
import logging
import math
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# (key, month, day, hour_utc, description, date_str, time_local, direction_deg)
# direction_deg = direction shadow points (opposite of sun azimuth)
SHADOW_SCENARIOS = [
    ("jun21_9am",   6, 21, 23, "ADG worst case 9am Jun 21",  "2025-06-21", "09:00", 222.6),
    ("jun21_12pm",  6, 21,  2, "ADG worst case noon Jun 21", "2025-06-21", "12:00", 179.2),
    ("jun21_3pm",   6, 21,  5, "ADG worst case 3pm Jun 21",  "2025-06-21", "15:00", 136.3),
    ("sep21_12pm",  9, 21,  2, "Spring equinox noon",        "2025-09-21", "12:00", 175.0),
    ("dec21_12pm", 12, 21,  2, "Summer solstice noon",       "2025-12-21", "12:00", 183.0),
]
# ADG: 2 hours solar access 9am-3pm Jun 21 required.

_SCENARIO_MAP = {s[0]: s for s in SHADOW_SCENARIOS}


def model_shadow(lot_geometry_geojson: dict, height_limit_m: float, scenario: str = "jun21_12pm") -> dict:
    """
    Compute shadow polygon for a max-permissible building on a lot.
    Returns GeoJSON FeatureCollection in WGS84 (EPSG:4326).

    pybdshadow requires metric coordinates — we reproject to UTM Zone 55S
    (EPSG:32755, correct for Sydney) before passing to pybdshadow, then
    reproject shadow output back to WGS84 for downstream use.
    """
    try:
        import geopandas as gpd
        import pybdshadow
        from shapely.geometry import shape
    except ImportError:
        raise RuntimeError("geopandas / pybdshadow not installed")

    if scenario not in _SCENARIO_MAP:
        raise ValueError(f"Unknown scenario: {scenario}")
    _, month, day, hour_utc, *_ = _SCENARIO_MAP[scenario]

    target_year = 2025
    if hour_utc == 23 and month == 6 and day == 21:
        target_dt = datetime(target_year, 6, 20, 23, 0, 0, tzinfo=timezone.utc)
    else:
        target_dt = datetime(target_year, month, day, hour_utc, 0, 0, tzinfo=timezone.utc)

    lot_polygon = shape(lot_geometry_geojson)

    # Reproject to UTM Zone 55S (metres) — pybdshadow treats coordinates as metres.
    # Passing WGS84 degrees makes the lot ~0.05mm wide, producing zero shadows.
    buildings = gpd.GeoDataFrame(
        {"building_id": [0], "height": [float(height_limit_m)]},
        geometry=[lot_polygon], crs="EPSG:4326",
    ).to_crs("EPSG:32755")

    shadows = pybdshadow.bdshadow_sunlight(buildings, target_dt)
    logger.debug(
        "pybdshadow: rows=%d crs=%s empty=%s",
        len(shadows) if shadows is not None else -1,
        getattr(shadows, "crs", "N/A"),
        shadows.empty if shadows is not None else "None",
    )

    if shadows is None or shadows.empty:
        return {"type": "FeatureCollection", "features": []}

    # pybdshadow does not always preserve CRS on its output GeoDataFrame.
    # Set it explicitly before reprojecting back to WGS84.
    if shadows.crs is None:
        shadows = shadows.set_crs("EPSG:32755")

    return shadows.to_crs("EPSG:4326").__geo_interface__


def model_all_scenarios(lot_geometry_geojson: dict, height_limit_m: float) -> dict:
    """Run all 5 scenarios. Returns dict keyed by scenario key. Each runs in <1s."""
    results = {}
    for key, *_ in SHADOW_SCENARIOS:
        try:
            results[key] = model_shadow(lot_geometry_geojson, height_limit_m, key)
        except Exception as e:
            logger.warning(f"Scenario {key} failed: {e}")
            results[key] = {"error": str(e)}
    return results


def get_scenario_metadata() -> list:
    return [
        {"key": s[0], "month": s[1], "day": s[2], "hour_utc": s[3],
         "description": s[4], "date_str": s[5], "time_local": s[6], "direction_deg": s[7]}
        for s in SHADOW_SCENARIOS
    ]


def shadow_length_m(shadow_geojson: dict, lot_centroid_lng: float, lot_centroid_lat: float) -> float:
    """Max distance from lot centroid to any vertex of the shadow polygon, in metres."""
    max_dist = 0.0
    clat = math.radians(lot_centroid_lat)
    for feature in shadow_geojson.get("features", []):
        geom = feature.get("geometry", {})
        coords = _extract_coords(geom)
        for lng, lat in coords:
            dlat = math.radians(lat - lot_centroid_lat)
            dlng = math.radians(lng - lot_centroid_lng)
            a = (math.sin(dlat / 2) ** 2
                 + math.cos(clat) * math.cos(math.radians(lat)) * math.sin(dlng / 2) ** 2)
            dist = 6_371_000 * 2 * math.asin(math.sqrt(max(0.0, a)))
            if dist > max_dist:
                max_dist = dist
    return round(max_dist, 1)


def overlaps_lot(shadow_geojson: dict, lot_geojson: dict) -> bool:
    """True if any shadow feature intersects the lot polygon."""
    try:
        from shapely.geometry import shape
        lot_shape = shape(lot_geojson)
        for feature in shadow_geojson.get("features", []):
            if lot_shape.intersects(shape(feature["geometry"])):
                return True
    except Exception as e:
        logger.warning(f"Overlap check failed: {e}")
    return False


def _extract_coords(geom: dict) -> list:
    gtype = geom.get("type", "")
    coords = geom.get("coordinates", [])
    if gtype == "Polygon":
        return coords[0] if coords else []
    if gtype == "MultiPolygon":
        out = []
        for poly in coords:
            if poly:
                out.extend(poly[0])
        return out
    return []
