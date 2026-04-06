"""
Shadow modelling -- geometric pybdshadow + pvlib solar position.

5 ADG-standard scenarios for any lot+height combination.

VERIFIED 2026-04-06 via pvlib: shadows extend SOUTHWARD for Sydney June 21.
  9am:  sun at NE 42.6° → shadow SW 222.6°
  noon: sun at N  359.2° → shadow S  179.2°
  3pm:  sun at NW 316.3° → shadow SE 136.3°
pybdshadow uses suncalc-py which computes correct solar position for Southern Hemisphere.
No special Southern Hemisphere handling needed.
"""
import logging
from datetime import datetime, timezone
logger = logging.getLogger(__name__)

SHADOW_SCENARIOS = [
    ("jun21_9am",   6, 21, 23, "ADG worst case 9am Jun 21"),
    ("jun21_12pm",  6, 21,  2, "ADG worst case noon Jun 21"),
    ("jun21_3pm",   6, 21,  5, "ADG worst case 3pm Jun 21"),
    ("sep21_12pm",  9, 21,  2, "Spring equinox noon"),
    ("dec21_12pm", 12, 21,  2, "Summer solstice noon"),
]
# ADG: 2 hours solar access 9am-3pm Jun 21 required.


def model_shadow(lot_geometry_geojson: dict, height_limit_m: float, scenario: str = "jun21_12pm") -> dict:
    """
    Compute shadow polygon for a max-permissible building on a lot.
    Returns GeoJSON FeatureCollection.
    """
    try:
        import geopandas as gpd
        import pybdshadow
        from shapely.geometry import shape
    except ImportError:
        raise RuntimeError("geopandas / pybdshadow not installed")

    s_map = {s[0]: s for s in SHADOW_SCENARIOS}
    if scenario not in s_map:
        raise ValueError(f"Unknown scenario: {scenario}")
    _, month, day, hour_utc, _ = s_map[scenario]

    # Jun 21 9am AEST = 23:00 UTC Jun 20
    target_year = 2025
    if hour_utc == 23 and month == 6 and day == 21:
        target_dt = datetime(target_year, 6, 20, 23, 0, 0, tzinfo=timezone.utc)
    else:
        target_dt = datetime(target_year, month, day, hour_utc, 0, 0, tzinfo=timezone.utc)

    lot_polygon = shape(lot_geometry_geojson)
    buildings = __import__('geopandas').GeoDataFrame(
        {"height": [float(height_limit_m)]},
        geometry=[lot_polygon], crs="EPSG:4326",
    )
    shadows = pybdshadow.bdshadow_sunlight(buildings, target_dt)
    return shadows.__geo_interface__


def model_all_scenarios(lot_geometry_geojson: dict, height_limit_m: float) -> dict:
    """Run all 5 scenarios. Returns dict keyed by label. Each runs in <1s (pure geometry)."""
    results = {}
    for label, *_ in SHADOW_SCENARIOS:
        try:
            results[label] = model_shadow(lot_geometry_geojson, height_limit_m, label)
        except Exception as e:
            logger.warning(f"Scenario {label} failed: {e}")
            results[label] = {"error": str(e)}
    return results


def get_scenario_metadata() -> list:
    return [{"label": s[0], "month": s[1], "day": s[2], "hour_utc": s[3], "description": s[4]}
            for s in SHADOW_SCENARIOS]
