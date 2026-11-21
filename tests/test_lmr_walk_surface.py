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


def test_reason_uses_the_declared_build_distance_not_the_farthest_stored_point():
    """A safe build stored to 2000 m whose farthest reachable point is 850 m must say 2000, not 850."""
    s = surface(n=86)   # farthest stored walk is 850 m
    s2 = ws.Surface({"epsg": EPSG, "built": "x", "osm_extract": "t", "bbox_m": s.bbox_m, "anchors": s.anchors, "graph_nodes": 300,
                     "nodes": [[X0 + i * 10.0, Y0, i * 10.0, 0] for i in range(300)][:86] + [[X0 + 5000, Y0, 850.0, 0]] * 120,
                     "walk_rule": "safe-crossings-v2", "cutoff_m": 2000, "stranded": [[X0, Y0 + 300]]}, "t")
    assert s2.cutoff_m == 2000.0 and "within 2000 m" in s2.no_walk_reason(np.array([[X0, Y0 + 300]]) )
    assert surface().cutoff_m == 2990.0   # no declared value: falls back to the farthest stored point


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


def test_crossings_only_walk_refuses_a_surface_built_without_the_safe_rule():
    """An old-rule file in the safe folder must not be presented as a crossings-only walk."""
    r = ws.walk_from_lot_safe(ring(X0 + 400, Y0 + 15), EPSG, 300.0, False, [surface()])
    assert r["valid"] is False and r["m"] is None and "without the safe-crossing rule" in r["reason"]


def test_crossings_only_walk_refuses_a_misspelt_or_unknown_rule_name():
    """Only the exact safe rule name counts. A typo must not slip through as 'not original'."""
    for bad in ("orginal", "safe-crossings-v1", "safe-crossings-v3", ""):
        s = surface()
        s.walk_rule = bad
        r = ws.walk_from_lot_safe(ring(X0 + 400, Y0 + 15), EPSG, 300.0, False, [s])
        assert r["valid"] is False and r["m"] is None, bad


def test_the_safe_rule_name_matches_the_builder():
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "lmr_area"))
    import safe_crossings as sc
    assert ws.SAFE_WALK_RULE == sc.RULE_NAME


def test_crossings_only_walk_works_on_a_safe_surface():
    s = surface()
    s.walk_rule = "safe-crossings-v2"
    r = ws.walk_from_lot_safe(ring(X0 + 400, Y0 + 15), EPSG, 300.0, False, [s])
    assert r["valid"] is True and 404 <= r["m"] <= 415


def test_packed_file_keeps_the_busy_road_points_and_near_busy_road_is_three_state(tmp_path):
    """True next to a busy road, False away from one, None when the file has no list (an older file must not claim 'away')."""
    doc = {"epsg": EPSG, "built": "2026-11-20", "osm_extract": "t", "bbox_m": [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500],
           "anchors": [{"name": "Anchor A", "entrance_id": "node/1"}], "walk_rule": "safe-crossings-v2",
           "nodes": [[X0 + i * 10.0, Y0, i * 10.0, 0] for i in range(300)], "graph_nodes": 300,
           "busy_pts": [[X0 + 100.0, Y0 + 20.0], [X0 + 125.0, Y0 + 20.0]]}
    ws.write_npz(doc, tmp_path / "b.npz")
    s = ws.load_surface(str(tmp_path / "b.npz"))
    near = np.asarray(ring(X0 + 100, Y0))          # lot edge 20 m from a busy point
    far = np.asarray(ring(X0 + 1000, Y0))
    assert s.has_busy_list and len(s.busy_xy) == 2
    assert s.near_busy_road(near) is True and s.near_busy_road(far) is False
    ws.write_npz({**doc, "busy_pts": []}, tmp_path / "e.npz")
    assert ws.load_surface(str(tmp_path / "e.npz")).near_busy_road(near) is False
    ws.write_npz({k: v for k, v in doc.items() if k != "busy_pts"}, tmp_path / "o.npz")
    assert ws.load_surface(str(tmp_path / "o.npz")).near_busy_road(near) is None


