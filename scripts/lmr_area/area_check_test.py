"""Scratchpad: the honest 100-lot test of the low-and-mid-rise area check (distance part).
FIX   = services.lmr_area_inputs.gather() with walking surfaces built from our own OSM footpath network.
JUDGE = public OSM foot router (OSRM, routing.openstreetmap.de): a different engine, never used by the fix.
Both answers go through the SAME decide() rules, so any disagreement comes from the walking measure alone.
Lots drawn with a fixed seed from the NSW Property layer around anchors in the test councils. Lots that were in the
stage-1 sample (used to choose the 100 m band) are labelled 'tuned'; the rest are 'new'.
Prints DONE i/N after every lot and resumes from test_results.json.
Run: python -u -I lmr_area_test.py --n 100 --seed 20261107"""
# prior-art-checked: 2026-11-07. A grep of scripts/ and services/ for station entrance, walking surface, valhalla and gtfs finds no
# existing builder or test of this data; this script is part of the low-and-mid-rise area-check data pipeline
# (see ~/.claude/plans/ce-NEXT-PROMPT-2026-11-07b-lmr-area-check-build.md). Working files go to data/lmr_area_work/ (not committed).
import argparse
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(REPO))
from pyproj import Transformer
from shapely.geometry import Point, Polygon
from shapely.ops import transform

from services import lmr_area_decision as dec
from services import lmr_area_inputs as inp
from services import lmr_walk_surface as ws

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__import__("os").environ.get("LMR_WORK", REPO / "data" / "lmr_area_work"))  # working folder, not committed
HERE.mkdir(parents=True, exist_ok=True)
import os
SURF = HERE / os.environ.get("LMR_SURF_DIR", "walk_surfaces")
OUT_NAME = os.environ.get("LMR_RESULTS", "test_results.json")
# The FIX may use estimated entrances; the JUDGE may not (it uses known entrances only, else the station point), so it stays independent.
STATIONS_FIX = os.environ.get("LMR_STATIONS", "lmr_station_entrances_final.json")
STATIONS_JUDGE = "lmr_station_entrances_final.json"
UA = {"User-Agent": "plotdetect-lmr-test/1.0"}
import threading as _th
JUDGE_LOCK = _th.Lock()
PROP = "https://maps.six.nsw.gov.au/arcgis/rest/services/public/NSW_Property/MapServer/4/query"
STAGE1 = HERE / "no_tuning_sample.json"  # the stage-1 sample is not in the repo: every lot reports as new


def jget(url, params=None, post=False, timeout=60, tries=3):
    for i in range(tries):
        try:
            if post:
                req = urllib.request.Request(url, data=urllib.parse.urlencode(params).encode(), headers=UA)
            else:
                req = urllib.request.Request(url + ("?" + urllib.parse.urlencode(params) if params else ""), headers=UA)
            return json.load(urllib.request.urlopen(req, timeout=timeout))
        except Exception:
            time.sleep(2 * (i + 1))
    return None


def foot(la1, lo1, la2, lo2):
    j = jget(f"https://routing.openstreetmap.de/routed-foot/route/v1/foot/{lo1},{la1};{lo2},{la2}", {"overview": "false"}, tries=2)
    try:
        return j["routes"][0]["distance"]
    except Exception:
        return None


def draw(n, seed, stations, tcs, boxes):
    rng = random.Random(seed)
    pool = []
    anchors = [(st["lat"], st["lon"], st["name"]) for st in stations["stations"] if st["schedule"] == 11]
    for t in tcs:
        ll = [(p[1], p[0]) for r in t["rings"] for p in r]
        anchors.append((sum(a for a, _ in ll) / len(ll), sum(b for _, b in ll) / len(ll), str(t["label"])))
    anchors = [a for a in anchors if any(b[0] <= a[0] <= b[2] and b[1] <= a[1] <= b[3] for b in boxes)]
    rng.shuffle(anchors)
    CAP = 5   # at most 5 lots from any one station or town centre. (An earlier version stopped once it had enough candidates, and the
              # first station alone supplied all 100 lots: the whole test was one station, Lidcombe. This cap prevents that.)
    from concurrent.futures import ThreadPoolExecutor

    def one(a):
        la, lo, nm = a
        j = jget(PROP, {"geometry": f"{lo},{la}", "geometryType": "esriGeometryPoint", "distance": 1250, "units": "esriSRUnit_Meter",
                        "inSR": 4326, "outSR": 4326, "spatialRel": "esriSpatialRelIntersects", "outFields": "address,propid",
                        "returnGeometry": "true", "f": "json"}, post=True)
        if not j or "features" not in j:
            print("  draw query failed for", nm, str((j or {}).get("error"))[:80], flush=True)
        lots = []
        for f in (j or {}).get("features", []):
            r = (f.get("geometry") or {}).get("rings")
            if not r:
                continue
            p = Polygon(r[0]).buffer(0)
            if p.is_empty:
                continue
            rp = p.representative_point()
            lots.append({"anchor": nm, "lat": rp.y, "lon": rp.x, "address": f["attributes"].get("address"), "rings": r[0]})
        random.Random(f"{seed}-{nm}").shuffle(lots)
        return lots[:CAP]

    with ThreadPoolExecutor(max_workers=4) as ex:
        for got in ex.map(one, anchors):
            pool.extend(got)
    print("candidates:", len(pool), "from", len({c["anchor"] for c in pool}), "anchors", flush=True)
    rng.shuffle(pool)
    seen, out = set(), []
    for c in pool:
        k = (c["address"] or "").upper().strip()
        if k and k not in seen:
            seen.add(k)
            out.append(c)
        if len(out) >= n:
            break
    return out


