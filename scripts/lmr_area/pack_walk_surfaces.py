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


def strips(doc: dict) -> list[dict]:
    nodes = np.asarray(doc["nodes"], dtype=float).reshape(-1, 4)
    if len(nodes) <= MAX_NODES_PER_FILE:
        return [doc]
    k = int(np.ceil(len(nodes) / (MAX_NODES_PER_FILE * 0.8)))   # 0.8: leave room for the overlap
    cuts = np.quantile(nodes[:, 0], np.linspace(0, 1, k + 1))
    x_lo, y_lo, x_hi, y_hi = doc["bbox_m"]
    out = []
    for i in range(k):
        core_lo = x_lo if i == 0 else float(cuts[i])
        core_hi = x_hi if i == k - 1 else float(cuts[i + 1]) + OVERLAP_M
        keep = (nodes[:, 0] >= core_lo - NODE_MARGIN_M) & (nodes[:, 0] <= core_hi + NODE_MARGIN_M)
        part = dict(doc)
        part["bbox_m"] = [core_lo, y_lo, core_hi, y_hi]
        part["nodes"] = nodes[keep]
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
