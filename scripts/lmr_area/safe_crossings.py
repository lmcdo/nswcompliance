"""Safe-crossing rule for the low-and-mid-rise walking-distance builder.

The law (Housing SEPP Sch 10, p128) measures the shortest route "that may be safely walked by a pedestrian using, as far as
reasonably practicable, public footpaths and pedestrian crossings". The original builder joins every OpenStreetMap way that shares a
node, so a route could cross a busy road anywhere two ways touch. That tends to give a walk SHORTER than a safe one (planner feedback,
scope: ~/.claude/plans/ce-walk-safe-crossings-SCOPE-2026-11-19.md).

The rule, as built and measured on real Pymble data (the first version, which removed roads that have a footpath beside them, left 43% of
places within 800 m unreachable because the footpaths there only join up through the road; it was dropped):

  Rule 1 (two sides)  A busy road is modelled as TWO lines, one per side. A footpath or side street joins the line on its own side. The two lines join
      only at a signalised, zebra or marked crossing (or a signalised junction). Walking ALONG a busy road on your own side stays possible.
  Rule 2 (unmarked crossings)  A mapped crossing that is not a signalised, zebra or marked type is removed when it crosses a busy road.
  Everything else, including crossing a low-speed street at an ordinary junction, is unchanged. With safe=False the graph is exactly the
  original one.

Three-state contract: build_graph never raises on bad OpenStreetMap data and never falls back silently. Malformed elements are skipped and
counted in stats; an unexpected failure returns a GraphBuild with `error` set and an empty graph, and the caller must stop.

The surface the engine reads must not contain the busy-road lines themselves: both sides' copies sit at the same coordinates, and the
lookup would take the nearer side's distance for a lot on the far side. The builder stores only nodes that are NOT busy-road copies
(see GraphBuild.is_line_copy).
"""
# prior-art-checked: 2026-11-19. Searched services/ scripts/ src/ tests/ for traffic_signals, maxspeed, highway=crossing, safe crossing
# (only a comment in services/lmr_area_decision.py mentions "safely walked"); frontend app/ and components/ for "crossing" (none);
# plans and memory indexes (only the scope and the Ron Gounder feedback note). Called by scripts/lmr_area/build_walk_surfaces.py.
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Any, Iterable

import networkx as nx
from shapely.geometry import LineString
from shapely.strtree import STRtree

RULE_NAME = "safe-crossings-v2"

# Roads: ways a vehicle drives on. Everything else the query returns (footway, path, steps, cycleway, pedestrian, track...) is a path.
ROAD_CLASSES = frozenset({
    "trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link", "tertiary", "tertiary_link",
    "unclassified", "residential", "living_street", "service",
})
# Always busy: main roads carry fast, heavy traffic whatever their signed speed.
ALWAYS_BUSY_CLASSES = frozenset({"trunk", "trunk_link", "primary", "primary_link", "secondary", "secondary_link"})
# Busy when fast, and ALSO when the speed is not mapped. Safe answer, not the convenient one: an unmapped tertiary road is treated as
# busy so the route cannot cross it casually. Costs some extra detours; measured at Pymble (2 of 129 busy-road ways untagged).
SPEED_SENSITIVE_CLASSES = frozenset({"tertiary", "tertiary_link"})
BUSY_SPEED_KMH = 60                  # the scope's threshold: 60 km/h and over is a road a pedestrian should not cross freely
WALK_SPEED_KMH = 10                  # maxspeed=walk
MPH_TO_KMH = 1.609

# OpenStreetMap crossing=* values that are a formal pedestrian crossing. 'uncontrolled' is OSM's value for a marked crossing without
# lights. 'unmarked', 'no' and a missing value are NOT accepted: 33 of 98 crossing nodes at Pymble carry no type, so an untyped crossing
# is not proof of a safe one.
ALLOWED_CROSSING_VALUES = frozenset({"traffic_signals", "zebra", "marked", "uncontrolled"})
SIGNALISED_JUNCTION_TAG = "traffic_signals"   # highway=traffic_signals on a node: assumed to have a pedestrian phase (counted in stats, to be checked with planners)

