#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
conn = psycopg2.connect(os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("""
    SELECT conname, pg_get_constraintdef(oid) FROM pg_constraint
    WHERE conrelid = 'dcp_setback_controls'::regclass
""")
for r in cur.fetchall():
    print(f"{r[0]}: {r[1][:200]}")
conn.close()
