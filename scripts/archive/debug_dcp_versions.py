#!/usr/bin/env python3
import os, sys, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("""
    SELECT council, chapter_key, r2_current_path
    FROM dcp_chapter_registry
    WHERE council ILIKE ANY(ARRAY['%ashfield%','%leichhardt%','%marrickville%',
                                   '%waverley%','%woollahra%','%ku-ring-gai%','%ku_ring_gai%'])
      AND r2_current_path IS NOT NULL
    ORDER BY council, chapter_key
""")

seen = set()
for r in cur.fetchall():
    parts = (r['r2_current_path'] or '').split('/')
    version = parts[3] if len(parts) > 3 else 'unknown'
    key = (r['council'], version)
    if key not in seen:
        seen.add(key)
        print(f"{r['council']:30} {version}")

conn.close()
