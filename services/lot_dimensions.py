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
    if area <= 0:
        return None

    # Frontage/depth from the oriented bounding box (minimum rotated rectangle).
    # Robust to vertex count and ring order — unlike the old "ring[0] is the
    # frontage" heuristic, which misclassified real cadastre lots (e.g. a 312 m²
    # lot reported as 35 m × 7.5 m).
    frontage, depth = _frontage_depth_obb(points, area)

    return LotDimensions(
        area_m2=round(area, 1),
        frontage_m=round(frontage, 1) if frontage else None,
        depth_m=round(depth, 1) if depth else None,
        is_corner=False,
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


def _frontage_depth_obb(
    points: list[tuple[float, float]],
    polygon_area: float,
) -> tuple[Optional[float], Optional[float]]:
    """Frontage/depth from the oriented bounding box (minimum rotated rectangle).

    Returns (frontage, depth) where frontage = the shorter side and depth = the
    longer side. NB: shorter-side-is-frontage is a HEURISTIC — correct for typical
    deeper-than-wide lots, but not for wide/corner lots. The accurate frontage is
    the lot edge that faces a road (road-frontage detection via the road network);
    that is a planned upgrade. Here we return clean *dimensions*; the assignment is
    the heuristic.

    Returns (None, None) when the lot is too irregular for a rectangle to be
    representative (so the engine's area-based estimate runs). Pure Python — no
    external geometry dependency (shapely is optional in this stack).
    """
    rect = _min_area_rect(points)
    if not rect:
        return None, None
    side1, side2 = rect
    if side1 <= 0 or side2 <= 0:
        return None, None
    # If the polygon fills <60% of its bounding rectangle it is too irregular
    # (L-shape, battle-axe handle) for frontage/depth to be meaningful — defer
    # to the engine's area-based estimate downstream.
    if (polygon_area / (side1 * side2)) < 0.6:
        return None, None
    return (min(side1, side2), max(side1, side2))


def _convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    """Andrew's monotone-chain convex hull (counter-clockwise, no repeat)."""
    pts = sorted(set(points))
    if len(pts) <= 2:
        return pts

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    upper: list[tuple[float, float]] = []
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    return lower[:-1] + upper[:-1]


def _min_area_rect(points: list[tuple[float, float]]) -> Optional[tuple[float, float]]:
    """Minimum-area bounding rectangle side lengths via rotating calipers.

    The min-area rectangle of a convex polygon always has one side collinear with
    a hull edge, so we test each edge orientation and keep the smallest-area box.
    Returns (side_a, side_b) in metres, or None if degenerate.
    """
    hull = _convex_hull(points)
    n = len(hull)
    if n < 3:
        return None

    best: Optional[tuple[float, float, float]] = None  # (area, w, h)
    for i in range(n):
        ax, ay = hull[i]
        bx, by = hull[(i + 1) % n]
        ex, ey = bx - ax, by - ay
        elen = math.hypot(ex, ey)
        if elen == 0:
            continue
        ux, uy = ex / elen, ey / elen      # edge direction (unit)
        vx, vy = -uy, ux                   # perpendicular (unit)
        min_u = min_v = math.inf
        max_u = max_v = -math.inf
        for px, py in hull:
            du = px * ux + py * uy
            dv = px * vx + py * vy
            min_u, max_u = min(min_u, du), max(max_u, du)
            min_v, max_v = min(min_v, dv), max(max_v, dv)
        w, h = max_u - min_u, max_v - min_v
        area = w * h
        if best is None or area < best[0]:
            best = (area, w, h)

    if best is None:
        return None
    return best[1], best[2]