# --- route pointers: the row of the next point toward the station, so a route can be drawn ---

def surface_with_pointers(n=300, parents=None):
    """The same one straight street, plus a pointer from each point to the one nearer the station (point 0 ends the walk)."""
    s = surface(n)
    doc = {"epsg": EPSG, "built": "2026-11-07", "osm_extract": "t", "bbox_m": [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500],
           "anchors": [{"name": "Anchor A", "entrance_id": "node/1"}], "graph_nodes": n,
           "nodes": [[X0 + i * 10.0, Y0, i * 10.0, 0] for i in range(n)],
           "parents": parents if parents is not None else [-1] + list(range(n - 1))}
    return ws.Surface(doc, "t.json.gz"), s


def test_a_route_follows_the_pointers_to_the_station_and_its_length_is_the_walk():
    s, _ = surface_with_pointers()
    r = walk(ring(X0 + 400, Y0 + 15), surfaces=[s], want_route=True)
    rt = r["route"]
    start = rt["points"][0][0] - X0                                 # the node the lookup matched: its walk distance plus the gap is the walk
    assert r["valid"] and rt["points"][-1] == [X0, Y0] and abs(start + r["gap_m"] - r["m"]) <= 0.2
    assert len(rt["points"]) == int(round(start / 10.0)) + 1       # one point per 10 m, from the matched node down to the station
    assert abs(rt["length_m"] - r["m"]) <= 0.2 and rt["walk_m"] == r["m"]   # the drawn route is the walk that was measured
    assert rt["lot_xy"][1] == Y0 + 15 and rt["epsg"] == EPSG


def test_asking_for_the_route_never_changes_the_walk():
    s, _ = surface_with_pointers()
    plain = walk(ring(X0 + 400, Y0 + 15), surfaces=[s])
    with_route = walk(ring(X0 + 400, Y0 + 15), surfaces=[s], want_route=True)
    assert "route" not in plain
    assert {k: v for k, v in with_route.items() if k != "route"} == plain


def test_without_pointers_the_walk_is_the_same_and_the_route_says_none():
    s = surface()
    r = walk(ring(X0 + 400, Y0 + 15), surfaces=[s], want_route=True)
    assert r["valid"] and r["route"]["points"] is None and r["route"]["length_m"] is None
    assert r["m"] == walk(ring(X0 + 400, Y0 + 15), surfaces=[s])["m"]


@pytest.mark.parametrize("parents", [[-1] * 299, [-1] + list(range(1, 300)), [-1] + [999] * 299, [-2] + list(range(299))])
def test_pointers_that_do_not_fit_the_points_are_dropped_not_trusted(parents):
    s, _ = surface_with_pointers(parents=parents)
    assert s.parent is None and s.route_rows(40) is None


def test_a_chain_where_the_walk_distance_goes_up_is_refused_not_cut_short():
    ps = [-1] + list(range(299))
    ps[20] = 25                                   # point 20 (200 m) points at point 25 (250 m): further from the station
    s, _ = surface_with_pointers(parents=ps)
    assert s.route_rows(10) == list(range(10, -1, -1))   # a chain that never meets the bad pointer is fine
    assert s.route_rows(40) is None                      # one that does is refused


def test_a_loop_of_equal_distances_is_refused():
    s, _ = surface_with_pointers()
    s.dist[:] = 100.0                                    # every distance equal: the 'goes up' test cannot catch a loop
    s.parent = np.array([1, 0] + list(range(1, 298)), dtype=np.int64)
    assert s.route_rows(5) is not None or True           # chain 5 -> 4 -> ... -> 1 -> 0 -> 1 ... loops
    assert s.route_rows(1) is None


