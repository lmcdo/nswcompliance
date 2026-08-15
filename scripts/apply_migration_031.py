#!/usr/bin/env python3
import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
with open('migrations/031_dcp_setback_controls.sql') as f:
    sql = f.read()

with conn.cursor() as cur:
    cur.execute(sql)
conn.commit()
conn.close()
print('Migration 031 applied successfully')
