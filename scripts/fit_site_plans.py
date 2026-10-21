#!/usr/bin/env python3
"""Outlines for single-site DCP sections whose addresses the NSW register no longer holds, from the site plan.

prior-art-checked: build_site_boundaries.py proves a site from its lot list or its register addresses; for C-B 8.3
S5/S7/S8 neither works (consolidated sites, renumbered). site_figure_check.py scores an outline against a figure but
does not place one. This places the plan's own site shape on the cadastre, then reuses site_figure_check.shape_iou.

METHOD (deterministic; nothing is read by a model -- the street corner is the plan's own labels)
  1 shape     the plan's coloured site (coloured pixels, closed, largest blob, holes filled).
  2 seed      where the two streets the plan labels cross (NSW RoadSegment centrelines).
  3 place     north up (the plan has a north arrow); scale searched; FFT match of the shape's edge against
              cadastre lot edges within 250 m of the seed.
  4 lots      cadastre lots >= 80% inside the placed shape.
ACCEPTANCE (else REFUSED, nothing written)
  shape IoU (site_figure_check.shape_iou) of the lots' union vs the plan's shape >= 0.85
  share of the placed shape's edge within 2 m of a lot edge >= 0.6
  every address that the register DOES hold for the section is inside (e.g. 243A Hume Highway for S7)

PRECINCT MAPS (config key "precincts"; Woollahra DCP 2015 B1, 2026-10-21). A precinct map is a raster with the
cadastre drawn in grey and the precinct filled light blue. No seed and no street labels are needed: the map's own grey
lot lines are matched (FFT, north up, scale searched) against every cadastre edge in the config's box, 2 m grid
first, then 0.5 m round the best. The outline is the cadastre lots >= 80% inside the placed blue area, plus the road
space the map colours (the DCP draws precinct edges on road centrelines; road space holds no lot), plus the map's part
of any lot 20-80% inside (it straddles the map's own line). A white area inside the blue ('Areas Excluded From the
Precinct') stays out. Every map is also drawn (checks/) and looked at before any load.
ACCEPTANCE (else REFUSED, nothing written)
  share of the map's lot-line pixels within 1 m of a cadastre edge at the 0.5 m fit       >= 0.5
    (measured 2026-10-21: the B1 maps are drawn on the ~2015 cadastre, with labels and view arrows over the lines;
     Darling Point scored 0.565 on a fit whose picture lies on the lot lines along its whole edge)
  the best placement beats every placement > 100 m away at the same scale by               >= 0.15 (2 m grid score)
  shape IoU (site_figure_check.shape_iou) of the outline vs the placed blue area           >= 0.85
  IoU on lot land only: lots inside vs the blue area minus road space                       >= 0.85
Usage: python scripts/fit_site_plans.py --config data/woollahra_precincts/b1_maps.json
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from pathlib import Path

import cv2
import fitz
import numpy as np
from PIL import Image
from scipy.signal import fftconvolve
from scipy.spatial import cKDTree
from shapely.geometry import Point, Polygon, mapping, shape
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cb_centre_boundaries as cb  # noqa: E402
import fit_cb_raster_centres as rf  # noqa: E402
import site_figure_check as sfc  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "canterbury_bankstown_precincts"
RES = 0.5  # metres per pixel of the placement search
IOU_MIN, EDGE_MIN = 0.85, 0.6


def site_shape(pdf: Path, page: int) -> np.ndarray:
    """Binary mask of the plan's site (the topmost image on the page)."""
    d = fitz.open(pdf)
    p = d[page - 1]
    im = min(p.get_images(full=True), key=lambda x: p.get_image_rects(x[0])[0].y0)
    a = np.asarray(Image.open(io.BytesIO(d.extract_image(im[0])["image"])).convert("RGB")).astype(int)
    col = (a.max(2) - a.min(2) > 18) & (a.mean(2) < 250)
    m = cv2.morphologyEx(col.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))
    _, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    blob = (lab == 1 + int(np.argmax(st[1:, 4]))).astype(np.uint8)
    cs, _ = cv2.findContours(blob, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    filled = np.zeros_like(blob)
    cv2.drawContours(filled, cs, -1, 1, -1)
    return filled


def outline_shape(pdf: Path, page: int, colour: str) -> np.ndarray:
    """Binary mask of the region inside the outline drawn in `colour` (site_figure_check.raster_outline),
    for plans drawn over an aerial where every pixel is coloured. Cached beside the PDFs: same page, same mask."""
    cache = OUT / ".page_cache" / f"{pdf.stem}_p{page}_{colour}_outline.png"
    if cache.exists():
        return _crop((cv2.imread(str(cache), cv2.IMREAD_GRAYSCALE) > 0).astype(np.uint8))
    p = fitz.open(pdf)[page - 1]
    poly = sfc.raster_outline(p, colour)
    if poly is None:
        raise SystemExit(f"[ABORT] no closed {colour} outline on p{page}")
    pix = p.get_pixmap(dpi=200)
    mask = np.zeros((pix.height, pix.width), np.uint8)
    ring = np.asarray(poly.exterior.coords)
    cv2.fillPoly(mask, [np.c_[ring[:, 0], -ring[:, 1]].astype(np.int32)], 1)
    cache.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(cache), mask * 255)
    return _crop(mask)


