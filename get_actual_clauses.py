from db_safety_wrapper import get_safe_connection
import json

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== GETTING ACTUAL CLAUSE 4.3 AND 4.4 CONTENT FROM INNER WEST LEP ===")

    # Get clause 4.3 content
    cur.execute("""
        SELECT ref_number, provision_type, provision_text, section_header, document_id, id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND ref_number = '4.3'
        AND provision_text IS NOT NULL
        AND LENGTH(provision_text) > 20
        ORDER BY LENGTH(provision_text) DESC
        LIMIT 5
    """)

    results = cur.fetchall()
    print(f"CLAUSE 4.3 - Found {len(results)} provisions:")
    for i, row in enumerate(results):
        print(f"\n--- Clause 4.3 Option {i+1} (ID: {row[5]}) ---")
        print(f"Type: {row[1]}")
        print(f"Document: {row[4]}")
        if row[3]:
            print(f"Section: {row[3]}")
        print(f"Content ({len(row[2])} chars):")
        print(row[2])
        print("-" * 80)

    # Get clause 4.4 content
    cur.execute("""
        SELECT ref_number, provision_type, provision_text, section_header, document_id, id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND ref_number = '4.4'
        AND provision_text IS NOT NULL
        AND LENGTH(provision_text) > 20
        ORDER BY LENGTH(provision_text) DESC
        LIMIT 5
    """)

    results = cur.fetchall()
    print(f"\nCLAUSE 4.4 - Found {len(results)} provisions:")
    for i, row in enumerate(results):
        print(f"\n--- Clause 4.4 Option {i+1} (ID: {row[5]}) ---")
        print(f"Type: {row[1]}")
        print(f"Document: {row[4]}")
        if row[3]:
            print(f"Section: {row[3]}")
        print(f"Content ({len(row[2])} chars):")
        print(row[2])
        print("-" * 80)

    conn.close()