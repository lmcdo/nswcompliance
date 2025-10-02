#!/usr/bin/env python3
"""
Fix orphaned duplicates from Phase 2A migration
================================================
Issue: Some duplicates point to other duplicates instead of canonical provisions
"""
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print('=' * 80)
print('FIXING ORPHANED DUPLICATES')
print('=' * 80)

# Find and fix orphaned duplicates
# Strategy: Re-link to the correct canonical provision
cur.execute('''
WITH orphaned AS (
  SELECT
    dup.id as dup_id,
    dup.document_id,
    dup.ref_number,
    md5(dup.provision_text) as text_hash,
    dup.canonical_provision_id as old_canonical_id
  FROM regulatory_provisions dup
  LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
  WHERE dup.is_canonical = FALSE
    AND (canonical.id IS NULL OR canonical.is_canonical = FALSE)
),
correct_canonical AS (
  SELECT DISTINCT ON (o.dup_id)
    o.dup_id,
    o.old_canonical_id,
    rp.id as correct_canonical_id
  FROM orphaned o
  JOIN regulatory_provisions rp
    ON o.document_id = rp.document_id
    AND o.ref_number = rp.ref_number
    AND md5(rp.provision_text) = o.text_hash
    AND rp.is_canonical = TRUE
  ORDER BY o.dup_id, rp.created_at ASC, rp.id ASC
)
UPDATE regulatory_provisions
SET canonical_provision_id = correct_canonical.correct_canonical_id
FROM correct_canonical
WHERE regulatory_provisions.id = correct_canonical.dup_id;
''')

fixed = cur.rowcount
print(f'\n[INFO] Re-linked {fixed} orphaned duplicates to correct canonical provisions')

# Check if any remain orphaned (couldn't find canonical)
cur.execute('''
SELECT COUNT(*)
FROM regulatory_provisions dup
LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
WHERE dup.is_canonical = FALSE
  AND (canonical.id IS NULL OR canonical.is_canonical = FALSE);
''')

remaining = cur.fetchone()[0]

if remaining > 0:
    print(f'[WARNING] {remaining} duplicates still orphaned (no canonical found)')

    # Show them
    cur.execute('''
    SELECT
      dup.id,
      dup.ref_number,
      dup.document_id,
      LEFT(dup.provision_text, 60) as text
    FROM regulatory_provisions dup
    LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
    WHERE dup.is_canonical = FALSE
      AND (canonical.id IS NULL OR canonical.is_canonical = FALSE)
    LIMIT 10;
    ''')

    print('\n  Still orphaned:')
    for row in cur.fetchall():
        print(f'    ID {row[0]:5d}: {row[1]:30s}')
        print(f'             Doc: {row[2][:50]}')
        print(f'             Text: {row[3]}...')

    # These might need to be marked as canonical instead
    print('\n  Suggested fix: Mark remaining orphans as canonical')

    response = input('\n  Mark remaining orphans as canonical? (yes/no): ')
    if response.lower() == 'yes':
        cur.execute('''
        UPDATE regulatory_provisions
        SET
            is_canonical = TRUE,
            canonical_provision_id = NULL
        WHERE is_canonical = FALSE
          AND canonical_provision_id IN (
            SELECT id FROM regulatory_provisions WHERE is_canonical = FALSE
          );
        ''')
        marked_canonical = cur.rowcount
        print(f'  [SUCCESS] Marked {marked_canonical} orphans as canonical')
else:
    print(f'[SUCCESS] All duplicates properly linked!')

# Commit changes
conn.commit()

# Final verification
cur.execute('''
SELECT
  COUNT(*) FILTER (WHERE is_canonical = TRUE) as canonical,
  COUNT(*) FILTER (WHERE is_canonical = FALSE) as duplicates,
  COUNT(*) as total
FROM regulatory_provisions;
''')

row = cur.fetchone()
print(f'\n[FINAL COUNTS]')
print(f'  Canonical: {row[0]:,} ({row[0]/row[2]*100:.1f}%)')
print(f'  Duplicates: {row[1]:,} ({row[1]/row[2]*100:.1f}%)')
print(f'  Total: {row[2]:,}')

conn.close()

print('\n' + '=' * 80)
print('FIX COMPLETE')
print('=' * 80)
print('\nRun post-verification again:')
print('  python verify_phase2a_migration.py post')
