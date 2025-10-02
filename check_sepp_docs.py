#!/usr/bin/env python3
"""Check SEPP documents in database."""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

print('='*80)
print('SEPP DOCUMENTS IN DATABASE')
print('='*80)

# Get all SEPP document IDs
cursor.execute("""
    SELECT DISTINCT document_id
    FROM regulatory_provisions
    WHERE provision_type = 'SEPP'
    ORDER BY document_id
    LIMIT 50
""")
rows = cursor.fetchall()
print(f"\nFound {len(rows)} SEPP documents:\n")
for r in rows:
    print(f"  {r['document_id']}")

# Check SEPP Housing specifically
print('\n' + '='*80)
print('SEPP HOUSING 2021 - STRUCTURE')
print('='*80)
cursor.execute("""
    SELECT DISTINCT section_header
    FROM regulatory_provisions
    WHERE document_id LIKE '%Housing%'
      AND section_header IS NOT NULL
    ORDER BY section_header
    LIMIT 30
""")
rows = cursor.fetchall()
print("\nSection headers in Housing SEPP:")
for r in rows:
    print(f"  {r['section_header'][:80]}")

# Check SEPP dev types
print('\n' + '='*80)
print('SEPP PROVISIONS WITH DEVELOPMENT TYPES')
print('='*80)
cursor.execute("""
    SELECT development_type, COUNT(*) as count
    FROM regulatory_provisions
    WHERE provision_type = 'SEPP'
      AND development_type IS NOT NULL
    GROUP BY development_type
    ORDER BY count DESC
""")
rows = cursor.fetchall()
print("\nDevelopment types in SEPP provisions:")
for r in rows:
    print(f"  {r['development_type']:<30} {r['count']:>6} provisions")

# Sample SEPP provisions
print('\n' + '='*80)
print('SAMPLE SEPP PROVISIONS')
print('='*80)
cursor.execute("""
    SELECT document_id, ref_number, section_header, development_type
    FROM regulatory_provisions
    WHERE provision_type = 'SEPP'
    LIMIT 10
""")
rows = cursor.fetchall()
for i, r in enumerate(rows, 1):
    doc_short = r['document_id'][:50] if r['document_id'] else 'N/A'
    section = r['section_header'][:50] if r['section_header'] else 'N/A'
    dev = r['development_type'] or 'NULL'
    print(f"\n  [{i}] {doc_short}")
    print(f"      Ref: {r['ref_number']} | Dev Type: {dev}")
    print(f"      Section: {section}")

cursor.close()
conn.close()