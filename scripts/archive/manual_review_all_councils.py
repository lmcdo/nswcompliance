#!/usr/bin/env python3
"""
Manual review samples for all councils: Ashfield, Marrickville, Leichhardt
"""

import os
import re
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard',
    'height': r'\bheight|storey|floor\s+level|building\s+height',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space',
    'solar': r'\bsolar|overshadow|sunlight|daylight',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation',
    'landscaping': r'\blandscap|garden|planting|vegetation',
    'heritage': r'\bheritage|conservation|historic',
    'trees': r'\btree|canopy|vegetation',
    'fencing': r'\bfenc|fence',
    'access': r'\baccess|entry|driveway|pedestrian',
    'stormwater': r'\bstormwater|drainage|runoff',
    'waste': r'\bwaste|garbage|recycling|bin',
    'signage': r'\bsign|signage|advertising',
    'building_form': r'\bbulk|scale|massing|form|character',
    'building_design': r'\bdesign|facade|articulation|materials',
    'open_space': r'\bopen\s+space|courtyard|private\s+open',
    'flooding': r'\bflood|inundation',
    'contamination': r'\bcontaminat|remediat',
    'safety': r'\bsafety|crime|cpted|surveillance',
    'residential': r'\bresidential|dwelling|apartment',
    'commercial': r'\bcommercial|retail|shop',
    'industrial': r'\bindustrial|warehouse',
    'precinct': r'\bprecinct|town\s+centre|neighbourhood',
    'general': r'\bobjective|aim|purpose|principle',
    'water': r'\bwater|rainwater|wsud',
    'environmental': r'\benvironmental|ecology|habitat',
    'sustainability': r'\bsustainab|BASIX',
}


def get_keyword_matches(text):
    if not text:
        return {}
    matches = {}
    text_lower = text.lower()
    for topic, pattern in TOPIC_KEYWORDS.items():
        found = re.findall(pattern, text_lower, re.IGNORECASE)
        if found:
            matches[topic] = len(found)
    return matches


def analyze_council(conn, council_name):
    print("\n" + "=" * 80)
    print(f"{council_name.upper()} - QUALITY ANALYSIS")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, v2_dcp_part
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
              AND v2_topic IS NOT NULL
              AND is_current = TRUE
            ORDER BY RANDOM()
        """, (f'%{council_name}%',))
        provisions = cur.fetchall()

    print(f"\nTotal provisions with topics: {len(provisions)}")

    # Categorize
    keyword_match = []
    c_marker = []
    part_default = []  # Chapter E1 heritage
    no_keywords = []
    wrong_topic = []

    for p in provisions:
        text = p['provision_text'] or ''
        assigned = p['v2_topic']
        part = p['v2_dcp_part'] or ''

        # C marker check
        if re.match(r'^C\d+', text.strip()):
            c_marker.append(p)
            continue

        # Part default (Chapter E1 = heritage)
        if part == 'Chapter E1' and assigned == 'heritage':
            part_default.append(p)
            continue

        matches = get_keyword_matches(text)

        if assigned in matches:
            keyword_match.append(p)
        elif not matches:
            no_keywords.append(p)
        else:
            wrong_topic.append({**p, 'matches': matches})

    total = len(provisions)
    print(f"\nCategory breakdown:")
    print(f"  Keyword match:    {len(keyword_match):>5} ({len(keyword_match)/total*100:>5.1f}%)")
    print(f"  C marker:         {len(c_marker):>5} ({len(c_marker)/total*100:>5.1f}%)")
    print(f"  Part default:     {len(part_default):>5} ({len(part_default)/total*100:>5.1f}%)")
    print(f"  No keywords:      {len(no_keywords):>5} ({len(no_keywords)/total*100:>5.1f}%)")
    print(f"  Wrong topic:      {len(wrong_topic):>5} ({len(wrong_topic)/total*100:>5.1f}%)")

    # Sample no_keywords for review
    print(f"\n--- NO KEYWORDS FOUND: Sample 10 ---")
    for i, p in enumerate(no_keywords[:10], 1):
        text = (p['provision_text'] or '')[:120].replace('\n', ' ')
        print(f"\n{i}. ID {p['id']} | {p['v2_dcp_part']} | Topic: {p['v2_topic']}")
        print(f"   {text}...")

    # Sample wrong_topic for review
    print(f"\n--- WRONG TOPIC: Sample 10 ---")
    for i, p in enumerate(wrong_topic[:10], 1):
        text = (p['provision_text'] or '')[:120].replace('\n', ' ')
        print(f"\n{i}. ID {p['id']} | {p['v2_dcp_part']}")
        print(f"   Assigned: {p['v2_topic']} | Found: {p['matches']}")
        print(f"   {text}...")

    return {
        'total': total,
        'keyword_match': len(keyword_match),
        'c_marker': len(c_marker),
        'part_default': len(part_default),
        'no_keywords': len(no_keywords),
        'wrong_topic': len(wrong_topic),
        'no_keywords_list': no_keywords,
        'wrong_topic_list': wrong_topic,
    }


def main():
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    results = {}
    for council in ['Ashfield', 'Marrickville']:
        results[council] = analyze_council(conn, council)

    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY - ESTIMATED TRUE ACCURACY")
    print("=" * 80)

    for council, r in results.items():
        # Assume: keyword_match=100%, c_marker=100%, part_default=100%
        # no_keywords=95%, wrong_topic=65% (from Leichhardt manual review)
        accurate = (
            r['keyword_match'] * 1.0 +
            r['c_marker'] * 1.0 +
            r['part_default'] * 1.0 +
            r['no_keywords'] * 0.95 +
            r['wrong_topic'] * 0.65
        )
        pct = accurate / r['total'] * 100

        print(f"\n{council}:")
        print(f"  Total: {r['total']}")
        print(f"  Estimated accurate: {accurate:.0f} ({pct:.1f}%)")
        print(f"  Estimated errors: {r['total'] - accurate:.0f} ({100-pct:.1f}%)")

    conn.close()


if __name__ == '__main__':
    main()
