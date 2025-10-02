#!/usr/bin/env python3
"""Explain the semantic types problem."""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

print('='*80)
print('WHAT ARE "SEMANTIC TYPES" AND WHY IS IT A PROBLEM?')
print('='*80)

# Show what we EXPECT vs what we HAVE
print('\n1. WHAT WE EXPECT: provision_type = document type')
print('-' * 80)
print("  Expected schema:")
print("    provision_type = 'SEPP' | 'LEP' | 'DCP'")
print("    (Tells us WHICH regulatory document it's from)")

print('\n2. WHAT WE ACTUALLY HAVE: provision_type = semantic classification')
print('-' * 80)
print("  Actual schema:")
print("    provision_type = 'formal_complying_development' | 'informal_should_statement' | ...")
print("    (Tells us WHAT TYPE of provision it is)")

# Show actual provision_type values
print('\n3. SAMPLE PROVISION_TYPE VALUES IN DATABASE')
print('-' * 80)
cursor.execute("""
    SELECT provision_type, COUNT(*) as count
    FROM regulatory_provisions
    GROUP BY provision_type
    ORDER BY count DESC
    LIMIT 15
""")
rows = cursor.fetchall()
for r in rows:
    print(f"  {r['provision_type']:<40} {r['count']:>6} provisions")

# Show how SEPP provisions are actually stored
print('\n4. EXAMPLE: SEPP HOUSING 2021 PROVISIONS')
print('-' * 80)
cursor.execute("""
    SELECT provision_type, section_header, document_id
    FROM regulatory_provisions
    WHERE document_id LIKE '%Housing%2021%'
    LIMIT 5
""")
rows = cursor.fetchall()
for i, r in enumerate(rows, 1):
    print(f"\n  [{i}] Document: {r['document_id'][:60]}")
    print(f"      provision_type: {r['provision_type']}")
    print(f"      section_header: {r['section_header'][:70] if r['section_header'] else 'N/A'}")

# Show the consequence: can't query by document type
print('\n5. THE PROBLEM: Cannot query "give me all SEPP provisions"')
print('-' * 80)
cursor.execute("""
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE provision_type = 'SEPP'
""")
result = cursor.fetchone()
print(f"  Query: SELECT * WHERE provision_type = 'SEPP'")
print(f"  Result: {result['count']} provisions  [FAIL] (Expected ~1000+)")

cursor.execute("""
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE provision_type = 'LEP'
""")
result = cursor.fetchone()
print(f"\n  Query: SELECT * WHERE provision_type = 'LEP'")
print(f"  Result: {result['count']} provisions  [FAIL] (Expected ~1000+)")

cursor.execute("""
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE provision_type = 'DCP'
""")
result = cursor.fetchone()
print(f"\n  Query: SELECT * WHERE provision_type = 'DCP'")
print(f"  Result: {result['count']} provisions  [FAIL] (Expected 15,136)")

# Show the current workaround
print('\n6. CURRENT WORKAROUND: Use document_id pattern matching')
print('-' * 80)
cursor.execute("""
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id LIKE '%SEPP%' OR document_id LIKE '%Housing%'
""")
result = cursor.fetchone()
print(f"  Query: SELECT * WHERE document_id LIKE '%SEPP%'")
print(f"  Result: {result['count']} provisions  [OK] (Works but hacky)")

cursor.execute("""
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id LIKE '%LEP%'
""")
result = cursor.fetchone()
print(f"\n  Query: SELECT * WHERE document_id LIKE '%LEP%'")
print(f"  Result: {result['count']} provisions  [OK] (Works but fragile)")

cursor.execute("""
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id LIKE '%DCP%'
""")
result = cursor.fetchone()
print(f"\n  Query: SELECT * WHERE document_id LIKE '%DCP%'")
print(f"  Result: {result['count']} provisions  [OK] (Works but fragile)")

# Check if documents table exists
print('\n7. CHECKING DOCUMENTS TABLE')
print('-' * 80)
cursor.execute("""
    SELECT COUNT(*) as count
    FROM information_schema.tables
    WHERE table_name = 'documents'
""")
has_docs_table = cursor.fetchone()['count'] > 0

if has_docs_table:
    print("  [OK] 'documents' table exists")

    # Check documents table structure
    cursor.execute("""
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'documents'
        ORDER BY ordinal_position
    """)
    cols = cursor.fetchall()
    print("\n  Columns:")
    for col in cols:
        print(f"    {col['column_name']:<30} {col['data_type']}")

    # Sample documents
    print("\n  Sample documents:")
    cursor.execute("""
        SELECT id, document_type
        FROM documents
        LIMIT 10
    """)
    rows = cursor.fetchall()
    for r in rows:
        doc_type = r.get('document_type', 'N/A')
        doc_id = r.get('id', 'N/A')
        print(f"    {doc_id:<60} Type: {doc_type}")
else:
    print("  [FAIL] 'documents' table does not exist")

print('\n' + '='*80)
print('SUMMARY')
print('='*80)
print("""
PROBLEM: provision_type stores SEMANTIC classification, not DOCUMENT type

Current state:
  provision_type = 'formal_complying_development'  (What KIND of provision)
  document_id = 'State Environmental Planning Policy (Housing) 2021'  (Which document)

This makes it impossible to query "all SEPP provisions" without text matching on document_id.

The 'documents' table DOES have a 'document_type' column that correctly identifies SEPP/LEP/DCP.
But regulatory_provisions doesn't have this - would need to JOIN or add a column.
""")

cursor.close()
conn.close()