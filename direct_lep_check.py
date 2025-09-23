from db_safety_wrapper import get_safe_connection

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== DIRECT LEP DATABASE EXAMINATION ===")

    # 1. Basic count check
    print("\n1. BASIC LEP CONTENT:")
    print("-" * 40)

    try:
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        """)
        total = cur.fetchone()
        if total:
            print(f"Total LEP provisions: {total[0]}")
    except Exception as e:
        print(f"Error getting total: {e}")

    # 2. Check clause 4.3 and 4.4 in detail
    print(f"\n2. CLAUSE 4.3 AND 4.4 CONTENT:")
    print("-" * 40)

    for clause_num in ['4.3', '4.4']:
        try:
            cur.execute("""
                SELECT provision_type, provision_text
                FROM regulatory_provisions
                WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
                AND ref_number = %s
                AND provision_text IS NOT NULL
                ORDER BY LENGTH(provision_text) DESC
                LIMIT 3
            """, (clause_num,))

            results = cur.fetchall()
            print(f"\nClause {clause_num} ({len(results)} found):")
            for i, row in enumerate(results):
                text_len = len(row[1]) if row[1] else 0
                text_preview = row[1][:100] if row[1] else "No text"
                print(f"  {i+1}. {row[0]} ({text_len} chars): {text_preview}...")
        except Exception as e:
            print(f"Error checking clause {clause_num}: {e}")

    # 3. Check what ref_numbers exist
    print(f"\n3. SAMPLE REFERENCE NUMBERS:")
    print("-" * 40)

    try:
        cur.execute("""
            SELECT DISTINCT ref_number
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND ref_number ~ '^[0-9]\\.[0-9]'
            ORDER BY ref_number
            LIMIT 20
        """)

        results = cur.fetchall()
        print("Found clause numbers:")
        for row in results:
            print(f"  {row[0]}")
    except Exception as e:
        print(f"Error getting ref numbers: {e}")

    # 4. Check provision types
    print(f"\n4. PROVISION TYPES:")
    print("-" * 40)

    try:
        cur.execute("""
            SELECT provision_type, COUNT(*)
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            GROUP BY provision_type
            ORDER BY COUNT(*) DESC
            LIMIT 15
        """)

        results = cur.fetchall()
        print("Top provision types:")
        for row in results:
            print(f"  {row[0]}: {row[1]} provisions")
    except Exception as e:
        print(f"Error getting provision types: {e}")

    # 5. Check for complete clause 4.4 text
    print(f"\n5. CLAUSE 4.4 TEXT INVESTIGATION:")
    print("-" * 40)

    try:
        cur.execute("""
            SELECT id, provision_type, LENGTH(provision_text), provision_text
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
            AND ref_number = '4.4'
            AND provision_text ILIKE '%floor space ratio%'
            ORDER BY LENGTH(provision_text) DESC
        """)

        results = cur.fetchall()
        print(f"Found {len(results)} clause 4.4 provisions:")
        for row in results:
            print(f"  ID {row[0]}: {row[1]} ({row[2]} chars)")
            print(f"    Text: {row[3]}")
    except Exception as e:
        print(f"Error checking clause 4.4: {e}")

    conn.close()

print("\nDirect check completed.")