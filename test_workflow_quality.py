#!/usr/bin/env python3
"""
Test realistic certifier/planner workflows and assess result quality.
"""
import requests
import json

API_BASE = "http://localhost:3007/api/provisions/for-property"

def test_scenario(name, params):
    """Test a scenario and show detailed results."""
    url = f"{API_BASE}?{'&'.join(f'{k}={v}' for k, v in params.items() if v)}"

    print("\n" + "=" * 70)
    print(f"SCENARIO: {name}")
    print("=" * 70)
    print(f"Query: {params}")

    try:
        response = requests.get(url, timeout=30)
        data = response.json()

        if not data.get('success'):
            print(f"ERROR: {data.get('error')}")
            return

        d = data['data']
        summary = d['summary']

        print(f"\nTOTAL: {summary['total_provisions']} provisions")
        print(f"  Layer 1 (Generic):      {summary['layer_1_generic']}")
        print(f"  Layer 2 (Zone):         {summary['layer_2_use_specific']}")
        print(f"  Layer 3 (Condition):    {summary['layer_3_condition']}")
        print(f"  Layer 4 (Precinct):     {summary['layer_4_precinct']}")

        # Topics breakdown
        topics = d['by_topic']
        print(f"\nTOPICS ({len(topics)} total):")
        for topic, provisions in sorted(topics.items(), key=lambda x: -len(x[1])):
            print(f"  {topic}: {len(provisions)}")

        # Sample provisions from key topics
        print("\n--- SAMPLE PROVISIONS ---")
        for topic in ['setbacks', 'height', 'parking', 'heritage']:
            provisions = topics.get(topic, [])[:2]
            if provisions:
                print(f"\n[{topic.upper()}]")
                for p in provisions:
                    layer = p.get('layer') or p.get('v2_dcp_layer', '?')
                    marker = p.get('v2_marker', '')
                    text = p['provision_text']
                    if len(text) > 150:
                        text = text[:150] + "..."
                    print(f"  [{layer}] {marker}: {text}")

        # Quality assessment
        print("\n--- QUALITY ASSESSMENT ---")

        # Check for empty/garbage provisions
        all_provisions = []
        for provs in topics.values():
            all_provisions.extend(provs)

        short_count = sum(1 for p in all_provisions if len(p['provision_text']) < 20)
        long_count = sum(1 for p in all_provisions if len(p['provision_text']) > 500)

        print(f"  Very short (<20 chars): {short_count}")
        print(f"  Very long (>500 chars): {long_count}")

        # Check layer distribution
        if summary['layer_1_generic'] > 0.9 * summary['total_provisions']:
            print("  WARNING: >90% are generic - filtering may not be working")
        else:
            print("  OK: Layer distribution looks reasonable")

    except Exception as e:
        print(f"ERROR: {e}")

def main():
    print("=" * 70)
    print("CERTIFIER/PLANNER WORKFLOW QUALITY TEST")
    print("=" * 70)

    # Scenario 1: Basic R2 dwelling DA
    test_scenario(
        "Certifier: R2 Dwelling House (DA)",
        {'zone': 'R2', 'dev_type': 'dwelling_house', 'assessment_type': 'DA'}
    )

    # Scenario 2: R2 dwelling CDC (should be much fewer)
    test_scenario(
        "Certifier: R2 Dwelling House (CDC - quantitative only)",
        {'zone': 'R2', 'dev_type': 'dwelling_house', 'assessment_type': 'CDC'}
    )

    # Scenario 3: Granny flat CDC
    test_scenario(
        "Certifier: Secondary Dwelling / Granny Flat (CDC)",
        {'zone': 'R2', 'dev_type': 'secondary_dwelling', 'assessment_type': 'CDC'}
    )

    # Scenario 4: Heritage property
    test_scenario(
        "Planner: Heritage Property Alteration (DA)",
        {'zone': 'R2', 'dev_type': 'dwelling_house_alteration', 'heritage': 'true', 'assessment_type': 'DA'}
    )

    # Scenario 5: Commercial
    test_scenario(
        "Planner: B2 Retail Premises (DA)",
        {'zone': 'B2', 'dev_type': 'retail_premises', 'assessment_type': 'DA'}
    )

    # Scenario 6: Full filter cascade
    test_scenario(
        "Certifier: Full Filter (R2 + dwelling + precinct + CDC)",
        {'zone': 'R2', 'dev_type': 'dwelling_house', 'precinct_id': '12_', 'assessment_type': 'CDC', 'heritage': 'false'}
    )

    print("\n" + "=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()
