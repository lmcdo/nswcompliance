#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute('SELECT provision_text FROM regulatory_provisions WHERE id = 80214')
print(repr(cur.fetchone()[0]))
cur.close()
conn.close()
