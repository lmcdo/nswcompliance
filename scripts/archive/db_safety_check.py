#!/usr/bin/env python3
"""
Database Safety Check - MANDATORY before any database operations
Adapted for Supabase environment
"""

import psycopg2
import os
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

def check_database_health():
    """Run database safety checks before operations"""

    print("DATABASE SAFETY CHECK - MANDATORY")
    print("=" * 50)

    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        print("[FAIL] DATABASE_URL not set - ABORTING")
        sys.exit(1)

    try:
        # 1. Check PostgreSQL health
        print("1. Checking PostgreSQL health...")
        conn = psycopg2.connect(db_url, connect_timeout=10)
        cur = conn.cursor()
        cur.execute("SELECT 1")
        if cur.fetchone()[0] == 1:
            print("   [OK] PostgreSQL responsive")
        else:
            print("   [FAIL] PostgreSQL not responsive - ABORTING")
            sys.exit(1)

        # 2. Check for active connections
        print("2. Checking database connections...")
        cur.execute("""
            SELECT COUNT(*) FROM pg_stat_activity
            WHERE state = 'active' AND pid != pg_backend_pid()
        """)
        active_connections = cur.fetchone()[0]
        if active_connections > 50:
            print(f"   [WARN]  Many active connections ({active_connections}) - proceed with caution")
        else:
            print(f"   [OK] Connection count OK ({active_connections})")

        # 3. Check for database locks
        print("3. Checking for database locks...")
        cur.execute("SELECT COUNT(*) FROM pg_locks WHERE NOT granted")
        locks = cur.fetchone()[0]
        if locks > 0:
            print(f"   [FAIL] Database locks detected ({locks}) - ABORTING")
            sys.exit(1)
        else:
            print("   [OK] No locks detected")

        # 4. Check table sizes (warn if very large)
        print("4. Checking table sizes...")
        cur.execute("""
            SELECT
                schemaname,
                tablename,
                pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
                pg_total_relation_size(schemaname||'.'||tablename) AS size_bytes
            FROM pg_tables
            WHERE schemaname = 'public'
            ORDER BY size_bytes DESC
            LIMIT 1
        """)
        result = cur.fetchone()
        if result:
            table_name, size = result[1], result[2]
            print(f"   [OK] Largest table: {table_name} ({size})")

        # 5. Verify backup directory exists
        print("5. Checking backup infrastructure...")
        backup_dir = Path("backups")
        backup_dir.mkdir(exist_ok=True)
        if backup_dir.exists():
            print("   [OK] Backup directory ready")
        else:
            print("   [FAIL] Cannot create backup directory - ABORTING")
            sys.exit(1)

        # 6. Check if we can write a test record
        print("6. Verifying write permissions...")
        try:
            cur.execute("BEGIN")
            cur.execute("""
                CREATE TEMP TABLE test_write_permissions (id INTEGER)
                ON COMMIT DROP
            """)
            cur.execute("INSERT INTO test_write_permissions VALUES (1)")
            cur.execute("ROLLBACK")
            print("   [OK] Write permissions OK")
        except Exception as e:
            print(f"   [FAIL] Write permission test failed: {e}")
            sys.exit(1)

        cur.close()
        conn.close()

        print()
        print("DATABASE SAFETY CHECK PASSED")
        print("You may proceed with database operations")
        print("REMEMBER: Use timeouts for all operations")
        print("=" * 50)

    except psycopg2.OperationalError as e:
        print(f"[FAIL] Database connection failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"[FAIL] Safety check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    check_database_health()
