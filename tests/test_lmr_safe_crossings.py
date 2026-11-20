"""Safe-crossing rule for the walking-distance builder (scripts/lmr_area/safe_crossings.py).

Each break-it scenario is a small road network in metres (lon is x, lat is y, so the coordinate function is the identity).
The planner-facing meaning of each is in the test's docstring.
"""
import math
import sys
from pathlib import Path

import networkx as nx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "lmr_area"))
import safe_crossings as sc  # noqa: E402

IDENT = lambda lon, lat: (float(lon), float(lat))  # noqa: E731


def node(i, x, y, **tags):
    el = {"type": "node", "id": i, "lon": x, "lat": y}
    if tags:
        el["tags"] = tags
    return el


def way(i, nodes, **tags):
    return {"type": "way", "id": i, "nodes": nodes, "tags": tags}


def walk(build, starts, end):
    """Shortest walk in metres between two physical OSM nodes (all side copies at a busy-road node count as that node)."""
    g = build.graph.copy()
    g.add_node("S")
    g.add_node("T")
    for s in starts:
        for k in sc.physical_group(build, s):
            if k in g:
                g.add_edge("S", k, w=0.0)
    for k in sc.physical_group(build, end):
        if k in g:
            g.add_edge(k, "T", w=0.0)
    try:
        return nx.shortest_path_length(g, "S", "T", weight="w")
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return math.inf


# Cross-road network. East-west busy road along y=0 (nodes 10..14 at x=-100..100). Footpath beside it on the north (20..24, y=5) and
# south (30..34, y=-5). Short connectors join each footpath to the road at x=0 (node 12) and x=100 (node 14), like informal paths that meet
# the road. A person at the north footpath at x=0 (node 22) wants the south footpath at x=0 (node 32), 10 m away as the crow flies.
def cross_net(road_tags=None, node14_tags=None, extra=()):
    road_tags = road_tags or {"highway": "primary"}
    els = [node(10 + i, -100 + 50 * i, 0) for i in range(5)]
    els += [node(20 + i, -100 + 50 * i, 5) for i in range(5)]
    els += [node(30 + i, -100 + 50 * i, -5) for i in range(5)]
    if node14_tags:
        els = [e for e in els if e["id"] != 14] + [node(14, 100, 0, **node14_tags)]
    els += [way(1, [10, 11, 12, 13, 14], **road_tags), way(2, [20, 21, 22, 23, 24], highway="footway"),
            way(3, [30, 31, 32, 33, 34], highway="footway"),
            way(4, [22, 12], highway="footway"), way(5, [32, 12], highway="footway"),
            way(6, [24, 14], highway="footway"), way(7, [34, 14], highway="footway")]
    return els + list(extra)


SIGNALS = {"highway": "crossing", "crossing": "traffic_signals"}


# ---------- small rules ----------
@pytest.mark.parametrize("raw,expected", [("60", 60), ("50 km/h", 50), ("30 mph", 48), ("50;60", 60), ("walk", 10),
                                          ("none", None), ("AU:urban", None), ("", None), (None, None), (60, None)])
def test_parse_speed(raw, expected):
    assert sc.parse_speed_kmh(raw) == expected


@pytest.mark.parametrize("tags,expected", [
    ({"highway": "trunk"}, True), ({"highway": "primary", "maxspeed": "30"}, True), ({"highway": "secondary"}, True),
    ({"highway": "residential", "maxspeed": "50"}, False), ({"highway": "residential", "maxspeed": "60"}, True),
    ({"highway": "tertiary"}, True),                 # speed not mapped: treated as busy (the safe answer)
    ({"highway": "tertiary", "maxspeed": "50"}, False), ({"highway": "service"}, False), ({"highway": "footway"}, False),
    ({}, False), (None, False)])
def test_is_busy(tags, expected):
    assert sc.is_busy(tags) is expected


@pytest.mark.parametrize("tags,expected", [
    ({"highway": "traffic_signals"}, True), ({"highway": "crossing", "crossing": "zebra"}, True),
    ({"highway": "crossing", "crossing": "marked"}, True), ({"highway": "crossing", "crossing": "uncontrolled"}, True),
    ({"highway": "crossing", "crossing:signals": "yes"}, True),
    ({"highway": "crossing", "crossing": "unmarked"}, False),
    ({"highway": "crossing"}, False),                # untyped crossing is not proof of a safe one
    ({}, False), (None, False)])
def test_allowed_crossing_node(tags, expected):
    assert sc.allowed_crossing_node(tags) is expected


# ---------- the shortcut across a busy road ----------
def test_original_graph_takes_the_shortcut_across_the_busy_road():
    """Before the rule: the person walks the 10 m straight across the highway wherever two paths meet it."""
    b = sc.build_graph(cross_net(), IDENT, safe=False)
    assert walk(b, [22], 32) == pytest.approx(10.0)


def test_safe_graph_refuses_the_informal_crossing_and_uses_the_traffic_lights():
    """With a signalised crossing 100 m down the road, the safe walk goes there and back: 100 + 5 + 5 + 100 = 210 m, not 10 m."""
    b = sc.build_graph(cross_net(node14_tags=SIGNALS), IDENT, safe=True)
    assert b.error is None
    assert walk(b, [22], 32) == pytest.approx(210.0)


