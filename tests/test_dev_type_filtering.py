"""Systematic testing of dev type filtering across all 3 councils"""
import requests
import json
from collections import defaultdict

BASE_URL = "http://localhost:3007"

# Test addresses for each council
TEST_ADDRESSES = {
    "Leichhardt": {
        "address": "10 Norton Street Leichhardt 2040",
        "zone": "E1",
        "coords": {"lat": -33.887, "lon": 151.157}
    },
    "Marrickville": {
        "address": "180 Addison Road Marrickville 2204",
        "zone": "R2",
        "coords": {"lat": -33.91, "lon": 151.16}
    },
    "Ashfield": {
        "address": "15 Alt Street Ashfield 2131",
        "zone": "R2",
        "coords": {"lat": -33.89, "lon": 151.12}
    }
}

# Dev types to test - use "all" as baseline (shows everything)
DEV_TYPES = [
    ("all", "Baseline (all)"),
    ("dwelling_house", "Dwelling House"),
    ("dual_occupancy", "Dual Occupancy"),
    ("multi_dwelling", "Multi Dwelling"),
    ("residential_flat", "Residential Flat"),
    ("commercial", "Commercial"),
    ("shop", "Shop"),
    ("mixed_use_development", "Mixed Use"),
]

def fetch_dcp_provisions(address_info, council, dev_type):
    """Fetch DCP provisions for a given dev type"""
    try:
        # Use 'all' to mean no filtering, otherwise use the dev type
        actual_dev_type = dev_type if dev_type != "all" else "dwelling_house"

        resp = requests.post(
            f"{BASE_URL}/api/compliance/dcp-complete",
            json={
                "address": address_info["address"],
                "zone": address_info["zone"],
                "developmentType": actual_dev_type,
                "lga": "INNER WEST",
                "formerCouncil": council,
                "coordinates": address_info["coords"]
            },
            timeout=60
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            print(f"  HTTP {resp.status_code}: {resp.text[:200]}")
        return None
    except Exception as e:
        print(f"  Error: {e}")
        return None

def analyze_provisions(data):
    """Analyze provision distribution"""
    if not data or not data.get("success"):
        return None

    result = {
        "general_count": 0,
        "precinct_count": 0,
        "combined_total": 0,
        "categories": {},
    }

    # General provisions
    gp = data.get("general_provisions", {})
    gen_reqs = gp.get("requirements", []) or gp.get("provisions", []) or []
    result["general_count"] = len(gen_reqs)

    # Precinct provisions
    pp = data.get("precinct_provisions") or {}
    prec_reqs = pp.get("requirements", []) or pp.get("provisions", []) or []
    result["precinct_count"] = len(prec_reqs)

    # Combined
    combined = data.get("combined", {})
    if combined and combined.get("total"):
        result["combined_total"] = combined.get("total", 0)
    else:
        result["combined_total"] = result["general_count"] + result["precinct_count"]

    # Categories from combined or requirements
    if combined and combined.get("by_category"):
        for cat, items in combined["by_category"].items():
            result["categories"][cat] = len(items) if isinstance(items, list) else items
    else:
        # Count from requirements
        for req in gen_reqs + prec_reqs:
            cat = req.get("category", "Other")
            result["categories"][cat] = result["categories"].get(cat, 0) + 1

    return result

def test_council(council_name):
    """Test dev type filtering for a council"""
    print(f"\n{'='*70}")
    print(f"TESTING: {council_name.upper()}")
    print(f"{'='*70}")

    address_info = TEST_ADDRESSES[council_name]
    print(f"Address: {address_info['address']}")
    print(f"Zone: {address_info['zone']}")

    results = {}

    # Test each dev type
    print(f"\n{'Dev Type':<25} {'Total':>8} {'General':>10} {'Precinct':>10} {'Categories':>12}")
    print("-" * 70)

    baseline_total = None

    for dev_type, label in DEV_TYPES:
        data = fetch_dcp_provisions(address_info, council_name, dev_type)
        analysis = analyze_provisions(data)

        if analysis:
            if baseline_total is None:
                baseline_total = analysis["combined_total"]

            cat_count = len(analysis["categories"])
            print(f"{label:<25} {analysis['combined_total']:>8} {analysis['general_count']:>10} {analysis['precinct_count']:>10} {cat_count:>12}")
            results[dev_type] = analysis
        else:
            print(f"{label:<25} {'FAILED':>8}")

    # Show filtering effectiveness
    if baseline_total and len(results) > 1:
        print(f"\n--- Filtering Effectiveness (vs Baseline) ---")
        print(f"{'Dev Type':<25} {'Removed':>10} {'% Removed':>10}")
        print("-" * 45)

        for dev_type, label in DEV_TYPES[1:]:  # Skip baseline
            if dev_type in results:
                removed = baseline_total - results[dev_type]["combined_total"]
                pct = (removed / baseline_total * 100) if baseline_total > 0 else 0
                print(f"{label:<25} {removed:>10} {pct:>9.1f}%")

    # Analyze category differences
    if "dwelling_house" in results and "commercial" in results:
        print(f"\n--- Category Comparison: Dwelling vs Commercial ---")

        dh_cats = results["dwelling_house"]["categories"]
        comm_cats = results["commercial"]["categories"]

        # Find categories with significant differences
        all_cats = set(dh_cats.keys()) | set(comm_cats.keys())

        print(f"\n{'Category':<30} {'Dwelling':>10} {'Commercial':>10} {'Diff':>10}")
        print("-" * 65)

        diffs = []
        for cat in all_cats:
            dh_count = dh_cats.get(cat, 0)
            comm_count = comm_cats.get(cat, 0)
            diff = dh_count - comm_count
            diffs.append((cat, dh_count, comm_count, diff))

        # Sort by absolute difference
        diffs.sort(key=lambda x: abs(x[3]), reverse=True)

        for cat, dh, comm, diff in diffs[:15]:
            diff_str = f"+{diff}" if diff > 0 else str(diff)
            print(f"{cat[:30]:<30} {dh:>10} {comm:>10} {diff_str:>10}")

    return results

def main():
    print("=" * 70)
    print("DEV TYPE FILTERING SYSTEMATIC TEST")
    print("=" * 70)

    all_results = {}

    # Test Leichhardt first as requested
    councils_order = ["Leichhardt", "Marrickville", "Ashfield"]

    for council in councils_order:
        results = test_council(council)
        if results:
            all_results[council] = results

    # Summary comparison
    print("\n" + "=" * 70)
    print("CROSS-COUNCIL SUMMARY")
    print("=" * 70)

    print(f"\n{'Council':<15} {'Baseline':>10} {'Dwelling':>10} {'Commercial':>12} {'DH Removed':>12} {'Comm Removed':>12}")
    print("-" * 75)

    for council in councils_order:
        if council in all_results:
            r = all_results[council]
            baseline = r.get("all", {}).get("combined_total", 0)
            dh = r.get("dwelling_house", {}).get("combined_total", 0)
            comm = r.get("commercial", {}).get("combined_total", 0)
            dh_rem = baseline - dh
            comm_rem = baseline - comm
            print(f"{council:<15} {baseline:>10} {dh:>10} {comm:>12} {dh_rem:>12} {comm_rem:>12}")

    # Save results
    with open("tests/results/dev_type_filtering_results.json", "w") as f:
        json.dump(all_results, f, indent=2, default=str)

    print("\n\nResults saved to tests/results/dev_type_filtering_results.json")

if __name__ == "__main__":
    main()
