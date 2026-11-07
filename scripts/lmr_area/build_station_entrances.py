"""Scratchpad one-off (bulk version): public entrances for the Schedule 11 and 12 stations, from OpenStreetMap.
Two Overpass queries in total: (1) every rail/light-rail station in NSW, (2) every entrance node within 200 m of one.
Station names are read from the saved law facts and matched locally. Writes lmr_station_entrances.json next to this file."""
# prior-art-checked: 2026-11-07. A grep of scripts/ and services/ for station entrance, walking surface, valhalla and gtfs finds no
# existing builder or test of this data; this script is part of the low-and-mid-rise area-check data pipeline
# (see ~/.claude/plans/ce-NEXT-PROMPT-2026-11-07b-lmr-area-check-build.md). Working files go to data/lmr_area_work/ (not committed).
import json
import math
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__import__("os").environ.get("LMR_WORK", REPO / "data" / "lmr_area_work"))  # working folder, not committed
HERE.mkdir(parents=True, exist_ok=True)
FACTS = REPO / "data" / "law" / "housing_sepp_lmr_facts.json"
OUT = HERE / "lmr_station_entrances.json"
UA = {"User-Agent": "plotdetect-lmr-stations/1.0"}
RAD = 200


def op(q):
    for i in range(5):
        try:
            r = urllib.request.Request("https://overpass-api.de/api/interpreter", data=urllib.parse.urlencode({"data": q}).encode(), headers=UA)
            j = json.load(urllib.request.urlopen(r, timeout=300))
            print("overpass ok", len(j["elements"]), "elements", flush=True)
            return j["elements"]
        except Exception as e:
            print("retry", i, str(e)[:80], flush=True)
            time.sleep(10 * (i + 1))
    raise SystemExit("overpass failed")


def pos(e):
    return (e.get("lat") or e["center"]["lat"], e.get("lon") or e["center"]["lon"])


def hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742000 * math.asin(math.sqrt(x))


facts = json.loads(FACTS.read_text(encoding="utf-8"))
f = facts["facts"]
jobs = [(n, 11) for n in f["schedule_11_stations"]["value"]] + [(n, 12) for n in f["schedule_12_stations"]["value"]]
bb = "(-37.6,140.9,-28.1,153.7)"
stn = op(f'[out:json][timeout:240];(nwr["railway"~"^(station|halt|tram_stop)$"]["name"]{bb};);out center;')
by_name = {}
for x in stn:
    by_name.setdefault(re.sub(r"( railway)?( station)?( light rail)?( stop)?$", "", x["tags"]["name"].strip(), flags=re.I).lower(), []).append(x)
ok, miss = [], []
for nm, sc in jobs:
    light = "light rail station" in nm
    base = re.sub(r"\s+(light rail )?station$", "", nm).strip().lower()
    # Reviewed alias (2026-11-07): the law says "Kingsford Juniors", OpenStreetMap names that stop "Juniors Kingsford"
    # (relation 16741089). OSM's separate "Kingsford" stop (way 822368372) is the other light rail stop: NOT used.
    base = {"kingsford juniors": "juniors kingsford"}.get(base, base)
    c = by_name.get(base, [])

    def kind_ok(x):
        t = x.get("tags", {})
        l = t.get("station") == "light_rail" or t.get("railway") == "tram_stop" or t.get("light_rail") == "yes"
        return l if light else not l

    c = sorted([x for x in c if kind_ok(x)], key=lambda x: (x["tags"].get("railway") != "station", x["type"] != "node"))
    if not c:
        miss.append({"name": nm})
        continue
    la, lo = pos(c[0])
    ok.append({"name": nm, "schedule": sc, "light_rail": light, "osm": f'{c[0]["type"]}/{c[0]["id"]}', "lat": la, "lon": lo,
               "candidates": len(c), "entrances": []})
print("matched", len(ok), "of", len(jobs), "| missing:", [m["name"] for m in miss], flush=True)
# one query for every entrance node near any chosen station
# Only the standard station-entrance tag. A bare entrance=* node within 200 m is often a shop or office door, and counting it
# would make the station look closer than its public entrance (a wrong "yes"). A station with none gets its station node and a doubled margin.
around = "".join(f'node["railway"="subway_entrance"](around:{RAD},{s["lat"]},{s["lon"]});' for s in ok)
# Second source: entrance nodes that are vertices of the STATION BUILDING or platform complex (a shop door never is).
bld = "".join(f'way["building"="train_station"](around:{RAD},{s["lat"]},{s["lon"]});way["public_transport"="station"](around:{RAD},{s["lat"]},{s["lon"]});'
              f'way["railway"="station"](around:{RAD},{s["lat"]},{s["lon"]});' for s in ok)
ents = op(f"[out:json][timeout:240];({around});out;") + op(f'[out:json][timeout:240];({bld})->.w;node(w.w)["entrance"];out;')
for e in ents:
    best = min(ok, key=lambda s: hav(s["lat"], s["lon"], e["lat"], e["lon"]))
    if hav(best["lat"], best["lon"], e["lat"], e["lon"]) <= RAD and not any(x["id"] == f'node/{e["id"]}' for x in best["entrances"]):
        best["entrances"].append({"id": f'node/{e["id"]}', "lat": e["lat"], "lon": e["lon"]})
for s in ok:
    s["no_mapped_entrance"] = not s["entrances"]
OUT.write_text(json.dumps({"built": date.today().isoformat(), "source": "OpenStreetMap via Overpass (ODbL)", "law_version_date": facts["law_version_date"],
                           "stations": ok, "not_found": [m["name"] for m in miss]}, indent=1), encoding="utf-8")
print(f"found {len(ok)} of {len(jobs)}")
print("ambiguous (more than 1 candidate):", [(s["name"], s["candidates"]) for s in ok if s["candidates"] > 1])
print("no mapped entrance:", [s["name"] for s in ok if s["no_mapped_entrance"]])
