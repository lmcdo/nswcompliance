"""
Lot Dimensions Calculator — Python port of frontend lot-dimensions.ts.

Extracts frontage, depth, area from lot geometry polygon rings.
Input: NSW Planning Portal lot geometry (EPSG:3857 Web Mercator rings).
Output: LotDimensions with real-world metres.

Coordinate handling:
- Portal returns rings in EPSG:3857 (Web Mercator, metres at equator).
- Scale correction applied for NSW latitude (~33.87S).
- Shoelace formula on corrected coordinates for area.
- Boundary classification: 4-edge lots use ring order; irregular use bearing heuristic.
"""
from __future__ import annotations

import math
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from services.intelligence_brief import LotDimensions


# NSW average latitude for Web Mercator scale correction
_NSW_LATITUDE = -33.87
_SCALE_FACTOR = 1.0 / math.cos(math.radians(abs(_NSW_LATITUDE)))

# Planning Portal lot API
LOT_API = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi/lot"


def fetch_lot_geometry(prop_id: str) -> Optional[dict]:
    """Fetch lot geometry from NSW Planning Portal.

    Returns the raw geometry dict with 'rings' in EPSG:3857, or None on failure.
    """
    import requests

    try:
        r = requests.get(LOT_API, params={"propId": prop_id}, timeout=15)
        r.raise_for_status()
        data = r.json()
        if data and isinstance(data, list) and len(data) > 0:
            return data[0].get("geometry")
        return None
    except Exception:
        return None


def calculate_lot_dimensions(geometry: Optional[dict]) -> Optional[LotDimensions]:
    """Calculate lot dimensions from Portal geometry.

    Args:
        geometry: dict with 'rings' key containing coordinate arrays in EPSG:3857.

    Returns:
        LotDimensions with area_m2, frontage_m, depth_m populated, or None.
    """
    from services.intelligence_brief import LotDimensions

    if not geometry or not geometry.get("rings"):
        return None

    rings = geometry["rings"]  # noqa: bracket-access — guarded by .get() check above
    if not rings or not rings[0] or len(rings[0]) < 4:
        return None

    outer_ring = rings[0]

    # Convert to real-world metres (scale correction for NSW latitude)
    points = [(x / _SCALE_FACTOR, y / _SCALE_FACTOR) for x, y in outer_ring]

    # Remove closing point if duplicate
    if len(points) > 1 and points[0] == points[-1]:
        points = points[:-1]

    if len(points) < 3:
        return None

    area = _shoelace_area(points)
    boundaries = _extract_boundaries(points)
    _classify_boundaries(boundaries)

    front = next((b for b in boundaries if b["type"] == "front"), None)  # noqa: bracket-access
    rear = next((b for b in boundaries if b["type"] == "rear"), None)  # noqa: bracket-access
    left = next((b for b in boundaries if b["type"] == "side_left"), None)  # noqa: bracket-access
    right = next((b for b in boundaries if b["type"] == "side_right"), None)  # noqa: bracket-access

    frontage = front["length"] if front else None  # noqa: bracket-access
    side_l = left["length"] if left else 0.0  # noqa: bracket-access
    side_r = right["length"] if right else 0.0  # noqa: bracket-access

    if side_l and side_r:
        depth = (side_l + side_r) / 2.0
    elif side_l or side_r:
        depth = side_l or side_r
    else:
        depth = None

    is_corner = False
    if front and rear:
        # Corner lots often have two "front" boundaries (two street-facing sides).
        # Heuristic: if front and rear are similar length and both short relative
        # to sides, it's more likely rectangular. Not attempting corner detection
        # without street data — would need cadastre road-frontage classification.
        pass

    return LotDimensions(
        area_m2=round(area, 1),
        frontage_m=round(frontage, 1) if frontage else None,
        depth_m=round(depth, 1) if depth else None,
        is_corner=is_corner,
    )


def _shoelace_area(points: list[tuple[float, float]]) -> float:
    """Shoelace formula for polygon area in square metres."""
    n = len(points)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += points[i][0] * points[j][1]
        area -= points[j][0] * points[i][1]
    return abs(area) / 2.0


def _extract_boundaries(points: list[tuple[float, float]]) -> list[dict]:
    """Extract boundary segments with length and bearing."""
    n = len(points)
    boundaries = []
    for i in range(n):
        sx, sy = points[i]
        ex, ey = points[(i + 1) % n]
        dx = ex - sx
        dy = ey - sy
        length = math.sqrt(dx * dx + dy * dy)
        bearing = (math.degrees(math.atan2(dx, dy)) + 360) % 360
        boundaries.append({
            "type": "unknown",
            "length": length,
            "bearing": bearing,
            "start": (sx, sy),
            "end": (ex, ey),
        })
    return boundaries


def _classify_boundaries(boundaries: list[dict]) -> None:
    """Classify boundaries as front, rear, side_left, side_right.

    For 4-edge lots: assumes first boundary is front (matches portal ring order).
    For irregular: uses bearing-based heuristic (same as TypeScript version).
    """
    # All bracket access below is on dicts we construct in _extract_boundaries  # noqa: bracket-access
    if len(boundaries) == 4:
        types = ["front", "side_right", "rear", "side_left"]
        for b, t in zip(boundaries, types):
            b["type"] = t  # noqa: bracket-access
        return

    # Irregular lots: bearing-based classification
    centroid_y = sum(b["start"][1] for b in boundaries) / len(boundaries)  # noqa: bracket-access
    centroid_x = sum(b["start"][0] for b in boundaries) / len(boundaries)  # noqa: bracket-access

    for b in boundaries:
        mid_y = (b["start"][1] + b["end"][1]) / 2.0  # noqa: bracket-access
        mid_x = (b["start"][0] + b["end"][0]) / 2.0  # noqa: bracket-access
        bearing = b["bearing"]  # noqa: bracket-access

        # Roughly horizontal (E-W): bearing 45-135 or 225-315
        is_horizontal = (45 <= bearing < 135) or (225 <= bearing < 315)

        if is_horizontal:
            b["type"] = "front" if mid_y < centroid_y else "rear"  # noqa: bracket-access
        else:
            b["type"] = "side_left" if mid_x < centroid_x else "side_right"  # noqa: bracket-access
