"""Scratchpad: can OpenStreetMap features predict where a station's public entrances are? Test on stations whose real entrances we KNOW.
Heuristic H (stated for the user to judge): a point is a likely entrance if it is an entrance=yes/main node, an Opal card reader
(amenity=ticket_validator) or a lift (highway=elevator) AND lies within NEAR_M of the station building/platform outline.
Truth = entrances already in our file (OpenStreetMap railway=subway_entrance + TfNSW GTFS Pathways) for the 36 stations that have them.
Prints: how many real entrances H finds within 40 m (recall), how many of H's points are near a real entrance (precision)."""
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
UA = {"User-Agent": "plotdetect-lmr-probe/1.0"}
NEAR_M = int(sys.argv[1]) if len(sys.argv) > 1 else 40
doc = json.loads((HERE / "lmr_station_entrances_final.json").read_text(encoding="utf-8"))
st = doc["stations"]


def overpass(q):
    for i in range(5):
        try:
            r = urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(), headers=UA)
            return json.load(urllib.request.urlopen(r, timeout=300))["elements"]
        except Exception as e:
            print("retry", i, str(e)[:60], flush=True)
            time.sleep(10 * (i + 1))
    sys.exit("overpass failed")


cache = HERE / "heuristic_data.json"
if cache.exists():
    data = json.loads(cache.read_text())
else:
    ar = lambda s: f"(around:200,{s['lat']},{s['lon']})"
    outl = "".join(f'way["building"="train_station"]{ar(s)};way["railway"="platform"]{ar(s)};way["public_transport"~"platform|station"]{ar(s)};way["railway"="station"]{ar(s)};' for s in st)
    pts = "".join(f'node["entrance"~"^(yes|main)$"]{ar(s)};node["amenity"="ticket_validator"]{ar(s)};node["highway"="elevator"]{ar(s)};' for s in st)
    data = {"outlines": overpass(f"[out:json][timeout:240];({outl});out geom;"), "points": overpass(f"[out:json][timeout:240];({pts});out;")}
    cache.write_text(json.dumps(data))
print("outline ways", len(data["outlines"]), "candidate points", len(data["points"]), flush=True)


def hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742000 * math.asin(math.sqrt(x))


rec_hit = rec_n = prec_hit = prec_n = 0
errs = []
per = []
for s in st:
    to_m = Transformer.from_crs(4326, 28300 + int((s["lon"] + 180) // 6) + 1, always_xy=True).transform
    c = Point(*to_m(s["lon"], s["lat"]))
    polys = []
    for w in data["outlines"]:
        g = w.get("geometry") or []
        if len(g) >= 3:
            pg = transform(to_m, Polygon([(p["lon"], p["lat"]) for p in g]).buffer(0))
            if not pg.is_empty and pg.distance(c) <= 120:
                polys.append(pg)
    if not polys:
        continue
    foot = unary_union(polys).convex_hull
    cand = []
    for p in data["points"]:
        pm = Point(*to_m(p["lon"], p["lat"]))
        if hav(s["lat"], s["lon"], p["lat"], p["lon"]) <= 250 and foot.distance(pm) <= NEAR_M:
            cand.append((p["lat"], p["lon"], p["tags"].get("amenity") or p["tags"].get("highway") or "entrance"))
    truth = [(e["lat"], e["lon"]) for e in s["entrances"]]
    if truth:
        for (tl, tn) in truth:
            d = min((hav(tl, tn, a, b) for a, b, _ in cand), default=None)
            rec_n += 1
            if d is not None and d <= 40:
                rec_hit += 1
            if d is not None:
                errs.append(d)
        for (a, b, _) in cand:
            prec_n += 1
            if min(hav(a, b, tl, tn) for tl, tn in truth) <= 40:
                prec_hit += 1
        per.append((s["name"], len(truth), len(cand)))
    else:
        s["_heuristic_candidates"] = cand
print(f"NEAR_M={NEAR_M}: real entrances found within 40 m by H: {rec_hit}/{rec_n} ({100*rec_hit/max(1,rec_n):.0f}%) | "
      f"H points within 40 m of a real entrance: {prec_hit}/{prec_n} ({100*prec_hit/max(1,prec_n):.0f}%)")
if errs:
    errs.sort()
    print("distance from each real entrance to nearest H point (m): median", round(errs[len(errs)//2]), "p90", round(errs[int(len(errs)*.9)]), "max", round(errs[-1]))
print("stations with no entrance in our file: H gives candidates for",
      sum(1 for s in st if s.get("_heuristic_candidates")), "of", sum(1 for s in st if not s["entrances"]))
print({s["name"]: len(s["_heuristic_candidates"]) for s in st if "_heuristic_candidates" in s})
