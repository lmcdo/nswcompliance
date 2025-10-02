#!/usr/bin/env python3
"""
Deep analysis of duplicate root causes
"""
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print('=' * 80)
print('DUPLICATE ROOT CAUSE ANALYSIS')
print('=' * 80)

# 1. By extraction method
print('\n1. By Extraction Method:')
print('-' * 80)
cur.execute('''
SELECT
  extraction_method,
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE is_canonical = FALSE) as duplicates,
  COUNT(*) FILTER (WHERE is_canonical = TRUE) as canonical
FROM regulatory_provisions
GROUP BY extraction_method
ORDER BY duplicates DESC;
''')

for row in cur.fetchall():
    method = row[0] or 'NULL'
    total, dups, canon = row[1], row[2], row[3]
    dup_pct = (dups / total * 100) if total > 0 else 0
    print(f'  {method:25s}: {total:6,} total | {canon:6,} canonical | {dups:6,} dups ({dup_pct:.1f}%)')

# 2. Document ID patterns
print('\n2. Document ID Patterns Causing Duplicates:')
print('-' * 80)
cur.execute('''
WITH duplicate_refs AS (
  SELECT document_id, ref_number, text_hash, COUNT(*) as cnt
  FROM regulatory_provisions
  GROUP BY document_id, ref_number, text_hash
  HAVING COUNT(*) > 1
)
SELECT
  CASE
    WHEN document_id LIKE '%_section_%' THEN 'Section Split'
    WHEN document_id LIKE '%_schedule_%' THEN 'Schedule Split'
    WHEN document_id LIKE '%_part_%' THEN 'Part Split'
    WHEN document_id LIKE '%___part%' THEN 'Triple Underscore Split'
    ELSE 'No Split Pattern'
  END as split_type,
  COUNT(DISTINCT document_id || ref_number) as duplicate_groups,
  SUM(cnt) as total_provisions
FROM duplicate_refs
GROUP BY split_type
ORDER BY duplicate_groups DESC;
''')

for row in cur.fetchall():
    print(f'  {row[0]:25s}: {row[1]:5,} groups, {row[2]:6,} total provisions')

# 3. Check Exempt/Complying document specifically
print('\n3. Exempt & Complying SEPP Duplicates:')
print('-' * 80)
cur.execute('''
SELECT
  document_id,
  COUNT(*) as total,
  COUNT(*) FILTER (WHERE is_canonical = FALSE) as duplicates
FROM regulatory_provisions
WHERE document_id LIKE '%Exempt%'
   OR document_id LIKE '%Complying%'
GROUP BY document_id
ORDER BY duplicates DESC
LIMIT 10;
''')

results = cur.fetchall()
if results:
    for row in results:
        doc = row[0][:60] + '...' if len(row[0]) > 60 else row[0]
        print(f'  {doc:65s}: {row[1]:4,} total, {row[2]:4,} dups')
else:
    print('  [No Exempt/Complying documents found]')

# 4. Sample duplicate that's breaking things
print('\n4. Example Duplicate Provision:')
print('-' * 80)
cur.execute('''
SELECT
  id,
  ref_number,
  LEFT(provision_text, 80) as text_preview,
  is_canonical,
  canonical_provision_id,
  document_id
FROM regulatory_provisions
WHERE ref_number IN (
  SELECT ref_number
  FROM regulatory_provisions
  GROUP BY ref_number, document_id, text_hash
  HAVING COUNT(*) > 1
  LIMIT 1
)
ORDER BY id
LIMIT 5;
''')

for row in cur.fetchall():
    print(f'\n  ID: {row[0]}')
    print(f'  Ref: {row[1]}')
    print(f'  Text: {row[2]}...')
    print(f'  Canonical: {row[3]}')
    print(f'  Points to: {row[4]}')
    print(f'  Doc: {row[5][:60]}...')

# 5. Check if foreign keys point to non-canonical
print('\n\n5. Foreign Key Integrity Check:')
print('-' * 80)
cur.execute('''
SELECT
  'development_controls' as table_name,
  COUNT(*) as total_refs,
  COUNT(*) FILTER (WHERE rp.is_canonical = FALSE) as points_to_duplicates
FROM development_controls dc
LEFT JOIN regulatory_provisions rp ON dc.provision_id = rp.id;
''')
row = cur.fetchone()
print(f'  {row[0]:30s}: {row[1]:6,} total refs, {row[2]:6,} point to duplicates')

cur.execute('''
SELECT
  'development_permissions' as table_name,
  COUNT(*) as total_refs,
  COUNT(*) FILTER (WHERE rp.is_canonical = FALSE) as points_to_duplicates
FROM development_permissions dp
LEFT JOIN regulatory_provisions rp ON dp.source_provision_id = rp.id
WHERE dp.source_provision_id IS NOT NULL;
''')
row = cur.fetchone()
if row:
    print(f'  {row[0]:30s}: {row[1]:6,} total refs, {row[2]:6,} point to duplicates')

conn.close()

print('\n' + '=' * 80)
print('ANALYSIS COMPLETE')
print('=' * 80)
