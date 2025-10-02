#!/usr/bin/env python3
from db_config import get_connection

conn = get_connection()
cur = conn.cursor()

# Look for zone provisions in LEP
cur.execute("""
    SELECT ref_number, section_header, provision_text
    FROM regulatory_provisions
    WHERE document_id ILIKE '%inner%west%lep%'
    AND ref_number LIKE '2.%'
    ORDER BY ref_number
    LIMIT 20
""")

print("=== LEP Clause 2 (Land Use) Provisions ===\n")
for ref, header, text in cur.fetchall():
    print(f"Clause {ref}: {header}")
    if text:
        # Check if it's a structured table
        if '|' in text or '\t' in text or 'Zone' in text:
            print(f"  [TABLE DATA] Length: {len(text)} chars")
            print(f"  Preview: {text[:150]}...")
        else:
            print(f"  [TEXT] {text[:100]}...")
    print()

conn.close()
