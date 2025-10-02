#!/usr/bin/env python3
"""Check and fix orphaned duplicates from Phase 2A"""
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print('=' * 80)
print('ORPHANED DUPLICATES ANALYSIS')
print('=' * 80)

# Find orphaned duplicates
cur.execute('''
SELECT
  dup.id,
  dup.ref_number,
  dup.canonical_provision_id,
  dup.migration_phase,
  canonical.id as pointed_to_id,
  canonical.is_canonical as pointed_to_canonical
FROM regulatory_provisions dup
LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
WHERE dup.is_canonical = FALSE
  AND (canonical.id IS NULL OR canonical.is_canonical = FALSE)
ORDER BY dup.id
LIMIT 15;
''')

orphaned = cur.fetchall()
print(f'\nFound {len(orphaned)} orphaned duplicates:')
for row in orphaned:
    print(f'  ID {row[0]:5d}: {row[1]:30s}')
    print(f'           Points to: {row[2]} (exists: {row[4] is not None}, canonical: {row[5]})')

# Check the root cause
print(f'\n\nROOT CAUSE ANALYSIS')
print('-' * 80)

# Are these from Phase 2A?
cur.execute('''
SELECT
  migration_phase,
  COUNT(*) as count
FROM regulatory_provisions dup
LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
WHERE dup.is_canonical = FALSE
  AND (canonical.id IS NULL OR canonical.is_canonical = FALSE)
GROUP BY migration_phase;
''')

for row in cur.fetchall():
    print(f'  {row[0] or "NULL":20s}: {row[1]} orphaned')

# Fix strategy: Re-link orphaned to correct canonical
print(f'\n\nFIX STRATEGY')
print('-' * 80)

cur.execute('''
WITH orphaned AS (
  SELECT
    dup.id as dup_id,
    dup.document_id,
    dup.ref_number,
    md5(dup.provision_text) as text_hash
  FROM regulatory_provisions dup
  LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
  WHERE dup.is_canonical = FALSE
    AND (canonical.id IS NULL OR canonical.is_canonical = FALSE)
),
correct_canonical AS (
  SELECT DISTINCT ON (o.document_id, o.ref_number, o.text_hash)
    o.dup_id,
    rp.id as correct_canonical_id
  FROM orphaned o
  JOIN regulatory_provisions rp
    ON o.document_id = rp.document_id
    AND o.ref_number = rp.ref_number
    AND md5(rp.provision_text) = o.text_hash
    AND rp.is_canonical = TRUE
  ORDER BY o.document_id, o.ref_number, o.text_hash, rp.created_at ASC
)
SELECT
  COUNT(*) as fixable,
  COUNT(DISTINCT correct_canonical_id) as unique_canonicals
FROM correct_canonical;
''')

row = cur.fetchone()
print(f'  Fixable orphans: {row[0]}')
print(f'  Unique canonicals to link to: {row[1]}')

# Show what would be fixed
cur.execute('''
WITH orphaned AS (
  SELECT
    dup.id as dup_id,
    dup.document_id,
    dup.ref_number,
    md5(dup.provision_text) as text_hash
  FROM regulatory_provisions dup
  LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
  WHERE dup.is_canonical = FALSE
    AND (canonical.id IS NULL OR canonical.is_canonical = FALSE)
),
correct_canonical AS (
  SELECT DISTINCT ON (o.document_id, o.ref_number, o.text_hash)
    o.dup_id,
    rp.id as correct_canonical_id,
    rp.ref_number
  FROM orphaned o
  JOIN regulatory_provisions rp
    ON o.document_id = rp.document_id
    AND o.ref_number = rp.ref_number
    AND md5(rp.provision_text) = o.text_hash
    AND rp.is_canonical = TRUE
  ORDER BY o.document_id, o.ref_number, o.text_hash, rp.created_at ASC
)
SELECT * FROM correct_canonical LIMIT 5;
''')

print(f'\n  Sample fixes:')
for row in cur.fetchall():
    print(f'    Orphan ID {row[0]} -> Canonical ID {row[1]} ({row[2]})')

conn.close()

print('\n' + '=' * 80)
print('To fix, run: python fix_orphaned_duplicates.py')
print('=' * 80)
