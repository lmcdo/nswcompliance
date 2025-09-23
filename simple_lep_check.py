from db_safety_wrapper import get_safe_connection

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== SIMPLE LEP DATABASE CONTENT CHECK ===")

    # 1. Check what clause numbers exist
    print("\n1. CLAUSE NUMBERS BY PART:")
    print("-" * 50)

    parts = ['1', '2', '3', '4', '5', '6', '7']

    for part in parts:
        cur.execute("""
            SELECT COUNT(DISTINCT ref_number)
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND ref_number LIKE %s
        """, (f'{part}.%',))

        count = cur.fetchone()[0]
        print(f"Part {part}: {count} unique clauses")

    # 2. Check specific important clauses
    print(f"\n2. SPECIFIC KEY CLAUSES:")
    print("-" * 50)

    key_clauses = ['1.2', '2.1', '2.2', '2.3', '2.4', '2.5', '4.1', '4.2', '4.3', '4.4', '4.5', '4.6', '5.10']

    for clause in key_clauses:
        cur.execute("""
            SELECT COUNT(*), MAX(LENGTH(provision_text))
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND ref_number = %s
            AND provision_text IS NOT NULL
        """, (clause,))

        result = cur.fetchone()
        print(f"Clause {clause}: {result[0]} provisions, max length {result[1] or 0}")

    # 3. Check zone-related provisions
    print(f"\n3. ZONE CONTENT CHECK:")
    print("-" * 50)

    # Check for zone objectives (Part 2)
    cur.execute("""
        SELECT ref_number, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND ref_number LIKE '2.%'
        AND provision_text ILIKE '%objective%'
        GROUP BY ref_number
        ORDER BY ref_number
    """)

    results = cur.fetchall()
    print("Zone objectives found:")
    for row in results:
        print(f"  {row[0]}: {row[1]} objective provisions")

    # 4. Check permitted uses
    print(f"\n4. PERMITTED USES CHECK:")
    print("-" * 50)

    cur.execute("""
        SELECT ref_number, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND (provision_text ILIKE '%permitted with consent%'
             OR provision_text ILIKE '%permitted without consent%'
             OR provision_text ILIKE '%prohibited%')
        GROUP BY ref_number
        ORDER BY ref_number
    """)

    results = cur.fetchall()
    print("Land use provisions found:")
    for row in results:
        print(f"  {row[0]}: {row[1]} land use provisions")

    # 5. Check development standards
    print(f"\n5. DEVELOPMENT STANDARDS CHECK:")
    print("-" * 50)

    standards = ['height', 'floor space', 'setback', 'coverage', 'landscaping']

    for standard in standards:
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND provision_text ILIKE %s
        """, (f'%{standard}%',))

        count = cur.fetchone()[0]
        print(f"{standard.title()} provisions: {count}")

    # 6. Sample some actual content
    print(f"\n6. SAMPLE PROVISION CONTENT:")
    print("-" * 50)

    # Get a sample of different provision types
    cur.execute("""
        SELECT DISTINCT provision_type
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        ORDER BY provision_type
        LIMIT 10
    """)

    provision_types = [row[0] for row in cur.fetchall()]
    print("Provision types found:")
    for ptype in provision_types:
        print(f"  - {ptype}")

    # 7. Check for heritage and environmental
    print(f"\n7. HERITAGE AND ENVIRONMENTAL:")
    print("-" * 50)

    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND provision_text ILIKE '%heritage%'
    """)
    heritage_count = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND (provision_text ILIKE '%environment%'
             OR provision_text ILIKE '%flood%'
             OR provision_text ILIKE '%bushfire%')
    """)
    env_count = cur.fetchone()[0]

    print(f"Heritage provisions: {heritage_count}")
    print(f"Environmental provisions: {env_count}")

    conn.close()

print("\nSimple check completed.")