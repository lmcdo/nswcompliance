"""Check provision ID mismatch issue"""

from db_safety_wrapper import get_safe_connection

def check_ids():
    conn = get_safe_connection()
    cur = conn.cursor()

    # Check if IDs 292-296 exist anywhere
    print("=== Checking if IDs 292-296 exist ===\n")

    cur.execute("""
        SELECT id, document_id, ref_number
        FROM regulatory_provisions
        WHERE id IN (292, 293, 294, 295, 296)
    """)

    rows = cur.fetchall()
    if rows:
        print(f"Found {len(rows)} provisions with these IDs:")
        for row in rows:
            print(f"  ID {row[0]}: {row[1]} - {row[2]}")
    else:
        print("No provisions found with IDs 292-296")

    # Check what document_id is stored in dcp_precinct_provisions
    print("\n=== Checking precinct_id in dcp_precinct_requirements ===\n")

    cur.execute("""
        SELECT DISTINCT precinct_id, precinct_name, source_document_ids[1] as first_doc
        FROM dcp_precinct_requirements
        WHERE precinct_name = 'Abergeldie Estate'
    """)

    rows = cur.fetchall()
    for row in rows:
        print(f"  Precinct ID: {row[0]}")
        print(f"  Precinct Name: {row[1]}")
        print(f"  Source Document: {row[2]}")

    # Check how many precincts have this issue
    print("\n=== Checking all precincts for wrong provision IDs ===\n")

    cur.execute("""
        SELECT
            pr.precinct_name,
            COUNT(*) as req_count,
            ARRAY_AGG(DISTINCT unnest(pr.source_provision_ids)) as all_ids
        FROM dcp_precinct_requirements pr
        GROUP BY pr.precinct_name
        LIMIT 5
    """)

    rows = cur.fetchall()
    print(f"Sample of precinct provision IDs:")
    for row in rows:
        # Check if any of the IDs exist
        ids_to_check = row[2][:5] if len(row[2]) > 5 else row[2]

        cur.execute("""
            SELECT COUNT(*) FROM regulatory_provisions
            WHERE id = ANY(%s)
        """, (ids_to_check,))

        existing_count = cur.fetchone()[0]

        print(f"\n  {row[0]}: {row[1]} requirements")
        print(f"    Sample IDs: {ids_to_check}")
        print(f"    Existing in DB: {existing_count}/{len(ids_to_check)}")

    conn.close()

if __name__ == '__main__':
    check_ids()
