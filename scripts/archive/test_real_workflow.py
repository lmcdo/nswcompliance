#!/usr/bin/env python3
"""Test the actual filtering workflow with a real address"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Simulate property data for a real address
# Example: 45 Norton Street, Leichhardt (R2 zone, non-heritage)
property_data = {
    'former_council': 'Leichhardt',
    'zone': 'R2',
    'heritage': False,
    'precinct_id': None  # Not in a distinctive neighbourhood
}

print('=' * 70)
print('REAL WORKFLOW TEST')
print('=' * 70)
print(f'\nProperty: 45 Norton Street, Leichhardt')
print(f'  Zone: {property_data["zone"]}')
print(f'  Heritage: {property_data["heritage"]}')
print(f'  Precinct: {property_data["precinct_id"] or "None"}')
print(f'  Former Council: {property_data["former_council"]}')

# Layer 1: Generic (always apply)
print('\n--- LAYER 1: GENERIC (always apply) ---')
cur.execute('''
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_dcp_layer = 'generic'
      AND document_id ILIKE %s
''', (f'%{property_data["former_council"]}%',))
layer1_count = cur.fetchone()[0]
print(f'Generic provisions: {layer1_count:,}')

# Layer 2: Use-specific (zone-filtered)
print('\n--- LAYER 2: USE-SPECIFIC (zone-filtered) ---')
cur.execute('''
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_dcp_layer = 'use_specific'
      AND document_id ILIKE %s
      AND (v2_applicable_zones IS NULL
           OR %s = ANY(v2_applicable_zones)
           OR 'ALL' = ANY(v2_applicable_zones))
''', (f'%{property_data["former_council"]}%', property_data['zone']))
layer2_count = cur.fetchone()[0]
print(f'Zone-specific provisions for {property_data["zone"]}: {layer2_count:,}')

# Layer 3: Condition (heritage/flood - none apply)
print('\n--- LAYER 3: CONDITION (heritage/flood) ---')
print(f'Heritage: {property_data["heritage"]} -> 0 provisions (not heritage)')

# Layer 4: Precinct (location-filtered)
print('\n--- LAYER 4: PRECINCT (location-filtered) ---')
if property_data['precinct_id']:
    cur.execute('''
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE v2_dcp_layer = 'precinct'
          AND document_id ILIKE %s
          AND v2_precinct_id = %s
    ''', (f'%{property_data["former_council"]}%', property_data['precinct_id']))
    layer4_count = cur.fetchone()[0]
    print(f'Precinct provisions for {property_data["precinct_id"]}: {layer4_count:,}')
else:
    layer4_count = 0
    print(f'Not in precinct -> 0 provisions')

# TOTAL
total = layer1_count + layer2_count + layer4_count
print('\n' + '=' * 70)
print(f'TOTAL PROVISIONS SHOWN TO USER: {total:,}')
print('=' * 70)

print('\n--- BREAKDOWN BY TOPIC ---')
cur.execute('''
    SELECT v2_topic, COUNT(*) as count
    FROM regulatory_provisions
    WHERE v2_dcp_layer IN ('generic', 'use_specific')
      AND document_id ILIKE %s
      AND (
        v2_dcp_layer = 'generic'
        OR (v2_dcp_layer = 'use_specific'
            AND (v2_applicable_zones IS NULL
                 OR %s = ANY(v2_applicable_zones)
                 OR 'ALL' = ANY(v2_applicable_zones)))
      )
    GROUP BY v2_topic
    ORDER BY count DESC
    LIMIT 15
''', (f'%{property_data["former_council"]}%', property_data['zone']))

for row in cur.fetchall():
    topic = row[0] or 'other'
    count = row[1]
    print(f'  {topic}: {count:,}')

print('\n--- IS THERE ANY DEV_TYPE FILTERING? ---')
print('NO - dev_type parameter exists in API but:')
print('  1. Frontend does NOT pass it (checked ProvisionsByTocStructure.tsx)')
print('  2. API uses it only for RELEVANCE SCORING, not filtering')
print('  3. All provisions are returned, just ranked if dev_type provided')

conn.close()
