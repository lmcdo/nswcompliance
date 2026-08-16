#!/usr/bin/env python3
import os, sys, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enrichment.extractors.numeric_extractor import NumericExtractor

extractor = NumericExtractor()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# Full B3_8 text
cur.execute("""
    SELECT id, ref_number, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'woollahra' AND is_current = TRUE
      AND ref_number ILIKE '%B3_8%'
""")
r = cur.fetchone()
if r:
    text = r['provision_text'] or ''
    print(f"REF: {r['ref_number']}")
    print(f"LENGTH: {len(text)} chars\n")
    print(text)
    print("\n--- EXTRACTOR ---")
    result = extractor.extract(text)
    print(result['values'])

# Also check B1 for secondary dwelling setback controls
print("\n\n=== WOOLLAHRA B1 — all provisions with numeric setbacks ===")
cur.execute("""
    SELECT id, ref_number, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'woollahra' AND is_current = TRUE
      AND source_chapter_key = 'chapter-b1-residential-precincts'
    ORDER BY ref_number
""")
import re
NUMERIC_TYPES = {'setback', 'separation', 'height', 'site_coverage', 'landscaping'}
for r in cur.fetchall():
    text = r['provision_text'] or ''
    if not text:
        continue
    result = extractor.extract(text)
    vals = [v for v in result.get('values', []) if v.get('value_type') in NUMERIC_TYPES]
    if not vals:
        continue
    print(f"\nREF: {r['ref_number'].split('__')[-1]}  topic={r['v2_topic']}")
    print(f"TEXT: {text[:300]}")
    print(f"VALS: {vals}")

conn.close()
