"""Download and extract coherence for all 3 Kellyville jobs."""
import os, json, pathlib, zipfile
os.environ.setdefault("ASF_EARTHDATA_USERNAME", "bandylala")
creds = pathlib.Path(__file__).parent / "drawdown_creds.txt"
for line in creds.read_text(encoding="utf-8", errors="replace").splitlines():
    if line.strip() and not line.startswith("#"):
        os.environ["ASF_EARTHDATA_PASSWORD"] = line.strip()
        break

import numpy as np
import hyp3_sdk as sdk
from hyp3_sdk import Batch
import rasterio
from rasterio.crs import CRS
from rasterio.transform import rowcol
from rasterio.warp import transform as warp_transform

CENTROID_LAT = -33.706693
CENTROID_LON = 150.936325

JOBS = [
    ("kellyville-early2024", "a7063991-c00f-4946-a4a2-425ea9437107", "2024-01-11", "2024-01-23"),
    ("kellyville-mid2024",   "d9c82ff4-4d07-47ad-a33b-700d00dfb7df", "2024-06-03", "2024-06-15"),
    ("kellyville-late2024",  "586b8c59-4873-4c4b-bfaf-b8d1bbf0d9e8", "2024-10-01", "2024-10-13"),
]

OUTPUT_BASE = pathlib.Path(__file__).parent.parent / "validation_output" / "kellyville"
OUTPUT_BASE.mkdir(parents=True, exist_ok=True)

hyp3 = sdk.HyP3(username=os.environ["ASF_EARTHDATA_USERNAME"], password=os.environ["ASF_EARTHDATA_PASSWORD"])

results = []

for label, job_id, date_before, date_after in JOBS:
    print(f"\n{'='*55}")
    print(f"{label}  ({date_before} -> {date_after})")
    site_dir = OUTPUT_BASE / label
    site_dir.mkdir(exist_ok=True)

    j = hyp3.get_job_by_id(job_id)

    # Download if not already present
    zip_files = list(site_dir.glob("*.zip"))
    if not zip_files:
        print(f"  Downloading...")
        Batch([j]).download_files(location=str(site_dir))
        zip_files = list(site_dir.glob("*.zip"))

    # Extract
    corr_files = list(site_dir.rglob("*_corr.tif"))
    if not corr_files and zip_files:
        print(f"  Extracting {zip_files[0].name}...")
        with zipfile.ZipFile(zip_files[0]) as zf:
            zf.extractall(str(site_dir))
        corr_files = list(site_dir.rglob("*_corr.tif"))

    if not corr_files:
        print(f"  ERROR: no coherence file found")
        continue

    corr_path = str(corr_files[0])
    print(f"  Coherence file: {corr_files[0].name}")

    with rasterio.open(corr_path) as src:
        data = src.read(1)
        valid = data[data > 0]
        scene_mean = float(valid.mean()) if len(valid) else 0.0
        scene_median = float(np.median(valid)) if len(valid) else 0.0

        # Extract at centroid
        xs, ys = warp_transform(CRS.from_epsg(4326), src.crs, [CENTROID_LON], [CENTROID_LAT])
        row, col = rowcol(src.transform, xs[0], ys[0])
        h, w = data.shape

        if 0 <= row < h and 0 <= col < w:
            centroid_val = float(data[row, col])
            # 3x3 window
            r0, r1 = max(0, row-1), min(h, row+2)
            c0, c1 = max(0, col-1), min(w, col+2)
            window_mean = float(data[r0:r1, c0:c1].mean())
        else:
            centroid_val = -1.0
            window_mean = -1.0
            print(f"  WARNING: centroid outside raster (row={row}, col={col}, shape={h}x{w})")

    print(f"  Scene-wide mean:    {scene_mean:.4f}")
    print(f"  Scene-wide median:  {scene_median:.4f}")
    print(f"  Centroid value:     {centroid_val:.4f}")
    print(f"  3x3 window mean:    {window_mean:.4f}")

    results.append({
        "label": label,
        "dates": f"{date_before} -> {date_after}",
        "scene_mean": round(scene_mean, 4),
        "scene_median": round(scene_median, 4),
        "centroid": round(centroid_val, 4),
        "window_3x3": round(window_mean, 4),
    })

print(f"\n\n{'='*55}")
print("SUMMARY — 21 Martens Circuit, Kellyville")
print(f"{'='*55}")
print(f"{'Window':<25} {'Centroid':>10} {'3x3 mean':>10} {'Scene mean':>12}")
print("-" * 60)
for r in results:
    print(f"{r['label']:<25} {r['centroid']:>10.4f} {r['window_3x3']:>10.4f} {r['scene_mean']:>12.4f}")

if len(results) >= 2:
    vals = [r['window_3x3'] for r in results]
    print(f"\nMin coherence across windows: {min(vals):.4f}  ({results[vals.index(min(vals))]['label']})")
    print(f"Max coherence across windows: {max(vals):.4f}  ({results[vals.index(max(vals))]['label']})")
    spread = max(vals) - min(vals)
    print(f"Spread (max-min): {spread:.4f}")
    if spread > 0.15:
        print(">> Significant variation across windows — suggests active construction in lower-coherence period")
    else:
        print(">> Low variation — site was either stable or consistently disturbed throughout 2024")
