"""Check which precinct 170 Illawarra Rd belongs to"""

from db_safety_wrapper import get_safe_connection

def check_address_precinct():
    conn = get_safe_connection()
    cur = conn.cursor()

    address = "170 ILLAWARRA ROAD MARRICKVILLE 2204"

    print("=== Checking Precinct for 170 Illawarra Rd ===\n")

    # Check what precincts exist for Marrickville
    cur.execute("""
        SELECT DISTINCT precinct_id, precinct_name, lga, COUNT(*) as req_count
        FROM dcp_precinct_requirements
        WHERE lga = 'Inner West'
        AND precinct_name ILIKE '%marrickville%'
        GROUP BY precinct_id, precinct_name, lga
        ORDER BY precinct_name
    """)

    rows = cur.fetchall()
    print(f"Found {len(rows)} Marrickville precincts:\n")
    for precinct_id, precinct_name, lga, count in rows:
        print(f"  {precinct_id}: {precinct_name} ({count} requirements)")

    # Check if "South Western Marrickville" exists
    print("\n=== Checking South Western Marrickville ===\n")

    cur.execute("""
        SELECT precinct_id, precinct_name, COUNT(*) as req_count
        FROM dcp_precinct_requirements
        WHERE precinct_name ILIKE '%south western%'
        GROUP BY precinct_id, precinct_name
    """)

    rows = cur.fetchall()
    if rows:
        for precinct_id, precinct_name, count in rows:
            print(f"  {precinct_id}: {precinct_name} ({count} requirements)")
    else:
        print("  No 'South Western Marrickville' precinct found")

    # Check what the API would return
    print("\n=== What API returns for 'South Western Marrickville' ===\n")

    cur.execute("""
        SELECT id, category, requirement_text
        FROM dcp_precinct_requirements
        WHERE precinct_name ILIKE '%south western marrickville%'
        LIMIT 5
    """)

    rows = cur.fetchall()
    print(f"  Found {len(rows)} requirements")
    for req_id, category, text in rows:
        print(f"    Req {req_id} ({category}): {text[:60]}...")

    # Check total requirements count
    print("\n=== Total Requirements Check ===\n")

    cur.execute("SELECT COUNT(*) FROM dcp_precinct_requirements")
    total = cur.fetchone()[0]
    print(f"  Total requirements in database: {total}")

    conn.close()

if __name__ == '__main__':
    check_address_precinct()
