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
from shapely.geometry import Point, Polygon
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


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=str(OUT / "site_plans_8_3.json"))
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
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