CROSSING_TO_ROAD_MATCH_M = 4.0       # a mapped crossing this close to a busy road's line is treated as crossing that road
SIDE_MIN_SIN = 0.17                  # a path leaving a busy-road node within about 10 degrees of the road's own direction is "along the road", not on a side
MAX_SKIP_NOTES = 20                  # keep the first few skip reasons; counts are always exact


@dataclass
class GraphBuild:
    """Result of build_graph. error is None on success; on failure graph is empty and the caller must stop."""
    graph: nx.Graph
    coords: dict[Any, tuple[float, float]]            # graph node id -> metric (x, y); includes the two side copies at busy-road nodes
    groups: dict[Any, list[Any]]                      # physical OSM node id -> every graph node id at that spot
    stats: dict[str, Any] = field(default_factory=dict)
    rule: str = "original"
    error: str | None = None

    @staticmethod
    def is_line_copy(node_id: Any) -> bool:
        """True for a side copy of a busy-road node. These must not be written to a surface (see module docstring)."""
        return isinstance(node_id, tuple)


def parse_speed_kmh(raw: Any) -> int | None:
    """Speed in km/h from an OSM maxspeed value, or None when it cannot be read. '50;60' gives the higher figure (safer)."""
    if not isinstance(raw, str):
        return None
    low = raw.strip().lower()
    if low == "walk":
        return WALK_SPEED_KMH
    nums = [int(n) for n in re.findall(r"\d+", low)]
    if not nums:
        return None
    value = max(nums)
    return round(value * MPH_TO_KMH) if "mph" in low else value


def is_busy(tags: dict[str, str] | None) -> bool:
    """True when a road is one a pedestrian may cross only at a signalised, zebra or marked crossing."""
    tags = tags or {}
    highway = tags.get("highway")
    if highway not in ROAD_CLASSES:
        return False
    if highway in ALWAYS_BUSY_CLASSES:
        return True
    speed = parse_speed_kmh(tags.get("maxspeed"))
    if speed is not None:
        return speed >= BUSY_SPEED_KMH
    return highway in SPEED_SENSITIVE_CLASSES


def crossing_type_ok(tags: dict[str, str] | None) -> bool:
    """True when the tags say this is a signalised, zebra or marked crossing."""
    tags = tags or {}
    return tags.get("crossing") in ALLOWED_CROSSING_VALUES or tags.get("crossing:signals") == "yes"


def allowed_crossing_node(tags: dict[str, str] | None) -> bool:
    """A node where a pedestrian may cross a busy road."""
    tags = tags or {}
    return tags.get("highway") == SIGNALISED_JUNCTION_TAG or crossing_type_ok(tags)


def is_crossing_way(tags: dict[str, str] | None) -> bool:
    tags = tags or {}
    return tags.get("footway") == "crossing" or tags.get("cycleway") == "crossing"


def _line(points: Iterable[tuple[float, float]]) -> LineString | None:
    pts = list(points)
    if len(pts) < 2:
        return None
    try:
        line = LineString(pts)
    except (ValueError, TypeError):
        return None
    return line if line.length > 0 else None


def _note(stats: dict[str, Any], why: str) -> None:
    stats["skipped"] = (stats.get("skipped") or 0) + 1
    notes = stats.setdefault("skip_notes", [])
    if len(notes) < MAX_SKIP_NOTES:
        notes.append(why)


def _read_elements(elements: Iterable[Any], to_m, stats: dict[str, Any]):
    """Split raw Overpass elements into node coordinates, node tags and ways. Bad elements are skipped and counted."""
    nodes: dict[int, tuple[float, float]] = {}
    node_tags: dict[int, dict[str, str]] = {}
    ways: list[dict[str, Any]] = []
    for el in elements:
        try:
            kind = el["type"]
            if kind == "node":
                nodes[el["id"]] = to_m(el["lon"], el["lat"])
                if el.get("tags"):
                    node_tags[el["id"]] = el["tags"]
            elif kind == "way":
                if not isinstance(el.get("nodes"), list):
                    _note(stats, f"way {el.get('id')}: no node list")
                    continue
                ways.append({"id": el["id"], "nodes": el["nodes"], "tags": el.get("tags") or {}})
        except (KeyError, TypeError, ValueError) as e:
            _note(stats, f"{type(e).__name__}: {str(e)[:60]}")
    return nodes, node_tags, ways


