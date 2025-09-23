from db_safety_wrapper import get_safe_connection
import json

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== SEARCHING FOR CLAUSE 4.3 AND 4.4 CONTENT ===")

    # Search exactly like the API would
    search_terms = ["4.3", "4.4", "Clause 4.3", "Clause 4.4", "Building Height", "Floor Space Ratio"]

    for term in search_terms:
        print(f"\nSearching for: '{term}'")
        cur.execute("""
            SELECT ref_number, provision_type, document_id, provision_text, section_header
            FROM regulatory_provisions
            WHERE (ref_number ILIKE %s
                   OR provision_text ILIKE %s
                   OR section_header ILIKE %s)
            AND provision_text IS NOT NULL
            AND LENGTH(provision_text) > 20
            LIMIT 5
        """, (f'%{term}%', f'%{term}%', f'%{term}%'))

        results = cur.fetchall()
        print(f"Found {len(results)} results:")

        for row in results:
            print(f"  - Ref: {row[0]} | Type: {row[1]} | Doc: {row[2][:50]}...")
            if row[4]:
                print(f"    Section: {row[4]}")
            print(f"    Content: {row[3][:150]}...")
            print()

    print("\n=== SEARCHING FOR INNER WEST LEP DOCUMENTS ===")
    cur.execute("""
        SELECT DISTINCT document_id, COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%inner%west%'
           OR document_id ILIKE '%LEP%'
           OR document_id ILIKE '%local%environmental%'
        GROUP BY document_id
        ORDER BY count DESC
        LIMIT 10
    """)

    docs = cur.fetchall()
    print(f"Found {len(docs)} document types:")
    for doc in docs:
        print(f"  - {doc[0]}: {doc[1]} provisions")

    print("\n=== SEARCHING FOR PROVISIONS WITH CLAUSE REFERENCES ===")
    cur.execute("""
        SELECT ref_number, provision_type, document_id, provision_text
        FROM regulatory_provisions
        WHERE (ref_number ~ '^[0-9]+\\.[0-9]+$' OR ref_number ~ '^Clause [0-9]+\\.[0-9]+$')
        AND document_id ILIKE '%inner%west%'
        AND provision_text IS NOT NULL
        ORDER BY ref_number
        LIMIT 10
    """)

    results = cur.fetchall()
    print(f"Found {len(results)} clause-formatted provisions:")
    for row in results:
        print(f"  - {row[0]} | {row[1]} | {row[2][:40]}...")
        print(f"    Content: {row[3][:200]}...")
        print()

    conn.close()