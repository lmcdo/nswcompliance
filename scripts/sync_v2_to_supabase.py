#!/usr/bin/env python3
"""
Sync v2_ enriched columns from local PostgreSQL to Supabase production.
This syncs only the v2_ enrichment data, not the full database.
"""
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

import psycopg2
from psycopg2.extras import RealDictCursor, execute_values

V2_COLUMNS = [
    'v2_is_actionable',
    'v2_dcp_layer',
    'v2_dcp_part',
    'v2_topic',
    'v2_provision_type',
    'v2_precinct_id',
    'v2_marker',
    'v2_display_behavior',
    'v2_applicable_zones',
    'v2_applicable_dev_types',
    'v2_site_condition_required',
    'v2_has_numeric_value',
    'pdf_page'  # Added for page offset sync
]

def get_local_connection():
    """Connect to local PostgreSQL database."""
    return psycopg2.connect(
        host=os.getenv('PGHOST', 'localhost'),
        port=os.getenv('PGPORT', '5432'),
        database=os.getenv('PGDATABASE', 'nsw_planning'),
        user=os.getenv('PGUSER', 'postgres'),
        password=os.getenv('PGPASSWORD', 'postgres')
    )

def get_supabase_connection():
    """Connect to Supabase production database."""
    url = os.getenv('SUPABASE_DB_URL')
    if not url:
        print("ERROR: SUPABASE_DB_URL not set in .env")
        sys.exit(1)
    return psycopg2.connect(url)

def export_v2_data(local_conn):
    """Export v2_ enriched provisions from local database."""
    cur = local_conn.cursor(cursor_factory=RealDictCursor)

    columns_str = ', '.join(['id'] + V2_COLUMNS)
    cur.execute(f"""
        SELECT {columns_str}
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
        ORDER BY id
    """)

    rows = cur.fetchall()
    print(f"  Exported {len(rows)} enriched provisions from local")
    return rows

def sync_to_supabase(supa_conn, data):
    """Sync v2_ data to Supabase by updating existing rows."""
    cur = supa_conn.cursor()

    # Build UPDATE query
    set_clauses = ', '.join([f"{col} = data.{col}" for col in V2_COLUMNS])
    columns_str = ', '.join(['id'] + V2_COLUMNS)

    updated = 0
    errors = 0

    for row in data:
        try:
            # Build values for this row
            values = [row['id']]
            for col in V2_COLUMNS:
                val = row.get(col)
                values.append(val)

            # Create parameterized UPDATE
            set_parts = []
            params = []
            for i, col in enumerate(V2_COLUMNS):
                set_parts.append(f"{col} = %s")
                params.append(row.get(col))
            params.append(row['id'])  # For WHERE clause

            sql = f"""
                UPDATE regulatory_provisions
                SET {', '.join(set_parts)}
                WHERE id = %s
            """
            cur.execute(sql, params)
            updated += 1

            if updated % 100 == 0:
                print(f"    Updated {updated} rows...")
                supa_conn.commit()

        except Exception as e:
            errors += 1
            if errors <= 5:
                print(f"    Error on id {row['id']}: {e}")

    supa_conn.commit()
    print(f"  Synced {updated} provisions to Supabase ({errors} errors)")
    return updated, errors

def main():
    print("=" * 60)
    print("SYNC V2_ COLUMNS TO SUPABASE")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Confirm before proceeding
    print("\nThis will UPDATE v2_ columns in Supabase production database.")
    print("Make sure you have run the migration first:")
    print("  psql $SUPABASE_DB_URL -f migrations/001_add_v2_columns.sql")
    print()

    confirm = input("Continue? (yes/no): ")
    if confirm.lower() != 'yes':
        print("Aborted.")
        sys.exit(0)

    # Export from local
    print("\n1. Connecting to LOCAL database...")
    local_conn = get_local_connection()
    print("   Connected")

    print("\n2. Exporting v2_ enriched provisions...")
    data = export_v2_data(local_conn)
    local_conn.close()

    if not data:
        print("   No enriched provisions found. Nothing to sync.")
        sys.exit(0)

    # Import to Supabase
    print("\n3. Connecting to SUPABASE database...")
    supa_conn = get_supabase_connection()
    print("   Connected")

    print("\n4. Syncing to Supabase...")
    updated, errors = sync_to_supabase(supa_conn, data)
    supa_conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("SYNC COMPLETE")
    print(f"  Updated: {updated} provisions")
    print(f"  Errors: {errors}")
    print(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # Suggest verification
    print("\nVerify sync by running:")
    print("  python scripts/compare_local_supabase.py")

if __name__ == "__main__":
    main()
