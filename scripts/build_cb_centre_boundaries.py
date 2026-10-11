#!/usr/bin/env python3
"""Build the land-application outlines of three Canterbury-Bankstown DCP 2023 centre chapters.

prior-art-checked: dcp_precinct_boundaries holds 0 Canterbury-Bankstown rows (2026-10-11);
import_parramatta_part8_boundaries.py loads a council shapefile and the archived KRG/CoS importers
read hand-digitised or ArcGIS polygons. None derives a boundary from a DCP's own vector figure.

WHY (served-answer audit, 2026-10-11): every Canterbury-Bankstown house is served chapters
6.2 Bankstown City Centre (726 rules), 7.5 Canterbury Local Centre (351) and 7.6 Belmore and
Lakemba (407), because nothing records where those centres are. Each chapter says it applies
only to land "as identified in Figure N" (6.2 p8, 7.5 p6, 7.6 p7).

SOURCES, chosen by measurement, not by availability
  7.6  NSW Planning "Local Provisions" layer, Precinct Map 'Belmore and Lakemba Precinct'
       (OBJECTID 221783). Fitting the chapter's Figure 2 trace to it: median 0.8 m, p95 1.8 m,
       fitted scale 1:12,494 against the printed 1:12,500. Same line, so the official polygon is used.
  6.2  The state 'Bankstown City Centre' outline (74.7 ha) is far SMALLER than Figure 1 (it omits
       Bankstown Oval, Stevens Reserve, the blocks north of French Ave): using it would hide the
       chapter from houses it covers. Built from Figure 1 instead.
  7.5  The state 'Canterbury Precinct' (4 parts) drops 4 lots Figure 1 includes and adds 26 it
       excludes. Built from Figure 1 instead.

METHOD for 6.2 / 7.5 (deterministic; no model reads anything)
  1. The figure is vector: its lot lines and the dash-dot boundary are read from the PDF.
  2. A similarity transform (scale, rotation, shift) is fitted from the figure's lot lines to the
     NSW cadastre (nsw_cadastre_lots, MGA56) by trimmed ICP from many starting offsets, then
     re-fitted locally within 250 m of each boundary vertex (the figure is not perfectly uniform).
     Residual is ~4 m median because the figure draws kerbs and buildings in the same line style.
  3. The answer is a set of REAL LOTS, not the traced line: a lot >= 80% inside is in; a lot
     20-80% inside is "uncertain" and is ALSO kept, so doubt keeps the chapter on the page
     (today's behaviour) rather than hiding it.

Usage:  python scripts/build_cb_centre_boundaries.py        # writes data/canterbury_bankstown_precincts/
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
import requests
from pyproj import Transformer
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Polygon, mapping, shape
from shapely.ops import polygonize, transform as stx, unary_union

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "canterbury_bankstown_precincts"
PDF_BASE = ("https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/source-pdfs/dcps/"
            "canterbury_bankstown/v1.0-baseline/")
LOCAL_PROVISIONS = ("https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/"
                    "Planning/Development_Control/MapServer/3/query")
TO_MGA = Transformer.from_crs(4326, 28356, always_xy=True).transform
TO_WGS = Transformer.from_crs(28356, 4326, always_xy=True).transform

IN_SHARE, UNCERTAIN_SHARE = 0.8, 0.2

FIGURE_CHAPTERS = [
    {
        "precinct_id": "6.2", "name": "Bankstown City Centre",
        "pdf": "chapter-6-2-bankstown-city-centre.pdf", "page": 8, "figure": "Figure 1",
        "quote": "This chapter of the CBDCP 2023 applies to all development on the land within "
                 "the Bankstown City Centre as identified in Figure 1.",
        "boundary_dash": "[ 3.902 1.951 .078 1.951 ]", "lot_grey": 0.65, "lot_width": 0.16,
        # Starting guess only (labels in the figure -> their places on the NSW base map); the
        # multi-start ICP below searches +-80 m around it and decides the fit.
        "init_points": {"Paul Keating Park": [[586.5, 258.5], [318352.9, 6245464.0]],
                        "Stevens Reserve": [[654.8, 405.5], [318657.5, 6244765.5]],
                        "Rickard Rd / Chapel Rd": [[586.8, 234.0], [318293.7, 6245566.5]]},
        "cadastre_box": (316200, 6243000, 320800, 6247800),
    },
    {
        "precinct_id": "7.5", "name": "Canterbury Local Centre",
        "pdf": "chapter-7-5-canterbury-local-centre.pdf", "page": 6, "figure": "Figure 1",
        "quote": "This Chapter of the CBDCP 2023 applies to all development on the land within "
                 "the Canterbury Local Centre as identified in Figure 1.",
        "boundary_dash": "[ 7.571 4.543 2.271 4.543 ]", "lot_grey": 0.70, "lot_width": 0.23,
        # Starting guess: the figure's boundary fitted to the state 'Canterbury Precinct'
        # outline, whose edges it mostly shares.
        "init_outline": [221779, 221780, 221781, 221782],
        "cadastre_box": (324700, 6244900, 327500, 6247600),
    },
]

OFFICIAL_CHAPTERS = [
    {
        "precinct_id": "7.6", "name": "Belmore and Lakemba Precinct",
        "pdf": "chapter-7-6-belmore-and-lakemba.pdf", "page": 7, "figure": "Figure 2",
        "quote": "This Chapter of the CBDCP 2023 applies to all development on the land within "
                 "the Precinct as identified in Figure 2.",
        "objectid": 221783,
    },
]


# ---------------------------------------------------------------- inputs

def fetch_pdf(name: str, cache: Path) -> Path:
    p = cache / name
    if not p.exists():
        r = requests.get(PDF_BASE + name, timeout=300)
        r.raise_for_status()
        p.write_bytes(r.content)
    return p


def fetch_outlines(objectids: list[int]) -> list[dict]:
    r = requests.get(LOCAL_PROVISIONS, params={
        "where": f"OBJECTID IN ({','.join(map(str, objectids))})", "outFields": "*",
        "outSR": 4326, "f": "geojson"}, timeout=60)
    r.raise_for_status()
    feats = r.json()["features"]
    if {f["properties"]["OBJECTID"] for f in feats} != set(objectids):
        raise SystemExit(f"[ABORT] state layer did not return all of {objectids}")
    return feats


def database_url() -> str:
    from dotenv import dotenv_values
    if os.environ.get("DATABASE_URL"):
        return os.environ["DATABASE_URL"]
    for d in [REPO, *REPO.parents]:  # a worktree has no .env of its own
        if (d / ".env").exists() and dotenv_values(d / ".env").get("DATABASE_URL"):
            return dotenv_values(d / ".env")["DATABASE_URL"]
    raise SystemExit("[ABORT] DATABASE_URL not found in the environment or any parent .env")


def fetch_cadastre(box: tuple) -> list[tuple[str, object]]:
    import psycopg2
    conn = psycopg2.connect(database_url(), connect_timeout=15,
                            options="-c statement_timeout=30000 -c default_transaction_read_only=on")
    with conn.cursor() as cur:
        cur.execute("""SELECT lotidstring, ST_AsGeoJSON(ST_Transform(geom, 28356), 2)
                         FROM nsw_cadastre_lots
                        WHERE geom && ST_Transform(ST_MakeEnvelope(%s,%s,%s,%s,28356),4326)""", box)
        rows = [(lot, shape(json.loads(g))) for lot, g in cur.fetchall()]
    conn.close()
    return rows


def read_figure(pdf: Path, ch: dict) -> tuple[np.ndarray, list]:
    """Lot-line points (PDF y flipped up) and the boundary path segments, from the vector figure."""
    pg = fitz.open(pdf)[ch["page"] - 1]
    lots, boundary = [], None
    for d in pg.get_drawings():
        col, w = d.get("color"), d.get("width") or 0
        if (d.get("dashes") or "").startswith(ch["boundary_dash"]) and len(d["items"]) > 20:
            boundary = [((it[1].x, -it[1].y), (it[-1].x, -it[-1].y))
                        for it in d["items"] if it[0] in ("l", "c")]
        elif col and abs(col[0] - ch["lot_grey"]) < 0.01 and abs(w - ch["lot_width"]) < 0.01:
            lots += [((it[1].x, it[1].y), (it[2].x, it[2].y)) for it in d["items"] if it[0] == "l"]
    if not boundary or not lots:
        raise SystemExit(f"[ABORT] {ch['precinct_id']}: figure boundary or lot lines not found "
                         f"on page {ch['page']} -- the PDF has changed; re-derive the styles.")
    seg = np.array(lots)
    pts = np.unique(np.round(np.vstack([seg[:, 0], seg[:, 1], seg.mean(1)]), 2), axis=0)
    pts[:, 1] *= -1
    return pts, boundary


# ---------------------------------------------------------------- fitting

def umeyama(a: np.ndarray, b: np.ndarray):
    ma, mb = a.mean(0), b.mean(0)
    u, s, vt = np.linalg.svd((b - mb).T @ (a - ma) / len(a))
    d = np.eye(2)
    if np.linalg.det(u @ vt) < 0:
        d[1, 1] = -1
    r = u @ d @ vt
    sc = np.trace(np.diag(s) @ d) / (a - ma).var(0).sum()
    return sc, r, mb - sc * r @ ma


def apply(fit, p):
    s, r, t = fit
    return (s * (r @ np.asarray(p, float).T)).T + t


def edge_points(geoms, step=0.5) -> np.ndarray:
    out = []
    for g in geoms:
        for poly in getattr(g, "geoms", [g]):
            for ring in [poly.exterior, *poly.interiors]:
                c = np.asarray(ring.coords)[:, :2]
                for a, b in zip(c[:-1], c[1:]):
                    n = max(1, int(np.hypot(*(b - a)) / step))
                    out.append(a + (b - a) * np.linspace(0, 1, n, endpoint=False)[:, None])
    return np.vstack(out)


def icp(fit, src, tgt, tree, schedule):
    for q in schedule:
        dist, idx = tree.query(apply(fit, src))
        m = dist <= np.quantile(dist, q)
        fit = umeyama(src[m], tgt[idx[m]])
    return fit


def initial_fit(ch: dict, boundary) -> tuple:
    if "init_points" in ch:
        pairs = list(ch["init_points"].values())
        a = np.array([[p[0][0], -p[0][1]] for p in pairs])
        return umeyama(a, np.array([p[1] for p in pairs]))
    outline = [stx(TO_MGA, shape(f["geometry"])).buffer(0) for f in fetch_outlines(ch["init_outline"])]
    tgt = edge_points(outline, 1.0)
    tree = cKDTree(tgt)
    src = []
    for a, b in boundary:
        a, b = np.array(a), np.array(b)
        src += list(a + (b - a) * np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) * 2)))[:, None])
    src = np.array(src)
    best = None
    for rot in np.radians(np.arange(-20, 21, 2)):
        r = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
        s = np.ptp(tgt, 0).max() / np.ptp(src, 0).max()
        fit = icp((s, r, tgt.mean(0) - s * r @ src.mean(0)), src, tgt, tree, [0.6] * 60)
        med = np.median(tree.query(apply(fit, src))[0])
        if best is None or med < best[0]:
            best = (med, fit)
    return best[1]


def fit_figure(ch: dict, lots_pts: np.ndarray, boundary, cad) -> tuple[list, dict]:
    tgt = edge_points([g for _, g in cad])
    tree = cKDTree(tgt)
    sub = lots_pts[np.random.default_rng(0).choice(len(lots_pts), min(3000, len(lots_pts)), replace=False)]
    s0, r0, t0 = initial_fit(ch, boundary)
    best = None
    for dx in np.arange(-80, 81, 10):
        for dy in np.arange(-80, 81, 10):
            fit = icp((s0, r0, t0 + [dx, dy]), sub, tgt, tree, [0.3] * 8 + [0.5] * 6)
            score = (tree.query(apply(fit, sub))[0] <= 1.0).mean()
            if best is None or score > best[0]:
                best = (score, fit)
    glob = icp(best[1], lots_pts, tgt, tree, [0.3] * 15 + [0.45] * 15 + [0.6] * 15)
    gdist = tree.query(apply(glob, lots_pts))[0]
    # Local re-fit around each boundary vertex.
    placed = apply(glob, lots_pts)
    ptree, cache, segs, shifts = cKDTree(placed), {}, [], []
    for a, b in boundary:
        ends = []
        for p in (a, b):
            g = apply(glob, [p])[0]
            key = tuple((g // 50).astype(int))
            if key not in cache:
                local = lots_pts[ptree.query_ball_point(g, 250)]
                cache[key] = icp(glob, local, tgt, tree, [0.3] * 12 + [0.5] * 12)
            q = apply(cache[key], [p])[0]
            shifts.append(float(np.hypot(*(q - g))))
            ends.append(tuple(q))
        segs.append(ends)
    report = {
        "scale_m_per_pt": round(float(glob[0]), 4),
        "rotation_deg": round(float(np.degrees(np.arctan2(glob[1][1, 0], glob[1][0, 0]))), 3),
        "lot_line_residual_m": {"median": round(float(np.median(gdist)), 2),
                                "p75": round(float(np.quantile(gdist, .75)), 2)},
        "local_refit_shift_m": {"median": round(float(np.median(shifts)), 2),
                                "max": round(float(np.max(shifts)), 2)},
    }
    return segs, report


def lots_inside(segs, cad) -> tuple[Polygon, list, list]:
    merged = unary_union([LineString(s) for s in segs if s[0] != s[1]])
    rings = list(polygonize(merged))
    if not rings:
        raise SystemExit("[ABORT] the figure boundary does not close into a polygon")
    fig = max(rings, key=lambda p: p.area)
    inside, uncertain = [], []
    for lot, g in cad:
        g = g if g.is_valid else g.buffer(0)
        if g.area <= 0 or not g.intersects(fig):
            continue
        share = g.intersection(fig).area / g.area
        if share >= IN_SHARE:
            inside.append((lot, g))
        elif share > UNCERTAIN_SHARE:
            uncertain.append((lot, g, round(share, 2)))
    return fig, inside, uncertain


# ---------------------------------------------------------------- main

def feature(pid, name, geom_mga, props) -> dict:
    geom_mga = geom_mga.buffer(0)
    wgs = stx(TO_WGS, geom_mga)
    return {"type": "Feature", "geometry": mapping(wgs), "properties": {
        "precinct_id": pid, "precinct_name": name,
        "area_sqm": round(geom_mga.area, 1), "perimeter_m": round(geom_mga.length, 1), **props}}


def main() -> int:
    cache = OUT / ".pdf_cache"
    cache.mkdir(parents=True, exist_ok=True)
    feats, report = [], {}
    for ch in FIGURE_CHAPTERS:
        pdf = fetch_pdf(ch["pdf"], cache)
        lot_pts, boundary = read_figure(pdf, ch)
        cad = fetch_cadastre(ch["cadastre_box"])
        segs, rep = fit_figure(ch, lot_pts, boundary, cad)
        fig, inside, uncertain = lots_inside(segs, cad)
        # Kept lots, plus the road space inside the figure (lots do not cover roads, and an
        # address point on a frontage must not fall between blocks). No other lot is added.
        roads = fig.difference(unary_union([g if g.is_valid else g.buffer(0) for _, g in cad]))
        kept = unary_union([g for _, g in inside] + [g for _, g, _ in uncertain] + [roads])
        kept = kept.buffer(0.5).buffer(-0.5)
        rep.update(figure_area_ha=round(fig.area / 1e4, 1), lots_inside=len(inside),
                   lots_uncertain_kept=len(uncertain))
        report[ch["precinct_id"]] = rep
        print(f"{ch['precinct_id']} {ch['name']}: {rep}")
        feats.append(feature(ch["precinct_id"], ch["name"], kept, {
            "method": "dcp_figure_georeferenced_to_cadastre",
            "source": f"Canterbury-Bankstown DCP 2023 Chapter {ch['precinct_id']} {ch['figure']} "
                      f"(p{ch['page']}) -- lots >=80% inside the figure boundary, plus lots 20-80% inside",
            "quote": ch["quote"],
            "lots": sorted(l for l, _ in inside) + sorted(l for l, _, _ in uncertain),
            "uncertain_lots": sorted([l, s] for l, _, s in uncertain)}))
    for ch in OFFICIAL_CHAPTERS:
        f = fetch_outlines([ch["objectid"]])[0]
        a = f["properties"]
        geom = stx(TO_MGA, shape(f["geometry"]))
        feats.append(feature(ch["precinct_id"], ch["name"], geom, {
            "method": "nsw_planning_local_provisions",
            "source": f"NSW Planning Development_Control/MapServer/3 OBJECTID {ch['objectid']} "
                      f"'{a['LAY_CLASS']}' ({a['AMENDMENT']}); matches DCP Chapter {ch['precinct_id']} "
                      f"{ch['figure']} (p{ch['page']}) to median 0.8 m",
            "quote": ch["quote"]}))
        print(f"{ch['precinct_id']} {ch['name']}: state outline {geom.area / 1e4:.1f} ha")
    (OUT / "centres.geojson").write_text(json.dumps(
        {"type": "FeatureCollection", "features": feats}, indent=1), encoding="utf-8")
    (OUT / "fit_report.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"wrote {OUT / 'centres.geojson'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
