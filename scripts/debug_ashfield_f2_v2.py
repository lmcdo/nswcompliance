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

# Find the actual secondary dwellings chapter - F-Part2
cur.execute("""
    SELECT id, ref_number, source_chapter_key, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'ashfield'
      AND is_current = TRUE
      AND (
          ref_number ILIKE '%-Part2%'
          AND source_chapter_key ILIKE '%chapter_f%'
      )
    ORDER BY ref_number
    LIMIT 30
""")
rows = cur.fetchall()
print(f"Found {len(rows)} Ashfield Chapter F Part2 provisions\n")

for r in rows:
    text = r['provision_text'] or ''
    spaced = len(re.findall(r'(?<= )[A-Za-z](?= )', text))
    # Reversed text indicator: backward words
    reversed_words = len(re.findall(r'\b[A-Za-z]{3,}\b', text[::-1].lower()))
    verdict = 'GARBLED' if spaced > 10 else ('SUSPECT' if spaced > 3 else 'clean')
    ref_short = r['ref_number'][-70:]
    print(f"[{verdict:8}] spaced={spaced:3d} | {ref_short}")
    if verdict in ('GARBLED', 'SUSPECT') or len(text) < 500:
        print(f"  TEXT: {text[:400]}")

conn.close()