def _original_graph(nodes, ways) -> GraphBuild:
    """The builder's original graph: every way, joined wherever ways share a node."""
    g = nx.Graph()
    for w in ways:
        ns = [k for k in w["nodes"] if k in nodes]
        for p, q in zip(ns, ns[1:]):
            g.add_edge(p, q, w=math.hypot(nodes[p][0] - nodes[q][0], nodes[p][1] - nodes[q][1]))
    return GraphBuild(graph=g, coords=dict(nodes), groups={}, rule="original")


def build_graph(elements: Iterable[Any], to_m, safe: bool) -> GraphBuild:
    """Build the walking graph from raw Overpass elements (ways with tags, nodes with tags and lat/lon).

    Args:
        elements: Overpass JSON 'elements'. For safe=True nodes must carry their tags (query with `out body` for nodes).
        to_m: function (lon, lat) -> (x, y) in metres.
        safe: False reproduces the original graph; True applies the two-sides rule and the unmarked-crossing rule.

    Returns:
        GraphBuild. Check `.error` before using `.graph`.
    """
    stats: dict[str, Any] = {}
    try:
        nodes, node_tags, ways = _read_elements(elements, to_m, stats)
        stats["ways"] = len(ways)
        if not safe:
            build = _original_graph(nodes, ways)
            build.stats = stats
            return build
        return _safe_graph(nodes, node_tags, ways, stats)
    except Exception as e:  # noqa: BLE001 - the contract is a typed error, never a raise, never a silent fallback
        return GraphBuild(graph=nx.Graph(), coords={}, groups={}, stats=stats, rule=RULE_NAME if safe else "original",
                          error=f"{type(e).__name__}: {e}")


def _crossing_way_allowed(way: dict[str, Any], node_tags: dict[int, dict[str, str]]) -> bool:
    if crossing_type_ok(way["tags"]):
        return True
    return any(allowed_crossing_node(node_tags.get(n)) for n in way["nodes"])


