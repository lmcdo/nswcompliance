#!/usr/bin/env python3
"""Show structural source data per council — chapter keys and section headers."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))
import psycopg2

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
cur = conn.cursor()

for council in ['leichhardt', 'marrickville', 'ashfield', 'waverley', 'woollahra']:
    # Chapter keys
    cur.execute("""
        SELECT source_chapter_key, COUNT(*)
        FROM regulatory_provisions
        WHERE is_current = true AND source_council = %s
        GROUP BY source_chapter_key
        ORDER BY source_chapter_key
    """, (council,))
    rows = cur.fetchall()
    print(f"=== {council.upper()} ({len(rows)} chapter keys, {sum(r[1] for r in rows)} provisions) ===")
    for r in rows:
        print(f"  {r[0]:55s} {r[1]:4d}")

    # Unique section headers (sample)
    cur.execute("""
        SELECT DISTINCT section_header
        FROM regulatory_provisions
        WHERE is_current = true AND source_council = %s
          AND section_header IS NOT NULL
        ORDER BY section_header
        LIMIT 30
    """, (council,))
    headers = [r[0] for r in cur.fetchall()]
    print(f"  --- Section headers (sample of {len(headers)}) ---")
    for h in headers[:20]:
        print(f"    {h[:70]}")
    print()

cur.close()
conn.close()
