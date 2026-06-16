"""
Reverse Shadow Model — models shadow cast BY neighbouring lots'
maximum legal building envelopes ONTO the subject lot.

The flip of shadow_model.py: instead of 'does my building shadow
the neighbour?', this answers 'if my neighbour builds to their max
height, when does my backyard go dark?'

See TIER1_BUILD_SPEC.md §4, §A1.8 (multi-directional).
"""
import logging
import math
from typing import Literal, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Which neighbour direction matters for each time-of-day scenario
# ---------------------------------------------------------------------------

NEIGHBOUR_DIRECTIONS: dict[str, str] = {
    "jun21_9am": "east",    # Eastern neighbour's shadow falls west onto subject
    "jun21_12pm": "north",  # Northern neighbour's shadow falls south onto subject
    "jun21_3pm": "west",    # Western neighbour's shadow falls east onto subject
}

# Shadow scenarios from shadow_model.py (Jun 21 only — ADG compliance window)
SHADOW_SCENARIO_DESCRIPTIONS = {
    "jun21_9am": "Winter solstice 9am — shadow from east",
    "jun21_12pm": "Winter solstice noon — shadow from north",
    "jun21_3pm": "Winter solstice 3pm — shadow from west",
}


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class NeighbourShadowResult(BaseModel):
    scenario: str
    scenario_description: str
    neighbour_direction: str
    neighbour_height_m: float
    neighbour_footprint_area_m2: float
    shadow_on_subject_m2: float
    subject_lot_area_m2: float
    shadow_fraction: float  # 0.0 to 1.0
    shadow_polygon_geojson: Optional[dict] = None


class SolarAccessRisk(BaseModel):
    subject_lot_area_m2: float
    scenarios: list[NeighbourShadowResult]
    worst_case_fraction: float
    adg_compliant: bool  # 2hrs solar access 9am-3pm Jun 21
    risk_level: Literal["low", "moderate", "high"]
    consumer_summary: str


# ---------------------------------------------------------------------------
# Neighbour proxy estimation
# ---------------------------------------------------------------------------

def estimate_neighbour_proxy(
    subject_lot_geojson: dict,
    direction: str,
) -> dict:
    """Create a proxy lot polygon shifted in the given direction from subject.

    Extends northern_neighbour_proxy() pattern to east/west.
    Returns a GeoJSON Polygon (bounding-box based).
    """
    try:
        from shapely.geometry import shape, mapping, box
        from shapely.affinity import translate

        lot = shape(subject_lot_geojson)
        bounds = lot.bounds  # (minx, miny, maxx, maxy)
        width = bounds[2] - bounds[0]
        height = bounds[3] - bounds[1]
        depth_m = height * 111_000

        # Approximate degree offsets
        lat_offset = depth_m / 111_000
        lng_offset = (width * 111_000 * math.cos(math.radians((bounds[1] + bounds[3]) / 2))) / 111_000

        lot_bbox = box(bounds[0], bounds[1], bounds[2], bounds[3])

        if direction == "north":
            shifted = translate(lot_bbox, xoff=0.0, yoff=lat_offset)
        elif direction == "east":
            shifted = translate(lot_bbox, xoff=width, yoff=0.0)
        elif direction == "west":
            shifted = translate(lot_bbox, xoff=-width, yoff=0.0)
        else:
            logger.warning("Unknown direction %s, defaulting to north", direction)
            shifted = translate(lot_bbox, xoff=0.0, yoff=lat_offset)

        return mapping(shifted)
    except ImportError:
        logger.warning("shapely not available — returning subject lot as proxy")
        return subject_lot_geojson
    except Exception as e:
        logger.warning("estimate_neighbour_proxy failed: %s", e)
        return subject_lot_geojson


# ---------------------------------------------------------------------------
# Core shadow modelling
# ---------------------------------------------------------------------------

