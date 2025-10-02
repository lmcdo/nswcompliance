#!/usr/bin/env python3
"""
SAFE ANALYSIS: Understand duplicate patterns without modifying database
"""
from db_config import get_connection
import hashlib

conn = get_connection()
cur = conn.cursor()

print("=" * 100)
print("DUPLICATE PATTERN ANALYSIS (READ-ONLY)")
print("=" * 100)

# 1. How many total provisions?
cur.execute("SELECT COUNT(*) FROM regulatory_provisions;")
total = cur.fetchone()[0]
print(f"\n1. TOTAL PROVISIONS: {total:,}")

# 2. How many unique (document_id, ref_number) combinations?
cur.execute("""
SELECT COUNT(DISTINCT (document_id, ref_number))
FROM regulatory_provisions;
""")
unique_combos = cur.fetchone()[0]
print(f"   UNIQUE (document_id, ref_number) combinations: {unique_combos:,}")
print(f"   POTENTIAL DUPLICATES: {total - unique_combos:,} ({(total - unique_combos) / total * 100:.1f}%)")

# 3. Breakdown by duplicate type
print("\n2. DUPLICATE BREAKDOWN BY TYPE:")
print("-" * 100)

# Type A: Exact same text, same document, same ref_number (TRUE duplicates)
cur.execute("""
WITH text_hashes AS (
  SELECT
    id,
    document_id,
    ref_number,
    md5(provision_text) as text_hash
  FROM regulatory_provisions
),
duplicate_groups AS (
  SELECT
    document_id,
    ref_number,
    text_hash,
    COUNT(*) as count
  FROM text_hashes
  GROUP BY document_id, ref_number, text_hash
  HAVING COUNT(*) > 1
)
SELECT
  COUNT(*) as duplicate_groups,
  SUM(count) as total_duplicate_records,
  SUM(count - 1) as excess_records
FROM duplicate_groups;
""")
result = cur.fetchone()
print(f"   TYPE A (TRUE DUPLICATES - same text, same doc, same ref):")
print(f"     Groups: {result[0]:,}")
print(f"     Total records: {result[1]:,}")
print(f"     Excess records: {result[2]:,}")

# Type B: Different text, same document, same ref_number (SUBSECTION COLLAPSE)
cur.execute("""
WITH text_hashes AS (
  SELECT
    id,
    document_id,
    ref_number,
    md5(provision_text) as text_hash
  FROM regulatory_provisions
),
different_text_groups AS (
  SELECT
    document_id,
    ref_number,
    COUNT(DISTINCT text_hash) as unique_texts,
    COUNT(*) as total_records
  FROM text_hashes
  GROUP BY document_id, ref_number
  HAVING COUNT(DISTINCT text_hash) > 1
)
SELECT
  COUNT(*) as affected_ref_numbers,
  SUM(total_records) as total_records,
  AVG(unique_texts) as avg_unique_texts_per_ref
FROM different_text_groups;
""")
result = cur.fetchone()
print(f"\n   TYPE B (SUBSECTION COLLAPSE - different text, same ref):")
print(f"     Affected ref_numbers: {result[0]:,}")
print(f"     Total records: {result[1]:,}")
print(f"     Avg unique texts per ref: {result[2]:.1f}")

# Type C: Cross-reference arrow in ref_number
cur.execute("""
SELECT COUNT(*)
FROM regulatory_provisions
WHERE ref_number LIKE '%->%';
""")
arrow_count = cur.fetchone()[0]
print(f"\n   TYPE C (CROSS-REF ARROWS in ref_number):")
print(f"     Records with '->' in ref_number: {arrow_count:,}")

# Check if these are duplicates
cur.execute("""
WITH arrow_provisions AS (
  SELECT
    id,
    REGEXP_REPLACE(ref_number, '\s*->.*$', '') as base_ref_number,
    document_id,
    md5(provision_text) as text_hash
  FROM regulatory_provisions
  WHERE ref_number LIKE '%->%'
)
SELECT COUNT(*)
FROM arrow_provisions ap
JOIN regulatory_provisions rp
  ON ap.document_id = rp.document_id
  AND ap.base_ref_number = rp.ref_number
  AND md5(rp.provision_text) = ap.text_hash
WHERE rp.ref_number NOT LIKE '%->%';
""")
arrow_duplicates = cur.fetchone()[0]
print(f"     Of these, {arrow_duplicates:,} are TRUE duplicates (same text exists without arrow)")

