#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
with conn.cursor() as cur:
    cur.execute("DELETE FROM dcp_setback_controls WHERE lga = 'leichhardt'")
    print(f"Deleted {cur.rowcount} Leichhardt rows")
conn.commit()
conn.close()
