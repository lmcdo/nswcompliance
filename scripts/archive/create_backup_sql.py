"""
Create Database Backup using Python pg library
Safer than pg_dump for our purposes
"""

import psycopg2
import json
from datetime import datetime
import os

def create_backup():
    """Create logical backup of critical tables"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    backup_file = f"{backup_dir}/indexes_backup_{timestamp}.json"

    print("=" * 80)
    print("DATABASE BACKUP - Performance Optimization")
    print("=" * 80)
    print()
    print(f"Creating logical backup: {backup_file}")
    print()

    conn = psycopg2.connect(
        host="localhost",
        database="nsw_planning",
        user="postgres",
        password="postgres"
    )
    cursor = conn.cursor()

    backup_data = {
        "timestamp": timestamp,
        "database": "nsw_planning",
        "purpose": "Before adding performance indexes",
        "tables": {}
    }

    # Get current database size
    cursor.execute("SELECT pg_size_pretty(pg_database_size('nsw_planning'))")
    db_size = cursor.fetchone()[0]
    print(f"Current database size: {db_size}")
    print()

    # Backup existing indexes for tables we'll modify
    tables_to_backup = [
        'dcp_general_requirements',
        'dcp_general_provisions',
        'regulatory_provisions'
    ]

    print("Backing up existing index definitions...")
    print()

    for table in tables_to_backup:
        # Get table row count
        cursor.execute(f"SELECT COUNT(*) FROM {table}")
        row_count = cursor.fetchone()[0]

        # Get existing indexes
        cursor.execute(f"""
            SELECT
                indexname,
                indexdef
            FROM pg_indexes
            WHERE tablename = '{table}'
            AND schemaname = 'public'
            ORDER BY indexname
        """)

        indexes = cursor.fetchall()

        backup_data["tables"][table] = {
            "row_count": row_count,
            "indexes": [
                {"name": idx[0], "definition": idx[1]}
                for idx in indexes
            ]
        }

        print(f"  {table}:")
        print(f"    Rows: {row_count:,}")
        print(f"    Existing indexes: {len(indexes)}")

    print()

    # Save backup
    with open(backup_file, 'w') as f:
        json.dump(backup_data, f, indent=2)

    backup_size = os.path.getsize(backup_file) / 1024  # KB
    print("=" * 80)
    print("BACKUP SUCCESSFUL (Index Definitions)")
    print("=" * 80)
    print(f"File: {backup_file}")
    print(f"Size: {backup_size:.2f} KB")
    print()
    print("This backup contains:")
    print("  - Current index definitions for 3 critical tables")
    print("  - Row counts for verification")
    print("  - Rollback information")
    print()
    print("Note: This is a logical backup of index definitions only.")
    print("      Data is NOT backed up (not needed for index changes).")
    print()
    print("Next step: Run index creation script")
    print()

    cursor.close()
    conn.close()

    return True

if __name__ == "__main__":
    success = create_backup()
    exit(0 if success else 1)
