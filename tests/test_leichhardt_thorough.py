"""Thorough Leichhardt test - compare to Ashfield/Marrickville"""
import requests
import json

BASE_URL = "http://localhost:3007"

TEST_ADDRESSES = {
    "Marrickville": [
        "180 Addison Road Marrickville 2204",
        "45 Denison Road Dulwich Hill 2203",
    ],
    "Ashfield": [
        "15 Alt Street Ashfield 2131",
        "1 The Parade Haberfield 2045",
    ],
    "Leichhardt": [
        "10 Norton Street Leichhardt 2040",
        "25 Marion Street Leichhardt 2040",
        "150 Balmain Road Leichhardt 2040",
        "5 Lombard Street Glebe 2037",
    ]
}

def test_address(address: str):
    """Test a single address through property + DCP APIs"""
    print(f"\n{'='*60}")
    print(f"Testing: {address}")
    print('='*60)

    # Step 1: Property API
    print("\n[1] Property API...")
    prop_resp = requests.get(f"{BASE_URL}/api/property", params={"address": address}, timeout=30)
    prop_data = prop_resp.json()

    if not prop_data.get("success"):
        print(f"  ERROR: Property API failed")
        return None

    data = prop_data.get("data", {})
    constraints = data.get("constraints", {})

    print(f"  Zone: {constraints.get('zone')} ({constraints.get('zoneDescription')})")
    print(f"  LGA: {constraints.get('lga')}")
    print(f"  Former Council: {constraints.get('formerCouncil')}")
    print(f"  Precinct ID: {constraints.get('precinctId')}")
    print(f"  Heritage: {constraints.get('heritage')}")

    coords = data.get("coordinates", {})

    # Step 2: DCP Complete API
    print("\n[2] DCP Complete API...")
    dcp_payload = {
        "address": address,
        "zone": constraints.get("zone") or "R2",
        "developmentType": "dwelling_house",
        "lga": constraints.get("lga") or "Inner West",
        "coordinates": {
            "lat": coords.get("lat"),
            "lon": coords.get("lon")
        }
    }

    dcp_resp = requests.post(
        f"{BASE_URL}/api/compliance/dcp-complete",
        json=dcp_payload,
        timeout=60
    )
    dcp_data = dcp_resp.json()

    if not dcp_data.get("success"):
        print(f"  ERROR: DCP API failed - {dcp_data.get('error')}")
        return None

    query = dcp_data.get("query", {})
    print(f"  Query formerCouncil: {query.get('formerCouncil')}")
    print(f"  Query precinctId: {query.get('precinctId')}")

    gp = dcp_data.get("general_provisions") or {}
    pp = dcp_data.get("precinct_provisions") or {}
    combined = dcp_data.get("combined") or {}

    print(f"\n  General Provisions: {gp.get('total', 0)}")
    print(f"  Precinct Provisions: {pp.get('total', 0)}")
    print(f"  Combined Total: {combined.get('total_requirements', 0)}")

    # Show categories
    cats = combined.get("categories", [])
    if cats:
        print(f"\n  Categories ({len(cats)}):")
        for c in cats[:8]:
            print(f"    - {c.get('category')}: {c.get('count')} items")
        if len(cats) > 8:
            print(f"    ... and {len(cats) - 8} more")

    # Show sample requirements
    reqs = combined.get("requirements", [])
    if reqs:
        print(f"\n  Sample Requirements (first 3):")
        for r in reqs[:3]:
            text = (r.get("requirement_text") or "")[:100]
            print(f"    - [{r.get('category')}] {text}...")

    return {
        "address": address,
        "formerCouncil": constraints.get("formerCouncil"),
        "precinctId": constraints.get("precinctId"),
        "general_count": gp.get("total", 0),
        "precinct_count": pp.get("total", 0),
        "total": combined.get("total_requirements", 0),
        "categories": len(cats)
    }


def main():
    print("="*60)
    print("THOROUGH LEICHHARDT TEST vs ASHFIELD/MARRICKVILLE")
    print("="*60)

    results = {}

    for council, addresses in TEST_ADDRESSES.items():
        print(f"\n\n{'#'*60}")
        print(f"# {council.upper()}")
        print('#'*60)

        results[council] = []
        for addr in addresses:
            result = test_address(addr)
            if result:
                results[council].append(result)

    # Summary
    print("\n\n" + "="*60)
    print("SUMMARY")
    print("="*60)

    for council, council_results in results.items():
        if not council_results:
            print(f"\n{council}: NO RESULTS")
            continue

        totals = [r["total"] for r in council_results]
        avg = sum(totals) / len(totals) if totals else 0
        print(f"\n{council}:")
        print(f"  Addresses tested: {len(council_results)}")
        print(f"  Avg provisions: {avg:.0f}")
        for r in council_results:
            print(f"    - {r['address'][:30]}...: {r['total']} provisions ({r['categories']} categories)")


if __name__ == "__main__":
    main()
