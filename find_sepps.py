#!/usr/bin/env python3
"""Find how SEPPs are actually stored."""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

print('='*80)
print('HOW ARE SEPPs STORED?')
print('='*80)

# Check all provision types
print('\n1. ALL PROVISION TYPES')
print('-' * 80)
cursor.execute("""
    SELECT provision_type, COUNT(*) as count
    FROM regulatory_provisions
    GROUP BY provision_type
    ORDER BY count DESC
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['provision_type']:<30} {r['count']:>8} provisions")

# Find documents with "SEPP" in document_id
print('\n2. DOCUMENTS WITH "SEPP" IN NAME')
print('-' * 80)
cursor.execute("""
    SELECT DISTINCT document_id, provision_type
    FROM regulatory_provisions
    WHERE document_id LIKE '%SEPP%'
    ORDER BY document_id
    LIMIT 20
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  [{r['provision_type']:<20}] {r['document_id'][:70]}")

# Check Housing SEPP specifically
print('\n3. HOUSING SEPP PROVISIONS')
print('-' * 80)
cursor.execute("""
    SELECT provision_type, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id LIKE '%Housing%'
    GROUP BY provision_type
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['provision_type']:<30} {r['count']:>8} provisions")

# Sample from Housing SEPP
print('\n4. SAMPLE HOUSING SEPP PROVISIONS')
print('-' * 80)
cursor.execute("""
    SELECT document_id, provision_type, ref_number, section_header, provision_text
    FROM regulatory_provisions
    WHERE document_id LIKE '%Housing%'
    LIMIT 3
""")
rows = cursor.fetchall()
for i, r in enumerate(rows, 1):
    print(f"\n  [{i}] Doc: {r['document_id'][:60]}")
    print(f"      Type: {r['provision_type']}")
    print(f"      Ref: {r['ref_number']}")
    print(f"      Section: {r['section_header'][:60] if r['section_header'] else 'N/A'}")
    print(f"      Text: {r['provision_text'][:100] if r['provision_text'] else 'N/A'}...")

# Check if we can identify dev-type-specific SEPP provisions by section header
print('\n5. SEPP SECTIONS MENTIONING DEVELOPMENT TYPES')
print('-' * 80)
cursor.execute("""
    SELECT section_header, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id LIKE '%SEPP%'
      AND (
        section_header LIKE '%secondary dwelling%'
        OR section_header LIKE '%boarding house%'
        OR section_header LIKE '%multi dwelling%'
        OR section_header LIKE '%residential flat%'
        OR section_header LIKE '%shop top%'
      )
    GROUP BY section_header
    ORDER BY count DESC
    LIMIT 20
""")
rows = cursor.fetchall()
if rows:
    for r in rows:
        print(f"  {r['section_header'][:70]:<70} {r['count']:>4}")
else:
    print("  No dev-type-specific sections found in SEPP provisions")

cursor.close()
conn.close()