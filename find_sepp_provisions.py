import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres', port='5432')
cursor = conn.cursor(cursor_factory=RealDictCursor)

print('SEARCHING FOR ALL SEPP DOCUMENTS IN DATABASE...')
cursor.execute("SELECT DISTINCT document_id FROM regulatory_provisions WHERE document_id ILIKE '%SEPP%' ORDER BY document_id")
sepp_docs = cursor.fetchall()

print('SEPP Documents found:')
for doc in sepp_docs:
    print(f'  - {doc["document_id"]}')

print('\nSEARCHING FOR LONGEST SEPP PROVISIONS (MOST DETAILED)...')
cursor.execute('''
SELECT id, ref_number, provision_text, document_id, provision_type
FROM regulatory_provisions
WHERE document_id ILIKE '%SEPP%'
ORDER BY LENGTH(provision_text) DESC
LIMIT 3
''')

records = cursor.fetchall()
for i, record in enumerate(records, 1):
    print(f'\n=== DETAILED SEPP PROVISION {i} ===')
    print(f'ID: {record["id"]}')
    print(f'Reference: {record["ref_number"]}')
    print(f'Document: {record["document_id"]}')
    print(f'Type: {record["provision_type"]}')
    print(f'Text Length: {len(record["provision_text"])} characters')
    print(f'\n--- COMPLETE PROVISION TEXT ---')
    print(record['provision_text'])
    print('=' * 100)

conn.close()