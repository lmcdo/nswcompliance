#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
conn = psycopg2.connect(os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("SELECT council, chapter_key, chapter_label FROM dcp_chapter_registry WHERE council ILIKE '%ku%ring%' ORDER BY chapter_key")
for r in cur.fetchall():
    print(r)
# Also check what lga value other parking rows use
cur.execute("SELECT DISTINCT lga FROM dcp_setback_controls WHERE lga ILIKE '%ku%' OR lga ILIKE '%kur%'")
print("\nExisting lga values:", [r[0] for r in cur.fetchall()])
conn.close()
