"""Pack the walking-surface builder's JSON output into the compact files committed under data/lmr_walk/.

The repo refuses files over 2 MB, so a big area is cut into strips by easting. Strips overlap by OVERLAP_M so a lot that sits on a cut
is still entirely inside at least one strip's covered box, and each strip keeps the nodes up to NODE_MARGIN_M beyond its covered box so
a lot near the edge still finds the street in front of it. Every strip keeps the full anchor list of its area, because the walk check
requires that every anchor within reach has a built surface.

Usage: python scripts/lmr_area/pack_walk_surfaces.py [INPUT_DIR] [OUTPUT_DIR]
       (defaults: data/lmr_area_work/walk_surfaces -> data/lmr_walk)
"""
# prior-art-checked: 2026-11-07. No script in scripts/ packs walking surfaces; services/lmr_walk_surface.write_npz is the writer this uses.
import gzip
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from services import lmr_walk_surface as ws  # noqa: E402

MAX_NODES_PER_FILE = 260_000   # about 1.5 MB packed; the repo limit is 2 MB per file
OVERLAP_M = 300.0              # engineering overlap between neighbouring strips (a lot is at most 600 m across; see MAX_LOT_EXTENT_M)
NODE_MARGIN_M = 100.0          # nodes kept beyond a strip's covered box so the street in front of an edge lot is present

# The packed crossings-only walk files committed under data/lmr_walk_safe/ (built with build_walk_surfaces.py --safe, packed with this script).
# tests/test_lmr_data_files.py checks the folder holds exactly these, so a missing or extra file fails a test instead of silently dropping an area.
SAFE_SHIPPED_FILES = (
    "cb-bankstown.npz", "georges-river.npz", "kuringgai.npz", "woollahra.npz",
    "inner-west-1of4.npz", "inner-west-2of4.npz", "inner-west-3of4.npz", "inner-west-4of4.npz",
    "pilot-blacktown.npz", "pilot-hornsby.npz", "pilot-northern_beaches.npz", "pilot-parramatta.npz",
    "pilot-penrith.npz", "pilot-waverley.npz", "pilot-wollongong.npz",
)
# The packed normal-rule files committed under data/lmr_route_normal/: the same areas built WITHOUT --safe from the same map cut, kept only so
# the evidence page can draw the normal route (they carry route pointers; the files that decide the answer, data/lmr_walk/, do not).
# tests/test_lmr_data_files.py checks the folder holds exactly these. After any rebuild run scripts/lmr_area/check_route_pointers.py on both folders.
ROUTE_NORMAL_SHIPPED_FILES = (
    "cb-bankstown.npz", "georges-river.npz", "kuringgai.npz", "woollahra.npz",
    "inner-west-1of3.npz", "inner-west-2of3.npz", "inner-west-3of3.npz",
    "pilot-blacktown.npz", "pilot-hornsby.npz", "pilot-northern_beaches.npz", "pilot-parramatta.npz",
    "pilot-penrith.npz", "pilot-waverley.npz", "pilot-wollongong.npz",
)


def close_under_pointers(keep: np.ndarray, parents: np.ndarray) -> np.ndarray:
    """Add to `keep` every point that a kept point's route passes through, so each route stays whole inside its own strip file.

    A route can leave the strip it starts in (the station may be in the next strip); without this the pointer would point at a point
    that is not in the file. Only the points ON those routes are added (one chain per kept point, merged), not their neighbours."""
    keep = keep.copy()
    while True:
        nxt = parents[keep]
        nxt = nxt[nxt >= 0]
        new = nxt[~keep[nxt]]
        if len(new) == 0:
            return keep
        keep[new] = True


def strips(doc: dict) -> list[dict]:
    nodes = np.asarray(doc["nodes"], dtype=float).reshape(-1, 4)
    if len(nodes) <= MAX_NODES_PER_FILE:
        return [doc]
    parents = np.asarray(doc["parents"], dtype=np.int64).reshape(-1) if doc.get("parents") is not None else None
    if parents is not None and len(parents) != len(nodes):
        raise ValueError("route pointers and nodes differ in length")
    k = int(np.ceil(len(nodes) / (MAX_NODES_PER_FILE * 0.8)))   # 0.8: leave room for the overlap
    cuts = np.quantile(nodes[:, 0], np.linspace(0, 1, k + 1))
    x_lo, y_lo, x_hi, y_hi = doc["bbox_m"]
    out = []
    for i in range(k):
        core_lo = x_lo if i == 0 else float(cuts[i])
        core_hi = x_hi if i == k - 1 else float(cuts[i + 1]) + OVERLAP_M
        keep = (nodes[:, 0] >= core_lo - NODE_MARGIN_M) & (nodes[:, 0] <= core_hi + NODE_MARGIN_M)
        if parents is not None:
            keep = close_under_pointers(keep, parents)
        part = dict(doc)
        part["bbox_m"] = [core_lo, y_lo, core_hi, y_hi]
        part["nodes"] = nodes[keep]
        if parents is not None:   # renumber each pointer to its target's row in this strip (the target is always kept: the strip is closed)
            new_row = np.cumsum(keep) - 1
            kept_p = parents[keep]
            part["parents"] = np.where(kept_p >= 0, new_row[np.clip(kept_p, 0, None)], -1)
        if doc.get("route_only") is not None:   # the flags follow their rows; absent stays absent
            part["route_only"] = np.asarray(doc["route_only"], dtype=np.int64).reshape(-1)[keep]  # noqa: bracket-access -- guarded by the .get() above
        if doc.get("stranded") is not None:   # absent stays absent: "not calculated" is not "calculated, none"
            st = np.asarray(doc["stranded"], dtype=float).reshape(-1, 2)  # noqa: bracket-access -- guarded by the .get() above
            part["stranded"] = st[(st[:, 0] >= core_lo - NODE_MARGIN_M) & (st[:, 0] <= core_hi + NODE_MARGIN_M)] if len(st) else st
        if doc.get("busy_pts") is not None:   # same rule as the stranded list: trimmed to the strip, absent stays absent
            bp = np.asarray(doc["busy_pts"], dtype=float).reshape(-1, 2)  # noqa: bracket-access -- guarded by the .get() above
            part["busy_pts"] = bp[(bp[:, 0] >= core_lo - NODE_MARGIN_M) & (bp[:, 0] <= core_hi + NODE_MARGIN_M)] if len(bp) else bp
        out.append(part)
    return out


def main(argv: list[str]) -> int:
    src = Path(argv[0]) if argv else REPO / "data" / "lmr_area_work" / "walk_surfaces"
    dst = Path(argv[1]) if len(argv) > 1 else REPO / "data" / "lmr_walk"
    dst.mkdir(parents=True, exist_ok=True)
    files = sorted(src.glob("*.json.gz"))
    if not files:
        print(f"no input files in {src}")
        return 1
    for f in files:
        with gzip.open(f, "rt", encoding="utf-8") as fh:
            doc = json.load(fh)
        name = f.name[: -len(".json.gz")]
        parts = strips(doc)
        for i, part in enumerate(parts):
            out = dst / (f"{name}.npz" if len(parts) == 1 else f"{name}-{i + 1}of{len(parts)}.npz")
            ws.write_npz(part, out)
            print(f"{out.name}: {len(part['nodes'])} nodes, {out.stat().st_size // 1024} KB")
            if out.stat().st_size > 2 * 1024 * 1024:
                print("  TOO BIG for the repo (2 MB limit): lower MAX_NODES_PER_FILE")
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
