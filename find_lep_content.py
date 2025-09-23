from db_safety_wrapper import get_safe_connection
import json

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== SEARCHING FOR INNER WEST LEP CONTENT ===")

    # Get all Inner West LEP documents and their content
    cur.execute("""
        SELECT document_id, COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        GROUP BY document_id
        ORDER BY count DESC
    """)

    docs = cur.fetchall()
    print(f"Found {len(docs)} Inner West LEP documents:")
    for doc in docs:
        print(f"  - {doc[0]}: {doc[1]} provisions")

    # Look for any clauses that might be height or FSR related
    print(f"\n=== SEARCHING FOR HEIGHT/FSR CONTENT IN INNER WEST LEP ===")

    cur.execute("""
        SELECT ref_number, provision_type, provision_text, section_header, document_id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND (provision_text ILIKE '%height%'
             OR provision_text ILIKE '%floor space%'
             OR provision_text ILIKE '%FSR%'
             OR ref_number ~ '^4\\.[0-9]+'
             OR section_header ILIKE '%height%'
             OR section_header ILIKE '%floor%space%')
        AND provision_text IS NOT NULL
        AND LENGTH(provision_text) > 50
        ORDER BY ref_number, document_id
        LIMIT 20
    """)

    results = cur.fetchall()
    print(f"Found {len(results)} height/FSR related provisions:")

    for row in results:
        print(f"\n- Ref: {row[0]} | Type: {row[1]}")
        print(f"  Doc: {row[4]}")
        if row[3]:
            print(f"  Section: {row[3]}")
        print(f"  Content: {row[2][:250]}...")

    # Check what clause numbers exist in part 4
    print(f"\n=== ALL CLAUSE 4.X NUMBERS IN INNER WEST LEP ===")

    cur.execute("""
        SELECT DISTINCT ref_number, COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND ref_number ~ '^4\\.'
        GROUP BY ref_number
        ORDER BY ref_number
    """)

    results = cur.fetchall()
    print(f"Found {len(results)} different clause 4.x references:")
    for row in results:
        print(f"  - {row[0]} ({row[1]} provisions)")

    conn.close()