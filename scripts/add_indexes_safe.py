"""
Add Performance Indexes Safely
Uses psycopg2 to add indexes with proper error handling
"""

import psycopg2
from psycopg2 import sql
import time

# Index definitions: (name, table, columns, type, purpose)
INDEXES_TO_CREATE = [
    # GIN indexes for array queries (Priority 1)
    {
        "name": "idx_dcp_gen_req_zones_gin",
        "table": "dcp_general_requirements",
        "column": "applicable_zones",
        "type": "GIN",
        "purpose": "Speeds up zone filtering in Ashfield queries (ANY operator)",
        "code_location": "route.ts:857"
    },
    {
        "name": "idx_dcp_gen_req_devtypes_gin",
        "table": "dcp_general_requirements",
        "column": "development_types",
        "type": "GIN",
        "purpose": "Speeds up development type filtering (ANY operator)",
        "code_location": "route.ts:858"
    },
    {
        "name": "idx_dcp_gen_prov_zones_gin",
        "table": "dcp_general_provisions",
        "column": "applicable_zones",
        "type": "GIN",
        "purpose": "Speeds up provision filtering by zone",
        "code_location": "route.ts:206"
    },
    {
        "name": "idx_dcp_gen_prov_devtypes_gin",
        "table": "dcp_general_provisions",
        "column": "development_types",
        "type": "GIN",
        "purpose": "Speeds up provision filtering by development type",
        "code_location": "route.ts:207"
    },
    # B-tree indexes for core queries (Priority 1)
    {
        "name": "idx_dcp_gen_req_former_council",
        "table": "dcp_general_requirements",
        "column": "former_council",
        "type": "BTREE",
        "purpose": "Critical for Inner West council filtering",
        "code_location": "route.ts:859,891,922"
    },
    {
        "name": "idx_reg_prov_document_id",
        "table": "regulatory_provisions",
        "column": "document_id",
        "type": "BTREE",
        "purpose": "Critical for fallback query performance (48k rows)",
        "code_location": "route.ts:358,508"
    },
]

def create_indexes():
    """Create all performance indexes safely"""

    print("=" * 80)
    print("PERFORMANCE INDEX CREATION - Safe Mode")
    print("=" * 80)
    print()
    print(f"Adding {len(INDEXES_TO_CREATE)} indexes for query optimization")
    print()

    conn = psycopg2.connect(
        host="localhost",
        database="nsw_planning",
        user="postgres",
        password="postgres"
    )

    # Use autocommit for CREATE INDEX CONCURRENTLY
    # (can't run in transaction block)
    conn.set_session(autocommit=True)
    cursor = conn.cursor()

    results = {
        "created": [],
        "already_exists": [],
        "failed": []
    }

    for i, idx_def in enumerate(INDEXES_TO_CREATE, 1):
        name = idx_def["name"]
        table = idx_def["table"]
        column = idx_def["column"]
        idx_type = idx_def["type"]
        purpose = idx_def["purpose"]
        location = idx_def["code_location"]

        print(f"[{i}/{len(INDEXES_TO_CREATE)}] Creating {idx_type} index: {name}")
        print(f"      Table: {table}")
        print(f"      Column: {column}")
        print(f"      Purpose: {purpose}")
        print(f"      Used in: {location}")

        # Check if index already exists
        cursor.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE schemaname = 'public'
            AND indexname = %s
        """, (name,))

        if cursor.fetchone():
            print(f"      STATUS: Already exists (skipping)")
            results["already_exists"].append(name)
            print()
            continue

        # Create index
        try:
            start_time = time.time()

            if idx_type == "GIN":
                # GIN index for array columns
                create_sql = f"""
                    CREATE INDEX CONCURRENTLY {name}
                    ON {table} USING GIN ({column})
                """
            else:  # BTREE
                # B-tree index for regular columns
                create_sql = f"""
                    CREATE INDEX CONCURRENTLY {name}
                    ON {table} ({column})
                """

            cursor.execute(create_sql)

            elapsed = time.time() - start_time
            print(f"      STATUS: Created successfully ({elapsed:.2f}s)")

            # Get index size
            cursor.execute(f"""
                SELECT pg_size_pretty(pg_relation_size('{name}'))
            """)
            size = cursor.fetchone()[0]
            print(f"      Size: {size}")

            results["created"].append(name)

        except Exception as e:
            print(f"      STATUS: Failed - {e}")
            results["failed"].append((name, str(e)))

        print()

    # Update table statistics (critical for query planner)
    print("Updating table statistics for query planner...")
    tables_to_analyze = list(set(idx["table"] for idx in INDEXES_TO_CREATE))

    for table in tables_to_analyze:
        cursor.execute(f"ANALYZE {table}")
        print(f"  ✓ {table}")

    print()

    # Show summary
    print("=" * 80)
    print("INDEX CREATION SUMMARY")
    print("=" * 80)
    print(f"Created: {len(results['created'])}")
    print(f"Already existed: {len(results['already_exists'])}")
    print(f"Failed: {len(results['failed'])}")
    print()

    if results["created"]:
        print("New indexes created:")
        for name in results["created"]:
            print(f"  ✓ {name}")
        print()

    if results["already_exists"]:
        print("Indexes already existed (no action needed):")
        for name in results["already_exists"]:
            print(f"  - {name}")
        print()

    if results["failed"]:
        print("FAILED indexes (review errors):")
        for name, error in results["failed"]:
            print(f"  ✗ {name}: {error}")
        print()

    # Show total index sizes by table
    print("Total index sizes by table:")
    for table in tables_to_analyze:
        cursor.execute(f"""
            SELECT pg_size_pretty(pg_indexes_size('{table}'::regclass))
        """)
        size = cursor.fetchone()[0]
        print(f"  {table}: {size}")

    print()

    # Show database size
    cursor.execute("SELECT pg_size_pretty(pg_database_size('nsw_planning'))")
    db_size = cursor.fetchone()[0]
    print(f"Total database size: {db_size}")
    print()

    cursor.close()
    conn.close()

    # Return success if no failures
    return len(results["failed"]) == 0

if __name__ == "__main__":
    try:
        success = create_indexes()

        if success:
            print("=" * 80)
            print("SUCCESS: All indexes created")
            print("=" * 80)
            print()
            print("Next steps:")
            print("  1. Test API performance: python scripts/test_query_performance.py")
            print("  2. Verify index usage: python scripts/verify_index_usage.py")
            print("  3. Monitor application logs for query times")
            print()
            print("If you need to rollback:")
            print("  python scripts/rollback_indexes.py")
            print()
            exit(0)
        else:
            print("=" * 80)
            print("WARNING: Some indexes failed to create")
            print("=" * 80)
            print("Review errors above and check:")
            print("  - Database connection")
            print("  - Disk space")
            print("  - PostgreSQL version (need 9.4+ for CONCURRENTLY)")
            print()
            exit(1)

    except Exception as e:
        print()
        print("=" * 80)
        print("ERROR: Unexpected failure")
        print("=" * 80)
        print(f"Error: {e}")
        print()
        print("Database state should be unchanged (CREATE INDEX CONCURRENTLY is atomic)")
        print()
        exit(1)
