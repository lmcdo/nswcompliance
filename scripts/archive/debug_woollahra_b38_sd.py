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

# Get B3_8 from correct chapter
cur.execute("""
    SELECT provision_text FROM regulatory_provisions
    WHERE source_council = 'woollahra' AND is_current = TRUE
      AND source_chapter_key = 'chapter-b3-general-development'
      AND ref_number ILIKE '%B3_8%'
""")
r = cur.fetchone()
text = r['provision_text'] or ''

# Find secondary dwelling section
m = re.search(r'secondary dwelling', text, re.IGNORECASE)
if not m:
    print("Section not found!")
else:
    section = text[m.start(): m.start() + 6000]
    print(f"Found at offset {m.start()}\n")
    print(section)

# Also get B3_2 setback controls
print("\n\n=== B3_2 SETBACK TABLES ===")
cur.execute("""
    SELECT provision_text FROM regulatory_provisions
    WHERE source_council = 'woollahra' AND is_current = TRUE
      AND source_chapter_key = 'chapter-b3-general-development'
      AND ref_number ILIKE '%B3_2%'
""")
r = cur.fetchone()
if r:
    text2 = r['provision_text'] or ''
    # Find front/side/rear setback tables
    for m2 in re.finditer(r'(front|side|rear)\s+setback', text2, re.IGNORECASE):
        chunk = text2[max(0, m2.start()-50): m2.start()+800]
        print(f"\n--- {m2.group(0)} at offset {m2.start()} ---")
        print(chunk)

conn.close()
