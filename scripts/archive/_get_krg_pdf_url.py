#!/usr/bin/env python3
import os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / '.env')
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()
cur.execute("""
    SELECT chapter_key, pdf_url, r2_public_pdf_url
    FROM dcp_chapter_registry
    WHERE council = 'ku_ring_gai' AND chapter_key ILIKE '%signage%'
    LIMIT 3
""")
for row in cur.fetchall():
    print(f"chapter: {row[0]}")
    print(f"  pdf_url: {row[1]}")
    print(f"  r2_url:  {row[2]}")
cur.close()
conn.close()
