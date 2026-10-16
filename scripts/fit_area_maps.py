#!/usr/bin/env python3
"""CANDIDATE outlines for area-limited DCP chapters whose rules are hidden (DQ-146). Writes candidates only.

prior-art-checked: fit_vector_centres.py fits kerb/lot lines to NSW ROAD centrelines (refused 14C/14F, road share
0.48/0.54); fit_cb_raster_centres.py needs a white-road basemap; build_cb_centre_boundaries.py needs a typed
start point. This starts a vector plan from the zone the plan's own legend names (a START only -- zoning is never the
outline), refines on the plan's lot lines against the cadastre, snaps cadastre lots, and PROVES the result.

A candidate needs ALL of (else REFUSED with the reason):
  1 shape      site_figure_check.shape_iou(figure outline, candidate lots) >= 0.85
  2 picture    data/area_map_checks/<chapter>_<precinct>.png: the figure outline fitted onto the NSW road network
               beside the candidate outline (looked at by a person before any load)
  3 addresses  2 register points inside and 2 outside resolve correctly. The plan prints house numbers on its lots:
               a number printed inside the outline must have a register address of that number inside the candidate
               (within 45 m of where the plan puts it); a number printed outside (near) must not.
Nothing is loaded into the database and no rule is keyed here.

Usage: python scripts/fit_area_maps.py --only 14G
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import cv2
import fitz
import numpy as np
from scipy.spatial import cKDTree
from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import polygonize, unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cb_centre_boundaries as cb  # noqa: E402
import fit_cb_raster_centres as rf  # noqa: E402
import fit_vector_centres as fv  # noqa: E402
import site_figure_check as sfc  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUTDIR = REPO / "data" / "area_map_checks"
KRG = REPO / "data" / "ku_ring_gai_precincts"
MATCH = sfc.MATCH
CLOSE_M = 15.0


def zone_polys(regex: str, lga: str, cx: float, cy: float, radius: float) -> list:
    import psycopg2
    if cx is None or cy is None or radius is None:
        raise ValueError("zone lookup needs a centre and radius")
    conn = psycopg2.connect(cb.database_url(), connect_timeout=15,
                            options="-c statement_timeout=60000 -c default_transaction_read_only=on")
    with conn.cursor() as cur:
        cur.execute("""SELECT ST_AsGeoJSON(ST_Transform(geom,28356),1) FROM spatial_overlays
                        WHERE layer_type='zone' AND lga_name ILIKE %s AND value ~ %s
                          AND ST_DWithin(geom::geography, ST_Transform(ST_SetSRID(ST_MakePoint(%s,%s),28356),4326)::geography, %s)""",
                    (lga, regex, float(cx), float(cy), float(radius)))
        out = [shape(json.loads(r[0])) for r in cur.fetchall()]
    conn.close()
    return out


def read_vector_plan(pdf: Path, page: int, cfg: dict):
    """(lot-line points y-up, outline polygon y-up in PDF points, number labels [(text, x, y)]).

    Lines are the page's thin dark strokes, or (cfg lines='fill') the boundaries of dark filled shapes bigger than
    14 pt (14G draws every line as a filled hairline polygon). The outline is the orange stroke (width >= 2) or
    orange fill, closed; its inner face is widened by half the line width to the line's centre."""
    pg = fitz.open(pdf)[page - 1]
    lots, outline = [], []
    for d in pg.get_drawings():
        col, fill, w = d.get("color"), d.get("fill"), d.get("width") or 0
        if cfg.get("lines") == "fill":
            if fill and fill[0] > 0.95 and 0.6 < fill[1] < 0.7 and fill[2] < 0.2:
                outline += fv._segs(d)
            elif fill and max(d["rect"].width, d["rect"].height) > 14 and max(fill) - min(fill) < 0.02 and fill[0] < 0.3:
                lots += fv._segs(d)
        else:
            if fv._is_orange(col) and w >= 2:
                outline += fv._segs(d)
                cfg.setdefault("_w", w)
            elif col and len(col) == 3 and max(col) < 0.5 and w < cfg.get("line_w_max", 0.2):
                lots += fv._segs(d)
    if not lots or not outline:
        raise SystemExit("lot lines or outline not found on the plan page")
    pts = []
    for a, b in np.array(lots):
        n = max(1, int(np.hypot(*(b - a)) / 0.5))
        pts.append(a + (b - a) * np.linspace(0, 1, n, endpoint=False)[:, None])
    pts = np.unique(np.round(np.vstack(pts), 2), axis=0)
    ring = unary_union([LineString(s) for s in outline if s[0] != s[1]])
    hw = cfg.get("outline_half_width_pt", 2.0)
    faces = [p for p in polygonize(ring.buffer(0.3).boundary) if p.area > 50 and not ring.buffer(0.3).contains(p)]
    if not faces:
        raise SystemExit("outline does not close")
    if cfg.get("outline_parts") == "all":
        poly = unary_union([p.buffer(hw) for p in faces])
    else:
        poly = max(faces, key=lambda p: p.area).buffer(hw)
    nums = [((w[4]), (w[0] + w[2]) / 2, -(w[1] + w[3]) / 2) for w in pg.get_text("words")
            if re.fullmatch(r"\d{1,3}[A-Z]?", w[4])]
    return pts, poly, nums


