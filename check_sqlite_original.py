import sqlite3

conn = sqlite3.connect('nsw_planning.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print('=== CHECKING ORIGINAL SQLITE FOR COMPLETE CLAUSE 2.2 TEXT ===')
print()

# Find provision 6080 in SQLite
cursor.execute('SELECT * FROM regulatory_provisions WHERE id = ?', (6080,))
provision = cursor.fetchone()

if provision:
    print('Provision 6080 in SQLite:')
    print(f'  Document: {provision["document_id"]}')
    print(f'  Ref: {provision["ref_number"]}')
    print(f'  Text length: {len(provision["provision_text"]) if provision["provision_text"] else 0} chars')
    print()
    print('COMPLETE SQLITE TEXT:')
    print('='*80)
    print(provision["provision_text"])
    print('='*80)
    print()

# Check if there are related provisions
cursor.execute('''
    SELECT id, ref_number, LENGTH(provision_text) as text_length, provision_text
    FROM regulatory_provisions
    WHERE document_id = 'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation'
    AND (ref_number LIKE '2.2%' OR provision_text LIKE '%competing provision%')
    ORDER BY id
''')
related = cursor.fetchall()

print(f'Related provisions in SQLite ({len(related)}):')
for prov in related:
    print(f'  ID {prov["id"]}: Ref {prov["ref_number"]} ({prov["text_length"]} chars)')
    if prov["text_length"] > 500:
        print('    COMPLETE TEXT:')
        print('    ' + '='*70)
        print('    ' + prov["provision_text"])
        print('    ' + '='*70)
    else:
        print(f'    Text: {prov["provision_text"][:150]}...')
    print()

# Check provisions near 6080 in SQLite
cursor.execute('SELECT id, ref_number, LENGTH(provision_text) as text_length, provision_text FROM regulatory_provisions WHERE id BETWEEN 6078 AND 6085 ORDER BY id')
nearby = cursor.fetchall()

print('Nearby provisions in SQLite:')
for prov in nearby:
    print(f'  ID {prov["id"]}: Ref {prov["ref_number"]} ({prov["text_length"]} chars)')
    if prov["text_length"] > 600:  # Look for longer texts
        print('    COMPLETE TEXT:')
        print('    ' + '='*70)
        print('    ' + prov["provision_text"])
        print('    ' + '='*70)
    else:
        print(f'    Text: {prov["provision_text"][:100]}...')
    print()

cursor.close()
conn.close()