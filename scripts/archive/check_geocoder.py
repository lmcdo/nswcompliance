import requests, json, math, sys

NSW_API_BASE = "https://api.apps1.nsw.gov.au/planning"
NSW_HEADERS = {
    "Origin": "https://www.planningportal.nsw.gov.au",
    "Referer": "https://www.planningportal.nsw.gov.au/",
}

# Step 1: address → propId
r = requests.get(
    f"{NSW_API_BASE}/viewersf/V1/ePlanningApi/address",
    params={"a": "14 Smith Street Marrickville", "noOfRecords": 1},
    headers=NSW_HEADERS,
    timeout=10)
print(f"Address endpoint status: {r.status_code}")
data = r.json()
print("Full response:")
print(json.dumps(data, indent=2)[:1200])

if data:
    prop_id = data[0].get("propId")
    print(f"\npropId: {prop_id}")
    print(f"Keys in response[0]: {list(data[0].keys())}")

    # Step 2: lot geometry
    lot_r = requests.get(
        f"{NSW_API_BASE}/viewersf/V1/ePlanningApi/lot",
        params={"propId": prop_id},
        headers=NSW_HEADERS,
        timeout=10)
    print(f"\nLot endpoint status: {lot_r.status_code}")
    lots = lot_r.json()
    if lots:
        print(f"Keys in lot[0]: {list(lots[0].keys())}")
        # Convert centroid from EPSG:3857 to WGS84
        ring = lots[0]["geometry"]["rings"][0]
        cx = sum(pt[0] for pt in ring) / len(ring)
        cy = sum(pt[1] for pt in ring) / len(ring)
        R = 20037508.342789244
        lon = cx / R * 180
        lat = math.degrees(2.0 * math.atan(math.exp(cy * math.pi / R)) - math.pi / 2.0)
        print(f"Centroid: lat={lat:.5f} lon={lon:.5f}")
        # Print all lot fields
        for k, v in lots[0].items():
            if k != "geometry":
                print(f"  {k}: {v}")

sys.stdout.flush()
