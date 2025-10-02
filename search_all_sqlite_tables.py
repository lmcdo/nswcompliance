import sqlite3

conn = sqlite3.connect('nsw_planning.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print('=== SEARCHING ALL SQLITE TABLES FOR COMPLETE CLAUSE 2.2 ===')
print()

# Get all table names
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [row[0] for row in cursor.fetchall()]

print(f'Searching {len(tables)} tables...')
print()

for table in tables:
    try:
        # Get columns that might contain text
        cursor.execute(f"PRAGMA table_info({table})")
        columns = cursor.fetchall()
        text_columns = [col[1] for col in columns if 'text' in col[1].lower() or 'content' in col[1].lower() or 'provision' in col[1].lower()]

        if text_columns:
            print(f'Table: {table}')
            print(f'  Text columns: {text_columns}')

            for col in text_columns:
                # Search for the specific clause content
                cursor.execute(f'''
                    SELECT rowid, {col}, LENGTH({col}) as text_length
                    FROM {table}
                    WHERE {col} LIKE '%competing provision%'
                    AND {col} LIKE '%mains-supplied potable water%'
                    ORDER BY text_length DESC
                    LIMIT 3
                ''')
                results = cursor.fetchall()

                if results:
                    print(f'  Found {len(results)} matches in {col}:')
                    for result in results:
                        print(f'    Row {result[0]}: {result["text_length"]} chars')
                        if result["text_length"] > 500:
                            print('    COMPLETE TEXT FOUND:')
                            print('    ' + '='*70)
                            print('    ' + result[col])
                            print('    ' + '='*70)
                            break  # Found it!
                        else:
                            print(f'    Text: {result[col][:100]}...')
                    print()
            print()

    except Exception as e:
        print(f'  Error checking {table}: {e}')

# Also search for any provision with longer text that might be the complete version
print('\n=== SEARCHING FOR LONGER PROVISIONS WITH SIMILAR CONTENT ===')
cursor.execute('''
    SELECT id, document_id, ref_number, provision_text, LENGTH(provision_text) as text_length
    FROM regulatory_provisions
    WHERE provision_text LIKE '%competing provision%'
    AND LENGTH(provision_text) > 500
    ORDER BY text_length DESC
    LIMIT 5
''')
longer_provisions = cursor.fetchall()

print(f'Found {len(longer_provisions)} longer provisions with similar content:')
for prov in longer_provisions:
    print(f'  ID {prov["id"]}: Doc {prov["document_id"]}')
    print(f'  Ref: {prov["ref_number"]} ({prov["text_length"]} chars)')
    print('  COMPLETE TEXT:')
    print('  ' + '='*70)
    print('  ' + prov["provision_text"])
    print('  ' + '='*70)
    print()

cursor.close()
conn.close()