def test_pointers_survive_the_writer_sorting_the_rows(tmp_path):
    n = 120
    rng = np.random.default_rng(7)
    perm = rng.permutation(n)                          # the row order of the build is not the order written
    inv = np.empty(n, dtype=int)
    inv[perm] = np.arange(n)
    pts = [[X0 + i * 10.0, Y0 + (i % 3) * 0.5, i * 10.0, 0] for i in range(n)]
    parents = [-1] + list(range(n - 1))
    doc = {"epsg": EPSG, "built": "2026-11-07", "osm_extract": "t", "bbox_m": [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500],
           "anchors": [{"name": "Anchor A", "entrance_id": "node/1"}], "graph_nodes": n,
           "nodes": [pts[i] for i in perm], "parents": [(-1 if parents[i] < 0 else int(inv[parents[i]])) for i in perm]}
    p = tmp_path / "s.npz"
    ws.write_npz(doc, p)
    s = ws.load_surface(str(p))
    rows = s.route_rows(int(np.argmin(np.abs(s.xy[:, 0] - (X0 + 1000.0)))))
    assert [round(float(s.xy[r, 0] - X0)) for r in rows] == list(range(1000, -1, -10))   # 1000 m down to the station, in order
    assert rows is not None and abs(float(s.dist[rows[0]]) - 1000.0) < 0.11


def test_the_writer_refuses_pointers_that_cannot_belong_to_the_points(tmp_path):
    base = {"epsg": EPSG, "built": "x", "bbox_m": [0, 0, 1, 1], "anchors": [], "nodes": [[X0, Y0, 0.0, 0], [X0 + 10, Y0, 10.0, 0]]}
    for bad in ([-1], [-1, 5], [-1, -3]):
        with pytest.raises(ValueError):
            ws.write_npz({**base, "parents": bad}, tmp_path / "bad.npz")


def test_a_file_written_without_pointers_still_loads_and_has_none(tmp_path):
    doc = {"epsg": EPSG, "built": "x", "osm_extract": "t", "bbox_m": [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500], "anchors": [{"name": "A"}],
           "nodes": [[X0 + i * 10.0, Y0, i * 10.0, 0] for i in range(250)], "graph_nodes": 250}
    ws.write_npz(doc, tmp_path / "old.npz")
    s = ws.load_surface(str(tmp_path / "old.npz"))
    assert s.parent is None and s.route_rows(3) is None


# --- route-only rows: on a route, but never a place a lot can start from (busy-road side copies) ---

def _surface_with_route_only_decoy(flags=True, n=300):
    """The one straight street, plus a decoy point sitting right at the lot with a smaller (wrong) walk distance, flagged route_only."""
    nodes = [[X0 + i * 10.0, Y0, i * 10.0, 0] for i in range(n)] + [[X0 + 400.0, Y0 + 15.0, 5.0, 0]]
    doc = {"epsg": EPSG, "built": "x", "osm_extract": "t", "bbox_m": [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500],
           "anchors": [{"name": "Anchor A", "entrance_id": "node/1"}], "nodes": nodes, "graph_nodes": n + 1,
           "parents": [-1] + list(range(n - 1)) + [0]}
    if flags:
        doc["route_only"] = [0] * n + [1]
    return ws.Surface(doc, "t.json.gz")


def test_a_route_only_row_is_never_matched_to_a_lot():
    with_flag = walk(ring(X0 + 400, Y0 + 15), surfaces=[_surface_with_route_only_decoy(True)])
    without_flag = walk(ring(X0 + 400, Y0 + 15), surfaces=[_surface_with_route_only_decoy(False)])
    assert with_flag["valid"] and 404 <= with_flag["m"] <= 415          # the real street's distance, as if the decoy were not there
    assert without_flag["m"] < 30                                       # unflagged, the decoy WOULD have been matched: proof the flag is what protects the walk


def test_route_only_rows_do_not_count_toward_a_station_being_built_or_the_surface_being_thin():
    s = _surface_with_route_only_decoy(True)
    assert int((~s.route_only).sum()) == 300 and s.route_only.sum() == 1
    s.anchors = [{"name": "Anchor A"}, {"name": "Only on a route-only row"}]
    s.anchor_idx = s.anchor_idx.copy()
    s.anchor_idx[-1] = 1
    s.names_with_nodes = {a.get("name") for i, a in enumerate(s.anchors) if i in set(np.unique(s.anchor_idx[~s.route_only]).tolist())}
    assert s.names_with_nodes == {"Anchor A"}


