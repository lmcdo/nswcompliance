#!/usr/bin/env python3
"""Investigate why SEPP VIEW is imperfect and how to fix it."""

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.db_config import get_dict_connection

conn = get_dict_connection()
cursor = conn.cursor()

print('='*80)
print('QUESTION 2: Why is SEPP VIEW imperfect? How to fix?')
print('='*80)

# First create the VIEW
print('\n1. Creating VIEW (if not exists)')
print('-' * 80)
cursor.execute("""
    CREATE OR REPLACE VIEW provisions_with_category AS
    SELECT
        rp.*,
        d.document_type as document_category
    FROM regulatory_provisions rp
    LEFT JOIN documents d ON rp.document_id = d.id
""")
print("  View created successfully")

# Recap the problem
print('\n2. THE IMPERFECTION')
print('-' * 80)
cursor.execute("""
    SELECT COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id LIKE '%SEPP%' OR document_id LIKE '%Housing%'
""")
old_method = cursor.fetchone()['count']

cursor.execute("""
    SELECT COUNT(*) as count
    FROM provisions_with_category
    WHERE document_category = 'SEPP'
""")
new_method = cursor.fetchone()['count']

cursor.execute("""
    SELECT COUNT(*) as count
    FROM provisions_with_category
    WHERE document_category IS NULL
""")
null_category = cursor.fetchone()['count']

print(f"  Old method (LIKE '%SEPP%'): {old_method:>6} provisions")
print(f"  New method (VIEW/JOIN):     {new_method:>6} provisions")
print(f"  NULL category (failed JOIN): {null_category:>6} provisions")
print(f"\n  Missing from old method: {new_method - old_method:>6} provisions (VIEW finds MORE)")
print(f"  But still have NULL:     {null_category:>6} provisions (JOIN failures)")

# Find out WHY the JOIN fails
print('\n3. WHY DOES THE JOIN FAIL? (Key Mismatch)')
print('-' * 80)
print("  Checking document_id mismatches between tables...")

# Sample provisions with NULL category (failed JOIN)
cursor.execute("""
    SELECT DISTINCT rp.document_id as prov_doc_id
    FROM regulatory_provisions rp
    LEFT JOIN documents d ON rp.document_id = d.id
    WHERE d.id IS NULL
    LIMIT 10
""")
rows = cursor.fetchall()
print("\n  Sample document_ids in regulatory_provisions (no match in documents):")
for r in rows:
    print(f"    {r['prov_doc_id'][:70]}")

# Sample documents table IDs
cursor.execute("""
    SELECT id
    FROM documents
    WHERE document_type = 'SEPP'
    LIMIT 5
""")
rows = cursor.fetchall()
print("\n  Sample document IDs in documents table (SEPP):")
for r in rows:
    print(f"    {r['id'][:70]}")

# Check if there are similar but not exact matches
print('\n4. FUZZY MATCHING: Can we find near-matches?')
print('-' * 80)
cursor.execute("""
    SELECT
        rp.document_id as prov_id,
        d.id as doc_id,
        d.document_type
    FROM regulatory_provisions rp
    CROSS JOIN documents d
    WHERE rp.document_id LIKE '%Housing%2021%'
      AND d.id LIKE '%Housing%2021%'
    LIMIT 5
""")
rows = cursor.fetchall()
if rows:
    print("  Found similar document IDs:")
    for r in rows:
        print(f"\n    regulatory_provisions.document_id:")
        print(f"      '{r['prov_id']}'")
        print(f"    documents.id:")
        print(f"      '{r['doc_id']}'")
        print(f"    Match: {r['prov_id'] == r['doc_id']}")
else:
    print("  No similar documents found")

# Check exact format differences
print('\n5. EXACT FORMAT COMPARISON')
print('-' * 80)
cursor.execute("""
    SELECT DISTINCT document_id
    FROM regulatory_provisions
    WHERE document_id LIKE '%Housing%2021%'
    LIMIT 3
""")
prov_docs = cursor.fetchall()

