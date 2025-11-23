#!/usr/bin/env python3
"""
Test realistic user scenarios against the 4-layer API.

Tests cover:
1. R2 zone dwelling scenarios (most common)
2. Heritage property scenarios
3. Commercial/industrial scenarios
4. CDC vs DA filtering
5. Precinct-specific queries
6. Filter cascade verification
"""
import requests
import json
from datetime import datetime

API_BASE = "http://localhost:3007/api/provisions/for-property"

def test_scenario(name, params, expected_range=None):
    """Test a scenario and print results."""
    url = f"{API_BASE}?{'&'.join(f'{k}={v}' for k, v in params.items() if v)}"

    try:
        response = requests.get(url, timeout=30)
        data = response.json()

        if not data.get('success'):
            print(f"FAIL {name}: {data.get('error')}")
            return None

        summary = data['data']['summary']
        total = summary['total_provisions']
        topics = list(data['data']['by_topic'].keys())

        # Check if within expected range
        status = "PASS"
        if expected_range:
            min_val, max_val = expected_range
            if total < min_val or total > max_val:
                status = "WARN"

        print(f"\n{status} {name}")
        print(f"   Params: {params}")
        print(f"   Total: {total} provisions")
        print(f"   By Layer: L1={summary['layer_1_generic']}, L2={summary['layer_2_use_specific']}, L3={summary['layer_3_condition']}, L4={summary['layer_4_precinct']}")
        print(f"   Topics: {', '.join(topics[:5])}{'...' if len(topics) > 5 else ''}")

        if expected_range:
            print(f"   Expected: {expected_range[0]}-{expected_range[1]} (actual: {total})")

        return total

    except Exception as e:
        print(f"ERROR {name}: {e}")
        return None

