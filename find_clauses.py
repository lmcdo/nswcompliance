from db_safety_wrapper import get_safe_connection
import json

conn = get_safe_connection()
if conn:
    cur = conn.cursor()

    # Check for clause 4.3 and 4.4 content
    print("Checking for clause 4.3 (Building Height) and 4.4 (FSR) content...")
    cur.execute("""
        SELECT ref_number, provision_type, provision_text, document_id, section_header
        FROM regulatory_provisions
        WHERE (ref_number LIKE '4.3%' OR ref_number LIKE '4.4%'
               OR provision_text ILIKE '%height of building%'
               OR provision_text ILIKE '%floor space ratio%'
               OR section_header ILIKE '%height%'
               OR section_header ILIKE '%FSR%')
        AND provision_text IS NOT NULL
        AND LENGTH(provision_text) > 50
        LIMIT 10
    """)
    results = cur.fetchall()
    if results:
        for row in results:
            print(f'\nRef: {row[0]}')
            print(f'Type: {row[1]}')
            print(f'Document: {row[3]}')
            print(f'Section: {row[4]}')
            if row[2]:
                print(f'Content length: {len(row[2])}')
                print(f'Content preview: {row[2][:400]}...')
            print('---')
    else:
        print("No relevant clauses found")

    # Also check if there's LEP data
    print("\n\nChecking for Inner West LEP data...")
    cur.execute("""
        SELECT DISTINCT document_id, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%inner%west%'
           OR document_id ILIKE '%LEP%'
        GROUP BY document_id
        LIMIT 5
    """)
    docs = cur.fetchall()
    if docs:
        print("Found documents:")
        for doc in docs:
            print(f"  - {doc[0]}: {doc[1]} provisions")
    else:
        print("No Inner West LEP documents found")

    conn.close()