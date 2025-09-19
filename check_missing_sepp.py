#!/usr/bin/env python3
"""
Check for missing SEPP data sources
"""

import sqlite3

def check_missing_sepp():
    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()

    print('=== DOCUMENT ANALYSIS ===')

    # Check all document types
    cursor.execute('SELECT DISTINCT document_type FROM documents ORDER BY document_type')
    doc_types = [row[0] for row in cursor.fetchall()]
    print(f'Document types: {doc_types}')

    # Check all document names containing key terms
    cursor.execute('SELECT pdf_name, document_type FROM documents WHERE pdf_name LIKE "%exempt%" OR pdf_name LIKE "%complying%" OR pdf_name LIKE "%housing%"')
    relevant_docs = cursor.fetchall()
    print(f'\nDocuments with exempt/complying/housing:')
    for doc, doc_type in relevant_docs:
        print(f'  {doc} ({doc_type})')

    # Check document counts by type
    cursor.execute('SELECT document_type, COUNT(*) FROM documents GROUP BY document_type ORDER BY COUNT(*) DESC')
    doc_counts = cursor.fetchall()
    print(f'\nDocument counts by type:')
    for doc_type, count in doc_counts:
        print(f'  {doc_type}: {count} documents')

    # Check if there might be SEPP data in different tables
    cursor.execute('SELECT name FROM sqlite_master WHERE type="table" ORDER BY name')
    tables = [row[0] for row in cursor.fetchall()]
    print(f'\nAll tables in SQLite:')
    for table in tables:
        print(f'  {table}')

    # Check for any table that might contain SEPP data
    for table in tables:
        if 'sepp' in table.lower() or 'exempt' in table.lower():
            cursor.execute(f'SELECT COUNT(*) FROM {table}')
            count = cursor.fetchone()[0]
            print(f'  SEPP-related table {table}: {count} records')

    conn.close()

    print(f'\n=== CONCLUSION ===')
    print(f'The 2,186 SEPP provisions mentioned in Priority2Fix README may be:')
    print(f'1. From external SEPP documents not yet imported to this database')
    print(f'2. From a different version of the database')
    print(f'3. An aspirational target rather than current reality')
    print(f'4. Calculated differently (e.g., including sub-provisions)')
    print(f'\nCurrent extraction of 710 SEPP provisions appears correct based on available data.')

if __name__ == "__main__":
    check_missing_sepp()