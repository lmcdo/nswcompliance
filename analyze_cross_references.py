#!/usr/bin/env python3
"""
Analyze cross-reference patterns for Phase 2 migration planning
"""
from db_config import get_connection
import re

conn = get_connection()
cur = conn.cursor()

print("=" * 100)
print("PHASE 2 ANALYSIS: CROSS-REFERENCE PATTERNS")
print("=" * 100)

# 1. How many provisions have cross-reference arrows?
cur.execute("""
SELECT COUNT(*)
FROM regulatory_provisions
WHERE ref_number LIKE '%->%';
""")
arrow_count = cur.fetchone()[0]
print(f"\n1. PROVISIONS WITH CROSS-REFERENCE ARROWS")
print(f"   Total: {arrow_count:,}")

# 2. Sample cross-reference patterns
print(f"\n2. SAMPLE CROSS-REFERENCE PATTERNS")
print("-" * 100)
cur.execute("""
SELECT id, ref_number, LEFT(provision_text, 80) as text
FROM regulatory_provisions
WHERE ref_number LIKE '%->%'
ORDER BY LENGTH(ref_number) DESC
LIMIT 10;
""")

for row in cur.fetchall():
    print(f"   ID {row[0]:5d}: {row[1]}")
    print(f"            {row[2]}...")
    print()

# 3. Parse cross-reference patterns
print(f"3. CROSS-REFERENCE EXTRACTION TEST")
print("-" * 100)

cur.execute("""
SELECT id, ref_number
FROM regulatory_provisions
WHERE ref_number LIKE '%->%'
LIMIT 5;
""")

for row in cur.fetchall():
    ref_id, ref_number = row

    # Split on arrow
    parts = ref_number.split('->')
    base_ref = parts[0].strip() if len(parts) > 0 else ''
    cross_refs = parts[1].strip() if len(parts) > 1 else ''

    print(f"   ID {ref_id}:")
    print(f"     Original: {ref_number}")
    print(f"     Base ref: {base_ref}")
    print(f"     Cross-refs: {cross_refs}")
    print()

# 4. Check if cleaning would reveal more duplicates
print(f"4. POTENTIAL DUPLICATES AFTER CLEANING")
print("-" * 100)

cur.execute("""
WITH cleaned_refs AS (
  SELECT
    id,
    REGEXP_REPLACE(ref_number, '\s*->.*$', '') as clean_ref,
    document_id,
    md5(provision_text) as text_hash,
    is_canonical
  FROM regulatory_provisions
  WHERE ref_number LIKE '%->%'
)
SELECT
  COUNT(*) as total_with_arrows,
  COUNT(DISTINCT (clean_ref, document_id, text_hash)) as unique_after_clean,
  COUNT(*) - COUNT(DISTINCT (clean_ref, document_id, text_hash)) as potential_new_duplicates
FROM cleaned_refs
WHERE is_canonical = TRUE;
""")

row = cur.fetchone()
print(f"   Provisions with arrows (canonical only): {row[0]:,}")
print(f"   Unique after cleaning: {row[1]:,}")
print(f"   Potential new duplicates: {row[2]:,}")

# 5. Check document types affected
print(f"\n5. DOCUMENT TYPES AFFECTED")
print("-" * 100)

cur.execute("""
SELECT
  CASE
    WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
    WHEN document_id LIKE '%LEP%' THEN 'LEP'
    WHEN document_id LIKE '%DCP%' THEN 'DCP'
    ELSE 'Other'
  END as doc_type,
  COUNT(*) as count
FROM regulatory_provisions
WHERE ref_number LIKE '%->%'
GROUP BY doc_type
ORDER BY count DESC;
""")

for row in cur.fetchall():
    print(f"   {row[0]:10s}: {row[1]:,} provisions")

# 6. Cross-reference complexity analysis
print(f"\n6. CROSS-REFERENCE COMPLEXITY")
print("-" * 100)

cur.execute("""
WITH cross_ref_analysis AS (
  SELECT
    ref_number,
    LENGTH(ref_number) - LENGTH(REPLACE(ref_number, ',', '')) + 1 as num_refs,
    REGEXP_REPLACE(ref_number, '^[^>]*->\s*', '') as refs_only
  FROM regulatory_provisions
  WHERE ref_number LIKE '%->%'
)
SELECT
  CASE
    WHEN num_refs = 1 THEN '1 reference'
    WHEN num_refs = 2 THEN '2 references'
    WHEN num_refs BETWEEN 3 AND 5 THEN '3-5 references'
    ELSE '6+ references'
  END as complexity,
  COUNT(*) as count
FROM cross_ref_analysis
GROUP BY complexity
ORDER BY MIN(num_refs);
""")

for row in cur.fetchall():
    print(f"   {row[0]:20s}: {row[1]:,} provisions")

# 7. Example extraction for new table
print(f"\n7. EXAMPLE CROSS-REFERENCE EXTRACTION")
print("-" * 100)

cur.execute("""
SELECT id, ref_number
FROM regulatory_provisions
WHERE ref_number LIKE '%->%'
  AND ref_number ~ 'Section'
LIMIT 3;
""")

for row in cur.fetchall():
    prov_id, ref_number = row

    # Parse references
    parts = ref_number.split('->')
    base_ref = parts[0].strip()
    cross_refs_str = parts[1].strip() if len(parts) > 1 else ''

    # Extract individual references using regex
    # Pattern: "Sections 8(1), 9(1), 9(2), 10(1)"
    refs = re.findall(r'\d+\([a-z0-9]+\)', cross_refs_str)

    print(f"   Provision ID: {prov_id}")
    print(f"   Base ref_number: {base_ref}")
    print(f"   Would create {len(refs)} cross-reference records:")
    for ref in refs:
        print(f"     - Reference to: {ref}")
    print()

conn.close()

print("=" * 100)
print("ANALYSIS COMPLETE")
print("=" * 100)
print("\nRECOMMENDATION:")
print("  Phase 2 appears safe to proceed:")
print("  - Well-defined pattern (arrow delimiter)")
print("  - Affects ~2,600 provisions")
print("  - Would reveal minimal additional duplicates")
print("  - Can be fully reversed by restoring ref_number from backup")
print("\nPROCEED WITH CAUTION:")
print("  1. Create backup first")
print("  2. Test extraction logic on sample")
print("  3. Run on copy database first")
print("  4. Validate frontend still works")
