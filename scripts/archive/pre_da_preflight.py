"""Pre-DA Site History Report — preflight checks."""
import requests
import json
import math

# ── 1. Wayback releases ────────────────────────────────────────────────────
print("=== Wayback releases ===")
r = requests.get(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer",
    params={"f": "json"},
    timeout=20,
)
data = r.json()
releases = data.get("Selection", [])
print(f"Total releases: {len(releases)}")

# Parse dates from Name field: "World Imagery (Wayback 2022-03-15)" -> "2022-03-15"
def parse_date(name):
    import re
    m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else ""

releases_parsed = [
    {"M": r["M"], "ID": r["ID"], "date": parse_date(r["Name"]), "name": r["Name"]}
    for r in releases
]
releases_parsed.sort(key=lambda x: x["date"])

print(f"Earliest: {releases_parsed[0]}")
print(f"Latest:   {releases_parsed[-1]}")

in_range = [x for x in releases_parsed if "2017" <= x["date"][:4] <= "2025"]
print(f"\nReleases 2017-2025: {len(in_range)}")
pre2020 = [x for x in in_range if x["date"][:4] <= "2019"]
print(f"Pre-2020 releases ({len(pre2020)}):")
for x in pre2020:
    print(f"  M={x['M']}  {x['date']}")

# ── 2. Wayback tile test — Marrickville inner Sydney ──────────────────────
print("\n=== Wayback tile test (Marrickville -33.9139, 151.1554) ===")
lat, lon, zoom = -33.9139, 151.1554, 19
n = 2 ** zoom
tx = int((lon + 180.0) / 360.0 * n)
lat_rad = math.radians(lat)
ty = int((1.0 - math.asinh(math.tan(lat_rad)) / math.pi) / 2.0 * n)
TILE = "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/{M}/{z}/{y}/{x}"

# Test earliest in range, a mid-range, and latest
test_releases = []
if pre2020:
    test_releases.append(pre2020[0])
if in_range:
    mid = in_range[len(in_range)//2]
    test_releases.append(mid)
    test_releases.append(in_range[-1])

for rel in test_releases:
    url = TILE.format(M=rel["M"], z=zoom, y=ty, x=tx)
    tr = requests.get(url, timeout=10)
    ct = tr.headers.get("Content-Type", "")
    print(f"  M={rel['M']} ({rel['date']})  status={tr.status_code}  size={len(tr.content)}b  type={ct[:30]}")

# ── 3. ePlanning API — unauthenticated ─────────────────────────────────────
print("\n=== ePlanning API (no auth) ===")
DA_URL = "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA"
headers = {
    "filters": json.dumps({"CouncilName": "Inner West Council", "LodgementDateFrom": "2023-01-01"}),
    "PageSize": "3",
    "PageNumber": "1",
    "Cache-Control": "no-cache",
}
dr = requests.get(DA_URL, headers=headers, timeout=15)
print(f"Status: {dr.status_code}")
if dr.status_code == 200:
    apps = dr.json().get("Application") or dr.json().get("ApplicationList") or []
    print(f"Applications returned: {len(apps)}")
    if apps:
        a = apps[0]
        print(f"Fields: {list(a.keys())}")
        print(f"Address: {a.get('Address')}")
        print(f"Has X/Y: {'X' in a and 'Y' in a}")
        print(f"LodgementDate: {a.get('LodgementDate')}")
        print(f"DevelopmentType: {a.get('DevelopmentType')}")
else:
    print(f"Response: {dr.text[:200]}")

# ── 4. geotessera ─────────────────────────────────────────────────────────
print("\n=== geotessera ===")
try:
    from geotessera import GeoTessera
    gt = GeoTessera()
    years = gt.registry.get_available_years()
    print(f"Available years: {sorted(years)}")
    counts = gt.registry.get_tile_counts_by_year()
    # Filter to years in range
    for yr in sorted(years):
        print(f"  {yr}: {counts.get(yr, '?')} tiles globally")
except Exception as e:
    print(f"geotessera error: {e}")

# ── 5. Quick AU coverage spot-check ───────────────────────────────────────
print("\n=== Tessera AU spot-check (Marrickville centroid) ===")
try:
    import numpy as np
    from geotessera import GeoTessera
    gt = GeoTessera()
    pts = [(-33.9139, 151.1554)]  # (lat, lon) — geotessera wants lon,lat tuples
    pts_lonlat = [(151.1554, -33.9139)]
    emb = gt.sample_embeddings_at_points(pts_lonlat, year=2023)
    if emb is not None and not np.isnan(emb).all():
        print(f"2023 embedding shape: {emb.shape}  mean: {emb.mean():.4f}  any NaN: {np.isnan(emb).any()}")
    else:
        print("2023 embedding: NaN / missing")
    # Check 2017
    emb17 = gt.sample_embeddings_at_points(pts_lonlat, year=2017)
    if emb17 is not None and not np.isnan(emb17).all():
        print(f"2017 embedding shape: {emb17.shape}  mean: {emb17.mean():.4f}  any NaN: {np.isnan(emb17).any()}")
        # Cosine sim 2017 vs 2023
        e1 = emb17[0]; e2 = emb[0]
        sim = float(np.dot(e1, e2) / (np.linalg.norm(e1) * np.linalg.norm(e2)))
        print(f"Cosine similarity 2017 vs 2023: {sim:.4f}")
    else:
        print("2017 embedding: NaN / missing")
except Exception as e:
    print(f"Tessera spot-check error: {e}")
