import psycopg2
import json

conn = psycopg2.connect(
    dbname='nsw_planning',
    user='postgres',
    password='Duffysql1!',
    host='localhost',
    port='5432'
)
cur = conn.cursor()

print('=== Searching for Precinct Boundary Data ===\n')

# 1. Check what data we have for each precinct
cur.execute('''
    SELECT precinct_id, precinct_name, COUNT(*) as provision_count
    FROM dcp_precinct_provisions
    GROUP BY precinct_id, precinct_name
    ORDER BY precinct_id
''')

print('1. All precincts in database:')
all_precincts = cur.fetchall()
for p in all_precincts:
    print(f'   {p[0]}: {p[1]} ({p[2]} provisions)')

# 2. Search for boundary descriptions
print('\n2. Searching for boundary/extent descriptions...')
cur.execute('''
    SELECT precinct_id, precinct_name, ref_number, section_header,
           LEFT(provision_text, 500) as text_sample
    FROM dcp_precinct_provisions
    WHERE (LOWER(provision_text) LIKE '%boundary%'
       OR LOWER(provision_text) LIKE '%extent%'
       OR LOWER(provision_text) LIKE '%bounded by%'
       OR LOWER(section_header) LIKE '%boundary%'
       OR LOWER(section_header) LIKE '%extent%'
       OR LOWER(ref_number) LIKE '%boundary%')
    ORDER BY precinct_id
    LIMIT 10
''')

boundary_rows = cur.fetchall()
if boundary_rows:
    for row in boundary_rows:
        print(f'\n   Precinct {row[0]}: {row[1]}')
        print(f'   Ref: {row[2]}')
        print(f'   Header: {row[3]}')
        print(f'   Text: {row[4][:200]}...')
else:
    print('   No explicit boundary descriptions found')

# 3. Check document_id patterns to find source PDFs
print('\n3. DCP document sources:')
cur.execute('''
    SELECT DISTINCT document_id
    FROM dcp_precinct_provisions
    ORDER BY document_id
    LIMIT 10
''')
for row in cur.fetchall():
    print(f'   {row[0]}')

# 4. Check if there are any JSON files with precinct data
print('\n4. Checking for extracted JSON data...')
import os
import glob

json_files = glob.glob('extraction_outputs/dcps/**/Marrickville*Precinct*.json', recursive=True)
if json_files:
    print(f'   Found {len(json_files)} JSON files')
    for f in json_files[:5]:
        print(f'   {os.path.basename(f)}')
else:
    print('   No JSON files found in extraction_outputs/dcps/')

# 5. Check MinerU output directory
json_files2 = glob.glob('output/**/Marrickville*Precinct*/*.json', recursive=True)
if json_files2:
    print(f'\n   Found {len(json_files2)} JSON files in output/')
    for f in json_files2[:5]:
        print(f'   {os.path.basename(f)}')

cur.close()
conn.close()
