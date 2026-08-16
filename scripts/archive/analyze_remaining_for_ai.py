#!/usr/bin/env python3
"""
Analyze remaining errors to prepare for AI classification.
These are provisions that keyword matching can't fix.
"""

import os
import re
import sys
import json
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
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space',
    'solar': r'\bsolar|overshadow|sunlight|daylight',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation',
    'landscaping': r'\blandscap|garden|planting|vegetation|deep\s+soil',
    'heritage': r'\bheritage|conservation|historic|contributory',
    'trees': r'\btree|canopy|arborist',
    'fencing': r'\bfenc|fence',
    'access': r'\baccess|entry|driveway|pedestrian|mobility',
    'stormwater': r'\bstormwater|drainage|runoff|OSD',
    'waste': r'\bwaste|garbage|recycling|bin',
    'signage': r'\bsign\b|signage|advertising\s+structure',
    'building_form': r'\bbulk|scale|massing|streetscape',
    'building_design': r'\bfacade|articulation|materials|architectural',
    'open_space': r'\bopen\s+space|courtyard|private\s+open',
    'flooding': r'\bflood|inundation',
    'contamination': r'\bcontaminat|remediat',
    'safety': r'\bsafety|crime|cpted|surveillance',
    'residential': r'\bresidential|dwelling|apartment|house',
    'commercial': r'\bcommercial|retail|shop\b',
    'industrial': r'\bindustrial|warehouse',
    'precinct': r'\bprecinct|town\s+centre|neighbourhood|character\s+area',
    'general': r'\bobjective|aim|purpose|principle',
    'energy': r'\benergy\s+efficien|renewable|thermal|insulation|NABERS|NatHERS',
    'environmental': r'\benvironmental|ecology|habitat|biodiversity',
    'water': r'\bwater\s+management|rainwater|water\s+quality|WSUD|water\s+sensitive',
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

    wrong_topic_all = []
    no_keywords_all = []

    for council in ['Leichhardt', 'Ashfield', 'Marrickville']:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, provision_text, v2_topic, v2_dcp_part, document_id
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

            # Skip C markers and part defaults
            if re.match(r'^C\d+', text.strip()):
                continue
            if part == 'Chapter E1' and assigned == 'heritage':
                continue

            scores = get_keyword_scores(text)

            if assigned in scores:
                continue  # Good

            record = {
                'id': p['id'],
                'council': council,
                'part': part,
                'topic': assigned,
                'text': text[:500],  # Truncate for analysis
                'keyword_matches': scores,
            }

            if not scores:
                no_keywords_all.append(record)
            else:
                record['best_match'] = max(scores.items(), key=lambda x: x[1])
                wrong_topic_all.append(record)

    print("=" * 70)
    print("REMAINING ERRORS - ANALYSIS FOR AI CLASSIFICATION")
    print("=" * 70)

    print(f"\nWrong topic (has keywords for different topic): {len(wrong_topic_all)}")
    print(f"No keywords (no keywords for any topic): {len(no_keywords_all)}")
    print(f"Total needing AI classification: {len(wrong_topic_all) + len(no_keywords_all)}")

    # Breakdown by topic
    print("\n--- WRONG TOPIC BY ASSIGNED ---")
    by_assigned = defaultdict(list)
    for p in wrong_topic_all:
        by_assigned[p['topic']].append(p)

    for topic, items in sorted(by_assigned.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  {topic}: {len(items)}")

    print("\n--- NO KEYWORDS BY ASSIGNED ---")
    by_assigned2 = defaultdict(list)
    for p in no_keywords_all:
        by_assigned2[p['topic']].append(p)

    for topic, items in sorted(by_assigned2.items(), key=lambda x: -len(x[1]))[:15]:
        print(f"  {topic}: {len(items)}")

    # Save for AI processing
    output = {
        'wrong_topic': wrong_topic_all,
        'no_keywords': no_keywords_all,
        'total': len(wrong_topic_all) + len(no_keywords_all),
    }

    output_path = pathlib.Path(__file__).parent / 'remaining_errors_for_ai.json'
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to: {output_path}")

    # Estimate AI cost
    total_chars = sum(len(p['text']) for p in wrong_topic_all + no_keywords_all)
    estimated_tokens = total_chars / 4
    haiku_cost = (estimated_tokens / 1_000_000) * 0.25 + (len(wrong_topic_all) + len(no_keywords_all)) * 50 / 1_000_000 * 1.25
    print(f"\nEstimated AI cost (Haiku): ~${haiku_cost:.2f}")

    conn.close()


if __name__ == '__main__':
    main()
