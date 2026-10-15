#!/usr/bin/env python3
"""Outlines for centres a DCP draws only as a RASTER street map, fitted to NSW road centrelines.

prior-art-checked: build_cb_centre_boundaries.py fits a VECTOR figure's lot lines to the cadastre
(it cannot read pixels); site_figure_check.py only SCORES an outline already built. This places a
raster Land Application Map on the ground, then reuses build_cb's cadastre fetch and lot snap.

WHY (address audit 2026-10-15): C-B DCP 2023 Chapter 7.2's 339 served rules sit in the precinct
layer with no key -- the route now shows them to no house. Each Section N "applies to land shown in
Figure Na", a raster basemap (white roads on grey, the land drawn as a thin dark line). No state
layer holds these centres, and their zoning is NOT their land (IoU 0.09-0.30 on 6.2/7.5/7.6).

METHOD (deterministic; a person or model only READS street labels into the data file)
  1 roads     NSW Transport Theme RoadSegment centrelines in a box round a seed (suburb or first
              named street's address points), every 2 m.
  2 fit       north-up scale + shift: for each scale, FFT cross-correlation of the centreline points
              with the map's road pixels; score = share on road ABOVE the road share of the map.
              seed 'street' fits on the named streets only (zoomed maps have too few streets for
              the whole network to be unique).
  3 outline   every closed dark line on the map (labels dropped by size, the north arrow by place).
  4 lots      build_cb_centre_boundaries.lots_inside: >= 80% in, 20-80% kept (doubt keeps the rule).
ACCEPTANCE (all three, else the centre is REFUSED and not written)
  named streets' centreline points on map road pixels >= 0.90   (the labels the map itself prints)
  whole road network on road pixels                   >= 0.55
  outline vertices to nearest cadastre lot edge, median <= 5 m   (the land is drawn on lot lines)
Learned on the first run: a high score alone accepted 4 wrong fits on zoomed maps; every result
is also drawn (--draw) and looked at before any write.

Usage:
    python scripts/fit_cb_raster_centres.py                 # fit, prove, write the geojson + report
    python scripts/fit_cb_raster_centres.py --only 6,7 --draw
Load with: python scripts/import_cb_centre_boundaries.py --src data/canterbury_bankstown_precincts/centres_7_2.geojson
"""
from __future__ import annotations

import argparse
import io
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

import cv2
import fitz  # PyMuPDF
import numpy as np
from PIL import Image
from scipy.signal import fftconvolve
from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_cb_centre_boundaries as cb  # noqa: E402  (fetch_pdf, fetch_cadastre, lots_inside, feature)

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "data" / "canterbury_bankstown_precincts"
ROADS = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Transport_Theme/FeatureServer/5/query"
ADDR = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Geocoded_Addressing_Theme/MapServer/1/query"
TYPES = {"St": "STREET", "Rd": "ROAD", "Ave": "AVENUE", "Cres": "CRESCENT", "Dr": "DRIVE", "Parade": "PARADE",
         "Cl": "CLOSE", "Pl": "PLACE", "Hwy": "HIGHWAY", "Cct": "CIRCUIT", "Ln": "LANE"}
NAMED_MIN, ALL_MIN, LOT_EDGE_MAX = 0.90, 0.55, 5.0
OUTSIDE_MAX_M2 = 1500  # a doubtful lot sticking out further than this is a corridor, not a centre lot
METHOD = "dcp_raster_map_fitted_to_road_centrelines"


def _get(url: str, params: dict, tries: int = 4) -> dict:
    import time
    for i in range(tries):
        try:
            with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=90) as r:
                return json.load(r)
        except (TimeoutError, OSError):
            if i == tries - 1:
                raise
            time.sleep(5 * (i + 1))


