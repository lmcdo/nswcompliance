import sqlite3

conn = sqlite3.connect('nsw_planning.db')
cursor = conn.cursor()

print('=== SEPP/LEP COVERAGE IN DATABASE ===\n')

# Check documents table for SEPP content
cursor.execute('SELECT COUNT(DISTINCT document_id) FROM regulatory_provisions WHERE LOWER(document_id) LIKE "%sepp%"')
sepp_docs = cursor.fetchone()[0]
print(f'SEPP documents in regulatory_provisions: {sepp_docs}')

# Sample some SEPP documents
cursor.execute('SELECT DISTINCT document_id FROM regulatory_provisions WHERE LOWER(document_id) LIKE "%sepp%" LIMIT 5')
samples = cursor.fetchall()
if samples:
    print('\nSample SEPP documents:')
    for s in samples:
        doc_name = s[0]
        if len(doc_name) > 100:
            print(f'  - {doc_name[:100]}...')
        else:
            print(f'  - {doc_name}')

# Check for specific SEPPs that were claimed missing
print('\n=== CHECKING "MISSING" SEPPs ===')
missing_sepps = {
    'SEPP (Exempt and Complying)': 'exempt',
    'SEPP (Housing) 2021': 'housing',
    'SEPP 65 Design Quality': '65',
    'SEPP Transport': 'transport'
}

for sepp_name, search_term in missing_sepps.items():
    cursor.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE LOWER(document_id) LIKE ?', (f'%{search_term}%',))
    count = cursor.fetchone()[0]
    status = 'FOUND' if count > 0 else 'NOT FOUND'
    print(f'{sepp_name}: {count} provisions - {status}')

# Check for Inner West LEP
print('\n=== LEP COVERAGE ===')
cursor.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE LOWER(document_id) LIKE "%inner%west%"')
inner_west = cursor.fetchone()[0]
print(f'Inner West LEP provisions: {inner_west}')

cursor.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE LOWER(document_id) LIKE "%lep%"')
any_lep = cursor.fetchone()[0]
print(f'Any LEP provisions: {any_lep}')

# Check documents table for more detail
print('\n=== DOCUMENTS TABLE ===')
cursor.execute('SELECT COUNT(*) FROM documents')
total_docs = cursor.fetchone()[0]
print(f'Total documents: {total_docs}')

cursor.execute('SELECT pdf_name FROM documents WHERE LOWER(pdf_name) LIKE "%sepp%" LIMIT 5')
sepp_pdfs = cursor.fetchall()
if sepp_pdfs:
    print('\nSEPP PDFs found in documents:')
    for pdf in sepp_pdfs:
        print(f'  - {pdf[0]}')
else:
    print('\nNo SEPP PDFs found in documents table')

# Check what documents we actually have
print('\n=== SAMPLE OF ALL DOCUMENTS ===')
cursor.execute('SELECT pdf_name FROM documents LIMIT 10')
sample_docs = cursor.fetchall()
for doc in sample_docs:
    print(f'  - {doc[0]}')

conn.close()