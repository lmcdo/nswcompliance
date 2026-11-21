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
# Optional second set, built with the safe-crossing rule (scripts/lmr_area/build_walk_surfaces.py --safe). Absent = no second walk shown.
SAFE_SURFACE_DIR = REPO_ROOT / "data" / "lmr_walk_safe"
# The normal-rule walk built from the same map cut as the crossings-only set, with route pointers. Used ONLY to draw the normal route on the
# evidence page; the distances that decide the answer still come from SURFACE_DIR. See services/lmr_route_map.py for when a route is drawn.
ROUTE_SURFACE_DIR = REPO_ROOT / "data" / "lmr_route_normal"

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
NEAR_BUSY_M = 30.0  # noqa: regulatory-number -- a lot this close to a busy road may snap to a footpath on its far side; busy-road points are ~25 m apart


class Surface:
    def __init__(self, doc: dict, name: str = ""):
        self.name = name
        self.epsg: int = doc["epsg"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        self.bbox_m = tuple(doc["bbox_m"])  # (minx, miny, maxx, maxy) in the surface CRS  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        self.built: str = doc["built"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        self.osm_extract: str = doc.get("osm_extract") or ""
        self.anchors: list[dict] = doc["anchors"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        arr = np.asarray(doc["nodes"], dtype=float).reshape(-1, 4)  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
        self.xy = arr[:, :2]
        self.dist = arr[:, 2]
        self.anchor_idx = arr[:, 3].astype(int)
        # Route pointers: row of the next point toward the station, -1 at the end of a walk. None for a file built without them, or when
        # they do not fit the points (a route is never drawn from pointers that could point somewhere else).
        raw_p = doc.get("parents")
        p = np.asarray(raw_p, dtype=np.int64).reshape(-1) if raw_p is not None else None
        self.parent = p if (p is not None and len(p) == len(arr)
                            and (len(p) == 0 or (p.min() >= -1 and p.max() < len(arr) and not bool(np.any(p == np.arange(len(p))))))) else None   # a point pointing at itself is no route
        # Rows that are on a route but are NOT places a lot can start from (busy-road side copies share their coordinates with the other side's
        # copy, so matching one could take the wrong side's distance). The lot lookup ignores them. Older files have none (all rows matchable, as
        # before). A flag list that is PRESENT but does not fit is refused: ignoring it would make the side copies matchable and could give a lot a
        # plausible but wrong distance, so the file is rejected visibly instead.
        raw_ro = doc.get("route_only")
        if raw_ro is None:
            self.route_only = np.zeros(len(arr), dtype=bool)
        else:
            ro = np.asarray(raw_ro, dtype=np.int64).reshape(-1)
            if len(ro) != len(arr) or (len(ro) and (ro.min() < 0 or ro.max() > 1)):
                raise ValueError(f"route_only flags do not fit the points of {name or 'this surface'}: the file is not used")
            self.route_only = ro == 1
        self.graph_nodes: int = int(doc.get("graph_nodes", len(arr)))
        # "original" = every way joins wherever two share a node; anything else (e.g. "safe-crossings-v2") crosses busy roads only at formal crossings
        self.walk_rule: str = str(doc.get("walk_rule") or "original")
        # The distance the build stored out to (declared), not the farthest point it happened to store; older files fall back to the latter.
        declared = doc.get("cutoff_m")
        self.cutoff_m: float = float(self.dist.max()) if len(self.dist) else 0.0
        if declared is not None and isinstance(declared, (int, float)) and not isinstance(declared, bool) and declared > 0:
            self.cutoff_m = float(declared)
        # Footpath points with no route to any station within the cutoff (safe-crossing builds only). Empty for older files.
        self.has_stranded_list: bool = doc.get("stranded") is not None
        self.stranded_xy = np.asarray(doc.get("stranded") if doc.get("stranded") is not None else [], dtype=float).reshape(-1, 2)
        # Points along busy roads, one about every 25 m (safe-crossing builds only). Lets the answer say a lot is next to a busy road.
        self.has_busy_list: bool = doc.get("busy_pts") is not None
        self.busy_xy = np.asarray(doc.get("busy_pts") if doc.get("busy_pts") is not None else [], dtype=float).reshape(-1, 2)
        # A station is only "built" when at least one of its entrances reaches a stored footpath node. The anchor list holds every
        # station name, including ones whose entrances sit outside the footpath download (46 to 52 of 83 names in the Inner West files).
        used = set(np.unique(self.anchor_idx[~self.route_only]).tolist())
        self.names_with_nodes = {a.get("name") for i, a in enumerate(self.anchors) if i in used}

    def route_rows(self, idx: int) -> Optional[list[int]]:
        """The stored points on the shortest walk from point `idx` to the station, following the route pointers; the last row is the
        point the station link joins. None when this file has no usable pointers or the chain is not a walk toward a station.

        A chain is refused (None), never cut short, when the walk distance ever goes UP along it or it runs longer than the file: an
        honest "no route" beats a route that wanders."""
        if self.parent is None or not (0 <= idx < len(self.parent)):
            return None
        rows = [int(idx)]
        cur = int(idx)
        for _ in range(len(self.parent)):
            nxt = int(self.parent[cur])
            if nxt < 0:
                return rows
            if self.dist[nxt] > self.dist[cur] + 0.05:   # 0.05 m: the distances are stored to 0.1 m
                return None
            rows.append(nxt)
            cur = nxt
        return None

    def no_walk_reason(self, pts: Optional[np.ndarray] = None) -> str:
        """Why a lot got no walking distance from this surface, in words a planner can act on.

        `pts` are the lot's outline points. When the surface holds stranded footpath points (a safe-crossing build) the two causes are told
        apart: footpath here but no safe route, or no footpath here. A surface without that list cannot tell, and says both."""
        no_path = f"there is no mapped footpath within {MAX_GAP_M:.0f} m of the lot ({self.name})"
        if self.walk_rule == "original":
            return no_path
        route_gone = (f"there is a footpath next to the lot, but the map has no route from it to a station within {self.cutoff_m:.0f} m "
                      "that crosses busy roads only at signals, zebra or marked crossings. A crossing may be missing from the map: check the route on the ground")
        if pts is None or not self.has_stranded_list:   # cannot tell the two apart: say both
            return f"{no_path}, or {route_gone[0].lower() + route_gone[1:]}"
        if len(self.stranded_xy):
            gap = np.hypot(pts[:, None, 0] - self.stranded_xy[None, :, 0], pts[:, None, 1] - self.stranded_xy[None, :, 1]).min()
            if gap <= MAX_GAP_M:
                return f"{route_gone} ({self.name})"
        return no_path

    def near_busy_road(self, pts: np.ndarray) -> Optional[bool]:
        """True if the lot outline is within NEAR_BUSY_M of a busy road, False if not, None if this file has no busy-road list.
        None is not False: an older file cannot say the lot is away from busy roads."""
        if not self.has_busy_list:
            return None
        if not len(self.busy_xy):
            return False
        lo, hi = pts.min(axis=0) - NEAR_BUSY_M, pts.max(axis=0) + NEAR_BUSY_M
        b = self.busy_xy[(self.busy_xy[:, 0] >= lo[0]) & (self.busy_xy[:, 0] <= hi[0]) & (self.busy_xy[:, 1] >= lo[1]) & (self.busy_xy[:, 1] <= hi[1])]
        if not len(b):
            return False
        return bool(np.hypot(pts[:, None, 0] - b[None, :, 0], pts[:, None, 1] - b[None, :, 1]).min() <= NEAR_BUSY_M)

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
    meta = {k: v for k, v in doc.items() if k not in ("nodes", "stranded", "busy_pts", "parents", "route_only")}
    route_only = None
    if doc.get("route_only") is not None:   # rows that are on a route but must never be matched to a lot (busy-road side copies)
        ro = np.asarray(doc["route_only"], dtype=np.int64).reshape(-1)  # noqa: bracket-access -- guarded by the .get() above
        if len(ro) != len(order) or (len(ro) and (ro.min() < 0 or ro.max() > 1)):
            raise ValueError("route_only flags and nodes differ in length, or a flag is not 0 or 1")
        route_only = ro[order].astype(np.uint8)
    # Route pointers (row of the next point toward the station, -1 at the end of a walk). The rows are re-sorted above, so each
    # pointer is renumbered to the row its target now has. Written only when the build produced them: an older file has none.
    parent = None
    if doc.get("parents") is not None:
        p_old = np.asarray(doc["parents"], dtype=np.int64).reshape(-1)  # noqa: bracket-access -- guarded by the .get() above
        if len(p_old) != len(order):
            raise ValueError("route pointers and nodes differ in length")
        if len(p_old) and (p_old.max() >= len(order) or p_old.min() < -1):
            raise ValueError("a route pointer points outside the stored points")
        rank = np.empty(len(order), dtype=np.int64)
        rank[order] = np.arange(len(order))                 # old row -> new row
        p_sorted = p_old[order]
        parent = np.where(p_sorted >= 0, rank[np.clip(p_sorted, 0, max(len(order) - 1, 0))], -1).astype(np.int32)
    meta["origin"] = [ox, oy]
    # Written only when the build produced a list: a file without one must not claim "nothing is stranded".
    st = np.asarray(doc["stranded"], dtype=float).reshape(-1, 2) if doc.get("stranded") is not None else None  # noqa: bracket-access -- guarded by the .get() on this line
    extra = {} if st is None else {"sx": np.round((st[:, 0] - ox) * 10).astype(np.int32), "sy": np.round((st[:, 1] - oy) * 10).astype(np.int32)}
    bp = np.asarray(doc["busy_pts"], dtype=float).reshape(-1, 2) if doc.get("busy_pts") is not None else None  # noqa: bracket-access -- guarded by the .get() on this line
    if bp is not None:   # written only when the build produced a list, like the stranded list
        extra.update(bx=np.round((bp[:, 0] - ox) * 10).astype(np.int32), by=np.round((bp[:, 1] - oy) * 10).astype(np.int32))
    if parent is not None:
        extra["p"] = parent
    if route_only is not None:
        extra["ro"] = route_only
    np.savez_compressed(
        path, **extra,
        x=np.round((arr[:, 0] - ox) * 10).astype(np.int32), y=np.round((arr[:, 1] - oy) * 10).astype(np.int32),
        d=np.round(arr[:, 2] * 10).astype(np.uint16), a=arr[:, 3].astype(np.uint16),
        meta=np.array([json.dumps(meta)]))


def _doc_from_npz(path: str) -> dict:
    z = np.load(path, allow_pickle=False)
    meta = json.loads(str(z["meta"][0]))  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    ox, oy = meta.pop("origin")
    if "sx" in z.files:   # older files have no stranded list
        meta["stranded"] = np.column_stack([z["sx"] / 10.0 + ox, z["sy"] / 10.0 + oy]) if len(z["sx"]) else np.empty((0, 2))  # noqa: bracket-access -- "sx" is in z.files, checked on the line above
    if "bx" in z.files:   # older files have no busy-road list
        meta["busy_pts"] = np.column_stack([z["bx"] / 10.0 + ox, z["by"] / 10.0 + oy]) if len(z["bx"]) else np.empty((0, 2))  # noqa: bracket-access -- "bx" is in z.files, checked on the line above
    if "p" in z.files:   # older files have no route pointers
        meta["parents"] = z["p"]  # noqa: bracket-access -- "p" is in z.files, checked on the line above
    if "ro" in z.files:   # older files have no route-only rows
        meta["route_only"] = z["ro"]  # noqa: bracket-access -- "ro" is in z.files, checked on the line above
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


# prior-art-checked: nothing in services/ or scripts/ hashes the walking files; the accuracy record (data/lmr_area_accuracy.json,
# written by scripts/lmr_area/area_check_score.py, read by scripts/outreach_claim_checks.py OC-22) needs one shared definition.
def data_fingerprint(root: Path = REPO_ROOT) -> str:
    """One hash of the data the area check serves: every walking file, the station entrances and the saved law figures.

    JSON files are hashed as parsed (sorted keys), so a Windows and a Linux checkout of the same file give the same hash.
    """
    import hashlib

    h = hashlib.sha256()
    for p in sorted((root / "data" / "lmr_walk").glob("*.npz")):
        h.update(p.name.encode())
        h.update(p.read_bytes())
    for rel in ("data/law/lmr_station_entrances.json", "data/law/housing_sepp_lmr_facts.json"):
        h.update(json.dumps(json.loads((root / rel).read_text(encoding="utf-8")), sort_keys=True).encode())
    return h.hexdigest()


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


SAFE_WALK_RULE = "safe-crossings-v2"   # must equal scripts/lmr_area/safe_crossings.RULE_NAME; tests/test_lmr_walk_surface.py checks that


def walk_from_lot_safe(ring_m, epsg, straight_m, touches_anchor, surfaces, required_anchors=None, want_route: bool = False) -> dict:
    """The crossings-only walk. Refuses any surface not built with the safe-crossing rule: an old-rule file in the safe folder would
    otherwise be shown as a walk that crosses busy roads only at formal crossings."""
    wrong = [s.name for s in surfaces if s.walk_rule != SAFE_WALK_RULE]   # an exact match: a typo or a future rule name is refused too
    if wrong:
        return _invalid(f"the crossings-only map folder holds a file built without the safe-crossing rule ({wrong[0]}), so it was not used")
    return walk_from_lot(ring_m, epsg, straight_m, touches_anchor, surfaces, required_anchors=required_anchors, want_route=want_route)


def _invalid(reason: str, **extra) -> dict:
    return {"m": None, "valid": False, "reason": reason, **extra}


def walk_from_lot(
    ring_m: list[tuple[float, float]],
    epsg: int,
    straight_m: Optional[float],
    touches_anchor: bool,
    surfaces: Optional[list[Surface]] = None,
    required_anchors: Optional[set] = None,
    want_route: bool = False,
) -> dict:
    """Walking distance from the lot outline (ring in metres, CRS `epsg`) to the nearest anchor.

    Returns {"m", "valid", "reason", "anchor", "entrance_id", "margin_factor", "gap_m", "surface", "built"}.

    With want_route=True a valid result also carries "route": {"epsg", "lot_xy", "points", "length_m", "walk_m", "surface"}: the lot point
    the walk starts from, then the stored points along it to the station link (all in metres in the surface CRS). "points" is None
    when this file has no route pointers or they do not give a walk. Nothing about the distance or the verdict changes with this flag.
    """
    if surfaces is None:
        surfaces = [load_surface(str(p)) for p in available_surfaces()]
    if len(ring_m) < 4:
        return _invalid("the lot outline on the map is too small to measure a walk from")
    pts = sample_outline(ring_m)
    minx, miny = pts.min(axis=0)
    maxx, maxy = pts.max(axis=0)
    if maxx - minx > MAX_LOT_EXTENT_M or maxy - miny > MAX_LOT_EXTENT_M:
        return _invalid("the lot is larger than this check can measure a walk from")
    cands =[s for s in surfaces if s.epsg == epsg and s.covers(minx, miny, maxx, maxy)]
    if not cands:
        return _invalid("we do not have a footpath map for this area yet, so the walk to the nearest station could not be measured")
    if required_anchors:
        built = {n for s in cands for n in s.names_with_nodes}
        missing = sorted(set(required_anchors) - built)
        if missing:
            return _invalid(f"we do not have footpath data for a station or town centre near this lot ({', '.join(missing[:3])}), so the walk could not be measured")
    best: Optional[dict] = None
    notes: list[str] = []
    for s in cands:
        if s.graph_nodes < MIN_NODES or int((~s.route_only).sum()) < MIN_NODES:   # route-only rows are not places a lot can start from
            notes.append(f"the footpath map for this area ({s.name}) is too sparse to measure a walk")
            continue
        # gap matrix: sample points x surface nodes, only nodes inside the box around the lot matter
        near = (np.abs(s.xy[:, 0] - (minx + maxx) / 2) <= (maxx - minx) / 2 + MAX_GAP_M) & \
               (np.abs(s.xy[:, 1] - (miny + maxy) / 2) <= (maxy - miny) / 2 + MAX_GAP_M) & ~s.route_only   # route_only rows are never a start
        if not near.any():
            notes.append(s.no_walk_reason(pts))
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
            notes.append(s.no_walk_reason(pts))
            continue
        cand = {"m": float(total[i, j]), "gap_m": float(gap[i, j]), "anchor_i": int(na[j]), "surface": s,
                "node": int(np.nonzero(near)[0][j]), "lot_xy": (float(pts[i, 0]), float(pts[i, 1]))}
        if best is None or cand["m"] < best["m"]:  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
            best = cand
    if best is None:
        return _invalid("; ".join(notes) or "the footpath map gave no walking distance for this lot")
    s: Surface = best.pop("surface")
    node, lot_xy = best.pop("node"), best.pop("lot_xy")
    a = s.anchors[best["anchor_i"]]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    m = best["m"]  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    out = {"m": round(m, 1), "valid": True, "reason": "", "anchor": a.get("name"), "entrance_id": a.get("entrance_id"),
           # Set only for a station whose entrance is not mapped: the walk was measured to the station outline, so it can be
           # too short by up to the outline's length. The decision widens the range upward by this much.
           "optimistic_by_m": float(a.get("optimistic_by_m") or 0), "gap_m": round(best["gap_m"], 1),  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
           "surface": s.name, "built": s.built, "osm_extract": s.osm_extract,
           "near_busy_road": s.near_busy_road(pts)}   # True / False / None (None: this file has no busy-road list)
    if straight_m is not None and not touches_anchor and m < straight_m - STRAIGHT_SLACK_M:
        return {**out, "valid": False, "reason": f"walk ({m:.0f} m) is shorter than the straight line ({straight_m:.0f} m)"}
    if m <= 0 and straight_m is not None and straight_m > ZERO_GUARD_M:
        return {**out, "valid": False, "reason": "walk came out as zero for a lot that is not at an anchor"}
    if want_route:
        rows = s.route_rows(node)
        pts_xy = [[round(float(s.xy[r, 0]), 1), round(float(s.xy[r, 1]), 1)] for r in rows] if rows else None
        seg = sum(math.hypot(b[0] - a_[0], b[1] - a_[1]) for a_, b in zip(pts_xy, pts_xy[1:])) if pts_xy else None
        # The last stored point is where the station link joins; the link itself (the distance stored at that point, from the point to the
        # station entrance or town-centre edge) is part of the walk but is drawn by the caller, so its length is returned separately and
        # counted in length_m.
        end_gap = float(s.dist[rows[-1]]) if rows else None
        # Busy-road points (a safe-crossing file only) within 150 m of the route, so a map can show which roads the walk goes round.
        busy = []
        if pts_xy and s.has_busy_list and len(s.busy_xy):
            xs, ys = [p[0] for p in pts_xy] + [lot_xy[0]], [p[1] for p in pts_xy] + [lot_xy[1]]
            inside = (s.busy_xy[:, 0] >= min(xs) - 150.0) & (s.busy_xy[:, 0] <= max(xs) + 150.0) & \
                     (s.busy_xy[:, 1] >= min(ys) - 150.0) & (s.busy_xy[:, 1] <= max(ys) + 150.0)
            busy = [[round(float(x), 1), round(float(y), 1)] for x, y in s.busy_xy[inside]]
        out["route"] = {"epsg": s.epsg, "lot_xy": [round(lot_xy[0], 1), round(lot_xy[1], 1)], "points": pts_xy, "surface": s.name,
                        "osm_extract": s.osm_extract, "busy_pts": busy, "anchor": a.get("name"), "entrance_id": a.get("entrance_id"),
                        "walk_m": round(m, 1), "gap_m": round(best["gap_m"], 1),  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
                        "end_gap_m": None if end_gap is None else round(end_gap, 1),
                        "length_m": None if seg is None or end_gap is None else round(best["gap_m"] + seg + end_gap, 1)}  # noqa: bracket-access -- own dict or committed file; a missing key must fail closed (cant_tell)
    return out
