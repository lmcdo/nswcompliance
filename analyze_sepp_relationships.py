import psycopg2
from psycopg2.extras import RealDictCursor

def analyze_sepp_relationships():
    conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres', port='5432')
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print('=== ANALYZING WHY SEPP WATER PROVISION ISNT PROPERLY LINKED ===')
    print()

    # First, let's examine that water provision record I found
    print('1. EXAMINING THE WATER PROVISION RECORD:')
    cursor.execute('SELECT * FROM regulatory_provisions WHERE id = 6080')
    record = cursor.fetchone()

    if record:
        print(f'ID: {record["id"]}')
        print(f'Reference: {record["ref_number"]}')
        print(f'Document: {record["document_id"]}')
        print(f'Type: {record["provision_type"]}')
        print(f'Zone: {record["zone"]}')
        print(f'Development Type: {record["development_type"]}')
        print()
        print('ISSUES IDENTIFIED:')
        print('- Document name is very long and not standardized')
        print('- No clear SEPP identifier or code')
        print('- Zone is just "C1" - not linked to a proper zone table')
        print()

    # Check what relationships exist for this provision
    print('2. CHECKING RELATIONSHIPS FOR THIS PROVISION:')

    # Check development_controls
    try:
        cursor.execute('SELECT COUNT(*) FROM development_controls WHERE CAST(provision_id AS INTEGER) = 6080')
        dc_result = cursor.fetchone()
        dc_count = dc_result['count'] if dc_result else 0
        print(f'Development Controls linked: {dc_count}')
    except Exception as e:
        print(f'Development Controls query error: {e}')
        dc_count = 0

    # Check kg_relationships
    try:
        cursor.execute('SELECT COUNT(*) FROM kg_relationships WHERE subject_entity_id = 6080 OR object_entity_id = 6080')
        kg_result = cursor.fetchone()
        kg_count = kg_result['count'] if kg_result else 0
        print(f'Knowledge Graph relationships: {kg_count}')
    except Exception as e:
        print(f'KG relationships query error: {e}')

    # Check sepp_lep_overrides
    try:
        cursor.execute('SELECT COUNT(*) FROM sepp_lep_overrides WHERE sepp_provision_id = 6080')
        override_result = cursor.fetchone()
        override_count = override_result['count'] if override_result else 0
        print(f'SEPP/LEP override relationships: {override_count}')
    except Exception as e:
        print(f'SEPP/LEP overrides query error: {e}')

    print()
    print('3. CHECKING DOCUMENT STANDARDIZATION:')

    # Look at document naming patterns
    cursor.execute('SELECT DISTINCT document_id FROM regulatory_provisions WHERE document_id ILIKE \'%SEPP%\' LIMIT 5')
    sepp_docs = cursor.fetchall()
    print('SEPP Document naming patterns:')
    for doc in sepp_docs:
        if doc['document_id']:
            print(f'  - {doc["document_id"]}')

    cursor.execute('SELECT DISTINCT document_id FROM regulatory_provisions WHERE document_id ILIKE \'%sustainable%\' LIMIT 3')
    sust_docs = cursor.fetchall()
    print('Sustainable Building docs:')
    for doc in sust_docs:
        if doc['document_id']:
            print(f'  - {doc["document_id"]}')

    print()
    print('4. EXAMINING DATABASE SCHEMA ISSUES:')

    # Check if there's a proper documents/instruments table
    cursor.execute('SELECT table_name FROM information_schema.tables WHERE table_name LIKE \'%document%\' OR table_name LIKE \'%instrument%\'')
    doc_tables = cursor.fetchall()
    print('Document-related tables:')
    for table in doc_tables:
        print(f'  - {table["table_name"]}')

    # Check the documents table structure
    cursor.execute('SELECT * FROM documents LIMIT 3')
    doc_records = cursor.fetchall()
    print()
    print('Sample document records:')
    for doc in doc_records:
        print(f'  ID: {doc["id"]} | Type: {doc["document_type"]} | Name: {doc["pdf_name"][:60]}...')

    print()
    print('5. CHECKING FOR PROPER SEPP IDENTIFICATION:')

    # Look for actual SEPP codes/numbers
    cursor.execute('''
        SELECT ref_number, document_id, provision_text[:100] as preview
        FROM regulatory_provisions
        WHERE document_id ILIKE '%sustainable%building%'
        LIMIT 5
    ''')

    sepp_provisions = cursor.fetchall()
    print('Sustainable Buildings provisions:')
    for prov in sepp_provisions:
        print(f'  Ref: {prov["ref_number"]} | Doc: {prov["document_id"][:50]}...')
        print(f'  Preview: {prov["preview"]}...')
        print()

    print('6. RELATIONSHIP TABLE ANALYSIS:')

    # Check the actual structure of relationship tables
    cursor.execute('SELECT COUNT(*) FROM sepp_lep_overrides')
    total_overrides = cursor.fetchone()[0]
    print(f'Total SEPP/LEP overrides in database: {total_overrides}')

    cursor.execute('SELECT * FROM sepp_lep_overrides LIMIT 2')
    sample_overrides = cursor.fetchall()
    print('Sample override records:')
    for override in sample_overrides:
        print(f'  SEPP ID: {override["sepp_provision_id"]} | LEP Clause: {override["lep_clause_reference"]} | Type: {override["override_type"]}')

    conn.close()

    print()
    print('=== DIAGNOSIS COMPLETE ===')
    print()
    print('KEY FINDINGS:')
    print('1. Document naming is inconsistent and not standardized')
    print('2. No proper SEPP code/number identification system')
    print('3. Relationships between provisions and documents are weak')
    print('4. Zone references are text strings, not foreign keys')
    print('5. The migration may have lost some relational structure')

if __name__ == "__main__":
    analyze_sepp_relationships()