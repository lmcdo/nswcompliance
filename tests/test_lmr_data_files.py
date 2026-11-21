"""Guards for the committed data behind the low-and-mid-rise area check: the station file and the packed walking files.

Scripts that build or test this data live in scripts/lmr_area/ and are named here so a rename cannot go unnoticed.
"""
import json
from pathlib import Path

import pytest

from services import lmr_area_decision as dec
from services import lmr_walk_surface as ws

REPO = Path(__file__).resolve().parent.parent
STATIONS = REPO / "data" / "law" / "lmr_station_entrances.json"
WALK_DIR = REPO / "data" / "lmr_walk"
SCRIPTS = [
    "scripts/lmr_area/build_station_entrances.py",   # step 1: stations and OpenStreetMap entrances, names read from the law
    "scripts/lmr_area/merge_gtfs_entrances.py",      # step 2: add the official TfNSW GTFS Pathways entrances
    "scripts/lmr_area/add_station_footprints.py",    # step 3: building / platform outlines for stations with no entrance
    "scripts/lmr_area/entrance_rule_test.py",        # step 4: test the entrance-finding rule on stations whose entrances are known
    "scripts/lmr_area/apply_entrance_rule.py",       # step 5: apply the tested rule to the stations with none
    "scripts/lmr_area/build_walk_surfaces.py",       # step 6: walking files from OpenStreetMap footpaths
    "scripts/lmr_area/pack_walk_surfaces.py",        # step 7: pack them into data/lmr_walk/ (repo limit 2 MB per file)
    "scripts/lmr_area/area_check_test.py",           # the test of the area check against an independent router
    "scripts/lmr_area/area_check_score.py",          # its scorer: prints PASS or FAIL
    "scripts/lmr_area/tod_check.py",                 # the Chapter 5 (TOD) check
]
# The packed walking files that must exist. One is cut into three overlapping strips because the repo refuses files over 2 MB.
WALK_FILES = [
    "data/lmr_walk/cb-bankstown.npz", "data/lmr_walk/georges-river.npz", "data/lmr_walk/inner-west-1of3.npz",
    "data/lmr_walk/inner-west-2of3.npz", "data/lmr_walk/inner-west-3of3.npz", "data/lmr_walk/kuringgai.npz",
    "data/lmr_walk/woollahra.npz",
    # Added 2026-11-17: the seven pilot councils that had no walking file (one per council, built from OpenStreetMap footpaths).
    "data/lmr_walk/pilot-blacktown.npz", "data/lmr_walk/pilot-hornsby.npz", "data/lmr_walk/pilot-northern_beaches.npz",
    "data/lmr_walk/pilot-parramatta.npz", "data/lmr_walk/pilot-penrith.npz", "data/lmr_walk/pilot-waverley.npz",
    "data/lmr_walk/pilot-wollongong.npz",
]
REPO_FILE_LIMIT = 2 * 1024 * 1024  # the pre-commit large-file gate


@pytest.mark.parametrize("path", SCRIPTS)
def test_the_data_scripts_exist(path):
    assert (REPO / path).is_file()


def test_exactly_the_expected_walking_files_exist():
    assert sorted(p.relative_to(REPO).as_posix() for p in WALK_DIR.glob("*.npz")) == sorted(WALK_FILES)


def load_stations():
    return json.loads(STATIONS.read_text(encoding="utf-8"))


def test_station_file_has_exactly_the_stations_the_law_lists():
    facts = dec.LawFacts.load()
    s11, s12 = set(facts.names("schedule_11_stations")), set(facts.names("schedule_12_stations"))
    doc = load_stations()
    by_name = {s["name"]: s for s in doc["stations"]}
    assert len(by_name) == len(doc["stations"]) == len(s11) + len(s12)
    assert set(by_name) == s11 | s12
    assert {n for n, s in by_name.items() if s["schedule"] == 12} == s12