def test_with_no_formal_crossing_at_all_the_far_side_is_unreachable_not_a_short_number():
    """No traffic light, zebra or marked crossing anywhere: there is no safe route. The builder must not invent a short one."""
    b = sc.build_graph(cross_net(), IDENT, safe=True)
    assert walk(b, [22], 32) == math.inf


def test_unmarked_crossing_path_across_a_busy_road_is_dropped():
    """A mapped crossing with no formal type that cuts straight over the highway is not a safe crossing."""
    cw = way(8, [22, 32], highway="footway", footway="crossing", crossing="unmarked")
    b = sc.build_graph(cross_net(node14_tags=SIGNALS, extra=[cw]), IDENT, safe=True)
    assert walk(b, [22], 32) == pytest.approx(210.0)
    assert b.stats["crossing_ways_dropped"] == 1


def test_signalised_crossing_path_across_a_busy_road_is_kept():
    cw = way(8, [22, 32], highway="footway", footway="crossing", crossing="traffic_signals")
    b = sc.build_graph(cross_net(extra=[cw]), IDENT, safe=True)
    assert walk(b, [22], 32) == pytest.approx(10.0)
    assert b.stats["crossing_ways_dropped"] == 0


def test_crossing_path_with_no_type_is_formal_when_a_traffic_signal_node_is_on_it():
    cw = way(8, [22, 40, 32], highway="footway", footway="crossing")
    els = cross_net(extra=[node(40, 0, 0, highway="traffic_signals"), cw])
    b = sc.build_graph(els, IDENT, safe=True)
    assert walk(b, [22], 32) == pytest.approx(10.0)


def test_walking_along_your_own_side_of_a_busy_road_is_still_possible():
    """The first version of the rule cut the footpaths that only join up through the road: 43% of places near Pymble became unreachable.
    A person can walk along the highway on their own side; only switching sides is restricted."""
    els = cross_net()
    els = [e for e in els if not (e["type"] == "way" and e["id"] == 2)]     # no north footpath mapped: the road is the only link
    b = sc.build_graph(els, IDENT, safe=True)
    assert walk(b, [22], 24) == pytest.approx(5 + 100 + 5)                    # 22 -> road node 12 (5 m), along the road to node 14 (100 m), up to 24 (5 m)


def test_walking_along_the_other_side_of_a_busy_road_is_also_possible():
    """Both sides get a line. A person starting on the south side with no south footpath mapped can still walk along the road to the end."""
    els = [e for e in cross_net() if not (e["type"] == "way" and e["id"] == 3)]
    b = sc.build_graph(els, IDENT, safe=True)
    assert walk(b, [32], 34) == pytest.approx(5 + 100 + 5)


def test_a_quiet_street_can_be_crossed_at_an_ordinary_junction():
    els = cross_net(road_tags={"highway": "residential", "maxspeed": "50"})
    b = sc.build_graph(els, IDENT, safe=True)
    assert walk(b, [22], 32) == pytest.approx(10.0)


def test_tertiary_road_with_no_speed_is_treated_as_busy_and_with_a_50_sign_is_not():
    assert walk(sc.build_graph(cross_net(road_tags={"highway": "tertiary"}), IDENT, safe=True), [22], 32) == math.inf
    assert walk(sc.build_graph(cross_net(road_tags={"highway": "tertiary", "maxspeed": "50"}), IDENT, safe=True), [22], 32) == pytest.approx(10.0)


def test_a_path_running_along_the_road_on_its_nodes_is_not_a_way_across():
    """A footpath mapped on the road's own nodes (not beside it) must not join the two sides."""
    els = cross_net()
    els += [way(9, [11, 12, 13], highway="footway")]
    b = sc.build_graph(els, IDENT, safe=True)
    assert walk(b, [22], 32) == math.inf


def test_an_along_the_road_path_keeps_its_own_group_and_does_not_join_either_side():
    """The along-road path at node 12 sits in neither side's group, so it cannot be used to hop from the north side to the south."""
    els = cross_net() + [way(9, [11, 12, 13], highway="footway")]
    b = sc.build_graph(els, IDENT, safe=True)
    assert (12, 0) in b.graph
    assert all(isinstance(nb, tuple) and nb[1] == 0 for nb in b.graph.neighbors((12, 0)))


# ---------- what the surface stores ----------
def test_busy_road_side_copies_are_marked_so_they_are_never_stored():
    """Both sides' copies share one spot. If both were stored, a lot across the highway could pick up the near side's short walk."""
    b = sc.build_graph(cross_net(node14_tags=SIGNALS), IDENT, safe=True)
    copies = [k for k in b.graph.nodes if sc.GraphBuild.is_line_copy(k)]
    assert copies and all(sc.GraphBuild.is_line_copy(k) for k in copies)
    assert not sc.GraphBuild.is_line_copy(22) and not sc.GraphBuild.is_line_copy(32)
    assert len({b.coords[(12, 1)], b.coords[(12, -1)]}) == 1               # the two sides really do share a spot


