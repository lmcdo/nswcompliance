from db_config import get_connection

c = get_connection()
cur = c.cursor()

print("=== TRANSPORT AND INFRASTRUCTURE SEPP PROVISIONS ===\n")

# Search for any provisions from Transport and Infrastructure SEPP
cur.execute("""
    SELECT id, provision_text, ref_number, document_id, provision_type
    FROM regulatory_provisions
    WHERE document_id ILIKE '%transport%infrastructure%'
    OR document_id ILIKE '%transport%infra%'
    OR provision_text ILIKE '%transport%infrastructure%sepp%'
    LIMIT 20
""")

rows = cur.fetchall()

if rows:
    print(f"Found {len(rows)} provisions from Transport and Infrastructure SEPP:\n")
    for row in rows:
        print(f"ID: {row[0]}")
        print(f"Ref: {row[2]}")
        print(f"Document: {row[3]}")
        print(f"Type: {row[4]}")
        print(f"Text: {row[1][:300]}...")
        print("\n" + "="*80 + "\n")
else:
    print("No provisions found with 'Transport and Infrastructure' in document_id or text")
    print("\nSearching for all unique document_ids containing 'SEPP'...\n")

    cur.execute("""
        SELECT DISTINCT document_id, COUNT(*) as provision_count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%sepp%'
        GROUP BY document_id
        ORDER BY provision_count DESC
    """)

    sepp_docs = cur.fetchall()
    for doc in sepp_docs:
        print(f"{doc[0]}: {doc[1]} provisions")

c.close()