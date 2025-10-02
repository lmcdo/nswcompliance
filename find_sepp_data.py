import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

# Look for SEPP references in documents table
cursor.execute('SELECT * FROM documents WHERE filename LIKE "%SEPP%" LIMIT 5')
sepp_docs = cursor.fetchall()
print('SEPP documents:')
for doc in sepp_docs:
    print(f'  ID: {doc[0]}, Filename: {doc[1]}')

# Look for SEPP references in provision text
cursor.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE provision_text LIKE "%SEPP%" OR ref_number LIKE "%SEPP%"')
sepp_count = cursor.fetchone()[0]
print(f'\nSEPP provisions: {sepp_count}')

if sepp_count > 0:
    cursor.execute('SELECT ref_number, provision_text FROM regulatory_provisions WHERE provision_text LIKE "%SEPP%" OR ref_number LIKE "%SEPP%" LIMIT 5')
    samples = cursor.fetchall()
    print('\nSample SEPP provisions:')
    for s in samples:
        text = s[1][:150] + '...' if s[1] and len(s[1]) > 150 else s[1]
        print(f'  {s[0]}: {text}')

# Check sepp_lep_overrides table
cursor.execute('SELECT COUNT(*) FROM sepp_lep_overrides')
override_count = cursor.fetchone()[0]
print(f'\nSEPP-LEP overrides: {override_count}')

if override_count > 0:
    cursor.execute('SELECT * FROM sepp_lep_overrides LIMIT 5')
    overrides = cursor.fetchall()
    print('Sample SEPP overrides:')
    for override in overrides:
        print(f'  {override}')

conn.close()