#!/usr/bin/env python3
"""Compare a site outline with the site map printed in the chapter itself (DQ-143).

prior-art-checked: build_cb_centre_boundaries.py fits a VECTOR figure's lot lines to the cadastre
by ICP to BUILD an outline; it cannot read a raster aerial with a red line, and it needs hand-set
start points. This only SCORES an outline already built from lots or addresses, so it needs no
georeferencing: shape is compared up to scale, rotation and shift.

METHOD (deterministic; no model reads anything)
  1 figure outline  raster: pixels of the outline colour on the rendered page, dilated to close
                    dashes, outer contour filled, eroded back. vector: the PDF's own stroked path
                    of that colour, polygonised.
  2 shape score     both polygons centred and scaled to unit area; the candidate is rotated in
                    1-degree steps (then 0.1) and the best intersection-over-union is kept.
  3 verdict         PASS at IoU >= MATCH, calibrated on known-right and known-wrong candidates.
"""
from __future__ import annotations

import math

import numpy as np
from shapely import affinity
from shapely.geometry import LineString, Polygon
from shapely.ops import polygonize, unary_union

MATCH = 0.85
#: An outline smaller than this share of the page is a legend swatch, not the site (Marco Ave
#: legend box scored 0.999 against a rectangular site by luck before this guard).
MIN_PAGE_SHARE = 0.01


def _unit(poly):
    """Centre on the centroid and scale to area 1."""
    c = poly.centroid
    p = affinity.translate(poly, -c.x, -c.y)
    s = 1 / math.sqrt(p.area)
    return affinity.scale(p, s, s, origin=(0, 0))


def shape_iou(figure_poly, candidate_poly) -> tuple[float, float]:
    """Best IoU over rotations of the candidate, and the rotation (degrees) that gave it."""
    a, b = _unit(figure_poly), _unit(candidate_poly)

    def iou(deg: float) -> float:
        r = affinity.rotate(b, deg, origin=(0, 0))
        inter = a.intersection(r).area
        return inter / (a.area + r.area - inter)

    best = max(((iou(d), d) for d in range(0, 360)), key=lambda t: t[0])
    fine = max(((iou(best[1] + d / 10), best[1] + d / 10) for d in range(-10, 11)), key=lambda t: t[0])
    return round(fine[0], 3), round(fine[1] % 360, 1)


def colour_mask(img, colour: str):
    """Pixels of the outline colour. 'red' excludes orange shading (g ~160)."""
    import cv2
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    if colour == "red":
        return (r > 150) & (g < 100) & (b < 100) & (r - g > 80)
    if colour == "green":
        return (g > 120) & (g - r > 60) & (g - b > 30)
    if colour == "orange":
        return (r > 200) & (g > 110) & (g < 190) & (b < 80)
    if colour == "black-thick":
        dark = ((r < 70) & (g < 70) & (b < 70)).astype(np.uint8)
        return cv2.morphologyEx(dark, cv2.MORPH_OPEN, np.ones((4, 4), np.uint8)) > 0
    raise ValueError(colour)


#: Dash gaps differ by map, so the join step grows until the outline closes: the closed shape's
#: filled area must be at least FILL_RATIO times the line's own pixels. Same input, same answer.
CLOSE_STEPS = (6, 10, 16, 24, 32, 48)
FILL_RATIO = 5  # measured: an open line fills 0.1-3x its pixels, a closed one 10x+


