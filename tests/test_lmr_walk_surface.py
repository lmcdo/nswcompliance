"""Break-it tests for the walking-surface lookup (services/lmr_walk_surface.py). Synthetic surface, no network.

The surface is one straight street: node i is i*10 m from the anchor, walking distance i*10 m.
"""
import numpy as np
import pytest

from services import lmr_walk_surface as ws

X0, Y0, EPSG = 330000.0, 6250000.0, 28356


def surface(n=300, anchors=None, graph_nodes=None, bbox=None, epsg=EPSG):
    nodes = [[X0 + i * 10.0, Y0, i * 10.0, 0] for i in range(n)]
    return ws.Surface({
        "epsg": epsg, "built": "2026-11-07", "osm_extract": "t",
        "bbox_m": bbox or [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500],
        "anchors": anchors or [{"name": "Anchor A", "entrance_id": "node/1"}],
        "nodes": nodes, "graph_nodes": graph_nodes if graph_nodes is not None else n}, "t.json.gz")


def ring(x, y, w=20.0, h=20.0):
    return [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)]


def walk(r, straight=300.0, touches=False, surfaces=None, **kw):
    return ws.walk_from_lot(r, EPSG, straight, touches, surfaces if surfaces is not None else [surface()], **kw)


def test_packed_file_reads_back_the_same_surface(tmp_path):
    doc = {"epsg": EPSG, "built": "2026-11-07", "osm_extract": "t", "bbox_m": [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500],
           "anchors": [{"name": "Anchor A", "entrance_id": "node/1", "optimistic_by_m": 40}],
           "nodes": [[X0 + i * 10.0, Y0 + (i % 3) * 0.5, i * 10.0, 0] for i in range(300)], "graph_nodes": 300}
    p = tmp_path / "s.npz"
    ws.write_npz(doc, p)
    s = ws.load_surface(str(p))
    assert s.epsg == EPSG and s.built == "2026-11-07" and s.anchors[0]["optimistic_by_m"] == 40 and len(s.xy) == 300
    assert abs(float(s.dist.max()) - 2990.0) < 0.11 and abs(float(s.xy[:, 0].min()) - X0) < 0.11
    r = ws.walk_from_lot(ring(X0 + 400, Y0 + 15), EPSG, 300.0, False, [s])
    assert r["valid"] and 404 <= r["m"] <= 415 and r["optimistic_by_m"] == 40


def test_walk_is_node_distance_plus_gap():
    r = walk(ring(X0 + 400, Y0 + 15))  # outline corner (X0+400, Y0+15) is 15 m from node 40 (400 m)
    assert r["valid"] and 404 <= r["m"] <= 415 and r["anchor"] == "Anchor A"  # not 401: no corner-cutting to a farther node


def test_walk_measured_from_the_nearest_part_of_the_lot():
    near = walk(ring(X0 + 400, Y0 + 10, w=300.0))  # a long lot: its nearest corner is at 400 m
    far_corner_only = walk(ring(X0 + 700, Y0 + 10))
    assert near["m"] < far_corner_only["m"]


def _far_lot_reason(rule, stranded=None):
    """A lot 300 m north of the only street: no stored walk point within 40 m of it."""
    s = surface()
    s.walk_rule = rule
    if stranded is not None:
        s.has_stranded_list = True
        s.stranded_xy = np.asarray(stranded, dtype=float).reshape(-1, 2)
    r = walk(ring(X0 + 400, Y0 + 300), surfaces=[s])
    assert r["valid"] is False and r["m"] is None
    return r["reason"]


def test_safe_surface_with_footpath_but_no_route_says_so():
    """Footpath points sit next to the lot but none reaches a station: the planner is told to look for a missing crossing."""
    why = _far_lot_reason("safe-crossings-v2", stranded=[[X0 + 410, Y0 + 310]])
    assert why.startswith("there is a footpath next to the lot, but the map has no route")
    assert "no mapped footpath" not in why and "check the route on the ground" in why


def test_safe_surface_with_no_footpath_near_the_lot_says_that():
    why = _far_lot_reason("safe-crossings-v2", stranded=[[X0 + 2000, Y0 + 2000]])   # stranded footpath exists, but far away
    assert why.startswith("there is no mapped footpath within 40 m") and "no route" not in why
    assert _far_lot_reason("safe-crossings-v2", stranded=[]).startswith("there is no mapped footpath within 40 m")


def test_packed_file_keeps_the_stranded_footpath_points(tmp_path):
    doc = {"epsg": EPSG, "built": "2026-11-19", "osm_extract": "t", "bbox_m": [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500],
           "anchors": [{"name": "Anchor A", "entrance_id": "node/1"}], "walk_rule": "safe-crossings-v2",
           "nodes": [[X0 + i * 10.0, Y0, i * 10.0, 0] for i in range(300)], "graph_nodes": 300,
           "stranded": [[X0 + 410.0, Y0 + 310.0], [X0 + 425.5, Y0 + 310.0]]}
    ws.write_npz(doc, tmp_path / "s.npz")
    s = ws.load_surface(str(tmp_path / "s.npz"))
    assert s.has_stranded_list and len(s.stranded_xy) == 2 and abs(s.stranded_xy[1][0] - (X0 + 425.5)) < 0.11
    ws.write_npz({**doc, "stranded": []}, tmp_path / "e.npz")
    e = ws.load_surface(str(tmp_path / "e.npz"))
    assert e.has_stranded_list and len(e.stranded_xy) == 0
    old = {k: v for k, v in doc.items() if k != "stranded"}
    ws.write_npz(old, tmp_path / "o.npz")
    assert ws.load_surface(str(tmp_path / "o.npz")).has_stranded_list is False


