"""Build data/anef/sydney_anef_2045.json: the four ANEF contours of Sydney Airport's endorsed 2045 chart as map polygons.

prior-art-checked: 2026-11-08. grep of scripts/ services/ data/ for anef: only the old data/anef digitisation (5-point hand-drawn polygons, flags
223 of 400 test lots) and the Western Sydney portal band rule exist. This reads the contours straight from the vector chart, so nothing is hand-drawn.
Plan: ~/.claude/plans/ce-anef-pdf-trace-FEASIBILITY-2026-11-08.md.

Source: Sydney Airport Master Plan 2045, Section 5 Appendices, Appendix H, Map H-1 (PDF page 25). Chapter 15 Map 15-1 is the same chart. Airservices
Australia endorsed ANEF 2045 for technical accuracy on 26 February 2026 (Sydney Airport's Master Plan 2045 page). The four big dark-navy stroke paths
are the contours; the level labels printed on the lines read 20, 25, 30, 35 from the outermost line inward (read on the rendered page, 2026-11-08), and
the build checks that the lines nest in that order.

The georeference file comes from scripts/anef/georef_chart_to_roads.py (run it first); this script refuses a georeference that was not accepted
or that was fitted to a different PDF.

    python scripts/anef/build_sydney_anef_2045.py --pdf <Appendices.pdf> --georef data/anef/sydney_anef_2045_georef.json --out data/anef/sydney_anef_2045.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from pyproj import Transformer

PAGE_INDEX = 24
NAVY = (0.082, 0.216, 0.345)  # contour stroke colour on the page
MIN_ITEMS = 500  # the four contours have 934 to 2305 segments; the other navy strokes are label glyphs
LEVELS = (20, 25, 30, 35)  # outermost to innermost, as labelled on the chart
SIMPLIFY_M = 3.0  # drop points that move the line by less than this
SOURCE_URL = "https://www.sydneyairport.com.au/corporate/planning-and-projects/master-plan/master-plan-2045-downloads"
ENDORSED = "2026-02-26"
FRAME_PT = (0.0, 195.0, 420.0, 830.0)  # the map frame on the page, in points (x0, y0, x1, y1)
ALIGNMENT_BOUND_M = 30.0  # EVERY chart road point lands within 30 m of a real road (share_within_m["30"] is 1.0 in the georef file); the build refuses otherwise
LINE_WIDTH_PT = 1.785  # drawn width of a contour on the chart


def sample_path(items: list) -> np.ndarray:
    pts: list[tuple[float, float]] = []
    for it in items:
        if it[0] == "l":
            pts += [(it[1].x, it[1].y), (it[2].x, it[2].y)]
        elif it[0] == "c":  # cubic Bezier: p1, c1, c2, p2
            p = [np.array([q.x, q.y]) for q in it[1:5]]
            for t in np.linspace(0, 1, 7):
                b = (1 - t) ** 3 * p[0] + 3 * (1 - t) ** 2 * t * p[1] + 3 * (1 - t) * t ** 2 * p[2] + t ** 3 * p[3]
                pts.append((float(b[0]), float(b[1])))
    out = [pts[0]]
    for q in pts[1:]:
        if abs(q[0] - out[-1][0]) > 1e-9 or abs(q[1] - out[-1][1]) > 1e-9:
            out.append(q)
    return np.array(out)


def simplify(xy: np.ndarray, tol: float) -> np.ndarray:
    """Douglas-Peucker on metre coordinates."""
    keep = np.zeros(len(xy), bool)
    keep[0] = keep[-1] = True
    stack = [(0, len(xy) - 1)]
    while stack:
        i, j = stack.pop()
        if j <= i + 1:
            continue
        a, b = xy[i], xy[j]
        ab = b - a
        n = float(np.hypot(*ab)) or 1e-9
        d = np.abs(ab[0] * (xy[i + 1:j, 1] - a[1]) - ab[1] * (xy[i + 1:j, 0] - a[0])) / n
        k = int(np.argmax(d))
        if d[k] > tol:
            keep[i + 1 + k] = True
            stack += [(i, i + 1 + k), (i + 1 + k, j)]
    return xy[keep]


def simplify_ring(xy: np.ndarray, tol: float) -> np.ndarray:
    """A closed ring starts and ends at the same point, which breaks the line test above: split it at the point farthest from the start."""
    k = int(np.argmax(np.hypot(*(xy - xy[0]).T)))
    first, second = simplify(xy[: k + 1], tol), simplify(xy[k:], tol)
    return np.vstack([first, second[1:]])


def inside(poly: np.ndarray, pt: np.ndarray) -> bool:
    x, y, c = pt[0], pt[1], False
    for (x1, y1), (x2, y2) in zip(poly, np.roll(poly, -1, axis=0)):
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            c = not c
    return c


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "x").strip().splitlines()[0])
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--georef", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    g = json.loads(Path(a.georef).read_text(encoding="utf-8"))
    if not g.get("accepted"):
        print("georeference was not accepted; refusing to build")
        return 1
    if g.get("share_within_m", {}).get("30", 0.0) < 1.0:  # the margin below assumes no chart road point is more than ALIGNMENT_BOUND_M from a real road
        print(f"some chart road points are more than {ALIGNMENT_BOUND_M:g} m from a real road; the margin cannot be stated; refusing to build")
        return 1
    pdf = Path(a.pdf)
    if hashlib.sha256(pdf.read_bytes()).hexdigest() != g["pdf_sha256"]:
        print("the PDF is not the one the georeference was fitted to")
        return 1
    page = fitz.open(str(pdf))[PAGE_INDEX]
    paths = [d for d in page.get_drawings()
             if d["type"] == "s" and d.get("color") and all(abs(c - n) < 0.01 for c, n in zip(d["color"], NAVY)) and len(d["items"]) >= MIN_ITEMS]
    if len(paths) != len(LEVELS):
        print(f"expected {len(LEVELS)} contour paths, found {len(paths)}")
        return 1
    s, ox, oy = g["scale_mercator_m_per_pt"], g["x_offset_3857"], g["y_offset_3857"]
    to_ll = Transformer.from_crs(3857, 4326, always_xy=True)
    to_m = Transformer.from_crs(4326, 28356, always_xy=True)
    rings = []
    for d in paths:
        pt = sample_path(d["items"])
        gap = float(np.hypot(*(pt[0] - pt[-1])))
        if gap > 0.5:
            print(f"a contour is not closed (gap {gap:.2f} pt); refusing")
            return 1
        lon, lat = to_ll.transform(ox + s * pt[:, 0], oy - s * pt[:, 1])
        e, n = to_m.transform(lon, lat)
        full = np.c_[e, n]  # full detail, used to check nesting; only the stored copy is simplified
        xy = simplify_ring(full, SIMPLIFY_M)
        lon2, lat2 = Transformer.from_crs(28356, 4326, always_xy=True).transform(xy[:, 0], xy[:, 1])
        rings.append({"bbox_pt": [round(v, 1) for v in d["rect"]], "full": full, "xy": xy,
                      "lonlat": [[round(float(x), 6), round(float(y), 6)] for x, y in zip(lon2, lat2)]})
    rings.sort(key=lambda r: -((r["bbox_pt"][2] - r["bbox_pt"][0]) * (r["bbox_pt"][3] - r["bbox_pt"][1])))  # biggest first = 20
    for outer, inner in zip(rings, rings[1:]):  # every inner line must lie wholly inside the next one out
        if not all(inside(outer["full"], p) for p in inner["full"]):
            print("the contours do not nest as 20 > 25 > 30 > 35; refusing")
            return 1
    ground = g["ground_m_per_pt"]
    half_width = 0.5 * LINE_WIDTH_PT * ground
    margin = math.ceil(half_width + ALIGNMENT_BOUND_M)
    x0, y0, x1, y1 = FRAME_PT
    fl, fb = to_ll.transform(ox + s * x0, oy - s * y1)
    fr, ft = to_ll.transform(ox + s * x1, oy - s * y0)
    doc = {
        "name": "Sydney Airport ANEF 2045 contours",
        "source": {"document": "Sydney Airport Master Plan 2045, Section 5 Appendices, Appendix H, Map H-1 (also Chapter 15 Map 15-1)", "url": SOURCE_URL,
                   "endorsed_by_airservices_australia": ENDORSED, "pdf_sha256": g["pdf_sha256"], "pdf_page": PAGE_INDEX + 1},
        "levels_read_from_labels_on_the_chart": list(LEVELS),
        "frame_lonlat": {"west": round(fl, 6), "south": round(fb, 6), "east": round(fr, 6), "north": round(ft, 6)},
        "accuracy": {"alignment": "chart streets matched to NSW road centrelines", "share_of_chart_road_points_within_m": g["share_within_m"],
                     "chance_share_within_20m_when_shifted": g["chance_share_within_20m_when_shifted"],
                     "half_drawn_line_width_m": round(half_width, 1), "alignment_bound_m": ALIGNMENT_BOUND_M, "margin_m": margin,
                     "note": "A lot closer to a contour than margin_m cannot be placed on one side of it from this chart."},
        "contours": [{"anef": lv, "ring_lonlat": r["lonlat"]} for lv, r in zip(LEVELS, rings)],
    }
    Path(a.out).write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {a.out}: margin {margin} m; points per contour {[len(r['lonlat']) for r in rings]}; bytes {Path(a.out).stat().st_size}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
