"""Check provision IDs for Abergeldie Estate"""

from db_safety_wrapper import get_safe_connection

def check_provisions():
    conn = get_safe_connection()
    cur = conn.cursor()

    # Check provision IDs for Abergeldie
    print("=== Checking Abergeldie Estate Provisions ===\n")

    cur.execute("""
        SELECT id, ref_number, LEFT(provision_text, 80) as text
        FROM regulatory_provisions
        WHERE document_id LIKE '%Abergeldie%'
        ORDER BY id
        LIMIT 10
    """)

    rows = cur.fetchall()
    print(f"Found {len(rows)} provisions for Abergeldie Estate:")
    for row in rows:
        print(f"  ID {row[0]}: {row[1]} - {row[2]}")

    # Check what IDs are referenced in categorized requirements
    print("\n=== Checking Referenced Provision IDs ===\n")

    cur.execute("""
        SELECT id, category, source_provision_ids
        FROM dcp_precinct_requirements
        WHERE precinct_name = 'Abergeldie Estate'
        LIMIT 5
    """)

    rows = cur.fetchall()
    print(f"Found {len(rows)} categorized requirements:")
    for row in rows:
        print(f"  Req ID {row[0]} ({row[1]}): references provisions {row[2]}")

    conn.close()

if __name__ == '__main__':
    check_provisions()
