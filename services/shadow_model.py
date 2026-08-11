"""
Shadow modelling -- geometric shadow casting via pybdshadow.

5 ADG-standard scenarios for any lot+height combination.

METHOD, as the code actually runs it: `model_shadow` passes the building
footprint, its height and a UTC instant to `pybdshadow.bdshadow_sunlight`,
which derives the sun position itself (via `suncalc`) and returns the shadow
polygon. The bearing REPORTED alongside it comes from `services.solar_position`,
which calls that same `suncalc` function -- so the Direction column and the
drawn polygon cannot disagree. pvlib is not imported anywhere in production and
must not be; it is a test-only reference (see tests/test_shadow_calibration.py).

WHAT CHANGED 2026-08-07 (calibration lane 2) and why
----------------------------------------------------
1. Each scenario declared BOTH a display label ("12:00") and a hand-computed
   `hour_utc`. Nothing bound them together, so they drifted: `dec21_12pm` stored
   `hour_utc=2`, which is 13:00 AEDT -- the summer scenario was modelled an hour
   late in all 538 stored reports. Scenarios now declare only the LOCAL
   wall-clock time; the UTC instant is derived through the IANA database by
   `solar_position.local_wall_clock_to_utc`. There is no longer a second number
   to keep in step.

2. `direction_deg` was a STORED constant per scenario, identical for every
   address. Four of the five reproduced `suncalc` at Sydney CBD to <=0.09 deg,
   so they were real; the December one (183.0) matched no computable instant and
   was out by 11.4 deg. Bearing is now computed per address at request time.
   Measured spread of the true bearing across the served NSW envelope: 17-23 deg
   for the June/September scenarios, 134 deg for December.

3. The "shadows fall southward in Sydney" claim -- open since April as an
   unverified caveat -- is now asserted by a committed test across latitude,
   season and hour, and holds: NSW lies entirely south of the Tropic of
   Capricorn, so the noon sun is always north of the zenith.
"""
import json
import logging
import math
from datetime import datetime
from typing import NamedTuple, Optional

try:
    from services.solar_position import (
        NSW_TZ, local_wall_clock_to_utc, shadow_bearing_deg,
    )
except ImportError:  # flat-import deploy mode (services/ on PYTHONPATH)
    from solar_position import (
        NSW_TZ, local_wall_clock_to_utc, shadow_bearing_deg,
    )

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
    Return a GeoJSON Polygon standing in for a hypothetical maximum-height
    building north of the subject lot.

    ⚠ THIS IS NOT A CADASTRAL PARCEL AND MUST NEVER BE PRESENTED AS ONE.
    It is the SUBJECT lot's own bounding box, translated north by the subject
    lot's own depth. No neighbouring parcel is fetched, and none is available:
    the NSW lot API is keyed by `propId` only, and nothing in this repo resolves
    parcel adjacency. Where the real neighbour's boundary actually falls is
    unknown to this computation.

    Consequence for served surfaces: any caption drawn over this polygon must
    describe it as a modelled envelope positioned by offset from the subject's
    own boundary — not as "the adjacent lot".

    Uses the BOUNDING BOX rather than the exact outline because irregular lots
    (triangular, battleaxe, L-shaped) would otherwise produce proxy shapes no
    building could occupy.

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

# The fixed year every scenario models (solar positions repeat closely year to
# year; the manifests record this so a report states WHICH year was modelled).
SCENARIO_YEAR = 2025


class Scenario(NamedTuple):
    """One ADG test instant.

    Declares the LOCAL WALL-CLOCK time only. There is deliberately no `hour_utc`
    field: storing a display label beside a hand-computed UTC offset is what let
    the December scenario be modelled at 13:00 while labelled 12:00. Index
    access (`s[0]`) and unpacking still work, so existing iteration is unaffected.
    """
    key: str
    month: int
    day: int
    local_hour: int      # wall-clock hour in NSW_TZ, as the customer reads it
    local_minute: int
    description: str

    @property
    def date_str(self) -> str:
        return f"{SCENARIO_YEAR:04d}-{self.month:02d}-{self.day:02d}"

    @property
    def time_local(self) -> str:
        """The label. Derived from the modelled hour, so it cannot contradict it."""
        return f"{self.local_hour:02d}:{self.local_minute:02d}"

    def instant_utc(self, year: int = SCENARIO_YEAR) -> datetime:
        """The UTC instant this scenario's wall-clock time names, DST resolved."""
        return local_wall_clock_to_utc(
            year, self.month, self.day, self.local_hour, self.local_minute, NSW_TZ)


