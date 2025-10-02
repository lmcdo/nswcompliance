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
        print('✓ documents table exists in PostgreSQL')

        # Check record count
        pg_cursor.execute('SELECT COUNT(*) as count FROM documents')
        pg_count = pg_cursor.fetchone()['count']
        print(f'  PostgreSQL records: {pg_count}')

        # Check if our specific document is there
        pg_cursor.execute("""
            SELECT id, document_name, LENGTH(full_text) as text_length
            FROM documents
            WHERE full_text LIKE '%competing provision%'
            AND full_text LIKE '%mains-supplied potable water%'
        """)
        pg_sepp_doc = pg_cursor.fetchone()

        if pg_sepp_doc:
            print(f'  ✓ SEPP document found: ID {pg_sepp_doc["id"]}, {pg_sepp_doc["text_length"]} chars')
        else:
            print('  ✗ SEPP document NOT found in PostgreSQL')

    else:
        print('✗ documents table does NOT exist in PostgreSQL')

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

    # Check our specific document
    sqlite_cursor.execute("""
        SELECT rowid, document_name, LENGTH(full_text) as text_length
        FROM documents
        WHERE full_text LIKE '%competing provision%'
        AND full_text LIKE '%mains-supplied potable water%'
    """)
    sqlite_sepp_doc = sqlite_cursor.fetchone()

    if sqlite_sepp_doc:
        print(f'  ✓ SEPP document in SQLite: ID {sqlite_sepp_doc["rowid"]}, {sqlite_sepp_doc["text_length"]} chars')
    else:
        print('  ✗ SEPP document NOT found in SQLite')

    sqlite_cursor.close()
    sqlite_conn.close()

except Exception as e:
    print(f'SQLite error: {e}')

print()
print('CONCLUSION:')
if not pg_table_exists:
    print('The documents table was NOT migrated to PostgreSQL!')
    print('This means the complete SEPP text is missing from the corrected database.')
else:
    print('Need to check why the SEPP document data is missing.')