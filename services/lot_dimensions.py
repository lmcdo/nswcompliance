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
    from services.constraint_models import LotDimensions


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
    from services.constraint_models import LotDimensions

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

    # Battleaxe (flag-lot) detection — precisely the shape class the rectangle
    # model rejects (fills <60% of its OBB), which previously left width None
    # and made every width-gated eligibility form "unconfirmed" (38 Park Rd
    # Bowral: 16.3 m handle on a 70 m head read as "frontage not mapped").
    ba = _detect_battleaxe(points)
    if ba:
        lot_type = "battleaxe"
    elif len(points) == 4 and frontage is not None:
        lot_type = "rectangular"
    else:
        lot_type = "irregular"

    return LotDimensions(
        area_m2=round(area, 1),
        frontage_m=round(frontage, 1) if frontage else None,
        depth_m=round(depth, 1) if depth else None,
        is_corner=False,
        # _frontage_depth_obb returns (None, None) only when the shape defeats
        # the rectangle model — carry that so the UI can say WHY dims are null.
        irregular=frontage is None,
        lot_type=lot_type,
        battleaxe_access_way_width_m=ba.get("access_way_width_m") if ba else None,
        battleaxe_access_way_length_m=ba.get("access_way_length_m") if ba else None,
        battleaxe_main_lot_width_m=ba.get("main_lot_width_m") if ba else None,
        battleaxe_main_lot_area_m2=ba.get("main_lot_area_m2") if ba else None,
    )


def eligibility_lot_width(dims: Optional["LotDimensions"]) -> Optional[float]:
    """Battleaxe-aware lot width for SEPP/LMR eligibility tests.

    prior-art-checked: Python port of lib/geometry/effective-lot-width.ts
    battleaxeAwareLotWidth — for a battleaxe (flag) lot the cadastral frontage
    is the access HANDLE; width-based minimum-lot-width tests must use the
    developable width of the head (main lot). Falls back to frontage_m; None
    when nothing usable is present (callers keep the engine's unconfirmed path).
    """
    if dims is None:
        return None
    if (
        dims.lot_type == "battleaxe"
        and dims.battleaxe_main_lot_width_m
        and dims.battleaxe_main_lot_width_m > 0
    ):
        return dims.battleaxe_main_lot_width_m
    return dims.frontage_m


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


# ---------------------------------------------------------------------------
# Battleaxe (flag-lot) detection — width-profile analysis.
#
# prior-art-checked: direct Python port of frontend
# lib/geometry/lot-shape-analysis.ts detectBattleaxeLot (thresholds kept
# VERBATIM — they are tuned and test-backed there, and produced the verified
# 16.31 m handle / 70.09 m head result for 38 Park Rd Bowral in Verify).
# Slice the lot perpendicular to its long axis, look for a sustained narrow
# run (the handle) against a wide head.
# ---------------------------------------------------------------------------

_HANDLE_TO_HEAD_MAX_RATIO = 0.40   # handle < 40% of head width
_MIN_HEAD_WIDTH = 9.0              # metres
_MAX_NARROW_PERCENTAGE = 0.65      # handle is a minority of lot length
_MIN_WIDTH_RATIO = 0.65            # min/max width contrast required
_NUM_SLICES = 20
_MIN_CONSECUTIVE_NARROW = 3


def _detect_battleaxe(points: list[tuple[float, float]]) -> Optional[dict]:
    """Detect a battleaxe lot from real-metre polygon points.

    Returns {access_way_width_m, access_way_length_m, main_lot_width_m,
    main_lot_area_m2, confidence} or None when the lot is not a battleaxe
    (or has too few vertices for the shape to exist).
    """
    if len(points) < 6:
        return None  # battleaxe needs 6+ vertices (L-shape minimum)

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    bbox_w, bbox_h = max_x - min_x, max_y - min_y
    if bbox_w <= 0 or bbox_h <= 0:
        return None
    is_vertical = bbox_h > bbox_w
    total_length = bbox_h if is_vertical else bbox_w

    widths: list[float] = []
    for i in range(_NUM_SLICES):
        t = (i + 0.5) / _NUM_SLICES
        if is_vertical:
            w = _width_at(points, min_y + t * bbox_h, axis="y")
        else:
            w = _width_at(points, min_x + t * bbox_w, axis="x")
        if w > 0:
            widths.append(w)
    if len(widths) < _NUM_SLICES:
        return None

    min_w, max_w = min(widths), max(widths)
    if max_w <= 0:
        return None
    narrow_threshold = max_w * _HANDLE_TO_HEAD_MAX_RATIO

    narrow = [w < narrow_threshold for w in widths]
    narrow_pct = sum(narrow) / len(widths)
    consecutive = 0
    has_consecutive = False
    for is_n in narrow:
        consecutive = consecutive + 1 if is_n else 0
        if consecutive >= _MIN_CONSECUTIVE_NARROW:
            has_consecutive = True
            break

    is_battleaxe = (
        0 < min_w < narrow_threshold
        and max_w >= _MIN_HEAD_WIDTH
        and (min_w / max_w) < _MIN_WIDTH_RATIO
        and narrow_pct < _MAX_NARROW_PERCENTAGE
        and has_consecutive
    )
    if not is_battleaxe:
        return None

    # Handle sits at whichever end the narrow run is longer.
    leading = 0
    for is_n in narrow:
        if not is_n:
            break
        leading += 1
    trailing = 0
    for is_n in reversed(narrow):
        if not is_n:
            break
        trailing += 1
    handle_ratio = max(leading, trailing) / len(widths)
    handle_length = handle_ratio * total_length
    head_length = total_length - handle_length

    head_widths = [w for w in widths if w >= narrow_threshold]
    main_lot_area = (
        (sum(head_widths) / len(head_widths)) * head_length if head_widths else 0.0
    )

    # Confidence: contrast + clear narrow section + typical dimensions.
    confidence = 0.5
    ratio = min_w / max_w
    if ratio < 0.3:
        confidence += 0.2
    elif ratio < 0.5:
        confidence += 0.1
    if narrow_pct < 0.3:
        confidence += 0.15
    elif narrow_pct < 0.4:
        confidence += 0.1
    if 3 <= min_w <= 5:
        confidence += 0.1
    if 10 <= max_w <= 20:
        confidence += 0.05

    return {
        "access_way_width_m": round(min_w, 2),
        "access_way_length_m": round(handle_length, 2),
        "main_lot_width_m": round(max_w, 2),
        "main_lot_area_m2": round(main_lot_area),
        "confidence": min(0.95, confidence),
    }


def _width_at(points: list[tuple[float, float]], level: float, axis: str) -> float:
    """Polygon extent at a slice: width at y=level (axis='y') or height at x=level."""
    a, b = (1, 0) if axis == "y" else (0, 1)
    intersections: list[float] = []
    n = len(points)
    for i in range(n):
        p1, p2 = points[i], points[(i + 1) % n]
        c1, c2 = p1[a], p2[a]
        if (c1 <= level < c2) or (c2 <= level < c1):
            t = (level - c1) / (c2 - c1)
            intersections.append(p1[b] + t * (p2[b] - p1[b]))
    if len(intersections) < 2:
        return 0.0
    intersections.sort()
    return intersections[-1] - intersections[0]


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
