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

TARGET_CHAPTERS = ('part-c-s1-general', 'part-c-s3-residential')
TOPICS = ('setbacks', 'building_form', 'height', 'residential', 'site_coverage', 'landscaping')

# Control code pattern — only C-prefixed provisions (not O = objective)
CONTROL_RE = re.compile(r'__(C|DS|PC|AS)\d+', re.IGNORECASE)
OBJECTIVE_RE = re.compile(r'__O\d+', re.IGNORECASE)

extractor = NumericExtractor()

for chapter in TARGET_CHAPTERS:
    cur.execute("""
        SELECT id, ref_number, source_chapter_key, v2_topic, provision_text
        FROM regulatory_provisions
        WHERE source_council = 'leichhardt'
          AND is_current = TRUE
          AND source_chapter_key = %s
          AND v2_topic = ANY(%s)
        ORDER BY ref_number
    """, (chapter, list(TOPICS)))
    rows = cur.fetchall()
    print(f"\n=== {chapter} — {len(rows)} topic-matched provisions ===")

    for r in rows:
        ref = r['ref_number']
        # Skip objective provisions
        if OBJECTIVE_RE.search(ref):
            continue
        # Only control provisions
        if not CONTROL_RE.search(ref):
            continue

        text = r['provision_text'] or ''
        result = extractor.extract(text)
        setback_vals = [v for v in result['values']
                        if v.get('value_type') in ('setback', 'separation', 'height', 'site_coverage', 'landscaping')]
        if not setback_vals:
            continue

        print(f"\n  REF: {ref.split('__')[-1]}")
        print(f"  TOPIC: {r['v2_topic']}")
        print(f"  TEXT: {text[:300]}")
        print(f"  VALUES: {setback_vals}")

conn.close()
