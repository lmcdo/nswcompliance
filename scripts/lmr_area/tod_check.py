"""Check the Chapter 5 (Transport Oriented Development) answer on about 30 lots, drawn so the hard cases are included.

The Chapter 5 answer is a map lookup: land on the TOD Sites Map AND in one of the 12 councils in s152(1), and (s152(2)) the whole lot
if any part is on the map, except a lot with a heritage item (s152(4)). So this check does not measure a walk. It checks that the
code applies those three rules correctly, by recomputing the answer a second way: it fetches the TOD map polygons themselves and
tests them against the lot outline here, with the council read from the saved law. Both ways use the same published map, so this
cannot show the map is wrong; a person should read the printed table.

Lots: 10 whose address point is on the map; 10 whose lot outline touches the map but whose address point is not (the whole-lot rule);
10 within about 150 m of the map but not touching it. Fixed seed.
Usage: python scripts/lmr_area/tod_check.py [seed]
"""
# prior-art-checked: 2026-11-07. No script checks the Chapter 5 answer; services/lmr_area_inputs and lmr_area_decision are what it tests.
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from shapely.geometry import Point, Polygon  # noqa: E402

from services import lmr_area_decision as dec  # noqa: E402
from services import lmr_area_inputs as inp  # noqa: E402

UA = {"User-Agent": "plotdetect-lmr-tod-check/1.0"}
PROP = inp.LAYERS["lot"]
TOD = inp.LAYERS["tod_map"]


def post(url, params, tries=3):
    for i in range(tries):
        try:
            r = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(), headers=UA)
            return json.load(urllib.request.urlopen(r, timeout=60))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def tod_polys_near(lat, lng, dist_m):
    j = post(TOD, {"geometry": f"{lng},{lat}", "geometryType": "esriGeometryPoint", "distance": dist_m, "units": "esriSRUnit_Meter",
                   "inSR": 4326, "outSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "OBJECTID",
                   "returnGeometry": "true", "f": "json"})
    if not j or "features" not in j:
        return None
    return [Polygon(f["geometry"]["rings"][0]).buffer(0) for f in j["features"] if (f.get("geometry") or {}).get("rings")]


def lots_near(lat, lng, dist_m):
    j = post(PROP, {"geometry": f"{lng},{lat}", "geometryType": "esriGeometryPoint", "distance": dist_m, "units": "esriSRUnit_Meter",
                    "inSR": 4326, "outSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "address",
                    "returnGeometry": "true", "f": "json"})
    out = []
    for f in (j or {}).get("features", []):
        r = (f.get("geometry") or {}).get("rings")
        if r and f["attributes"].get("address"):
            p = Polygon(r[0]).buffer(0)
            if not p.is_empty:
                rp = p.representative_point()
                out.append({"address": f["attributes"]["address"], "lat": rp.y, "lon": rp.x, "rings": r[0], "poly": p})
    return out


def main(seed: int) -> int:
    rng = random.Random(seed)
    facts = dec.LawFacts.load()
    # seed points: centres of town centres and stations inside the 12 councils give TOD areas to sample around
    st = json.loads((REPO / "data" / "law" / "lmr_station_entrances.json").read_text(encoding="utf-8"))["stations"]
    seeds = [(s["lat"], s["lon"]) for s in st]
    rng.shuffle(seeds)
    groups = {"on_map": [], "whole_lot_case": [], "just_outside": []}
    for lat, lng in seeds:
        if all(len(v) >= 10 for v in groups.values()):
            break
        polys = tod_polys_near(lat, lng, 400)
        if not polys:
            continue
        taken = {k: 0 for k in groups}   # at most 1 lot per group from any one station, so the sample spreads across stations and councils
        lots_here = lots_near(lat, lng, 400)
        rng.shuffle(lots_here)
        for lot in lots_here:
            hit_point = any(p.contains(Point(lot["lon"], lot["lat"])) for p in polys)
            hit_lot = any(p.intersects(lot["poly"]) for p in polys)
            near = any(p.distance(lot["poly"]) < 0.0015 for p in polys)  # about 150 m in degrees
            key = "on_map" if hit_point else "whole_lot_case" if hit_lot else "just_outside" if near else None
            if key and len(groups[key]) < 10 and taken[key] < 1 and lot["address"] not in {x["address"] for v in groups.values() for x in v}:
                lot["station_seed"] = (round(lat, 4), round(lng, 4))
                groups[key].append(lot)
                taken[key] += 1
    rows, agree, n = [], 0, 0
    for key, lots in groups.items():
        for lot in lots:
            layers = inp.fetch_layers(lot["lat"], lot["lon"], lot["rings"])
            m = dict(layers)
            m["sched12_straight_m"], m["straight_m"], m["walk"] = 9999.0, 9999.0, None  # the distance rules are not under test here
            ours = dec.decide(m, facts)["tod"]
            polys = tod_polys_near(lot["lat"], lot["lon"], 250) or []   # wide enough for a large lot whose edge is far from its centre
            hp = any(p.contains(Point(lot["lon"], lot["lat"])) for p in polys)
            hl = any(p.intersects(lot["poly"]) for p in polys)
            heritage = (layers.get("heritage") or {}).get("item")
            lga = layers.get("lga")
            listed = bool(lga) and dec._in_names(lga, facts.names("tod_lgas"))
            # the same rules written out a second way, from the polygons
            if lga is None or heritage is None:
                expect = "cant_tell"
            elif not listed:
                expect = "no"
            elif hp:
                expect = "yes"
            elif hl:
                expect = "cant_tell" if heritage else "yes"   # s152(4): the whole-lot rule is off for a heritage-item lot
            else:
                expect = "no"
            n += 1
            ok = ours["answer"] == expect
            agree += ok
            rows.append((key, lot["address"], lga, "point" if hp else "lot-only" if hl else "off-map", heritage, ours["answer"], expect, "OK" if ok else "DIFF"))
    print(f"{'group':<15} {'address':<42} {'council':<22} {'map':<9} {'heritage':<9} {'ours':<10} {'recomputed':<10}")
    for r in rows:
        print(f"{r[0]:<15} {r[1][:41]:<42} {str(r[2])[:21]:<22} {r[3]:<9} {str(r[4]):<9} {r[5]:<10} {r[6]:<10} {r[7]}")
    from collections import Counter
    print(f"\nChapter 5 answers: {agree}/{n} match the second computation | groups drawn:", {k: len(v) for k, v in groups.items()})
    print("stations sampled:", len({lot["station_seed"] for v in groups.values() for lot in v}),
          "| councils:", dict(Counter(r[2] for r in rows)), "| answers:", dict(Counter(r[5] for r in rows)))
    return 0 if n and agree == n else 1


if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else 20261107))