def register_by_number(number: str, x: float, y: float, r: float = 45) -> list:
    """Register points with exactly this street number (any street) within r m of (x, y) (MGA 56)."""
    where = (f"address LIKE '{number} %' OR address LIKE '%/{number} %' OR address LIKE '{number}-%' "
             f"OR address LIKE '%-{number} %'")
    fs = rf._get(rf.ADDR, {"where": where, "geometry": f"{x-r},{y-r},{x+r},{y+r}", "geometryType": "esriGeometryEnvelope",
                           "inSR": "28356", "spatialRel": "esriSpatialRelIntersects", "outFields": "address",
                           "returnGeometry": "true", "outSR": "28356", "f": "json"}).get("features") or []
    return [(f["attributes"]["address"], Point(f["geometry"]["x"], f["geometry"]["y"])) for f in fs]


def fit_vector(cfg: dict) -> dict:
    pdf = KRG / ".pdf_cache" / f"{cfg['chapter']}.pdf"
    fig, fig_outline, nums = read_vector_plan(pdf, cfg["page"], cfg)
    ux0, uy0, ux1, uy1 = fig_outline.bounds
    if cfg.get("seed_street"):  # a street the chapter names: a suburb median can sit in another centre
        fs = rf._get(rf.ADDR, {"where": f"address LIKE '% {cfg['seed_street']}'", "outFields": "address", "returnGeometry": "true",
                               "outSR": "28356", "f": "json", "resultRecordCount": 200}).get("features") or []
        sx, sy = np.median(np.array([[f["geometry"]["x"], f["geometry"]["y"]] for f in fs]), 0)
    else:
        sx, sy = fv.seed(cfg["suburb"])
    if cfg.get("init") == "roads":
        # start = the road-network fit fit_vector_centres makes (kerbs on NSW centrelines); it was refused there on its
        # own road-share test, but is only a START here -- the lot-line refinement and the proofs below decide
        ch = next(c for c in json.loads((KRG / "vector_centres.json").read_text(encoding="utf-8"))["chapters"] if c["id"] == cfg["id"])
        import pickle
        cache = OUTDIR / ".cache" / f"{cfg['id']}_init.pkl"
        if cache.exists():
            fit0, med0 = pickle.loads(cache.read_bytes())
        else:
            r0 = fv.fit_chapter({**ch, "accept_on_lot_lines": None}, pdf)
            fit0, med0 = r0["_fit"], float(r0.get("outline_edge_median_m") or 0)
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(pickle.dumps((fit0, med0)))
        best = (med0, fit0)
        zx, zy = cb.apply(fit0, [fig_outline.centroid.coords[0]])[0]
    else:
        zs = [q for g in zone_polys(cfg["zone_regex"], "ku%ring%", sx, sy, 3000) for q in getattr(g, "geoms", [g])]
        zone = max(zs, key=lambda g: g.area) if cfg.get("zone_pick") == "largest" else min(zs, key=lambda g: g.distance(Point(sx, sy)))
        zone = unary_union([z for z in zs if z.distance(zone) < 60])
        zt = cb.edge_points([zone], 1.0)
        ztree = cKDTree(zt)
        src = cb.edge_points([fig_outline], 0.5)
        s0 = (zone.area / fig_outline.area) ** 0.5
        best = None
        for rot in np.radians(np.arange(-12, 13, 2)):
            r = np.array([[np.cos(rot), -np.sin(rot)], [np.sin(rot), np.cos(rot)]])
            f = (s0, r, np.array(zone.centroid.coords[0]) - s0 * r @ np.array(fig_outline.centroid.coords[0]))
            f = cb.icp(f, src, zt, ztree, [0.6] * 40)
            med = float(np.median(ztree.query(cb.apply(f, src))[0]))
            if best is None or med < best[0]:
                best = (med, f)
        fit0 = best[1]
        zx, zy = zone.centroid.coords[0]
    cad = cb.fetch_cadastre(tuple(float(v) for v in (zx - 1500, zy - 1500, zx + 1500, zy + 1500)))
    tgt = cb.edge_points([g for _, g in cad], 0.5)
    tree = cKDTree(tgt)
    near = fig[(fig[:, 0] > ux0 - 40) & (fig[:, 0] < ux1 + 40) & (fig[:, 1] > uy0 - 40) & (fig[:, 1] < uy1 + 40)]
    fit = cb.icp(fit0, near, tgt, tree, [0.3] * 10 + [0.5] * 10)
    d = tree.query(cb.apply(fit, near))[0]
    row = {"chapter": cfg["chapter"], "route": "vector_plan_lot_lines_started_from_legend_zone",
           "zone_start_edge_median_m": round(best[0], 2), "m_per_pt": round(float(fit[0]), 4),
           "rotation_deg": round(float(np.degrees(np.arctan2(fit[1][1, 0], fit[1][0, 0]))), 3),
           "plan_lines_within_1_5m_of_lot_edge": round(float((d <= 1.5).mean()), 3),
           "plan_line_to_lot_edge_median_m": round(float(np.median(d)), 2)}
    parts_pdf = list(getattr(fig_outline, "geoms", [fig_outline]))
    placed_parts = []
    for p in parts_pdf:
        pf = fit
        if cfg.get("local_parts"):
            # each outline part re-fitted on its own lot lines + outline (a plan drifts across its width)
            bx0, by0, bx1, by1 = p.bounds
            loc = fig[(fig[:, 0] > bx0 - 25) & (fig[:, 0] < bx1 + 25) & (fig[:, 1] > by0 - 25) & (fig[:, 1] < by1 + 25)]
            loc = np.vstack([loc, cb.edge_points([p], 0.5)]) if len(loc) else cb.edge_points([p], 0.5)
            pf = cb.icp(fit, loc, tgt, tree, [0.5] * 12 + [0.7] * 8)
        placed_parts.append(Polygon(cb.apply(pf, np.asarray(p.exterior.coords))))
    placed = unary_union(placed_parts).buffer(0)
    lots, unc = [], []
    for part in getattr(placed, "geoms", [placed]):
        segs = list(zip(list(part.exterior.coords)[:-1], list(part.exterior.coords)[1:]))
        _, ins, u = cb.lots_inside(segs, cad)
        lots += [x for _, x in ins]
        unc += [x for _, x, _ in u if x.difference(part).area <= fv.OUTSIDE_MAX_M2]
    merged = unary_union(lots + unc).buffer(0.3).buffer(-0.3)
    cand = unary_union([q for q in getattr(merged, "geoms", [merged]) if q.area >= 50])
    row["lots"] = [len(lots), len(unc)]
    row.update(_cand=cand, _placed=placed, _fit=fit, _nums=nums, _figoutline=fig_outline)
    return row


