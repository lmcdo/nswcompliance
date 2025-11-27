#!/usr/bin/env python3
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

cur.execute('''
    SELECT column_name, data_type
    FROM information_schema.columns
    WHERE table_name = 'dcp_precinct_requirements'
    ORDER BY ordinal_position
''')

print('dcp_precinct_requirements columns:')
for row in cur.fetchall():
    print(f'  {row[0]}: {row[1]}')

cur.close()
conn.close()