def judge_walk(lot, stations, tcs, to_m):
    ring = lot["rings"]
    poly = transform(to_m, Polygon(ring).buffer(0))
    starts = [(lot["lat"], lot["lon"])] + [(y, x) for x, y in ring[:-1:max(1, len(ring) // 6)]]
    targets = []
    for st in stations["stations"]:
        if st["schedule"] != 11:
            continue
        for e in (st["entrances"] or [{"id": "station node", "lat": st["lat"], "lon": st["lon"]}]):
            targets.append((e["lat"], e["lon"], st["name"], e["id"]))
    for t in tcs:
        for r in t["rings"]:
            for p in r[::3]:
                targets.append((p[1], p[0], str(t["label"]), "town centre edge"))
    # The 6 targets nearest by straight line: a walk cannot beat the straight line, so farther ones are very unlikely to win.
    targets.sort(key=lambda t: poly.distance(Point(*to_m(t[1], t[0]))))
    # ONE request: the router's table endpoint returns every start-to-target walking distance (was up to 24 requests per lot).
    # The 3 nearest target points of EACH station / town centre, nearest anchors first, at most 8 anchors. (Taking the 12 nearest
    # points overall let one town centre's many boundary points crowd out a neighbouring town centre.)
    per, tg = {}, []
    for t in targets:
        if per.setdefault(t[2], 0) < 3:
            per[t[2]] += 1
            tg.append(t)
        if len(per) >= 8 and all(v >= 3 for v in per.values()):
            break
    tg = tg[:24]
    st = starts[:4]   # the service allows at most 100 start-to-target pairs per request: 4 starts x 24 targets = 96
    # JUDGE = the OpenStreetMap Valhalla pedestrian service (a different routing engine from our own footpath files). One matrix call
    # per lot, one call at a time with a pause (the first judge, a public OSRM router, stopped answering after six parallel callers).
    body = json.dumps({"sources": [{"lat": la, "lon": lo} for la, lo in st], "targets": [{"lat": t[0], "lon": t[1]} for t in tg],
                       "costing": "pedestrian", "units": "km"}).encode()
    j = None
    with JUDGE_LOCK:
        for attempt in range(4):
            try:
                req = urllib.request.Request("https://valhalla1.openstreetmap.de/sources_to_targets", data=body,
                                             headers={"User-Agent": UA["User-Agent"], "Content-Type": "application/json"})
                j = json.load(urllib.request.urlopen(req, timeout=40))
                break
            except Exception:
                time.sleep(3 * (attempt + 1))
        time.sleep(0.4)
    best = None
    try:
        for row in j["sources_to_targets"]:
            for cell in row:
                d = cell.get("distance")
                if d is not None and (best is None or d * 1000 < best[0]):
                    best = (d * 1000, tg[cell["to_index"]][2], tg[cell["to_index"]][3])
    except Exception:
        return None
    return best


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--seed", type=int, default=20261107)
    a = ap.parse_args()
    stations = json.loads((HERE / STATIONS_FIX).read_text(encoding="utf-8"))
    stations_judge = json.loads((HERE / STATIONS_JUDGE).read_text(encoding="utf-8"))
    tcs = inp.town_centre_polygons()
    surfaces = [ws.load_surface(str(p)) for p in sorted(SURF.glob("*.json.gz"))]
    print("surfaces", len(surfaces), flush=True)
    boxes = [(-33.99, 150.99, -33.78, 151.30), (-34.06, 151.00, -33.93, 151.17), (-33.95, 150.98, -33.88, 151.08),
             (-33.82, 151.10, -33.70, 151.20), (-33.93, 151.20, -33.85, 151.29)]
    out_path = HERE / OUT_NAME
    res = json.loads(out_path.read_text()) if out_path.exists() else {"lots": []}
    done = {r["address"] for r in res["lots"]}
    tuned = ({(x.get("address_src") or "").upper().strip() for x in json.loads(STAGE1.read_text(encoding="utf-8"))}
             if STAGE1.exists() else set())
    import threading
    from concurrent.futures import ThreadPoolExecutor
    lots_cache = HERE / f"cache_lots_{a.seed}_{a.n}.json"
    if lots_cache.exists():
        lots = json.loads(lots_cache.read_text())          # same lots every run, no re-drawing (the draw is ~100 slow map calls)
    else:
        lots = draw(a.n, a.seed, stations, tcs, boxes)
        if len(lots) == a.n:
            lots_cache.write_text(json.dumps(lots))
    print("lots drawn", len(lots), flush=True)
    if len(lots) < a.n:
        sys.exit(f"ONLY {len(lots)} lots drawn, wanted {a.n}: the draw is broken, nothing was scored")
    # Saved map measurements and saved judge walks: they do not depend on the walking files, so a re-run after changing those
    # files makes no map calls and no router calls. Delete the cache files to force fresh measurements.
    layers_path, judge_path = HERE / "cache_layers.json", HERE / f"cache_judge_valhalla2_{STATIONS_JUDGE}"
    layers_cache = json.loads(layers_path.read_text()) if layers_path.exists() else {}
    judge_cache = json.loads(judge_path.read_text()) if judge_path.exists() else {}
    lock = threading.Lock()

    def process(lot):
        epsg = inp._epsg_for(lot["lon"])
        to_m = Transformer.from_crs(4326, epsg, always_xy=True).transform
        key = lot["address"]
        if key not in layers_cache:
            layers_cache[key] = inp.fetch_layers(lot["lat"], lot["lon"], lot["rings"])
        m = inp.gather(lot["lat"], lot["lon"], rings=lot["rings"], stations=stations, walk_surfaces=surfaces, layers=layers_cache[key])
        fix = dec.decide(m)
        if not judge_cache.get(key):                      # a failed judge call is never saved as if it were an answer
            judge_cache[key] = judge_walk(lot, stations_judge, tcs, to_m)
        jw = judge_cache[key]
        mj = json.loads(json.dumps(m, default=str))
        mj["walk"] = {"m": jw[0], "anchor": jw[1], "entrance_id": jw[2], "valid": True} if jw else None
        judge = dec.decide(mj)
        rec = ({
            "address": lot["address"], "anchor": lot["anchor"],
            "set": "tuned" if (lot["address"] or "").upper().strip() in tuned else "new",
            "straight_m": m.get("straight_m"), "lga": m.get("lga"),
            "fix_walk": (m.get("walk") or {}).get("m"), "fix_reason": (m.get("walk") or {}).get("reason"),
            "judge_walk": jw[0] if jw else None, "fix": fix["lmr"]["answer"], "fix_code": fix["lmr"]["reason_code"],
            "fix_low": (fix["lmr"].get("figures") or {}).get("walk_low_m"), "fix_high": (fix["lmr"].get("figures") or {}).get("walk_high_m"),
            "fix_lean": fix["lmr"].get("lean"), "fix_share_inside": fix["lmr"].get("share_of_range_inside"),
            "fix_extra_m": (fix["lmr"].get("figures") or {}).get("entrance_unmapped_extra_m"),
            "judge": judge["lmr"]["answer"], "judge_code": judge["lmr"]["reason_code"]})
        with lock:
            res["lots"].append(rec)
            out_path.write_text(json.dumps(res, indent=1))
            layers_path.write_text(json.dumps(layers_cache))
            judge_path.write_text(json.dumps(judge_cache))
            r = rec
            print(f"DONE {len(res['lots'])}/{len(lots)} {r['address']} | straight {r['straight_m'] and round(r['straight_m'])} | "
                  f"fix {r['fix_walk']} {r['fix']}({r['fix_code']}) | judge {r['judge_walk'] and round(r['judge_walk'])} {r['judge']}", flush=True)

    todo = [lot for lot in lots if lot["address"] not in done]
    with ThreadPoolExecutor(max_workers=6) as pool:   # 6 lots at a time (was one at a time)
        list(pool.map(process, todo))
