import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

# Check table structure
cursor.execute('PRAGMA table_info(regulatory_provisions)')
columns = cursor.fetchall()
print('Columns in regulatory_provisions:')
for col in columns:
    print(f'  {col[1]} ({col[2]})')

# Look for SEPP references
cursor.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE clause_reference LIKE "%SEPP%" OR document_title LIKE "%SEPP%"')
sepp_count = cursor.fetchone()[0]
print(f'\nSEPP provisions: {sepp_count}')

if sepp_count > 0:
    cursor.execute('SELECT clause_reference, clause_text FROM regulatory_provisions WHERE clause_reference LIKE "%SEPP%" OR document_title LIKE "%SEPP%" LIMIT 3')
    samples = cursor.fetchall()
    print('\nSample SEPP provisions:')
    for s in samples:
        text = s[1][:100] + '...' if s[1] and len(s[1]) > 100 else s[1]
        print(f'  {s[0]}: {text}')

# Check what document types exist
cursor.execute('SELECT DISTINCT document_title FROM regulatory_provisions LIMIT 10')
docs = cursor.fetchall()
print('\nSample document titles:')
for doc in docs:
    print(f'  {doc[0]}')

conn.close()