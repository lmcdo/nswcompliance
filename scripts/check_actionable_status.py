#!/usr/bin/env python3
"""Check actionable classification status in database"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

import psycopg2

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

print('\n' + '=' * 70)
print('ACTIONABLE CLASSIFICATION STATUS')
print('=' * 70)

print('\n1. v2_is_actionable breakdown:')
cur.execute('SELECT v2_is_actionable, COUNT(*) FROM regulatory_provisions GROUP BY v2_is_actionable')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]:,}')

print('\n2. Check if column exists and type:')
cur.execute('''
    SELECT column_name, data_type, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
      AND column_name = 'v2_is_actionable'
''')
for row in cur.fetchall():
    print(f'  Column: {row[0]}, Type: {row[1]}, Nullable: {row[2]}')

print('\n3. Sample of provisions (first 10):')
cur.execute('''
    SELECT id, provision_text, v2_is_actionable, v2_dcp_layer
    FROM regulatory_provisions
    WHERE document_id ILIKE '%DCP%'
    LIMIT 10
''')
for row in cur.fetchall():
    text = row[1][:80] if row[1] else 'None'
    print(f'  ID {row[0]}: actionable={row[2]}, layer={row[3]}')
    print(f'    "{text}..."')

print('\n4. Classification reason (if column exists):')
cur.execute('''
    SELECT column_name
    FROM information_schema.columns
    WHERE table_name = 'regulatory_provisions'
      AND column_name = 'v2_actionable_reason'
''')
if cur.fetchone():
    cur.execute('''
        SELECT v2_actionable_reason, COUNT(*)
        FROM regulatory_provisions
        GROUP BY v2_actionable_reason
        ORDER BY COUNT(*) DESC
        LIMIT 10
    ''')
    print('  Reasons:')
    for row in cur.fetchall():
        print(f'    {row[0]}: {row[1]:,}')
else:
    print('  v2_actionable_reason column not found')

conn.close()
