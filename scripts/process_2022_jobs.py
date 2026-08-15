"""Download and extract coherence for the 2022 Kellyville jobs."""
import os, pathlib, zipfile
os.environ.setdefault("ASF_EARTHDATA_USERNAME", "bandylala")
creds = pathlib.Path(__file__).parent / "drawdown_creds.txt"
for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.strip() and not line.startswith("#"):
        os.environ["ASF_EARTHDATA_PASSWORD"] = line.strip()
        break

import numpy as np, hyp3_sdk as sdk
from hyp3_sdk import Batch
import rasterio
from rasterio.crs import CRS
from rasterio.transform import rowcol
from rasterio.warp import transform as warp_transform

# Real lot centroid from NSW Planning Portal
CENTROID_LAT = -33.707407
CENTROID_LON = 150.936039

JOBS = [
    ("kellyville-2022jul",  "2296ffb5-8811-4ea5-ae79-536be0a11483", "2022-07-08", "2022-07-20"),
    ("kellyville-2022aug",  "4cf73e66-c52c-4e7a-afea-9d53f4418885", "2022-07-20", "2022-08-01"),
    ("kellyville-2022aug2", "c769fe7d-fa59-443f-94b1-22f059e06b8f", "2022-08-01", "2022-08-13"),
]

OUTPUT_BASE = pathlib.Path(__file__).parent.parent / "validation_output" / "kellyville_2022"
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

hyp3 = sdk.HyP3(username=os.environ["ASF_EARTHDATA_USERNAME"], password=os.environ["ASF_EARTHDATA_PASSWORD"])

all_results = []

# Also include 2024 results for comparison
PRIOR = [
    ("kellyville-early2024", 0.8989, "2024-01-11->2024-01-23"),
    ("kellyville-mid2024",   0.9769, "2024-06-03->2024-06-15"),
    ("kellyville-late2024",  0.9594, "2024-10-01->2024-10-13"),
]

for label, job_id, date_before, date_after in JOBS:
    print(f"\n{'='*55}")
    print(f"{label}  ({date_before} -> {date_after})")
    site_dir = OUTPUT_BASE / label
    site_dir.mkdir(exist_ok=True)

    j = hyp3.get_job_by_id(job_id)
    zip_files = list(site_dir.glob("*.zip"))
    if not zip_files:
        print(f"  Downloading...")
        Batch([j]).download_files(location=str(site_dir))
        zip_files = list(site_dir.glob("*.zip"))

    corr_files = list(site_dir.rglob("*_corr.tif"))
    if not corr_files and zip_files:
        print(f"  Extracting...")
        with zipfile.ZipFile(zip_files[0]) as zf:
            zf.extractall(str(site_dir))
        corr_files = list(site_dir.rglob("*_corr.tif"))

    if not corr_files:
        print(f"  ERROR: no coherence file")
        continue

    with rasterio.open(str(corr_files[0])) as src:
        data = src.read(1)
        valid = data[data > 0]
        xs, ys = warp_transform(CRS.from_epsg(4326), src.crs, [CENTROID_LON], [CENTROID_LAT])
        row, col = rowcol(src.transform, xs[0], ys[0])
        h, w = data.shape
        if 0 <= row < h and 0 <= col < w:
            centroid_val = float(data[row, col])
            r0,r1 = max(0,row-1), min(h,row+2)
            c0,c1 = max(0,col-1), min(w,col+2)
            window = float(data[r0:r1,c0:c1].mean())
        else:
            centroid_val = window = -1.0
            print(f"  WARNING: centroid outside raster")

    print(f"  Centroid:    {centroid_val:.4f}")
    print(f"  3x3 window:  {window:.4f}")
    all_results.append((label, f"{date_before}->{date_after}", centroid_val, window))

print(f"\n\n{'='*65}")
print("FULL TIMELINE — 21 Martens Circuit, Kellyville")
print(f"Real lot centroid: {CENTROID_LAT}, {CENTROID_LON} (NSW Planning Portal)")
print(f"{'='*65}")
print(f"{'Window':<28} {'Period':<22} {'Centroid':>9} {'3x3 mean':>9}")
print("-"*70)

for label, dates, prior_window in PRIOR:
    print(f"{label:<28} {dates:<22} {'':>9} {prior_window:>9}  [2024 — completed]")

for label, dates, centroid, window in all_results:
    flag = "  << CONSTRUCTION?" if window < 0.6 else ""
    print(f"{label:<28} {dates:<22} {centroid:>9.4f} {window:>9.4f}{flag}")

print()
windows_2022 = [w for _, _, _, w in all_results if w > 0]
if windows_2022:
    print(f"2022 range: {min(windows_2022):.4f} – {max(windows_2022):.4f}")
    print(f"2024 range: 0.8989 – 0.9769  (stable completed structure)")
    drop = 0.9394 - min(windows_2022)  # vs 2024 mean
    print(f"Drop vs 2024 mean (0.9394): {drop:+.4f}")
    if min(windows_2022) < 0.65:
        print("\nSIGNAL DETECTED: coherence < 0.65 in 2022 window")
        print("Construction was active at this site during this period.")
    elif min(windows_2022) < 0.80:
        print("\nWEAK SIGNAL: coherence 0.65-0.80, moderate disturbance")
    else:
        print("\nNO SIGNAL: coherence stable in 2022 — construction may have been earlier")
        print("Try 2021 H2 or 2022 H1 window.")
