"""Check NSW/AU tile coverage in geotessera registry parquet."""
import pandas as pd

df = pd.read_parquet("C:/Users/lawre/AppData/Local/geotessera/registry.parquet")

# NSW bounding box: lat -29 to -38, lon 147 to 154
au_nsw = df[(df["lat"] >= -38) & (df["lat"] <= -29) & (df["lon"] >= 147) & (df["lon"] <= 154)]
print(f"NSW tiles in registry: {len(au_nsw)}")
print(f"Years covered: {sorted(au_nsw['year'].unique().tolist())}")
print("\nTiles per year:")
for yr, cnt in au_nsw.groupby("year").size().items():
    print(f"  {yr}: {cnt}")

# Marrickville spot check: lat=-33.9139, lon=151.1554
# Tiles are 0.1 degree grid
lat_r = round(-33.9139 / 0.1) * 0.1
lon_r = round(151.1554 / 0.1) * 0.1
marrick = au_nsw[(abs(au_nsw["lat"] - lat_r) < 0.06) & (abs(au_nsw["lon"] - lon_r) < 0.06)]
print(f"\nMarrickville tile ({lat_r:.1f},{lon_r:.1f}): {len(marrick)} rows")
print(f"  Years: {sorted(marrick['year'].unique().tolist())}")
if len(marrick) > 0:
    print(f"  Sample hash: {marrick.iloc[0]['hash']}")
