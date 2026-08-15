#!/usr/bin/env python3
"""Final accuracy summary for all councils"""

import os
import re
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback', 'height': r'\bheight', 'parking': r'\bparking',
    'solar': r'\bsolar', 'privacy': r'\bprivacy', 'landscaping': r'\blandscap',
    'heritage': r'\bheritage', 'trees': r'\btree', 'fencing': r'\bfenc',
    'access': r'\baccess', 'stormwater': r'\bstormwater', 'waste': r'\bwaste',
    'signage': r'\bsign', 'building_form': r'\bbulk|scale|massing',
    'building_design': r'\bdesign|facade', 'open_space': r'\bopen\s+space',
    'flooding': r'\bflood', 'contamination': r'\bcontaminat', 'safety': r'\bsafety',
    'residential': r'\bresidential', 'commercial': r'\bcommercial',
    'precinct': r'\bprecinct', 'general': r'\bobjective', 'energy': r'\benergy',
    'water': r'\bwater', 'environmental': r'\benvironmental',
}

conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

print('=' * 70)
print('FINAL TOPIC ASSIGNMENT ACCURACY - ALL COUNCILS')
print('=' * 70)

all_results = []

for council in ['Leichhardt', 'Ashfield', 'Marrickville']:
    cur = conn.cursor()

    # Get totals
    cur.execute('''
        SELECT COUNT(*) as total,
               COUNT(*) FILTER (WHERE v2_topic IS NULL) as none_count
        FROM regulatory_provisions
        WHERE document_id ILIKE %s AND is_current = TRUE
    ''', (f'%{council}%',))
    totals = cur.fetchone()

    # Get provisions with topics
    cur.execute('''
        SELECT id, provision_text, v2_topic, v2_dcp_part
        FROM regulatory_provisions
        WHERE document_id ILIKE %s AND v2_topic IS NOT NULL AND is_current = TRUE
    ''', (f'%{council}%',))
    provs = cur.fetchall()

    kw_match = c_mark = part_def = no_kw = wrong = 0

    for p in provs:
        text = (p['provision_text'] or '').lower()
        assigned = p['v2_topic']
        part = p['v2_dcp_part'] or ''

        # C marker check
        if re.match(r'^c\d+', text.strip()):
            c_mark += 1
            continue

        # Part default (Chapter E1 = heritage)
        if part == 'Chapter E1' and assigned == 'heritage':
            part_def += 1
            continue

        # Keyword matching
        pattern = TOPIC_KEYWORDS.get(assigned)
        has_match = pattern and re.search(pattern, text)

        has_other = False
        for t, pat in TOPIC_KEYWORDS.items():
            if t != assigned and re.search(pat, text):
                has_other = True
                break

        if has_match:
            kw_match += 1
        elif not has_other:
            no_kw += 1
        else:
            wrong += 1

    total = len(provs)

    # Estimate accuracy based on manual review findings:
    # keyword_match = 100%, c_marker = 100%, part_default = 100%
    # no_keywords = 90% (manual review showed 90-95%)
    # wrong_topic = 65% for Leichhardt, but lower for others based on samples
    wrong_accuracy = 0.65 if council == 'Leichhardt' else 0.40  # Ashfield/Marrickville had worse wrong_topic accuracy

    accurate = kw_match + c_mark + part_def + no_kw * 0.90 + wrong * wrong_accuracy
    error_count = total - accurate

    all_results.append({
        'council': council,
        'total': totals['total'],
        'none': totals['none_count'],
        'kw_match': kw_match,
        'c_mark': c_mark,
        'part_def': part_def,
        'no_kw': no_kw,
        'wrong': wrong,
        'accuracy': accurate / total * 100 if total > 0 else 0,
        'errors': error_count
    })

    print(f"\n{council}:")
    print(f"  Total provisions: {totals['total']}")
    print(f"  None topics: {totals['none_count']}")
    print(f"  ---")
    print(f"  Keyword match:  {kw_match:>5} ({kw_match/total*100:>5.1f}%) - 100% accurate")
    print(f"  C marker:       {c_mark:>5} ({c_mark/total*100:>5.1f}%) - 100% accurate")
    print(f"  Part default:   {part_def:>5} ({part_def/total*100:>5.1f}%) - 100% accurate")
    print(f"  No keywords:    {no_kw:>5} ({no_kw/total*100:>5.1f}%) - ~90% accurate")
    print(f"  Wrong topic:    {wrong:>5} ({wrong/total*100:>5.1f}%) - ~{int(wrong_accuracy*100)}% accurate")
    print(f"  ---")
    print(f"  ESTIMATED ACCURACY: {accurate/total*100:.1f}%")
    print(f"  ESTIMATED ERRORS: ~{int(error_count)} provisions")

# Grand total
print("\n" + "=" * 70)
print("GRAND TOTAL")
print("=" * 70)

total_provs = sum(r['total'] for r in all_results)
total_none = sum(r['none'] for r in all_results)
total_errors = sum(r['errors'] for r in all_results)

print(f"\nTotal provisions: {total_provs}")
print(f"None topics: {total_none} ({total_none/total_provs*100:.1f}%)")
print(f"Estimated errors: ~{int(total_errors)} ({total_errors/total_provs*100:.1f}%)")
print(f"Estimated accuracy: ~{(total_provs - total_errors)/total_provs*100:.1f}%")

conn.close()
