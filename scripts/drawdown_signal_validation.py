"""
Step 2 — Manual signal validation script.
Submits HyP3 Burst InSAR jobs for 3 known Sydney construction sites
and downloads the coherence GeoTIFFs for visual inspection in QGIS.

Usage:
    python scripts/drawdown_signal_validation.py

Requires:
    ASF_EARTHDATA_USERNAME and ASF_EARTHDATA_PASSWORD env vars set.
    pip install hyp3_sdk asf_search rasterio

Output:
    ./validation_output/{site_name}/
        - *_corr.tif       (coherence map — open this in QGIS)
        - scenes.txt       (scene IDs used)
        - result.txt       (coherence value at lot centroid)
"""

import os
import time
from pathlib import Path
from datetime import datetime, timedelta

import asf_search as asf
import hyp3_sdk as sdk

USERNAME = os.environ.get("ASF_EARTHDATA_USERNAME", "bandylala")
PASSWORD = os.environ.get("ASF_EARTHDATA_PASSWORD", "")

OUTPUT_DIR = Path("./validation_output")
OUTPUT_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Test sites — 3 known Sydney construction sites with approximate CC dates.
# Replace these with real addresses + CC dates from the NSW Planning Portal.
# Pick knockdown-rebuilds or new builds on previously clear lots for best signal.
# ---------------------------------------------------------------------------
SITES = [
    {
        "name": "parramatta_test",
        "description": "Parramatta — new dwelling (replace with real CC site)",
        # Bounding box: ±0.002° around lot centroid (~200m box — covers the lot + buffer)
        "bbox_wkt": "POLYGON((151.000 -33.820, 151.004 -33.820, 151.004 -33.816, 151.000 -33.816, 151.000 -33.820))",
        "centroid_lon": 151.002,
        "centroid_lat": -33.818,
        # Date the slab/frame was claimed — search for scenes around this date
        "cc_date": "2023-09-15",
        # Search window: 30 days before to 14 days after
        "search_start": "2023-08-15",
        "search_end": "2023-09-30",
    },
    {
        "name": "hills_district_test",
        "description": "Hills District — new dwelling (replace with real CC site)",
        "bbox_wkt": "POLYGON((150.990 -33.730, 150.994 -33.730, 150.994 -33.726, 150.990 -33.726, 150.990 -33.730))",
        "centroid_lon": 150.992,
        "centroid_lat": -33.728,
        "cc_date": "2023-06-20",
        "search_start": "2023-05-20",
        "search_end": "2023-07-05",
    },
    {
        "name": "inner_west_test",
        "description": "Inner West — knockdown rebuild (replace with real CC site)",
        "bbox_wkt": "POLYGON((151.148 -33.896, 151.152 -33.896, 151.152 -33.892, 151.148 -33.892, 151.148 -33.896))",
        "centroid_lon": 151.150,
        "centroid_lat": -33.894,
        "cc_date": "2023-11-10",
        "search_start": "2023-10-10",
        "search_end": "2023-11-25",
    },
]


def find_scene_pair(bbox_wkt: str, search_start: str, search_end: str, cc_date: str):
    """
    Find two Sentinel-1 SLC scenes from the same orbit bracketing cc_date.
    Returns (scene_before, scene_after, date_before, date_after) or None.
    """
    print(f"  Searching ASF for scenes between {search_start} and {search_end}...")

    results = asf.search(
        platform=asf.PLATFORM.SENTINEL1,
        processingLevel=asf.PRODUCT_TYPE.SLC,
        intersectsWith=bbox_wkt,
        start=search_start,
        end=search_end,
    )

    if len(results) < 2:
        print(f"  ERROR: Only {len(results)} scene(s) found — need at least 2.")
        return None

    print(f"  Found {len(results)} scenes.")

    # Sort by acquisition date
    results_sorted = sorted(results, key=lambda r: r.properties.get("startTime", ""))

    # Show all found scenes
    for r in results_sorted:
        p = r.properties
        print(f"    {p['sceneName']}  orbit={p['pathNumber']}  date={p['startTime'][:10]}")

    # Filter to most common orbit (largest group)
    orbit_groups: dict = {}
    for r in results_sorted:
        orbit = str(r.properties.get("pathNumber", ""))
        orbit_groups.setdefault(orbit, []).append(r)
    primary_orbit = max(orbit_groups, key=lambda k: len(orbit_groups[k]))
    results_sorted = orbit_groups[primary_orbit]
    print(f"  Using orbit {primary_orbit} ({len(results_sorted)} scenes)")

    # Find before/after pair bracketing cc_date
    before = None
    after = None
    for scene in results_sorted:
        scene_date = scene.properties.get("startTime", "")[:10]
        if scene_date <= cc_date:
            before = scene
        elif before is not None and after is None:
            after = scene
            break

    # Fallback: use first two if bracketing fails
    if before is None or after is None:
        before, after = results_sorted[0], results_sorted[1]
        print(f"  Warning: could not bracket {cc_date} — using first two scenes.")

    date_before = before.properties["startTime"][:10]
    date_after = after.properties["startTime"][:10]
    print(f"  Selected pair: {date_before} → {date_after}")

    return (
        before.properties["sceneName"],
        after.properties["sceneName"],
        date_before,
        date_after,
    )


def submit_job(hyp3: sdk.HyP3, scene_before: str, scene_after: str, job_name: str):
    """Submit a HyP3 Burst InSAR job. Returns job object."""
    print(f"  Submitting HyP3 job: {job_name}")
    job = hyp3.submit_insar_job(
        granule1=scene_before,
        granule2=scene_after,
        name=job_name,
        looks="10x2",           # 40m resolution
        apply_water_mask=False,
        include_dem=False,
        include_wrapped_phase=False,
    )
    job_id = job.jobs[0].job_id
    print(f"  Job submitted: {job_id}")
    return job


