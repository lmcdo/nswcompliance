#!/usr/bin/env python3
import os, sys
sys.path.insert(0, '.')
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from enrichment.extractors.numeric_extractor import NumericExtractor
load_dotenv()

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)
cur.execute("""
    SELECT id, ref_number, provision_text
    FROM regulatory_provisions
    WHERE source_council = 'ku_ring_gai'
    AND is_current = TRUE
    AND source_chapter_key ILIKE '%part_4_1_secondary_dwellings%'
    ORDER BY ref_number
""")
extractor = NumericExtractor()
for r in cur.fetchall():
    text = r['provision_text'] or ''
    result = extractor.extract(text)
    if result['has_numeric']:
        print('REF:', r['ref_number'])
        print('TEXT:', text[:300])
        print('VALUES:', result['values'])
        print('---')
conn.close()
