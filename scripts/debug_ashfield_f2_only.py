#!/usr/bin/env python3
import os, re, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# Look for F-Part2 / secondary dwelling chapter
cur.execute("""
    SELECT id, ref_number, source_chapter_key, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'ashfield'
      AND is_current = TRUE
      AND (
          ref_number ILIKE '%Part2%'
          OR ref_number ILIKE '%F-Part2%'
          OR ref_number ILIKE '%secondary%'
          OR source_chapter_key ILIKE '%secondary%'
          OR source_chapter_key ILIKE '%f2%'
      )
    ORDER BY ref_number
    LIMIT 20
""")
rows = cur.fetchall()
print(f"Found {len(rows)} Ashfield F-Part2/secondary provisions")
for r in rows:
    print(f"\nREF: {r['ref_number']}")
    print(f"CHAPTER: {r['source_chapter_key']}")
    text = r['provision_text'] or ''
    # Count garble indicators
    spaced = len(re.findall(r'(?<= )[A-Za-z](?= )', text))
    print(f"LENGTH: {len(text)} chars, spaced_chars: {spaced}")
    print(text[:600])
    print('---')

# Also check what F-Part2 DS entries exist
cur.execute("""
    SELECT id, ref_number, source_chapter_key, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'ashfield'
      AND is_current = TRUE
      AND ref_number ILIKE '%application_DS%'
      AND ref_number LIKE '%Part2%'
    ORDER BY ref_number
    LIMIT 20
""")
rows2 = cur.fetchall()
print(f"\n\nFound {len(rows2)} Ashfield F-Part2 DS provisions (design solutions)")
for r in rows2:
    text = r['provision_text'] or ''
    spaced = len(re.findall(r'(?<= )[A-Za-z](?= )', text))
    print(f"REF: {r['ref_number'][-70:]}")
    print(f"  LENGTH: {len(text)}, spaced_chars: {spaced}")
    if spaced > 5:
        print(f"  TEXT: {text[:300]}")

conn.close()