def address_proof(row: dict, k: int = 2) -> dict:
    """Printed house numbers: inside the figure outline -> a same-numbered register point inside the candidate;
    outside (near the outline) -> none inside the candidate. Counts, plus the first k examples of each."""
    fit, cand, nums, fo = row["_fit"], row["_cand"], row["_nums"], row["_figoutline"]
    ins, outs = [], []
    for t, x, y in nums:
        p = Point(x, y)
        mx, my = cb.apply(fit, [(x, y)])[0]
        if fo.contains(p) and len(ins) < 14:
            hits = [(a, q) for a, q in register_by_number(t, mx, my) if cand.contains(q)]
            ins.append({"number": t, "ok": bool(hits), "address": hits[0][0] if hits else None})
        elif not fo.contains(p) and fo.distance(p) < 60 and len(outs) < 14:
            near = register_by_number(t, mx, my)
            bad = [a for a, q in near if cand.contains(q)]
            outs.append({"number": t, "ok": not bad and bool(near), "address": near[0][0] if near else None})
        if len(ins) >= 14 and len(outs) >= 14:
            break
    return {"inside_checked": len(ins), "inside_ok": sum(i["ok"] for i in ins),
            "outside_checked": len(outs), "outside_ok": sum(i["ok"] for i in outs),
            "inside": [i for i in ins if i["ok"]][:k], "outside": [i for i in outs if i["ok"]][:k]}


