#!/usr/bin/env python3
"""Find R2 PDF paths for OCR targets: Marrickville, Ku-ring-gai, Waverley general residential chapters."""
import os, sys, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# Marrickville — find part 4 residential chapter
cur.execute("""
    SELECT chapter_key, r2_public_pdf_url, page_start, page_end
    FROM dcp_chapter_registry
    WHERE council ILIKE '%marrickville%'
    ORDER BY chapter_key
""")
print("=== MARRICKVILLE ===")
for r in cur.fetchall():
    print(f"  {r['chapter_key']:50} pages {r['page_start']}-{r['page_end']}")
    if r['r2_public_pdf_url']:
        print(f"    {r['r2_public_pdf_url']}")

# Ku-ring-gai
cur.execute("""
    SELECT chapter_key, r2_public_pdf_url, page_start, page_end
    FROM dcp_chapter_registry
    WHERE council ILIKE '%ku%ring%gai%' OR council ILIKE '%ku_ring_gai%'
    ORDER BY chapter_key
""")
print("\n=== KU-RING-GAI ===")
for r in cur.fetchall():
    print(f"  {r['chapter_key']:50} pages {r['page_start']}-{r['page_end']}")
    if r['r2_public_pdf_url']:
        print(f"    {r['r2_public_pdf_url']}")

# Waverley
cur.execute("""
    SELECT chapter_key, r2_public_pdf_url, page_start, page_end
    FROM dcp_chapter_registry
    WHERE council ILIKE '%waverley%'
    ORDER BY chapter_key
""")
print("\n=== WAVERLEY ===")
for r in cur.fetchall():
    print(f"  {r['chapter_key']:50} pages {r['page_start']}-{r['page_end']}")
    if r['r2_public_pdf_url']:
        print(f"    {r['r2_public_pdf_url']}")

conn.close()
