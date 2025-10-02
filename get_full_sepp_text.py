import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host='localhost', database='nsw_planning_corrected', user='postgres', password='postgres', port='5432')
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Get the complete legal text from provision 6080
cursor.execute('SELECT * FROM regulatory_provisions WHERE id = %s', (6080,))
provision = cursor.fetchone()

if provision:
    print('=== COMPLETE SEPP PROVISION 6080 ===')
    print(f'Document: {provision["document_id"]}')
    print(f'Reference: {provision["ref_number"]}')
    print(f'Page: {provision["page_number"]}')
    print()
    print('COMPLETE LEGAL TEXT:')
    print('=' * 80)
    print(provision["provision_text"])
    print('=' * 80)
    print()

    # Get instrument details
    if provision["instrument_id"]:
        cursor.execute('SELECT * FROM legal_instruments WHERE id = %s', (provision["instrument_id"],))
        instrument = cursor.fetchone()
        if instrument:
            print('LEGAL INSTRUMENT DETAILS:')
            print(f'  Code: {instrument["instrument_code"]}')
            print(f'  Type: {instrument["instrument_type"]}')
            print(f'  Title: {instrument["title"]}')
            print(f'  Legal Precedence: {instrument["legal_precedence"]}')
            print(f'  Status: {instrument["status"]}')

else:
    print('Provision 6080 not found')

cursor.close()
conn.close()