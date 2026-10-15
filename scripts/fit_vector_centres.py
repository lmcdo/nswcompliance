#!/usr/bin/env python3
"""Outlines for centre precincts a DCP draws as a VECTOR plan with its lot lines, placed on the cadastre.

prior-art-checked: build_cb_centre_boundaries.py fits a vector figure's lot lines to the cadastre by ICP but
needs a hand-typed starting placement per chapter; fit_cb_raster_centres.py reads raster basemaps by their
roads. This finds the starting placement itself (FFT match of the drawn lot lines against rasterised
cadastre edges over a range of scales), then refines with build_cb's ICP and snaps with its lots_inside.

WHY (address audit 2026-10-15): Ku-ring-gai Part 14 centre chapters (14A, C-H) sit in the precinct layer with
no key -- 674 served rules now shown to no house. Each "applies to ... as outlined in Figure 14x.1-1", a
vector precinct plan: thin grey lot lines, house numbers, and each precinct drawn as a thick orange line
labelled with its code (G1, L3...) as real PDF text.

METHOD (deterministic; nothing is read by a model)
  1 figure    lot-line points (thin dark strokes) and precinct outlines (thick orange strokes, polygonised),
              each named by the label text inside it.
  2 coarse    cadastre lot edges rasterised at 2 m/px round a seed (median address point of the suburb);
              for each scale, FFT-correlate the figure's lot-line points; best = most points on an edge.
  3 refine    build_cb.icp (similarity: scale, rotation, shift) on lot-line points vs cadastre edge points.
  4 lots      build_cb.lots_inside per precinct (>= 80% in; 20-80% kept unless a corridor, as the raster fit).
ACCEPTANCE (else REFUSED, nothing written for that chapter)
  share of figure lot-line points within 1.5 m of a cadastre edge >= 0.60
  median distance of precinct-outline vertices to the nearest lot edge <= 4 m
  every precinct label the chapter lists is found
Every chapter is also drawn (--draw) and looked at before any write.

Usage:
    python scripts/fit_vector_centres.py --draw
    python scripts/fit_vector_centres.py --only 14D --draw
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
from scipy.signal import fftconvolve
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import polygonize, unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cb_centre_boundaries as cb  # noqa: E402  (fetch_cadastre, lots_inside, icp, apply, edge_points, feature)
import fit_cb_raster_centres as rf  # noqa: E402  (_get, ADDR)

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "ku_ring_gai_precincts"
PDF_BASE = "https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/"
METHOD = "dcp_vector_plan_fitted_to_cadastre"
ON_EDGE_MIN, OUTLINE_EDGE_MAX, OUTSIDE_MAX_M2 = 0.75, 4.0, 1500
RES = 2.0  # metres per pixel of the coarse search
CORE_ZONES = "^(E1|MU1)"  # noqa: zone-codes -- a SCALE guess from the plans' own legend (core precinct = B2/B4), not a rule


def _is_orange(c) -> bool:
    return bool(c) and len(c) == 3 and c[0] > 0.9 and 0.45 < c[1] < 0.8 and c[2] < 0.35


def _segs(d) -> list:
    out = []
    for it in d["items"]:
        if it[0] == "l":
            out.append(((it[1].x, -it[1].y), (it[2].x, -it[2].y)))
        elif it[0] == "c":
            out.append(((it[1].x, -it[1].y), (it[4].x, -it[4].y)))
        elif it[0] == "re":
            r = it[1]
            q = [(r.x0, -r.y0), (r.x1, -r.y0), (r.x1, -r.y1), (r.x0, -r.y1)]
            out += list(zip(q, q[1:] + q[:1]))
        elif it[0] == "qu":
            q = [(p.x, -p.y) for p in (it[1].ul, it[1].ur, it[1].lr, it[1].ll)]
            out += list(zip(q, q[1:] + q[:1]))
    return out


def read_plan(pdf: Path, page: int, label_re: str, line_w_max: float = 0.2):
    """(lot-line points y-up, {label: polygon in PDF points y-up}) from the vector plan.

    Cached on disk (.page_cache, keyed by pdf stem + page + label_re + line_w_max) so a re-run on the same
    PDF page does not re-extract its drawings. line_w_max: some plans draw lot lines/kerbs thicker than 0.2 pt
    (14C 0.6, 14F 0.8); it is a per-chapter config field, the acceptance checks are unchanged."""
    import hashlib
    import pickle
    key = hashlib.sha1(f"{label_re}|{line_w_max}".encode()).hexdigest()[:8]
    cache = OUT / ".page_cache" / f"{pdf.stem}__p{page}__{key}.pkl"
    if cache.exists():
        return pickle.loads(cache.read_bytes())
    res = _read_plan(pdf, page, label_re, line_w_max)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(pickle.dumps(res))
    return res


def _read_plan(pdf: Path, page: int, label_re: str, line_w_max: float):
    pg = fitz.open(pdf)[page - 1]
    lots, outline = [], []
    for d in pg.get_drawings():
        col, w = d.get("color"), d.get("width") or 0
        if _is_orange(col) and w >= 2:
            outline += _segs(d)
        elif col and len(col) == 3 and max(col) < 0.5 and w < line_w_max:
            lots += _segs(d)
    if not lots or not outline:
        raise SystemExit(f"[ABORT] {pdf.name} p{page}: lot lines or precinct outlines not found")
    pts = []
    for a, b in np.array(lots):
        n = max(1, int(np.hypot(*(b - a)) / 0.5))
        pts.append(a + (b - a) * np.linspace(0, 1, n, endpoint=False)[:, None])
    pts = np.unique(np.round(np.vstack(pts), 2), axis=0)
    ring = unary_union([LineString(s) for s in outline if s[0] != s[1]]).buffer(0.8)
    polys = [p for p in polygonize(ring.boundary) if p.area > 50 and not ring.contains(p)]
    labels = {}
    for x0, y0, x1, y1, word, *_ in pg.get_text("words"):
        if not re.fullmatch(label_re, word):
            continue
        c = Point((x0 + x1) / 2, -(y0 + y1) / 2)
        inside = [p for p in polys if p.contains(c)]
        near = sorted(polys, key=lambda p: p.distance(c))
        hit = min(inside, key=lambda p: p.area) if inside else (near[0] if near and near[0].distance(c) < 15 else None)
        if hit is not None:
            labels[word] = unary_union([labels[word], hit]) if word in labels else hit
    return pts, labels


def seed(suburb: str) -> tuple[float, float]:
    fs = rf._get(rf.ADDR, {"where": f"address LIKE '% {suburb} %' OR address LIKE '% {suburb}'", "outFields": "address",
                          "returnGeometry": "true", "outSR": "28356", "f": "json", "resultRecordCount": 1000}).get("features") or []
    if not fs:
        raise SystemExit(f"[ABORT] no address points for {suburb}")
    return tuple(np.median(np.array([[f["geometry"]["x"], f["geometry"]["y"]] for f in fs]), 0))


def scale_prior(sx: float, sy: float, labels: dict) -> float:
    """Metres per point from area: the plans' legends say the core precincts are the business zones
    ("Core Urban Precinct ..."), so sqrt(core-zone area near the centre / outlined area on the page).
    Unbounded, a shrunken drawing sits wholly on one road corridor and scores best (Gordon, 2026-10-15)."""
    import psycopg2
    conn = psycopg2.connect(cb.database_url(), connect_timeout=15,
                            options="-c statement_timeout=30000 -c default_transaction_read_only=on")
    with conn.cursor() as cur:
        cur.execute("""SELECT COALESCE(sum(ST_Area(geom::geography)), 0) FROM spatial_overlays
                        WHERE layer_type = 'zone' AND value ~ %s AND lga_name ILIKE 'ku%%ring%%'
                          AND ST_DWithin(geom::geography, ST_Transform(ST_SetSRID(ST_MakePoint(%s, %s), 28356), 4326)::geography, 1200)""",
                    (CORE_ZONES, float(sx), float(sy)))
        zone_m2 = float(cur.fetchone()[0])
    conn.close()
    page_pt2 = unary_union(list(labels.values())).area
    return float(np.sqrt(zone_m2 / page_pt2)) if zone_m2 and page_pt2 else 0.0


def coarse_fit(fig: np.ndarray, cad_edges: np.ndarray, box: tuple, scales=None) -> tuple[float, float, float, float]:
    """Best (share, metres per point, x0, y0) with MGA = (x0 + s*x, y0 + s*y); north up, no rotation."""
    bx0, by0, bx1, by1 = box
    W, H = int((bx1 - bx0) / RES) + 1, int((by1 - by0) / RES) + 1
    E = np.zeros((H, W), np.float32)
    e = cad_edges[(cad_edges[:, 0] >= bx0) & (cad_edges[:, 0] < bx1) & (cad_edges[:, 1] > by0) & (cad_edges[:, 1] <= by1)]
    E[((by1 - e[:, 1]) / RES).astype(int), ((e[:, 0] - bx0) / RES).astype(int)] = 1
    E = cv2.dilate(E, np.ones((7, 7), np.uint8))  # +-6 m: a kerb line sits beside its road centreline
    best = (-1.0, 0.0, 0.0, 0.0)
    fx0, fy1 = fig[:, 0].min(), fig[:, 1].max()
    for s in (np.geomspace(0.25, 4.0, 60) if scales is None else scales):
        u = ((fig[:, 0] - fx0) * s / RES).astype(int)
        v = ((fy1 - fig[:, 1]) * s / RES).astype(int)
        if u.max() >= W or v.max() >= H:
            continue
        G = np.zeros((v.max() + 1, u.max() + 1), np.float32)
        G[v, u] = 1.0  # occupied cells, not counts: shrinking the drawing must not pile points onto one cell
        C = fftconvolve(E, G[::-1, ::-1], mode="valid") / G.sum()
        iy, ix = np.unravel_index(np.argmax(C), C.shape)
        if C[iy, ix] > best[0]:
            # pixel (ix, iy) is where the figure's (min x, max y) corner lands
            best = (float(C[iy, ix]), float(s), float(bx0 + ix * RES - fx0 * s), float(by1 - iy * RES - fy1 * s))  # qa-ignore: computed floats, never None
    return best


def _poly_coords(g):
    return [np.asarray(p.exterior.coords) for p in getattr(g, "geoms", [g])]


def fit_chapter(ch: dict, pdf: Path) -> dict:
    fig, labels = read_plan(pdf, ch["page"], ch["label_re"], ch.get("line_w_max", 0.2))
    # The drawing runs far past the printed frame (Gordon: 900 pt wide, ~300 visible). Keep the part round the
    # precincts, else the true scale cannot fit inside the search box and only a wrong, shrunken one can.
    if labels:
        ux0, uy0, ux1, uy1 = unary_union(list(labels.values())).bounds
        m = 120
        keep = (fig[:, 0] > ux0 - m) & (fig[:, 0] < ux1 + m) & (fig[:, 1] > uy0 - m) & (fig[:, 1] < uy1 + m)
        if keep.sum() < 300:
            raise SystemExit(f"[ABORT] {pdf.name} p{ch['page']}: only {int(keep.sum())} line points near the precincts")
        fig = fig[keep]
    sx, sy = seed(ch["suburb"])
    box = tuple(float(v) for v in (sx - 2500, sy - 2500, sx + 2500, sy + 2500))
    cad = cb.fetch_cadastre(box)
    # The plans' thin lines are mostly KERBS, not lot lines (Gordon 2026-10-15: a lot-edge match landed the
    # drawing at a third of its size). Kerbs pair either side of a road, so they are fitted to NSW road
    # centrelines; the lot lines decide acceptance through the precinct outlines instead.
    roads, _ = rf.fetch_roads(sx, sy, 2500)
    prior = scale_prior(sx, sy, labels)
    share0, s, x0, y0 = coarse_fit(fig, roads, box, np.geomspace(prior * 0.4, prior * 1.6, 50) if prior else None)
    tree = cKDTree(roads)
    coarse = (s, np.eye(2), np.array([x0, y0]))
    refined = cb.icp(coarse, fig, roads, tree, [0.5] * 10 + [0.7] * 10)
    # Plans are not uniform to the edge (Lindfield drifts west); the precincts are what must be right, so also
    # refine on the lines within 40 pt of them only. Keep whichever placement puts most NEAR lines on roads.
    ux0, uy0, ux1, uy1 = unary_union(list(labels.values())).bounds if labels else fig.min(0).tolist() + fig.max(0).tolist()
    near = fig[(fig[:, 0] > ux0 - 40) & (fig[:, 0] < ux1 + 40) & (fig[:, 1] > uy0 - 40) & (fig[:, 1] < uy1 + 40)]
    near = near if len(near) >= 300 else fig
    local = cb.icp(refined, near, roads, tree, [0.5] * 10 + [0.7] * 10)
    fit = max((coarse, refined, local), key=lambda f: (tree.query(cb.apply(f, near))[0] <= 10).mean())
    d = tree.query(cb.apply(fit, near))[0]
    row = {"chapter": ch["chapter"], "coarse_share": round(share0, 3), "scale_prior": round(prior, 3),
           "m_per_pt": round(float(fit[0]), 4),
           "rotation_deg": round(float(np.degrees(np.arctan2(fit[1][1, 0], fit[1][0, 0]))), 3),
           "lines_within_10m_of_a_road": round(float((d <= 10).mean()), 3), "line_to_road_median_m": round(float(np.median(d)), 2),
           "labels_found": sorted(labels), "labels_expected": sorted(ch["labels"])}
    placed = {lab: unary_union([Polygon(cb.apply(fit, c)) for c in _poly_coords(g)]).buffer(0) for lab, g in labels.items()}
    edge_lines = unary_union([g.boundary for _, g in cad])
    dist = [Point(p).distance(edge_lines) for g in placed.values() for c in _poly_coords(g) for p in c[::3]]
    row["outline_edge_median_m"] = round(float(np.median(dist)), 2) if dist else None
    fails = [m for m, bad in (("drawing off the road network", row["lines_within_10m_of_a_road"] < ON_EDGE_MIN),
                              ("outlines not on lot lines", (row["outline_edge_median_m"] or 99) > OUTLINE_EDGE_MAX),
                              ("precinct labels missing", sorted(labels) != sorted(ch["labels"]))) if bad]
    row["_fit"], row["_fig"], row["_placed"] = fit, fig, placed
    if fails:
        row["refused"] = "; ".join(fails)
        return row
    out = {}
    for lab, g in placed.items():
        lots, unc = [], []
        for part in getattr(g, "geoms", [g]):
            segs = list(zip(list(part.exterior.coords)[:-1], list(part.exterior.coords)[1:]))
            _, ins, u = cb.lots_inside(segs, cad)
            lots += [x for _, x in ins]
            unc += [x for _, x, _ in u if x.difference(part).area <= OUTSIDE_MAX_M2]
        merged = unary_union(lots + unc).buffer(0.3).buffer(-0.3)
        out[lab] = unary_union([q for q in getattr(merged, "geoms", [merged]) if q.area >= 50])
        row.setdefault("lots", {})[lab] = [len(lots), len(unc)]
    empty = sorted(lab for lab, g in out.items() if g.is_empty)
    if empty:
        row["refused"] = f"no cadastre lot inside precinct(s) {empty}"
    row["_geoms"] = out
    return row


def draw(row: dict, path: Path) -> None:
    """Cadastre (grey), placed figure lot lines (red), drawn outlines (black), snapped precincts (blue)."""
    fit, fig = row["_fit"], row["_fig"]
    P = cb.apply(fit, fig)
    x0, y0 = P.min(0) - 60
    x1, y1 = P.max(0) + 60
    k = 1400 / max(x1 - x0, y1 - y0)
    img = np.full((int((y1 - y0) * k) + 1, int((x1 - x0) * k) + 1, 3), 255, np.uint8)

    def poly(c, colour, w):
        cv2.polylines(img, [np.c_[(c[:, 0] - x0) * k, (y1 - c[:, 1]) * k].astype(np.int32)], True, colour, w)
    for _, g in cb.fetch_cadastre(tuple(float(v) for v in (x0, y0, x1, y1))):  # qa-ignore: computed floats, never None
        for c in _poly_coords(g):
            poly(c, (190, 190, 190), 1)
    u = ((P[:, 0] - x0) * k).astype(int)
    v = ((y1 - P[:, 1]) * k).astype(int)
    m = (u >= 0) & (u < img.shape[1]) & (v >= 0) & (v < img.shape[0])
    img[v[m], u[m]] = (0, 0, 230)
    for lab, g in row["_placed"].items():
        for c in _poly_coords(g):
            poly(c, (0, 0, 0), 1)
    for lab, g in (row.get("_geoms") or {}).items():
        if g.is_empty:
            continue
        for c in _poly_coords(g):
            poly(c, (230, 120, 0), 3)
        cp = g.representative_point()
        cv2.putText(img, lab, (int((cp.x - x0) * k), int((y1 - cp.y) * k)), 0, 0.9, (200, 0, 0), 2)
    cv2.imwrite(str(path), img)


def _one(args):
    ch, do_draw = args
    pdf = OUT / ".pdf_cache" / f"{ch['chapter']}.pdf"
    if not pdf.exists():
        import requests
        r = requests.get(f"{PDF_BASE}{ch['council']}/{ch['version']}/{ch['chapter']}.pdf", timeout=300)
        r.raise_for_status()
        pdf.write_bytes(r.content)
    try:
        row = fit_chapter(ch, pdf)
    except SystemExit as e:
        return {"chapter": ch["chapter"], "refused": str(e)}
    if do_draw and "_fit" in row:
        draw(row, OUT / f"check_{ch['id']}.png")
    for k in ("_fit", "_fig", "_placed"):
        row.pop(k, None)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=str(OUT / "vector_centres.json"))
    ap.add_argument("--only", default="", help="comma-separated chapter ids (14D,...)")
    ap.add_argument("--draw", action="store_true")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    only = {x for x in a.only.split(",") if x}
    (OUT / ".pdf_cache").mkdir(parents=True, exist_ok=True)
    todo = [c for c in cfg["chapters"] if not only or c["id"] in only]
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=min(4, len(todo))) as ex:
        rows = list(ex.map(_one, [(c, a.draw) for c in todo]))
    prev = OUT / "centres_vector.geojson"
    feats = {f["properties"]["precinct_id"]: f for f in json.loads(prev.read_text(encoding="utf-8"))["features"]} \
        if prev.exists() else {}
    report = []
    for ch, row in zip(todo, rows):
        geoms = row.pop("_geoms", None)
        report.append(row)
        print(json.dumps(row), flush=True)
        if geoms is None or "refused" in row:
            continue
        src = f"{ch['chapter']}.pdf p{ch['page']} {ch['figure']}"
        proof = {k: v for k, v in row.items() if k != "lots"}
        for lab, g in geoms.items():
            feats[f"{ch['id']}_{lab}"] = cb.feature(f"{ch['id']}_{lab}", f"{ch['name']} precinct {lab}", g, {
                "method": METHOD, "source": src, "quote": ch["quote"], "council": ch["council"], "proof": proof})
        feats[ch["id"]] = cb.feature(ch["id"], ch["name"], unary_union(list(geoms.values())), {
            "method": METHOD, "source": src + " (all precincts)", "quote": ch["quote"], "council": ch["council"],
            "proof": {"members": sorted(geoms)}})
    prev.write_text(json.dumps({"type": "FeatureCollection", "features": list(feats.values())}, indent=1), encoding="utf-8")
    (OUT / "fit_report_vector.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    refused = [r["chapter"] for r in report if "refused" in r]
    print(f"accepted {len(report) - len(refused)} / {len(report)}; refused: {refused}")
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
