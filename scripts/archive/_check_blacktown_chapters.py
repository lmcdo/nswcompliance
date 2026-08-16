#!/usr/bin/env python3
import os
from dotenv import load_dotenv
import psycopg2

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
conn = psycopg2.connect(os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("SELECT council, chapter_key, chapter_label FROM dcp_chapter_registry WHERE council ILIKE '%blacktown%' ORDER BY chapter_key")
rows = cur.fetchall()
if rows:
    for r in rows:
        print(r)
else:
    print("No chapters found for Blacktown")
conn.close()
