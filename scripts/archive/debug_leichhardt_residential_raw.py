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

CONTROL_RE = re.compile(r'__(C|DS|PC|AS)\d+', re.IGNORECASE)
OBJECTIVE_RE = re.compile(r'__O\d+($|[^a-z])', re.IGNORECASE)

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)
extractor = NumericExtractor()

for chapter in ('part-c-s1-general', 'part-c-s3-residential'):
    cur.execute("""
        SELECT id, ref_number, v2_topic, provision_text
        FROM regulatory_provisions
        WHERE source_council = 'leichhardt'
          AND is_current = TRUE
          AND source_chapter_key = %s
        ORDER BY ref_number
    """, (chapter,))
    rows = cur.fetchall()
    print(f"\n=== {chapter} — {len(rows)} total provisions ===")

    for r in rows:
        ref = r['ref_number']
        if OBJECTIVE_RE.search(ref):
            continue

        text = r['provision_text'] or ''
        result = extractor.extract(text)
        setback_vals = [v for v in result['values']
                        if v.get('value_type') in ('setback', 'separation', 'height', 'site_coverage', 'landscaping')]
        if not setback_vals:
            continue

        spaced = len(re.findall(r'(?<= )[A-Za-z](?= )', text))
        verdict = 'GARBLED' if spaced > 10 else ('SUSPECT' if spaced > 3 else 'clean')
        print(f"\n  [{verdict:8}] {ref.split('__')[-1]} (topic={r['v2_topic']})")
        print(f"  TEXT: {text[:300]}")
        print(f"  VALUES: {setback_vals}")

conn.close()