def figure_image(pdf: Path, page: int) -> np.ndarray:
    """The largest image on the page, greyscale."""
    d = fitz.open(pdf)
    p = d[page - 1]
    xref = max(p.get_images(full=True), key=lambda im: d.extract_image(im[0])["width"] * d.extract_image(im[0])["height"])[0]
    return np.asarray(Image.open(io.BytesIO(d.extract_image(xref)["image"])).convert("L"))


def _street(name: str) -> tuple[str, str]:
    """'Haig Ave' -> ('HAIG', 'AVENUE')."""
    *base, t = name.split()
    return " ".join(base).upper(), TYPES.get(t, t.upper())


def seed(c: dict) -> tuple[float, float]:
    """Median address point of the suburb, or of the first named street in it (MGA56)."""
    if c["seed"] == "street":
        b, t = _street(c["streets"][0])
        where = f"address LIKE '% {b} {t} {c['suburb']}%'"
    else:
        where = f"address LIKE '% {c['suburb']} %' OR address LIKE '% {c['suburb']}'"
    fs = _get(ADDR, {"where": where, "outFields": "address", "returnGeometry": "true", "outSR": "28356",
                     "f": "json", "resultRecordCount": 1000}).get("features", [])
    if not fs:
        raise SystemExit(f"[ABORT] no address points for seed {where!r}")
    pts = np.array([[f["geometry"]["x"], f["geometry"]["y"]] for f in fs])
    return tuple(np.median(pts, 0))


def fetch_roads(cx: float, cy: float, half: float) -> tuple[np.ndarray, np.ndarray]:
    """Centreline points every 2 m in the box, ONE request, and each point's 'BASE|TYPE' street key."""
    fs, offset = [], 0
    while True:  # the service caps a page at 2,000 segments; a cut-off page silently drops named streets
        page = _get(ROADS, {"geometry": f"{cx-half},{cy-half},{cx+half},{cy+half}", "geometryType": "esriGeometryEnvelope",
                            "inSR": "28356", "spatialRel": "esriSpatialRelIntersects", "outFields": "roadnamebase,roadnametype",
                            "returnGeometry": "true", "outSR": "28356", "f": "json", "orderByFields": "objectid",
                            "resultOffset": offset, "resultRecordCount": 2000})
        fs += page.get("features", [])
        if not page.get("exceededTransferLimit") or not page.get("features"):
            break
        offset += len(page["features"])
    out, keys = [], []
    for f in fs:
        a = f["attributes"]
        key = (a.get("roadnamebase") or "").upper() + "|" + (a.get("roadnametype") or "").upper()
        for path in f["geometry"]["paths"]:
            p = np.array(path)
            for p0, p1 in zip(p[:-1], p[1:]):
                n = max(1, int(np.hypot(*(p1 - p0)) / 2))
                out.append(p0 + (p1 - p0) * np.linspace(0, 1, n, endpoint=False)[:, None])
                keys += [key] * n
    return (np.vstack(out) if out else np.zeros((0, 2))), np.array(keys)


def named(pts: np.ndarray, keys: np.ndarray, names: list[str]) -> tuple[np.ndarray, set]:
    """The named streets' points, and the names the state layer does not hold here."""
    want = {"|".join(_street(n)) for n in names}
    m = np.isin(keys, list(want))
    return pts[m], {w.replace("|", " ") for w in want - set(keys[m])}


def _road_mask(img: np.ndarray) -> np.ndarray:
    """Map road pixels (white), widened 2 px so a centreline inside a carriageway counts."""
    return cv2.dilate((img >= 249).astype(np.uint8), np.ones((5, 5), np.uint8))


