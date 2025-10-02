#!/usr/bin/env python3
"""Check if we can map SEPP provisions to dev types by section headers."""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

print('='*80)
print('CAN WE MAP SEPPs TO DEV TYPES?')
print('='*80)

# Check for dev-type-specific section headers in all provisions
print('\n1. SECTIONS MENTIONING DEVELOPMENT TYPES')
print('-' * 80)

dev_types = [
    'secondary dwelling',
    'boarding house',
    'multi dwelling',
    'residential flat',
    'shop top',
    'dual occupancy',
    'group home',
    'seniors housing',
    'subdivision'
]

for dev_type in dev_types:
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE LOWER(section_header) LIKE %s
    """, (f'%{dev_type}%',))
    result = cursor.fetchone()
    if result['count'] > 0:
        print(f"  {dev_type:<30} {result['count']:>6} provisions")

# Sample secondary dwelling provisions
print('\n2. SAMPLE: SECONDARY DWELLING PROVISIONS')
print('-' * 80)
cursor.execute("""
    SELECT document_id, provision_type, section_header
    FROM regulatory_provisions
    WHERE LOWER(section_header) LIKE '%secondary dwelling%'
    LIMIT 10
""")
rows = cursor.fetchall()
for r in rows:
    doc_short = r['document_id'][:50] if r['document_id'] else 'N/A'
    print(f"  [{r['provision_type']:<30}] {doc_short}")
    print(f"    Section: {r['section_header'][:70]}")
    print()

# Check which documents these come from
print('\n3. WHICH DOCUMENTS HAVE DEV-TYPE-SPECIFIC SECTIONS?')
print('-' * 80)
cursor.execute("""
    SELECT DISTINCT document_id
    FROM regulatory_provisions
    WHERE LOWER(section_header) LIKE '%secondary dwelling%'
       OR LOWER(section_header) LIKE '%boarding house%'
       OR LOWER(section_header) LIKE '%multi dwelling%'
    ORDER BY document_id
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['document_id']}")

# Check if we can identify DCP vs SEPP
print('\n4. ARE THESE DCP OR SEPP DOCUMENTS?')
print('-' * 80)
cursor.execute("""
    SELECT
        document_id,
        CASE
            WHEN document_id LIKE '%DCP%' THEN 'DCP'
            WHEN document_id LIKE '%LEP%' THEN 'LEP'
            WHEN document_id LIKE '%SEPP%' OR document_id LIKE '%Housing%' THEN 'SEPP'
            ELSE 'UNKNOWN'
        END as doc_category,
        COUNT(*) as provisions_with_devtype_sections
    FROM regulatory_provisions
    WHERE LOWER(section_header) LIKE '%dwelling house%'
       OR LOWER(section_header) LIKE '%secondary dwelling%'
       OR LOWER(section_header) LIKE '%boarding house%'
       OR LOWER(section_header) LIKE '%multi dwelling%'
       OR LOWER(section_header) LIKE '%residential flat%'
    GROUP BY document_id, doc_category
    ORDER BY provisions_with_devtype_sections DESC
""")
rows = cursor.fetchall()
print(f"{'Document':<60} {'Type':<10} {'Count':>8}")
print('-' * 80)
for r in rows:
    doc_short = r['document_id'][:58] if r['document_id'] else 'N/A'
    print(f"{doc_short:<60} {r['doc_category']:<10} {r['provisions_with_devtype_sections']:>8}")

cursor.close()
conn.close()