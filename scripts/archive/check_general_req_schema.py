#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print('Columns in dcp_general_requirements:')
cur.execute('''
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'dcp_general_requirements'
    ORDER BY ordinal_position
''')
for r in cur.fetchall():
    print(f'  {r[0]}')

print('\n\nSample data:')
cur.execute('''
    SELECT id, part_number, part_name, category, former_council, pdf_page
    FROM dcp_general_requirements
    WHERE category = 'heritage' OR part_name = 'Heritage'
    LIMIT 10
''')
for r in cur.fetchall():
    print(f'ID {r[0]}: part_num={r[1]}, part_name={r[2]}, cat={r[3]}, council={r[4]}, page={r[5]}')

cur.close()
conn.close()
