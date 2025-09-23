#!/usr/bin/env python3
"""
Restore the PostgreSQL backup to populate all the data
"""

import psycopg2
import sys

print("Restoring 40MB backup to nsw_planning database...")
print("This will populate all the authoritative schema tables with data.")

# Read the backup file
backup_file = 'nsw_planning_backup_20250908_163513.sql'
print(f"\nReading backup file: {backup_file}")

with open(backup_file, 'r', encoding='utf-8') as f:
    sql_content = f.read()

print(f"Backup file size: {len(sql_content):,} bytes")

# Connect to database
conn = psycopg2.connect(
    host='127.0.0.1',
    database='nsw_planning',
    user='postgres',
    port=5432
)
conn.autocommit = True  # Important for restoring backups

cursor = conn.cursor()

try:
    # Split by statements (this is a simple approach, may need refinement)
    statements = sql_content.split(';\n')
    total = len(statements)

    print(f"\nExecuting {total} SQL statements...")

    for i, statement in enumerate(statements):
        if statement.strip():
            try:
                cursor.execute(statement)
                if (i + 1) % 1000 == 0:
                    print(f"  Progress: {i+1}/{total} statements...")
            except psycopg2.Error as e:
                # Skip errors for duplicate constraints, etc
                if "already exists" not in str(e):
                    print(f"  Warning on statement {i+1}: {str(e)[:100]}")
                continue

    print("\nBackup restored successfully!")

    # Check what we have now
    print("\nVerifying restored data:")
    cursor.execute("""
        SELECT schemaname, tablename, n_live_tup as row_count
        FROM pg_stat_user_tables
        WHERE schemaname IN ('public', 'authoritative', 'versions')
        ORDER BY schemaname, tablename
    """)

    tables = cursor.fetchall()
    for schema, table, count in tables:
        if count > 0:
            print(f"  {schema}.{table}: {count:,} rows")

except Exception as e:
    print(f"Error during restore: {e}")
    sys.exit(1)
finally:
    conn.close()

print("\n✓ Database restore complete!")