from db_safety_wrapper import get_safe_connection
import json

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== SEARCHING FOR INNER WEST LEP CLAUSE 4.3 AND 4.4 ===")

    # Search specifically in Inner West LEP documents
    inner_west_docs = [
        'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_1_50',
        'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_51_100',
        'Inner_West_Local_Environmental_Plan_2022___NSW_Legislation_section_19'
    ]

    for doc in inner_west_docs:
        print(f"\nSearching in: {doc}")

        # Look for clause 4.3 and 4.4 specifically
        cur.execute("""
            SELECT ref_number, provision_type, provision_text, section_header
            FROM regulatory_provisions
            WHERE document_id = %s
            AND (ref_number IN ('4.3', '4.4')
                 OR provision_text ILIKE '%height of building%'
                 OR provision_text ILIKE '%floor space ratio%'
                 OR section_header ILIKE '%height%'
                 OR section_header ILIKE '%floor space%')
            AND provision_text IS NOT NULL
            ORDER BY ref_number
        """, (doc,))

        results = cur.fetchall()
        print(f"Found {len(results)} results:")

        for row in results:
            print(f"  - Ref: {row[0]} | Type: {row[1]}")
            if row[3]:
                print(f"    Section: {row[3]}")
            print(f"    Content: {row[2][:300]}...")
            print()

    print("\n=== SEARCHING FOR ANY BUILDING HEIGHT/FSR CLAUSES IN INNER WEST LEP ===")

    # Broader search for building height and FSR in Inner West LEP
    for doc in inner_west_docs:
        cur.execute("""
            SELECT ref_number, provision_type, provision_text, section_header
            FROM regulatory_provisions
            WHERE document_id = %s
            AND (provision_text ILIKE '%height%'
                 OR provision_text ILIKE '%floor space%'
                 OR provision_text ILIKE '%FSR%'
                 OR section_header ILIKE '%height%'
                 OR section_header ILIKE '%floor%space%')
            AND provision_text IS NOT NULL
            AND LENGTH(provision_text) > 100
            ORDER BY ref_number
            LIMIT 5
        """, (doc,))

        results = cur.fetchall()
        if results:
            print(f"\nIn {doc}:")
            for row in results:
                print(f"  - Ref: {row[0]} | Type: {row[1]}")
                if row[3]:
                    print(f"    Section: {row[3]}")
                print(f"    Content: {row[2][:200]}...")
                print()

    print("\n=== CHECKING ALL REF_NUMBERS IN INNER WEST LEP STARTING WITH 4 ===")

    # Look for all clauses starting with 4
    for doc in inner_west_docs:
        cur.execute("""
            SELECT DISTINCT ref_number
            FROM regulatory_provisions
            WHERE document_id = %s
            AND ref_number ~ '^4\\.'
            ORDER BY ref_number
        """, (doc,))

        results = cur.fetchall()
        if results:
            print(f"\nClauses starting with '4.' in {doc}:")
            for row in results:
                print(f"  - {row[0]}")

    conn.close()