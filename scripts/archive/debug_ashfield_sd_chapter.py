#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, re
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# 1. All distinct chapter_keys in Ashfield
cur.execute("""
    SELECT DISTINCT source_chapter_key, count(*) as cnt
    FROM regulatory_provisions
    WHERE source_council = 'ashfield' AND is_current = TRUE
    GROUP BY source_chapter_key
    ORDER BY source_chapter_key
""")
print("=== All Ashfield chapter keys ===")
for r in cur.fetchall():
    print(f"  {r['source_chapter_key']:50} ({r['cnt']} provisions)")

# 2. Look for secondary dwelling text anywhere in Chapter F
cur.execute("""
    SELECT id, ref_number, source_chapter_key,
           LEFT(provision_text, 300) as snippet
    FROM regulatory_provisions
    WHERE source_council = 'ashfield'
      AND is_current = TRUE
      AND provision_text ILIKE '%secondary dwelling%'
    ORDER BY ref_number
    LIMIT 15
""")
rows = cur.fetchall()
print(f"\n=== Provisions mentioning 'secondary dwelling' ({len(rows)}) ===")
for r in rows:
    print(f"\nREF: {r['ref_number']}")
    print(f"CHAPTER: {r['source_chapter_key']}")
    print(f"SNIPPET: {r['snippet']}")

conn.close()
