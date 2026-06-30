"""Sample Leichhardt addresses to analyze precinct patterns"""
import requests
import psycopg2
import json

BASE_URL = "http://localhost:3007"

# Comprehensive list of Leichhardt LGA addresses across different suburbs and areas
LEICHHARDT_ADDRESSES = [
    # Leichhardt suburb - various streets
    "10 Norton Street Leichhardt 2040",
    "25 Marion Street Leichhardt 2040",
    "150 Balmain Road Leichhardt 2040",
    "5 Wetherill Street Leichhardt 2040",
    "100 Parramatta Road Leichhardt 2040",
    "45 Flood Street Leichhardt 2040",
    "8 Carlisle Street Leichhardt 2040",

    # Balmain
    "10 Darling Street Balmain 2041",
    "55 Beattie Street Balmain 2041",
    "120 Victoria Road Balmain 2041",
    "25 Mort Street Balmain 2041",
    "8 Thames Street Balmain 2041",

    # Balmain East
    "5 Nicholson Street Balmain East 2041",
    "15 Thornton Street Balmain East 2041",

    # Birchgrove
    "20 Louisa Road Birchgrove 2041",
    "10 Grove Street Birchgrove 2041",

    # Rozelle
    "100 Victoria Road Rozelle 2039",
    "50 Darling Street Rozelle 2039",
    "15 Terry Street Rozelle 2039",
    "200 Balmain Road Rozelle 2039",

    # Lilyfield
    "25 Perry Street Lilyfield 2040",
    "10 Cecily Street Lilyfield 2040",
    "50 Lilyfield Road Lilyfield 2040",

    # Annandale
    "100 Johnston Street Annandale 2038",
    "50 Booth Street Annandale 2038",
    "25 Nelson Street Annandale 2038",
    "150 Parramatta Road Annandale 2038",

    # Stanmore (partially in Leichhardt LGA)
    "100 Parramatta Road Stanmore 2048",

    # Summer Hill (partially in Leichhardt LGA)
    "50 Lackey Street Summer Hill 2130",

    # Lewisham
    "25 Old Canterbury Road Lewisham 2049",
    "10 Lewisham Street Lewisham 2049",
]

def fetch_property(address):
    """Fetch property data from API"""
    try:
        resp = requests.get(
            f"{BASE_URL}/api/property",
            params={"address": address},
            timeout=30
        )
        if resp.status_code == 200:
            result = resp.json()
            if result.get("success") and result.get("data"):
                return result["data"]
        return None
    except Exception as e:
        return None