def search(img: np.ndarray, pts: np.ndarray, cx: float, cy: float, scales, down: int = 1,
           near: tuple | None = None) -> tuple[float, float, float, float]:
    """Best (lift, metres/pixel, x of pixel (0,0), y of pixel (0,0)) over the scales, north up.
    down: search the map shrunk this many times (coarse pass, ~down^2 faster). near=(ox, oy, margin_m):
    keep only points near that placement (fine pass) so the correlation grid stays small."""
    road = _road_mask(img).astype(np.float32)
    if down > 1:
        road = cv2.resize(road, (road.shape[1] // down, road.shape[0] // down), interpolation=cv2.INTER_AREA)
        road = (road > 0.25).astype(np.float32)
    base = road.mean()
    H, W = road.shape
    if near is not None:
        ox, oy, mg = near
        ext = max(img.shape) * max(scales)
        k = (pts[:, 0] > ox - mg) & (pts[:, 0] < ox + ext + mg) & (pts[:, 1] < oy + mg) & (pts[:, 1] > oy - ext - mg)
        pts = pts[k]
    best = (-1.0, 0.0, 0.0, 0.0)
    for s0 in scales:
        s = s0 * down
        u = (pts[:, 0] - cx) / s
        v = -(pts[:, 1] - cy) / s
        keep = (np.abs(u) < 2 * W) & (np.abs(v) < 2 * H)
        u, v = u[keep], v[keep]
        if not len(u):
            continue
        gu, gv = int(u.min()), int(v.min())
        G = np.zeros((int(v.max()) - gv + 1, int(u.max()) - gu + 1), np.float32)
        if G.shape[0] < H or G.shape[1] < W:
            continue  # the fetched box is smaller than the map at this scale
        np.add.at(G, ((v - gv).astype(int), (u - gu).astype(int)), 1.0)
        C = fftconvolve(G, road[::-1, ::-1], mode="valid")
        N = fftconvolve(G, np.ones_like(road), mode="valid")  # points inside the map window
        lift = np.where(N > 0.5 * N.max(), C / np.maximum(N, 1) - base, -1)
        iy, ix = np.unravel_index(np.argmax(lift), lift.shape)
        if lift[iy, ix] > best[0]:
            best = (float(lift[iy, ix]), float(s0), float(cx + (ix + gu) * s), float(cy - (iy + gv) * s))
    return best


def on_road_share(img: np.ndarray, fit: dict, pts: np.ndarray) -> float:
    """Share of the centreline points inside the map that land on its road pixels."""
    road = _road_mask(img)
    u = ((pts[:, 0] - fit["ox"]) / fit["s"]).astype(int)
    v = (-(pts[:, 1] - fit["oy"]) / fit["s"]).astype(int)
    k = (u >= 0) & (u < img.shape[1]) & (v >= 0) & (v < img.shape[0])
    return float(road[v[k], u[k]].mean()) if k.sum() else 0.0


def outline(img: np.ndarray, fit: dict, min_px2: float = 1500):
    """Every closed dark line (a map may draw several parts): the holes of the dark mask after
    labels (short components) are dropped; the north arrow (bottom-right corner) is not land."""
    dark = (img < 160).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(dark, connectivity=8)
    keep = np.zeros_like(dark)
    for i in range(1, n):
        if np.hypot(stats[i, 2], stats[i, 3]) >= 80:
            keep[lab == i] = 255
    keep = cv2.dilate(keep, np.ones((3, 3), np.uint8))
    cs, hier = cv2.findContours(keep, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
    polys = []
    for c, h in zip(cs, hier[0] if hier is not None else []):
        x, y, _, _ = cv2.boundingRect(c)
        if x > 0.85 * img.shape[1] and y > 0.85 * img.shape[0]:
            continue
        if h[3] >= 0 and cv2.contourArea(c) >= min_px2:
            r = c[:, 0, :].astype(float)
            polys.append(Polygon(np.c_[fit["ox"] + r[:, 0] * fit["s"], fit["oy"] - r[:, 1] * fit["s"]]).buffer(0))
    return unary_union(polys) if polys else None


def fit_centre(pdf: Path, c: dict) -> dict:
    """Fit, measure and snap one centre. Returns the report row (with 'lots_geom' when accepted)."""
    img = figure_image(pdf, c["page"])
    sx, sy = seed(c)
    pts, keys = fetch_roads(sx, sy, 2000)                      # the only road request for this centre
    nm, missing = named(pts, keys, c["streets"])
    fit_pts = nm if c["seed"] == "street" else pts
    lo = 0.15 if c["seed"] == "street" else 0.4
    # Zoomed maps (street seed) lose small streets at 1/4 size and some fit better at 1/2: try both, keep the
    # placement whose WHOLE road network sits best on the map (the named streets are checked again below).
    best = None
    for down in ((2, 4) if c["seed"] == "street" else (4,)):
        coarse = search(img, fit_pts, sx, sy, np.geomspace(lo, 2.5, 40), down=down)
        cand = search(img, fit_pts, sx, sy, np.linspace(coarse[1] * 0.96, coarse[1] * 1.04, 9),
                      near=(coarse[2], coarse[3], 150))
        f = {"s": cand[1], "ox": cand[2], "oy": cand[3]}
        score = (on_road_share(img, f, nm) >= NAMED_MIN, on_road_share(img, f, pts)) if cand[1] > 0 else (False, -1)
        if best is None or score > best[0]:
            best = (score, cand)
    lift, s, ox, oy = best[1]
    fit = {"s": s, "ox": ox, "oy": oy}
    row = {"section": c["section"], "name": c["name"], "lift": round(lift, 3), "m_per_px": round(s, 4),
           "origin_mga": [round(ox, 1), round(oy, 1)], "seed": c["seed"],
           "named_on_road": round(on_road_share(img, fit, nm), 3),
           "all_on_road": round(on_road_share(img, fit, pts), 3),
           "names_not_in_nsw_roads": sorted(missing), "_pts": pts}
    if s <= 0 or lift <= 0 or np.hypot(ox - sx, oy - sy) > 5000:
        row["refused"] = "no placement found near the seed"
        return row
    poly = outline(img, fit)
    if poly is None:
        row["refused"] = "no closed outline on the map"
        return row
    x0, y0, x1, y1 = poly.bounds
    cad = cb.fetch_cadastre((x0 - 50, y0 - 50, x1 + 50, y1 + 50))
    edges = unary_union([g.boundary for _, g in cad])
    parts = list(getattr(poly, "geoms", [poly]))
    dist = [Point(p).distance(edges) for g in parts for p in list(g.exterior.coords)[::5]]
    row.update(parts=len(parts), outline_m2=round(poly.area), lot_edge_median_m=round(float(np.median(dist)), 2),
               lot_edge_p90_m=round(float(np.percentile(dist, 90)), 2))
    fails = [f for f, bad in (("named streets off the map's roads", row["named_on_road"] < NAMED_MIN),
                              ("road network off the map's roads", row["all_on_road"] < ALL_MIN),
                              ("outline not on lot lines", row["lot_edge_median_m"] > LOT_EDGE_MAX)) if bad]
    if fails:
        row["refused"] = "; ".join(fails)
        return row
    lots, uncertain = [], []
    for g in parts:
        segs = list(zip(list(g.exterior.coords)[:-1], list(g.exterior.coords)[1:]))
        _, ins, unc = cb.lots_inside(segs, cad)
        lots += [x for _, x in ins]
        # A doubtful lot is kept only if little of it lies OUTSIDE the line: rail and road corridor lots
        # run for hundreds of metres past a centre and would stretch the outline along them.
        uncertain += [x for _, x, _ in unc if x.difference(g).area <= OUTSIDE_MAX_M2]
    row.update(lots_in=len(lots), lots_uncertain_kept=len(uncertain))
    # Close hairline gaps between neighbouring lots and drop specks: a sliver can take the outline's
    # inner point, which then rounds outside it (the importer's lookup proof refused 6 outlines on that).
    merged = unary_union(lots + uncertain).buffer(0.3).buffer(-0.3)
    row["lots_geom"] = unary_union([q for q in getattr(merged, "geoms", [merged]) if q.area >= 50])
    return row


def draw(pdf: Path, c: dict, row: dict, path: Path) -> None:
    """The map with NSW roads (red) and the snapped lots (blue) for a person to look at."""
    img = figure_image(pdf, c["page"])
    s, (ox, oy) = row["m_per_px"], row["origin_mga"]
    o = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    pts = row["_pts"]
    u = ((pts[:, 0] - ox) / s).astype(int)
    v = (-(pts[:, 1] - oy) / s).astype(int)
    k = (u >= 0) & (u < img.shape[1]) & (v >= 0) & (v < img.shape[0])
    o[v[k], u[k]] = (0, 0, 255)
    for g in getattr(row.get("lots_geom"), "geoms", [row.get("lots_geom")] if row.get("lots_geom") else []):
        cc = np.array(g.exterior.coords)
        cv2.polylines(o, [np.c_[(cc[:, 0] - ox) / s, -(cc[:, 1] - oy) / s].astype(np.int32)], True, (255, 120, 0), 3)
    cv2.imwrite(str(path), cv2.resize(o, None, fx=0.5, fy=0.5))


def _one(args):
    """One centre in a worker process: fit, draw if asked, drop the road points before returning."""
    pdf, c, do_draw, path = args
    row = fit_centre(pdf, c)
    if do_draw:
        draw(pdf, c, row, path)
    row.pop("_pts", None)
    return row


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", default=str(OUT / "raster_centres_7_2.json"))
    ap.add_argument("--only", default="", help="comma-separated section numbers")
    ap.add_argument("--draw", action="store_true", help="write a picture per centre beside the report")
    a = ap.parse_args()
    cfg = json.loads(Path(a.config).read_text(encoding="utf-8"))
    only = {int(x) for x in a.only.split(",") if x}
    cache = OUT / ".pdf_cache"
    cache.mkdir(parents=True, exist_ok=True)
    pdf = cb.fetch_pdf(cfg["pdf"], cache)
    stem = Path(a.config).stem.replace("raster_centres_", "")
    feats, report = [], []
    todo = [c for c in cfg["centres"] if not only or c["section"] in only]
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=min(3, len(todo))) as ex:   # centres in parallel
        rows = list(ex.map(_one, [(pdf, c, a.draw, OUT / f"check_{stem}_{c['section']}.png") for c in todo]))
    for c, row in zip(todo, rows):
        geom = row.pop("lots_geom", None)
        report.append(row)
        print(json.dumps(row), flush=True)
        if geom is not None:
            pid = f"{cfg['union_id']}.{c['section']}"
            feats.append(cb.feature(pid, c["name"], geom, {
                "method": METHOD, "source": f"{cfg['pdf']} p{c['page']} Figure {c['section']}a Land Application Map",
                "quote": f"Section {c['section']} applies to land shown in Figure {c['section']}a.", "proof": row}))
    refused = [r for r in report if "refused" in r]
    if not only and feats:  # the union covers the ACCEPTED centres; a refused one stays unkeyed (shown to nobody)
        union = unary_union([cb.shape(f["geometry"]) for f in feats])
        from pyproj import Transformer
        from shapely.ops import transform as stx
        feats.append(cb.feature(cfg["union_id"], cfg["union_name"],
                                stx(Transformer.from_crs(4326, 28356, always_xy=True).transform, union), {
            "method": METHOD, "source": f"union of {len(feats)} {cfg['pdf']} centre outlines",
            "quote": "Section 1 and Appendix 1 apply to the centres of this chapter.", "proof": {"members": len(feats)}}))
    (OUT / f"centres_{stem}.geojson").write_text(json.dumps({"type": "FeatureCollection", "features": feats}, indent=1),
                                                 encoding="utf-8")
    (OUT / f"fit_report_{stem}.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    print(f"accepted {len(report) - len(refused)} / {len(report)}; refused: {[r['section'] for r in refused]}")
    return 1 if refused else 0


if __name__ == "__main__":
    sys.exit(main())
