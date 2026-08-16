"""Download and extract coherence for the Tallawong 2023 jobs."""
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

# NSW Planning Portal exact lot centroid for 5 Marwan Ave Tallawong
CENTROID_LAT = -33.690398
CENTROID_LON = 150.888235

JOBS = [
    ("tallawong-2023jul-a", "44745b41-9020-453d-95d3-6e023cb47054", "2023-07-03", "2023-07-15"),
    ("tallawong-2023jul-b", "fae75b19-1593-4d43-87b9-4d30bc903a15", "2023-07-15", "2023-07-27"),
    ("tallawong-2023aug",   "ac30786c-479f-44ae-9dab-c217480aa6d2", "2023-07-27", "2023-08-08"),
    ("tallawong-2024feb-a", "8eb536ab-0eb9-4a83-bf63-284825f07ced", "2024-02-04", "2024-02-16"),
    ("tallawong-2024feb-b", "2b83f392-6d5d-480c-9172-34df73bd89ca", "2024-02-16", "2024-02-28"),
    ("tallawong-2024mar",   "39e2566f-828b-4f0d-8747-480c31da4004", "2024-02-28", "2024-03-11"),
]

OUTPUT_BASE = pathlib.Path(__file__).parent.parent / "validation_output" / "tallawong_2023"
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

hyp3 = sdk.HyP3(username=os.environ["ASF_EARTHDATA_USERNAME"], password=os.environ["ASF_EARTHDATA_PASSWORD"])

all_results = []

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
        xs, ys = warp_transform(CRS.from_epsg(4326), src.crs, [CENTROID_LON], [CENTROID_LAT])
        row, col = rowcol(src.transform, xs[0], ys[0])
        h, w = data.shape
        if 0 <= row < h and 0 <= col < w:
            centroid_val = float(data[row, col])
            r0, r1 = max(0, row-1), min(h, row+2)
            c0, c1 = max(0, col-1), min(w, col+2)
            window = float(data[r0:r1, c0:c1].mean())
        else:
            centroid_val = window = -1.0
            print(f"  WARNING: centroid outside raster")

    print(f"  Centroid:    {centroid_val:.4f}")
    print(f"  3x3 window:  {window:.4f}")
    all_results.append((label, f"{date_before}->{date_after}", centroid_val, window))

print(f"\n\n{'='*65}")
print("TALLAWONG VALIDATION — 5 Marwan Avenue Tallawong NSW 2762")
print(f"Lot centroid: {CENTROID_LAT}, {CENTROID_LON} (NSW Planning Portal)")
print(f"DA determined: 2024-01-05  |  DevelopmentType: Dwelling house / Erection of new structure")
print(f"{'='*65}")
print(f"{'Window':<28} {'Period':<22} {'Centroid':>9} {'3x3 mean':>9}")
print("-"*72)

for label, dates, centroid, window in all_results:
    flag = "  << CONSTRUCTION SIGNAL" if window < 0.65 else ("  << WEAK SIGNAL" if window < 0.80 else "")
    print(f"{label:<28} {dates:<22} {centroid:>9.4f} {window:>9.4f}{flag}")

print()
windows = [w for _, _, _, w in all_results if w > 0]
if windows:
    print(f"Range: {min(windows):.4f} - {max(windows):.4f}")
    kellyville_mean = 0.9394
    print(f"Kellyville 2024 baseline (completed): {kellyville_mean:.4f}")
    print(f"Drop vs baseline: {kellyville_mean - min(windows):+.4f}")
    if min(windows) < 0.65:
        print("\nSIGNAL CONFIRMED: coherence < 0.65 during construction window.")
        print("Step 2 go/no-go gate: PASSED")
    elif min(windows) < 0.80:
        print("\nWEAK SIGNAL: coherence 0.65-0.80. Partial disturbance detected.")
        print("Step 2 gate: MARGINAL - try windows closer to slab/frame stages.")
    else:
        print("\nNO SIGNAL: coherence stable. Construction may not have started yet.")
        print("Try earlier windows (2022 H2) or a different site.")
