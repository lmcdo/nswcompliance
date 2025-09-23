from db_safety_wrapper import get_safe_connection
import json

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== GETTING FULL CLAUSE CONTENT ===")

    # Get full clause 4.4 content (ID 17473)
    cur.execute("""
        SELECT ref_number, provision_type, provision_text, section_header, document_id, id
        FROM regulatory_provisions
        WHERE id = %s
    """, (17473,))

    result = cur.fetchone()
    if result:
        print(f"CLAUSE 4.4 - Floor Space Ratio (ID: {result[5]})")
        print(f"Type: {result[1]}")
        print(f"Document: {result[4]}")
        if result[3]:
            print(f"Section: {result[3]}")
        print(f"Full Content:")
        print(result[2])
        print("=" * 100)

    # Now search more broadly for clause 4.3 (height of buildings)
    print(f"\n=== SEARCHING FOR BUILDING HEIGHT CLAUSE 4.3 ===")

    cur.execute("""
        SELECT ref_number, provision_type, provision_text, section_header, document_id, id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND (ref_number = '4.3'
             OR provision_text ILIKE '%height of building%'
             OR provision_text ILIKE '%maximum height%'
             OR section_header ILIKE '%height of building%')
        AND provision_text IS NOT NULL
        AND LENGTH(provision_text) > 100
        ORDER BY LENGTH(provision_text) DESC
        LIMIT 10
    """)

    results = cur.fetchall()
    print(f"Found {len(results)} height-related provisions:")
    for i, row in enumerate(results):
        print(f"\n--- Option {i+1} (ID: {row[5]}) ---")
        print(f"Ref: {row[0]} | Type: {row[1]}")
        print(f"Document: {row[4]}")
        if row[3]:
            print(f"Section: {row[3]}")
        print(f"Content preview: {row[2][:200]}...")

    # Try to find the actual height of buildings clause
    print(f"\n=== SEARCHING FOR 'Height of buildings' SECTION HEADER ===")

    cur.execute("""
        SELECT ref_number, provision_type, provision_text, section_header, document_id, id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND section_header ILIKE '%height of buildings%'
        AND provision_text IS NOT NULL
        ORDER BY LENGTH(provision_text) DESC
        LIMIT 5
    """)

    results = cur.fetchall()
    print(f"Found {len(results)} provisions with 'Height of buildings' section:")
    for i, row in enumerate(results):
        print(f"\n--- Building Height Clause {i+1} (ID: {row[5]}) ---")
        print(f"Ref: {row[0]} | Type: {row[1]}")
        print(f"Section: {row[3]}")
        print(f"Full Content:")
        print(row[2])
        print("-" * 80)

    conn.close()