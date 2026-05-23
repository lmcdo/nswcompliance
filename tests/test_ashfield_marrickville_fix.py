import pytest
pytestmark = pytest.mark.stale

"""Test Ashfield and Marrickville dev type filtering after fix"""
import requests
import json

BASE_URL = "http://localhost:3007"

# Test configurations
TESTS = [
    # Ashfield tests
    {"council": "Ashfield", "address": "15 Alt Street Ashfield 2131", "zone": "R2", "dev_type": "dwelling_house", "coords": {"lat": -33.89, "lon": 151.12}},
    {"council": "Ashfield", "address": "15 Alt Street Ashfield 2131", "zone": "R2", "dev_type": "dual_occupancy", "coords": {"lat": -33.89, "lon": 151.12}},
    {"council": "Ashfield", "address": "15 Alt Street Ashfield 2131", "zone": "R2", "dev_type": "multi_dwelling", "coords": {"lat": -33.89, "lon": 151.12}},
    {"council": "Ashfield", "address": "120 Liverpool Road Ashfield 2131", "zone": "E1", "dev_type": "commercial", "coords": {"lat": -33.89, "lon": 151.12}},

    # Marrickville tests
    {"council": "Marrickville", "address": "180 Addison Road Marrickville 2204", "zone": "R2", "dev_type": "dwelling_house", "coords": {"lat": -33.91, "lon": 151.16}},
    {"council": "Marrickville", "address": "180 Addison Road Marrickville 2204", "zone": "R2", "dev_type": "dual_occupancy", "coords": {"lat": -33.91, "lon": 151.16}},
    {"council": "Marrickville", "address": "180 Addison Road Marrickville 2204", "zone": "R2", "dev_type": "commercial", "coords": {"lat": -33.91, "lon": 151.16}},
]

def run_test(test):
    """Run a single test"""
    try:
        resp = requests.post(
            f"{BASE_URL}/api/compliance/dcp-complete",
            json={
                "address": test["address"],
                "zone": test["zone"],
                "developmentType": test["dev_type"],
                "lga": "INNER WEST",
                "formerCouncil": test["council"],
                "coordinates": test["coords"]
            },
            timeout=30
        )

        if resp.status_code == 200:
            data = resp.json()
            gp = data.get("general_provisions", {})
            pp = data.get("precinct_provisions") or {}

            gen_prov = gp.get("count", 0)
            gen_req = gp.get("requirements_count", 0)
            prec_req = pp.get("requirements_count", 0) if pp else 0

            return {
                "success": True,
                "provisions": gen_prov,
                "requirements": gen_req,
                "precinct_reqs": prec_req,
                "total": gen_req + prec_req
            }
        else:
            return {"success": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    print("=" * 70)
    print("ASHFIELD & MARRICKVILLE DEV TYPE FILTERING TEST")
    print("=" * 70)

    print(f"\n{'Council':<12} {'Zone':<6} {'Dev Type':<18} {'Prov':>6} {'Reqs':>6} {'Prec':>6} {'Total':>6}")
    print("-" * 70)

    results_by_council = {}

    for test in TESTS:
        result = run_test(test)
        council = test["council"]
        dev_type = test["dev_type"]

        if council not in results_by_council:
            results_by_council[council] = {}
        results_by_council[council][dev_type] = result

        if result["success"]:
            print(f"{council:<12} {test['zone']:<6} {dev_type:<18} {result['provisions']:>6} {result['requirements']:>6} {result['precinct_reqs']:>6} {result['total']:>6}")
        else:
            print(f"{council:<12} {test['zone']:<6} {dev_type:<18} {'FAILED':>6} - {result.get('error', 'Unknown')[:30]}")

    # Analysis
    print("\n" + "=" * 70)
    print("ANALYSIS")
    print("=" * 70)

    for council, results in results_by_council.items():
        print(f"\n{council}:")
        dev_types = list(results.keys())

        if len(dev_types) >= 2:
            # Check if different dev types produce different results
            totals = [r.get("total", 0) for r in results.values() if r.get("success")]

            if len(set(totals)) > 1:
                print(f"  [OK] Dev type filtering is WORKING - different counts for different dev types")
                for dt, r in results.items():
                    if r.get("success"):
                        print(f"       {dt}: {r['total']} total requirements")
            else:
                print(f"  [!] Dev type filtering may NOT be working - same count ({totals[0] if totals else 'N/A'}) for all dev types")

        # Check if any results have 0 total
        for dt, r in results.items():
            if r.get("success") and r.get("total", 0) == 0:
                print(f"  [X] {dt} returned 0 requirements - POTENTIAL ISSUE")

if __name__ == "__main__":
    main()