def test_an_entrance_on_a_busy_road_node_reaches_both_sides():
    b = sc.build_graph(cross_net(), IDENT, safe=True)
    assert walk(b, [12], 22) == pytest.approx(5.0)
    assert walk(b, [12], 32) == pytest.approx(5.0)


def test_safe_false_matches_the_original_edges_exactly():
    els = cross_net(node14_tags=SIGNALS)
    b = sc.build_graph(els, IDENT, safe=False)
    legacy = nx.Graph()
    nodes = {e["id"]: (e["lon"], e["lat"]) for e in els if e["type"] == "node"}
    for w in (e for e in els if e["type"] == "way"):
        ns = [k for k in w["nodes"] if k in nodes]
        for p, q in zip(ns, ns[1:]):
            legacy.add_edge(p, q, w=math.hypot(nodes[p][0] - nodes[q][0], nodes[p][1] - nodes[q][1]))
    assert set(map(frozenset, b.graph.edges)) == set(map(frozenset, legacy.edges))
    assert all(b.graph[u][v]["w"] == pytest.approx(legacy[u][v]["w"]) for u, v in legacy.edges)
    assert b.rule == "original"


# ---------- bad data ----------
def test_bad_elements_are_skipped_and_counted_never_raised():
    els = cross_net(node14_tags=SIGNALS) + [
        {"type": "node", "id": 99}, {"type": "way", "id": 98}, {"id": 97}, "junk", None,
        {"type": "way", "id": 96, "nodes": "not a list", "tags": {}},
        way(95, [999, 998], highway="footway"),                               # nodes that were never downloaded
        way(94, [22, 22, 23], highway="footway")]                             # repeated node
    b = sc.build_graph(els, IDENT, safe=True)
    assert b.error is None
    assert b.stats["skipped"] >= 5 and b.stats["skip_notes"]
    assert walk(b, [22], 32) == pytest.approx(210.0)


def test_unexpected_failure_returns_a_typed_error_not_an_exception_and_not_a_silent_other_graph():
    def boom(lon, lat):
        raise RuntimeError("projection failed")
    b = sc.build_graph(cross_net(), boom, safe=True)
    assert b.error and "RuntimeError" in b.error
    assert b.graph.number_of_nodes() == 0 and b.rule == sc.RULE_NAME


def test_stats_say_what_the_rule_did():
    b = sc.build_graph(cross_net(node14_tags=SIGNALS), IDENT, safe=True)
    assert b.stats["busy_roads"] == 1 and b.stats["allowed_crossing_nodes"] == 1
    assert b.stats["busy_nodes"] == 5 and b.rule == "safe-crossings-v2"


def test_safe_build_lists_points_along_the_busy_road_and_the_ordinary_build_does_not():
    """The engine says 'next to a busy road' from these points: about every 25 m, ends included, on the road line only."""
    b = sc.build_graph(cross_net(), IDENT, safe=True)
    pts = b.busy_pts
    assert pts is not None and (-100.0, 0.0) in pts and (100.0, 0.0) in pts
    assert all(y == 0.0 for _, y in pts)                                  # the footways at y=5 and y=-5 are not busy roads
    xs = sorted(x for x, _ in pts)
    assert max(b2 - a for a, b2 in zip(xs, xs[1:])) <= sc.BUSY_PT_STEP_M + 0.1
    assert sc.build_graph(cross_net(), IDENT, safe=False).busy_pts is None
    assert sc.build_graph(cross_net(road_tags={"highway": "residential"}), IDENT, safe=True).busy_pts == []


def split_road_net(second_way_reversed):
    """One busy road along y=0 drawn as two ways meeting at node 11. The second way is drawn east-to-west when reversed.
    A footway leaves the road to the NORTH at node 11 (node 21) and at node 12 (node 22); one leaves to the SOUTH at node 12 (node 32)."""
    els = [node(10, -100, 0), node(11, 0, 0), node(12, 100, 0), node(21, 0, 5), node(22, 100, 5), node(32, 100, -5)]
    second = [12, 11] if second_way_reversed else [11, 12]
    return els + [way(1, [10, 11], highway="primary"), way(2, second, highway="primary"),
                  way(3, [21, 11], highway="footway"), way(4, [22, 12], highway="footway"), way(5, [32, 12], highway="footway")]


@pytest.mark.parametrize("reversed_", [False, True])
def test_a_road_drawn_in_two_ways_has_the_same_north_side_along_its_whole_length(reversed_):
    """Open risk 2. The north footpaths must stay joined to each other and must NOT join the south footpath, however the second way is drawn.
    Without one consistent orientation the reversed way's 'left' is the south side and the walk changes sides with no crossing."""
    b = sc.build_graph(split_road_net(reversed_), IDENT, safe=True)
    assert walk(b, [21], 22) == pytest.approx(110.0)       # north to north: 5 m connector, 100 m along the road, 5 m connector
    assert walk(b, [21], 32) == math.inf                    # north to south: only at a formal crossing, and there is none
    assert b.stats["orientation_conflicts"] == 0
    assert b.stats["orientation_flipped_ways"] == (1 if reversed_ else 0)
