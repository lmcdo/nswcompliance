from db_safety_wrapper import get_safe_connection

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== CHECKING FULL CLAUSE TEXT LENGTH ===")

    # Check clause 4.4 (FSR) - ID 17473
    cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = %s", (17473,))
    result = cur.fetchone()
    if result:
        text = result[0]
        print(f"Clause 4.4 (FSR) - Full text length: {len(text)} characters")
        print(f"Full text:")
        print(text)
        print("\n" + "="*100)

    # Check clause 4.3 (Height) - ID 17479
    cur.execute("SELECT provision_text FROM regulatory_provisions WHERE id = %s", (17479,))
    result = cur.fetchone()
    if result:
        text = result[0]
        print(f"\nClause 4.3 (Height) - Full text length: {len(text)} characters")
        print(f"Full text:")
        print(text)
        print("\n" + "="*100)

    # Also check if there are longer versions of clause 4.4
    print(f"\n=== CHECKING FOR LONGER VERSIONS OF CLAUSE 4.4 ===")
    cur.execute("""
        SELECT id, LENGTH(provision_text) as length, provision_text
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND ref_number = '4.4'
        AND provision_text IS NOT NULL
        ORDER BY LENGTH(provision_text) DESC
    """)

    results = cur.fetchall()
    for row in results:
        print(f"ID: {row[0]}, Length: {row[1]} chars")
        print(f"Text: {row[2]}")
        print("-" * 80)

    conn.close()