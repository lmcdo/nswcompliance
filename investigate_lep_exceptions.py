#!/usr/bin/env python3
"""Investigate LEP provisions with dev-type-specific rules."""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

print('='*80)
print('QUESTION 1: How to tag LEP exceptions like "residential flats 12m"?')
print('='*80)

# Find LEP provisions mentioning specific dev types
print('\n1. LEP PROVISIONS MENTIONING DEVELOPMENT TYPES')
print('-' * 80)

dev_type_keywords = [
    'residential flat',
    'dwelling house',
    'multi dwelling',
    'shop top',
    'boarding house',
    'secondary dwelling',
    'dual occupancy',
    'commercial',
    'industrial'
]

for keyword in dev_type_keywords:
    cursor.execute(f"""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id LIKE '%LEP%'
          AND LOWER(provision_text) LIKE '%{keyword}%'
    """)
    result = cursor.fetchone()
    if result['count'] > 0:
        print(f"  {keyword:<25} {result['count']:>6} LEP provisions")

# Sample provisions with dev type specific height rules
print('\n2. SAMPLE: LEP HEIGHT PROVISIONS WITH DEV TYPE SPECIFICITY')
print('-' * 80)
cursor.execute("""
    SELECT id, ref_number, section_header, provision_text
    FROM regulatory_provisions
    WHERE document_id LIKE '%LEP%'
      AND (
        LOWER(provision_text) LIKE '%height%'
        OR LOWER(section_header) LIKE '%height%'
      )
      AND (
        LOWER(provision_text) LIKE '%residential flat%'
        OR LOWER(provision_text) LIKE '%dwelling house%'
        OR LOWER(provision_text) LIKE '%multi dwelling%'
      )
    LIMIT 5
""")
rows = cursor.fetchall()
if rows:
    for i, r in enumerate(rows, 1):
        print(f"\n  [{i}] ID: {r['id']}")
        print(f"      Ref: {r['ref_number']}")
        print(f"      Section: {r['section_header'][:70] if r['section_header'] else 'N/A'}")
        print(f"      Text snippet: {r['provision_text'][:150] if r['provision_text'] else 'N/A'}...")
else:
    print("  No dev-type-specific height provisions found")

# Sample FSR provisions
print('\n3. SAMPLE: LEP FSR PROVISIONS WITH DEV TYPE SPECIFICITY')
print('-' * 80)
cursor.execute("""
    SELECT id, ref_number, section_header, provision_text
    FROM regulatory_provisions
    WHERE document_id LIKE '%LEP%'
      AND (
        LOWER(provision_text) LIKE '%floor space%'
        OR LOWER(provision_text) LIKE '%fsr%'
        OR LOWER(section_header) LIKE '%floor space%'
      )
      AND (
        LOWER(provision_text) LIKE '%residential flat%'
        OR LOWER(provision_text) LIKE '%shop top%'
        OR LOWER(provision_text) LIKE '%commercial%'
      )
    LIMIT 5
""")
rows = cursor.fetchall()
if rows:
    for i, r in enumerate(rows, 1):
        print(f"\n  [{i}] ID: {r['id']}")
        print(f"      Ref: {r['ref_number']}")
        print(f"      Section: {r['section_header'][:70] if r['section_header'] else 'N/A'}")
        print(f"      Text snippet: {r['provision_text'][:150] if r['provision_text'] else 'N/A'}...")
else:
    print("  No dev-type-specific FSR provisions found")

# Check current development_type tagging in LEP
print('\n4. CURRENT: LEP provisions with development_type tagged')
print('-' * 80)
cursor.execute("""
    SELECT development_type, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id LIKE '%LEP%'
      AND development_type IS NOT NULL
    GROUP BY development_type
    ORDER BY count DESC
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  {r['development_type']:<30} {r['count']:>6} provisions")
else:
    print("  No LEP provisions have development_type tagged")

# How many LEP provisions total?
cursor.execute("""
    SELECT COUNT(*) as total
    FROM regulatory_provisions
    WHERE document_id LIKE '%LEP%'
""")
total_lep = cursor.fetchone()['total']
print(f"\n  Total LEP provisions: {total_lep}")

# Check clauses 4.3 and 4.4 specifically
print('\n5. CLAUSES 4.3 (HEIGHT) AND 4.4 (FSR) - DEV TYPE VARIANTS?')
print('-' * 80)
cursor.execute("""
    SELECT ref_number, section_header, provision_text
    FROM regulatory_provisions
    WHERE document_id LIKE '%LEP%'
      AND (ref_number LIKE '4.3%' OR ref_number LIKE '4.4%')
    LIMIT 10
""")
rows = cursor.fetchall()
for r in rows:
    print(f"\n  Ref: {r['ref_number']}")
    print(f"  Section: {r['section_header'][:70] if r['section_header'] else 'N/A'}")
    print(f"  Text: {r['provision_text'][:200] if r['provision_text'] else 'N/A'}...")

print('\n' + '='*80)
print('TAGGING STRATEGY')
print('='*80)
print("""
Approach 1: Text Pattern Matching (Simple)
-----------------------------------------
UPDATE regulatory_provisions
SET development_type = 'residential_flat_building'
WHERE document_id LIKE '%LEP%'
  AND LOWER(provision_text) LIKE '%residential flat building%';

Pros: Easy to implement
Cons: May miss variations, over-tag general provisions

Approach 2: Manual Tagging with Review (Accurate)
-------------------------------------------------
1. Export all LEP provisions mentioning dev types
2. Manually review and tag each one
3. Import tags back to database

Pros: 100% accurate
Cons: Time-consuming

Approach 3: NLP Entity Extraction (Advanced)
--------------------------------------------
Use entity recognition to identify when a provision is specifically
scoped to a development type vs just mentioning it.

Pros: Can distinguish "applies to X" vs "mentions X"
Cons: Complex, requires ML model
""")

cursor.close()
conn.close()