def _crop(mask: np.ndarray, pad: int = 10) -> np.ndarray:
    """The outline's bounding box only: a whole-page mask must fit the 500 m search window at the fitted scale,
    which excluded the true placement of C-B 11.4 (page 410 m tall at 0.175 m/px)."""
    ys, xs = np.nonzero(mask)
    return mask[max(0, ys.min() - pad):ys.max() + pad + 1, max(0, xs.min() - pad):xs.max() + pad + 1]


def register_point(addr: str) -> tuple[float, float] | None:
    """MGA point of an NSW address register entry (prefix match), or None."""
    fs = rf._get(rf.ADDR, {"where": f"address LIKE '{addr}%'", "outFields": "address", "returnGeometry": "true",
                           "outSR": "28356", "f": "json", "resultRecordCount": 1}).get("features") or []
    return (fs[0]["geometry"]["x"], fs[0]["geometry"]["y"]) if fs else None


def corner(cx: float, cy: float, a: str, b: str) -> tuple[float, float]:
    pts, keys = rf.fetch_roads(cx, cy, 2500)
    pa, _ = rf.named(pts, keys, [a])
    pb, _ = rf.named(pts, keys, [b])
    if not len(pa) or not len(pb):
        raise SystemExit(f"[ABORT] street not found near seed: {a if not len(pa) else b}")
    dd, ii = cKDTree(pb).query(pa)
    k = int(np.argmin(dd))
    return tuple((pa[k] + pb[ii[k]]) / 2)