def test_every_station_has_an_entrance_or_an_outline_and_estimates_are_labelled():
    for s in load_stations()["stations"]:
        assert s["entrances"] or s.get("footprint"), s["name"]
        assert isinstance(s["lat"], float) and isinstance(s["lon"], float)
        for e in s["entrances"]:
            if str(e["id"]).startswith("osm-estimate:"):
                assert e.get("estimated") is True, (s["name"], e["id"])  # a guessed entrance is never presented as a mapped one
            else:
                assert not e.get("estimated"), (s["name"], e["id"])
        if any(e.get("estimated") for e in s["entrances"]):
            assert s.get("entrance_estimate_extra_m", 0) >= 40


def test_station_file_carries_its_licence_and_method_notes():
    doc = load_stations()
    assert "CC-BY" in doc["source"] and "OpenStreetMap" in doc["source"] and "Transport for NSW" in doc["source"]
    assert "estimated" in doc["estimate_note"].lower() and doc["law_version_date"] == dec.LawFacts.load().version_date


def test_walking_files_exist_fit_the_repo_limit_and_load():
    files = sorted(WALK_DIR.glob("*.npz"))
    assert len(files) >= 5
    names = set()
    for f in files:
        assert f.stat().st_size < REPO_FILE_LIMIT, f.name
        s = ws.load_surface(str(f))
        assert s.graph_nodes >= ws.MIN_NODES and len(s.xy) >= ws.MIN_NODES and s.anchors, f.name
        assert float(s.dist.max()) <= 1100.01 and float(s.dist.min()) >= 0, f.name
        names |= {a["name"] for a in s.anchors}
    station_names = {s["name"] for s in load_stations()["stations"]}
    assert names & station_names, "no walking file contains any station"


def test_cut_strips_overlap_so_a_lot_on_the_cut_is_still_covered():
    strips = sorted(WALK_DIR.glob("*of*.npz"))
    assert strips, "expected the large area to be cut into strips"
    boxes = sorted((ws.load_surface(str(f)).bbox_m for f in strips), key=lambda b: b[0])
    for a, b in zip(boxes, boxes[1:]):
        assert a[2] - b[0] >= 300.0, "neighbouring strips must overlap by at least 300 m"
    for f in strips:  # every strip of one area keeps the full anchor list
        assert len(ws.load_surface(str(f)).anchors) == len(ws.load_surface(str(strips[0])).anchors)


def test_the_python_image_copies_every_file_the_area_check_reads():
    """Dockerfile.python copied only services/. The area check reads data/law and data/lmr_walk at REPO_ROOT (/app in the image), so
    without these COPY lines every deployed lot would come back with a "Why:" reason and no area."""
    docker = (REPO / "Dockerfile.python").read_text(encoding="utf-8")
    for needed in ("data/law/housing_sepp_lmr_facts.json", "data/law/lmr_station_entrances.json", "data/lmr_walk/", "data/lmr_walk_safe/", "data/lmr_route_normal/", "data/anef/sydney_anef_2045.json",
                   "data/law/road_rules_2014_pedestrian_facts.json", "data/law/road-rules-2014-regs-231-232-234-copied-2026-11-20.txt"):
        assert any(line.startswith("COPY") and needed in line for line in docker.splitlines()), needed
    assert (REPO / "data" / "law" / "housing_sepp_lmr_facts.json").is_file()
    assert (REPO / "data" / "anef" / "sydney_anef_2045.json").is_file()


