import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host='localhost', database='nsw_planning_corrected', user='postgres', password='postgres', port='5432')
cursor = conn.cursor(cursor_factory=RealDictCursor)

print('=== SEARCHING FOR COMPLETE CLAUSE 2.2 TEXT ===')
print()

# Check all tables that might contain the full text
tables_to_check = [
    'regulatory_provisions',
    'regulatory_provisions_clean',
    'contextual_guidance_real',
    'visual_elements',
    'visual_elements_real'
]

for table in tables_to_check:
    try:
        print(f'Checking table: {table}')

        # Check if table has provision_text or similar column
        cursor.execute(f'''
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{table}'
            AND column_name ILIKE '%text%'
        ''')
        text_columns = [row['column_name'] for row in cursor.fetchall()]

        if text_columns:
            print(f'  Text columns found: {text_columns}')

            for col in text_columns:
                # Search for the clause 2.2 content
                cursor.execute(f'''
                    SELECT id, {col}, LENGTH({col}) as text_length
                    FROM {table}
                    WHERE {col} ILIKE '%competing provision%'
                    AND {col} ILIKE '%mains-supplied potable water%'
                    ORDER BY text_length DESC
                    LIMIT 3
                ''')
                results = cursor.fetchall()

                if results:
                    print(f'  Found {len(results)} matches in {col}:')
                    for result in results:
                        print(f'    ID {result["id"]}: {result["text_length"]} chars')
                        if result["text_length"] > 500:
                            print(f'    COMPLETE TEXT:')
                            print('    ' + '='*70)
                            print('    ' + result[col])
                            print('    ' + '='*70)
                        else:
                            print(f'    Text: {result[col][:150]}...')
                        print()
        else:
            print(f'  No text columns found')

    except Exception as e:
        print(f'  Error checking {table}: {e}')

    print()

# Also check if there are other documents with this clause
print('=== CHECKING OTHER DOCUMENTS FOR CLAUSE 2.2 ===')
cursor.execute('''
    SELECT document_id, ref_number, provision_text, LENGTH(provision_text) as text_length
    FROM regulatory_provisions
    WHERE ref_number = '2.2'
    AND provision_text ILIKE '%competing provision%'
    ORDER BY text_length DESC
''')
other_docs = cursor.fetchall()

print(f'Found {len(other_docs)} documents with clause 2.2:')
for doc in other_docs:
    print(f'  Doc: {doc["document_id"]}')
    print(f'  Length: {doc["text_length"]} chars')
    if doc["text_length"] > 500:
        print(f'  COMPLETE TEXT:')
        print('  ' + '='*70)
        print('  ' + doc["provision_text"])
        print('  ' + '='*70)
    else:
        print(f'  Text: {doc["provision_text"][:200]}...')
    print()

cursor.close()
conn.close()