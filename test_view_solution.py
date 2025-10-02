#!/usr/bin/env python3
"""TEST: Does the VIEW solution actually work?"""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

print('='*80)
print('TESTING: Can we JOIN documents table to fix SEPP/LEP/DCP filtering?')
print('='*80)

# Test 1: Can we JOIN the tables?
print('\n1. TEST JOIN: regulatory_provisions.document_id = documents.id')
print('-' * 80)
cursor.execute("""
    SELECT COUNT(*) as total
    FROM regulatory_provisions rp
    LEFT JOIN documents d ON rp.document_id = d.id
""")
result = cursor.fetchone()
print(f"  Total provisions after JOIN: {result['total']}")

cursor.execute("""
    SELECT COUNT(*) as matched
    FROM regulatory_provisions rp
    INNER JOIN documents d ON rp.document_id = d.id
""")
result = cursor.fetchone()
print(f"  Provisions WITH matching document: {result['matched']}")

cursor.execute("""
    SELECT COUNT(*) as unmatched
    FROM regulatory_provisions rp
    LEFT JOIN documents d ON rp.document_id = d.id
    WHERE d.id IS NULL
""")
result = cursor.fetchone()
print(f"  Provisions WITHOUT matching document: {result['unmatched']}")

# Test 2: Are SEPPs in the documents table?
print('\n2. TEST: SEPP documents in documents table')
print('-' * 80)
cursor.execute("""
    SELECT id, document_type
    FROM documents
    WHERE document_type = 'SEPP'
       OR id LIKE '%SEPP%'
       OR id LIKE '%Housing%'
    LIMIT 10
""")
rows = cursor.fetchall()
if rows:
    print(f"  Found {len(rows)} SEPP documents:")
    for r in rows:
        print(f"    {r['id'][:70]:<70} Type: {r['document_type']}")
else:
    print("  [FAIL] NO SEPP documents found in documents table!")

# Test 3: Sample JOIN to see what we get
print('\n3. TEST: Sample JOIN results for SEPP provisions')
print('-' * 80)
cursor.execute("""
    SELECT
        rp.id,
        rp.document_id,
        d.document_type,
        rp.section_header
    FROM regulatory_provisions rp
    LEFT JOIN documents d ON rp.document_id = d.id
    WHERE rp.document_id LIKE '%Housing%'
    LIMIT 5
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  [{r['id']}] {r['document_id'][:50]}")
    print(f"       JOIN result: document_type = {r['document_type']}")
    print(f"       Section: {r['section_header'][:60] if r['section_header'] else 'N/A'}")
    print()

# Test 4: What if we create the VIEW - does it work?
print('\n4. TEST: Create VIEW and query it')
print('-' * 80)

try:
    cursor.execute("""
        CREATE OR REPLACE VIEW provisions_with_category AS
        SELECT
            rp.*,
            d.document_type as document_category
        FROM regulatory_provisions rp
        LEFT JOIN documents d ON rp.document_id = d.id
    """)
    print("  [OK] View created successfully")

    # Query the view
    cursor.execute("""
        SELECT document_category, COUNT(*) as count
        FROM provisions_with_category
        GROUP BY document_category
        ORDER BY count DESC
    """)
    rows = cursor.fetchall()
    print("\n  Query: SELECT * FROM provisions_with_category GROUP BY document_category")
    for r in rows:
        doc_cat = r['document_category'] or 'NULL'
        print(f"    {doc_cat:<20} {r['count']:>8} provisions")

    # Test SEPP query
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM provisions_with_category
        WHERE document_category = 'SEPP'
    """)
    result = cursor.fetchone()
    print(f"\n  Query: WHERE document_category = 'SEPP'")
    print(f"  Result: {result['count']} provisions")

    if result['count'] == 0:
        print("  [FAIL] View returns 0 SEPP provisions!")
    else:
        print("  [OK] View returns SEPP provisions")

    # Compare to old method
    cursor.execute("""
        SELECT COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id LIKE '%SEPP%' OR document_id LIKE '%Housing%'
    """)
    old_result = cursor.fetchone()
    print(f"\n  Old method (LIKE '%SEPP%'): {old_result['count']} provisions")
    print(f"  New method (JOIN): {result['count']} provisions")

    if result['count'] < old_result['count']:
        print(f"  [FAIL] Missing {old_result['count'] - result['count']} provisions!")

except Exception as e:
    print(f"  [FAIL] Error: {e}")

print('\n' + '='*80)
print('CONCLUSION')
print('='*80)

cursor.close()
conn.close()