#!/usr/bin/env python3
import os, sys, re, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enrichment.extractors.numeric_extractor import NumericExtractor

extractor = NumericExtractor()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# Waverley — full secondary dwelling provision text
print("=" * 60)
print("WAVERLEY — C1_1_16_controls (Secondary Dwellings) FULL TEXT")
print("=" * 60)
cur.execute("""
    SELECT id, ref_number, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'waverley' AND is_current = TRUE
      AND ref_number ILIKE '%1_16%'
    ORDER BY ref_number
""")
for r in cur.fetchall():
    print(f"\nREF: {r['ref_number']}")
    text = r['provision_text'] or ''
    print(f"TEXT ({len(text)} chars):\n{text}")
    result = extractor.extract(text)
    vals = result.get('values', [])
    print(f"\nEXTRACTED: {vals}")

# Woollahra — search for secondary dwelling provisions
print("\n\n" + "=" * 60)
print("WOOLLAHRA — secondary dwelling provisions")
print("=" * 60)
cur.execute("""
    SELECT id, ref_number, source_chapter_key, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'woollahra' AND is_current = TRUE
      AND (
          provision_text ILIKE '%secondary dwelling%'
          OR ref_number ILIKE '%secondary%'
          OR ref_number ILIKE '%granny%'
      )
    ORDER BY ref_number
""")
rows = cur.fetchall()
print(f"Found {len(rows)} secondary dwelling provisions")
for r in rows:
    print(f"\nREF: {r['ref_number'].split('__')[-1]}  ch={r['source_chapter_key']}  topic={r['v2_topic']}")
    text = r['provision_text'] or ''
    print(f"TEXT:\n{text[:500]}")
    result = extractor.extract(text)
    vals = result.get('values', [])
    if vals:
        print(f"VALS: {vals}")

conn.close()
