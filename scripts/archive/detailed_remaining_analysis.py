#!/usr/bin/env python3
"""
Detailed analysis of remaining provisions to find more fixable patterns.
"""

import os
import re
import sys
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
    print("DETAILED REMAINING ANALYSIS")
    print("=" * 70)

    wrong_topic = []
    no_keywords = []

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

            if re.match(r'^C\d+', text.strip()):
                continue
            if part == 'Chapter E1' and assigned == 'heritage':
                continue

            scores = get_keyword_scores(text)

            if assigned in scores:
                continue

            record = {
                'id': p['id'],
                'council': council,
                'part': part,
                'topic': assigned,
                'text': text,
                'scores': scores,
            }

            if not scores:
                no_keywords.append(record)
            else:
                record['num_topics'] = len(scores)
                wrong_topic.append(record)

    print(f"\nWrong topic (keywords for different topic): {len(wrong_topic)}")
    print(f"No keywords: {len(no_keywords)}")

    # Analyze wrong_topic by number of competing topics
    print("\n--- WRONG TOPIC BY COMPETING TOPICS ---")
    by_num = defaultdict(list)
    for p in wrong_topic:
        by_num[p['num_topics']].append(p)

    for num, items in sorted(by_num.items()):
        print(f"\n  {num} competing topic(s): {len(items)} provisions")
        if num == 1:
            # These have exactly one keyword match - should be easy to fix
            # But we already tried this...
            by_topic = defaultdict(int)
            for item in items:
                by_topic[item['topic']] += 1
            print(f"    Assigned topics: {dict(by_topic)}")

    # Analyze no_keywords by assigned topic
    print("\n--- NO KEYWORDS BY TOPIC ---")
    by_topic = defaultdict(list)
    for p in no_keywords:
        by_topic[p['topic']].append(p)

    for topic, items in sorted(by_topic.items(), key=lambda x: -len(x[1]))[:10]:
        print(f"  {topic}: {len(items)}")
        # Sample text
        for item in items[:2]:
            text_preview = item['text'][:100].replace('\n', ' ')
            print(f"    - {text_preview}...")

    # Check if "general" no-keyword provisions are actually general
    print("\n--- CHECKING 'GENERAL' NO-KEYWORD PROVISIONS ---")
    general_no_kw = by_topic.get('general', [])
    print(f"Total 'general' with no keywords: {len(general_no_kw)}")

    # Sample some
    print("Sample:")
    for item in general_no_kw[:5]:
        text_preview = item['text'][:150].replace('\n', ' ')
        print(f"  - {text_preview}...")

    conn.close()


if __name__ == '__main__':
    main()
