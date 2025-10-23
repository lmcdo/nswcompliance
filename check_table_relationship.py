"""Check relationship between tables"""

from db_safety_wrapper import get_safe_connection

def check_tables():
    conn = get_safe_connection()
    cur = conn.cursor()

    # Check dcp_precinct_provisions
    print("=== dcp_precinct_provisions Table ===\n")

    cur.execute("SELECT COUNT(*) FROM dcp_precinct_provisions")
    count = cur.fetchone()[0]
    print(f"Total rows: {count}")

    cur.execute("""
        SELECT id, document_id, LEFT(provision_text, 60)
        FROM dcp_precinct_provisions
        WHERE precinct_id = '16_'
        ORDER BY id
        LIMIT 7
    """)

    rows = cur.fetchall()
    print(f"\nAbergeldie provisions in dcp_precinct_provisions:")
    for row in rows:
        print(f"  ID {row[0]}: {row[1][:40]}... - {row[2]}...")

    # Check regulatory_provisions
    print("\n=== regulatory_provisions Table ===\n")

    cur.execute("""
        SELECT id, document_id, LEFT(provision_text, 60)
        FROM regulatory_provisions
        WHERE document_id LIKE '%Abergeldie%'
        ORDER BY id
        LIMIT 7
    """)

    rows = cur.fetchall()
    print(f"Abergeldie provisions in regulatory_provisions:")
    for row in rows:
        print(f"  ID {row[0]}: {row[1][:40]}... - {row[2]}...")

    # Check if there's a mapping
    print("\n=== Checking for ID mapping ===\n")

    cur.execute("""
        SELECT
            dpp.id as dpp_id,
            rp.id as rp_id,
            dpp.document_id,
            LEFT(dpp.provision_text, 50) as dpp_text,
            LEFT(rp.provision_text, 50) as rp_text
        FROM dcp_precinct_provisions dpp
        LEFT JOIN regulatory_provisions rp
            ON dpp.document_id = rp.document_id
            AND dpp.provision_text = rp.provision_text
        WHERE dpp.precinct_id = '16_'
        LIMIT 5
    """)

    rows = cur.fetchall()
    print("Attempting to match provisions by text:")
    for row in rows:
        if row[1]:
            print(f"  dcp_precinct_provisions ID {row[0]} → regulatory_provisions ID {row[1]}")
        else:
            print(f"  dcp_precinct_provisions ID {row[0]} → NO MATCH in regulatory_provisions")

    conn.close()

if __name__ == '__main__':
    check_tables()
