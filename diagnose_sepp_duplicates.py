#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

print("=" * 80)
print("SEPP DUPLICATE DIAGNOSIS")
print("=" * 80)

# Check the duplicate Section 11(2) provisions
print("\n=== Duplicate Section 11(2) ===")
cur.execute("""
    SELECT id, ref_number, section_header, document_id,
           LEFT(provision_text, 100) as text_preview
    FROM regulatory_provisions
    WHERE id IN (6141, 6194)
    ORDER BY id
""")

for row in cur.fetchall():
    print(f"\nID: {row[0]}")
    print(f"  Ref: {row[1]}")
    print(f"  Header: {row[2]}")
    print(f"  Doc: {row[3]}")
    print(f"  Text: {row[4]}...")

# Check if they're in different documents
print("\n=== Are they from different source documents? ===")
cur.execute("""
    SELECT id, document_id
    FROM regulatory_provisions
    WHERE id IN (6141, 6194, 6142, 6195)
    ORDER BY id
""")

for id, doc in cur.fetchall():
    section = doc.split('section_')[-1] if 'section_' in doc else 'N/A'
    print(f"  ID {id}: document_id ends with 'section_{section}'")

# Check for other duplicates by ref_number
print("\n=== Other potential duplicates in SEPP Sustainable Buildings ===")
cur.execute("""
    SELECT ref_number, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Sustainable%Buildings%2022%'
    GROUP BY ref_number
    HAVING COUNT(*) > 1
    ORDER BY count DESC
    LIMIT 10
""")

for ref, count in cur.fetchall():
    print(f"  Ref '{ref}': {count} occurrences")

# Check extraction method
print("\n=== Extraction methods used ===")
cur.execute("""
    SELECT extraction_method, COUNT(*) as count
    FROM regulatory_provisions
    WHERE document_id ILIKE '%Sustainable%Buildings%2022%'
    GROUP BY extraction_method
""")

for method, count in cur.fetchall():
    print(f"  {method}: {count} provisions")

# Root cause analysis
print("\n\n=== ROOT CAUSE ANALYSIS ===")

cur.execute("""
    SELECT
        rp1.id as id1,
        rp1.ref_number,
        rp1.provision_text = rp2.provision_text as same_text,
        rp1.document_id = rp2.document_id as same_doc,
        rp1.document_id as doc1,
        rp2.document_id as doc2
    FROM regulatory_provisions rp1
    JOIN regulatory_provisions rp2 ON rp1.ref_number = rp2.ref_number
    WHERE rp1.id = 6141 AND rp2.id = 6194
""")

result = cur.fetchone()
if result:
    print(f"Comparing ID {result[0]} and 6194:")
    print(f"  Same ref_number: Yes ('{result[1]}')")
    print(f"  Same provision_text: {result[2]}")
    print(f"  Same document_id: {result[3]}")
    if not result[3]:
        print(f"\n  Doc 1: {result[4]}")
        print(f"  Doc 2: {result[5]}")
        print("\n  → CAUSE: Same provision extracted from different sections/documents")

print("""
LIKELY CAUSES:
1. Multiple PDF sections: SEPP split across multiple PDF sections during extraction
2. Cross-references: Provision appears in both main text and appendix
3. Schedule vs Body: Same provision in Schedule and main document body
4. Extraction artifact: Same content extracted twice with different metadata

ARCHITECTURAL FIX NEEDED:
- Deduplicate by (document_name + ref_number) instead of document_id
- Use canonical provision ID across all sections
- Add "is_duplicate_of" relationship field
""")

conn.close()
