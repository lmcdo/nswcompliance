"""Extract zip, find coherence file, read values at centroid and surrounding area."""
import zipfile, pathlib, urllib.request

OUTPUT = pathlib.Path(__file__).parent.parent / "validation_output" / "inner_west"
zip_files = list(OUTPUT.glob("*.zip"))
print(f"Zip files: {[z.name for z in zip_files]}")

# Extract
zf = zip_files[0]
with zipfile.ZipFile(zf) as z:
    names = z.namelist()
    print(f"Contents ({len(names)} files):")
    for n in names:
        print(f"  {n}")
    z.extractall(str(OUTPUT))

# Find coherence file
corr_files = list(OUTPUT.rglob("*corr*"))
print(f"\nCoherence files: {[f.name for f in corr_files]}")

all_tifs = list(OUTPUT.rglob("*.tif"))
print(f"All TIFs: {[f.name for f in all_tifs]}")

# Read coherence at placeholder centroid + wider area stats
import rasterio
import numpy as np
from rasterio.crs import CRS
from rasterio.warp import transform as warp_transform
from rasterio.transform import rowcol

centroid_lon = 151.150
centroid_lat = -33.894

for tif in corr_files:
    print(f"\n--- {tif.name} ---")
    with rasterio.open(str(tif)) as src:
        print(f"  CRS: {src.crs}")
        print(f"  Shape: {src.width}x{src.height} px")
        print(f"  Bounds: {src.bounds}")
        data = src.read(1)
        valid = data[data > 0]
        print(f"  Valid pixels: {len(valid)}")
        if len(valid) > 0:
            print(f"  Min: {valid.min():.4f}  Max: {valid.max():.4f}  Mean: {valid.mean():.4f}  Median: {np.median(valid):.4f}")

        # Extract at centroid
        try:
            xs, ys = warp_transform(CRS.from_epsg(4326), src.crs, [centroid_lon], [centroid_lat])
            row, col = rowcol(src.transform, xs[0], ys[0])
            h, w = data.shape
            if 0 <= row < h and 0 <= col < w:
                val = float(data[row, col])
                print(f"  Centroid value: {val:.4f}")
                # 3x3 window mean
                r0, r1 = max(0, row-1), min(h, row+2)
                c0, c1 = max(0, col-1), min(w, col+2)
                window = data[r0:r1, c0:c1]
                print(f"  3x3 window mean: {window.mean():.4f}")
            else:
                print(f"  Centroid outside raster (row={row}, col={col}, shape={h}x{w})")
        except Exception as e:
            print(f"  Centroid extraction failed: {e}")

# Fetch failure log for parramatta
print("\n\n--- Parramatta failure log ---")
log_url = "https://d3gm2hf49xd6jj.cloudfront.net/a01d59d4-9372-412e-909a-1da798e07eee/a01d59d4-9372-412e-909a-1da798e07eee.log"
try:
    with urllib.request.urlopen(log_url, timeout=10) as r:
        log = r.read().decode("utf-8", errors="replace")
        # Print last 3000 chars (errors are at the end)
        print(log[-3000:])
except Exception as e:
    print(f"Could not fetch log: {e}")
