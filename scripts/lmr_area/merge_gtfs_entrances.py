"""Scratchpad: add TfNSW GTFS Pathways entrances (location_type 2) to lmr_station_entrances.json.
Matches a GTFS station (location_type 1) to ours by name, keeps entrances within MAX_M of our station point.
Source: Transport for NSW 'GTFS Pathways', CC-BY 3.0 Australia (attribution recorded in the file).
Writes lmr_station_entrances_merged.json (the original is kept)."""
# prior-art-checked: 2026-11-07. A grep of scripts/ and services/ for station entrance, walking surface, valhalla and gtfs finds no
# existing builder or test of this data; this script is part of the low-and-mid-rise area-check data pipeline
# (see ~/.claude/plans/ce-NEXT-PROMPT-2026-11-07b-lmr-area-check-build.md). Working files go to data/lmr_area_work/ (not committed).
import csv
import json
import math
import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
HERE = Path(__import__("os").environ.get("LMR_WORK", REPO / "data" / "lmr_area_work"))  # working folder, not committed
HERE.mkdir(parents=True, exist_ok=True)
MAX_M = 300


def hav(a, b, c, d):
    p = math.pi / 180
    x = math.sin((c - a) * p / 2) ** 2 + math.cos(a * p) * math.cos(c * p) * math.sin((d - b) * p / 2) ** 2
    return 12742000 * math.asin(math.sqrt(x))


def key(n):
    n = re.sub(r"\b(station|light rail|railway)\b", " ", n.lower())
    return re.sub(r"[^a-z]+", " ", n).strip()


rows = list(csv.DictReader(open(HERE / "gtfs_pathways" / "stops_0.txt", encoding="utf-8")))
parents = {r["stop_id"]: r for r in rows if r["location_type"] == "1"}
ents = [r for r in rows if r["location_type"] == "2"]
by_key = {}
for p in parents.values():
    by_key.setdefault(key(p["stop_name"]), set()).add(p["stop_id"])
doc = json.loads((HERE / "lmr_station_entrances.json").read_text(encoding="utf-8"))
added_total, far = 0, []
for s in doc["stations"]:
    pids = by_key.get(key(s["name"]), set())
    have = {(round(e["lat"], 5), round(e["lon"], 5)) for e in s["entrances"]}
    for e in ents:
        if e["parent_station"] not in pids:
            continue
        la, lo = float(e["stop_lat"]), float(e["stop_lon"])
        d = hav(s["lat"], s["lon"], la, lo)
        if d > MAX_M:
            far.append((s["name"], e["stop_name"], round(d)))
            continue
        if (round(la, 5), round(lo, 5)) in have:
            continue
        s["entrances"].append({"id": f"gtfs:{e['stop_id']}", "lat": la, "lon": lo, "name": e["stop_name"]})
        added_total += 1
    s["no_mapped_entrance"] = not s["entrances"]
doc["source"] = ("OpenStreetMap via Overpass (ODbL) + Transport for NSW GTFS Pathways (CC-BY 3.0 Australia, "
                 "https://opendata.transport.nsw.gov.au/dataset/gtfs-pathways)")
(HERE / "lmr_station_entrances_merged.json").write_text(json.dumps(doc, indent=1), encoding="utf-8")
st = doc["stations"]
print("entrances added:", added_total, "| entrances beyond", MAX_M, "m ignored:", len(far), far[:5])
print("stations with an entrance:", sum(1 for s in st if s["entrances"]), "of", len(st))
print("still none:", [s["name"] for s in st if not s["entrances"]])