def main():
    print("=" * 70)
    print("USER SCENARIO TESTS")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    results = {}

    # =========================================================================
    # SCENARIO 1: R2 Dwelling House - Most Common Use Case
    # =========================================================================
    print("\n" + "=" * 70)
    print("SCENARIO 1: R2 DWELLING HOUSE (Most Common)")
    print("=" * 70)

    # Baseline - no filters
    results['baseline'] = test_scenario(
        "Baseline (no filters)",
        {},
        expected_range=(500, 2000)
    )

    # Zone filter only
    results['r2_only'] = test_scenario(
        "R2 zone only",
        {'zone': 'R2'},
        expected_range=(500, 1500)
    )

    # R2 + dwelling_house
    results['r2_dh'] = test_scenario(
        "R2 + dwelling_house",
        {'zone': 'R2', 'dev_type': 'dwelling_house'},
        expected_range=(200, 800)
    )

    # R2 + dwelling_house + DA
    results['r2_dh_da'] = test_scenario(
        "R2 + dwelling_house + DA",
        {'zone': 'R2', 'dev_type': 'dwelling_house', 'assessment_type': 'DA'},
        expected_range=(200, 800)
    )

    # R2 + dwelling_house + CDC (TARGET: ~50)
    results['r2_dh_cdc'] = test_scenario(
        "R2 + dwelling_house + CDC",
        {'zone': 'R2', 'dev_type': 'dwelling_house', 'assessment_type': 'CDC'},
        expected_range=(20, 100)
    )

    # =========================================================================
    # SCENARIO 2: GRANULAR DEV TYPES
    # =========================================================================
    print("\n" + "=" * 70)
    print("SCENARIO 2: GRANULAR DEVELOPMENT TYPES")
    print("=" * 70)

    # Rear addition
    results['rear_add'] = test_scenario(
        "R2 + dwelling_addition_rear",
        {'zone': 'R2', 'dev_type': 'dwelling_addition_rear'},
        expected_range=(200, 800)
    )

    # First floor addition
    results['first_floor'] = test_scenario(
        "R2 + dwelling_addition_first",
        {'zone': 'R2', 'dev_type': 'dwelling_addition_first'},
        expected_range=(200, 800)
    )

    # Secondary dwelling (granny flat)
    results['granny'] = test_scenario(
        "R2 + secondary_dwelling",
        {'zone': 'R2', 'dev_type': 'secondary_dwelling'},
        expected_range=(50, 300)
    )

    # Dual occupancy
    results['dual_occ'] = test_scenario(
        "R2 + dual_occupancy",
        {'zone': 'R2', 'dev_type': 'dual_occupancy'},
        expected_range=(50, 300)
    )

    # =========================================================================
    # SCENARIO 3: HERITAGE PROPERTIES
    # =========================================================================
    print("\n" + "=" * 70)
    print("SCENARIO 3: HERITAGE PROPERTIES")
    print("=" * 70)

    # Heritage = false (non-heritage property)
    results['non_heritage'] = test_scenario(
        "R2 + non-heritage",
        {'zone': 'R2', 'heritage': 'false'},
        expected_range=(500, 1500)
    )

    # Heritage = true (heritage property - should get more provisions)
    results['heritage'] = test_scenario(
        "R2 + heritage property",
        {'zone': 'R2', 'heritage': 'true'},
        expected_range=(500, 2000)
    )

    # Heritage + dwelling alterations
    results['heritage_alt'] = test_scenario(
        "R2 + heritage + dwelling_house_alteration",
        {'zone': 'R2', 'heritage': 'true', 'dev_type': 'dwelling_house_alteration'},
        expected_range=(200, 1000)
    )

    # =========================================================================
    # SCENARIO 4: COMMERCIAL/INDUSTRIAL
    # =========================================================================
    print("\n" + "=" * 70)
    print("SCENARIO 4: COMMERCIAL & INDUSTRIAL")
    print("=" * 70)

    # B2 (commercial)
    results['b2'] = test_scenario(
        "B2 zone + commercial_premises",
        {'zone': 'B2', 'dev_type': 'commercial_premises'},
        expected_range=(50, 500)
    )

    # B2 retail
    results['b2_retail'] = test_scenario(
        "B2 zone + retail_premises",
        {'zone': 'B2', 'dev_type': 'retail_premises'},
        expected_range=(50, 500)
    )

    # IN1 (industrial)
    results['in1'] = test_scenario(
        "IN1 zone + light_industry",
        {'zone': 'IN1', 'dev_type': 'light_industry'},
        expected_range=(20, 300)
    )

    # =========================================================================
    # SCENARIO 5: PRECINCT-SPECIFIC
    # =========================================================================
    print("\n" + "=" * 70)
    print("SCENARIO 5: PRECINCT-SPECIFIC QUERIES")
    print("=" * 70)

    # Marrickville Precinct 12
    results['precinct_12'] = test_scenario(
        "R2 + Marrickville Precinct 12",
        {'zone': 'R2', 'precinct_id': '12_'},
        expected_range=(200, 800)
    )

    # Leichhardt G6
    results['g6'] = test_scenario(
        "R2 + Leichhardt G6",
        {'zone': 'R2', 'precinct_id': 'G6'},
        expected_range=(200, 800)
    )

    # Ashfield Part 1
    results['ashfield_p1'] = test_scenario(
        "B2 + Ashfield Part 1",
        {'zone': 'B2', 'precinct_id': 'Part 1'},
        expected_range=(100, 500)
    )

    # =========================================================================
    # SCENARIO 6: COMBINED FILTERS (REALISTIC USER JOURNEY)
    # =========================================================================
    print("\n" + "=" * 70)
    print("SCENARIO 6: REALISTIC USER JOURNEYS")
    print("=" * 70)

    # User 1: Homeowner adding granny flat (CDC)
    results['user1'] = test_scenario(
        "User 1: Granny flat CDC",
        {'zone': 'R2', 'dev_type': 'secondary_dwelling', 'assessment_type': 'CDC', 'heritage': 'false'},
        expected_range=(10, 50)
    )

    # User 2: Certifier checking rear addition
    results['user2'] = test_scenario(
        "User 2: Rear addition CDC",
        {'zone': 'R2', 'dev_type': 'dwelling_addition_rear', 'assessment_type': 'CDC', 'heritage': 'false'},
        expected_range=(10, 80)
    )

    # User 3: Planner assessing heritage DA
    results['user3'] = test_scenario(
        "User 3: Heritage alteration DA",
        {'zone': 'R2', 'dev_type': 'dwelling_house_alteration', 'assessment_type': 'DA', 'heritage': 'true'},
        expected_range=(100, 800)
    )

    # User 4: Full filter cascade
    results['user4'] = test_scenario(
        "User 4: Full cascade (zone+dev+precinct+CDC)",
        {'zone': 'R2', 'dev_type': 'dwelling_house', 'precinct_id': '12_', 'assessment_type': 'CDC', 'heritage': 'false'},
        expected_range=(10, 100)
    )

    # =========================================================================
    # SUMMARY
    # =========================================================================
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    print("\nFilter Cascade Effect:")
    print(f"   Baseline:          {results.get('baseline', 'N/A')} provisions")
    print(f"   + Zone (R2):       {results.get('r2_only', 'N/A')} provisions")
    print(f"   + Dev type:        {results.get('r2_dh', 'N/A')} provisions")
    print(f"   + CDC:             {results.get('r2_dh_cdc', 'N/A')} provisions")

    print("\nTarget Achieved:")
    target_achieved = results.get('r2_dh_cdc', 999)
    if target_achieved and 20 <= target_achieved <= 100:
        print(f"   CDC target (~50): PASS ({target_achieved} provisions)")
    else:
        print(f"   CDC target (~50): NEEDS REVIEW ({target_achieved} provisions)")

    print(f"\nCompleted: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()
