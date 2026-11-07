"""Pin the Sydney Airport ANEF 2045 chart (Master Plan 2045, Appendix H, Map H-1) to the ground, and say how well.

prior-art-checked: 2026-11-08. grep of scripts/ services/ data/ for anef: only the old data/anef digitisation (5-point polygons, flags 223 of 400
test lots) and the Western Sydney portal band rule in services/lmr_area_inputs.py exist. This is the only georeference of the endorsed 2045 chart.
Plan: ~/.claude/plans/ce-anef-pdf-trace-FEASIBILITY-2026-11-08.md.

The chart is a vector page with a street map under the contour lines. The streets are matched to NSW road centrelines (NSW_Transport_Theme layer 5)
with a uniform scale and a shift (no rotation; the chart is north-up). The fit is only accepted when most chart road points land within a few metres
of a real road AND a deliberately wrong shift scores far worse (the chance level). Earlier controls (runway icons, dashed council lines) failed that.

    python scripts/anef/georef_chart_to_roads.py --pdf <Appendices.pdf> --out data/anef/sydney_anef_2045_georef.json
Slow once (about 2 minutes: 31,000 road segments are fetched); the result file is committed, so nothing else needs this.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np
from pyproj import Transformer
from scipy.spatial import cKDTree

PAGE_INDEX = 24  # PDF page 25: Map H-1 "ANEF 2045"
ROADS_URL = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Transport_Theme/FeatureServer/5/query"
ROAD_BOX = "151.03,-34.08,151.25,-33.80"  # lon/lat box over the WHOLE chart map (the 20 line reaches lat -34.06 to -33.84), not just the airport
ROAD_GREYS = {1.01, 1.44}  # stroke widths of the chart's road lines (colour 0.74 grey)
CENTRE_PT = (285.0, 526.0)  # chart point near the middle of the airport; only the search starts here
FRAME_PT = (0.0, 195.0, 420.0, 830.0)  # the map frame on the page, in points (x0, y0, x1, y1); every chart road point inside it is used
CONTOUR_BBOX_PT = {"20": (136.0, 251.0, 405.0, 821.0), "25": (189.0, 339.0, 363.0, 706.0)}  # where the 20 and 25 lines lie on the page; accuracy is reported there


def _get(params: dict) -> dict:
    last: Exception | None = None
    for _ in range(3):
        try:
            req = urllib.request.Request(ROADS_URL + "?" + urllib.parse.urlencode(params), headers={"User-Agent": "ComplianceEngine/1.0"})
            return json.load(urllib.request.urlopen(req, timeout=120))
        except Exception as exc:  # noqa: BLE001 -- retried, then raised
            last = exc
            time.sleep(2)
    raise RuntimeError(f"road layer did not answer: {last}")


def fetch_roads() -> np.ndarray:
    base = {"where": "1=1", "geometry": ROAD_BOX, "geometryType": "esriGeometryEnvelope", "inSR": 4326, "outSR": 3857,
            "spatialRel": "esriSpatialRelIntersects", "outFields": "objectid", "returnGeometry": "true", "maxAllowableOffset": 5, "f": "json"}
    out, off = [], 0
    while True:
        feats = _get({**base, "resultOffset": off, "resultRecordCount": 2000}).get("features") or []
        for f in feats:
            for path in f["geometry"]["paths"]:
                r = np.array(path)
                for a, b in zip(r[:-1], r[1:]):
                    k = max(2, int(np.hypot(*(b - a)) / 10))
                    out.append(a + (b - a) * np.linspace(0, 1, k)[:, None])
        print(f"roads fetched {off + len(feats)}", flush=True)
        if not feats:  # only an EMPTY page ends the download: a server may cap a page below the 2,000 asked for and say exceededTransferLimit
            return np.vstack(out)
        off += len(feats)


def chart_road_points(pdf: Path) -> np.ndarray:
    page = fitz.open(str(pdf))[PAGE_INDEX]
    pts = []
    for d in page.get_drawings():
        col = tuple(round(v, 2) for v in (d.get("color") or ()))
        if d["type"] == "s" and col == (0.74, 0.74, 0.74) and round(d.get("width") or 0, 2) in ROAD_GREYS:
            for it in d["items"]:
                if it[0] == "l":
                    a, b = np.array([it[1].x, it[1].y]), np.array([it[2].x, it[2].y])
                    pts.append(a + (b - a) * np.linspace(0, 1, max(2, int(np.hypot(*(b - a)) / 2.5)))[:, None])
    c = np.vstack(pts)
    x0, y0, x1, y1 = FRAME_PT
    return c[(c[:, 0] >= x0) & (c[:, 0] <= x1) & (c[:, 1] >= y0) & (c[:, 1] <= y1)]


def fit(chart: np.ndarray, real: np.ndarray) -> dict:
    tree = cKDTree(real)
    sub = chart[np.random.default_rng(1).choice(len(chart), min(3000, len(chart)), replace=False)]
    x0, y0 = Transformer.from_crs(28356, 3857, always_xy=True).transform(331452.0, 6242242.5)  # middle of runway 16R/34L (published ends)

    def share(s: float, ox: float, oy: float, pts: np.ndarray = sub, thr: float = 15) -> float:
        d, _ = tree.query(np.c_[ox + s * pts[:, 0], oy - s * pts[:, 1]])
        return float((d < thr).mean())

    best = (0.0, (0.0, 0.0, 0.0))
    for s in np.arange(43.0, 53.01, 0.5):
        ox, oy = x0 - s * CENTRE_PT[0], y0 + s * CENTRE_PT[1]
        for dx in range(-3000, 3001, 150):
            for dy in range(-3000, 3001, 150):
                v = share(s, ox + dx, oy + dy)
                if v > best[0]:
                    best = (v, (float(s), ox + dx, oy + dy))
    s, ox, oy = best[1]
    for step, span, ds in ((40, 200, 0.3), (10, 50, 0.1), (3, 15, 0.03)):
        for ss in np.arange(s - 3 * ds, s + 3 * ds + 1e-9, ds):
            for dx in range(-span, span + 1, step):
                for dy in range(-span, span + 1, step):
                    v = share(float(ss), ox + dx, oy + dy)
                    if v > best[0]:
                        best = (v, (float(ss), ox + dx, oy + dy))
        s, ox, oy = best[1]
    for _ in range(20):  # trimmed least squares on every chart road point near a road: the grid above fixes the peak, this removes its scale bias
        d, idx = tree.query(np.c_[ox + s * chart[:, 0], oy - s * chart[:, 1]])
        keep = d < 25
        c, r = chart[keep], real[idx[keep]]
        A = np.zeros((2 * len(c), 3))
        b = np.zeros(2 * len(c))
        A[0::2] = np.c_[c[:, 0], np.ones(len(c)), np.zeros(len(c))]
        b[0::2] = r[:, 0]
        A[1::2] = np.c_[-c[:, 1], np.zeros(len(c)), np.ones(len(c))]
        b[1::2] = r[:, 1]
        s, ox, oy = (float(v) for v in np.linalg.lstsq(A, b, rcond=None)[0])
    d, _ = tree.query(np.c_[ox + s * chart[:, 0], oy - s * chart[:, 1]])
    chance = []
    for dx, dy in ((500, 300), (-700, 400), (300, -800)):
        d2, _ = tree.query(np.c_[ox + dx + s * chart[:, 0], oy + dy - s * chart[:, 1]])
        chance.append(float((d2 < 20).mean()))
    lat_factor = math.cos(math.radians(33.93))
    regions = {}  # accuracy where the lines actually lie, not just where the fit was easiest
    for name, (bx0, by0, bx1, by1) in CONTOUR_BBOX_PT.items():
        m = (chart[:, 0] >= bx0) & (chart[:, 0] <= bx1) & (chart[:, 1] >= by0) & (chart[:, 1] <= by1)
        dm = d[m]
        regions[name] = {"chart_road_points": int(m.sum()), "share_within_m": {str(t): float((dm < t).mean()) for t in (10, 20, 30, 40, 50)},
                         "max_distance_m_of_points_matched_within_100m": float(dm[dm < 100].max()), "share_matched_within_100m": float((dm < 100).mean())}
    return {"scale_mercator_m_per_pt": s, "x_offset_3857": ox, "y_offset_3857": oy, "ground_m_per_pt": s * lat_factor,
            "chart_road_points": int(len(chart)), "real_road_samples": int(len(real)),
            "share_within_m": {str(t): float((d < t).mean()) for t in (5, 10, 15, 20, 30)},
            "chance_share_within_20m_when_shifted": chance, "region_accuracy": regions}


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=(__doc__ or "x").strip().splitlines()[0])
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    pdf = Path(a.pdf)
    result = fit(chart_road_points(pdf), fetch_roads())
    result["page_index"] = PAGE_INDEX
    result["pdf_sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
    result["roads_source"] = "NSW_Transport_Theme layer 5 RoadSegment (portal.spatial.nsw.gov.au)"
    ok = result["share_within_m"]["20"] >= 0.95 and max(result["chance_share_within_20m_when_shifted"]) <= 0.5
    result["accepted"] = ok
    Path(a.out).write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
