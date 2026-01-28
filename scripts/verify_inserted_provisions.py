#!/usr/bin/env python3
"""Verify the newly inserted SEPP Housing provisions."""
import psycopg2, os, sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.getenv('DATABASE_URL'))
cur = conn.cursor()

# Check newly inserted provisions
cur.execute("""
SELECT ref_number, section_header, LENGTH(provision_text) as len, extraction_method, id
FROM regulatory_provisions
WHERE extraction_method = 'manual_Dec2025_update'
ORDER BY ref_number
""")

print('Newly inserted provisions:')
print('-' * 120)
print(f'{"Ref":<10} {"Section Header":<55} {"Length":<10} {"ID":<10} {"Method"}')
print('-' * 120)

rows = cur.fetchall()
for row in rows:
    ref = row[0]
    header = row[1][:55]
    length = row[2]
    method = row[3]
    id_ = row[4]
    print(f'{ref:<10} {header:<55} {length:<10} {id_:<10} {method}')

print(f'\n✓ Total: {len(rows)} provisions inserted')

# Check total SEPP Housing count now
cur.execute("""
SELECT COUNT(*)
FROM regulatory_provisions
WHERE document_id LIKE '%Housing%2021%'
""")

total = cur.fetchone()[0]
print(f'✓ Total SEPP Housing provisions in DB: {total}')

# Show a sample of one provision
print('\n' + '='*120)
print('Sample provision (§74 parking rates):')
print('='*120)
cur.execute("""
SELECT provision_text
FROM regulatory_provisions
WHERE ref_number = '74' AND extraction_method = 'manual_Dec2025_update'
""")
row = cur.fetchone()
if row:
    print(row[0][:500] + '...')

conn.close()
