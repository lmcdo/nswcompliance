#!/usr/bin/env python3
"""Quick check of migration results"""
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print("=" * 80)
print("MIGRATION RESULTS CHECK")
print("=" * 80)

# Check for actual circular references (duplicates pointing to duplicates)
cur.execute('''
SELECT COUNT(*)
FROM regulatory_provisions dup
JOIN regulatory_provisions target ON dup.canonical_provision_id = target.id
WHERE dup.is_canonical = FALSE
  AND target.is_canonical = FALSE;
''')
circular = cur.fetchone()[0]
print(f'\n[CHECK] Duplicates pointing to duplicates: {circular}')
if circular == 0:
    print("        [PASS] No circular references")
else:
    print(f"        [FAIL] {circular} circular references found!")

# Check for orphaned (pointing to NULL or non-existent)
cur.execute('''
SELECT COUNT(*)
FROM regulatory_provisions dup
LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
WHERE dup.is_canonical = FALSE
  AND (canonical.id IS NULL OR canonical.is_canonical = FALSE);
''')
orphaned = cur.fetchone()[0]
print(f'\n[CHECK] Orphaned duplicates: {orphaned}')
if orphaned == 0:
    print("        [PASS] No orphaned duplicates")
else:
    print(f"        [FAIL] {orphaned} orphaned duplicates found!")

# Check counts
cur.execute('''
SELECT
  COUNT(*) FILTER (WHERE is_canonical = TRUE) as canonical,
  COUNT(*) FILTER (WHERE is_canonical = FALSE) as duplicates,
  COUNT(*) as total
FROM regulatory_provisions;
''')
row = cur.fetchone()
print(f'\n[COUNTS]')
print(f'  Total provisions: {row[2]:,}')
print(f'  Canonical: {row[0]:,} ({row[0]/row[2]*100:.1f}%)')
print(f'  Duplicates: {row[1]:,} ({row[1]/row[2]*100:.1f}%)')

# Sample duplicate groups
print(f'\n[SAMPLE] Top 3 duplicate groups:')
cur.execute('''
SELECT
  canonical.ref_number,
  LEFT(canonical.provision_text, 60) as text,
  COUNT(*) as dup_count
FROM regulatory_provisions dup
JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
WHERE dup.is_canonical = FALSE
GROUP BY canonical.id, canonical.ref_number, canonical.provision_text
ORDER BY COUNT(*) DESC
LIMIT 3;
''')
for i, row in enumerate(cur.fetchall(), 1):
    print(f'  {i}. {row[0]:30s} ({row[2]} duplicates)')
    print(f'     "{row[1]}..."')

print("\n" + "=" * 80)
print("CHECK COMPLETE")
print("=" * 80)

conn.close()
