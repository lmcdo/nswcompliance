"""Quick Tessera registry check — no tile download, just verify years available."""
import sys
from geotessera import GeoTessera

gt = GeoTessera()
years = sorted(gt.registry.get_available_years())
counts = gt.registry.get_tile_counts_by_year()
print(f"Available years: {years}")
for yr in years:
    print(f"  {yr}: {counts.get(yr, '?')} tiles")

# Check 2017-2025 are all present
required = set(range(2017, 2026))
missing = required - set(years)
if missing:
    print(f"MISSING YEARS: {sorted(missing)}")
else:
    print("ALL years 2017-2025 present in registry")

sys.stdout.flush()
