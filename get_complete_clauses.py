from db_safety_wrapper import get_safe_connection
import json

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== GETTING COMPLETE CLAUSE 4.3 AND 4.4 CONTENT ===")

    # Get clause 4.3 (ID: 17479)
    cur.execute("""
        SELECT ref_number, provision_type, provision_text, section_header, document_id, id
        FROM regulatory_provisions
        WHERE id = %s
    """, (17479,))

    result = cur.fetchone()
    if result:
        print(f"CLAUSE 4.3 - Height of Buildings (ID: {result[5]})")
        print(f"Type: {result[1]}")
        print(f"Document: {result[4]}")
        if result[3]:
            print(f"Section: {result[3]}")
        print(f"Full Content:")
        print(result[2])
        print("=" * 100)

    # Get clause 4.4 (ID: 17473) - get full content
    cur.execute("""
        SELECT ref_number, provision_type, provision_text, section_header, document_id, id
        FROM regulatory_provisions
        WHERE id = %s
    """, (17473,))

    result = cur.fetchone()
    if result:
        print(f"\nCLAUSE 4.4 - Floor Space Ratio (ID: {result[5]})")
        print(f"Type: {result[1]}")
        print(f"Document: {result[4]}")
        if result[3]:
            print(f"Section: {result[3]}")
        print(f"Full Content:")
        print(result[2])
        print("=" * 100)

    # Also check if there are any formal Height of Buildings provisions
    print(f"\n=== SEARCHING FOR FORMAL HEIGHT PROVISIONS ===")

    cur.execute("""
        SELECT ref_number, provision_type, provision_text, section_header, document_id, id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND ref_number = '4.3'
        AND provision_type ILIKE '%formal%'
        AND provision_text IS NOT NULL
        ORDER BY LENGTH(provision_text) DESC
    """)

    results = cur.fetchall()
    print(f"Found {len(results)} formal clause 4.3 provisions:")
    for row in results:
        print(f"\n--- Formal Clause 4.3 (ID: {row[5]}) ---")
        print(f"Type: {row[1]}")
        print(f"Content: {row[2]}")

    conn.close()