def model_neighbour_shadow_on_subject(
    subject_lot_geojson: dict,
    neighbour_lot_geojson: Optional[dict],
    neighbour_height_m: float,
    direction: str,
    scenario: str = "jun21_12pm",
) -> NeighbourShadowResult:
    """Model shadow from a neighbour's max envelope onto the subject lot.

    Uses shadow_model.model_shadow() with the neighbour's geometry and height,
    then intersects with the subject lot to get the shadow fraction.
    """
    description = SHADOW_SCENARIO_DESCRIPTIONS.get(scenario, scenario)

    # Use proxy if no real neighbour geometry
    if neighbour_lot_geojson is None:
        neighbour_lot_geojson = estimate_neighbour_proxy(subject_lot_geojson, direction)

    try:
        from shapely.geometry import shape
        from services.shadow_model import model_shadow, shadow_overlap_fraction

        subject_lot = shape(subject_lot_geojson)
        subject_area = subject_lot.area * (111_000 ** 2)  # Rough deg² → m² for Sydney
        neighbour_lot = shape(neighbour_lot_geojson)
        neighbour_area = neighbour_lot.area * (111_000 ** 2)

        # Model shadow cast by neighbour's max building
        shadow_geojson = model_shadow(neighbour_lot_geojson, neighbour_height_m, scenario)

        # Intersect with subject lot
        fraction = shadow_overlap_fraction(shadow_geojson, subject_lot_geojson)

        # Get shadow-on-subject geometry for rendering
        from services.shadow_model import shadow_on_lot_geojson
        shadow_on_subject = shadow_on_lot_geojson(shadow_geojson, subject_lot_geojson)

        return NeighbourShadowResult(
            scenario=scenario,
            scenario_description=description,
            neighbour_direction=direction,
            neighbour_height_m=neighbour_height_m,
            neighbour_footprint_area_m2=round(neighbour_area, 1),
            shadow_on_subject_m2=round(fraction * subject_area, 1),
            subject_lot_area_m2=round(subject_area, 1),
            shadow_fraction=fraction,
            shadow_polygon_geojson=shadow_on_subject,
        )
    except ImportError:
        logger.warning("pybdshadow/shapely not available — returning zero shadow")
        return NeighbourShadowResult(
            scenario=scenario,
            scenario_description=description,
            neighbour_direction=direction,
            neighbour_height_m=neighbour_height_m,
            neighbour_footprint_area_m2=0,
            shadow_on_subject_m2=0,
            subject_lot_area_m2=0,
            shadow_fraction=0.0,
        )
    except Exception as e:
        logger.warning("model_neighbour_shadow_on_subject failed: %s", e)
        return NeighbourShadowResult(
            scenario=scenario,
            scenario_description=description,
            neighbour_direction=direction,
            neighbour_height_m=neighbour_height_m,
            neighbour_footprint_area_m2=0,
            shadow_on_subject_m2=0,
            subject_lot_area_m2=0,
            shadow_fraction=0.0,
        )


def assess_solar_access_risk(
    subject_lot_geojson: dict,
    neighbour_lots: Optional[dict[str, dict]] = None,
    neighbour_height_m: float = 9.0,
) -> SolarAccessRisk:
    """Comprehensive solar access risk assessment.

    Runs all 3 Jun-21 scenarios (9am, noon, 3pm) with the appropriate
    neighbour direction for each. Uses proxy lots if real neighbours
    not provided.

    Args:
        subject_lot_geojson: Subject lot GeoJSON polygon
        neighbour_lots: Dict of {direction: lot_geojson} for real neighbours
        neighbour_height_m: Max building height for neighbours (from constraint arithmetic)
    """
    if neighbour_lots is None:
        neighbour_lots = {}

    try:
        from shapely.geometry import shape
        subject_area_m2 = shape(subject_lot_geojson).area * (111_000 ** 2)
    except Exception:
        subject_area_m2 = 0

    scenarios: list[NeighbourShadowResult] = []
    for scenario_key, direction in NEIGHBOUR_DIRECTIONS.items():
        neighbour_geojson = neighbour_lots.get(direction)
        result = model_neighbour_shadow_on_subject(
            subject_lot_geojson=subject_lot_geojson,
            neighbour_lot_geojson=neighbour_geojson,
            neighbour_height_m=neighbour_height_m,
            direction=direction,
            scenario=scenario_key,
        )
        scenarios.append(result)

    worst_fraction = max((s.shadow_fraction for s in scenarios), default=0.0)

    # ADG compliance: 2hrs solar access 9am-3pm Jun 21
    # If worst case covers >50% of the lot, solar access is at risk
    # Simplified check: if noon (primary) fraction < 0.5 → likely compliant
    noon_result = next((s for s in scenarios if s.scenario == "jun21_12pm"), None)
    noon_fraction = noon_result.shadow_fraction if noon_result else 0.0

    # ADG: need at least 2hrs of the 6hr window (9am-3pm) with solar access
    # If shadow fraction < 0.5 at noon, likely 2+ hrs of access
    adg_ok = noon_fraction < 0.50

    if worst_fraction < 0.20:
        risk = "low"
    elif worst_fraction < 0.50:
        risk = "moderate"
    else:
        risk = "high"

    summary = _make_risk_summary(risk, worst_fraction, neighbour_height_m, scenarios)

    return SolarAccessRisk(
        subject_lot_area_m2=round(subject_area_m2, 1),
        scenarios=scenarios,
        worst_case_fraction=worst_fraction,
        adg_compliant=adg_ok,
        risk_level=risk,
        consumer_summary=summary,
    )


def _make_risk_summary(
    risk: str,
    worst_fraction: float,
    height_m: float,
    scenarios: list[NeighbourShadowResult],
) -> str:
    """Generate factual consumer summary. No banned liability words."""
    pct = round(worst_fraction * 100)
    worst = max(scenarios, key=lambda s: s.shadow_fraction) if scenarios else None
    when = worst.scenario_description if worst else "winter solstice"

    if risk == "low":
        return (
            f"At maximum permissible building height ({height_m:.0f}m), "
            f"neighbouring lots would cast shadow over approximately {pct}% "
            f"of your lot at the worst-case scenario ({when})."
        )
    elif risk == "moderate":
        return (
            f"At maximum permissible building height ({height_m:.0f}m), "
            f"neighbouring lots could shadow approximately {pct}% of your "
            f"property at {when}, which may affect afternoon sun in rear areas."
        )
    else:
        return (
            f"At maximum permissible building height ({height_m:.0f}m), "
            f"neighbouring lots could shadow approximately {pct}% of your "
            f"property at {when}, potentially reducing solar access to "
            f"rear yard and living areas during winter months."
        )
