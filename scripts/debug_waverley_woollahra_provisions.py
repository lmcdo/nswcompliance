#!/usr/bin/env python3
import os, sys, re, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from enrichment.extractors.numeric_extractor import NumericExtractor

CONTROL_RE = re.compile(r'__(C|DS|PC|AS)\d+', re.IGNORECASE)
OBJECTIVE_RE = re.compile(r'__O\d+($|[^a-z])', re.IGNORECASE)
NUMERIC_TYPES = {'setback', 'separation', 'separation_min', 'height', 'site_coverage', 'landscaping'}

extractor = NumericExtractor()
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# ----- WAVERLEY -----
print("=" * 60)
print("WAVERLEY — setbacks + height provisions")
print("=" * 60)
cur.execute("""
    SELECT id, ref_number, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'waverley' AND is_current = TRUE
      AND v2_topic IN ('setbacks', 'height', 'residential', 'building_form')
    ORDER BY ref_number
""")
for r in cur.fetchall():
    ref = r['ref_number']
    if OBJECTIVE_RE.search(ref):
        continue
    text = r['provision_text'] or ''
    result = extractor.extract(text)
    vals = [v for v in result['values'] if v.get('value_type') in NUMERIC_TYPES]
    if not vals:
        continue
    spaced = len(re.findall(r'(?<= )[A-Za-z](?= )', text))
    verdict = 'GARBLED' if spaced > 10 else ('SUSPECT' if spaced > 3 else 'clean')
    print(f"\n  [{verdict:7}] {ref.split('__')[-1]}  topic={r['v2_topic']}")
    print(f"  TEXT: {text[:250]}")
    print(f"  VALS: {vals}")

# ----- WOOLLAHRA -----
print("\n\n" + "=" * 60)
print("WOOLLAHRA — b1/b3/b4 residential + setback provisions")
print("=" * 60)
cur.execute("""
    SELECT id, ref_number, source_chapter_key, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'woollahra' AND is_current = TRUE
      AND source_chapter_key IN (
          'chapter-b1-residential-precincts',
          'chapter-b3-general-development',
          'chapter-b4-housing-accessible-areas'
      )
    ORDER BY source_chapter_key, ref_number
""")
for r in cur.fetchall():
    ref = r['ref_number']
    if OBJECTIVE_RE.search(ref):
        continue
    text = r['provision_text'] or ''
    result = extractor.extract(text)
    vals = [v for v in result['values'] if v.get('value_type') in NUMERIC_TYPES]
    if not vals:
        continue
    spaced = len(re.findall(r'(?<= )[A-Za-z](?= )', text))
    verdict = 'GARBLED' if spaced > 10 else ('SUSPECT' if spaced > 3 else 'clean')
    print(f"\n  [{verdict:7}] {ref.split('__')[-1]}  ch={r['source_chapter_key']}  topic={r['v2_topic']}")
    print(f"  TEXT: {text[:250]}")
    print(f"  VALS: {vals}")

conn.close()