def test_the_crossings_only_walk_files_are_exactly_the_shipped_set_and_each_loads_with_the_safe_rule():
    import sys
    sys.path.insert(0, str(REPO / "scripts" / "lmr_area"))
    import pack_walk_surfaces as pk
    safe_dir = REPO / "data" / "lmr_walk_safe"
    assert sorted(p.name for p in safe_dir.glob("*.npz")) == sorted(pk.SAFE_SHIPPED_FILES)
    for f in sorted(safe_dir.glob("*.npz")):
        assert f.stat().st_size < REPO_FILE_LIMIT, f.name
        s = ws.load_surface(str(f))
        assert s.walk_rule == ws.SAFE_WALK_RULE, f.name        # an old-rule file would show a longer walk that is not the crossings-only one
        assert s.busy_xy is not None and len(s.busy_xy) > 0, f.name   # without the busy-road points the near-a-busy-road note cannot be said
        assert s.graph_nodes >= ws.MIN_NODES and s.anchors, f.name
    # same areas as the ordinary walk: one safe strip set per ordinary one, so no area silently loses its second line
    ordinary = {p.name.split("-1of")[0].split("-2of")[0].split("-3of")[0].replace(".npz", "") for p in WALK_DIR.glob("*.npz")}
    safe = {p.name.split("-1of")[0].split("-2of")[0].split("-3of")[0].split("-4of")[0].replace(".npz", "") for p in safe_dir.glob("*.npz")}
    assert ordinary == safe


def test_packing_trims_the_busy_road_points_to_each_strip_and_leaves_an_absent_list_absent():
    import sys
    import numpy as np
    sys.path.insert(0, str(REPO / "scripts" / "lmr_area"))
    import pack_walk_surfaces as pk
    n = pk.MAX_NODES_PER_FILE + 10
    nodes = np.column_stack([np.linspace(0, 20000, n), np.zeros(n), np.zeros(n), np.zeros(n)])
    doc = {"bbox_m": [0.0, -10.0, 20000.0, 10.0], "nodes": nodes, "busy_pts": [[100.0, 0.0], [19900.0, 0.0]]}
    parts = pk.strips(doc)
    assert len(parts) >= 2
    assert len(parts[0]["busy_pts"]) == 1 and parts[0]["busy_pts"][0][0] == 100.0      # the far point is not copied into strip 1
    assert len(parts[-1]["busy_pts"]) == 1 and parts[-1]["busy_pts"][-1][0] == 19900.0
    assert all("busy_pts" not in p for p in pk.strips({k: v for k, v in doc.items() if k != "busy_pts"}))


def test_strips_keep_every_route_whole_inside_their_own_file(monkeypatch):
    """A route can start in one strip and have its station in the next. Each strip must hold the whole chain, or its pointer would
    point at a point that is not in the file."""
    import sys
    import numpy as np
    sys.path.insert(0, str(REPO / "scripts" / "lmr_area"))
    import pack_walk_surfaces as pk
    monkeypatch.setattr(pk, "MAX_NODES_PER_FILE", 100)
    n = 400
    doc = {"epsg": 28356, "built": "x", "osm_extract": "t", "bbox_m": [0.0, -10.0, n * 10.0, 10.0], "anchors": [{"name": "A"}], "graph_nodes": n,
           "nodes": [[i * 10.0, 0.0, i * 10.0, 0] for i in range(n)], "parents": [-1] + list(range(n - 1))}   # one street, the station at x = 0
    parts = pk.strips(doc)
    assert len(parts) >= 4
    for part in parts:
        xs = np.asarray(part["nodes"])[:, 0]
        p = np.asarray(part["parents"])
        assert len(p) == len(xs) and p.max() < len(xs) and p.min() >= -1
        s = ws.Surface({**part, "nodes": part["nodes"], "parents": part["parents"]}, "strip")
        far = int(np.argmax(xs))
        rows = s.route_rows(far)
        assert rows is not None and float(s.xy[rows[-1], 0]) == 0.0              # the last strip's far point still reaches the station
        assert len(rows) == int(round(xs[far] / 10.0)) + 1                        # and the chain is the whole street, not cut short
    assert len(parts[-1]["nodes"]) > len(parts[0]["nodes"]) - 1                  # the later strips carry the earlier points their routes pass through


