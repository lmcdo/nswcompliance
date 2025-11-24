#!/usr/bin/env python3
"""
Professional Scenario Testing - Real queries that certifiers/planners would make.
Tests quality, relevance, and completeness of results.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

def run_query(cur, params):
    """Execute 4-layer query and return results."""
    zone = params.get('zone')
    dev_type = params.get('dev_type')
    heritage = params.get('heritage', 'false')
    precinct_id = params.get('precinct_id')
    assessment_type = params.get('assessment_type', 'DA')

    # Build query
    sql = """
        SELECT id, v2_dcp_layer, v2_topic, v2_marker,
               LEFT(provision_text, 200) as text_preview,
               v2_provision_type, v2_has_numeric_value
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
    """
    conditions = []
    query_params = []

    # Layer 1: Generic (always)
    # Layer 2: Zone filter ('ALL' = wildcard, matches any zone)
    if zone:
        conditions.append(f"(%s = ANY(v2_applicable_zones) OR 'ALL' = ANY(v2_applicable_zones) OR v2_applicable_zones IS NULL OR cardinality(v2_applicable_zones) = 0)")
        query_params.append(zone)

    # Layer 3: Heritage filter
    if heritage == 'false':
        conditions.append("(v2_site_condition_required IS NULL OR v2_site_condition_required != 'heritage')")

    # Dev type filter
    if dev_type:
        conditions.append(f"(%s = ANY(v2_applicable_dev_types))")
        query_params.append(dev_type)

    # CDC filter
    if assessment_type == 'CDC':
        conditions.append("v2_provision_type = 'control'")
        conditions.append("v2_has_numeric_value = true")

    if conditions:
        sql += " AND " + " AND ".join(conditions)

    sql += " ORDER BY v2_dcp_layer, v2_topic"

    cur.execute(sql, query_params)
    return cur.fetchall()


def assess_quality(results, scenario_name, expected_topics):
    """Assess quality of results for a scenario."""
    print(f"\n{'='*70}")
    print(f"SCENARIO: {scenario_name}")
    print(f"{'='*70}")

    if not results:
        print("  [FAIL] No results returned!")
        return False

    # Count by layer
    layers = {}
    topics = {}
    numeric_count = 0
    with_marker = 0

    for r in results:
        layer = r[1] or 'unknown'
        topic = r[2] or 'other'
        marker = r[3]
        has_numeric = r[6]

        layers[layer] = layers.get(layer, 0) + 1
        topics[topic] = topics.get(topic, 0) + 1
        if has_numeric:
            numeric_count += 1
        if marker:
            with_marker += 1

    print(f"\n  TOTAL: {len(results)} provisions")
    print(f"  Numeric values: {numeric_count} ({100*numeric_count/len(results):.0f}%)")
    print(f"  With markers: {with_marker} ({100*with_marker/len(results):.0f}%)")

    print(f"\n  BY LAYER:")
    for layer, count in sorted(layers.items()):
        print(f"    {layer}: {count}")

    print(f"\n  BY TOPIC (top 10):")
    for topic, count in sorted(topics.items(), key=lambda x: -x[1])[:10]:
        expected = "[expected]" if topic in expected_topics else ""
        print(f"    {topic}: {count} {expected}")

    # Quality checks
    issues = []

    # Check 1: Result count in reasonable range
    if len(results) < 20:
        issues.append(f"Too few results ({len(results)} < 20)")
    elif len(results) > 500:
        issues.append(f"Too many results ({len(results)} > 500) - filtering may not be working")

    # Check 2: Expected topics present
    missing_topics = [t for t in expected_topics if t not in topics]
    if missing_topics:
        issues.append(f"Missing expected topics: {missing_topics}")

    # Check 3: Numeric provisions for CDC
    if 'CDC' in scenario_name and numeric_count < 20:
        issues.append(f"Too few numeric provisions for CDC ({numeric_count})")

    # Check 4: Sample provisions look relevant
    print(f"\n  SAMPLE PROVISIONS:")
    for topic in expected_topics[:3]:
        topic_results = [r for r in results if r[2] == topic]
        if topic_results:
            sample = topic_results[0]
            preview = sample[4][:100] + "..." if len(sample[4]) > 100 else sample[4]
            print(f"    [{topic}] {preview}")

    # Verdict
    print(f"\n  QUALITY ASSESSMENT:")
    if issues:
        for issue in issues:
            print(f"    [WARNING] {issue}")
        return False
    else:
        print(f"    [PASS] Results meet quality criteria")
        return True


def main():
    print("="*70)
    print("PROFESSIONAL SCENARIO TESTING")
    print("="*70)

    conn = psycopg2.connect('dbname=nsw_planning')
    cur = conn.cursor()

    scenarios = [
        # Scenario 1: Certifier - Secondary Dwelling CDC
        {
            "name": "Certifier: Secondary Dwelling (Granny Flat) CDC in R2",
            "params": {"zone": "R2", "dev_type": "secondary_dwelling", "assessment_type": "CDC", "heritage": "false"},
            "expected_topics": ["setbacks", "height", "parking", "landscaping"],
            "description": "Most common CDC application - secondary dwellings"
        },

        # Scenario 2: Certifier - Dual Occupancy CDC
        {
            "name": "Certifier: Dual Occupancy CDC in R2",
            "params": {"zone": "R2", "dev_type": "dual_occupancy", "assessment_type": "CDC", "heritage": "false"},
            "expected_topics": ["setbacks", "height", "parking", "landscaping"],
            "description": "Common CDC - subdividing existing lot"
        },

        # Scenario 3: Planner - Residential Flat Building DA
        {
            "name": "Planner: Residential Flat Building DA in R3",
            "params": {"zone": "R3", "dev_type": "residential_flat_building", "assessment_type": "DA", "heritage": "false"},
            "expected_topics": ["height", "setbacks", "parking", "landscaping", "building_form"],
            "description": "Multi-storey apartment development"
        },

        # Scenario 4: Commercial - Retail Premises
        {
            "name": "Planner: Retail Shop DA in B2",
            "params": {"zone": "B2", "dev_type": "retail_premises", "assessment_type": "DA", "heritage": "false"},
            "expected_topics": ["parking", "signage", "access", "waste"],
            "description": "New retail shop in local centre"
        },

        # Scenario 5: Industrial - Warehouse CDC
        {
            "name": "Certifier: Warehouse CDC in IN1",
            "params": {"zone": "IN1", "dev_type": "warehouse", "assessment_type": "CDC", "heritage": "false"},
            "expected_topics": ["parking", "setbacks", "height", "access"],
            "description": "Industrial warehouse development"
        },

        # Scenario 6: Special Use - Child Care Centre
        {
            "name": "Planner: Child Care Centre DA in R2",
            "params": {"zone": "R2", "dev_type": "child_care_centre", "assessment_type": "DA", "heritage": "false"},
            "expected_topics": ["parking", "setbacks", "landscaping", "access"],
            "description": "Child care in residential area"
        },

        # Scenario 7: Mixed Use - Shop Top Housing
        {
            "name": "Planner: Shop Top Housing DA in B4",
            "params": {"zone": "B4", "dev_type": "shop_top_housing", "assessment_type": "DA", "heritage": "false"},
            "expected_topics": ["height", "parking", "setbacks", "building_form"],
            "description": "Residential above retail"
        },

        # Scenario 8: Heritage Property
        {
            "name": "Planner: Dwelling Alteration in Heritage Area",
            "params": {"zone": "R2", "dev_type": "dwelling_house", "assessment_type": "DA", "heritage": "true"},
            "expected_topics": ["heritage", "building_form", "height", "setbacks"],
            "description": "Alterations to heritage item"
        },

        # Scenario 9: Office Development
        {
            "name": "Planner: Office Premises DA in B3",
            "params": {"zone": "B3", "dev_type": "office_premises", "assessment_type": "DA", "heritage": "false"},
            "expected_topics": ["parking", "height", "setbacks", "access"],
            "description": "Commercial office building"
        },

        # Scenario 10: Boarding House
        {
            "name": "Planner: Boarding House DA in R2",
            "params": {"zone": "R2", "dev_type": "boarding_house", "assessment_type": "DA", "heritage": "false"},
            "expected_topics": ["parking", "setbacks", "landscaping", "privacy"],
            "description": "Affordable housing development"
        },
    ]

    passed = 0
    failed = 0

    for scenario in scenarios:
        results = run_query(cur, scenario["params"])
        if assess_quality(results, scenario["name"], scenario["expected_topics"]):
            passed += 1
        else:
            failed += 1

    # Summary
    print("\n" + "="*70)
    print("SUMMARY")
    print("="*70)
    print(f"  Passed: {passed}/{len(scenarios)}")
    print(f"  Failed: {failed}/{len(scenarios)}")

    if failed == 0:
        print("\n  [SUCCESS] All professional scenarios pass quality checks")
    else:
        print(f"\n  [ATTENTION] {failed} scenarios need review")

    conn.close()


if __name__ == "__main__":
    main()
