"""
Poll HyP3 jobs from validation_output/jobs.json, download GeoTIFFs when complete,
extract coherence at lot centroid, and write result.txt for each site.

Run any time after drawdown_submit_jobs.py. Safe to re-run — skips already-complete sites.

Usage:
    python scripts/drawdown_poll_results.py [--wait]
    --wait: block until all jobs finish (checks every 60s). Omit to just check current status.
"""

import json
import os
import sys
import time
from pathlib import Path

import hyp3_sdk as sdk
import rasterio
from rasterio.crs import CRS
from rasterio.transform import rowcol
from rasterio.warp import transform as warp_transform

USERNAME = os.environ.get("ASF_EARTHDATA_USERNAME", "bandylala")
PASSWORD = os.environ.get("ASF_EARTHDATA_PASSWORD", "")

if not PASSWORD:
    creds_file = Path(__file__).parent / "drawdown_creds.txt"
    if creds_file.exists():
        for line in creds_file.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.strip() and not line.startswith("#"):
                PASSWORD = line.strip()
                break

if not PASSWORD:
    raise SystemExit("ASF_EARTHDATA_PASSWORD not set and drawdown_creds.txt not found.")

OUTPUT_DIR = Path(__file__).parent.parent / "validation_output"
MANIFEST = OUTPUT_DIR / "jobs.json"
WAIT = "--wait" in sys.argv

if not MANIFEST.exists():
    raise SystemExit(f"No jobs manifest found at {MANIFEST}. Run drawdown_submit_jobs.py first.")

jobs = json.loads(MANIFEST.read_text())

print(f"Connecting to HyP3 as {USERNAME}...")
hyp3 = sdk.HyP3(username=USERNAME, password=PASSWORD)
print(f"HyP3 credits remaining: {hyp3.check_credits()}\n")


def extract_coherence(corr_tif: str, lon: float, lat: float) -> float:
    with rasterio.open(corr_tif) as src:
        xs, ys = warp_transform(CRS.from_epsg(4326), src.crs, [lon], [lat])
        row, col = rowcol(src.transform, xs[0], ys[0])
        data = src.read(1)
        h, w = data.shape
        if 0 <= row < h and 0 <= col < w:
            val = float(data[row, col])
            print(f"    Coherence at ({lat:.4f}, {lon:.4f}): {val:.4f}")
            return val
        else:
            print(f"    ERROR: centroid ({lat}, {lon}) outside raster extent")
            print(f"    Raster shape: {h}x{w}, attempted row={row} col={col}")
            return -1.0


