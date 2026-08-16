#!/usr/bin/env python3
import os, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# Get Ashfield secondary dwelling chapter (F-Part2)
cur.execute("""
    SELECT id, ref_number, source_chapter_key, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'ashfield'
      AND is_current = TRUE
      AND (
          source_chapter_key ILIKE '%chapter_f%'
          OR source_chapter_key ILIKE '%f_dev_category%'
      )
    ORDER BY ref_number
    LIMIT 30
""")
rows = cur.fetchall()
print(f"Found {len(rows)} Ashfield Chapter F provisions")
for r in rows:
    print(f"\nREF: {r['ref_number']}")
    print(f"CHAPTER: {r['source_chapter_key']}")
    text = r['provision_text'] or ''
    print(f"TEXT ({len(text)} chars):")
    print(text[:800])
    print('---')

conn.close()
