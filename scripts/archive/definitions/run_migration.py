#!/usr/bin/env python3
"""Run the regulatory_definitions migration on Supabase."""

import os
import psycopg2
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

PROJECT_ROOT = Path(__file__).parent.parent.parent

# Use DATABASE_URL (Supabase) if available, otherwise local
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    DB_CONFIG = {
        'dbname': 'nsw_planning',
        'user': 'postgres',
        'password': 'Sturt1802!',
        'host': 'localhost'
    }
else:
    DB_CONFIG = None


def get_db_connection():
    """Get database connection."""
    if DATABASE_URL:
        print(f"  Connecting to Supabase...")
        return psycopg2.connect(DATABASE_URL)
    else:
        print(f"  Connecting to local database...")
        return psycopg2.connect(**DB_CONFIG)


def main():
    print("Running migration: create_regulatory_definitions.sql")

    migration_path = PROJECT_ROOT / "migrations" / "create_regulatory_definitions.sql"
    migration_sql = migration_path.read_text(encoding='utf-8')

    conn = get_db_connection()
    cur = conn.cursor()

    try:
        cur.execute(migration_sql)
        conn.commit()
        print("[OK] Migration completed successfully")

        # Verify table exists
        cur.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_name = 'regulatory_definitions'
            );
        """)
        exists = cur.fetchone()[0]
        print(f"Table exists: {exists}")

        # Count rows
        if exists:
            cur.execute("SELECT COUNT(*) FROM regulatory_definitions;")
            count = cur.fetchone()[0]
            print(f"Current row count: {count}")

    except Exception as e:
        print(f"[ERROR] Migration failed: {e}")
        conn.rollback()

    finally:
        cur.close()
        conn.close()


if __name__ == "__main__":
    main()
