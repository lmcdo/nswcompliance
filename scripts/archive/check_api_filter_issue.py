#!/usr/bin/env python3
"""Check why API returns 0 provisions"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print('=' * 70)
print('WHY API RETURNS 0 PROVISIONS')
print('=' * 70)

# Check if the API filter (v2_is_actionable = true) is the problem
print('\nChecking v2_is_actionable status...\n')

cur.execute('''
    SELECT v2_is_actionable, COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
    GROUP BY v2_is_actionable
''')

print('Leichhardt provisions by actionable status:')
for row in cur.fetchall():
    print(f'  v2_is_actionable = {row[0]}: {row[1]:,}')

print('\n' + '=' * 70)
print('THE PROBLEM')
print('=' * 70)

print('\nAPI code (route.ts line 692):')
print('  WHERE v2_is_actionable = true')
print('  AND v2_dcp_layer = \'generic\'')

print('\nDatabase state:')
print('  ALL provisions have v2_is_actionable = False')

print('\nResult:')
print('  API returns 0 provisions because filter excludes everything')

print('\n' + '=' * 70)
print('WHAT SHOULD HAPPEN')
print('=' * 70)

cur.execute('''
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_dcp_layer = 'generic'
''')
generic_count = cur.fetchone()[0]

cur.execute('''
    SELECT COUNT(*)
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND v2_dcp_layer = 'use_specific'
      AND ('R2' = ANY(v2_applicable_zones) OR 'ALL' = ANY(v2_applicable_zones))
''')
use_specific_count = cur.fetchone()[0]

print(f'\nWithout v2_is_actionable filter:')
print(f'  Generic layer: {generic_count:,}')
print(f'  Use-specific (R2): {use_specific_count:,}')
print(f'  TOTAL: {generic_count + use_specific_count:,}')

conn.close()
