"""Scratchpad: fill missing station entrances with the tested OpenStreetMap rule (see entrance_heuristic_test.py).
Rule H: entrance=yes/main nodes, Opal card readers (amenity=ticket_validator) and lifts (highway=elevator) within 60 m of the
station building/platform outline. Measured on 36 stations with KNOWN entrances (120 real entrances): H finds 96% within 40 m;
median miss 5 m, 90th percentile 25 m. So an estimated entrance carries 40 m of extra uncertainty (the measured error, rounded up).
Stations where H finds nothing keep their building/platform outline method. Writes lmr_station_entrances_v3.json."""
# prior-art-checked: 2026-11-07. A grep of scripts/ and services/ for station entrance, walking surface, valhalla and gtfs finds no
# existing builder or test of this data; this script is part of the low-and-mid-rise area-check data pipeline
# (see ~/.claude/plans/ce-NEXT-PROMPT-2026-11-07b-lmr-area-check-build.md). Working files go to data/lmr_area_work/ (not committed).
import json
import math
from pathlib import Path

from pyproj import Transformer
from shapely.geometry import Point, Polygon
from shapely.ops import transform, unary_union

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__import__("os").environ.get("LMR_WORK", REPO / "data" / "lmr_area_work"))  # working folder, not committed
HERE.mkdir(parents=True, exist_ok=True)
NEAR_M = 60
EXTRA_M = 40
data = json.loads((HERE / "heuristic_data.json").read_text())
doc = json.loads((HERE / "lmr_station_entrances_final.json").read_text(encoding="utf-8"))
filled, kept_outline = [], []
for s in doc["stations"]:
    if s["entrances"]:
        continue
    to_m = Transformer.from_crs(4326, 28300 + int((s["lon"] + 180) // 6) + 1, always_xy=True).transform
    c = Point(*to_m(s["lon"], s["lat"]))
    polys = []
    for w in data["outlines"]:
        g = w.get("geometry") or []
        if len(g) >= 3:
            pg = transform(to_m, Polygon([(p["lon"], p["lat"]) for p in g]).buffer(0))
            if not pg.is_empty and pg.distance(c) <= 120:
                polys.append(pg)
    cand = []
    if polys:
        foot = unary_union(polys).convex_hull
        for p in data["points"]:
            pm = Point(*to_m(p["lon"], p["lat"]))
            if c.distance(pm) <= 250 and foot.distance(pm) <= NEAR_M:
                kind = p["tags"].get("amenity") or p["tags"].get("highway") or "entrance"
                cand.append({"id": f"osm-estimate:node/{p['id']}", "lat": p["lat"], "lon": p["lon"], "kind": kind, "estimated": True})
    if cand:
        s["entrances"] = cand
        s["entrance_estimate_extra_m"] = EXTRA_M
        s["no_mapped_entrance"] = False
        s.pop("footprint", None)
        filled.append((s["name"], len(cand)))
    else:
        kept_outline.append(s["name"])
doc["estimate_note"] = (f"Entrances marked estimated: found by rule H (entrance=yes/main, ticket validator or lift within {NEAR_M} m of the station outline). "
                        f"Tested on 36 stations with known entrances: 96% of real entrances within 40 m, median miss 5 m, p90 25 m. Extra uncertainty {EXTRA_M} m.")
(HERE / "lmr_station_entrances_v3.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
print("filled by rule H:", len(filled), filled)
print("still on the outline method:", kept_outline)
