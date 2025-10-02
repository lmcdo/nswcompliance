import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host='localhost', database='nsw_planning_corrected', user='postgres', password='postgres', port='5432')
cursor = conn.cursor(cursor_factory=RealDictCursor)

# Test the specific provision we found before (ID 6080)
cursor.execute('SELECT * FROM regulatory_provisions WHERE id = %s', (6080,))
provision = cursor.fetchone()

if provision:
    print(f'Provision 6080 found:')
    print(f'  Document ID: {provision["document_id"]}')
    print(f'  Ref Number: {provision["ref_number"]}')
    print(f'  Text: {provision["provision_text"][:200]}...')
    print()

    # Check if it has an instrument_id now
    if provision["instrument_id"]:
        cursor.execute('SELECT * FROM legal_instruments WHERE id = %s', (provision["instrument_id"],))
        instrument = cursor.fetchone()
        if instrument:
            print(f'  Linked to: {instrument["instrument_code"]} ({instrument["instrument_type"]})')
            print(f'  Legal Precedence: {instrument["legal_precedence"]}')

    # Test relationships without CAST
    cursor.execute('SELECT COUNT(*) as count FROM development_controls WHERE provision_id = %s', (6080,))
    dc_count = cursor.fetchone()['count']
    print(f'  Development Controls: {dc_count} (no CAST needed!)')

    cursor.execute('SELECT COUNT(*) as count FROM sepp_lep_overrides WHERE sepp_provision_id = %s', (6080,))
    override_count = cursor.fetchone()['count']
    print(f'  SEPP Overrides: {override_count}')
else:
    print('Provision 6080 not found')

cursor.close()
conn.close()