def test_original_surface_blames_a_missing_footpath():
    assert "no mapped footpath within 40 m of the lot" in _far_lot_reason("original")


def test_safe_surface_without_the_list_names_both_causes_rather_than_guessing():
    """An older safe file that has no stranded list cannot tell the two causes apart, so it says both."""
    why = _far_lot_reason("safe-crossings-v2")
    assert "no mapped footpath within 40 m" in why and ", or there is a footpath next to the lot" in why
    assert "no route from it to a station within 2990 m" in why


def test_surface_reads_its_rule_from_the_file(tmp_path):
    doc = {"epsg": EPSG, "built": "2026-11-19", "osm_extract": "t", "bbox_m": [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500],
           "anchors": [{"name": "Anchor A", "entrance_id": "node/1"}], "walk_rule": "safe-crossings-v2",
           "nodes": [[X0 + i * 10.0, Y0, i * 10.0, 0] for i in range(300)], "graph_nodes": 300}
    ws.write_npz(doc, tmp_path / "s.npz")
    assert ws.load_surface(str(tmp_path / "s.npz")).walk_rule == "safe-crossings-v2"
    assert surface().walk_rule == "original"


def test_no_surface_is_invalid_not_zero():
    r = walk(ring(X0 + 400, Y0 + 15), surfaces=[])
    assert r["valid"] is False and r["m"] is None


def test_lot_outside_every_surface_box_is_invalid():
    assert walk(ring(X0 + 9000, Y0 + 15))["valid"] is False


def test_wrong_projection_is_not_used():
    assert walk(ring(X0 + 400, Y0 + 15), surfaces=[surface(epsg=28355)])["valid"] is False


def test_no_footpath_within_the_gap_limit_is_invalid():
    r = walk(ring(X0 + 400, Y0 + 200))  # 200 m from the street
    assert r["valid"] is False and "footpath" in r["reason"]


def test_gap_limit_edge():
    assert walk(ring(X0 + 400, Y0 + 35))["valid"] is True
    assert walk(ring(X0 + 400, Y0 + 50))["valid"] is False


def test_thin_network_is_invalid():
    assert walk(ring(X0 + 400, Y0 + 15), surfaces=[surface(graph_nodes=50)])["valid"] is False
    assert walk(ring(X0 + 400, Y0 + 15), surfaces=[surface(n=100)])["valid"] is False


def test_walk_shorter_than_straight_line_is_invalid():
    r = walk(ring(X0 + 400, Y0 + 15), straight=900.0)  # straight 900 but walk ~410: impossible
    assert r["valid"] is False and "shorter than the straight line" in r["reason"]


def test_walk_slightly_under_straight_is_tolerated_and_touching_anchor_is_exempt():
    assert walk(ring(X0 + 400, Y0 + 15), straight=430.0)["valid"] is True  # within 30 m slack
    assert walk(ring(X0 + 400, Y0 + 15), straight=900.0, touches=True)["valid"] is True


def test_zero_walk_for_a_lot_away_from_the_anchor_is_invalid():
    r = walk(ring(X0 - 5, Y0 - 5, w=10.0, h=10.0), straight=300.0)  # sits on node 0, claims 300 m straight
    assert r["valid"] is False


def test_oversized_lot_is_invalid():
    assert walk(ring(X0 + 100, Y0 - 300, w=900.0, h=900.0))["valid"] is False


def test_too_few_points_is_invalid():
    assert ws.walk_from_lot([(0.0, 0.0), (1.0, 1.0)], EPSG, 100.0, False, [surface()])["valid"] is False


def test_every_nearby_anchor_must_have_a_built_surface():
    r = walk(ring(X0 + 400, Y0 + 15), required_anchors={"Anchor A", "Anchor B"})
    assert r["valid"] is False and "Anchor B" in r["reason"]
    assert walk(ring(X0 + 400, Y0 + 15), required_anchors={"Anchor A"})["valid"] is True


def test_a_station_named_in_the_file_but_with_no_nodes_is_not_built():
    # "Anchor B" is listed, but no stored node walks to it (its entrances sit outside the footpath download).
    s = surface(anchors=[{"name": "Anchor A", "entrance_id": "node/1"}, {"name": "Anchor B", "entrance_id": "node/2"}])
    r = walk(ring(X0 + 400, Y0 + 15), surfaces=[s], required_anchors={"Anchor A", "Anchor B"})
    assert r["valid"] is False and "Anchor B" in r["reason"]
    assert walk(ring(X0 + 400, Y0 + 15), surfaces=[s], required_anchors={"Anchor A"})["valid"] is True


def test_minimum_over_surfaces_is_taken():
    near = ws.Surface({**{"epsg": EPSG, "built": "d", "osm_extract": "", "bbox_m": [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500]},
                       "anchors": [{"name": "Anchor B", "entrance_id": "station outline", "optimistic_by_m": 150}],
                       "nodes": [[X0 + i * 10.0, Y0, max(0.0, i * 10.0 - 300.0), 0] for i in range(300)], "graph_nodes": 300}, "b")
    r = walk(ring(X0 + 400, Y0 + 15), surfaces=[surface(), near], straight=200.0)
    assert r["anchor"] == "Anchor B" and r["m"] < 200 and r["optimistic_by_m"] == 150
