# prior-art-checked: four sweeps 2026-11-07 on feat/lmr-clean-law. (1) DB: none read or written; surfaces are
# files built offline by scripts/build_lmr_walk_surfaces.py. (2) Frontend: nothing computes a walk.
# (3) Python: the city2graph service (silent 0 m outside the Inner West) and the stage-1 evidence scripts
# stage1_walk2.py / stage1_osrm.py (research, not in the repo). services/ has no precomputed-surface reader.
# (4) Plans: ce-eligible-homes-GATE-FIX-DESIGN-2026-11-07.md option 3 (chosen), invariants section.
"""Walking distance from a lot to the nearest low-and-mid-rise anchor, read from a precomputed surface.

A surface is one file per area: every footpath-network node within a cutoff of an anchor, with its
shortest walking distance to the nearest anchor (all station entrances and every Town Centre polygon in the
area, in one multi-source run). Looking a lot up is then a nearest-node search, not a routing request.

The walk is measured from ANY part of the lot (s163 definition paragraph (b) takes the whole site if part is
within the distance), so the start is every sampled point of the lot outline, not one address point.

Every failure is a result with valid=False and a reason, never a guessed number. The caller turns that into
"cant_tell". Checks that make a number invalid:
  - no surface covers the lot                     (area not built)
  - no mapped footpath node within MAX_GAP_M of the lot outline
  - the surface is thin (fewer nodes than MIN_NODES): the network did not load
  - walk shorter than the straight line minus STRAIGHT_SLACK_M (a walk cannot be shorter than a straight
    line; the slack covers coordinate rounding), unless the lot touches an anchor
  - walk of 0 m for a lot more than 50 m from the nearest anchor (the city2graph failure)
"""
from __future__ import annotations

import gzip
import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Optional

import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
SURFACE_DIR = REPO_ROOT / "data" / "lmr_walk"

# Engineering limits of the lookup, not planning figures.
# With a point every ~15 m along every street (see the surface builder), a lot's frontage is within a few metres of a stored point.
# 80 m was needed only while points sat at junctions, and it let a lot jump sideways to a junction on another street
# (2/87 Dunmore St, South Bexley: 485 m against a real walk of about 850 m). 40 m keeps a start on the street in front of the lot.
MAX_GAP_M = 40.0  # noqa: regulatory-number -- nearest-footpath tolerance for a lot's frontage, not a planning figure
MIN_NODES = 200  # noqa: regulatory-number -- a surface thinner than this did not load a real network
STRAIGHT_SLACK_M = 30.0  # noqa: regulatory-number -- coordinate rounding slack, one lot violated a tighter rule
ZERO_GUARD_M = 50.0  # noqa: regulatory-number -- the city2graph silent-zero guard
SAMPLE_STEP_M = 10.0  # noqa: regulatory-number -- spacing of start points along the lot outline
SNAP_SLACK_M = 10.0  # noqa: regulatory-number -- how much farther than its nearest node a start point may snap
MAX_LOT_EXTENT_M = 600.0  # noqa: regulatory-number -- keeps the gap matrix small; larger lots answer cant_tell


