"""Street frontage and lot width measured from the road, not the lot's shape.

prior-art-checked: Python port of frontend-nextjs/lib/geometry/street-frontage.ts
(and the road query in corner-lot-detection.ts). No Python road-frontage code
existed: services/lot_dimensions.py takes the shorter side of the minimum-area
rectangle, which overstates the street edge on a wedge lot (6 Berrigan St Winston
Hills: rectangle 22.4 m, street edge 13.3 m).

The Housing SEPP minimums are "a minimum lot width at the front building line".
For each named road the lot touches, the lot's width is measured at every
distance back from that road edge. Two numbers carry the answer:
  min_front_half_m  narrowest width from the road edge to halfway back;
  max_all_m         widest width anywhere.
Between them the answer is "depends on where the building sits", never guessed.
A lot edge counts as road frontage when at least half of it lies within
EDGE_TOLERANCE_M of a road-corridor boundary running within EDGE_MAX_ANGLE_DEG of
parallel. Unnamed road parcels (rear lanes) are never the front.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Optional

from services.lot_dimensions import _scale_factor_for_ring, _usable_ring

logger = logging.getLogger(__name__)

EDGE_TOLERANCE_M = 2.5
EDGE_MAX_ANGLE_DEG = 30.0
EDGE_MIN_FRACTION = 0.5
PROFILE_STEP_M = 0.5
GRID_M = 0.1  # each grid size MUST divide PROFILE_STEP_M exactly
GRID_LARGE_M = 0.25
LARGE_LOT_M2 = 2000.0
WIDTH_MARGIN_M = 0.3
ROAD_SEARCH_PAD_M = 20.0
ROAD_QUERY_URL = (
    "https://portal.spatial.nsw.gov.au/server/rest/services/"
    "NSW_Land_Parcel_Property_Theme_multiCRS/FeatureServer/5/query"
)

Pt = tuple[float, float]
Seg = tuple[Pt, Pt]


@dataclass
class RoadWidthRange:
    """Frontage and width range for one named road."""

    road: str
    frontage_m: float
    min_front_half_m: float
    max_all_m: float
    depth_m: float


@dataclass
class StreetFrontage:
    """Result: status is measured, not_identified or unavailable."""

    status: str
    roads: list[RoadWidthRange] = field(default_factory=list)
    unnamed_road_edge_m: float = 0.0
    error: Optional[str] = None


def _seg_dist(p: Pt, a: Pt, b: Pt) -> float:
    dx, dy = b[0] - a[0], b[1] - a[1]
    len2 = dx * dx + dy * dy
    t = 0.0 if len2 == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / len2))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def _angle_between(a: Seg, b: Seg) -> float:
    t1 = math.atan2(a[1][1] - a[0][1], a[1][0] - a[0][0])
    t2 = math.atan2(b[1][1] - b[0][1], b[1][0] - b[0][0])
    d = abs(math.degrees(t1 - t2)) % 180
    return min(d, 180 - d)


def _inside(p: Pt, ring: list[Pt]) -> bool:
    c = False
    j = len(ring) - 1
    for i in range(len(ring)):
        xi, yi = ring[i]
        xj, yj = ring[j]
        if (yi > p[1]) != (yj > p[1]) and p[0] < (xj - xi) * (p[1] - yi) / (yj - yi) + xi:
            c = not c
        j = i
    return c


def _segments_of(ring: list[Pt]) -> list[Seg]:
    return [(ring[i], ring[i + 1]) for i in range(len(ring) - 1)]


def _edge_runs_along(edge: Seg, road: list[Seg]) -> bool:
    """True when at least EDGE_MIN_FRACTION of the lot edge runs alongside a road segment."""
    n = 40
    hits = 0
    for i in range(n):
        t = (i + 0.5) / n
        p = (edge[0][0] + (edge[1][0] - edge[0][0]) * t, edge[0][1] + (edge[1][1] - edge[0][1]) * t)
        best: Optional[Seg] = None
        best_d = math.inf
        for s in road:
            d = _seg_dist(p, s[0], s[1])
            if d < best_d:
                best_d, best = d, s
        if best is not None and best_d < EDGE_TOLERANCE_M and _angle_between(edge, best) <= EDGE_MAX_ANGLE_DEG:
            hits += 1
    return hits / n >= EDGE_MIN_FRACTION


def _width_profile(ring: list[Pt], road_edges: list[Seg], area_m2: float) -> list[tuple[float, float]]:
    """(distance, width) pairs: lot area between d and d+step from the road, over step."""
    grid = GRID_LARGE_M if area_m2 > LARGE_LOT_M2 else GRID_M
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    counts: dict[int, int] = {}
    i = 0
    while min_x + grid / 2 + i * grid < max_x:
        x = min_x + grid / 2 + i * grid
        i += 1
        j = 0
        while min_y + grid / 2 + j * grid < max_y:
            y = min_y + grid / 2 + j * grid
            j += 1
            if not _inside((x, y), ring):
                continue
            d = min(_seg_dist((x, y), s[0], s[1]) for s in road_edges)
            b = int(d // PROFILE_STEP_M)
            counts[b] = counts.get(b, 0) + 1
    return [(b * PROFILE_STEP_M, counts[b] * grid * grid / PROFILE_STEP_M) for b in sorted(counts)]


def _edge_len(e: Seg) -> float:
    return math.hypot(e[1][0] - e[0][0], e[1][1] - e[0][1])


def measure_street_frontage(lot_ring_3857: object, roads: list[dict]) -> StreetFrontage:
    """Street frontage per named road and the lot's width range back from each.

    Args:
        lot_ring_3857: outer ring of the lot, EPSG:3857 [[x, y], ...].
        roads: road-corridor polygons, each {"name": str | None, "rings": [...]},
            in the same coordinate system.

    Returns:
        StreetFrontage; status "unavailable" when the ring is unusable.
    """
    raw = _usable_ring(lot_ring_3857)
    if not raw or len(raw) < 4:
        return StreetFrontage("unavailable", error="unusable lot ring")
    scale = _scale_factor_for_ring(raw)

    def to_m(ring: list) -> list[Pt]:
        return [(float(p[0]) / scale, float(p[1]) / scale) for p in ring]

    ring = to_m(raw)
    lot_edges = _segments_of(ring)
    area = abs(sum(a[0] * b[1] - b[0] * a[1] for a, b in lot_edges)) / 2

    by_road: dict[str, set[Seg]] = {}  # a set: one road can arrive as several parcels
    unnamed = 0.0
    for road in roads or []:
        road_segs: list[Seg] = []
        for r in road.get("rings") or []:
            ok = _usable_ring(r)
            if ok:
                road_segs.extend(_segments_of(to_m(ok)))
        if not road_segs:
            continue
        name = (road.get("name") or "").strip() or None
        for edge in lot_edges:
            if not _edge_runs_along(edge, road_segs):
                continue
            if name is None:
                unnamed += _edge_len(edge)
                continue
            by_road.setdefault(name, set()).add(edge)

    out: list[RoadWidthRange] = []
    for name in sorted(by_road, key=str.lower):
        edges = list(by_road[name])
        prof = _width_profile(ring, edges, area)
        if not prof:
            continue
        depth = prof[-1][0] + PROFILE_STEP_M
        front = [w for d, w in prof if d < depth / 2]
        out.append(RoadWidthRange(
            road=name,
            frontage_m=round(sum(_edge_len(e) for e in edges), 2),
            min_front_half_m=round(min(front), 2),
            max_all_m=round(max(w for _, w in prof), 2),
            depth_m=round(depth, 2),
        ))
    return StreetFrontage("measured" if out else "not_identified", out, round(unnamed, 2))


def width_verdict(sf: Optional[StreetFrontage], required_m: float) -> str:
    """'meets' | 'below' | 'depends' for a minimum width at the front building line.

    A corner lot must give the same answer from every named road, else 'depends'.
    """
    if sf is None or sf.status != "measured" or not sf.roads:
        return "depends"
    each = []
    for r in sf.roads:
        if r.min_front_half_m >= required_m + WIDTH_MARGIN_M:
            each.append("meets")
        elif r.max_all_m < required_m - WIDTH_MARGIN_M:
            each.append("below")
        else:
            each.append("depends")
    return each[0] if all(v == each[0] for v in each) else "depends"


def width_range(sf: Optional[StreetFrontage]) -> Optional[tuple[float, float]]:
    """(narrowest front-half width, widest width) over all roads, or None."""
    if sf is None or sf.status != "measured" or not sf.roads:
        return None
    return (min(r.min_front_half_m for r in sf.roads), max(r.max_all_m for r in sf.roads))


def fetch_nearby_roads(geometry: dict) -> Optional[list[dict]]:
    """Road-corridor polygons within ROAD_SEARCH_PAD_M of the lot (EPSG:3857), or None on any failure."""
    import requests

    try:
        ring = _usable_ring(((geometry or {}).get("rings") or [None])[0])
        if not ring:
            return None
        pad = ROAD_SEARCH_PAD_M * _scale_factor_for_ring(ring)
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        env = f"{min(xs) - pad},{min(ys) - pad},{max(xs) + pad},{max(ys) + pad}"
        resp = requests.get(ROAD_QUERY_URL, params={
            "geometry": env, "geometryType": "esriGeometryEnvelope",
            "inSR": 3857, "outSR": 3857, "spatialRel": "esriSpatialRelIntersects",
            "outFields": "roadnamelabel", "returnGeometry": "true", "f": "json",
        }, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        if not isinstance(data, dict) or data.get("error") or not isinstance(data.get("features"), list):
            logger.warning("road query returned no usable features: %s", str(data)[:200])
            return None
        return [
            {"name": (f.get("attributes") or {}).get("roadnamelabel"),
             "rings": (f.get("geometry") or {}).get("rings") or []}
            for f in data.get("features") or [] if (f.get("geometry") or {}).get("rings")
        ]
    except Exception as e:
        logger.warning("road corridor fetch failed: %s", e)
        return None


def street_frontage_for_geometry(geometry: Optional[dict]) -> StreetFrontage:
    """Fetch roads near the lot and measure; status 'unavailable' when the fetch fails."""
    rings = (geometry or {}).get("rings")
    if not rings or not rings[0]:
        return StreetFrontage("unavailable", error="no lot geometry")
    roads = fetch_nearby_roads(geometry)  # type: ignore[arg-type]
    if roads is None:
        return StreetFrontage("unavailable", error="road data unavailable")
    return measure_street_frontage(rings[0], roads)