def draw(row: dict, path: Path, pad: float = 120) -> None:
    """Fitted figure outline (blue) and candidate (orange) over NSW road centrelines (grey dots), lot edges pale."""
    cand, placed = row["_cand"], row["_placed"]
    x0, y0, x1, y1 = unary_union([cand, placed]).bounds
    x0, y0, x1, y1 = x0 - pad, y0 - pad, x1 + pad, y1 + pad
    k = 1000 / max(x1 - x0, y1 - y0)
    img = np.full((int((y1 - y0) * k) + 1, int((x1 - x0) * k) + 1, 3), 255, np.uint8)

    def pl(g, col, w):
        for q in getattr(g, "geoms", [g]):
            c = np.asarray(q.exterior.coords)
            cv2.polylines(img, [np.c_[(c[:, 0] - x0) * k, (y1 - c[:, 1]) * k].astype(np.int32)], True, col, w)

    for _, g in cb.fetch_cadastre(tuple(float(v) for v in (x0, y0, x1, y1))):
        for q in getattr(g, "geoms", [g]):
            pl(q, (225, 225, 225), 1)
    pts, _ = rf.fetch_roads((x0 + x1) / 2, (y0 + y1) / 2, max(x1 - x0, y1 - y0) / 2 + 50)
    m = (pts[:, 0] > x0) & (pts[:, 0] < x1) & (pts[:, 1] > y0) & (pts[:, 1] < y1)
    for p in pts[m]:
        cv2.circle(img, (int((p[0] - x0) * k), int((y1 - p[1]) * k)), 1, (120, 120, 120), -1)
    pl(cand, (0, 140, 255), 4)
    pl(placed, (220, 80, 0), 2)
    cv2.putText(img, "orange = candidate lots; blue = plan outline fitted; grey dots = NSW roads", (8, 18), 0, 0.5, (0, 0, 0), 1)
    from PIL import Image
    Image.fromarray(img[:, :, ::-1]).quantize(32).save(path, optimize=True)


