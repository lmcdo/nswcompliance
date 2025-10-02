#!/usr/bin/env python3
"""
Check the database schema design for regulatory_provisions
"""
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Check table schema
cur.execute('''
SELECT
  column_name,
  data_type,
  column_default,
  is_nullable
FROM information_schema.columns
WHERE table_name = 'regulatory_provisions'
ORDER BY ordinal_position;
''')

print('REGULATORY_PROVISIONS SCHEMA')
print('=' * 100)
print(f"{'Column Name':30s} {'Data Type':20s} {'Nullable':10s} {'Default'}")
print('-' * 100)
for row in cur.fetchall():
    default = row[2][:40] if row[2] else ''
    nullable = 'NULL' if row[3] == 'YES' else 'NOT NULL'
    print(f'{row[0]:30s} {row[1]:20s} {nullable:10s} {default}')

# Check for indexes and constraints
print('\n\nINDEXES AND CONSTRAINTS')
print('=' * 100)
cur.execute('''
SELECT
  indexname,
  indexdef
FROM pg_indexes
WHERE tablename = 'regulatory_provisions'
ORDER BY indexname;
''')

for row in cur.fetchall():
    print(f'\n{row[0]}:')
    print(f'  {row[1]}')

# Check for unique constraints
print('\n\nUNIQUE CONSTRAINTS')
print('=' * 100)
cur.execute('''
SELECT
  conname,
  pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'regulatory_provisions'::regclass
  AND contype = 'u';
''')

unique_constraints = cur.fetchall()
if unique_constraints:
    for row in unique_constraints:
        print(f'{row[0]}: {row[1]}')
else:
    print('❌ NO UNIQUE CONSTRAINTS FOUND')

# Check for foreign keys
print('\n\nFOREIGN KEY CONSTRAINTS')
print('=' * 100)
cur.execute('''
SELECT
  conname,
  pg_get_constraintdef(oid)
FROM pg_constraint
WHERE conrelid = 'regulatory_provisions'::regclass
  AND contype = 'f';
''')

fk_constraints = cur.fetchall()
if fk_constraints:
    for row in fk_constraints:
        print(f'{row[0]}: {row[1]}')
else:
    print('(No foreign keys on this table)')

conn.close()

print('\n' + '=' * 100)
print('SCHEMA ANALYSIS COMPLETE')
print('=' * 100)
