#!/usr/bin/env python3
import sqlite3
import os

# Find the database
db_paths = [
    'nsw_planning.db',
    'services/nsw_planning.db',
    'regulatory_database.db',
    'nsw_planning_data.db'
]

db_path = None
for path in db_paths:
    if os.path.exists(path):
        db_path = path
        break

if not db_path:
    print("Database not found!")
    exit(1)

print(f"Using database: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check for any tables that might contain SEPP data
cursor.execute('SELECT name FROM sqlite_master WHERE type="table"')
tables = cursor.fetchall()
print('Available tables:')
for table in tables:
    print(f'  {table[0]}')
    try:
        cursor.execute(f'SELECT COUNT(*) FROM {table[0]}')
        count = cursor.fetchone()[0]
        print(f'    Records: {count}')
    except Exception as e:
        print(f'    Error: {e}')

# Check if regulatory_provisions exists
if ('regulatory_provisions',) in tables:
    # Check for SEPP data in regulatory_provisions
    cursor.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE document_type LIKE "%SEPP%"')
    sepp_count = cursor.fetchone()[0]
    print(f'SEPP provisions: {sepp_count}')

    # Check total provisions
    cursor.execute('SELECT COUNT(*) FROM regulatory_provisions')
    total_count = cursor.fetchone()[0]
    print(f'Total provisions: {total_count}')

    # Check document types
    cursor.execute('SELECT DISTINCT document_type, COUNT(*) FROM regulatory_provisions GROUP BY document_type')
    doc_types = cursor.fetchall()
    print('Document types:')
    for doc_type, count in doc_types:
        print(f'  {doc_type}: {count}')

    # Sample a few provisions if SEPP exists
    if sepp_count > 0:
        cursor.execute('SELECT clause_number, clause_title, document_name FROM regulatory_provisions WHERE document_type LIKE "%SEPP%" LIMIT 5')
        samples = cursor.fetchall()
        print('Sample SEPP provisions:')
        for s in samples:
            print(f'  {s[0]}: {s[1]} ({s[2]})')
    else:
        # Sample any provisions to see what we have
        cursor.execute('SELECT clause_number, clause_title, document_name, document_type FROM regulatory_provisions LIMIT 5')
        samples = cursor.fetchall()
        print('Sample provisions (any type):')
        for s in samples:
            print(f'  {s[0]}: {s[1]} ({s[2]}) [{s[3]}]')
else:
    print('No regulatory_provisions table found')

conn.close()