def main():
    print("=" * 70)
    print("LEICHHARDT PRECINCT PATTERN ANALYSIS")
    print("=" * 70)

    # Connect to database for precinct boundary info
    conn = psycopg2.connect('postgresql://postgres@127.0.0.1:5432/nsw_planning')
    cur = conn.cursor()

    # First, check what precincts exist in database
    print("\n### DATABASE: Leichhardt Precinct Boundaries ###")
    cur.execute("""
        SELECT precinct_id, precinct_name, lga, former_council
        FROM dcp_precinct_boundaries
        WHERE former_council ILIKE '%Leichhardt%'
        ORDER BY precinct_id
    """)
    db_precincts = cur.fetchall()
    print(f"\nFound {len(db_precincts)} precincts in database:")
    for p in db_precincts:
        print(f"  {p[0]}: {p[1]} ({p[2]})")

    # Check precinct requirements
    print("\n### DATABASE: Leichhardt Precinct Requirements ###")
    cur.execute("""
        SELECT precinct_id, COUNT(*) as req_count
        FROM dcp_precinct_requirements
        WHERE precinct_id IN (
            SELECT precinct_id FROM dcp_precinct_boundaries
            WHERE former_council ILIKE '%Leichhardt%'
        )
        GROUP BY precinct_id
        ORDER BY precinct_id
    """)
    precinct_reqs = cur.fetchall()
    print(f"\nFound requirements for {len(precinct_reqs)} precincts:")
    for p in precinct_reqs:
        print(f"  {p[0]}: {p[1]} requirements")

    # Now test addresses
    print("\n" + "=" * 70)
    print("### API TESTS: Address -> Precinct Mapping ###")
    print("=" * 70)

    results = []
    precinct_stats = {}
    zone_stats = {}
    suburb_stats = {}

    for i, addr in enumerate(LEICHHARDT_ADDRESSES, 1):
        print(f"\n[{i}/{len(LEICHHARDT_ADDRESSES)}] {addr}")

        data = fetch_property(addr)
        if not data:
            print("  [X] API failed or no data")
            results.append({
                "address": addr,
                "success": False,
                "error": "API failed"
            })
            continue

        constraints = data.get("constraints") or {}
        coords = data.get("coordinates") or {}

        zone = constraints.get("zone") or "Unknown"
        zone_desc = data.get("zoneDescription") or ""
        lga = constraints.get("lga") or "Unknown"
        former_council = constraints.get("formerCouncil") or "Unknown"
        precinct_id = constraints.get("precinctId") or "None"
        heritage = constraints.get("heritage", False)

        # Extract suburb from address
        parts = addr.split()
        suburb = parts[-2] if len(parts) >= 2 else "Unknown"

        print(f"  Zone: {zone} ({zone_desc})")
        print(f"  LGA: {lga}")
        print(f"  Former Council: {former_council}")
        print(f"  Precinct ID: {precinct_id}")
        print(f"  Heritage: {heritage}")
        print(f"  Coords: {coords.get('lat')}, {coords.get('lon')}")

        results.append({
            "address": addr,
            "suburb": suburb,
            "success": True,
            "zone": zone,
            "zone_desc": zone_desc,
            "lga": lga,
            "former_council": former_council,
            "precinct_id": precinct_id,
            "heritage": heritage,
            "lat": coords.get("lat"),
            "lon": coords.get("lon")
        })

        # Stats
        precinct_stats[precinct_id] = precinct_stats.get(precinct_id, 0) + 1
        zone_stats[zone] = zone_stats.get(zone, 0) + 1
        suburb_stats[suburb] = suburb_stats.get(suburb, 0) + 1

    # Summary
    print("\n" + "=" * 70)
    print("### SUMMARY ###")
    print("=" * 70)

    success_count = sum(1 for r in results if r.get("success"))
    leichhardt_count = sum(1 for r in results if r.get("former_council") == "Leichhardt")

    print(f"\nTotal addresses tested: {len(results)}")
    print(f"Successful API calls: {success_count}")
    print(f"Detected as Leichhardt: {leichhardt_count}")

    print(f"\n### Precinct Distribution ###")
    for precinct, count in sorted(precinct_stats.items(), key=lambda x: -x[1]):
        print(f"  {precinct}: {count} addresses")

    print(f"\n### Zone Distribution ###")
    for zone, count in sorted(zone_stats.items(), key=lambda x: -x[1]):
        print(f"  {zone}: {count} addresses")

    print(f"\n### Suburb Distribution ###")
    for suburb, count in sorted(suburb_stats.items(), key=lambda x: -x[1]):
        print(f"  {suburb}: {count} addresses")

    # Identify patterns
    print("\n" + "=" * 70)
    print("### PATTERN ANALYSIS ###")
    print("=" * 70)

    # Group by precinct and show zones
    precinct_zones = {}
    for r in results:
        if r.get("success"):
            pid = r.get("precinct_id", "None")
            zone = r.get("zone", "Unknown")
            if pid not in precinct_zones:
                precinct_zones[pid] = set()
            precinct_zones[pid].add(zone)

    print("\n### Precinct -> Zone Mapping ###")
    for pid, zones in sorted(precinct_zones.items()):
        print(f"  {pid}: {', '.join(sorted(zones))}")

    # Check which precincts have requirements
    print("\n### Precinct Coverage Analysis ###")
    detected_precincts = set(precinct_stats.keys()) - {"None"}
    db_precinct_ids = set(p[0] for p in db_precincts)

    print(f"  Detected precincts: {len(detected_precincts)}")
    print(f"  Database precincts: {len(db_precinct_ids)}")

    in_both = detected_precincts & db_precinct_ids
    detected_only = detected_precincts - db_precinct_ids
    db_only = db_precinct_ids - detected_precincts

    print(f"\n  In both: {len(in_both)}")
    for p in sorted(in_both):
        print(f"    [OK] {p}")

    if detected_only:
        print(f"\n  Detected but not in DB: {len(detected_only)}")
        for p in sorted(detected_only):
            print(f"    [!] {p}")

    if db_only:
        print(f"\n  In DB but not detected: {len(db_only)}")
        for p in sorted(db_only):
            print(f"    - {p}")

    # Save results
    with open("tests/results/leichhardt_precinct_analysis.json", "w") as f:
        json.dump({
            "results": results,
            "precinct_stats": precinct_stats,
            "zone_stats": zone_stats,
            "suburb_stats": suburb_stats,
            "precinct_zones": {k: list(v) for k, v in precinct_zones.items()},
            "db_precincts": [{"id": p[0], "name": p[1], "lga": p[2]} for p in db_precincts],
            "precinct_requirements": [{"id": p[0], "count": p[1]} for p in precinct_reqs]
        }, f, indent=2)

    print("\n\nResults saved to tests/results/leichhardt_precinct_analysis.json")

    conn.close()

if __name__ == "__main__":
    main()
