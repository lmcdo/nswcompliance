"""
Query the NSW Planning Portal ArcGIS services to find all distinct LGA_NAME values
and test whether regional LGAs have data in the key layers.
Uses groupByFieldsForStatistics (COUNT) instead of returnDistinctValues.
"""
import requests

BASE = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning"
HEADERS = {
    "Origin": "https://www.planningportal.nsw.gov.au",
    "Referer": "https://www.planningportal.nsw.gov.au/",
}

def get_distinct_lgas(service, layer_id):
    url = f"{BASE}/{service}/MapServer/{layer_id}/query"
    params = {
        "where": "1=1",
        "outFields": "LGA_NAME",
        "outStatistics": '[{"statisticType":"count","onStatisticField":"LGA_NAME","outStatisticFieldName":"cnt"}]',
        "groupByFieldsForStatistics": "LGA_NAME",
        "returnGeometry": "false",
        "f": "json",
        "resultRecordCount": 500,
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    r.raise_for_status()
    data = r.json()
    features = data.get("features", [])
    names = sorted(
        f["attributes"]["LGA_NAME"]
        for f in features
        if f["attributes"].get("LGA_NAME")
    )
    if not names:
        # fallback: check for error message
        if "error" in data:
            print(f"  ArcGIS error: {data['error']}")
    return names

def count_lga(lga_name, service, layer_id):
    url = f"{BASE}/{service}/MapServer/{layer_id}/query"
    params = {
        "where": f"LGA_NAME='{lga_name}'",
        "outFields": "LGA_NAME",
        "returnCountOnly": "true",
        "f": "json",
    }
    r = requests.get(url, params=params, headers=HEADERS, timeout=30)
    data = r.json()
    return data.get("count", 0)

# ── Zone layer (Principal_Planning_Layers/11) ──────────────────────────────
print("Fetching LGA list from zone layer (Principal_Planning_Layers/11)...")
zone_lgas = get_distinct_lgas("Principal_Planning_Layers", 11)
print(f"  Found {len(zone_lgas)} LGAs")
if zone_lgas:
    print("  Sample:", zone_lgas[:5])
print()

GREATER_SYDNEY = {
    "INNER WEST", "SYDNEY", "KU-RING-GAI", "WAVERLEY", "WOOLLAHRA",
    "BAYSIDE", "BLACKTOWN", "BLUE MOUNTAINS", "BURWOOD", "CAMDEN",
    "CAMPBELLTOWN", "CANADA BAY", "CANTERBURY-BANKSTOWN", "CITY OF PARRAMATTA",
    "CUMBERLAND", "FAIRFIELD", "GEORGES RIVER", "HAWKESBURY", "HORNSBY",
    "HUNTERS HILL", "LANE COVE", "LIVERPOOL", "MOSMAN", "NORTH SYDNEY",
    "NORTHERN BEACHES", "PENRITH", "RANDWICK", "RYDE", "STRATHFIELD",
    "SUTHERLAND SHIRE", "THE HILLS SHIRE", "WILLOUGHBY", "WOLLONDILLY",
}

if zone_lgas:
    regional = [l for l in zone_lgas if l not in GREATER_SYDNEY]
    print(f"Regional LGAs in ArcGIS zone layer ({len(regional)}):")
    for l in regional:
        print(f"  {l}")
    print()

# ── Test flood coverage for key regional LGAs ─────────────────────────────
# Use the Hazard service, layer 1 (flood)
FLOOD_TEST = [
    "LISMORE", "BALLINA", "RICHMOND VALLEY", "LAKE MACQUARIE",
    "NEWCASTLE", "WOLLONGONG", "SHOALHAVEN", "MID-COAST",
    "PORT MACQUARIE-HASTINGS", "TWEED", "COFFS HARBOUR", "MAITLAND",
    "CENTRAL COAST", "CESSNOCK", "SINGLETON",
]

print("Flood layer (Hazard/1) coverage for key regional LGAs:")
for lga in FLOOD_TEST:
    count = count_lga(lga, "Hazard", 1)
    status = f"{count} features" if count > 0 else "NO DATA"
    print(f"  {lga}: {status}")

print()

# ── Test biodiversity coverage ─────────────────────────────────────────────
BIO_LAYER_SERVICE = "Principal_Planning_Layers"
BIO_LAYER_ID = 14  # biodiversity

print("Biodiversity layer coverage for key regional LGAs:")
for lga in ["LISMORE", "BALLINA", "LAKE MACQUARIE", "NEWCASTLE", "WOLLONGONG"]:
    count = count_lga(lga, BIO_LAYER_SERVICE, BIO_LAYER_ID)
    status = f"{count} features" if count > 0 else "NO DATA"
    print(f"  {lga}: {status}")
