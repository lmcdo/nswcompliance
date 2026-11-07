#!/usr/bin/env python3
"""Rebuild and check the data behind the low-and-mid-rise area check, one step at a time, in the right order.

  python scripts/lmr_area/run_lmr_area_pipeline.py stations   # station entrances: OpenStreetMap, TfNSW GTFS Pathways, outlines, tested rule
  python scripts/lmr_area/run_lmr_area_pipeline.py surfaces   # walking files per area from OpenStreetMap footpaths (slow: ~5 minutes)
  python scripts/lmr_area/run_lmr_area_pipeline.py pack       # pack them into data/lmr_walk/ (the repo refuses files over 2 MB)
  python scripts/lmr_area/run_lmr_area_pipeline.py test SEED  # the area check against an independent router, then score it (PASS/FAIL)
  python scripts/lmr_area/run_lmr_area_pipeline.py tod        # the Chapter 5 (TOD) check on about 30 lots
  python scripts/lmr_area/run_lmr_area_pipeline.py verify     # every expected committed data file exists and is under the repo limit

Working files go to data/lmr_area_work/ (not committed). One input must be saved by hand first: the TfNSW "GTFS Pathways" stops file
(https://opendata.transport.nsw.gov.au/dataset/gtfs-pathways, CC-BY) as data/lmr_area_work/gtfs_pathways/stops_0.txt.
"""
# prior-art-checked: 2026-11-07. No script in scripts/ runs this pipeline; the nine steps it calls were written for it (scripts/lmr_area/).
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
SCRIPTS = REPO / "scripts" / "lmr_area"
WORK = Path(os.environ.get("LMR_WORK", REPO / "data" / "lmr_area_work"))

# Test areas: name and south,west,north,east. Each is built as one footpath download (see build_walk_surfaces.py).
AREAS = {
    "inner-west": "-33.99,150.99,-33.78,151.30",
    "georges-river": "-34.06,151.00,-33.93,151.17",
    "cb-bankstown": "-33.95,150.98,-33.88,151.08",
    "kuringgai": "-33.82,151.10,-33.70,151.20",
    "woollahra": "-33.93,151.20,-33.85,151.29",
}
EXPECTED_WALK_FILES = [
    "data/lmr_walk/cb-bankstown.npz", "data/lmr_walk/georges-river.npz", "data/lmr_walk/inner-west-1of3.npz",
    "data/lmr_walk/inner-west-2of3.npz", "data/lmr_walk/inner-west-3of3.npz", "data/lmr_walk/kuringgai.npz",
    "data/lmr_walk/woollahra.npz",
]
REPO_FILE_LIMIT = 2 * 1024 * 1024


def run(script: str, *args: str, env: dict | None = None) -> None:
    cmd = [sys.executable, str(SCRIPTS / script), *args]
    print("==>", " ".join(Path(c).name if c.endswith(".py") else c for c in cmd), flush=True)
    r = subprocess.run(cmd, cwd=REPO, env={**os.environ, "LMR_WORK": str(WORK), **(env or {})})
    if r.returncode != 0:
        sys.exit(f"step failed: {script} (exit {r.returncode})")


def stations() -> None:
    run("build_station_entrances.py")            # writes lmr_station_entrances.json in the working folder
    run("merge_gtfs_entrances.py")               # adds official entrances -> lmr_station_entrances_merged.json
    run("add_station_footprints.py")             # outlines for stations with none -> lmr_station_entrances_final.json
    run("entrance_rule_test.py", "60")           # tests the entrance-finding rule on stations whose entrances are known; caches its data
    run("apply_entrance_rule.py")                # applies the tested rule -> lmr_station_entrances_v3.json
    shutil.copyfile(WORK / "lmr_station_entrances_v3.json", REPO / "data" / "law" / "lmr_station_entrances.json")
    print("wrote data/law/lmr_station_entrances.json")


def surfaces() -> None:
    env = {"LMR_STATIONS": "lmr_station_entrances_v3.json", "LMR_SURF_DIR": "walk_surfaces"}
    for name, box in AREAS.items():
        run("build_walk_surfaces.py", f"--bbox={box}", f"--name={name}", env=env)


def pack() -> None:
    run("pack_walk_surfaces.py", str(WORK / "walk_surfaces"), str(REPO / "data" / "lmr_walk"))


def test(seed: str) -> None:
    env = {"LMR_STATIONS": "lmr_station_entrances_v3.json", "LMR_SURF_DIR": "walk_surfaces", "LMR_RESULTS": f"results_{seed}.json"}
    run("area_check_test.py", "--n", "100", "--seed", seed, env=env)
    run("area_check_score.py", f"results_{seed}.json")


def verify() -> int:
    bad = 0
    for rel in EXPECTED_WALK_FILES + ["data/law/lmr_station_entrances.json"]:
        p = REPO / rel
        if not p.is_file():
            print("MISSING", rel)
            bad += 1
        elif p.stat().st_size >= REPO_FILE_LIMIT:
            print("TOO BIG", rel)
            bad += 1
    print("verify:", "OK" if not bad else f"{bad} problem(s)")
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    cmd = argv[0] if argv else ""
    if cmd == "stations":
        stations()
    elif cmd == "surfaces":
        surfaces()
    elif cmd == "pack":
        pack()
    elif cmd == "test":
        test(argv[1] if len(argv) > 1 else "20261110")
    elif cmd == "tod":
        run("tod_check.py")
    elif cmd == "verify":
        return verify()
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
