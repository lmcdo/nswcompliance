#!/usr/bin/env python3
from db_config import get_connection  # Unified PostgreSQL connection
import psycopg2

# Check SQLite development permissions
print("=== SQLite Development Permissions ===")
sqlite_conn = get_connection()
sqlite_cursor = sqlite_conn.cursor()

sqlite_cursor.execute('SELECT COUNT(*) FROM development_permissions')
sqlite_count = sqlite_cursor.fetchone()[0]
print(f"SQLite development_permissions: {sqlite_count:,} records")

# Get sample data
sqlite_cursor.execute('SELECT zone, development_type, permission_status FROM development_permissions LIMIT 5')
sample_data = sqlite_cursor.fetchall()
print("Sample SQLite data:")
for zone, dev_type, status in sample_data:
    print(f"  {zone}: {dev_type} = {status}")

sqlite_conn.close()

# Check PostgreSQL
print("\n=== PostgreSQL Status ===")
pg_conn = psycopg2.connect(
    host='localhost',
    port=5432,
    database='nsw_planning',
    user='postgres',
    password='postgres'
)
pg_cursor = pg_conn.cursor()

try:
    pg_cursor.execute('SELECT COUNT(*) FROM development_permissions')
    pg_count = pg_cursor.fetchone()[0]
    print(f"PostgreSQL development_permissions: {pg_count:,} records")
except Exception as e:
    print(f"PostgreSQL development_permissions table doesn't exist: {e}")

pg_cursor.execute('SELECT COUNT(*) FROM regulatory_provisions')
provisions_count = pg_cursor.fetchone()[0]
print(f"PostgreSQL regulatory_provisions: {provisions_count:,} records")

pg_conn.close()