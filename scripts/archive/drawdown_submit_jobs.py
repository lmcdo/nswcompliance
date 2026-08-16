"""
Submit HyP3 Burst InSAR jobs for 3 validation sites.
Uses scene pairs identified by drawdown_scene_check.py.
Saves job IDs to validation_output/jobs.txt for polling later.
"""

import os
import json
from pathlib import Path

import hyp3_sdk as sdk

# --- Credentials (local testing script — do not commit passwords) ---
USERNAME = os.environ.get("ASF_EARTHDATA_USERNAME", "bandylala")
PASSWORD = os.environ.get("ASF_EARTHDATA_PASSWORD", "")

if not PASSWORD:
    # Allow .env file in project root for convenience
    env_file = Path(__file__).parent.parent / ".env.drawdown"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            if line.startswith("ASF_EARTHDATA_PASSWORD="):
                PASSWORD = line.split("=", 1)[1].strip()
                break

if not PASSWORD:
    raise SystemExit(
        "ASF_EARTHDATA_PASSWORD not set.\n"
        "Either set the env var or create .env.drawdown with:\n"
        "ASF_EARTHDATA_PASSWORD=your_password"
    )

# --- Scene pairs from drawdown_scene_check.py output ---
JOBS = [
    {
        "name": "val-parramatta-20230910-20230922",
        "site": "parramatta_test",
        "scene_before": "S1A_IW_SLC__1SDV_20230910T191613_20230910T191640_050269_060D23_87A9",
        "scene_after":  "S1A_IW_SLC__1SDV_20230922T191549_20230922T191616_050444_061319_F14B",
        "date_before": "2023-09-10",
        "date_after":  "2023-09-22",
        "centroid_lon": 151.002,
        "centroid_lat": -33.818,
    },
    {
        "name": "val-hills-20230618-20230630",
        "site": "hills_district_test",
        "scene_before": "S1A_IW_SLC__1SDV_20230618T191609_20230618T191635_049044_05E5D0_8DC0",
        "scene_after":  "S1A_IW_SLC__1SDV_20230630T191544_20230630T191611_049219_05EB1C_2BEC",
        "date_before": "2023-06-18",
        "date_after":  "2023-06-30",
        "centroid_lon": 150.992,
        "centroid_lat": -33.728,
    },
    {
        "name": "val-innerwest-20231104-20231116",
        "site": "inner_west_test",
        "scene_before": "S1A_IW_SLC__1SDV_20231104T190804_20231104T190832_051071_06288F_99C6",
        "scene_after":  "S1A_IW_SLC__1SDV_20231116T190803_20231116T190831_051246_062E9E_A9B5",
        "date_before": "2023-11-04",
        "date_after":  "2023-11-16",
        "centroid_lon": 151.150,
        "centroid_lat": -33.894,
    },
]

OUTPUT_DIR = Path(__file__).parent.parent / "validation_output"
OUTPUT_DIR.mkdir(exist_ok=True)

print(f"Connecting to HyP3 as {USERNAME}...")
hyp3 = sdk.HyP3(username=USERNAME, password=PASSWORD)
quota = hyp3.check_quota()
print(f"HyP3 quota: {quota}")
print()

submitted = []

for j in JOBS:
    site_dir = OUTPUT_DIR / j["site"]
    site_dir.mkdir(exist_ok=True)

    print(f"Submitting: {j['name']}")
    print(f"  before: {j['scene_before']}")
    print(f"  after:  {j['scene_after']}")

    try:
        job = hyp3.submit_insar_job(
            granule1=j["scene_before"],
            granule2=j["scene_after"],
            name=j["name"],
            looks="10x2",           # 40m resolution, 5 credits
            apply_water_mask=False,
            include_dem=False,
            include_wrapped_phase=False,
        )
        job_ids = [jj.job_id for jj in job.jobs]
        print(f"  Submitted. job_id(s): {job_ids}")

        record = {**j, "job_ids": job_ids, "status": "submitted"}
        submitted.append(record)

        (site_dir / "scenes.txt").write_text(
            f"Before: {j['scene_before']}  ({j['date_before']})\n"
            f"After:  {j['scene_after']}  ({j['date_after']})\n"
            f"Centroid: {j['centroid_lat']}, {j['centroid_lon']}\n"
            f"Job IDs: {job_ids}\n"
        )

    except Exception as e:
        print(f"  ERROR: {e}")
        submitted.append({**j, "error": str(e)})

    print()

# Save job manifest for polling script
manifest_path = OUTPUT_DIR / "jobs.json"
manifest_path.write_text(json.dumps(submitted, indent=2))
print(f"Job manifest saved to: {manifest_path}")
print()
print("Jobs are running on NASA servers (1-2 hours).")
print("Run scripts/drawdown_poll_results.py to check status and download GeoTIFFs.")
