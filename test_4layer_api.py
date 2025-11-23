#!/usr/bin/env python3
"""
Test the 4-layer filtering logic directly against the database.
This simulates what the API endpoint does.
"""
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor(cursor_factory=RealDictCursor)

def query_layer(layer, filters):
    """Query a specific layer with filters."""
    params = [layer]

    sql = """
        SELECT
            id,
            LEFT(provision_text, 100) as text_preview,
            v2_dcp_layer,
            v2_dcp_part,
            v2_topic,
            v2_provision_type,
            v2_precinct_id
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
          AND v2_dcp_layer = %s
    """

    # Layer-specific filtering
    if layer == 'use_specific' and filters.get('zone'):
        sql += " AND (v2_applicable_zones IS NULL OR %s = ANY(v2_applicable_zones))"
        params.append(filters['zone'])

    if layer == 'condition':
        conditions = []
        if filters.get('heritage'):
            conditions.append('heritage')
        if filters.get('flood'):
            conditions.append('flood')

        if not conditions:
            return []

        sql += " AND v2_site_condition_required = ANY(%s::text[])"
        params.append(conditions)

    if layer == 'precinct' and filters.get('precinct_id'):
        sql += " AND v2_precinct_id = %s"
        params.append(filters['precinct_id'])

    sql += " ORDER BY v2_topic, v2_dcp_part LIMIT 100"

    cur.execute(sql, params)
    return cur.fetchall()


def test_scenario(name, filters):
    """Test a specific scenario."""
    print(f"\n{'=' * 70}")
    print(f"SCENARIO: {name}")
    print(f"Filters: {filters}")
    print("=" * 70)

    total = 0
    for layer in ['generic', 'use_specific', 'condition', 'precinct']:
        results = query_layer(layer, filters)
        count = len(results)
        total += count

        layer_names = {
            'generic': 'Layer 1: Generic',
            'use_specific': 'Layer 2: Use-Specific',
            'condition': 'Layer 3: Condition',
            'precinct': 'Layer 4: Precinct'
        }

        print(f"\n{layer_names[layer]}: {count} provisions")

        if count > 0:
            # Show topic distribution
            topics = {}
            for r in results:
                t = r['v2_topic'] or 'unknown'
                topics[t] = topics.get(t, 0) + 1

            print(f"  Topics: {dict(sorted(topics.items(), key=lambda x: -x[1])[:5])}")

            # Show sample
            print(f"  Sample: {results[0]['text_preview'][:60]}...")

    print(f"\n  TOTAL: {total} provisions")
    return total


# Test scenarios
print("=" * 70)
print("4-LAYER API TEST")
print("=" * 70)

# Scenario 1: Non-heritage R2 property in Marrickville Precinct 12
test_scenario(
    "R2 Non-Heritage in Marrickville Precinct 12",
    {
        'zone': 'R2',
        'heritage': False,
        'flood': False,
        'precinct_id': '12_'
    }
)

# Scenario 2: Heritage property in Leichhardt Part G (G6)
test_scenario(
    "Heritage property in Leichhardt G6",
    {
        'zone': 'R2',
        'heritage': True,
        'flood': False,
        'precinct_id': 'G6'
    }
)

# Scenario 3: Ashfield Town Centre (Part 1)
test_scenario(
    "Ashfield Town Centre (Part 1)",
    {
        'zone': 'B2',
        'heritage': False,
        'flood': False,
        'precinct_id': 'Part 1'
    }
)

# Scenario 4: No precinct filter (shows all precinct provisions)
test_scenario(
    "Generic query - no precinct filter",
    {
        'zone': 'R2',
        'heritage': False,
        'flood': False,
        'precinct_id': None  # No precinct filter
    }
)

conn.close()
print("\n\nDone!")
