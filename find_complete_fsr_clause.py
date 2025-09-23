from db_safety_wrapper import get_safe_connection

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    print("=== SEARCHING FOR COMPLETE FSR CLAUSE TEXT ===")

    # Search for any provision that might contain the complete clause 4.4 text
    cur.execute("""
        SELECT id, ref_number, provision_type, provision_text, document_id, LENGTH(provision_text) as length
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND (provision_text ILIKE '%floor space ratio for a building%'
             OR provision_text ILIKE '%floor space ratio shown%'
             OR provision_text ILIKE '%FSR Map%'
             OR provision_text ILIKE '%Floor Space Ratio Map%'
             OR (ref_number = '4.4' AND LENGTH(provision_text) > 500))
        ORDER BY LENGTH(provision_text) DESC
        LIMIT 10
    """)

    results = cur.fetchall()
    print(f"Found {len(results)} potentially complete FSR clauses:")

    for row in results:
        print(f"\n--- ID: {row[0]}, Ref: {row[1]}, Type: {row[2]}, Length: {row[5]} ---")
        print(f"Document: {row[4]}")
        print(f"Text: {row[3]}")
        print("-" * 100)

    # Also check for any formal FSR provisions
    print(f"\n=== CHECKING FORMAL FSR PROVISIONS ===")
    cur.execute("""
        SELECT id, ref_number, provision_type, provision_text, LENGTH(provision_text) as length
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Inner_West_Local_Environmental_Plan%'
        AND provision_type ILIKE '%formal%'
        AND provision_text ILIKE '%floor space%'
        ORDER BY LENGTH(provision_text) DESC
        LIMIT 5
    """)

    results = cur.fetchall()
    for row in results:
        print(f"\n--- Formal FSR ID: {row[0]}, Ref: {row[1]}, Length: {row[4]} ---")
        print(f"Text: {row[3]}")

    conn.close()