def fit_raster(cfg: dict) -> dict:
    """A raster map that prints the cadastre (light lot lines) with the land as a thick dark closed line (C-B 11.5).

    Scale comes from the map's own printed scale (cfg m_per_px: 1:7000 on A3), the start from a template match of
    the map's lines against cadastre edges round the suburb, then ICP on the lines. Same proofs as the vector route."""
    import io
    import pickle
    from PIL import Image
    pdf = REPO / "data" / "canterbury_bankstown_precincts" / ".pdf_cache" / f"{cfg['chapter']}.pdf"
    d = fitz.open(pdf)
    pg = d[cfg["page"] - 1]
    big = max(pg.get_images(full=True), key=lambda im: d.extract_image(im[0])["width"] * d.extract_image(im[0])["height"])
    img = np.asarray(Image.open(io.BytesIO(d.extract_image(big[0])["image"])).convert("L"))
    H, W = img.shape
    cx0, cy0, cx1, cy1 = cfg.get("crop", [cfg.get("legend_frac", 0.2), 0.01, 0.99, 0.96])  # map area as image fractions
    ox, oy = int(cx0 * W), int(cy0 * H)
    crop = img[oy:int(cy1 * H), ox:int(cx1 * W)]
    n, lab, st, _ = cv2.connectedComponentsWithStats((crop < cfg["line_below"]).astype(np.uint8), 8)
    keep = np.isin(lab, [i for i in range(1, n) if st[i, 4] > 40]).astype(np.uint8)
    ys, xs = np.nonzero(keep)
    pts = np.c_[xs + ox, -(ys + oy)].astype(float)  # image px, y up
    sx, sy = fv.seed(cfg["suburb"])
    cache = OUTDIR / ".cache" / f"{cfg['id']}_init.pkl"
    s0 = cfg["m_per_px"]
    if cache.exists() and not cfg.get("recoarse"):
        fit0, cad = pickle.loads(cache.read_bytes())
    else:
        half = cfg.get("half", 3500)
        cad = []
        if cache.exists():
            cad = pickle.loads(cache.read_bytes())[1]
        for ix in range(2):
            for iy in range(2):
                if cad:
                    break
                bx, by = sx - half + ix * half, sy - half + iy * half
                cad += cb.fetch_cadastre((float(bx), float(by), float(bx + half), float(by + half)))
        tg = cb.edge_points([g for _, g in cad], 1.0)
        R = 3.0
        Wc = int(2 * half / R)
        E = np.zeros((Wc, Wc), np.float32)
        E[((sy + half - tg[:, 1]) / R).astype(int).clip(0, Wc - 1), ((tg[:, 0] - (sx - half)) / R).astype(int).clip(0, Wc - 1)] = 1
        E = cv2.GaussianBlur(E, (0, 0), 1.2)
        best = (-1.0, 0.0, 0.0, 0.0)
        for s in np.linspace(s0 * (1 - cfg.get("scale_span", 0.15)), s0 * (1 + cfg.get("scale_span", 0.15)), cfg.get("scale_steps", 7)):
            t = cv2.GaussianBlur(cv2.resize(keep.astype(np.float32), None, fx=s / R, fy=s / R, interpolation=cv2.INTER_AREA), (0, 0), 1.2)
            m = cv2.matchTemplate(E, t, cv2.TM_CCOEFF_NORMED)
            iy, ix = np.unravel_index(np.argmax(m), m.shape)
            if m[iy, ix] > best[0]:
                best = (float(m[iy, ix]), float(s), sx - half + ix * R, sy + half - iy * R)
        _, s, x0, y0 = best
        # crop pixel (u, v) -> MGA (x0 + s*u, y0 - s*v); full-image px = crop px + (ox, oy)
        fit0 = (s, np.eye(2), np.array([x0 - s * ox, y0 + s * oy]))
        cache.parent.mkdir(parents=True, exist_ok=True)
        cache.write_bytes(pickle.dumps((fit0, cad)))
    tgt = cb.edge_points([g for _, g in cad], 1.0)
    tree = cKDTree(tgt)
    fit = fit0
    for sched in ([0.3] * 8, [0.4] * 8 + [0.5] * 8, [0.5] * 20):
        fit = cb.icp(fit, pts, tgt, tree, sched)
    dd = tree.query(cb.apply(fit, pts))[0]
    row = {"chapter": cfg["chapter"], "route": "raster_map_lot_lines_template_matched_to_cadastre",
           "m_per_px": round(float(fit[0]), 4), "printed_scale_m_per_px": s0,
           "rotation_deg": round(float(np.degrees(np.arctan2(fit[1][1, 0], fit[1][0, 0]))), 3),
           "plan_lines_within_3m_of_lot_edge": round(float((dd <= 3).mean()), 3),
           "plan_line_to_lot_edge_median_m": round(float(np.median(dd)), 2)}
    if cfg.get("outline_mode") == "coloured":  # the land is the coloured plan itself (C-B 11.6 land application map)
        rgb = np.asarray(Image.open(io.BytesIO(d.extract_image(big[0])["image"])).convert("RGB")).astype(int)
        col = ((rgb.max(2) - rgb.min(2) > 18) & (rgb.mean(2) < 250)).astype(np.uint8)
        region = np.zeros_like(col)
        region[oy:int(cy1 * H), ox:int(cx1 * W)] = 1
        dark = cv2.morphologyEx(col * region, cv2.MORPH_CLOSE, np.ones((cfg.get("close_px", 9), cfg.get("close_px", 9)), np.uint8))
        n, lab, st, _ = cv2.connectedComponentsWithStats(dark, 8)
        comps = [i for i in range(1, n) if st[i, 4] > 2000]
        comp = max(comps, key=lambda i: st[i, 4]) if comps else None
    else:
        dark = (img < cfg["outline_below"]).astype(np.uint8)
        dark[:, :ox] = 0
        dark[int(cy1 * H):] = 0
        n, lab, st, _ = cv2.connectedComponentsWithStats(dark, 8)
        comps = [i for i in range(1, n) if st[i, 4] > 300 and st[i, 2] < 0.6 * W]
        comp = max(comps, key=lambda i: st[i, 4]) if comps else None
    if comp is None:
        raise SystemExit("no closed outline component on the map")
    mask = np.zeros_like(dark)
    cs, _ = cv2.findContours((lab == comp).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    cv2.drawContours(mask, [max(cs, key=cv2.contourArea)], -1, 1, -1)
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    ring = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
    fig_outline = Polygon(np.c_[ring[:, 0], -ring[:, 1]]).buffer(0)  # px, y up
    placed = Polygon(cb.apply(fit, np.asarray(fig_outline.exterior.coords))).buffer(0)
    x0_, y0_, x1_, y1_ = placed.bounds
    cad2 = cb.fetch_cadastre(tuple(float(v) for v in (x0_ - 50, y0_ - 50, x1_ + 50, y1_ + 50)))
    lots, unc = [], []
    for part in getattr(placed, "geoms", [placed]):
        segs = list(zip(list(part.exterior.coords)[:-1], list(part.exterior.coords)[1:]))
        _, ins, u = cb.lots_inside(segs, cad2)
        lots += [x for _, x in ins]
        unc += [x for _, x, _ in u if x.difference(part).area <= fv.OUTSIDE_MAX_M2]
    merged = unary_union(lots + unc).buffer(0.3).buffer(-0.3)
    cand = unary_union([q for q in getattr(merged, "geoms", [merged]) if q.area >= 50])
    row["lots"] = [len(lots), len(unc)]
    row.update(_cand=cand, _placed=placed, _fit=fit, _nums=[], _figoutline=fig_outline)
    return row


def fit_lotmask(cfg: dict) -> dict:
    """A small raster site plan with no cadastre lines of its own (C-B 11.2 Undercliffe Bridge): roads are grey, every
    other pixel is land. Matches that land/road mask to the cadastre (lots = land, gaps = road) over scale and
    rotation round an address the chapter names, then the same snap and proofs as the other routes."""
    import io
    import pickle
    from PIL import Image
    pdf = REPO / "data" / "canterbury_bankstown_precincts" / ".pdf_cache" / f"{cfg['chapter']}.pdf"
    d = fitz.open(pdf)
    pg = d[cfg["page"] - 1]
    big = max(pg.get_images(full=True), key=lambda im: d.extract_image(im[0])["width"] * d.extract_image(im[0])["height"])
    rgb = np.asarray(Image.open(io.BytesIO(d.extract_image(big[0])["image"])).convert("RGB")).astype(int)
    H, W = rgb.shape[:2]
    v = rgb.mean(2)
    neutral = (rgb.max(2) - rgb.min(2) < 14)
    road = neutral & (v > cfg["road_grey"][0]) & (v < cfg["road_grey"][1])
    road = cv2.morphologyEx(road.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    legend = np.zeros((H, W), np.uint8)
    lx0, ly0 = cfg["legend_box"]
    legend[int(ly0 * H):, int(lx0 * W):] = 1
    land = ((road == 0) & (legend == 0)).astype(np.float32)
    valid = (legend == 0).astype(np.float32)
    import fit_site_plans as fsp
    sx0, sy0 = rf.seed({"seed": "street", "streets": [cfg["seed_streets"][0]], "suburb": cfg["suburb"]})
    p0 = Point(*fsp.corner(sx0, sy0, *cfg["seed_streets"]))  # where the two streets the plan names cross
    half = 350.0
    cad = cb.fetch_cadastre(tuple(float(q) for q in (p0.x - half - 150, p0.y - half - 150, p0.x + half + 150, p0.y + half + 150)))
    R = 1.0
    box = (p0.x - half, p0.y - half, p0.x + half, p0.y + half)
    Wc = int(2 * half / R)
    T = np.zeros((Wc, Wc), np.uint8)
    for _, g in cad:
        for q in getattr(g, "geoms", [g]):
            c = np.asarray(q.exterior.coords)
            cv2.fillPoly(T, [np.c_[(c[:, 0] - box[0]) / R, (box[3] - c[:, 1]) / R].astype(np.int32)], 1)
    T = T.astype(np.float32)
    best = (-1.0,)
    for s in np.arange(cfg["scale_range"][0], cfg["scale_range"][1] + 1e-9, cfg["scale_range"][2]):
        k = s / R
        for rot in range(0, 360, cfg.get("rot_step", 6)):
            M = cv2.getRotationMatrix2D((W / 2, H / 2), rot, k)
            cw, ch = int(W * k * 1.5), int(H * k * 1.5)
            M[0, 2] += cw / 2 - W / 2
            M[1, 2] += ch / 2 - H / 2
            t = cv2.warpAffine(land, M, (cw, ch), flags=cv2.INTER_AREA)
            m = cv2.warpAffine(valid, M, (cw, ch), flags=cv2.INTER_NEAREST)
            if cw >= Wc or ch >= Wc:
                continue
            tt = t * m
            res = cv2.matchTemplate(T, tt, cv2.TM_CCOEFF_NORMED, mask=m)
            iy, ix = np.unravel_index(np.nanargmax(res), res.shape)
            if res[iy, ix] > best[0] and s is not None and rot is not None:
                best = (float(res[iy, ix]), float(s), float(rot), int(ix), int(iy), M.copy(), cw, ch)
    score, s, rot, ix, iy, M, cw, ch = best
    # image px (u,v) -> warped px (M) -> target px (+ix,+iy) -> MGA (box[0]+x*R, box[3]-y*R)
    A = np.vstack([M, [0, 0, 1]])

    def to_mga(pts):
        q = np.c_[np.asarray(pts, float), np.ones(len(pts))] @ A.T
        return np.c_[box[0] + (q[:, 0] + ix) * R, box[3] - (q[:, 1] + iy) * R]

    row = {"chapter": cfg["chapter"], "route": "raster_land_road_mask_matched_to_cadastre", "match_score": round(score, 3),
           "m_per_px": round(s, 3), "rotation_deg": rot, "plan_line_to_lot_edge_median_m": 0.0}
    line = sfc.colour_mask(rgb, "red").astype(np.uint8) * 255
    parts = []
    for kk in (16, 24):
        joined = cv2.dilate(line, np.ones((kk, kk), np.uint8))
        cs, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        parts = []
        for c in cs:
            f = np.zeros_like(joined)
            cv2.drawContours(f, [c], -1, 255, cv2.FILLED)
            f = cv2.erode(f, np.ones((kk, kk), np.uint8))
            cc, _ = cv2.findContours(f, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            for q in cc:
                if cv2.contourArea(q) > 0.01 * W * H:
                    r = q[:, 0, :].astype(float)
                    parts.append(Polygon(np.c_[r[:, 0], -r[:, 1]]).buffer(0))
        if parts:
            break
    if not parts:
        raise SystemExit("no closed site boundary on the figure")
    fig_outline = unary_union(parts)
    placed = unary_union([Polygon(to_mga(np.c_[np.asarray(p.exterior.coords)[:, 0], -np.asarray(p.exterior.coords)[:, 1]]))
                          .buffer(0) for p in parts])
    lots, unc = [], []
    for part in getattr(placed, "geoms", [placed]):
        segs = list(zip(list(part.exterior.coords)[:-1], list(part.exterior.coords)[1:]))
        _, ins, u = cb.lots_inside(segs, cad)
        lots += [x for _, x in ins]
        unc += [x for _, x, _ in u if x.difference(part).area <= 300]
    merged = unary_union(lots + unc).buffer(0.3).buffer(-0.3)
    cand = unary_union([q for q in getattr(merged, "geoms", [merged]) if q.area >= 20])
    row["lots"] = [len(lots), len(unc)]
    row.update(_cand=cand, _placed=placed, _fit=None, _nums=[], _figoutline=fig_outline)
    return row


def boundary_points(row: dict, k: int = 2, band: float = 80.0) -> dict:
    """Register points beside the boundary: inside the FITTED figure outline the candidate must contain them, outside
    it must not (the plan prints no house numbers and the chapter names no addresses)."""
    placed, cand = row["_placed"], row["_cand"]
    x0, y0, x1, y1 = placed.bounds
    fs, off = [], 0
    while True:
        page = rf._get(rf.ADDR, {"where": "1=1", "geometry": f"{x0-band},{y0-band},{x1+band},{y1+band}",
                                 "geometryType": "esriGeometryEnvelope", "inSR": "28356", "spatialRel": "esriSpatialRelIntersects",
                                 "outFields": "address", "returnGeometry": "true", "outSR": "28356", "f": "json",
                                 "resultOffset": off, "resultRecordCount": 1000})
        fs += page.get("features") or []
        if not page.get("exceededTransferLimit") or not page.get("features"):
            break
        off += len(page["features"])
    ring = placed.boundary
    ins, outs = [], []
    for f in fs:
        q = Point(f["geometry"]["x"], f["geometry"]["y"])
        dist = ring.distance(q)
        if dist > band or dist < 4:
            continue
        (ins if placed.contains(q) else outs).append({"address": f["attributes"]["address"], "dist_m": round(dist, 1),
                                                      "ok": cand.buffer(1).contains(q) == placed.contains(q)})
    pick = lambda L: sorted(L, key=lambda r: r["dist_m"])[:k]  # noqa: E731
    return {"inside_checked": len(ins), "inside_ok": sum(r["ok"] for r in ins), "outside_checked": len(outs),
            "outside_ok": sum(r["ok"] for r in outs), "inside": pick(ins), "outside": pick(outs),
            "source": "register points within 80 m of the boundary"}


def run(cfg: dict) -> dict:
    row = {"raster": fit_raster, "lotmask": fit_lotmask}.get(cfg.get("kind"), fit_vector)(cfg)
    cand, fo = row["_cand"], row["_figoutline"]
    # roads inside the plan line are not lots: close them over for the SHAPE score only
    row["iou_vs_figure"] = sfc.shape_iou(fo, cand.buffer(CLOSE_M).buffer(-CLOSE_M))[0] if not cand.is_empty else 0.0
    row["address_proof"] = address_proof(row)
    if cfg.get("address_checks"):  # addresses the chapter's own text places inside / outside (no house numbers on the plan)
        ac = cfg["address_checks"]
        grown = cand.buffer(1)
        ins = [(a, (lambda q: q is not None and grown.contains(q))(fv.address_point(a))) for a in ac["inside"]]
        outs = [(a, (lambda q: q is not None and not grown.contains(q))(fv.address_point(a))) for a in ac["outside"]]
        row["address_proof"] = {"inside_checked": len(ins), "inside_ok": sum(ok for _, ok in ins),
                                "outside_checked": len(outs), "outside_ok": sum(ok for _, ok in outs),
                                "inside": [{"address": a, "ok": ok} for a, ok in ins],
                                "outside": [{"address": a, "ok": ok} for a, ok in outs], "source": "chapter text"}
    elif row["address_proof"]["inside_checked"] == 0 and cfg.get("boundary_points"):
        row["address_proof"] = boundary_points(row)
    ap = row["address_proof"]
    named_in = {a: (lambda q: q is not None and cand.buffer(1).contains(q))(fv.address_point(a)) for a in cfg.get("must_contain", [])}
    if named_in:
        row["chapter_named_addresses_inside"] = named_in
    pic = OUTDIR / f"{cfg['chapter']}_{cfg['precinct_id']}.png"
    draw(row, pic)
    row["picture"] = str(pic.relative_to(REPO)).replace("\\", "/")
    fails = []
    if row["iou_vs_figure"] < MATCH:
        fails.append(f"shape IoU {row['iou_vs_figure']} < {MATCH}")
    if ap["inside_ok"] < 2 or ap["outside_ok"] < 2:
        fails.append(f"address points: inside {ap['inside_ok']}/{ap['inside_checked']}, outside {ap['outside_ok']}/{ap['outside_checked']}")
    if not all(named_in.values()):
        fails.append(f"chapter-named address not inside: {[a for a, ok in named_in.items() if not ok]}")
    if row["plan_line_to_lot_edge_median_m"] > cfg.get("lot_edge_max_m", 2.0):
        fails.append("plan lot lines not on cadastre lot edges")
    row["refused"] = "; ".join(fails) if fails else None
    return row


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="")
    a = ap.parse_args()
    OUTDIR.mkdir(parents=True, exist_ok=True)
    cfgs = json.loads((OUTDIR / "config.json").read_text(encoding="utf-8"))["vector"]
    rep_path, geo_path = OUTDIR / "candidates_report.json", OUTDIR / "candidates.geojson"
    report = json.loads(rep_path.read_text(encoding="utf-8")) if rep_path.exists() else {}
    feats = {f["properties"]["precinct_id"]: f
             for f in (json.loads(geo_path.read_text(encoding="utf-8"))["features"] if geo_path.exists() else [])}
    for cfg in cfgs:
        if a.only and cfg["id"] not in a.only.split(","):
            continue
        try:
            row = run(cfg)
        except SystemExit as e:
            row = {"chapter": cfg["chapter"], "refused": str(e)}
        p = {k: v for k, v in row.items() if not k.startswith("_")}
        p["precinct_id"] = cfg["precinct_id"]
        p["pages_keyed"] = cfg.get("pages_keyed")
        report[cfg["id"]] = p
        feats.pop(cfg["precinct_id"], None)
        if not row.get("refused") and "_cand" in row:
            feats[cfg["precinct_id"]] = cb.feature(cfg["precinct_id"], cfg["name"], row["_cand"], {
                "status": "CANDIDATE -- not loaded", "method": row["route"], "source": f"{cfg['chapter']}.pdf p{cfg['page']}",
                "proof": {k: v for k, v in p.items() if k != "address_proof"}, "pages_keyed": cfg.get("pages_keyed")})
        print(json.dumps(p, default=str), flush=True)
        rep_path.write_text(json.dumps(report, indent=1, default=str), encoding="utf-8")
        geo_path.write_text(json.dumps({"type": "FeatureCollection", "features": list(feats.values())}), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
