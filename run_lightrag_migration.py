"""
Run LightRAG categorization schema migration
"""
import os
from dotenv import load_dotenv
from db_safety_wrapper import get_safe_connection

load_dotenv()

print("=" * 80)
print("LIGHTRAG SCHEMA MIGRATION")
print("=" * 80)

# Read migration SQL
with open('migrations/create_lightrag_categorization_schema.sql', 'r') as f:
    migration_sql = f.read()

print("\nRunning migration...")

with get_safe_connection(
    host=os.getenv('PGHOST'),
    database=os.getenv('PGDATABASE'),
    user=os.getenv('PGUSER'),
    port=int(os.getenv('PGPORT', 5432))
) as safe_conn:
    cur = safe_conn.cursor()

    try:
        # Execute migration
        cur.execute(migration_sql)

        # Commit
        safe_conn.commit()

        print("\nMigration completed successfully")

        # Verify tables created
        print("\nVerifying tables created:")
        required_tables = [
            'dcp_base_requirements',
            'dcp_precinct_requirements',
            'categorization_validation',
            'requirement_categories'
        ]

        for table in required_tables:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
            """, (table,))
            exists = cur.fetchone()[0]

            if exists:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                count = cur.fetchone()[0]
                print(f"  [OK] {table} (rows: {count})")
            else:
                print(f"  [FAILED] {table} not created")

        # Verify views created
        print("\nVerifying views created:")
        required_views = [
            'v_requirements_by_address',
            'v_validation_metrics'
        ]

        for view in required_views:
            cur.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.views
                    WHERE table_schema = 'public'
                    AND table_name = %s
                )
            """, (view,))
            exists = cur.fetchone()[0]

            if exists:
                print(f"  [OK] {view}")
            else:
                print(f"  [FAILED] {view} not created")

        print("\n" + "=" * 80)
        print("MIGRATION COMPLETE")
        print("=" * 80)
        print("Status: SUCCESS")
        print("\nNext Step: Set up LightRAG processing environment")
        print("=" * 80)

    except Exception as e:
        print(f"\nERROR: Migration failed")
        print(f"Details: {str(e)}")
        safe_conn.rollback()
        print("\nTransaction rolled back")