SHADOW_SCENARIOS = [
    Scenario("jun21_9am",   6, 21,  9, 0, "ADG worst case 9am Jun 21"),
    Scenario("jun21_12pm",  6, 21, 12, 0, "ADG worst case noon Jun 21"),
    Scenario("jun21_3pm",   6, 21, 15, 0, "ADG worst case 3pm Jun 21"),
    Scenario("sep21_12pm",  9, 21, 12, 0, "Spring equinox noon"),
    Scenario("dec21_12pm", 12, 21, 12, 0, "Summer solstice noon"),
]
# ADG: 2 hours solar access 9am-3pm Jun 21 required.
# June and September fall in AEST (UTC+10); December falls in AEDT (UTC+11).
# Nothing here encodes that -- `instant_utc` resolves it from the IANA database.

_SCENARIO_MAP = {s.key: s for s in SHADOW_SCENARIOS}


def scenario_shadow_bearing_deg(scenario_key: str, lat: float, lng: float,
                                year: int = SCENARIO_YEAR) -> Optional[float]:
    """Compass bearing the shadow falls toward, FOR THIS ADDRESS.

    Replaces the five stored `direction_deg` constants. Returns None when the
    bearing is not meaningful (sun below the horizon, or so near the zenith that
    it is ill-conditioned) -- never a fabricated number.
    """
    scenario = _SCENARIO_MAP.get(scenario_key)
    if scenario is None:
        return None
    return shadow_bearing_deg(scenario.instant_utc(year), lat, lng)


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

    # Derived, never typed. `local_wall_clock_to_utc` resolves AEST vs AEDT from
    # the IANA database, so the 9am June case rolls back to the previous UTC day
    # on its own -- the hand-written special case that used to do that is gone,
    # along with the December offset it did not cover.
    target_dt = _SCENARIO_MAP[scenario].instant_utc(SCENARIO_YEAR)

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
    for scenario in SHADOW_SCENARIOS:
        key = scenario.key
        try:
            results[key] = model_shadow(lot_geometry_geojson, height_limit_m, key)
        except Exception as e:
            logger.warning(f"Scenario {key} failed: {e}")
            results[key] = {"error": str(e)}
    return results


# prior-art-checked: reuse not viable because there is nothing to reuse -- this
# EDITS the existing get_scenario_metadata in place (same file, same function,
# same callers). No new capability, no parallel surface: the `direction_deg` key
# is dropped because bearing became per-address, and `hour_utc` is replaced by a
# DERIVED `instant_utc`. The guard matched generic English in the docstring.
def get_scenario_metadata() -> list:
    """Scenario descriptors. `instant_utc` is derived from the wall-clock time,
    so the two can never disagree; there is no stored `direction_deg` -- bearing
    is per address, via `scenario_shadow_bearing_deg`."""
    return [
        {"key": s.key, "month": s.month, "day": s.day,
         "local_hour": s.local_hour, "local_minute": s.local_minute,
         "description": s.description, "date_str": s.date_str,
         "time_local": s.time_local,
         "instant_utc": s.instant_utc().isoformat()}
        for s in SHADOW_SCENARIOS
    ]


# Fraction of subject lot area that must be shadowed to count as "overlapping".
# <40% → rear yard still gets meaningful sun; ≥40% → shadow materially covers the lot.
OVERLAP_THRESHOLD = 0.40


class ShadowGeometryError(RuntimeError):
    """The shadow/lot intersection could not be COMPUTED.

    Distinct from a computed empty intersection. Conflating the two is what
    let a GEOS TopologyException be served as "0% of the lot is in shadow" —
    a measurement the run never made, about the customer's own amenity.
    """


