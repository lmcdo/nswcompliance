#!/usr/bin/env python3
"""Check current database status - SQLite vs PostgreSQL"""

from db_config import get_connection  # Unified PostgreSQL connection
import psycopg2
from datetime import datetime

print(f'=== DATABASE COMPARISON AT {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} ===')
print()

# SQLite connection
sqlite_conn = get_connection()
sqlite_cursor = sqlite_conn.cursor()

# PostgreSQL connection  
pg_conn = psycopg2.connect(
    host='localhost',
    database='nsw_planning',
    user='postgres',
    password='postgres'
)
pg_cursor = pg_conn.cursor()

# Get SQLite stats
sqlite_cursor.execute('SELECT name FROM sqlite_master WHERE type="table" AND name NOT LIKE "sqlite_%" ORDER BY name')
sqlite_data = {}
for row in sqlite_cursor.fetchall():
    table = row[0]
    sqlite_cursor.execute(f'SELECT COUNT(*) FROM {table}')
    sqlite_data[table] = sqlite_cursor.fetchone()[0]

# Get PostgreSQL stats
pg_cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
pg_data = {}
for row in pg_cursor.fetchall():
    table = row[0]
    pg_cursor.execute(f'SELECT COUNT(*) FROM {table}')
    pg_data[table] = pg_cursor.fetchone()[0]

print('SQLITE:')
sqlite_total = sum(sqlite_data.values())
print(f'  Tables: {len(sqlite_data)}')
print(f'  Records: {sqlite_total:,}')

print()
print('POSTGRESQL:')
pg_total = sum(pg_data.values())
print(f'  Tables: {len(pg_data)}')
print(f'  Records: {pg_total:,}')

print()
print('DIFFERENCE:')
print(f'  PostgreSQL has {pg_total - sqlite_total:,} more records')
print(f'  PostgreSQL has {pg_total/sqlite_total*100:.1f}% of SQLite count')

# Show tables with different counts
print()
print('TABLES WITH DIFFERENT COUNTS:')
all_tables = set(sqlite_data.keys()) | set(pg_data.keys())
diff_count = 0
for table in sorted(all_tables):
    sq = sqlite_data.get(table, 0)
    pg = pg_data.get(table, 0)
    if sq != pg:
        diff = pg - sq
        diff_count += 1
        status = "MISSING" if pg == 0 else ("DUPLICATE" if pg > sq else "PARTIAL")
        print(f'  {table}: SQLite={sq:,} | PG={pg:,} | Diff={diff:+,} [{status}]')

print()
print(f'Total tables with differences: {diff_count}')

sqlite_conn.close()
pg_conn.close()