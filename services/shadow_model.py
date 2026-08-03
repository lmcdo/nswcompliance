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
import json
import logging
import math
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


def lot_depth_m(lot_geojson: dict) -> float:
    """North-south extent of the lot polygon in metres."""
    try:
        from shapely.geometry import shape
        bounds = shape(lot_geojson).bounds  # (minx, miny, maxx, maxy)
        return abs(bounds[3] - bounds[1]) * 111_000
    except Exception:
        return 20.0  # sensible suburban default


def northern_neighbour_proxy(lot_geojson: dict, offset_m: Optional[float] = None) -> dict:
    """
    Return a GeoJSON Polygon representing a hypothetical building on the
    lot immediately to the north of the subject lot.

    Uses the lot's BOUNDING BOX (not its exact shape) as the proxy footprint.
    Irregular lots (triangular, battleaxe, L-shaped) would produce unrealistic
    proxy shapes if the exact outline were copied — a rectangle is a better
    proxy for what a neighbouring building actually looks like.

    offset_m: override the auto-calculated offset (default = lot depth).
    """
    try:
        from shapely.geometry import shape, mapping, box
        from shapely.affinity import translate
        lot = shape(lot_geojson)
        bounds = lot.bounds  # (minx, miny, maxx, maxy)
        depth = offset_m if offset_m is not None else lot_depth_m(lot_geojson)
        delta_lat = depth / 111_000
        # Rectangular bounding-box footprint — realistic, shape-independent
        lot_bbox = box(bounds[0], bounds[1], bounds[2], bounds[3])
        shifted = translate(lot_bbox, xoff=0.0, yoff=delta_lat)
        return mapping(shifted)
    except Exception as e:
        logger.warning(f"northern_neighbour_proxy failed, using original lot: {e}")
        return lot_geojson

# (key, month, day, hour_utc, description, date_str, time_local, direction_deg)
# direction_deg = direction shadow points (opposite of sun azimuth)
# The fixed year every scenario models (solar positions repeat closely year to
# year; the manifests record this so a report states WHICH year was modelled).
SCENARIO_YEAR = 2025

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

    pybdshadow requires WGS84 (lat/lon degrees) input — it creates an internal
    azimuthal equidistant (aeqd) projection centred on the building centroid to
    perform metric shadow calculations, then returns results in the input CRS.
    DO NOT reproject to UTM before calling: pybdshadow treats coordinates as
    lat/lon for its internal solar position and aeqd setup; passing UTM easting/
    northing (~884,000 / ~6,241,000) as degrees makes lat_0 >> 90° → PROJ error.
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

    target_year = SCENARIO_YEAR
    if hour_utc == 23 and month == 6 and day == 21:
        target_dt = datetime(target_year, 6, 20, 23, 0, 0, tzinfo=timezone.utc)
    else:
        target_dt = datetime(target_year, month, day, hour_utc, 0, 0, tzinfo=timezone.utc)

    lot_polygon = shape(lot_geometry_geojson)

    # Pass WGS84 directly — pybdshadow handles metric conversion internally.
    buildings = gpd.GeoDataFrame(
        {"building_id": [0], "height": [float(height_limit_m)]},
        geometry=[lot_polygon], crs="EPSG:4326",
    )

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
    # Input was WGS84 so output is also WGS84 — set explicitly if missing.
    if shadows.crs is None:
        shadows = shadows.set_crs("EPSG:4326")

    # Use geopandas' own JSON serialiser — avoids numpy.int64/float64 types
    # that __geo_interface__ leaves in feature properties, which cause
    # psycopg2.extras.Json to raise TypeError at DB write time.
    return json.loads(shadows.to_json())


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


# Fraction of subject lot area that must be shadowed to count as "overlapping".
# <40% → rear yard still gets meaningful sun; ≥40% → shadow materially covers the lot.
OVERLAP_THRESHOLD = 0.40