def _safe_graph(nodes, node_tags, ways, stats) -> GraphBuild:
    road_ways, path_ways, crossing_ways = [], [], []
    for w in ways:
        if is_crossing_way(w["tags"]):
            crossing_ways.append(w)
        elif w["tags"].get("highway") in ROAD_CLASSES:
            road_ways.append(w)
        else:
            path_ways.append(w)
    busy_ways = [w for w in road_ways if is_busy(w["tags"])]
    busy_ids = {w["id"] for w in busy_ways}
    busy_nodes = {n for w in busy_ways for n in w["nodes"] if n in nodes}
    allowed_ways = [w for w in crossing_ways if _crossing_way_allowed(w, node_tags)]
    allowed_nodes = ({n for n in busy_nodes if allowed_crossing_node(node_tags.get(n))}
                     | {n for w in allowed_ways for n in w["nodes"]}) & busy_nodes
    stats["roads"] = len(road_ways)
    stats["busy_roads"] = len(busy_ways)
    stats["busy_nodes"] = len(busy_nodes)
    stats["allowed_crossing_nodes"] = len(allowed_nodes)
    stats["signalised_junction_nodes"] = sum(1 for n in busy_nodes if node_tags.get(n, {}).get("highway") == SIGNALISED_JUNCTION_TAG)
    stats["untyped_crossing_nodes"] = sum(1 for n in busy_nodes
                                          if node_tags.get(n, {}).get("highway") == "crossing" and not crossing_type_ok(node_tags.get(n)))

    # Rule 2: drop mapped crossings of busy roads that are not a formal crossing
    busy_lines = [ln for ln in (_line(nodes[n] for n in w["nodes"] if n in nodes) for w in busy_ways) if ln is not None]
    busy_tree = STRtree(busy_lines) if busy_lines else None
    allowed_ids = {w["id"] for w in allowed_ways}
    kept_crossings, dropped = [], 0
    for w in crossing_ways:
        if w["id"] in allowed_ids:
            kept_crossings.append(w)
            continue
        ln = _line(nodes[n] for n in w["nodes"] if n in nodes)
        mid = ln.interpolate(0.5, normalized=True) if ln is not None else None
        near_busy = (busy_tree is not None and mid is not None
                     and len(busy_tree.query(mid, predicate="dwithin", distance=CROSSING_TO_ROAD_MATCH_M)) > 0)
        if any(n in busy_nodes for n in w["nodes"]) or near_busy:
            dropped += 1
        else:
            kept_crossings.append(w)
    stats["crossing_ways"] = len(crossing_ways)
    stats["crossing_ways_dropped"] = dropped

    # direction of the busy road at each of its nodes: decides which side of it a path leaves on
    road_dir: dict[int, tuple[float, float]] = {}
    for w in busy_ways:
        ns_ = [n for n in w["nodes"] if n in nodes]
        for i, n in enumerate(ns_):
            if n not in road_dir:
                a = nodes[ns_[i - 1]] if i > 0 else nodes[n]
                b = nodes[ns_[i + 1]] if i < len(ns_) - 1 else nodes[n]
                dx, dy = b[0] - a[0], b[1] - a[1]
                if dx or dy:
                    road_dir[n] = (dx, dy)

    def side_of(n: int, toward: int) -> int:
        """+1 or -1: which side of the busy road the segment n->toward leaves on. 0: along the road, or direction unknown."""
        d = road_dir.get(n)
        if d is None:
            return 0
        vx, vy = nodes[toward][0] - nodes[n][0], nodes[toward][1] - nodes[n][1]
        norm = math.hypot(*d) * math.hypot(vx, vy)
        if norm == 0:
            return 0
        s = (d[0] * vy - d[1] * vx) / norm
        return 0 if abs(s) < SIDE_MIN_SIN else (1 if s > 0 else -1)

    g = nx.Graph()
    coords: dict[Any, tuple[float, float]] = {}
    groups: dict[Any, list[Any]] = {}

    def reg(n: int, side: int | None = None) -> Any:
        node_id: Any = n if side is None else (n, side)
        if node_id not in coords:
            coords[node_id] = nodes[n]
            if side is not None:
                groups.setdefault(n, []).append(node_id)
        return node_id

    def gid(n: int, toward: int) -> Any:
        return reg(n, side_of(n, toward)) if n in busy_nodes else reg(n)

    def dist(a: int, b: int) -> float:
        return math.hypot(nodes[a][0] - nodes[b][0], nodes[a][1] - nodes[b][1])

    for w in path_ways + kept_crossings + [r for r in road_ways if r["id"] not in busy_ids]:
        ns = [k for k in w["nodes"] if k in nodes]
        for p, q in zip(ns, ns[1:]):
            g.add_edge(gid(p, q), gid(q, p), w=dist(p, q))
    for w in busy_ways:           # a busy road is walked on ONE side: two parallel lines, one per side
        ns = [k for k in w["nodes"] if k in nodes]
        for p, q in zip(ns, ns[1:]):
            for s in (1, -1):
                g.add_edge(reg(p, s), reg(q, s), w=dist(p, q))
    for n in allowed_nodes:       # the two sides join only at a formal crossing
        g.add_edge(reg(n, 1), reg(n, -1), w=0.0)
        if (n, 0) in coords:
            g.add_edge(reg(n, 0), reg(n, 1), w=0.0)
    stats["graph_nodes"] = g.number_of_nodes()
    return GraphBuild(graph=g, coords={k: coords[k] for k in g.nodes}, groups=groups, stats=stats, rule=RULE_NAME)


def physical_group(build: GraphBuild, node_id: Any) -> list[Any]:
    """Every graph node at the same physical spot as node_id. A source (station entrance) snapped to one copy of a busy-road node
    must reach all copies: standing at the entrance is not crossing the road."""
    base = node_id[0] if isinstance(node_id, tuple) else node_id
    copies = build.groups.get(base)
    return list(copies) if copies else [node_id]