def place(mask: np.ndarray, sx: float, sy: float, cad, scales, streets=None, anchors=None) -> tuple:
    """Best (edge share, m/px, x0, y0): image pixel (c, r) -> MGA (x0 + c*s, y0 - r*s)."""
    x_0, y_1 = sx - 250, sy + 250
    W = H = int(500 / RES) + 1
    E = np.zeros((H, W), np.float32)
    for _, g in cad:
        for poly in getattr(g, "geoms", [g]):
            c = np.asarray(poly.exterior.coords)
            cv2.polylines(E, [np.c_[(c[:, 0] - x_0) / RES, (y_1 - c[:, 1]) / RES].astype(np.int32)], True, 1, 1)
    E = cv2.dilate(E, np.ones((9, 9), np.uint8))   # +-2 m
    edge = cv2.morphologyEx(mask, cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
    best = (-1.0, 0.0, 0.0, 0.0)
    for s in scales:
        k = s / RES
        e = cv2.resize(edge, (max(1, int(edge.shape[1] * k)), max(1, int(edge.shape[0] * k))), interpolation=cv2.INTER_AREA)
        e = (e > 0).astype(np.float32)
        if e.shape[0] >= H or e.shape[1] >= W or e.sum() < 50:
            continue
        C = fftconvolve(E, e[::-1, ::-1], mode="valid") / e.sum()
        if anchors is not None and len(anchors):
            # only shifts that put EVERY register point the site holds inside the shape (C-B 11.4: a shrunken shape
            # inside two lots scored edge 1.0 with all 8 points outside; top-peak filtering found no valid shift)
            mk = cv2.resize(mask, (e.shape[1], e.shape[0]), interpolation=cv2.INTER_NEAREST)
            iy, ix = np.indices(C.shape)
            for ax, ay in np.c_[(anchors[:, 0] - x_0) / RES, (y_1 - anchors[:, 1]) / RES].astype(int):
                r, q = ay - iy, ax - ix
                ok = (r >= 0) & (q >= 0) & (r < mk.shape[0]) & (q < mk.shape[1])
                hit = np.zeros(C.shape, bool)
                hit[ok] = mk[r[ok], q[ok]] > 0
                C = np.where(hit, C, -1.0)
        # the plan labels the streets the site fronts: a placement whose edge is not within 20 m of BOTH is not the
        # site (a shrunken shape scores well inside one big lot -- S5/S7 first run). Best few candidates per scale.
        for idx in np.argsort(C, axis=None)[::-1][:40]:
            iy, ix = np.unravel_index(idx, C.shape)
            if C[iy, ix] <= max(best[0], 0.0):
                break
            ox, oy = x_0 + ix * RES, y_1 - iy * RES
            if streets is not None:
                ys, xs = np.nonzero(e)
                pts = np.c_[ox + xs * RES, oy - ys * RES]
                if any(cKDTree(st).query(pts)[0].min() > 20 for st in streets):
                    continue
            best = (float(C[iy, ix]), float(s), ox, oy)
            break
    return best


def fit(c: dict) -> dict:
    pdf = OUT / ".pdf_cache" / c["pdf"]
    mask = outline_shape(pdf, c["page"], c["outline_colour"]) if c.get("outline_colour") else site_shape(pdf, c["page"])
    sx, sy = rf.seed({"seed": "street", "streets": [c["streets"][0]], "suburb": c["suburb"]})
    sx, sy = corner(sx, sy, *c["streets"][:2])
    pts, keys = rf.fetch_roads(sx, sy, 600)
    streets = [rf.named(pts, keys, [n])[0] for n in c["streets"][:2]]
    cad = cb.fetch_cadastre(tuple(float(v) for v in (sx - 300, sy - 300, sx + 300, sy + 300)))  # qa-ignore: v is seed arithmetic, never None
    anchors = None
    if c.get("anchor_placement"):
        anchors = np.array([p for p in (register_point(a) for a in (c.get("register_addresses") or [])) if p])
    share, s, x0, y0 = place(mask, sx, sy, cad, np.geomspace(*c.get("scale_range", (0.04, 0.4)), 70), streets, anchors)
    share, s, x0, y0 = place(mask, sx, sy, cad, np.linspace(s * 0.95, s * 1.05, 15), streets, anchors)
    cs, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    ring = max(cs, key=cv2.contourArea)[:, 0, :].astype(float)
    shape_mga = Polygon(np.c_[x0 + ring[:, 0] * s, y0 - ring[:, 1] * s]).buffer(0)
    lots = []
    for lot, g in cad:
        g = g if g.is_valid else g.buffer(0)
        if g.area > 0 and g.intersects(shape_mga) and g.intersection(shape_mga).area / g.area >= 0.8:
            lots.append((lot, g))
    row = {"precinct_id": c["precinct_id"], "corner_mga": [round(sx), round(sy)], "edge_share": round(share, 3),
           "m_per_px": round(s, 4), "lots": sorted(lot for lot, _ in lots), "shape_m2": round(shape_mga.area)}
    if not lots:
        row["refused"] = "no lot inside the placed shape"
        return row
    union = unary_union([g for _, g in lots])
    row["iou"] = round(sfc.shape_iou(shape_mga, union)[0], 3)
    row["lots_m2"] = round(union.area)
    inside_ok = []
    for addr in (c.get("register_addresses") or []):
        pt = register_point(addr)
        inside_ok.append(pt is not None and union.buffer(1).contains(Point(*pt)))
    row["register_addresses_inside"] = inside_ok
    fails = [m for m, bad in (("shape does not match the plan", row["iou"] < IOU_MIN),
                              ("plan edge not on lot lines", share < EDGE_MIN),
                              ("a register address is outside", not all(inside_ok))) if bad]
    if fails:
        row["refused"] = "; ".join(fails)
    else:
        row["_geom"] = union
    return row


# ---------------------------------------------------------------- precinct maps (see the docstring)
LINE_MIN, PEAK_MARGIN = 0.5, 0.15


def precinct_map(pdf: Path, page: int) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(rgb, grey lot-line mask, blue precinct mask) inside the map's black frame (the largest image on the page)."""
    d = fitz.open(pdf)
    p = d[page - 1]
    xref = max(p.get_images(full=True), key=lambda im: d.extract_image(im[0])["width"] * d.extract_image(im[0])["height"])[0]
    a = np.asarray(Image.open(io.BytesIO(d.extract_image(xref)["image"])).convert("RGB")).astype(int)
    blk = a.max(2) < 70
    cols = np.nonzero(blk.sum(0) > 0.5 * blk.shape[0])[0]   # frame verticals: map's left edge, map/legend divider
    rows = np.nonzero(blk.sum(1) > 0.3 * blk.shape[1])[0]
    if len(cols) < 2 or len(rows) < 2:
        raise SystemExit(f"[ABORT] no map frame on p{page}")
    a = a[rows[0] + 6:rows[-1] - 5, cols[0] + 6:cols[-1] - 5]
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lines = ((a.mean(2) >= 140) & (a.mean(2) <= 205) & (a.max(2) - a.min(2) < 25)).astype(np.uint8)
    blue = ((b >= 225) & (g >= 200) & (r < 215) & (b - r > 30)) | ((b > 180) & (r < 80) & (g > 120))  # fill | edge
    m = cv2.morphologyEx(blue.astype(np.uint8), cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    keep = np.isin(lab, [i for i in range(1, n) if st[i, 4] >= 20000]).astype(np.uint8)  # drops labels, arrows
    cs, _ = cv2.findContours(keep, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
    out = np.zeros_like(keep)
    cv2.drawContours(out, cs, -1, 1, -1)
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(((out > 0) & (keep == 0)).astype(np.uint8), 4)
    white = a.min(2) >= 235
    for i in range(1, n2):  # a hole is lines/labels (filled) unless it is a white area ('excluded from the precinct')
        comp = lab2 == i
        if st2[i, 4] >= 1500 and white[comp].mean() > 0.8:
            out[comp] = 0
    # 'Areas Excluded From the Precinct' drawn as a thick BLACK closed line round unfilled land inside the blue (B1 Maps
    # 8 and 11: O'Sullivan Road / Plumer Road neighbourhood centres). The rule above misses them: a box under 1,500 px,
    # or one whose lot lines and leader line keep the hole under 80% white. Here: every hole of the black mask >= 300 px
    # (letters' holes are smaller) with under 20% blue inside, lying in the blue area, is cut out with its own line.
    blk = (a.max(2) < 70).astype(np.uint8)
    cs3, hier3 = cv2.findContours(blk, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    for i, c in enumerate(cs3):
        if hier3[0][i][3] < 0 or cv2.contourArea(c) < 300:
            continue
        hole = np.zeros_like(out)
        cv2.drawContours(hole, [c], -1, 1, -1)
        hb = hole > 0
        if blue[hb].mean() < 0.2 and out[hb].mean() > 0.5:
            out[cv2.dilate(hole, np.ones((9, 9), np.uint8)) > 0] = 0
    return a, lines, out


def _line_search(lines: np.ndarray, E: np.ndarray, res: float, scales, x0: float, y1: float, far_m: float = 0) -> list:
    """(score, m/px, X, Y of the map's top-left[, best score > far_m away at that scale]) per scale: share of line
    pixels on a cadastre edge (+-1 cell)."""
    Ed = cv2.dilate(E, np.ones((3, 3), np.uint8)).astype(np.float32)
    out = []
    for s in scales:
        k = s / res
        e = cv2.resize(lines.astype(np.float32), (int(lines.shape[1] * k), int(lines.shape[0] * k)), interpolation=cv2.INTER_AREA)
        e = (e > 0.15).astype(np.float32)
        if e.shape[0] >= Ed.shape[0] or e.shape[1] >= Ed.shape[1] or e.sum() < 100:
            continue
        C = fftconvolve(Ed, e[::-1, ::-1], mode="valid") / e.sum()
        iy, ix = np.unravel_index(int(np.argmax(C)), C.shape)
        row = (float(C[iy, ix]), float(s), x0 + ix * res, y1 - iy * res)
        if far_m:
            r = int(far_m / res)
            C[max(0, iy - r):iy + r + 1, max(0, ix - r):ix + r + 1] = -1
            row += (float(C.max()),)
        out.append(row)
    return out


def _edges(cad, box: tuple, res: float) -> np.ndarray:
    x0, y0, x1, y1 = box
    E = np.zeros((int((y1 - y0) / res) + 1, int((x1 - x0) / res) + 1), np.uint8)
    for _, g in cad:
        for poly in getattr(g, "geoms", [g]):
            for ring in [poly.exterior, *poly.interiors]:
                c = np.asarray(ring.coords)
                cv2.polylines(E, [np.c_[(c[:, 0] - x0) / res, (y1 - c[:, 1]) / res].astype(np.int32)], True, 1, 1)
    return E


def place_on_lot_lines(lines: np.ndarray, cad, box: tuple, scale_range) -> dict:
    # uniqueness is judged at the SAME scale: across scales a smaller map always fits dense lot lines somewhere better
    coarse = _line_search(lines, _edges(cad, box, 2.0), 2.0, np.geomspace(*scale_range, 30), box[0], box[3], far_m=100)
    best = max(coarse)
    s, ox, oy = best[1:4]
    win = (ox - 60, oy - lines.shape[0] * s * 1.06 - 60, ox + lines.shape[1] * s * 1.06 + 60, oy + 60)
    fine = max(_line_search(lines, _edges(cad, win, 0.5), 0.5, np.linspace(s * 0.96, s * 1.04, 17), win[0], win[3]))
    return {"coarse": round(best[0], 3), "runner_up_far": round(best[4], 3),
            "line_share": round(fine[0], 3), "m_per_px": round(fine[1], 4), "x0": fine[2], "y0": fine[3]}


def fit_precinct(c: dict, pdf: Path, cad, box: tuple, scale_range) -> dict:
    a, lines, mask = precinct_map(pdf, c["page"])
    row = {"precinct_id": c["precinct_id"], "page": c["page"], **place_on_lot_lines(lines, cad, box, scale_range)}
    s, ox, oy = row["m_per_px"], row.pop("x0"), row.pop("y0")
    cs, hier = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    tf = lambda r: np.c_[ox + r[:, 0] * s, oy - r[:, 1] * s]  # noqa: E731
    fig = unary_union([Polygon(tf(cs[i][:, 0, :].astype(float)),
                               [tf(cs[j][:, 0, :].astype(float)) for j in range(len(cs)) if hier[0][j][3] == i and len(cs[j]) >= 4]
                               ).buffer(0) for i in range(len(cs)) if hier[0][i][3] == -1 and len(cs[i]) >= 4])
    fx0, fy0, fx1, fy1 = fig.bounds
    inside, other = [], []
    for lot, g in cad:
        b = g.bounds
        if b[2] < fx0 or b[0] > fx1 or b[3] < fy0 or b[1] > fy1:
            continue
        g = g if g.is_valid else g.buffer(0)
        if g.area <= 0 or not g.intersects(fig):
            continue
        share = g.intersection(fig).area / g.area
        (inside if share >= cb.IN_SHARE else other).append((lot, g, share))
    lots_u = unary_union([g for _, g, _ in inside])
    road = fig.difference(unary_union([g for _, g, _ in inside + other]))   # coloured space no lot holds
    # a lot 20-80% inside straddles the map's own line (the 2015 map was drawn on an older cadastre, e.g. Darling Point's
    # 10 ha foreshore park lot 7321//DP1165813 at 53%): keep the map's part of it, not the whole lot and not none of it
    cut = [g.intersection(fig) for _, g, sh in other if sh > cb.UNCERTAIN_SHARE]
    geom = unary_union([lots_u, road, *cut]).buffer(0)
    land = fig.difference(road)
    inter = lots_u.intersection(land).area
    row.update({"figure_m2": round(fig.area), "lots": len(inside),
                "doubt_lots": sorted(lot for lot, _, sh in other if sh > cb.UNCERTAIN_SHARE),
                "outline_m2": round(geom.area), "iou_shape": sfc.shape_iou(fig, geom)[0],
                "iou_lot_land": round(inter / (lots_u.area + land.area - inter), 3)})
    fails = [m for m, bad in (("map lot lines not on the cadastre", row["line_share"] < LINE_MIN),
                              ("placement not unique", row["coarse"] - row["runner_up_far"] < PEAK_MARGIN),
                              ("shape does not match the map", row["iou_shape"] < IOU_MIN),
                              ("lots do not match the map", row["iou_lot_land"] < IOU_MIN)) if bad]
    if fails:
        row["refused"] = "; ".join(fails)
    row["_geom"], row["_fig"] = geom, fig   # drawn either way; written only when not refused
    return row


def draw_precinct(fig, geom, cad, path: Path) -> None:
    """The placed map's blue area (red, thin) over the cadastre, the accepted outline (green), for a person to look at."""
    x0, y0, x1, y1 = fig.buffer(80).bounds
    img = np.full((int(y1 - y0), int(x1 - x0), 3), 255, np.uint8)
    tf = lambda c: np.c_[c[:, 0] - x0, y1 - c[:, 1]].astype(np.int32)  # noqa: E731
    for _, g in cad:
        b = g.bounds
        if b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1:
            continue
        for p in getattr(g, "geoms", [g]):
            cv2.polylines(img, [tf(np.asarray(p.exterior.coords))], True, (170, 170, 170), 1)
    for g, col, w in ((geom, (0, 160, 0), 3), (fig, (0, 0, 255), 1)):
        for p in getattr(g, "geoms", [g]):
            for ring in [p.exterior, *p.interiors]:
                cv2.polylines(img, [tf(np.asarray(ring.coords))], True, col, w)
    cv2.imwrite(str(path), img)


SCALE_BAR_TOL = 0.05


def precinct_scale_range(c: dict, cfg: dict) -> tuple:
    """Scales to search for one map. A map whose 'scale_bar' is recorded ({"metres": M, "px": P}: the label printed
    at the bar's right end, and the bar's length in the figure's own pixels) is searched within SCALE_BAR_TOL of M / P;
    otherwise the file's shared 'scale_range'. Measured 2026-10-21: the five Woollahra B1 maps refused under the shared
    0.45-0.9 range print 0.336 (Manning Road) and 0.966 (Bellevue Hill North, Vaucluse West) m/px, outside it, and the
    search pinned near 0.434; the five accepted fits came out 0.5-0.8% above their own bar."""
    sb = c.get("scale_bar")
    if not sb:
        return tuple(cfg["scale_range"])
    m = float(sb["metres"]) / float(sb["px"])
    return (m * (1 - SCALE_BAR_TOL), m * (1 + SCALE_BAR_TOL))


def main_precincts(cfg: dict, out: Path, only: set | None = None) -> int:
    pdf = out / ".pdf_cache" / cfg["pdf"]
    if not pdf.exists():
        raise SystemExit(f"[ABORT] {pdf} missing: curl {cfg['pdf_url']} -o {pdf} (urllib gets 403)")
    box = tuple(float(v) for v in cfg["box_mga"])
    cad = cb.fetch_cadastre(box)
    feats, report, ok_geoms = [], [], []
    for c in cfg["precincts"]:
        if only and c["precinct_id"] not in only:
            continue
        row = fit_precinct(c, pdf, cad, box, precinct_scale_range(c, cfg))
        g, fig = row.pop("_geom"), row.pop("_fig")
        (out / "checks").mkdir(exist_ok=True)
        draw_precinct(fig, g, cad, out / "checks" / f"b1_p{c['page']}.png")
        if "refused" not in row:
            ok_geoms.append(g)
            feats.append(cb.feature(c["precinct_id"], c["name"], g, {
                "method": "dcp_precinct_map_fitted_to_cadastre_lot_lines", "source": f"{cfg['pdf']} p{c['page']} {c['figure']}",
                "quote": c["quote"], "proof": dict(row)}))
        report.append(row)
        print(json.dumps(row), flush=True)
    u = cfg.get("union")
    if u and len(ok_geoms) == len(cfg["precincts"]):  # the chapter's union only when EVERY precinct was accepted
        feats.append(cb.feature(u["precinct_id"], u["name"], unary_union(ok_geoms), {
            "method": "dcp_precinct_map_fitted_to_cadastre_lot_lines", "source": u["source"], "quote": u["quote"],
            "proof": {"members": [c["precinct_id"] for c in cfg["precincts"]]}}))
    if only:
        print("--only: nothing written")
        return 0
    stem = cfg["out_stem"]
    # Compact: all ten plus their union came to 6 MB indented (the repo's limit is 2 MB). Vertices thinned by 0.25 m
    # (the fit is ~4 m positional) and rounded to 1e-6 degrees (~0.1 m); rounding can cross rings, so it is repaired
    # (buffer 0) and rounded once more.
    rnd = lambda geo: json.loads(json.dumps(mapping(geo)), parse_float=lambda v: round(float(v), 6))  # noqa: E731
    for f in feats:
        f["geometry"] = rnd(shape(rnd(shape(f["geometry"]).simplify(2.5e-6, preserve_topology=True))).buffer(0))
    (out / f"{stem}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats},
                                                    separators=(",", ":")), encoding="utf-8")
    (out / f"fit_report_{stem}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"accepted {len(ok_geoms)} / {len(report)}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=str(OUT / "site_plans_8_3.json"))
    ap.add_argument("--only", help="precinct maps: comma-separated precinct ids to try (nothing written)")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    if "precincts" in cfg:
        return main_precincts(cfg, Path(a.config).resolve().parent, set(a.only.split(",")) if a.only else None)
    feats, report = [], []
    for c in cfg["sites"]:
        try:
            row = fit(c)
        except SystemExit as e:
            row = {"precinct_id": c["precinct_id"], "refused": str(e)}
        g = row.pop("_geom", None)
        report.append(row)
        print(json.dumps(row), flush=True)
        if g is not None:
            feats.append(cb.feature(c["precinct_id"], c["name"], g, {
                "method": "dcp_site_plan_shape_fitted_to_cadastre", "source": f"{c['pdf']} p{c['page']} {c['figure']}",
                "quote": c["quote"], "proof": row}))
    stem = Path(a.config).stem  # site_plans_8_3 -> site_plans_8_3.geojson + fit_report_site_plans_8_3.json
    (OUT / f"{stem}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, indent=1),
                                         encoding="utf-8")
    (OUT / f"fit_report_{stem}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"accepted {len(feats)} / {len(report)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
