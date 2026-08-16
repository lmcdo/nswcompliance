"""
Submit HyP3 jobs for 21 Martens Circuit, Kellyville.
Uses 12-day adjacent pairs from the same orbit time slot.
Sold March 2026 → construction likely active mid-2024.
"""
import os, pathlib, json
os.environ.setdefault("ASF_EARTHDATA_USERNAME", "bandylala")
creds = pathlib.Path(__file__).parent / "drawdown_creds.txt"
for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.strip() and not line.startswith("#"):
        os.environ["ASF_EARTHDATA_PASSWORD"] = line.strip()
        break

import asf_search as asf
import hyp3_sdk as sdk
from hyp3_sdk import Batch

ADDRESS = "21 Martens Circuit, Kellyville NSW 2155"
CENTROID_LAT = -33.706693
CENTROID_LON = 150.936325
BBOX_WKT = "POLYGON((150.9343247 -33.7086929, 150.9383247 -33.7086929, 150.9383247 -33.7046929, 150.9343247 -33.7046929, 150.9343247 -33.7086929))"

OUTPUT_DIR = pathlib.Path(__file__).parent.parent / "validation_output" / "kellyville"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Find all orbit-9 scenes (08:39 acquisition — confirmed same-track) across 2023-2024
print("Searching orbit-9 scenes for Kellyville 2023-2025...")
results = asf.search(
    platform=asf.PLATFORM.SENTINEL1,
    processingLevel=asf.PRODUCT_TYPE.SLC,
    intersectsWith=BBOX_WKT,
    start="2023-01-01",
    end="2025-01-01",
)

# Filter to orbit 9, acquisition time ~08:39 (±2 min)
orbit9 = []
for r in results:
    p = r.properties
    if str(p.get("pathNumber")) == "9":
        t = p["startTime"][11:16]  # HH:MM
        if t.startswith("08:3"):
            orbit9.append(r)

orbit9 = sorted(orbit9, key=lambda r: r.properties["startTime"])
print(f"  Orbit-9 scenes (08:3x): {len(orbit9)}")
for s in orbit9:
    print(f"    {s.properties['sceneName']}  {s.properties['startTime'][:10]}")

# Build adjacent 12-day pairs
pairs = []
for i in range(len(orbit9) - 1):
    a = orbit9[i]
    b = orbit9[i + 1]
    da = a.properties["startTime"][:10]
    db = b.properties["startTime"][:10]
    # Check temporal gap is ~12 days (10-14 days)
    from datetime import date
    d1 = date.fromisoformat(da)
    d2 = date.fromisoformat(db)
    gap = (d2 - d1).days
    if 10 <= gap <= 14:
        pairs.append((a, b, da, db, gap))

print(f"\n  Valid 12-day pairs: {len(pairs)}")
for a, b, da, db, gap in pairs:
    print(f"    {da} -> {db}  (gap={gap}d)")

# Submit jobs for 3 key windows:
# 1. Early 2024 (likely slab/frame)
# 2. Mid 2024 (likely frame/lock-up)
# 3. Late 2024 (likely finishing)
TARGET_WINDOWS = [
    ("2024-01-01", "2024-03-31", "kellyville-early2024"),
    ("2024-06-01", "2024-08-31", "kellyville-mid2024"),
    ("2024-10-01", "2024-12-31", "kellyville-late2024"),
]

hyp3 = sdk.HyP3(username=os.environ["ASF_EARTHDATA_USERNAME"], password=os.environ["ASF_EARTHDATA_PASSWORD"])
print(f"\nCredits remaining: {hyp3.check_credits()}")

submitted_jobs = []

for win_start, win_end, label in TARGET_WINDOWS:
    window_pairs = [
        (a, b, da, db, gap)
        for a, b, da, db, gap in pairs
        if win_start <= da <= win_end
    ]
    if not window_pairs:
        print(f"\n  {label}: no pairs found in window")
        continue

    # Use first pair in each window
    a, b, da, db, gap = window_pairs[0]
    job_name = f"val-{label}-{da}-{db}"
    sname_a = a.properties["sceneName"]
    sname_b = b.properties["sceneName"]

    print(f"\n  Submitting {label}:")
    print(f"    {da} -> {db}  (gap={gap}d)")
    print(f"    before: {sname_a}")
    print(f"    after:  {sname_b}")

    try:
        job = hyp3.submit_insar_job(
            granule1=sname_a,
            granule2=sname_b,
            name=job_name,
            looks="10x2",
            apply_water_mask=False,
            include_dem=False,
            include_wrapped_phase=False,
        )
        job_id = job.jobs[0].job_id
        print(f"    Submitted. job_id: {job_id}")
        submitted_jobs.append({
            "label": label,
            "job_id": str(job_id),
            "job_name": job_name,
            "scene_before": sname_a,
            "scene_after": sname_b,
            "date_before": da,
            "date_after": db,
            "centroid_lat": CENTROID_LAT,
            "centroid_lon": CENTROID_LON,
            "address": ADDRESS,
        })
    except Exception as e:
        print(f"    ERROR: {e}")

manifest = OUTPUT_DIR / "jobs.json"
manifest.write_text(json.dumps(submitted_jobs, indent=2))
print(f"\nJobs manifest: {manifest}")
print(f"Credits remaining: {hyp3.check_credits()}")
print("Jobs running on NASA servers (~1 hour). Run check_jobs_kellyville.py to poll.")