def process_job(j: dict) -> None:
    site = j["site"]
    site_dir = OUTPUT_DIR / site
    result_file = site_dir / "result.txt"

    # Skip if already processed
    if result_file.exists():
        existing = result_file.read_text()
        if "Coherence at centroid" in existing or "FAILED" in existing:
            print(f"  {site}: already processed (result.txt exists) -- skipping")
            return

    job_ids = j.get("job_ids", [])
    if not job_ids:
        print(f"  {site}: no job IDs recorded (submission may have failed)")
        return

    job_id = job_ids[0]
    print(f"  {site}: checking job {job_id}")

    # Get current job status
    try:
        jj = hyp3.get_job_by_id(job_id)
    except Exception as e:
        print(f"    Could not fetch job: {e}")
        return
    status = jj.status_code
    print(f"    Status: {status}")

    if status == "RUNNING" or status == "PENDING":
        print(f"    Still running. Re-run this script later (or use --wait).")
        return

    if status == "FAILED":
        msg = getattr(jj, "status_message", "Unknown failure")
        print(f"    FAILED: {msg}")
        result_file.write_text(f"FAILED: {msg}\n")
        return

    if status != "SUCCEEDED":
        print(f"    Unexpected status: {status}")
        return

    # Download files
    print(f"    Downloading output files...")
    site_dir.mkdir(exist_ok=True)

    try:
        batch_obj = hyp3_sdk_batch_for_job(hyp3, jj)
        batch_obj.download_files(location=str(site_dir))
    except Exception as e:
        print(f"    Download error: {e}")
        # Try alternative download approach
        try:
            files = jj.files
            print(f"    Available files: {[f.get('filename') for f in files]}")
            for f in files:
                url = f.get("url")
                fname = f.get("filename")
                if url and fname:
                    import urllib.request
                    dest = site_dir / fname
                    if not dest.exists():
                        print(f"    Downloading {fname}...")
                        urllib.request.urlretrieve(url, str(dest))
        except Exception as e2:
            print(f"    Alternative download also failed: {e2}")
            return

    # List all downloaded files
    all_files = list(site_dir.rglob("*"))
    print(f"    Downloaded files: {[f.name for f in all_files if f.is_file()]}")

    # Find coherence file
    corr_files = list(site_dir.rglob("*_corr.tif"))
    if not corr_files:
        # Try zip — HyP3 sometimes delivers a zip
        zip_files = list(site_dir.rglob("*.zip"))
        if zip_files:
            import zipfile
            print(f"    Extracting zip: {zip_files[0].name}")
            with zipfile.ZipFile(zip_files[0]) as zf:
                zf.extractall(str(site_dir))
            corr_files = list(site_dir.rglob("*_corr.tif"))

    if not corr_files:
        print(f"    ERROR: no *_corr.tif found.")
        print(f"    All files: {[f.name for f in site_dir.rglob('*') if f.is_file()]}")
        result_file.write_text("ERROR: no coherence file found in HyP3 output.\n")
        return

    corr_path = str(corr_files[0])
    print(f"    Coherence file: {corr_files[0].name}")

    # Extract coherence at lot centroid
    lon = j["centroid_lon"]
    lat = j["centroid_lat"]
    coherence_after = extract_coherence(corr_path, lon, lat)

    coherence_before = 0.65  # proxy baseline (known limitation)
    delta = coherence_after - coherence_before

    if delta <= -0.30:
        signal = "STRONG CONSTRUCTION SIGNAL"
    elif delta <= -0.15:
        signal = "MODERATE SIGNAL"
    else:
        signal = "WEAK/NO SIGNAL"

    result = (
        f"Site: {site}\n"
        f"Scene pair: {j['date_before']} -> {j['date_after']}\n"
        f"Centroid: {lat}, {lon}\n"
        f"Coherence (proxy baseline): {coherence_before:.4f}\n"
        f"Coherence (measured after): {coherence_after:.4f}\n"
        f"Delta: {delta:+.4f}\n"
        f"Signal: {signal}\n"
        f"Note: these are PLACEHOLDER sites, not verified construction addresses.\n"
        f"      Signal result is for pipeline testing, not accuracy validation.\n"
    )
    print(f"\n    RESULT:\n{result}")
    result_file.write_text(result)


def hyp3_sdk_batch_for_job(hyp3_client, job_obj):
    """Wrap a single job into a batch-like object for download_files."""
    from hyp3_sdk import Batch
    return Batch([job_obj])


# --- Main ---
if WAIT:
    print("--wait mode: polling every 60s until all jobs complete...\n")

all_done = False
while not all_done:
    all_done = True
    for j in jobs:
        if "error" in j:
            print(f"  {j['site']}: submission failed earlier ({j['error']})")
            continue
        process_job(j)

    if WAIT:
        # Check if any are still running
        manifest_fresh = json.loads(MANIFEST.read_text())
        still_running = []
        for j in manifest_fresh:
            result_file = OUTPUT_DIR / j["site"] / "result.txt"
            if not result_file.exists():
                still_running.append(j["site"])
        if still_running:
            all_done = False
            print(f"\nStill waiting for: {still_running}")
            print("Sleeping 60s...\n")
            time.sleep(60)
    else:
        break

print("\nDone. Re-run with --wait to block until complete, or open validation_output/ in QGIS.")
print("Load *_corr.tif with a 0-1 colour ramp (blue=low coherence, red=high).")
