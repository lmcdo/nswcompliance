#!/usr/bin/env python3
import os, sys, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("""
    SELECT council, chapter_key, r2_current_path, r2_public_pdf_url, page_start, page_end
    FROM dcp_chapter_registry
    WHERE council ILIKE ANY(ARRAY['%leichhardt%', '%ashfield%'])
    ORDER BY council, chapter_key
""")
for r in cur.fetchall():
    print(f"{r['council']:20} | {r['chapter_key']:50} | pages {r['page_start']}-{r['page_end']}")
    if r['r2_current_path']:
        print(f"  r2: {r['r2_current_path']}")
    if r['r2_public_pdf_url']:
        print(f"  pub: {r['r2_public_pdf_url']}")
conn.close()
