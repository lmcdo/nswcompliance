#!/usr/bin/env python3
"""
Extract samples for manual review to determine TRUE accuracy.

Categories to review:
1. "No keywords found" - Are these correctly assigned?
2. "Wrong topic" - Are these actually wrong?
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


def main():
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    # Get Leichhardt provisions (excluding C markers and Chapter E1)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, v2_dcp_part
            FROM regulatory_provisions
            WHERE document_id ILIKE '%%Leichhardt%%'
              AND v2_topic IS NOT NULL
              AND is_current = TRUE
            ORDER BY RANDOM()
        """)
        provisions = cur.fetchall()

    # Categorize
    no_keywords = []
    wrong_topic = []

    for p in provisions:
        text = p['provision_text'] or ''
        assigned = p['v2_topic']

        # Skip C markers (we know these are correct)
        if re.match(r'^C\d+', text.strip()):
            continue

        matches = get_keyword_matches(text)

        if not matches:
            no_keywords.append(p)
        elif assigned not in matches and matches:
            wrong_topic.append({
                **p,
                'matches': matches
            })

    print("=" * 80)
    print("MANUAL REVIEW: NO KEYWORDS FOUND")
    print("=" * 80)
    print(f"\nTotal: {len(no_keywords)} provisions")
    print("\nSample 20 for review (is the assigned topic CORRECT?):\n")

    for i, p in enumerate(no_keywords[:20], 1):
        text = (p['provision_text'] or '')[:200].replace('\n', ' ')
        print(f"{i}. ID {p['id']} | Part: {p['v2_dcp_part']} | Topic: {p['v2_topic']}")
        print(f"   Text: {text}")
        print(f"   CORRECT? [ ] Yes  [ ] No -> Should be: _______")
        print()

    print("\n" + "=" * 80)
    print("MANUAL REVIEW: WRONG TOPIC (keyword mismatch)")
    print("=" * 80)
    print(f"\nTotal: {len(wrong_topic)} provisions")
    print("\nSample 20 for review:\n")

    for i, p in enumerate(wrong_topic[:20], 1):
        text = (p['provision_text'] or '')[:200].replace('\n', ' ')
        print(f"{i}. ID {p['id']} | Part: {p['v2_dcp_part']}")
        print(f"   Assigned: {p['v2_topic']} | Keywords found: {p['matches']}")
        print(f"   Text: {text}")
        print(f"   VERDICT: [ ] Keep '{p['v2_topic']}'  [ ] Change to: _______")
        print()

    conn.close()


if __name__ == '__main__':
    main()
