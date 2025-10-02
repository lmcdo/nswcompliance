#!/usr/bin/env python3
"""Check actual development type data samples."""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

print('='*80)
print('ACTUAL DEVELOPMENT TYPE DATA SAMPLES')
print('='*80)

# Get DCP document IDs
print('\n1. DCP DOCUMENT IDs')
print('-' * 80)
cursor.execute("""
    SELECT DISTINCT document_id
    FROM regulatory_provisions
    WHERE document_id LIKE '%DCP%'
    LIMIT 10
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['document_id']}")

# Get sample dwelling_house provisions from DCP
print('\n2. SAMPLE: dwelling_house DCP PROVISIONS')
print('-' * 80)
cursor.execute("""
    SELECT id, document_id, ref_number, section_header, provision_text
    FROM regulatory_provisions
    WHERE development_type = 'dwelling_house'
      AND document_id LIKE '%DCP%'
    LIMIT 3
""")
rows = cursor.fetchall()
for i, r in enumerate(rows, 1):
    print(f"\n  [{i}] ID: {r['id']}")
    print(f"      Doc: {r['document_id'][:70]}")
    print(f"      Ref: {r['ref_number']}")
    print(f"      Section: {r['section_header'][:70] if r['section_header'] else 'N/A'}")
    print(f"      Text: {r['provision_text'][:120] if r['provision_text'] else 'N/A'}...")

# Check what document types we have
print('\n3. DOCUMENT TYPE DISTRIBUTION')
print('-' * 80)
cursor.execute("""
    SELECT
        CASE
            WHEN document_id LIKE '%DCP%' THEN 'DCP'
            WHEN document_id LIKE '%LEP%' THEN 'LEP'
            WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
            ELSE 'OTHER'
        END as doc_type,
        COUNT(*) as count
    FROM regulatory_provisions
    GROUP BY doc_type
    ORDER BY count DESC
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['doc_type']:<20} {r['count']:>8} provisions")

# Check development types in DCP
print('\n4. DEVELOPMENT TYPES IN DCP PROVISIONS')
print('-' * 80)
cursor.execute("""
    SELECT development_type, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id LIKE '%DCP%'
      AND development_type IS NOT NULL
    GROUP BY development_type
    ORDER BY count DESC
    LIMIT 20
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['development_type']:<30} {r['count']:>6} provisions")

# Sample multi_dwelling provisions
print('\n5. SAMPLE: multi_dwelling DCP PROVISIONS')
print('-' * 80)
cursor.execute("""
    SELECT id, ref_number, section_header
    FROM regulatory_provisions
    WHERE development_type = 'multi_dwelling'
      AND document_id LIKE '%DCP%'
    LIMIT 5
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  Ref: {r['ref_number']:<15} Section: {r['section_header'][:60] if r['section_header'] else 'N/A'}")

# Check if we have Chapter F sections
print('\n6. INNER WEST DCP CHAPTER F STRUCTURE')
print('-' * 80)
cursor.execute("""
    SELECT DISTINCT ref_number
    FROM regulatory_provisions
    WHERE document_id LIKE '%Inner_West%DCP%'
      AND ref_number LIKE 'F.%'
    ORDER BY ref_number
    LIMIT 20
""")
rows = cursor.fetchall()
if rows:
    print("  Found Chapter F sections:")
    for r in rows:
        print(f"    {r['ref_number']}")
else:
    print("  No Chapter F sections found with 'F.%' pattern")
    # Try broader search
    cursor.execute("""
        SELECT DISTINCT ref_number
        FROM regulatory_provisions
        WHERE document_id LIKE '%Inner_West%DCP%'
        ORDER BY ref_number
        LIMIT 30
    """)
    rows = cursor.fetchall()
    print("\n  All ref_numbers in Inner West DCP:")
    for r in rows:
        print(f"    {r['ref_number']}")

print('\n' + '='*80)
print('ANALYSIS COMPLETE')
print('='*80)

cursor.close()
conn.close()