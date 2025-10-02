import psycopg2
from psycopg2.extras import RealDictCursor

conn = psycopg2.connect(host='localhost', database='nsw_planning_corrected', user='postgres', password='postgres', port='5432')
cursor = conn.cursor(cursor_factory=RealDictCursor)

print('=== SEARCHING FOR COMPLETE SEPP 2.2 TEXT IN DATABASE ===')
print()

# Search for all provisions with ref_number 2.2 in the same document
cursor.execute('''
    SELECT id, ref_number, provision_text, LENGTH(provision_text) as text_length
    FROM regulatory_provisions
    WHERE document_id = 'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation'
    AND (ref_number LIKE '2.2%' OR provision_text ILIKE '%competing provision%')
    ORDER BY id
''')
provisions = cursor.fetchall()

print(f'Found {len(provisions)} related provisions:')
for prov in provisions:
    print(f'  ID {prov["id"]}: Ref {prov["ref_number"]} ({prov["text_length"]} chars)')
    print(f'    Text: {prov["provision_text"][:100]}...')
    print()

# Search for provisions that might contain the continuation
cursor.execute('''
    SELECT id, ref_number, provision_text, LENGTH(provision_text) as text_length
    FROM regulatory_provisions
    WHERE document_id = 'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation'
    AND provision_text ILIKE '%subsection%'
    ORDER BY id
''')
subsections = cursor.fetchall()

print(f'Found {len(subsections)} provisions with "subsection":')
for prov in subsections:
    print(f'  ID {prov["id"]}: Ref {prov["ref_number"]} ({prov["text_length"]} chars)')
    print(f'    Text: {prov["provision_text"][:150]}...')
    print()

# Search for any provision starting with text that looks like continuation
cursor.execute('''
    SELECT id, ref_number, provision_text, LENGTH(provision_text) as text_length
    FROM regulatory_provisions
    WHERE document_id = 'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation'
    AND (provision_text ILIKE 'section%' OR provision_text ILIKE '(2)%' OR provision_text ILIKE '(3)%')
    ORDER BY id
''')
continuations = cursor.fetchall()

print(f'Found {len(continuations)} provisions that might be continuations:')
for prov in continuations:
    print(f'  ID {prov["id"]}: Ref {prov["ref_number"]} ({prov["text_length"]} chars)')
    print(f'    Text: {prov["provision_text"][:150]}...')
    print()

# Check provisions immediately after ID 6080
cursor.execute('''
    SELECT id, ref_number, provision_text, LENGTH(provision_text) as text_length
    FROM regulatory_provisions
    WHERE id BETWEEN 6080 AND 6085
    ORDER BY id
''')
nearby = cursor.fetchall()

print('Provisions near ID 6080:')
for prov in nearby:
    print(f'  ID {prov["id"]}: Ref {prov["ref_number"]} ({prov["text_length"]} chars)')
    print(f'    Text: {prov["provision_text"][:150]}...')
    print()

# Get the longest provision from this document to see if it contains the full text
cursor.execute('''
    SELECT id, ref_number, provision_text, LENGTH(provision_text) as text_length
    FROM regulatory_provisions
    WHERE document_id = 'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation'
    ORDER BY text_length DESC
    LIMIT 3
''')
longest = cursor.fetchall()

print('Longest provisions from this document:')
for prov in longest:
    print(f'  ID {prov["id"]}: Ref {prov["ref_number"]} ({prov["text_length"]} chars)')
    if prov["text_length"] > 500:
        print(f'    Full text:')
        print('    ' + '='*70)
        print('    ' + prov["provision_text"])
        print('    ' + '='*70)
    else:
        print(f'    Text: {prov["provision_text"][:200]}...')
    print()

cursor.close()
conn.close()