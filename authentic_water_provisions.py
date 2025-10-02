import psycopg2
from psycopg2.extras import RealDictCursor

def show_authentic_provisions():
    conn = psycopg2.connect(
        host='localhost',
        database='nsw_planning',
        user='postgres',
        password='postgres',
        port='5432'
    )

    cursor = conn.cursor(cursor_factory=RealDictCursor)

    print('=== AUTHENTIC WATER-RELATED PROVISIONS FROM POSTGRESQL DATABASE ===')
    print()

    # Get the most detailed water-related provisions
    cursor.execute('''
        SELECT id, ref_number, provision_text, document_id, provision_type, zone, page_number, development_type
        FROM regulatory_provisions
        WHERE provision_text ILIKE '%water%'
        AND LENGTH(provision_text) > 100
        ORDER BY LENGTH(provision_text) DESC
        LIMIT 5
    ''')

    water_records = cursor.fetchall()

    for i, record in enumerate(water_records, 1):
        print(f'AUTHENTIC WATER PROVISION RECORD {i}')
        print('=' * 60)
        print(f'Database ID: {record["id"]}')
        print(f'Reference Number: {record["ref_number"]}')
        print(f'Document Source: {record["document_id"]}')
        print(f'Provision Type: {record["provision_type"]}')
        print(f'Zone: {record["zone"] or "Not specified"}')
        print(f'Page Number: {record["page_number"] or "Not specified"}')
        print(f'Development Type: {record["development_type"] or "Not specified"}')
        print(f'Text Length: {len(record["provision_text"])} characters')
        print()
        print('COMPLETE PROVISION TEXT:')
        print('-' * 40)
        print(record["provision_text"])
        print()
        print('=' * 80)
        print()

    # Also get some development controls related to water
    print('=== WATER-RELATED DEVELOPMENT CONTROLS ===')
    cursor.execute('''
        SELECT dc.id, dc.control_type, dc.control_subtype, dc.value_numeric, dc.value_text, dc.unit, dc.zone_applicable, dc.confidence_score,
               rp.provision_text, rp.document_id, rp.ref_number
        FROM development_controls dc
        JOIN regulatory_provisions rp ON CAST(dc.provision_id AS INTEGER) = rp.id
        WHERE rp.provision_text ILIKE '%water%'
        ORDER BY dc.confidence_score DESC
        LIMIT 3
    ''')

    try:
        controls = cursor.fetchall()
        for i, control in enumerate(controls, 1):
            print(f'WATER DEVELOPMENT CONTROL {i}:')
            print(f'  Control Type: {control["control_type"]}')
            print(f'  Subtype: {control["control_subtype"]}')
            print(f'  Numeric Value: {control["value_numeric"]} {control["unit"] or ""}')
            print(f'  Text Value: {control["value_text"]}')
            print(f'  Applicable Zone: {control["zone_applicable"]}')
            print(f'  Confidence Score: {control["confidence_score"]}')
            print(f'  Source Document: {control["document_id"]}')
            print(f'  Reference: {control["ref_number"]}')
            print(f'  Source Text: {control["provision_text"][:300]}...')
            print()
    except Exception as e:
        print(f'Note: Development controls query had an issue: {e}')

    # Get some sample environmental provisions
    print('=== SAMPLE ENVIRONMENTAL PROVISIONS ===')
    cursor.execute('''
        SELECT id, ref_number, provision_text, document_id, provision_type
        FROM regulatory_provisions
        WHERE provision_type ILIKE '%environmental%'
        OR provision_text ILIKE '%environment%'
        ORDER BY LENGTH(provision_text) DESC
        LIMIT 2
    ''')

    env_records = cursor.fetchall()
    for record in env_records:
        print(f'Environmental Provision ID {record["id"]}:')
        print(f'  Reference: {record["ref_number"]}')
        print(f'  Document: {record["document_id"]}')
        print(f'  Type: {record["provision_type"]}')
        print(f'  Text: {record["provision_text"][:400]}...')
        print()

    conn.close()
    print('=== END OF AUTHENTIC PROVISIONS ===')

if __name__ == "__main__":
    show_authentic_provisions()