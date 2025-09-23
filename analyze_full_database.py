from db_safety_wrapper import get_safe_connection
import json

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== COMPREHENSIVE DATABASE ANALYSIS FOR LEP CONTENT ===")

    # 1. Full table analysis
    print("\n1. DATABASE TABLES AND RECORD COUNTS:")
    print("-" * 60)

    tables = [
        'regulatory_provisions', 'development_controls', 'quantitative_standards',
        'kg_entities', 'kg_relationships', 'documents', 'zone_setback_rules',
        'contextual_guidance_real', 'visual_elements_real'
    ]

    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"{table:<25}: {count:>8} records")
        except Exception as e:
            print(f"{table:<25}: ERROR - {e}")

    # 2. LEP-specific content analysis
    print(f"\n2. INNER WEST LEP CONTENT ANALYSIS:")
    print("-" * 60)

    # Check regulatory_provisions for LEP content
    cur.execute("""
        SELECT
            provision_type,
            COUNT(*) as count,
            COUNT(DISTINCT ref_number) as unique_refs
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        GROUP BY provision_type
        ORDER BY count DESC
        LIMIT 15
    """)

    results = cur.fetchall()
    print("LEP Provision Types:")
    for row in results:
        print(f"  {row[0]:<35}: {row[1]:>4} provisions, {row[2]:>3} unique refs")

    # 3. Zone and development controls
    print(f"\n3. ZONE AND DEVELOPMENT CONTROLS:")
    print("-" * 60)

    # Check development_controls table
    cur.execute("""
        SELECT
            control_type,
            COUNT(*) as count
        FROM development_controls
        WHERE document_source ILIKE '%Inner_West%' OR document_source ILIKE '%LEP%'
        GROUP BY control_type
        ORDER BY count DESC
        LIMIT 10
    """)

    results = cur.fetchall()
    if results:
        print("Development Control Types:")
        for row in results:
            print(f"  {row[0]:<25}: {row[1]:>4} controls")
    else:
        print("No development controls found for Inner West LEP")

    # Check zone_setback_rules
    cur.execute("""
        SELECT
            zone_type,
            development_type,
            COUNT(*) as count
        FROM zone_setback_rules
        GROUP BY zone_type, development_type
        ORDER BY count DESC
        LIMIT 15
    """)

    results = cur.fetchall()
    if results:
        print("\nZone Setback Rules:")
        for row in results:
            print(f"  {row[0]} - {row[1]}: {row[2]} rules")

    # 4. Knowledge Graph Analysis
    print(f"\n4. KNOWLEDGE GRAPH ENTITIES AND RELATIONSHIPS:")
    print("-" * 60)

    # Check kg_entities for LEP entities
    cur.execute("""
        SELECT
            entity_type,
            COUNT(*) as count
        FROM kg_entities
        WHERE source_document ILIKE '%Inner_West%' OR source_document ILIKE '%LEP%'
        GROUP BY entity_type
        ORDER BY count DESC
        LIMIT 10
    """)

    results = cur.fetchall()
    if results:
        print("LEP Knowledge Graph Entities:")
        for row in results:
            print(f"  {row[0]:<25}: {row[1]:>4} entities")

    # Check relationships
    cur.execute("""
        SELECT
            relationship_type,
            COUNT(*) as count
        FROM kg_relationships
        WHERE source_document ILIKE '%Inner_West%' OR source_document ILIKE '%LEP%'
        GROUP BY relationship_type
        ORDER BY count DESC
        LIMIT 10
    """)

    results = cur.fetchall()
    if results:
        print("\nLEP Knowledge Graph Relationships:")
        for row in results:
            print(f"  {row[0]:<25}: {row[1]:>4} relationships")

    # 5. Check for specific LEP clauses
    print(f"\n5. SPECIFIC LEP CLAUSE COVERAGE:")
    print("-" * 60)

    # Check what Part 2, 3, 4, 5, 6 content exists
    parts_check = ['1.', '2.', '3.', '4.', '5.', '6.']

    for part in parts_check:
        cur.execute("""
            SELECT COUNT(DISTINCT ref_number)
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND ref_number LIKE %s
        """, (f'{part}%',))

        count = cur.fetchone()[0]
        print(f"  Part {part[0]} clauses: {count} unique references")

    # 6. Sample some specific important clauses
    print(f"\n6. SAMPLE IMPORTANT CLAUSE COVERAGE:")
    print("-" * 60)

    important_clauses = ['2.1', '2.2', '2.3', '4.1', '4.3', '4.4', '5.10', '6.1']

    for clause in important_clauses:
        cur.execute("""
            SELECT COUNT(*), MAX(LENGTH(provision_text)) as max_length
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND ref_number = %s
            AND provision_text IS NOT NULL
        """, (clause,))

        result = cur.fetchone()
        if result and result[0] > 0:
            print(f"  Clause {clause}: {result[0]} provisions, max length {result[1]} chars")
        else:
            print(f"  Clause {clause}: Not found")

    conn.close()

print("\nAnalysis completed.")