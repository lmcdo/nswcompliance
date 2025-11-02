"""
Test Permissibility Checker API endpoint

This script tests the /api/permissibility/check endpoint with various scenarios.
"""

import requests
import json

API_BASE = "http://localhost:3007"

# Test cases covering different zones and development types
test_cases = [
    {
        "name": "Secondary Dwelling in R2 Zone (PERMITTED)",
        "address": "181 Addison Road, Ashfield",
        "developmentType": "secondary_dwelling",
        "expected_permitted": True,
        "expected_zone": "R2"
    },
    {
        "name": "Dual Occupancy in R2 Zone (PERMITTED)",
        "address": "181 Addison Road, Ashfield",
        "developmentType": "dual_occupancy",
        "expected_permitted": True,
        "expected_zone": "R2"
    },
    {
        "name": "Shop Top Housing in R2 Zone (PROHIBITED)",
        "address": "181 Addison Road, Ashfield",
        "developmentType": "shop_top_housing",
        "expected_permitted": False,
        "expected_zone": "R2"
    },
    {
        "name": "Dwelling House in R2 Zone (PERMITTED)",
        "address": "181 Addison Road, Ashfield",
        "developmentType": "dwelling_house",
        "expected_permitted": True,
        "expected_zone": "R2"
    },
    {
        "name": "Child Care Centre in R2 Zone (PERMITTED)",
        "address": "181 Addison Road, Ashfield",
        "developmentType": "child_care",
        "expected_permitted": True,
        "expected_zone": "R2"
    }
]

print("=" * 80)
print("PERMISSIBILITY CHECKER API TESTS")
print("=" * 80)

passed = 0
failed = 0

for i, test in enumerate(test_cases, 1):
    print(f"\nTest {i}: {test['name']}")
    print(f"  Address: {test['address']}")
    print(f"  Dev Type: {test['developmentType']}")

    try:
        response = requests.post(
            f"{API_BASE}/api/permissibility/check",
            json={
                "address": test['address'],
                "developmentType": test['developmentType']
            },
            timeout=30
        )

        if response.status_code != 200:
            print(f"  [FAIL] HTTP {response.status_code}: {response.text[:200]}")
            failed += 1
            continue

        result = response.json()

        # Check if permitted status matches expected
        if result.get('permitted') == test['expected_permitted']:
            print(f"  [PASS] Permissibility: {result.get('permitted')}")

            # Show additional info for permitted development
            if result.get('permitted'):
                print(f"    Zone: {result.get('zone_name')} ({result.get('zone')})")
                print(f"    Permissibility: {result.get('permissibility')}")

                if result.get('notes'):
                    print(f"    Notes: {result.get('notes')[:100]}...")

                if result.get('lep_controls', {}).get('dev_type_specific'):
                    clauses = result['lep_controls']['dev_type_specific']
                    print(f"    LEP Clauses: {len(clauses)} clause(s)")
                    for clause in clauses[:2]:
                        print(f"      - Clause {clause.get('clause_number')}: {clause.get('clause_title')}")
            else:
                print(f"    Reason: {result.get('reason')}")
                if result.get('alternative_options'):
                    print(f"    Alternatives: {len(result['alternative_options'])} options available")

            passed += 1
        else:
            print(f"  [FAIL] Expected permitted={test['expected_permitted']}, got {result.get('permitted')}")
            print(f"    Response: {json.dumps(result, indent=2)[:300]}")
            failed += 1

    except requests.exceptions.RequestException as e:
        print(f"  [ERROR] Request failed: {e}")
        failed += 1
    except Exception as e:
        print(f"  [ERROR] Unexpected error: {e}")
        failed += 1

print("\n" + "=" * 80)
print(f"TEST RESULTS: {passed} passed, {failed} failed")
print("=" * 80)

if failed == 0:
    print("\n[OK] All permissibility tests passed!")
else:
    print(f"\n[WARNING] {failed} test(s) failed")

print("\nMANUAL TESTING INSTRUCTIONS:")
print("1. Open http://localhost:3007/assessment in your browser")
print("2. Enter address: 181 Addison Road, Ashfield")
print("3. Select a development type from the dropdown")
print("4. Click 'Check Permissibility'")
print("5. Verify the result shows correct permissibility status")
print("\nExpected Results:")
print("  - Secondary Dwelling: YES - PERMITTED (with LEP Clause 5.4)")
print("  - Shop Top Housing: NO - PROHIBITED (with alternatives)")
print("  - Dwelling House: YES - PERMITTED")
