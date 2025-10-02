#!/usr/bin/env python3
"""
Deep analysis of duplication patterns to understand root cause
"""
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print("=" * 100)
print("DEEP DUPLICATION ANALYSIS")
print("=" * 100)

# 1. Check the exact structure of the 6 duplicates
print("\n1. SCHEDULE 4, SECTION 1.4 - ALL 6 DUPLICATES")
print("-" * 100)
cur.execute('''
SELECT
  id,
  ref_number,
  LEFT(provision_text, 80) as text_preview,
  extraction_method,
  created_at,
  SUBSTRING(document_id FROM POSITION('section_' IN document_id)) as doc_section
FROM regulatory_provisions
WHERE ref_number = 'Schedule 4, section 1.4'
ORDER BY id;
''')

for row in cur.fetchall():
    print(f"ID {row[0]:5d} | {row[3]:12s} | {row[5]:20s} | {row[4]}")
    print(f"         Text: {row[1]}")
    print(f"              {row[2]}...")
    print()

# 2. Check extraction method timeline
print("\n2. EXTRACTION METHOD TIMELINE")
print("-" * 100)
cur.execute('''
SELECT
  extraction_method,
  COUNT(*) as count,
  MIN(created_at) as first_insert,
  MAX(created_at) as last_insert
FROM regulatory_provisions
WHERE document_id LIKE '%Sustainable_Buildings_2022%'
GROUP BY extraction_method
ORDER BY first_insert;
''')

for row in cur.fetchall():
    print(f"{row[0]:15s}: {row[1]:4d} provisions | First: {row[2]} | Last: {row[3]}")

# 3. Check if duplicates have different provision_text
print("\n3. ARE DUPLICATES IDENTICAL TEXT?")
print("-" * 100)
cur.execute('''
SELECT
  ref_number,
  COUNT(*) as total_count,
  COUNT(DISTINCT provision_text) as unique_texts,
  COUNT(DISTINCT extraction_method) as unique_methods
FROM regulatory_provisions
WHERE document_id LIKE '%Sustainable_Buildings_2022%'
GROUP BY ref_number
HAVING COUNT(*) > 1
ORDER BY total_count DESC
LIMIT 10;
''')

print(f"{'Ref Number':50s} | Total | Unique Texts | Methods")
print("-" * 100)
for row in cur.fetchall():
    marker = " ⚠️ DIFFERENT TEXT" if row[2] > 1 else ""
    print(f"{row[0]:50s} | {row[1]:5d} | {row[2]:12d} | {row[3]:7d}{marker}")

# 4. Sample one duplicate set to see the difference
print("\n4. SAMPLE DUPLICATE COMPARISON: Section 11(2)")
print("-" * 100)
cur.execute('''
SELECT
  id,
  ref_number,
  provision_text,
  extraction_method
FROM regulatory_provisions
WHERE ref_number IN ('Section 11(2)', 'Section 11(2) -> Sections 8(1), 9(1), 9(2), 10(1)')
ORDER BY id;
''')

provisions = cur.fetchall()
for i, row in enumerate(provisions):
    print(f"\n--- DUPLICATE #{i+1} (ID {row[0]}) [{row[3]}] ---")
    print(f"Ref: {row[1]}")
    print(f"Text: {row[2][:200]}...")

if len(provisions) >= 2:
    print(f"\n--- COMPARISON ---")
    print(f"Same text? {provisions[0][2] == provisions[1][2]}")
    print(f"Ref differs? {provisions[0][1] != provisions[1][1]}")

# 5. Check document_id patterns
print("\n5. DOCUMENT_ID PATTERNS FOR DUPLICATES")
print("-" * 100)
cur.execute('''
SELECT
  id,
  ref_number,
  document_id
FROM regulatory_provisions
WHERE ref_number = 'Section 11(2)'
   OR ref_number = 'Section 11(2) -> Sections 8(1), 9(1), 9(2), 10(1)'
ORDER BY id;
''')

for row in cur.fetchall():
    doc_parts = row[2].split('___')
    print(f"ID {row[0]:5d}: {row[1]:60s}")
    print(f"         Document: {doc_parts[0] if len(doc_parts) > 0 else 'N/A'}")
    print(f"         Section:  {doc_parts[1] if len(doc_parts) > 1 else 'N/A'}")
    print()

conn.close()

print("\n" + "=" * 100)
print("DIAGNOSIS COMPLETE")
print("=" * 100)