cursor.execute("""
    SELECT id
    FROM documents
    WHERE id LIKE '%Housing%2021%'
    LIMIT 3
""")
doc_ids = cursor.fetchall()

if prov_docs and doc_ids:
    print("  regulatory_provisions.document_id:")
    for r in prov_docs:
        print(f"    '{r['document_id']}'")
        print(f"      Length: {len(r['document_id'])}")
        print(f"      Has spaces: {' ' in r['document_id']}")
        print(f"      Has underscores: {'_' in r['document_id']}")

    print("\n  documents.id:")
    for r in doc_ids:
        print(f"    '{r['id']}'")
        print(f"      Length: {len(r['id'])}")
        print(f"      Has spaces: {' ' in r['id']}")
        print(f"      Has underscores: {'_' in r['id']}")

print('\n' + '='*80)
print('ROOT CAUSE')
print('='*80)
print("""
The JOIN fails because:
  regulatory_provisions.document_id uses spaces
  documents.id uses underscores

Example:
  regulatory_provisions: "State Environmental Planning Policy (Housing) 2021"
  documents:            "State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation"

They don't match!
""")

print('='*80)
print('SOLUTIONS TO PERFECT THE VIEW')
print('='*80)
print("""
Option 1: Fix the JOIN with text normalization
----------------------------------------------
CREATE OR REPLACE VIEW provisions_with_category AS
SELECT
    rp.*,
    d.document_type as document_category
FROM regulatory_provisions rp
LEFT JOIN documents d ON REPLACE(rp.document_id, ' ', '_') = REPLACE(d.id, '___NSW_Legislation', '')
                       OR REPLACE(rp.document_id, ' ', '_') LIKE REPLACE(d.id, '___NSW_Legislation', '') || '%';

Pros: Works with existing data
Cons: Complex JOIN, slower performance


Option 2: Normalize document_id in regulatory_provisions
--------------------------------------------------------
-- Create a new column with normalized IDs
ALTER TABLE regulatory_provisions ADD COLUMN document_id_normalized TEXT;

UPDATE regulatory_provisions
SET document_id_normalized = REPLACE(document_id, ' ', '_');

-- Then JOIN becomes simple:
CREATE VIEW provisions_with_category AS
SELECT rp.*, d.document_type as document_category
FROM regulatory_provisions rp
LEFT JOIN documents d ON rp.document_id_normalized LIKE d.id || '%'
                      OR d.id LIKE rp.document_id_normalized || '%';

Pros: Clean JOIN, good performance
Cons: Requires schema migration


Option 3: Pattern-based fallback
---------------------------------
CREATE OR REPLACE VIEW provisions_with_category AS
SELECT
    rp.*,
    COALESCE(
        d.document_type,
        CASE
            WHEN rp.document_id LIKE '%SEPP%' OR rp.document_id LIKE '%Housing%' THEN 'SEPP'
            WHEN rp.document_id LIKE '%LEP%' THEN 'LEP'
            WHEN rp.document_id LIKE '%DCP%' THEN 'DCP'
            ELSE NULL
        END
    ) as document_category
FROM regulatory_provisions rp
LEFT JOIN documents d ON rp.document_id = d.id;

Pros: Handles all provisions (no NULLs)
Cons: Falls back to pattern matching (not perfect)


Option 4: Fuzzy JOIN (RECOMMENDED)
-----------------------------------
-- Match on the core document name, ignoring formatting
CREATE OR REPLACE VIEW provisions_with_category AS
SELECT
    rp.*,
    d.document_type as document_category
FROM regulatory_provisions rp
LEFT JOIN documents d ON
    LOWER(REPLACE(REPLACE(rp.document_id, ' ', ''), '_', ''))
    = LOWER(REPLACE(REPLACE(SUBSTRING(d.id, 1, 80), ' ', ''), '_', ''));

Pros: More flexible matching
Cons: May have false positives


BEST SOLUTION: Option 3 (Pattern fallback)
===========================================
It's the pragmatic choice:
- Uses JOIN when possible (most cases)
- Falls back to pattern matching for edge cases
- No schema changes needed
- Zero NULL categories
""")

cursor.close()
conn.close()