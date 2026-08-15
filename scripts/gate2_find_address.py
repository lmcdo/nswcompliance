"""Find a good Gate 2 test address — Inner West DA in a covered Tessera tile."""
import sys, os, json, requests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'services'))
import pre_da_history as m
import pandas as pd

# Covered tiles in Inner West: (-33.95, 151.15) and (-33.95, 151.25)
# These cover roughly: Marrickville, Dulwich Hill, St Peters, Newtown, Erskineville

# Fetch Inner West DAs, filter to addresses in the covered lat range
print("Fetching Inner West DAs...")
batch = m._fetch_eplanning_page(
    "OnlineDA",
    {"CouncilName": ["Inner West Council"], "ApplicationType": "Development Application"},
    1
)
print(f"Got {len(batch)} records")

# Filter to covered tile area: lat between -33.9 and -34.05, lon between 151.1 and 151.35
candidates = []
for rec in batch:
    flat = m._extract_da_fields(rec)
    lat, lon = flat.get('lat'), flat.get('lon')
    if lat and lon and -34.05 < lat < -33.90 and 151.10 < lon < 151.35:
        yr = flat.get('date_updated', '')[:4]
        candidates.append({**flat, 'year': yr})

print(f"\nAddresses in covered tile area ({len(candidates)} of {len(batch)}):")
for c in candidates[:10]:
    print(f"  {c['pan']:15}  {c['year']}  {c['address']}")
    print(f"           lat={c['lat']:.4f}  lon={c['lon']:.4f}  type={c['dev_type']!r}")

# Also check registry for specific coverage
df = pd.read_parquet("C:/Users/lawre/AppData/Local/geotessera/registry.parquet")

print("\n\nVerifying tile coverage for candidate addresses:")
for c in candidates[:5]:
    lat, lon = c['lat'], c['lon']
    nearby = df[
        (abs(df['lat'] - lat) < 0.08) &
        (abs(df['lon'] - lon) < 0.08)
    ]
    years = sorted(nearby['year'].unique().tolist())
    print(f"  {c['address'][:45]:45}  tiles: {years}")