# 4. Sample duplicate groups for inspection
print("\n3. SAMPLE DUPLICATE GROUPS:")
print("-" * 100)

cur.execute("""
WITH text_hashes AS (
  SELECT
    id,
    document_id,
    ref_number,
    LEFT(provision_text, 80) as text_preview,
    md5(provision_text) as text_hash,
    extraction_method,
    created_at
  FROM regulatory_provisions
),
duplicate_groups AS (
  SELECT
    document_id,
    ref_number,
    text_hash,
    COUNT(*) as count
  FROM text_hashes
  GROUP BY document_id, ref_number, text_hash
  HAVING COUNT(*) > 1
)
SELECT
  th.id,
  th.ref_number,
  th.text_preview,
  th.extraction_method,
  th.created_at,
  dg.count as total_in_group
FROM text_hashes th
JOIN duplicate_groups dg
  ON th.document_id = dg.document_id
  AND th.ref_number = dg.ref_number
  AND th.text_hash = dg.text_hash
ORDER BY dg.count DESC, th.ref_number, th.id
LIMIT 20;
""")

current_group = None
for row in cur.fetchall():
    group_key = f"{row[1]}_{row[5]}"
    if group_key != current_group:
        current_group = group_key
        print(f"\n   GROUP: {row[1]} ({row[5]} duplicates)")
        print("   " + "-" * 90)
    print(f"     ID {row[0]:5d} | {row[3]:12s} | {row[4]} | {row[2]}...")

# 5. Impact assessment
print("\n4. SAFE DEDUPLICATION IMPACT:")
print("-" * 100)

cur.execute("""
WITH text_hashes AS (
  SELECT
    id,
    document_id,
    ref_number,
    md5(provision_text) as text_hash,
    extraction_method,
    created_at,
    ROW_NUMBER() OVER (
      PARTITION BY document_id, ref_number, md5(provision_text)
      ORDER BY
        CASE extraction_method
          WHEN 'manual' THEN 1
          WHEN 'autoschema' THEN 2
          WHEN 'mineru' THEN 3
          ELSE 4
        END,
        created_at ASC
    ) as priority_rank
  FROM regulatory_provisions
)
SELECT
  SUM(CASE WHEN priority_rank = 1 THEN 1 ELSE 0 END) as would_keep,
  SUM(CASE WHEN priority_rank > 1 THEN 1 ELSE 0 END) as would_mark_duplicate,
  COUNT(*) as total
FROM text_hashes;
""")
result = cur.fetchone()
print(f"   Would KEEP as canonical: {result[0]:,} provisions")
print(f"   Would MARK as duplicate: {result[1]:,} provisions")
print(f"   Total provisions: {result[2]:,}")
print(f"   Data loss: 0 provisions (all preserved with is_canonical flag)")

# 6. Check for problematic patterns
print("\n5. POTENTIAL ISSUES TO RESOLVE:")
print("-" * 100)

# Check for provisions with no ref_number
cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE ref_number IS NULL OR ref_number = '';")
no_ref = cur.fetchone()[0]
print(f"   ⚠ Provisions with no ref_number: {no_ref:,}")

# Check for provisions with no document_id
cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE document_id IS NULL OR document_id = '';")
no_doc = cur.fetchone()[0]
print(f"   ⚠ Provisions with no document_id: {no_doc:,}")

# Check for extremely long ref_numbers (likely include full text)
cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE LENGTH(ref_number) > 100;")
long_ref = cur.fetchone()[0]
print(f"   ⚠ Provisions with ref_number > 100 chars: {long_ref:,}")

if long_ref > 0:
    print("     Sample:")
    cur.execute("SELECT id, LEFT(ref_number, 100) FROM regulatory_provisions WHERE LENGTH(ref_number) > 100 LIMIT 3;")
    for row in cur.fetchall():
        print(f"       ID {row[0]}: {row[1]}...")

conn.close()

print("\n" + "=" * 100)
print("ANALYSIS COMPLETE - NO CHANGES MADE TO DATABASE")
print("=" * 100)
