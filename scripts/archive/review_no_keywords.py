#!/usr/bin/env python3
"""Review no-keyword provisions grouped by topic."""
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
    print("NO KEYWORDS PROVISIONS BY TOPIC")
    print("=" * 70)

    no_kw = defaultdict(list)

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
            current = p['v2_topic']
            part = p['v2_dcp_part'] or ''

            if re.match(r'^C\d+', text.strip()):
                continue
            if part == 'Chapter E1' and current == 'heritage':
                continue

            scores = get_keyword_scores(text)

            if not scores and current not in scores:
                no_kw[current].append({
                    'id': p['id'],
                    'council': council,
                    'part': part,
                    'text': text,
                })

    # Show by topic
    for topic in sorted(no_kw.keys(), key=lambda x: -len(no_kw[x])):
        items = no_kw[topic]
        print(f"\n{topic}: {len(items)} provisions")
        # Sample 5
        for p in items[:5]:
            text_preview = p['text'][:150].replace('\n', ' ')
            print(f"  [{p['council']}] ID {p['id']}: {text_preview}...")

    conn.close()


if __name__ == '__main__':
    main()
