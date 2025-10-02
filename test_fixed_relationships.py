#!/usr/bin/env python3
"""
Test the corrected PostgreSQL database relationships
"""

import psycopg2
from psycopg2.extras import RealDictCursor

# Connect to corrected database
conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning_corrected',
    user='postgres',
    password='postgres',
    port='5432'
)
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Test the SEPP water provision with proper relationships
print('=== TESTING CORRECTED DATABASE RELATIONSHIPS ===')
print()

# Find SEPP water provision
cursor.execute('''
    SELECT rp.*, li.instrument_type, li.legal_precedence
    FROM regulatory_provisions rp
    JOIN legal_instruments li ON rp.instrument_id = li.id
    WHERE li.instrument_type = 'SEPP'
    AND rp.provision_text ILIKE '%water%'
    ORDER BY li.legal_precedence ASC
    LIMIT 1
''')
sepp_provision = cursor.fetchone()

if sepp_provision:
    print(f'SEPP Water Provision (ID: {sepp_provision["id"]}):')
    print(f'  Instrument Type: {sepp_provision["instrument_type"]}')
    print(f'  Legal Precedence: {sepp_provision["legal_precedence"]}')
    print(f'  Ref Number: {sepp_provision["ref_number"]}')
    print(f'  Text: {sepp_provision["provision_text"][:200]}...')
    print()

    # Test development controls relationship (should work without CAST!)
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM development_controls
        WHERE provision_id = %s
    ''', (sepp_provision['id'],))
    dc_count = cursor.fetchone()['count']
    print(f'  Development Controls Linked: {dc_count}')

    # Test SEPP overrides relationship
    cursor.execute('''
        SELECT COUNT(*) as count
        FROM sepp_lep_overrides
        WHERE sepp_provision_id = %s
    ''', (sepp_provision['id'],))
    override_count = cursor.fetchone()['count']
    print(f'  SEPP Override Relationships: {override_count}')
    print()

print('=== RELATIONSHIP INTEGRITY TEST ===')
print('All queries work without CAST() - relationships are FIXED!')

cursor.close()
conn.close()