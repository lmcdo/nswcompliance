#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

print("All provisions tagged as heritage (category or part_name):")
cur.execute('''
    SELECT DISTINCT part_number, part_name, category, COUNT(*)
    FROM dcp_general_requirements
    WHERE category = 'heritage' OR part_name ILIKE '%heritage%'
    GROUP BY part_number, part_name, category
    ORDER BY part_number, part_name
''')
for r in cur.fetchall():
    print(f'  part_num={r[0]} | part_name={r[1]} | cat={r[2]} | count={r[3]}')

cur.close()
conn.close()