def raster_outline(page, colour: str, dpi: int = 200, clip=None):
    """The filled region inside the outline drawn in `colour`, or None if it never closes."""
    import cv2
    pix = page.get_pixmap(dpi=dpi, clip=clip)
    img = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].astype(int)
    line = colour_mask(img, colour).astype(np.uint8) * 255
    line_px = int((line > 0).sum())
    if line_px < 50:
        return None
    for k in CLOSE_STEPS:
        kernel = np.ones((k, k), np.uint8)
        joined = cv2.dilate(line, kernel)
        contours, _ = cv2.findContours(joined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        filled = np.zeros_like(joined)
        cv2.drawContours(filled, [max(contours, key=cv2.contourArea)], -1, 255, thickness=cv2.FILLED)
        filled = cv2.erode(filled, kernel)
        if int((filled > 0).sum()) < FILL_RATIO * line_px:
            continue
        contours, _ = cv2.findContours(filled, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        big = max(contours, key=cv2.contourArea).reshape(-1, 2)
        if len(big) < 4 or cv2.contourArea(big) < MIN_PAGE_SHARE * filled.size:
            continue  # a legend swatch, not the site (cross-review 2026-10-12)
        poly = Polygon(np.column_stack([big[:, 0], -big[:, 1]]).astype(np.float64)).buffer(0)
        return max(poly.geoms, key=lambda g: g.area) if poly.geom_type == "MultiPolygon" else poly
    return None


def vector_outline(page, stroke: tuple[float, float, float], tol: float = 0.08,
                   dashed: bool | None = None, min_width: float = 0.0):
    """Polygonise the page's own stroked paths of colour `stroke` (RGB 0-1), optionally only dashed
    ones and only at least `min_width` wide (the legend's site-boundary style); largest face wins."""
    segs = []
    for d in page.get_drawings():
        col = d.get("color")
        if not col or max(abs(x - y) for x, y in zip(col, stroke)) > tol:
            continue
        is_dashed = bool(d.get("dashes") and d["dashes"] not in ("[] 0", ""))
        if (dashed is not None and is_dashed != dashed) or (d.get("width") or 0) < min_width:
            continue
        for item in d["items"]:
            if item[0] == "l":
                segs.append(LineString([(item[1].x, -item[1].y), (item[2].x, -item[2].y)]))
            elif item[0] == "c":
                segs.append(LineString([(item[1].x, -item[1].y), (item[4].x, -item[4].y)]))
            elif item[0] == "re":
                q = item[1]
                segs.append(LineString([(q.x0, -q.y0), (q.x1, -q.y0), (q.x1, -q.y1), (q.x0, -q.y1), (q.x0, -q.y0)]))
    if not segs:
        return None
    # Dashes leave gaps: close them by buffering, then take the outer ring of the largest blob.
    blob = unary_union([s.buffer(2.0) for s in segs])
    parts = [blob] if blob.geom_type == "Polygon" else list(blob.geoms)
    faces = [Polygon(p.exterior).buffer(-2.0) for p in parts]
    faces += list(polygonize(unary_union(segs)))
    # A legend swatch is drawn in the same style; a real site outline is a real share of the page.
    page_area = page.rect.width * page.rect.height
    faces = [f for f in faces if not f.is_empty and f.area >= MIN_PAGE_SHARE * page_area]
    return max(faces, key=lambda f: f.area) if faces else None


#: A neighbour search may only widen a candidate already anchored by the plan's own address or lot
#: list, and only when one combination clearly wins: a plain rectangle matches many parcels
#: (0.98 against four unrelated Lindfield lots), so shape alone never locates a site.
SEARCH_WIN, SEARCH_MARGIN, SEARCH_EXTRA = 0.95, 0.10, 3


def _mga_union(cur, lots):
    """The lots' union in metres (MGA zone 56), projected by PostGIS."""
    from shapely import wkt
    cur.execute("SELECT ST_AsText(ST_Transform(ST_Union(geom), 28356)) FROM nsw_cadastre_lots"
                " WHERE lotidstring = ANY(%s)", (lots,))
    text = cur.fetchone()[0]
    return wkt.loads(text) if text else None


def figure_outline(pdf_bytes: bytes, fig: dict):
    import fitz
    page = fitz.open(stream=pdf_bytes, filetype="pdf")[fig["page"] - 1]
    if fig["mode"] == "raster":
        return raster_outline(page, fig["colour"])
    return vector_outline(page, tuple(fig["stroke"]), dashed=fig.get("dashed"), min_width=fig.get("min_width", 0.0))


def map_check(cur, pdf_bytes: bytes, fig: dict | None, lots: list[str]) -> dict:
    """Score `lots` against the chapter's own site map. Widens by neighbour search only as above."""
    if not fig or fig.get("unreadable"):
        return {"status": "unreadable", "why": (fig or {}).get("unreadable", "no figure recorded"), "lots": lots}
    outline = figure_outline(pdf_bytes, fig)
    if outline is None or not lots:
        return {"status": "fail", "why": "site outline not found on the map" if outline is None else "no candidate lots",
                "lots": lots}
    iou, rot = shape_iou(outline, _mga_union(cur, lots))
    out = {"status": "pass" if iou >= MATCH else "fail", "iou": iou, "rotation": rot, "lots": lots}
    if iou >= MATCH:
        return out
    import itertools
    cur.execute("SELECT DISTINCT n.lotidstring FROM nsw_cadastre_lots a JOIN nsw_cadastre_lots n"
                " ON n.geom && ST_Expand(a.geom, 0.0002) AND ST_DWithin(a.geom, n.geom, 0.0001)"
                " WHERE a.lotidstring = ANY(%s) AND NOT n.lotidstring = ANY(%s)", (lots, lots))
    near = [r[0] for r in cur.fetchall()]
    scored = sorted(((shape_iou(outline, _mga_union(cur, lots + list(c)))[0], lots + list(c))
                     for k in range(1, SEARCH_EXTRA + 1) for c in itertools.combinations(near, k)), reverse=True)
    if scored and scored[0][0] >= SEARCH_WIN and (len(scored) == 1 or scored[0][0] - scored[1][0] >= SEARCH_MARGIN):
        return {"status": "pass", "iou": scored[0][0], "rotation": None, "lots": scored[0][1],
                "widened_from": lots, "runner_up": scored[1][0] if len(scored) > 1 else None}
    out["best_search"] = scored[0][0] if scored else None
    return out