class Surface:
    def __init__(self, doc: dict, name: str = ""):
        self.name = name
        self.epsg: int = doc["epsg"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        self.bbox_m = tuple(doc["bbox_m"])  # (minx, miny, maxx, maxy) in the surface CRS  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        self.built: str = doc["built"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        self.osm_extract: str = doc.get("osm_extract", "")
        self.anchors: list[dict] = doc["anchors"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        arr = np.asarray(doc["nodes"], dtype=float).reshape(-1, 4)  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        self.xy = arr[:, :2]
        self.dist = arr[:, 2]
        self.anchor_idx = arr[:, 3].astype(int)
        self.graph_nodes: int = int(doc.get("graph_nodes", len(arr)))

    def covers(self, minx: float, miny: float, maxx: float, maxy: float) -> bool:
        b = self.bbox_m
        return b[0] <= minx and b[1] <= miny and maxx <= b[2] and maxy <= b[3]


# prior-art-checked: reuse not viable: the files the guard lists read PDFs and legislation documents; none reads or writes a walking
# surface. This adds a binary form of the SAME surface this module already loads (the repo refuses files over 2 MB and ignores .gz).
def write_npz(doc: dict, path: Path) -> None:
    """Pack a surface document into a compact binary file: coordinates and distances as integers in 0.1 m units, one file.

    The repo refuses files over 2 MB and ignores .gz files, and the JSON form of the largest area is 4 MB; this form is about half that.
    """
    arr = np.asarray(doc["nodes"], dtype=float).reshape(-1, 4)  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    ox, oy = float(np.floor(arr[:, 0].min())), float(np.floor(arr[:, 1].min()))
    order = np.lexsort((arr[:, 1], arr[:, 0]))
    arr = arr[order]
    meta = {k: v for k, v in doc.items() if k != "nodes"}
    meta["origin"] = [ox, oy]
    np.savez_compressed(
        path,
        x=np.round((arr[:, 0] - ox) * 10).astype(np.int32), y=np.round((arr[:, 1] - oy) * 10).astype(np.int32),
        d=np.round(arr[:, 2] * 10).astype(np.uint16), a=arr[:, 3].astype(np.uint16),
        meta=np.array([json.dumps(meta)]))


def _doc_from_npz(path: str) -> dict:
    z = np.load(path, allow_pickle=False)
    meta = json.loads(str(z["meta"][0]))  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    ox, oy = meta.pop("origin")
    meta["nodes"] = np.column_stack([z["x"] / 10.0 + ox, z["y"] / 10.0 + oy, z["d"] / 10.0, z["a"].astype(float)])  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    return meta


@lru_cache(maxsize=64)
def load_surface(path: str) -> Surface:
    if str(path).endswith(".npz"):
        return Surface(_doc_from_npz(path), Path(path).name)
    with gzip.open(path, "rt", encoding="utf-8") as fh:
        return Surface(json.load(fh), Path(path).name)


def available_surfaces(directory: Path = SURFACE_DIR) -> list[Path]:
    if not directory.is_dir():
        return []
    return sorted(list(directory.glob("*.npz")) + list(directory.glob("*.json.gz")))


def sample_outline(coords_m: list[tuple[float, float]], step: float = SAMPLE_STEP_M) -> np.ndarray:
    """Points along a polygon ring every `step` metres, including every vertex."""
    pts: list[tuple[float, float]] = []
    for (x1, y1), (x2, y2) in zip(coords_m, coords_m[1:]):
        seg = math.hypot(x2 - x1, y2 - y1)
        n = max(1, int(seg // step))
        for i in range(n):
            t = i / n
            pts.append((x1 + (x2 - x1) * t, y1 + (y2 - y1) * t))
    pts.append(coords_m[-1])
    return np.asarray(pts, dtype=float)


def _invalid(reason: str, **extra) -> dict:
    return {"m": None, "valid": False, "reason": reason, **extra}


def walk_from_lot(
    ring_m: list[tuple[float, float]],
    epsg: int,
    straight_m: Optional[float],
    touches_anchor: bool,
    surfaces: Optional[list[Surface]] = None,
    required_anchors: Optional[set] = None,
) -> dict:
    """Walking distance from the lot outline (ring in metres, CRS `epsg`) to the nearest anchor.

    Returns {"m", "valid", "reason", "anchor", "entrance_id", "margin_factor", "gap_m", "surface", "built"}.
    """
    if surfaces is None:
        surfaces = [load_surface(str(p)) for p in available_surfaces()]
    if len(ring_m) < 4:
        return _invalid("lot outline has too few points")
    pts = sample_outline(ring_m)
    minx, miny = pts.min(axis=0)
    maxx, maxy = pts.max(axis=0)
    if maxx - minx > MAX_LOT_EXTENT_M or maxy - miny > MAX_LOT_EXTENT_M:
        return _invalid("lot is larger than the size this lookup handles")
    cands =[s for s in surfaces if s.epsg == epsg and s.covers(minx, miny, maxx, maxy)]
    if not cands:
        return _invalid("no walking surface has been built for this area")
    if required_anchors:
        built = {a.get("name") for s in cands for a in s.anchors}
        missing = sorted(set(required_anchors) - built)
        if missing:
            return _invalid(f"no walking surface built for nearby anchor(s): {', '.join(missing[:3])}")
    best: Optional[dict] = None
    notes: list[str] = []
    for s in cands:
        if s.graph_nodes < MIN_NODES or len(s.xy) < MIN_NODES:
            notes.append(f"{s.name}: network too thin ({s.graph_nodes} nodes)")
            continue
        # gap matrix: sample points x surface nodes, only nodes inside the box around the lot matter
        near = (np.abs(s.xy[:, 0] - (minx + maxx) / 2) <= (maxx - minx) / 2 + MAX_GAP_M) & \
               (np.abs(s.xy[:, 1] - (miny + maxy) / 2) <= (maxy - miny) / 2 + MAX_GAP_M)
        if not near.any():
            notes.append(f"{s.name}: no footpath node within {MAX_GAP_M:.0f} m of the lot")
            continue
        nxy, nd, na = s.xy[near], s.dist[near], s.anchor_idx[near]
        gap = np.hypot(pts[:, None, 0] - nxy[None, :, 0], pts[:, None, 1] - nxy[None, :, 1])
        # Snap each start point to its nearest node (plus a small slack): without this limit a start point could cut
        # diagonally across a block to a node further along, and the walk would come out too short.
        gmin = gap.min(axis=1, keepdims=True)
        allowed = (gap <= MAX_GAP_M) & (gap <= gmin + SNAP_SLACK_M)
        total = np.where(allowed, gap + nd[None, :], np.inf)
        flat = int(np.argmin(total))
        i, j = divmod(flat, total.shape[1])
        if not np.isfinite(total[i, j]):
            notes.append(f"{s.name}: no footpath node within {MAX_GAP_M:.0f} m of the lot")
            continue
        cand = {"m": float(total[i, j]), "gap_m": float(gap[i, j]), "anchor_i": int(na[j]), "surface": s}
        if best is None or cand["m"] < best["m"]:  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
            best = cand
    if best is None:
        return _invalid("; ".join(notes) or "no walking surface answered")
    s: Surface = best.pop("surface")
    a = s.anchors[best["anchor_i"]]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    m = best["m"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    out = {"m": round(m, 1), "valid": True, "reason": "", "anchor": a.get("name"), "entrance_id": a.get("entrance_id"),
           # Set only for a station whose entrance is not mapped: the walk was measured to the station outline, so it can be
           # too short by up to the outline's length. The decision widens the range upward by this much.
           "optimistic_by_m": float(a.get("optimistic_by_m") or 0), "gap_m": round(best["gap_m"], 1),  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
           "surface": s.name, "built": s.built, "osm_extract": s.osm_extract}
    if straight_m is not None and not touches_anchor and m < straight_m - STRAIGHT_SLACK_M:
        return {**out, "valid": False, "reason": f"walk ({m:.0f} m) is shorter than the straight line ({straight_m:.0f} m)"}
    if m <= 0 and straight_m is not None and straight_m > ZERO_GUARD_M:
        return {**out, "valid": False, "reason": "walk came out as zero for a lot that is not at an anchor"}
    return out