def _shadow_intersection(shadow_geojson: dict, lot_geojson: dict):
    """
    Return the shapely geometry of the shadow's intersection with the subject lot.
    Returns None on error or if shapely unavailable.
    """
    try:
        from shapely.geometry import shape
        from shapely.ops import unary_union
        lot = shape(lot_geojson)
        shadow_shapes = [
            shape(f["geometry"])
            for f in shadow_geojson.get("features", [])
            if f.get("geometry")
        ]
        if not shadow_shapes:
            return None
        intersection = unary_union(shadow_shapes).intersection(lot)
        return intersection if not intersection.is_empty else None
    except Exception as e:
        logger.warning(f"Shadow intersection failed: {e}")
        return None


def shadow_overlap_fraction(shadow_geojson: dict, lot_geojson: dict) -> float:
    """
    Fraction (0–1) of the subject lot area covered by the shadow polygon.
    0.0 = no overlap; 1.0 = entire lot in shadow.
    """
    try:
        from shapely.geometry import shape
        lot = shape(lot_geojson)
        lot_area = lot.area
        if lot_area == 0:
            return 0.0
        intersection = _shadow_intersection(shadow_geojson, lot_geojson)
        if intersection is None:
            return 0.0
        return round(min(1.0, intersection.area / lot_area), 3)
    except Exception as e:
        logger.warning(f"Overlap fraction failed: {e}")
        return 0.0


def shadow_reach_m(shadow_geojson: dict, lot_geojson: dict) -> float:
    """
    How far (metres) the shadow penetrates into the subject lot, measured
    from the lot's northern boundary southward.

    0   = shadow doesn't enter the lot.
    lot_depth_m = shadow covers the entire lot.

    This replaces the old shadow_length_m (which measured from lot centroid
    to all shadow vertices including the proxy building, making it useless).
    """
    try:
        from shapely.geometry import shape
        lot = shape(lot_geojson)
        lot_north_lat = lot.bounds[3]   # maxy
        intersection = _shadow_intersection(shadow_geojson, lot_geojson)
        if intersection is None:
            return 0.0
        # Southernmost point of the intersection = deepest shadow penetration
        south_lat = intersection.bounds[1]  # miny
        reach_lat = lot_north_lat - south_lat
        return round(max(0.0, reach_lat * 111_000), 1)
    except Exception as e:
        logger.warning(f"shadow_reach_m failed: {e}")
        return 0.0


def shadow_length_m(shadow_geojson: dict, lot_geojson: dict, **_kwargs) -> float:
    """
    Backwards-compatible wrapper — now returns shadow_reach_m.
    Old signature accepted (lot_centroid_lng, lot_centroid_lat); new callers
    should use shadow_reach_m directly.
    """
    return shadow_reach_m(shadow_geojson, lot_geojson)


def overlaps_lot(shadow_geojson: dict, lot_geojson: dict) -> bool:
    """
    True if the shadow covers ≥OVERLAP_THRESHOLD of the subject lot area.
    A 40% threshold means the rear yard (principal private open space) is
    materially impacted; minor edge shadows at 9am/3pm don't trigger this.
    """
    return shadow_overlap_fraction(shadow_geojson, lot_geojson) >= OVERLAP_THRESHOLD


def shadow_on_lot_geojson(shadow_geojson: dict, lot_geojson: dict) -> Optional[dict]:
    """
    Return a GeoJSON FeatureCollection of the shadow clipped to the subject lot.
    Used to render exactly which part of the lot is in shadow — not the full
    pybdshadow polygon (which includes the proxy building footprint).
    Returns None if no intersection.
    """
    intersection = _shadow_intersection(shadow_geojson, lot_geojson)
    if intersection is None:
        return None
    try:
        from shapely.geometry import mapping
        return {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "geometry": mapping(intersection), "properties": {}}],
        }
    except Exception as e:
        logger.warning(f"shadow_on_lot_geojson failed: {e}")
        return None


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
