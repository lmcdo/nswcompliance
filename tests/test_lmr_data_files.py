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
    for needed in ("data/law/housing_sepp_lmr_facts.json", "data/law/lmr_station_entrances.json", "data/lmr_walk/", "data/anef/sydney_anef_2045.json"):
        assert any(line.startswith("COPY") and needed in line for line in docker.splitlines()), needed
    assert (REPO / "data" / "law" / "housing_sepp_lmr_facts.json").is_file()
    assert (REPO / "data" / "anef" / "sydney_anef_2045.json").is_file()
