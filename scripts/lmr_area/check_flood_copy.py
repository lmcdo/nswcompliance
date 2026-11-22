# prior-art-checked: four sweeps 2026-11-22. (1) DB: reads spatial_overlays (full-detail HNRFS_2024 flood rows), read-only. (2) Frontend: none. (3) Python: scripts/lmr_area/check_route_pointers.py and the
# 50-lot map-copy compare (PR 1674) check other copies; none checks the flood copy against its source. (4) Plans: ce-evidence-flood-pmf-and-pipeline-SCOPE-2026-11-22.md (proof step 1).
"""Check our committed flood copy against the full-detail rows it was made from.

    python scripts/lmr_area/check_flood_copy.py [N]       # default 600 points, fixed seed; exits 1 on any failure

Points: half random inside the flood study's box, half placed 0 to 300 m from a randomly chosen flood-area edge (where a simplified copy is most likely to be wrong).
For every point the copy (services/lmr_map_copy.flood_distance, as the area check will call it) is compared with the source (PostGIS, unsimplified, read-only session).
FAIL if: the source says INSIDE and the copy says clear (outside and farther than the margin from every edge); or the copy's edge distance differs from the source's by more than
more than MAX_DIFF_M (about two simplification steps). Disagreements near the edge that the margin already covers are counted and listed, not hidden.
"""
from __future__ import annotations

import math
import os
import random
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from scripts.lmr_area.export_flood_copy import database_url   # noqa: E402
from services import lmr_map_copy as mc   # noqa: E402

MAX_DIFF_M = 25.0   # noqa: regulatory-number -- the copy's distance to an edge may differ from the source's by at most this (simplification is about 10 m), not a planning figure
KEYS = ("hn_pmf",)


def main(argv: list[str]) -> int:
    n = int(argv[0]) if argv else 600
    rnd = random.Random(20261122)
    import psycopg2

    conn = psycopg2.connect(database_url(), connect_timeout=15)
    try:
        return _run(conn, n, rnd)
    finally:
        conn.close()   # released on every path, including a failure part way through


def _run(conn, n: int, rnd) -> int:
    conn.set_session(readonly=True, autocommit=True)
    cur = conn.cursor()
    cur.execute("SET statement_timeout = 25000")
    copy = mc.MapCopy()
    lay = copy.layer("hn_pmf")
    if lay is None:
        print("FAIL: the committed copy did not load")
        return 1
    minx, miny, maxx, maxy = lay.bounds
    pts: list[tuple[float, float, str]] = []
    for _ in range(n // 2):
        pts.append((rnd.uniform(minx, maxx), rnd.uniform(miny, maxy), "random"))
    verts = [c for g in lay.geoms for poly in getattr(g, "geoms", [g]) for c in poly.exterior.coords][::7]
    for _ in range(n - n // 2):
        x, y = rnd.choice(verts)
        d, a = rnd.uniform(0, 300), rnd.uniform(0, 2 * math.pi)
        pts.append((x + d * math.cos(a) / (111320 * math.cos(math.radians(y))), y + d * math.sin(a) / 110540, "near edge"))
    bad_clear, bad_flip, big_diff, margin_cases = [], [], [], 0
    inside_n = 0
    for i, (x, y, kind) in enumerate(pts):
        got = copy.flood_distance("hn_pmf", y, x)
        cur.execute("SELECT bool_or(ST_Intersects(geom, ST_SetSRID(ST_Point(%s,%s),4326))), "
                    "min(ST_Distance(geom::geography, ST_SetSRID(ST_Point(%s,%s),4326)::geography)), "
                    "min(ST_Distance(ST_Boundary(geom)::geography, ST_SetSRID(ST_Point(%s,%s),4326)::geography)) "
                    "FROM spatial_overlays WHERE instrument_key = 'HNRFS_2024_PMF' AND geom && ST_Expand(ST_SetSRID(ST_Point(%s,%s),4326), 0.01)", (x, y, x, y, x, y, x, y))
        src_in, src_d, src_edge = cur.fetchone()
        src_in = bool(src_in)
        inside_n += src_in
        if got is None:
            print("FAIL: the copy gave no answer")
            return 1
        copy_clear = (not got["inside"]) and (got["edge_m"] is None or got["edge_m"] > mc.FLOOD_EDGE_M)
        if src_in and copy_clear:
            bad_clear.append((x, y, kind))
        if src_in != got["inside"]:
            if (src_edge is not None and src_edge > mc.FLOOD_EDGE_M) or (got["edge_m"] is not None and got["edge_m"] > mc.FLOOD_EDGE_M):
                bad_flip.append((x, y, kind, src_in, got["inside"]))
            else:
                margin_cases += 1   # a flip within the margin of an edge: the area check calls these "on the edge", never clear
        if src_edge is not None and got["edge_m"] is not None and abs(src_edge - got["edge_m"]) > MAX_DIFF_M and src_edge < 1000:
            big_diff.append((x, y, round(src_edge, 1), got["edge_m"]))
        if (i + 1) % 100 == 0:
            print(f"  {i + 1}/{len(pts)}", flush=True)
    print(f"points {len(pts)} ({inside_n} inside the source flood area)")
    print(f"source INSIDE but copy says clear: {len(bad_clear)}  <- must be 0")
    print(f"inside/outside flips beyond the margin: {len(bad_flip)}  <- must be 0")
    print(f"flips within the margin of an edge (area check says 'on the edge'): {margin_cases}")
    print(f"edge distance differing by more than {MAX_DIFF_M:g} m (source edge under 1 km): {len(big_diff)}")
    for b in (bad_clear + bad_flip + big_diff)[:8]:
        print("   ", b)
    return 1 if (bad_clear or bad_flip or big_diff) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
