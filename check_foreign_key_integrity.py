#!/usr/bin/env python3
"""Check if foreign keys point to non-canonical provisions"""
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print('=' * 80)
print('FOREIGN KEY INTEGRITY CHECK')
print('=' * 80)

# Check development_controls
print('\n1. development_controls table:')
print('-' * 80)

cur.execute('''
SELECT column_name, data_type
FROM information_schema.columns
WHERE table_name = 'development_controls'
  AND column_name IN ('id', 'provision_id');
''')
print('  Schema:')
for row in cur.fetchall():
    print(f'    {row[0]}: {row[1]}')

cur.execute('SELECT COUNT(*) FROM development_controls;')
total = cur.fetchone()[0]
print(f'\n  Total controls: {total:,}')

# Check if provision_id points to non-canonical
cur.execute('''
SELECT COUNT(*)
FROM development_controls dc
WHERE dc.provision_id IN (
  SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
);
''')
orphaned = cur.fetchone()[0]
print(f'  Controls pointing to NON-CANONICAL provisions: {orphaned:,}')

if orphaned > 0:
    print(f'\n  [WARNING] {orphaned} controls reference duplicate provisions!')
    print('  These will be invisible when using regulatory_provisions_canonical view')

# Sample some orphaned controls
if orphaned > 0:
    cur.execute('''
    SELECT
      dc.id,
      dc.provision_id,
      rp.ref_number,
      rp.canonical_provision_id,
      dc.control_type,
      dc.value_numeric
    FROM development_controls dc
    JOIN regulatory_provisions rp ON dc.provision_id = rp.id::text
    WHERE rp.is_canonical = FALSE
    LIMIT 10;
    ''')

    print('\n  Sample orphaned controls:')
    for row in cur.fetchall():
        print(f'    Control ID {row[0]}: points to provision {row[1]} (duplicate of {row[3]})')
        print(f'      Ref: {row[2]}, Type: {row[4]}, Value: {row[5]}')

# Check development_permissions
print('\n\n2. development_permissions table:')
print('-' * 80)

cur.execute('SELECT COUNT(*) FROM development_permissions;')
total = cur.fetchone()[0]
print(f'  Total permissions: {total:,}')

cur.execute('''
SELECT COUNT(*)
FROM development_permissions
WHERE source_provision_id IS NOT NULL;
''')
with_source = cur.fetchone()[0]
print(f'  Permissions with source_provision_id: {with_source:,}')

conn.close()

print('\n' + '=' * 80)
print('CHECK COMPLETE')
print('=' * 80)
