#!/usr/bin/env python3
import os, psycopg2
from dotenv import load_dotenv
load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor()
cur.execute("""
    SELECT column_name, data_type, column_default, is_nullable
    FROM information_schema.columns
    WHERE table_name = 'dcp_chapter_registry'
    ORDER BY ordinal_position
""")
for r in cur.fetchall():
    print(f"  {r[0]:35} {r[1]:20} nullable={r[3]} default={r[2]}")
print()
# Sample a row to see what's there
cur.execute("SELECT * FROM dcp_chapter_registry LIMIT 1")
cols = [d[0] for d in cur.description]
row = cur.fetchone()
if row:
    for c, v in zip(cols, row):
        print(f"  {c}: {v}")
conn.close()
