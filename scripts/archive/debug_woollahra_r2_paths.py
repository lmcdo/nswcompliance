#!/usr/bin/env python3
import os, sys, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("""
    SELECT chapter_key, r2_current_path, r2_public_pdf_url, page_start, page_end
    FROM dcp_chapter_registry
    WHERE council ILIKE '%woollahra%'
    ORDER BY chapter_key
""")
for r in cur.fetchall():
    print(f"{r['chapter_key']:45} pages {r['page_start']}-{r['page_end']}")
    if r['r2_public_pdf_url']:
        print(f"  pub: {r['r2_public_pdf_url']}")
    elif r['r2_current_path']:
        print(f"  r2:  {r['r2_current_path']}")
conn.close()
