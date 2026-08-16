#!/usr/bin/env python3
import os, sys, re, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enrichment.extractors.numeric_extractor import NumericExtractor

extractor = NumericExtractor()
NUMERIC_TYPES = {'setback', 'separation', 'separation_min', 'height', 'site_coverage', 'landscaping'}
conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# Get B3_8 from the correct chapter
cur.execute("""
    SELECT id, ref_number, source_chapter_key, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'woollahra' AND is_current = TRUE
      AND source_chapter_key = 'chapter-b3-general-development'
    ORDER BY ref_number
""")
rows = cur.fetchall()
print(f"chapter-b3-general-development: {len(rows)} provisions\n")
for r in rows:
    text = r['provision_text'] or ''
    ref_short = r['ref_number'].split('__')[-1]
    # Print full text for any provision mentioning secondary dwelling or setbacks
    if re.search(r'secondary.?dwell|setback|rear.+setback|side.+setback', text, re.IGNORECASE):
        print(f"\n{'='*55}")
        print(f"REF: {ref_short}  topic={r['v2_topic']}")
        print(f"TEXT ({len(text)} chars):")
        print(text[:2000])
        result = extractor.extract(text)
        vals = [v for v in result.get('values', []) if v.get('value_type') in NUMERIC_TYPES]
        if vals:
            print(f"\nEXTRACTED: {vals}")

conn.close()
