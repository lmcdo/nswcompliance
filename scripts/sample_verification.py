#!/usr/bin/env python3
"""
Sample verification to get true accuracy estimate.
Randomly sample provisions from each category and manually verify.
"""

import os
import re
import sys
import random
from collections import defaultdict
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard|building\s+line',
    'height': r'\bheight|storey|floor\s+level|building\s+height|FSR',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space|bicycle',
    'solar': r'\bsolar|overshadow|sunlight|daylight',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation',
    'landscaping': r'\blandscap|garden|planting|vegetation|deep\s+soil',
    'heritage': r'\bheritage|conservation|historic|contributory',
    'trees': r'\btree|canopy|arborist',
    'fencing': r'\bfenc|fence',
    'access': r'\baccess|entry|driveway|pedestrian|mobility',
    'stormwater': r'\bstormwater|drainage|runoff|OSD',
    'waste': r'\bwaste|garbage|recycling|bin',
    'signage': r'\bsign\b|signage|advertising',
    'building_form': r'\bbulk|scale|massing|streetscape',
    'building_design': r'\bfacade|articulation|materials|architectural',
    'open_space': r'\bopen\s+space|courtyard|private\s+open',
    'flooding': r'\bflood|inundation',
    'contamination': r'\bcontaminat|remediat',
    'safety': r'\bsafety|crime|cpted|surveillance',
    'residential': r'\bresidential|dwelling|apartment|house',
    'commercial': r'\bcommercial|retail|shop\b',
    'industrial': r'\bindustrial|warehouse',
    'precinct': r'\bprecinct|town\s+centre|neighbourhood',
    'general': r'\bobjective|aim|purpose|principle',
    'energy': r'\benergy|renewable|thermal|insulation',
    'environmental': r'\benvironmental|ecology|habitat|biodiversity',
    'water': r'\bwater\s+management|rainwater|WSUD',
}


def get_keyword_scores(text):
    if not text:
        return {}
    scores = {}
    text_lower = text.lower()
    for topic, pattern in TOPIC_KEYWORDS.items():
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            scores[topic] = len(matches)
    return scores


def main():
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    print("=" * 70)
    print("SAMPLE VERIFICATION FOR ACCURACY ESTIMATE")
    print("=" * 70)

    categories = {
        'keyword_match': [],
        'c_marker': [],
        'no_keywords': [],
        'wrong_topic': [],
    }

    for council in ['Leichhardt', 'Ashfield', 'Marrickville']:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, provision_text, v2_topic, v2_dcp_part
                FROM regulatory_provisions
                WHERE document_id ILIKE %s
                  AND v2_topic IS NOT NULL
                  AND is_current = TRUE
            """, (f'%{council}%',))
            provisions = cur.fetchall()

        for p in provisions:
            text = p['provision_text'] or ''
            assigned = p['v2_topic']
            part = p['v2_dcp_part'] or ''

            # C marker
            if re.match(r'^C\d+', text.strip()):
                categories['c_marker'].append((p, council))
                continue

            # Part default (Chapter E1 heritage)
            if part == 'Chapter E1' and assigned == 'heritage':
                continue  # Skip, known to be correct

            scores = get_keyword_scores(text)

            if assigned in scores:
                categories['keyword_match'].append((p, council))
            elif not scores:
                categories['no_keywords'].append((p, council))
            else:
                categories['wrong_topic'].append((p, council, scores))

    print(f"\nCategory sizes:")
    for cat, items in categories.items():
        print(f"  {cat}: {len(items)}")

    # Sample 10 from each category
    print("\n" + "=" * 70)
    print("SAMPLE FOR MANUAL VERIFICATION")
    print("=" * 70)

    for cat, items in categories.items():
        print(f"\n--- {cat.upper()} (sample 10) ---")
        sample = random.sample(items, min(10, len(items)))

        for i, item in enumerate(sample, 1):
            if cat == 'wrong_topic':
                p, council, scores = item
                print(f"\n{i}. [{council}] ID: {p['id']}")
                print(f"   Topic: {p['v2_topic']}")
                print(f"   Part: {p['v2_dcp_part']}")
                print(f"   Keywords found: {scores}")
                text_preview = (p['provision_text'] or '')[:200].replace('\n', ' ')
                print(f"   Text: {text_preview}...")
            else:
                p, council = item
                print(f"\n{i}. [{council}] ID: {p['id']}")
                print(f"   Topic: {p['v2_topic']}")
                print(f"   Part: {p['v2_dcp_part']}")
                text_preview = (p['provision_text'] or '')[:200].replace('\n', ' ')
                print(f"   Text: {text_preview}...")

    conn.close()


if __name__ == '__main__':
    main()