def _shadow_intersection(shadow_geojson: dict, lot_geojson: dict):
    """The shadow's intersection with the subject lot, or None if they do not meet.

    Returns None ONLY when the geometry is valid and the shadow genuinely does
    not touch the lot. Raises ShadowGeometryError when the intersection could
    not be computed at all — GEOS raises TopologyException on self-touching or
    unclosed cadastral rings, and that is an ABSENCE OF MEASUREMENT, not a
    finding of no shadow. The previous code caught it and returned None, which
    every caller then coerced to 0.0.
    """
    from shapely.geometry import shape
    from shapely.ops import unary_union
    try:
        lot = shape(lot_geojson)
        shadow_shapes = [
            shape(f["geometry"])
            for f in shadow_geojson.get("features", [])
            if f.get("geometry")
        ]
        if not shadow_shapes:
            return None
        intersection = unary_union(shadow_shapes).intersection(lot)
    except Exception as e:
        raise ShadowGeometryError(str(e)) from e
    return intersection if not intersection.is_empty else None


def shadow_overlap_fraction(shadow_geojson: dict,
                            lot_geojson: dict) -> Optional[float]:
    """
    Fraction (0–1) of the subject lot area covered by the shadow polygon.
    0.0 = no overlap; 1.0 = entire lot in shadow.

    None means the fraction COULD NOT BE COMPUTED — never that it is zero.
    Returning 0.0 from the failure path put a fabricated "no overlap" on
    stored reports: 7 of them told a customer they met the ADG solar-access
    test while the recomputed truth was up to 100% of the lot in shadow
    (measured 2026-08-07 over the stored corpus).
    """
    try:
        from shapely.geometry import shape
        lot = shape(lot_geojson)
        lot_area = lot.area
        if lot_area == 0:
            # A fraction OF zero area is undefined, not zero.
            logger.warning("Overlap fraction: lot has zero area")
            return None
        intersection = _shadow_intersection(shadow_geojson, lot_geojson)
        if intersection is None:
            return 0.0
        return round(min(1.0, intersection.area / lot_area), 3)
    except ShadowGeometryError as e:
        logger.warning(f"Overlap fraction unavailable — intersection failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"Overlap fraction unavailable: {e}")
        return None


def shadow_reach_m(shadow_geojson: dict, lot_geojson: dict) -> Optional[float]:
    """
    How far (metres) the shadow penetrates into the subject lot, measured
    from the lot's northern boundary southward.

    0   = shadow doesn't enter the lot.
    lot_depth_m = shadow covers the entire lot.
    None = the penetration could not be computed — NOT that it is zero.

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
    except ShadowGeometryError as e:
        logger.warning(f"shadow_reach_m unavailable — intersection failed: {e}")
        return None
    except Exception as e:
        logger.warning(f"shadow_reach_m unavailable: {e}")
        return None


def shadow_length_m(shadow_geojson: dict, lot_geojson: dict,
                    **_kwargs) -> Optional[float]:
    """
    Backwards-compatible wrapper — now returns shadow_reach_m.
    Old signature accepted (lot_centroid_lng, lot_centroid_lat); new callers
    should use shadow_reach_m directly.
    """
    return shadow_reach_m(shadow_geojson, lot_geojson)


def overlaps_lot(shadow_geojson: dict, lot_geojson: dict) -> Optional[bool]:
    """
    True if the shadow covers ≥OVERLAP_THRESHOLD of the subject lot area.
    A 40% threshold means the rear yard (principal private open space) is
    materially impacted; minor edge shadows at 9am/3pm don't trigger this.

    None when the fraction could not be computed. Never False from an
    uncomputed fraction: `None >= 0.40` would raise, and coercing it to False
    would assert the lot is unaffected on the strength of a failed geometry op.
    """
    fraction = shadow_overlap_fraction(shadow_geojson, lot_geojson)
    if fraction is None:
        return None
    return fraction >= OVERLAP_THRESHOLD


def shadow_on_lot_geojson(shadow_geojson: dict, lot_geojson: dict) -> Optional[dict]:
    """
    Return a GeoJSON FeatureCollection of the shadow clipped to the subject lot.
    Used to render exactly which part of the lot is in shadow — not the full
    pybdshadow polygon (which includes the proxy building footprint).
    Returns None if there is no intersection, and also if one could not be
    computed. Unlike the numeric fields, that conflation is harmless here: this
    is the clipped polygon the map draws, and drawing nothing is the correct
    response to both. The claim-bearing fields are handled above.
    """
    try:
        intersection = _shadow_intersection(shadow_geojson, lot_geojson)
    except ShadowGeometryError as e:
        logger.warning(f"shadow_on_lot_geojson unavailable: {e}")
        return None
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
