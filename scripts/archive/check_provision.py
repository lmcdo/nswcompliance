#!/usr/bin/env python3
import os
import sys
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

prov_id = int(sys.argv[1]) if len(sys.argv) > 1 else 78300

cur.execute('SELECT id, v2_topic, LEFT(provision_text, 500) FROM regulatory_provisions WHERE id = %s', (prov_id,))
row = cur.fetchone()
if row:
    print(f'ID: {row[0]}')
    print(f'Topic: {row[1]}')
    print(f'Text: {row[2]}')
else:
    print(f'Not found: {prov_id}')

cur.close()
conn.close()