def extract_coherence_at_point(corr_tif: str, lon: float, lat: float) -> float:
    """Extract coherence value at a lat/lon point from the coherence GeoTIFF."""
    import rasterio
    from rasterio.crs import CRS
    from rasterio.transform import rowcol
    from rasterio.warp import transform as warp_transform

    with rasterio.open(corr_tif) as src:
        xs, ys = warp_transform(CRS.from_epsg(4326), src.crs, [lon], [lat])
        row, col = rowcol(src.transform, xs[0], ys[0])
        data = src.read(1)
        h, w = data.shape
        if 0 <= row < h and 0 <= col < w:
            val = float(data[row, col])
            print(f"  Coherence at ({lat:.4f}, {lon:.4f}): {val:.4f}")
            return val
        else:
            print(f"  ERROR: centroid ({lat}, {lon}) outside raster extent")
            return -1.0


def main():
    if not PASSWORD:
        print("ERROR: ASF_EARTHDATA_PASSWORD env var not set.")
        print("Run: set ASF_EARTHDATA_PASSWORD=your_password  (Windows)")
        print("  or export ASF_EARTHDATA_PASSWORD=your_password  (bash)")
        return

    print(f"Connecting to HyP3 as {USERNAME}...")
    hyp3 = sdk.HyP3(username=USERNAME, password=PASSWORD)
    print("Connected.\n")

    submitted_jobs = []

    # --- Phase 1: submit all jobs ---
    for site in SITES:
        print(f"\n{'='*60}")
        print(f"Site: {site['name']} — {site['description']}")
        print(f"{'='*60}")

        site_dir = OUTPUT_DIR / site["name"]
        site_dir.mkdir(exist_ok=True)

        pair = find_scene_pair(
            site["bbox_wkt"],
            site["search_start"],
            site["search_end"],
            site["cc_date"],
        )

        if pair is None:
            print(f"  Skipping {site['name']} — no usable scene pair.")
            continue

        scene_before, scene_after, date_before, date_after = pair

        # Write scene info to file
        (site_dir / "scenes.txt").write_text(
            f"Before: {scene_before}  ({date_before})\n"
            f"After:  {scene_after}  ({date_after})\n"
            f"CC date: {site['cc_date']}\n"
            f"Centroid: {site['centroid_lat']}, {site['centroid_lon']}\n"
        )

        job_name = f"val-{site['name']}-{date_before}-{date_after}"

        try:
            job = submit_job(hyp3, scene_before, scene_after, job_name)
            submitted_jobs.append((site, job, site_dir))
        except Exception as e:
            print(f"  ERROR submitting job: {e}")
            (site_dir / "result.txt").write_text(f"Submission failed: {e}\n")

    if not submitted_jobs:
        print("\nNo jobs submitted. Check scene search results above.")
        return

    # --- Phase 2: wait and download ---
    print(f"\n\nWaiting for {len(submitted_jobs)} HyP3 jobs to complete (1–2 hours)...")
    print("You can safely Ctrl+C and rerun later — jobs continue running on NASA's servers.\n")

    for site, job, site_dir in submitted_jobs:
        print(f"\nWatching job for: {site['name']}")
        try:
            completed_job = hyp3.watch(job)
        except KeyboardInterrupt:
            print("\nInterrupted. Rerun this script to check job status and download results.")
            return

        if completed_job.jobs[0].status_code != "SUCCEEDED":
            msg = completed_job.jobs[0].status_message or "Unknown failure"
            print(f"  FAILED: {msg}")
            (site_dir / "result.txt").write_text(f"Job failed: {msg}\n")
            continue

        print(f"  Succeeded. Downloading files...")
        downloaded = completed_job.download_files(location=str(site_dir))

        # Find coherence file
        corr_files = list(site_dir.rglob("*_corr.tif"))
        print(f"  Files downloaded: {[f.name for f in site_dir.rglob('*')]}")

        if not corr_files:
            print(f"  ERROR: No *_corr.tif found in output.")
            print(f"  Available files: {[f.name for f in site_dir.rglob('*')]}")
            (site_dir / "result.txt").write_text("No coherence file found in HyP3 output.\n")
            continue

        corr_path = str(corr_files[0])
        print(f"  Coherence file: {corr_files[0].name}")

        # Extract coherence at lot centroid
        try:
            coherence = extract_coherence_at_point(
                corr_path,
                site["centroid_lon"],
                site["centroid_lat"],
            )
            delta = coherence - 0.65  # vs proxy baseline
            result_text = (
                f"Site: {site['name']}\n"
                f"CC date: {site['cc_date']}\n"
                f"Coherence at centroid: {coherence:.4f}\n"
                f"Delta vs 0.65 baseline: {delta:+.4f}\n"
                f"Signal: {'CONSTRUCTION DETECTED' if delta < -0.15 else 'WEAK/NO SIGNAL'}\n"
            )
            print(f"\n  RESULT:\n{result_text}")
            (site_dir / "result.txt").write_text(result_text)
        except Exception as e:
            print(f"  ERROR extracting coherence: {e}")
            (site_dir / "result.txt").write_text(f"Extraction failed: {e}\n")

    print("\n\nDone. Open validation_output/*/  in QGIS to inspect the coherence maps.")
    print("Load the *_corr.tif files with a blue-to-red colour ramp (0.0=blue, 1.0=red).")
    print("Construction sites should appear blue/dark (low coherence).")
    print("Stable roads and buildings should appear red/bright (high coherence).")


if __name__ == "__main__":
    main()
