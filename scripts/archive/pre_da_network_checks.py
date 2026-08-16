"""Fast network checks only — no tile downloads."""
import requests, json, math, re

# ── 1. Wayback releases ────────────────────────────────────────────────────
print("=== Wayback releases ===")
r = requests.get(
    "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/MapServer",
    params={"f": "json"}, timeout=20,
)
releases_raw = r.json().get("Selection", [])
print(f"Total releases: {len(releases_raw)}")

def parse_date(name):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", name)
    return m.group(1) if m else ""

releases = sorted(
    [{"M": x["M"], "date": parse_date(x["Name"])} for x in releases_raw],
    key=lambda x: x["date"]
)
print(f"Earliest: {releases[0]}")
print(f"Latest:   {releases[-1]}")
in_range = [x for x in releases if "2017" <= x["date"][:4] <= "2025"]
pre2020   = [x for x in in_range if x["date"][:4] <= "2019"]
print(f"Releases 2017-2025: {len(in_range)}")
print(f"Pre-2020 releases ({len(pre2020)}): {pre2020}")

# ── 2. Wayback tile test ───────────────────────────────────────────────────
print("\n=== Wayback tile test (Marrickville) ===")
lat, lon, zoom = -33.9139, 151.1554, 19
n = 2**zoom
tx = int((lon+180)/360*n)
ty = int((1 - math.asinh(math.tan(math.radians(lat)))/math.pi)/2*n)
TILE = "https://wayback.maptiles.arcgis.com/arcgis/rest/services/World_Imagery/WMTS/1.0.0/default028mm/MapServer/tile/{M}/{z}/{y}/{x}"

for rel in ([pre2020[0]] if pre2020 else []) + ([in_range[-1]] if in_range else []):
    url = TILE.format(M=rel["M"], z=zoom, y=ty, x=tx)
    tr = requests.get(url, timeout=10)
    print(f"  M={rel['M']} ({rel['date']})  status={tr.status_code}  size={len(tr.content)}b  type={tr.headers.get('Content-Type','')[:25]}")

# ── 3. ePlanning API unauthenticated ──────────────────────────────────────
print("\n=== ePlanning API (no auth) ===")
dr = requests.get(
    "https://api.apps1.nsw.gov.au/eplanning/data/v0/OnlineDA",
    headers={
        "filters": json.dumps({"CouncilName": "Inner West Council", "LodgementDateFrom": "2023-01-01"}),
        "PageSize": "3", "PageNumber": "1", "Cache-Control": "no-cache",
    },
    timeout=15,
)
print(f"Status: {dr.status_code}")
apps = dr.json().get("Application") or dr.json().get("ApplicationList") or []
print(f"Applications returned: {len(apps)}")
if apps:
    a = apps[0]
    print(f"Fields: {list(a.keys())}")
    print(f"Has X/Y: {'X' in a and 'Y' in a}")
    print(f"Address: {a.get('Address')}")
    print(f"LodgementDate: {a.get('LodgementDate')}")
    print(f"DevelopmentType: {a.get('DevelopmentType')}")

# ── 4. geotessera registry only (no tile download) ────────────────────────
print("\n=== geotessera registry ===")
try:
    from geotessera import GeoTessera
    gt = GeoTessera()
    years = sorted(gt.registry.get_available_years())
    print(f"Available years: {years}")
    counts = gt.registry.get_tile_counts_by_year()
    for yr in years:
        print(f"  {yr}: {counts.get(yr, '?')} tiles globally")
except Exception as e:
    print(f"geotessera error: {e}")
