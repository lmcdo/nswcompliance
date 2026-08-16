"""
Check why API returns different counts than database has.
"""

import psycopg2, os
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print('\n=== API QUERY MISMATCH INVESTIGATION ===\n')

# 1. Total Leichhardt actionable
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND document_id LIKE '%Leichhardt%'
""")
total_leichhardt = cur.fetchone()[0]
print(f'Total Leichhardt actionable provisions: {total_leichhardt:,}')

# 2. By layer
cur.execute("""
    SELECT
        COALESCE(v2_dcp_layer, 'NULL') as layer,
        COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND document_id LIKE '%Leichhardt%'
    GROUP BY v2_dcp_layer
    ORDER BY count DESC
""")
print('\nBy v2_dcp_layer:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]:,}')

# 3. Count provisions that match API query conditions
# API query filters by: v2_is_actionable=true AND v2_dcp_layer=<layer>
print('\n=== API Layer Queries ===')

layers = ['generic', 'use_specific', 'condition', 'precinct']
total_via_api = 0

for layer in layers:
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
          AND document_id LIKE %s
          AND v2_dcp_layer = %s
    """, ('%Leichhardt%', layer))

    count = cur.fetchone()[0]
    total_via_api += count
    print(f'  {layer}: {count:,}')

print(f'\nTotal via API queries: {total_via_api:,}')
print(f'Missing from API: {total_leichhardt - total_via_api:,} (provisions with NULL or unexpected layer values)')

# 4. Check a specific test case - Leichhardt + E1 zone
print('\n=== Test Case: Leichhardt R2 (like our test) ===')

# The API doesn't actually filter by zone in the WHERE clause for Leichhardt
# It only uses former_council (via document_id) and v2_dcp_layer
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND document_id LIKE '%Leichhardt%'
      AND v2_dcp_layer IN ('generic', 'use_specific', 'condition', 'precinct')
""")
leichhardt_any_zone = cur.fetchone()[0]
print(f'Leichhardt all zones (actionable + has layer): {leichhardt_any_zone:,}')

# Check what the test actually got
print('\nTest got 834 provisions')
print(f'Database has: {leichhardt_any_zone:,}')
print(f'Discrepancy: {leichhardt_any_zone - 834:,}')

# 5. Check if zone filtering is happening
cur.execute("""
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE v2_is_actionable = true
      AND document_id LIKE '%Leichhardt%'
      AND v2_dcp_layer IN ('generic', 'use_specific', 'condition', 'precinct')
      AND v2_applicable_zones IS NOT NULL
""")
with_zone_data = cur.fetchone()[0]
print(f'\nProvisions with v2_applicable_zones data: {with_zone_data:,}')

# 6. Sample provisions to understand structure
print('\n=== Sample Provisions (first 3 from each layer) ===')
for layer in layers:
    cur.execute("""
        SELECT id, v2_dcp_layer, v2_applicable_zones, LEFT(provision_text, 60)
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
          AND document_id LIKE '%Leichhardt%'
          AND v2_dcp_layer = %s
        LIMIT 3
    """, (layer,))

    results = cur.fetchall()
    if results:
        print(f'\n{layer}:')
        for r in results:
            zones = r[2] if r[2] else 'NULL'
            print(f'  ID={r[0]}, zones={zones}')
            print(f'    {r[3]}...')

conn.close()
