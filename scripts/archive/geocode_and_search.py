"""Geocode address, find Sentinel-1 scene pairs, submit HyP3 job."""
import os, json, urllib.request, pathlib, time
os.environ.setdefault("ASF_EARTHDATA_USERNAME", "bandylala")
creds = pathlib.Path(__file__).parent / "drawdown_creds.txt"
for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.strip() and not line.startswith("#"):
        os.environ["ASF_EARTHDATA_PASSWORD"] = line.strip()
        break

import asf_search as asf
import hyp3_sdk as sdk

ADDRESS = "21 Martens Circuit, Kellyville NSW 2155"

# --- Step 1: Geocode via Nominatim ---
print(f"Geocoding: {ADDRESS}")
nom_url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(ADDRESS)}&format=json&limit=1&countrycodes=au"
import urllib.parse
nom_url = f"https://nominatim.openstreetmap.org/search?q={urllib.parse.quote(ADDRESS)}&format=json&limit=1&countrycodes=au"
req = urllib.request.Request(nom_url, headers={"User-Agent": "PlotDetect-SAR-validation/1.0"})
with urllib.request.urlopen(req, timeout=15) as r:
    results = json.loads(r.read())

if not results:
    raise SystemExit("Geocode failed — no results")

lat = float(results[0]["lat"])
lon = float(results[0]["lon"])
print(f"  Lat: {lat:.6f}  Lon: {lon:.6f}")
print(f"  Display name: {results[0]['display_name']}")

# --- Step 2: Build bbox (~200m around centroid) ---
HALF = 0.002  # ~200m
bbox_wkt = (
    f"POLYGON(({lon-HALF} {lat-HALF}, {lon+HALF} {lat-HALF}, "
    f"{lon+HALF} {lat+HALF}, {lon-HALF} {lat+HALF}, {lon-HALF} {lat-HALF}))"
)
print(f"  BBox WKT: {bbox_wkt}")

# --- Step 3: Search ASF across likely construction window ---
# Sold March 2026 → completed ~mid 2025 → slab likely 2023-2024
SEARCH_WINDOWS = [
    ("2023-06-01", "2023-12-31", "window_2023h2"),
    ("2024-01-01", "2024-06-30", "window_2024h1"),
    ("2024-07-01", "2024-12-31", "window_2024h2"),
]

for start, end, label in SEARCH_WINDOWS:
    print(f"\n--- ASF search {label} ({start} to {end}) ---")
    results_asf = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel=asf.PRODUCT_TYPE.SLC,
        intersectsWith=bbox_wkt,
        start=start,
        end=end,
    )
    results_sorted = sorted(results_asf, key=lambda r: r.properties.get("startTime", ""))

    # Group by orbit
    orbit_groups = {}
    for r in results_sorted:
        orbit = str(r.properties.get("pathNumber", ""))
        orbit_groups.setdefault(orbit, []).append(r)

    print(f"  {len(results_asf)} scenes across {len(orbit_groups)} orbits")
    for orbit, scenes in sorted(orbit_groups.items(), key=lambda x: -len(x[1])):
        print(f"  Orbit {orbit}: {len(scenes)} scenes")
        for s in scenes[:3]:
            p = s.properties
            t = p["startTime"][11:19]  # HHMMSS
            print(f"    {p['sceneName']}  date={p['startTime'][:10]}  time={t}")

# --- Step 4: Find best pair with matching acquisition time ---
print("\n--- Finding matched pair (same acquisition time ±60s) ---")

# Use largest window with most scenes
all_scenes = []
for start, end, label in SEARCH_WINDOWS:
    r = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel=asf.PRODUCT_TYPE.SLC,
        intersectsWith=bbox_wkt,
        start=start,
        end=end,
    )
    all_scenes.extend(r)

all_scenes = sorted(all_scenes, key=lambda r: r.properties.get("startTime", ""))
print(f"  Total scenes across all windows: {len(all_scenes)}")

# Group by (orbit, time-within-orbit to nearest minute)
def time_key(scene):
    t = scene.properties["startTime"]  # e.g. 2023-09-10T191613Z
    hhmm = t[11:16].replace(":", "")  # HHMM
    orbit = str(scene.properties.get("pathNumber", ""))
    return f"{orbit}_{hhmm}"

groups = {}
for s in all_scenes:
    k = time_key(s)
    groups.setdefault(k, []).append(s)

# Find groups with 2+ scenes (=same location, different dates)
print(f"  Time-slot groups: {len(groups)}")
usable = {k: v for k, v in groups.items() if len(v) >= 2}
print(f"  Groups with 2+ scenes (usable pairs): {len(usable)}")

if not usable:
    print("  No matched pairs found in this window. Try wider date range.")
else:
    # Pick the group with most scenes; use first and last for max temporal baseline
    best_key = max(usable, key=lambda k: len(usable[k]))
    group = sorted(usable[best_key], key=lambda r: r.properties["startTime"])
    scene_before = group[0]
    scene_after = group[-1]

    date_before = scene_before.properties["startTime"][:10]
    date_after  = scene_after.properties["startTime"][:10]
    name_before = scene_before.properties["sceneName"]
    name_after  = scene_after.properties["sceneName"]

    print(f"\n  Best pair (orbit/time slot {best_key}):")
    print(f"    before: {name_before}  ({date_before})")
    print(f"    after:  {name_after}  ({date_after})")
    print(f"    Temporal baseline: {date_before} to {date_after}")

    # Save for submission
    pair_info = {
        "address": ADDRESS,
        "centroid_lat": lat,
        "centroid_lon": lon,
        "bbox_wkt": bbox_wkt,
        "scene_before": name_before,
        "scene_after": name_after,
        "date_before": date_before,
        "date_after": date_after,
        "orbit_slot": best_key,
    }
    out = pathlib.Path(__file__).parent.parent / "validation_output" / "kellyville_pair.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(pair_info, indent=2))
    print(f"\n  Pair saved to {out}")
    print("  Run scripts/submit_kellyville_job.py to submit the HyP3 job.")