def test_strips_without_pointers_stay_without_pointers(monkeypatch):
    import sys
    sys.path.insert(0, str(REPO / "scripts" / "lmr_area"))
    import pack_walk_surfaces as pk
    monkeypatch.setattr(pk, "MAX_NODES_PER_FILE", 100)
    n = 400
    doc = {"epsg": 28356, "built": "x", "bbox_m": [0.0, -10.0, n * 10.0, 10.0], "anchors": [], "nodes": [[i * 10.0, 0.0, i * 10.0, 0] for i in range(n)]}
    assert all("parents" not in part for part in pk.strips(doc))


def test_strips_carry_the_route_only_flags_with_their_rows(monkeypatch):
    import sys
    import numpy as np
    sys.path.insert(0, str(REPO / "scripts" / "lmr_area"))
    import pack_walk_surfaces as pk
    monkeypatch.setattr(pk, "MAX_NODES_PER_FILE", 100)
    n = 400
    flags = [1 if i % 7 == 0 else 0 for i in range(n)]
    doc = {"epsg": 28356, "built": "x", "bbox_m": [0.0, -10.0, n * 10.0, 10.0], "anchors": [{"name": "A"}], "graph_nodes": n, "route_only": flags,
           "nodes": [[i * 10.0, 0.0, i * 10.0, 0] for i in range(n)], "parents": [-1] + list(range(n - 1))}
    for part in pk.strips(doc):
        xs = np.asarray(part["nodes"])[:, 0]
        assert [int(f) for f in part["route_only"]] == [1 if int(round(x / 10)) % 7 == 0 else 0 for x in xs]


def test_every_crossings_only_file_carries_route_pointers_and_route_only_flags():
    import sys
    sys.path.insert(0, str(REPO / "scripts" / "lmr_area"))
    safe_dir = REPO / "data" / "lmr_walk_safe"
    for f in sorted(safe_dir.glob("*.npz")):
        s = ws.load_surface(str(f))
        assert s.parent is not None, f.name                           # a file without pointers cannot give a route
        assert s.route_only.any() and not s.route_only.all(), f.name   # busy-road side copies are stored, flagged, and never the only rows
        assert (s.parent[~s.route_only] != np_arange_like(s)[~s.route_only]).all(), f.name


def np_arange_like(s):
    import numpy as np
    return np.arange(len(s.parent))


def test_the_route_normal_files_are_exactly_the_shipped_set_with_the_normal_rule_and_pointers():
    import sys
    sys.path.insert(0, str(REPO / "scripts" / "lmr_area"))
    import pack_walk_surfaces as pk
    route_dir = REPO / "data" / "lmr_route_normal"
    assert sorted(p.name for p in route_dir.glob("*.npz")) == sorted(pk.ROUTE_NORMAL_SHIPPED_FILES)
    for f in sorted(route_dir.glob("*.npz")):
        assert f.stat().st_size < REPO_FILE_LIMIT, f.name
        s = ws.load_surface(str(f))
        assert s.walk_rule == "original", f.name                     # the normal rule, not the crossings-only one
        assert s.parent is not None and not s.route_only.any(), f.name
        assert s.graph_nodes >= ws.MIN_NODES and s.anchors, f.name
    # the same areas as the files that decide the answer: no area silently has no normal route
    def area(name):
        return name.split("-1of")[0].split("-2of")[0].split("-3of")[0].split("-4of")[0].replace(".npz", "")
    assert {area(p.name) for p in route_dir.glob("*.npz")} == {area(p.name) for p in WALK_DIR.glob("*.npz")}


def test_the_files_that_decide_the_answer_still_have_no_route_pointers():
    """The route set is separate on purpose: data/lmr_walk/ decides verdicts and was not rebuilt. If it gains pointers, the two sets must be reconsidered."""
    for f in sorted(WALK_DIR.glob("*.npz")):
        assert ws.load_surface(str(f)).parent is None, f.name
