"""
Verify Performance Indexes Were Created
"""

import psycopg2

def verify_indexes():
    """Verify all performance indexes exist and show their stats"""

    print("=" * 80)
    print("INDEX VERIFICATION")
    print("=" * 80)
    print()

    conn = psycopg2.connect(
        host="localhost",
        database="nsw_planning",
        user="postgres",
        password="postgres"
    )
    cursor = conn.cursor()

    # Expected indexes
    expected_indexes = [
        "idx_dcp_gen_req_zones_gin",
        "idx_dcp_gen_req_devtypes_gin",
        "idx_dcp_gen_prov_zones_gin",
        "idx_dcp_gen_prov_devtypes_gin",
        "idx_dcp_gen_req_former_council",
        "idx_reg_prov_document_id",
    ]

    print("Checking for performance indexes...")
    print()

    all_found = True
    for idx_name in expected_indexes:
        cursor.execute("""
            SELECT
                schemaname,
                relname as tablename,
                indexrelname as indexname,
                pg_size_pretty(pg_relation_size(indexrelid)) AS size,
                idx_scan as times_used
            FROM pg_stat_user_indexes
            WHERE indexrelname = %s
        """, (idx_name,))

        result = cursor.fetchone()
        if result:
            schema, table, name, size, times_used = result
            print(f"  OK {name}")
            print(f"      Table: {table}")
            print(f"      Size: {size}")
            print(f"      Times used: {times_used}")
            print()
        else:
            print(f"  MISSING: {idx_name}")
            all_found = False

    if all_found:
        print("=" * 80)
        print("SUCCESS: All 6 indexes verified")
        print("=" * 80)
    else:
        print("=" * 80)
        print("WARNING: Some indexes missing")
        print("=" * 80)

    print()

    # Show total index sizes by table
    print("Total index sizes by table:")
    cursor.execute("""
        SELECT
            tablename,
            pg_size_pretty(pg_indexes_size(tablename::regclass)) AS total_index_size,
            COUNT(*) as index_count
        FROM pg_indexes
        WHERE schemaname = 'public'
        AND tablename IN ('dcp_general_requirements', 'dcp_general_provisions', 'regulatory_provisions')
        GROUP BY tablename
        ORDER BY pg_indexes_size(tablename::regclass) DESC
    """)

    for table, size, count in cursor.fetchall():
        print(f"  {table}: {size} ({count} indexes)")

    print()

    # Show database size
    cursor.execute("SELECT pg_size_pretty(pg_database_size('nsw_planning'))")
    db_size = cursor.fetchone()[0]
    print(f"Total database size: {db_size}")
    print()

    cursor.close()
    conn.close()

    return all_found

if __name__ == "__main__":
    success = verify_indexes()
    exit(0 if success else 1)
