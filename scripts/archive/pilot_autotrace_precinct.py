"""Route-3 auto-trace PILOT — does auto-vectorising a DCP figure beat manual QGIS?

prior-art-checked: no existing auto-trace/vectorise pilot. Route-3 precedent scripts
(import_krg_local_centre_boundaries.py) only IMPORT a hand-digitised .gpkg; this is the
first attempt to DERIVE the polygon from the georeferenced figure. Reuses cv2/rasterio/
shapely/geopandas already in venv_linux. Design per ce-dcp-figure-geocoding-automation-2026-07 §7.

Method: take the ALREADY-georeferenced .tif (isolates the vectorise step from georeferencing)
-> HSV red mask (Marrickville draws precincts as a RED DASHED line) -> morphological close to
bridge dashes -> largest closed contour -> map pixel->geo via the raster transform -> polygon in
the raster CRS -> IoU vs the hand-traced truth polygon. One number decides if Route-3 is worth building.

Usage: python scripts/pilot_autotrace_precinct.py
"""
from __future__ import annotations
import os
import numpy as np
import cv2
import rasterio
from rasterio.transform import xy as rc_to_xy
import geopandas as gpd
from shapely.geometry import Polygon
from shapely.validation import make_valid

BASE = "archive/2026-01-pipeline-outputs/output"
TIF = f"{BASE}/high_res_maps/original 20 text boundaries/precinct_10_map_300dpi_modified.tif"
GPKG = f"{BASE}/gpkg for boundary mapping/precint_boudaries.gpkg"
TARGET_PRECINCT = 10


def load_georef_rgb(path: str):
    with rasterio.open(path) as src:
        print(f"  raster: {src.width}x{src.height}  crs={src.crs}  bands={src.count}")
        bands = [src.read(i) for i in range(1, min(src.count, 3) + 1)]
        rgb = np.dstack(bands[:3]) if len(bands) >= 3 else np.dstack([bands[0]] * 3)
        return rgb.astype(np.uint8), src.transform, src.crs


def red_mask(rgb: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(rgb, cv2.COLOR_RGB2HSV)
    # red wraps hue 0 and 180; require decent saturation+value to skip grey basemap
    m1 = cv2.inRange(hsv, (0, 70, 60), (12, 255, 255))
    m2 = cv2.inRange(hsv, (168, 70, 60), (180, 255, 255))
    return cv2.bitwise_or(m1, m2)


def topk_closed_contours(mask: np.ndarray, close_px: int, k_top: int = 8):
    """Return the top-K contours by area (not just the largest) so we can test whether
    the RIGHT precinct loop exists among them, not only whether #1 happens to be it."""
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (close_px, close_px))
    closed = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k)  # bridge dashes
    cnts, _ = cv2.findContours(closed, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = sorted(cnts, key=cv2.contourArea, reverse=True)[:k_top]
    return cnts


def contour_to_geo_polygon(contour, transform) -> Polygon | None:
    pts = contour.reshape(-1, 2)  # (col,row)
    if len(pts) < 4:
        return None
    xs, ys = rc_to_xy(transform, pts[:, 1].tolist(), pts[:, 0].tolist())  # rows, cols -> x,y
    poly = Polygon(zip(xs, ys))
    return make_valid(poly) if not poly.is_valid else poly


def load_truth():
    gdf = gpd.read_file(GPKG, engine="pyogrio")
    idcol = next((c for c in ("precinct_id", "precinct", "id") if c in gdf.columns), None)
    print(f"  truth gpkg: {len(gdf)} rows, crs={gdf.crs}, id-col={idcol}")
    sub = gdf[gdf[idcol].astype(str).str.strip() == str(TARGET_PRECINCT)]
    if sub.empty:  # some ids look like "10 Dulwich Hill North"
        sub = gdf[gdf[idcol].astype(str).str.strip().str.startswith(str(TARGET_PRECINCT))]
    return sub


def iou(a: Polygon, b: Polygon) -> float:
    inter = a.intersection(b).area
    union = a.union(b).area
    return inter / union if union else 0.0


def main():
    for p in (TIF, GPKG):
        if not os.path.exists(p):
            raise SystemExit(f"missing asset: {p}")
    print("=== Route-3 auto-trace pilot: Marrickville Precinct 10 (Dulwich Hill North) ===\n")
    print("[1] load georeferenced raster")
    rgb, transform, crs = load_georef_rgb(TIF)
    print("\n[2] red-dash mask")
    mask = red_mask(rgb)
    print(f"  red pixels: {int((mask > 0).sum()):,} ({100*(mask>0).mean():.3f}% of image)")

    print("\n[3] load truth polygon")
    truth = load_truth()
    if truth.empty:
        raise SystemExit("truth precinct 10 not found in gpkg")
    truth_geom = make_valid(truth.geometry.union_all())
    truth_crs = truth.crs

    print("\n[4] close dashes -> score TOP-8 contours per kernel (does the right loop exist at all?)")
    best = None
    for close_px in (15, 25, 41, 61):
        cnts = topk_closed_contours(mask, close_px)
        scores = []
        for contour in cnts:
            poly = contour_to_geo_polygon(contour, transform)
            if poly is None or poly.is_empty:
                continue
            pred = gpd.GeoSeries([poly], crs=crs).to_crs(truth_crs).iloc[0]
            s = iou(pred, truth_geom)
            scores.append(s)
            if best is None or s > best[0]:
                best = (s, close_px, pred)
        top = max(scores) if scores else 0.0
        print(f"  close={close_px:>3}px: {len(cnts)} contours, best-of-top-8 IoU={top:.3f}"
              f"  (all: {', '.join(f'{s:.2f}' for s in scores)})")

    print("\n[5] RESULT")
    if best:
        score, close_px, pred = best
        print(f"  best IoU = {score:.3f}  (close kernel {close_px}px)")
        print(f"  pred area / truth area = {pred.area:.3e} / {truth_geom.area:.3e}")
        # --- diagnostic: is IoU=0 a location bug or a shape failure? ---
        tc, pc = truth_geom.centroid, pred.centroid
        print(f"  truth centroid: ({tc.x:.5f}, {tc.y:.5f})  bounds={tuple(round(b,4) for b in truth_geom.bounds)}")
        print(f"  pred  centroid: ({pc.x:.5f}, {pc.y:.5f})  bounds={tuple(round(b,4) for b in pred.bounds)}")
        print(f"  centroid offset: {tc.distance(pc)*111000:.0f} m ; polygons intersect? {pred.intersects(truth_geom)}")
        verdict = ("STRONG - auto-trace viable, build Route-3" if score >= 0.85 else
                   "PARTIAL - needs cleanup/tuning, marginal vs manual" if score >= 0.6 else
                   "WEAK - manual/GIPA stays cheaper for now")
        print(f"  VERDICT: {verdict}")
    else:
        print("  no polygon recovered -> WEAK (manual stays cheaper)")


if __name__ == "__main__":
    main()
