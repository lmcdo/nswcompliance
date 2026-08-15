#!/usr/bin/env python3
"""
Check general residential (dwelling_house) setback provisions in DB text
for all 6 target councils. Identify what can be extracted vs needs OCR.
"""
import os, sys, re, psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
load_dotenv()
sys.stdout.reconfigure(encoding='utf-8')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from enrichment.extractors.numeric_extractor import NumericExtractor

extractor = NumericExtractor()
SETBACK_TYPES = {'setback', 'separation', 'height', 'site_coverage', 'landscaping'}

conn = psycopg2.connect(os.environ['SUPABASE_DB_URL'])
cur = conn.cursor(cursor_factory=RealDictCursor)

TARGETS = {
    'marrickville': {
        'chapter_keys': ['part4_s1_low_density', 'part4-s1-low-density'],
        'topics': ['setbacks', 'height', 'residential', 'building_form'],
        'note': 'Look for C10 general residential controls',
    },
    'ashfield': {
        'chapter_keys': ['chapter-f-dev-category', 'chapter_f_dev_category'],
        'topics': ['setbacks', 'height', 'residential', 'building_form'],
        'note': 'DS4 dwelling house controls in Chapter F',
    },
    'ku_ring_gai': {
        'chapter_keys': None,  # search all chapters
        'topics': ['setbacks', 'height', 'residential'],
        'note': 'Find general R2 residential setback chapter',
    },
    'leichhardt': {
        'chapter_keys': ['part-c-s3-residential', 'part-c-s1-general'],
        'topics': ['setbacks', 'height', 'residential', 'building_form'],
        'note': 'General residential envelope',
    },
    'waverley': {
        'chapter_keys': ['waverley-dcp-2022'],
        'topics': ['setbacks', 'height', 'residential', 'building_form'],
        'note': 'C1 Low Density Residential general setback section',
    },
}

CONTROL_RE = re.compile(r'__(C|DS|PC|AS|C\d)\d*', re.IGNORECASE)
OBJECTIVE_RE = re.compile(r'__O\d+', re.IGNORECASE)
GARBLE_RE = re.compile(r'(?<= )[A-Za-z](?= )')

for council, cfg in TARGETS.items():
    print(f"\n{'='*60}")
    print(f"{council.upper()} — {cfg['note']}")
    print('='*60)

    q_parts = ["source_council = %s", "is_current = TRUE"]
    params = [council]

    if cfg['topics']:
        q_parts.append("v2_topic = ANY(%s)")
        params.append(cfg['topics'])

    if cfg['chapter_keys']:
        like_clauses = ' OR '.join(['source_chapter_key ILIKE %s'] * len(cfg['chapter_keys']))
        q_parts.append(f"({like_clauses})")
        params.extend([f'%{k}%' for k in cfg['chapter_keys']])

    query = f"""
        SELECT id, ref_number, source_chapter_key, v2_topic, provision_text
        FROM regulatory_provisions
        WHERE {' AND '.join(q_parts)}
        ORDER BY source_chapter_key, ref_number
        LIMIT 200
    """
    cur.execute(query, params)
    rows = cur.fetchall()
    print(f"  Provisions found: {len(rows)}")

    found_any = False
    for r in rows:
        ref = r['ref_number'] or ''
        if OBJECTIVE_RE.search(ref):
            continue
        text = r['provision_text'] or ''
        if not text:
            continue

        result = extractor.extract(text)
        vals = [v for v in result.get('values', []) if v.get('value_type') in SETBACK_TYPES]
        if not vals:
            continue

        spaced = len(GARBLE_RE.findall(text))
        verdict = 'GARBLED' if spaced > 10 else ('SUSPECT' if spaced > 3 else 'clean ')
        found_any = True
        print(f"\n  [{verdict}] {ref.split('__')[-1]}  topic={r['v2_topic']}")
        print(f"  TEXT: {text[:200]}")
        print(f"  VALS: {vals}")

    if not found_any:
        print("  → No extractable setback values in DB text. Needs OCR.")

conn.close()
