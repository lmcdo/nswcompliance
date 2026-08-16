#!/usr/bin/env python3
"""
Run database migration from SQL file
"""

import psycopg2
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def run_migration(migration_file: str):
    """Execute SQL migration file"""

    migration_path = Path(migration_file)
    if not migration_path.exists():
        print(f"[FAIL] Migration file not found: {migration_file}")
        sys.exit(1)

    print(f"Running migration: {migration_path.name}")
    print("=" * 50)

    # Read SQL file
    with open(migration_path, 'r', encoding='utf-8') as f:
        sql = f.read()

    # Connect and execute
    conn = psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=30)
    conn.autocommit = False  # Use transaction
    cur = conn.cursor()

    try:
        print("Executing migration...")
        cur.execute(sql)
        conn.commit()

        print("\n[OK] Migration completed successfully!")

        # Verify tables were created
        print("\nVerifying migration...")
        cur.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_name IN ('provision_versions', 'provision_change_log')
            ORDER BY table_name
        """)
        tables = [row[0] for row in cur.fetchall()]
        print(f"   - Tables created: {', '.join(tables)}")

        # Verify columns were added
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'regulatory_provisions'
              AND column_name IN ('current_version_id', 'text_hash_current',
                                  'version_count', 'is_current', 'first_seen_date',
                                  'last_modified_date')
            ORDER BY column_name
        """)
        columns = [row[0] for row in cur.fetchall()]
        print(f"   - Columns added to regulatory_provisions: {len(columns)}")
        for col in columns:
            print(f"     - {col}")

        print("\n[OK] Migration verified!")

    except Exception as e:
        print(f"\n[FAIL] Migration failed: {e}")
        conn.rollback()
        sys.exit(1)
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        migration_file = sys.argv[1]
    else:
        migration_file = "scripts/migrations/create_version_schema.sql"

    run_migration(migration_file)
