#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

from enrichment.extractors.numeric_extractor import NumericExtractor

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

cur.execute("""
    SELECT id, ref_number, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'ashfield'
      AND is_current = TRUE
      AND source_chapter_key = 'chapter-f-dev-category'
    ORDER BY ref_number
""")
rows = cur.fetchall()
print(f"Total Chapter F provisions: {len(rows)}")
print("\n=== Provisions with numeric setback/height values ===\n")

extractor = NumericExtractor()

for r in rows:
    text = r['provision_text'] or ''
    if not text.strip():
        continue

    has_sd = 'secondary dwelling' in text.lower()
    result = extractor.extract(text)
    setback_vals = [v for v in result['values']
                    if v.get('value_type') in ('setback', 'separation', 'height', 'lot_area', 'site_coverage')]
    if not setback_vals:
        continue

    spaced = len(re.findall(r'(?<= )[A-Za-z](?= )', text))
    verdict = 'GARBLED' if spaced > 10 else ('SUSPECT' if spaced > 3 else 'clean')
    ref_short = r['ref_number'].split('__')[-1]
    print(f"[{verdict:8}] {'[SD]' if has_sd else '    '} {ref_short}")
    print(f"  TEXT: {text[:200]}")
    print(f"  VALUES: {setback_vals}")
    print()

conn.close()
