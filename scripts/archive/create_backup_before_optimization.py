"""
Create Database Backup Before Performance Optimization
Safe execution with verification
"""

import subprocess
import os
from datetime import datetime
import psycopg2

def create_backup():
    """Create PostgreSQL backup before index changes"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"backups/nsw_planning_before_indexes_{timestamp}.backup"

    # Ensure backups directory exists
    os.makedirs("backups", exist_ok=True)

    print("=" * 80)
    print("DATABASE BACKUP - Performance Optimization")
    print("=" * 80)
    print()
    print(f"Creating backup: {backup_file}")
    print()

    # Check if PostgreSQL is accessible
    try:
        conn = psycopg2.connect(
            host="localhost",
            database="nsw_planning",
            user="postgres",
            password="postgres"
        )
        cursor = conn.cursor()

        # Get current database size
        cursor.execute("SELECT pg_size_pretty(pg_database_size('nsw_planning'))")
        db_size = cursor.fetchone()[0]
        print(f"Current database size: {db_size}")

        # Get table counts
        cursor.execute("""
            SELECT
                'dcp_general_requirements' as table_name,
                COUNT(*) as rows
            FROM dcp_general_requirements
            UNION ALL
            SELECT 'dcp_general_provisions', COUNT(*) FROM dcp_general_provisions
            UNION ALL
            SELECT 'regulatory_provisions', COUNT(*) FROM regulatory_provisions
            ORDER BY table_name
        """)

        print("\nCritical table row counts:")
        for table, rows in cursor.fetchall():
            print(f"  {table}: {rows:,} rows")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"⚠️  WARNING: Could not connect to database: {e}")
        print("   Continuing with backup anyway...")

    print()
    print("Creating backup with pg_dump...")
    print("(This may take 1-2 minutes for ~150MB database)")
    print()

    # Use pg_dump with custom format (compressed)
    cmd = [
        r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
        "-h", "localhost",
        "-U", "postgres",
        "-d", "nsw_planning",
        "-F", "c",  # Custom format (compressed)
        "-f", backup_file,
        "--verbose"
    ]

    try:
        # Set PGPASSWORD environment variable
        env = os.environ.copy()
        env['PGPASSWORD'] = 'postgres'

        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )

        # Check if backup file was created
        if os.path.exists(backup_file):
            file_size = os.path.getsize(backup_file) / (1024 * 1024)  # MB
            print()
            print("=" * 80)
            print("✓ BACKUP SUCCESSFUL")
            print("=" * 80)
            print(f"File: {backup_file}")
            print(f"Size: {file_size:.2f} MB")
            print()
            print("You can now safely run the index creation script.")
            print()
            print("To restore this backup if needed:")
            print(f'  pg_restore -h localhost -U postgres -d nsw_planning -c "{backup_file}"')
            print()
            return True
        else:
            print("❌ ERROR: Backup file was not created")
            return False

    except subprocess.CalledProcessError as e:
        print(f"❌ ERROR: pg_dump failed: {e}")
        print(f"STDERR: {e.stderr}")
        return False
    except FileNotFoundError:
        print("❌ ERROR: pg_dump not found at expected path")
        print("   Please update the path in this script or ensure PostgreSQL 16 is installed")
        return False

if __name__ == "__main__":
    success = create_backup()
    exit(0 if success else 1)
