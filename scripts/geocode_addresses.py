"""
Geocode addresses via NSW Planning Portal API.
Gets propId -> lot geometry -> centroid lat/lng.
No API key needed.
"""
import json, time, requests

ADDRESSES = [
    "65 Elwick St Leichhardt NSW 2040",
    "11 Seale St Leichhardt NSW 2040",
    "9 Seale St Leichhardt NSW 2040",
    "17 Seale St Leichhardt NSW 2040",
    "16 O'Connor St Haberfield NSW 2045",
    "37 O'Connor St Haberfield NSW 2045",
    "2 St Davids Road Haberfield NSW 2045",
    "69 Parramatta Road Haberfield NSW 2045",
    "63 Parramatta Road Haberfield NSW 2045",
    "5 Haberfield Road Haberfield NSW 2045",
    "27 Tressider Avenue Haberfield NSW 2045",
]

BASE = "https://api.apps1.nsw.gov.au/planning/viewersf/V1/ePlanningApi"
HEADERS = {
    "Origin": "https://www.planningportal.nsw.gov.au",
    "Referer": "https://www.planningportal.nsw.gov.au/",
}

def centroid(rings):
    """Compute centroid of first ring of a polygon."""
    ring = rings[0]
    lngs = [c[0] for c in ring]
    lats = [c[1] for c in ring]
    return sum(lats) / len(lats), sum(lngs) / len(lngs)

results = []
for addr in ADDRESSES:
    try:
        # Step 1: address -> propId
        r1 = requests.get(f"{BASE}/address", params={"a": addr, "noOfRecords": 1},
                          headers=HEADERS, timeout=10)
        data1 = r1.json()
        if not data1:
            print(f"NONE {addr}")
            results.append({"address": addr, "error": "no address match"})
            continue
        prop_id = data1[0]["propId"]

        # Step 2: propId -> lot geometry
        r2 = requests.get(f"{BASE}/lot", params={"propId": prop_id},
                          headers=HEADERS, timeout=10)
        data2 = r2.json()
        if not data2:
            print(f"NONE (no lot) {addr}")
            results.append({"address": addr, "prop_id": prop_id, "error": "no lot"})
            continue

        geom = data2[0]["geometry"]
        rings = geom.get("rings") or geom.get("coordinates", [[]])
        lat, lng = centroid(rings)

        results.append({"address": addr, "prop_id": prop_id, "lat": round(lat, 7), "lng": round(lng, 7)})
        print(f"OK   {lat:.6f}, {lng:.6f}  |  {addr}  (propId={prop_id})")

    except Exception as e:
        print(f"ERR  {addr}: {e}")
        results.append({"address": addr, "error": str(e)})

    time.sleep(0.3)

with open("scripts/geocode_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\nSaved: scripts/geocode_results.json")