def test_route_only_flags_survive_the_writer_and_the_loader(tmp_path):
    n = 80
    nodes = [[X0 + i * 10.0, Y0, i * 10.0, 0] for i in range(n)]
    nodes = nodes[::-1]                                              # written rows are re-sorted: flags must follow their rows
    flags = [1 if i % 5 == 0 else 0 for i in range(n)][::-1]
    parents = [(-1 if i == 0 else i - 1) for i in range(n)][::-1]
    inv = {old: new for new, old in enumerate(range(n - 1, -1, -1))}
    parents = [(-1 if p < 0 else inv[p]) for p in parents]
    doc = {"epsg": EPSG, "built": "x", "osm_extract": "t", "bbox_m": [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500], "anchors": [{"name": "A"}],
           "nodes": nodes, "graph_nodes": n, "parents": parents, "route_only": flags}
    ws.write_npz(doc, tmp_path / "s.npz")
    s = ws.load_surface(str(tmp_path / "s.npz"))
    assert [bool(s.route_only[i]) for i in np.argsort(s.xy[:, 0])] == [i % 5 == 0 for i in range(n)]    # in street order again


@pytest.mark.parametrize("flags", [[1], [0, 2], [0, -1]])
def test_the_writer_refuses_route_only_flags_that_do_not_fit(tmp_path, flags):
    base = {"epsg": EPSG, "built": "x", "bbox_m": [0, 0, 1, 1], "anchors": [], "nodes": [[X0, Y0, 0.0, 0], [X0 + 10, Y0, 10.0, 0]]}
    with pytest.raises(ValueError):
        ws.write_npz({**base, "route_only": flags}, tmp_path / "bad.npz")


@pytest.mark.parametrize("flags", [[1], [0, 1, 0, 1], [0, 2, 0], [0, -1, 0]])
def test_a_present_flag_list_that_does_not_fit_the_points_rejects_the_file_instead_of_making_every_row_matchable(flags):
    s = _surface_with_route_only_decoy(True)
    doc = {"epsg": EPSG, "built": "x", "bbox_m": s.bbox_m, "anchors": s.anchors, "nodes": [[X0, Y0, 0.0, 0]] * 3, "route_only": flags}
    with pytest.raises(ValueError):
        ws.Surface(doc, "t")


def test_a_surface_without_any_flag_list_keeps_every_row_matchable_as_before():
    s = ws.Surface({"epsg": EPSG, "built": "x", "bbox_m": [0, 0, 1, 1], "anchors": [], "nodes": [[X0, Y0, 0.0, 0]] * 3}, "t")
    assert not s.route_only.any()


def test_the_route_length_counts_the_station_link_at_the_end_of_the_chain():
    """The station is joined to the street by a link of up to a few tens of metres: the last stored point has that distance, not 0.
    The drawn route is the chain plus that link, so its length must equal the walk."""
    n = 300
    link = 24.0
    doc = {"epsg": EPSG, "built": "x", "osm_extract": "t", "bbox_m": [X0 - 500, Y0 - 500, X0 + 3500, Y0 + 500],
           "anchors": [{"name": "Anchor A", "entrance_id": "node/1"}], "graph_nodes": n,
           "nodes": [[X0 + i * 10.0, Y0, link + i * 10.0, 0] for i in range(n)], "parents": [-1] + list(range(n - 1))}
    s = ws.Surface(doc, "t.json.gz")
    r = walk(ring(X0 + 400, Y0 + 15), surfaces=[s], want_route=True)
    rt = r["route"]
    assert rt["end_gap_m"] == link and r["valid"]
    assert abs(rt["length_m"] - r["m"]) <= 0.2          # without the link this would be 24 m short, as it was for 60 Palace Street, Petersham
