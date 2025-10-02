import psycopg2
from psycopg2.extras import RealDictCursor
import sqlite3

print('=== CHECKING DOCUMENTS TABLE MIGRATION ===')
print()

# Check PostgreSQL corrected database
try:
    pg_conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning_corrected',
        user='postgres',
        password='postgres',
        port='5432'
    )
    pg_cursor = pg_conn.cursor(cursor_factory=RealDictCursor)

    # Check if documents table exists in PostgreSQL
    pg_cursor.execute("""
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name = 'documents'
    """)
    pg_table_exists = pg_cursor.fetchone()

    if pg_table_exists:
        print('documents table EXISTS in PostgreSQL')

        # Check record count
        pg_cursor.execute('SELECT COUNT(*) as count FROM documents')
        pg_count = pg_cursor.fetchone()['count']
        print(f'PostgreSQL records: {pg_count}')

        # Check columns
        pg_cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'documents'
        """)
        pg_columns = [row['column_name'] for row in pg_cursor.fetchall()]
        print(f'PostgreSQL columns: {pg_columns}')

    else:
        print('documents table does NOT exist in PostgreSQL')

    pg_cursor.close()
    pg_conn.close()

except Exception as e:
    print(f'PostgreSQL error: {e}')

print()

# Check SQLite original
try:
    sqlite_conn = sqlite3.connect('nsw_planning.db')
    sqlite_conn.row_factory = sqlite3.Row
    sqlite_cursor = sqlite_conn.cursor()

    # Check record count in SQLite
    sqlite_cursor.execute('SELECT COUNT(*) as count FROM documents')
    sqlite_count = sqlite_cursor.fetchone()['count']
    print(f'SQLite documents records: {sqlite_count}')

    # Check columns in SQLite
    sqlite_cursor.execute('PRAGMA table_info(documents)')
    sqlite_columns = [row[1] for row in sqlite_cursor.fetchall()]
    print(f'SQLite columns: {sqlite_columns}')

    sqlite_cursor.close()
    sqlite_conn.close()

except Exception as e:
    print(f'SQLite error: {e}')

print()
print('MIGRATION STATUS:')
if not pg_table_exists:
    print('FAILED: documents table was NOT migrated!')
else:
    print('SUCCESS: documents table was migrated')