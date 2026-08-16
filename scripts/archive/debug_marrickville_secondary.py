#!/usr/bin/env python3
import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# Find secondary dwelling tagged provisions for Marrickville
cur.execute("""
    SELECT id, ref_number, source_chapter_key, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'marrickville'
    AND is_current = TRUE
    AND v2_applicable_dev_types @> ARRAY['secondary_dwelling']
    ORDER BY ref_number
    LIMIT 20
""")
rows = cur.fetchall()
print(f"Found {len(rows)} secondary_dwelling provisions for marrickville")
for r in rows:
    print('REF:', r['ref_number'])
    print('CHAPTER:', r['source_chapter_key'])
    print('TOPIC:', r['v2_topic'])
    print('TEXT:', (r['provision_text'] or '')[:400])
    print('---')

# Also look at part4 secondary dwelling chapter
cur.execute("""
    SELECT id, ref_number, source_chapter_key, v2_topic
    FROM regulatory_provisions
    WHERE source_council = 'marrickville'
    AND is_current = TRUE
    AND (
        source_chapter_key ILIKE '%secondary%'
        OR ref_number ILIKE '%secondary%'
        OR ref_number ILIKE '%part4_s1%'
    )
    LIMIT 20
""")
rows2 = cur.fetchall()
print(f"\nFound {len(rows2)} provisions matching secondary/part4_s1")
for r in rows2:
    print('REF:', r['ref_number'])
    print('CHAPTER:', r['source_chapter_key'])

conn.close()
