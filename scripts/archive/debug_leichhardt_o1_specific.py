#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')

from enrichment.extractors.numeric_extractor import NumericExtractor

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

# The specific O1 provision that was extracted
cur.execute("""
    SELECT ref_number, v2_topic, provision_text
    FROM regulatory_provisions
    WHERE ref_number = 'Leichhardt_DCP_2013__part_c_s2_urban_character__O1'
      AND is_current = TRUE
    LIMIT 1
""")
r = cur.fetchone()
if r:
    text = r['provision_text'] or ''
    print(f"REF: {r['ref_number']}")
    print(f"TOPIC: {r['v2_topic']}")
    print(f"TEXT ({len(text)} chars):")
    print(text[:1500])
    print()
    extractor = NumericExtractor()
    result = extractor.extract(text)
    print("EXTRACTED VALUES:")
    for v in result['values']:
        print(" ", v)
else:
    print("NOT FOUND — checking all O1 provisions:")
    cur.execute("""
        SELECT ref_number, v2_topic, LEFT(provision_text, 400) as snippet
        FROM regulatory_provisions
        WHERE source_council = 'leichhardt'
          AND is_current = TRUE
          AND ref_number LIKE '%__O1%'
          AND v2_topic IN ('height', 'residential', 'building_form', 'setbacks')
        ORDER BY ref_number
    """)
    for r in cur.fetchall():
        print(f"\nREF: {r['ref_number']}")
        print(f"TOPIC: {r['v2_topic']}")
        print(f"SNIPPET: {r['snippet']}")

conn.close()
