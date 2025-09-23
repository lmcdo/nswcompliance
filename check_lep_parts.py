from db_safety_wrapper import get_safe_connection

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== LEP PARTS AND CLAUSE COVERAGE ANALYSIS ===")

    # 1. Check what LEP parts are covered
    parts_analysis = [
        ("Part 1 - Preliminary", "1."),
        ("Part 2 - Permitted/Prohibited", "2."),
        ("Part 3 - Exempt/Complying", "3."),
        ("Part 4 - Development Standards", "4."),
        ("Part 5 - Miscellaneous", "5."),
        ("Part 6 - Local Provisions", "6."),
        ("Part 7 - Additional Local Provisions", "7."),
        ("Schedule", "Schedule")
    ]

    print("\n1. LEP PART COVERAGE:")
    print("-" * 70)

    for part_name, part_prefix in parts_analysis:
        if part_prefix == "Schedule":
            search_pattern = "%Schedule%"
        else:
            search_pattern = f'{part_prefix}%'

        cur.execute("""
            SELECT
                COUNT(*) as provisions,
                COUNT(DISTINCT ref_number) as clauses
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND (ref_number LIKE %s OR (ref_number ILIKE %s AND %s = 'Schedule'))
        """, (search_pattern, search_pattern, part_prefix))

        result = cur.fetchone()
        print(f"{part_name:<35}: {result[0]:>4} provisions, {result[1]:>3} clauses")

    # 2. Detailed Part 2 (Zoning) analysis
    print(f"\n2. PART 2 - ZONING CONTENT DETAIL:")
    print("-" * 70)

    cur.execute("""
        SELECT
            ref_number,
            provision_type,
            COUNT(*) as provisions,
            MAX(LENGTH(provision_text)) as max_length
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND ref_number LIKE '2.%'
        GROUP BY ref_number, provision_type
        ORDER BY ref_number, provisions DESC
    """)

    results = cur.fetchall()
    current_clause = None
    for row in results:
        if row[0] != current_clause:
            print(f"\nClause {row[0]}:")
            current_clause = row[0]
        print(f"  {row[1]:<30}: {row[2]:>2} provisions, max {row[3]:>3} chars")

    # 3. Detailed Part 4 (Development Standards) analysis
    print(f"\n3. PART 4 - DEVELOPMENT STANDARDS DETAIL:")
    print("-" * 70)

    cur.execute("""
        SELECT
            ref_number,
            provision_type,
            COUNT(*) as provisions,
            MAX(LENGTH(provision_text)) as max_length
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND ref_number LIKE '4.%'
        GROUP BY ref_number, provision_type
        ORDER BY ref_number, provisions DESC
    """)

    results = cur.fetchall()
    current_clause = None
    for row in results:
        if row[0] != current_clause:
            print(f"\nClause {row[0]}:")
            current_clause = row[0]
        print(f"  {row[1]:<30}: {row[2]:>2} provisions, max {row[3]:>3} chars")

    # 4. Sample key clauses to see content quality
    print(f"\n4. SAMPLE KEY CLAUSE CONTENT:")
    print("-" * 70)

    key_clauses = ['2.1', '2.2', '2.3', '4.1', '4.3', '4.4', '5.10']

    for clause in key_clauses:
        cur.execute("""
            SELECT
                provision_type,
                provision_text
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND ref_number = %s
            AND provision_text IS NOT NULL
            ORDER BY LENGTH(provision_text) DESC
            LIMIT 1
        """, (clause,))

        result = cur.fetchone()
        if result:
            text_preview = result[1][:150] + ('...' if len(result[1]) > 150 else '')
            print(f"\nClause {clause} ({result[0]}):")
            print(f"  {text_preview}")
        else:
            print(f"\nClause {clause}: Not found")

    # 5. Check for zone-specific content
    print(f"\n5. ZONE-SPECIFIC CONTENT:")
    print("-" * 70)

    zones = ['R1', 'R2', 'R3', 'R4', 'B1', 'B2', 'B4', 'IN1', 'IN2', 'RE1', 'E1']

    for zone in zones:
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND (provision_text ILIKE %s OR ref_number ILIKE %s)
        """, (f'%{zone}%', f'%{zone}%'))

        count = cur.fetchone()[0]
        if count > 0:
            print(f"  Zone {zone}: {count} relevant provisions")

    conn.close()

print("\nAnalysis completed.")