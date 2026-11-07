"""Scratchpad: for stations with NO mapped entrance, add the station footprint (building / platform outlines from OpenStreetMap).
The public entrance must be on or next to this footprint, so a walk to its nearest edge can only be too SHORT, by at most the
footprint's longest dimension (span_m). One Overpass request for all of them. Reads lmr_station_entrances_merged.json,
writes lmr_station_entrances_final.json."""
# prior-art-checked: 2026-11-07. A grep of scripts/ and services/ for station entrance, walking surface, valhalla and gtfs finds no
# existing builder or test of this data; this script is part of the low-and-mid-rise area-check data pipeline
# (see ~/.claude/plans/ce-NEXT-PROMPT-2026-11-07b-lmr-area-check-build.md). Working files go to data/lmr_area_work/ (not committed).
import json
import math
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import MultiPoint, Point, Polygon
from shapely.ops import transform, unary_union

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__import__("os").environ.get("LMR_WORK", REPO / "data" / "lmr_area_work"))  # working folder, not committed
HERE.mkdir(parents=True, exist_ok=True)
UA = {"User-Agent": "plotdetect-lmr-stations/1.0"}
RAD = 250
doc = json.loads((HERE / "lmr_station_entrances_merged.json").read_text(encoding="utf-8"))
todo = [s for s in doc["stations"] if not s["entrances"]]
print("stations without an entrance:", len(todo), flush=True)
around = "".join(
    f'way["building"="train_station"](around:{RAD},{s["lat"]},{s["lon"]});way["railway"="platform"](around:{RAD},{s["lat"]},{s["lon"]});'
    f'way["public_transport"~"platform|station"](around:{RAD},{s["lat"]},{s["lon"]});way["railway"="station"](around:{RAD},{s["lat"]},{s["lon"]});'
    for s in todo)
q = f"[out:json][timeout:240];({around});out geom;"
els = None
for i in range(5):
    try:
        r = urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(), headers=UA)
        els = json.load(urllib.request.urlopen(r, timeout=300))["elements"]
        break
    except Exception as e:
        print("retry", i, str(e)[:80], flush=True)
        time.sleep(10 * (i + 1))
if els is None:
    sys.exit("overpass failed")
print("ways returned:", len(els), flush=True)
polys = []
for w in els:
    g = w.get("geometry") or []
    if len(g) >= 3:
        pts = [(p["lon"], p["lat"]) for p in g]
        if pts[0] != pts[-1]:
            pts.append(pts[0])
        polys.append((w["id"], w.get("tags", {}), pts))
res = {}
for s in todo:
    to_m = Transformer.from_crs(4326, 28300 + int((s["lon"] + 180) // 6) + 1, always_xy=True).transform
    c = Point(*to_m(s["lon"], s["lat"]))
    near = []
    for wid, tags, pts in polys:
        pg = transform(to_m, Polygon(pts).buffer(0))
        if not pg.is_empty and pg.distance(c) <= 120:  # outlines that touch the station point's surroundings
            near.append(pg)
    if not near:
        res[s["name"]] = None
        continue
    hull = unary_union(near).convex_hull
    xs = list(hull.exterior.coords) if hull.geom_type == "Polygon" else []
    span = max((math.hypot(a[0] - b[0], a[1] - b[1]) for a in xs for b in xs), default=0.0)
    back = Transformer.from_crs(to_m.__self__.target_crs if hasattr(to_m, "__self__") else 4326, 4326, always_xy=True)
    s["footprint"] = {"outlines_used": len(near), "span_m": round(span),
                      "hull_lonlat": [list(Transformer.from_crs(28300 + int((s["lon"] + 180) // 6) + 1, 4326, always_xy=True).transform(x, y)) for x, y in xs]}
    res[s["name"]] = round(span)
doc["footprint_note"] = ("Stations with no mapped entrance carry an OSM building/platform footprint hull. The entrance lies on or near it, "
                         "so a walk to its nearest edge is too short by at most span_m.")
(HERE / "lmr_station_entrances_final.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
have = {k: v for k, v in res.items() if v is not None}
print("footprint found for", len(have), "of", len(todo), "| spans (m):", sorted(have.values()))
print("no footprint (will keep the doubled margin):", [k for k, v in res.items() if v is None])
