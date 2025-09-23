from db_safety_wrapper import get_safe_connection
import json

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== DEEP ANALYSIS OF LEP CONTENT IN DATABASE ===")

    # 1. Overall LEP coverage
    print("\n1. INNER WEST LEP DOCUMENT COVERAGE:")
    print("-" * 60)

    cur.execute("""
        SELECT
            document_id,
            COUNT(*) as provisions,
            COUNT(DISTINCT ref_number) as unique_clauses,
            COUNT(DISTINCT provision_type) as provision_types
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        GROUP BY document_id
        ORDER BY provisions DESC
    """)

    results = cur.fetchall()
    total_provisions = 0
    total_clauses = 0

    for row in results:
        print(f"{row[0][:50]+'...' if len(row[0]) > 50 else row[0]:<53}: {row[1]:>4} provisions, {row[2]:>3} clauses, {row[3]:>2} types")
        total_provisions += row[1]
        total_clauses += row[2]

    print(f"\nTOTAL LEP CONTENT: {total_provisions} provisions, {total_clauses} unique clause references")

    # 2. Check what LEP parts are covered
    print(f"\n2. LEP PART COVERAGE ANALYSIS:")
    print("-" * 60)

    parts_analysis = [
        ("Part 1 - Preliminary", "1."),
        ("Part 2 - Permitted/Prohibited", "2."),
        ("Part 3 - Exempt/Complying", "3."),
        ("Part 4 - Development Standards", "4."),
        ("Part 5 - Miscellaneous", "5."),
        ("Part 6 - Local Provisions", "6."),
        ("Part 7 - Additional Local Provisions", "7.")
    ]

    for part_name, part_prefix in parts_analysis:
        cur.execute("""
            SELECT
                COUNT(*) as provisions,
                COUNT(DISTINCT ref_number) as clauses,
                STRING_AGG(DISTINCT ref_number, ', ' ORDER BY ref_number) as clause_list
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND ref_number LIKE %s
        """, (f'{part_prefix}%',))

        result = cur.fetchone()
        print(f"{part_name:<35}: {result[0]:>3} provisions, {result[1]:>2} clauses")
        if result[2] and len(result[2]) < 200:
            print(f"  Clauses: {result[2]}")
        elif result[2]:
            print(f"  Clauses: {result[2][:150]}...")

    # 3. Zone-related content
    print(f"\n3. ZONING AND LAND USE CONTENT:")
    print("-" * 60)

    # Check for zone objectives and land uses
    cur.execute("""
        SELECT
            ref_number,
            provision_type,
            LEFT(provision_text, 100) as text_preview
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND (provision_text ILIKE '%zone%objective%'
             OR provision_text ILIKE '%permitted with consent%'
             OR provision_text ILIKE '%permitted without consent%'
             OR provision_text ILIKE '%prohibited%'
             OR ref_number ~ '^2\\.[1-9]')
        ORDER BY ref_number
        LIMIT 20
    """)

    results = cur.fetchall()
    print("Zone and Land Use Provisions:")
    for row in results:
        print(f"  {row[0]:<8} | {row[1]:<25} | {row[2]}...")

    # 4. Development standards content
    print(f"\n4. DEVELOPMENT STANDARDS CONTENT:")
    print("-" * 60)

    # Check specific development standards
    standards_clauses = ['4.1', '4.2', '4.3', '4.4', '4.5', '4.6']

    for clause in standards_clauses:
        cur.execute("""
            SELECT
                provision_type,
                COUNT(*) as count,
                MAX(LENGTH(provision_text)) as max_length
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND ref_number LIKE %s
            GROUP BY provision_type
            ORDER BY count DESC
        """, (f'{clause}%',))

        results = cur.fetchall()
        if results:
            print(f"\nClause {clause} content:")
            for row in results:
                print(f"  {row[0]:<30}: {row[1]:>2} provisions, max {row[2]:>3} chars")

    # 5. Heritage and environmental content
    print(f"\n5. HERITAGE AND ENVIRONMENTAL PROVISIONS:")
    print("-" * 60)

    cur.execute("""
        SELECT
            ref_number,
            provision_type,
            COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND (ref_number LIKE '5.%' OR provision_text ILIKE '%heritage%')
        GROUP BY ref_number, provision_type
        ORDER BY ref_number
        LIMIT 15
    """)

    results = cur.fetchall()
    if results:
        print("Heritage and Environmental Clauses:")
        for row in results:
            print(f"  {row[0]:<8} | {row[1]:<30} | {row[2]:>2} provisions")

    # 6. Check for relationships and cross-references
    print(f"\n6. CROSS-REFERENCES AND RELATIONSHIPS:")
    print("-" * 60)

    cur.execute("""
        SELECT
            provision_type,
            COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND provision_type LIKE '%relationship%'
        GROUP BY provision_type
        ORDER BY count DESC
    """)

    results = cur.fetchall()
    if results:
        print("Relationship Types in LEP:")
        for row in results:
            print(f"  {row[0]:<35}: {row[1]:>3} relationships")

    # 7. Sample some complete clauses to check content quality
    print(f"\n7. SAMPLE CLAUSE CONTENT QUALITY:")
    print("-" * 60)

    sample_clauses = ['2.1', '2.2', '4.3', '4.4', '5.10']

    for clause in sample_clauses:
        cur.execute("""
            SELECT
                provision_type,
                provision_text,
                LENGTH(provision_text) as length
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND ref_number = %s
            AND provision_text IS NOT NULL
            ORDER BY LENGTH(provision_text) DESC
            LIMIT 1
        """, (clause,))

        result = cur.fetchone()
        if result:
            text = result[1][:200] + ('...' if len(result[1]) > 200 else '')
            print(f"\nClause {clause} ({result[0]}, {result[2]} chars):")
            print(f"  {text}")

    conn.close()

print("\nDeep analysis completed.")