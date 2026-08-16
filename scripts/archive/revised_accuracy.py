#!/usr/bin/env python3
"""
Revised accuracy calculation based on sample verification.
"""

import os
import re
import sys
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
    print("REVISED ACCURACY CALCULATION")
    print("Based on sample verification")
    print("=" * 70)

    # Revised accuracy estimates from sample verification:
    # - Keyword match: 100%
    # - C marker: 100%
    # - Part default (Chapter E1 heritage): 100%
    # - No keywords: 75% (improved estimate from manual review)
    # - Wrong topic: 55% (improved estimate from manual review)

    results = []

    for council in ['Leichhardt', 'Ashfield', 'Marrickville']:
        keyword_match = 0
        c_marker = 0
        part_default = 0
        no_keywords = 0
        wrong_topic = 0

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
                c_marker += 1
                continue

            # Part default (Chapter E1 heritage)
            if part == 'Chapter E1' and assigned == 'heritage':
                part_default += 1
                continue

            scores = get_keyword_scores(text)

            if assigned in scores:
                keyword_match += 1
            elif not scores:
                no_keywords += 1
            else:
                wrong_topic += 1

        total = keyword_match + c_marker + part_default + no_keywords + wrong_topic

        # Calculate accuracy with revised estimates
        accurate = (
            keyword_match * 1.0 +
            c_marker * 1.0 +
            part_default * 1.0 +
            no_keywords * 0.75 +  # Revised from 0.90 to 0.75
            wrong_topic * 0.55    # Revised from 0.40-0.65 to 0.55
        )

        errors = total - accurate

        results.append({
            'council': council,
            'total': len(provisions),
            'keyword_match': keyword_match,
            'c_marker': c_marker,
            'part_default': part_default,
            'no_keywords': no_keywords,
            'wrong_topic': wrong_topic,
            'accurate': accurate,
            'errors': errors,
        })

        print(f"\n{council}:")
        print(f"  Total: {len(provisions)}")
        print(f"  Keyword match: {keyword_match} ({keyword_match/total*100:.1f}%) - 100% accurate")
        print(f"  C marker: {c_marker} ({c_marker/total*100:.1f}%) - 100% accurate")
        print(f"  Part default: {part_default} ({part_default/total*100:.1f}%) - 100% accurate")
        print(f"  No keywords: {no_keywords} ({no_keywords/total*100:.1f}%) - ~75% accurate")
        print(f"  Wrong topic: {wrong_topic} ({wrong_topic/total*100:.1f}%) - ~55% accurate")
        print(f"  ---")
        print(f"  ESTIMATED ACCURACY: {accurate/total*100:.1f}%")
        print(f"  ESTIMATED ERRORS: ~{int(errors)}")

    # Grand total
    print("\n" + "=" * 70)
    print("GRAND TOTAL (REVISED)")
    print("=" * 70)

    total_provs = sum(r['total'] for r in results)
    total_accurate = sum(r['accurate'] for r in results)
    total_errors = sum(r['errors'] for r in results)

    print(f"\nTotal provisions: {total_provs}")
    print(f"Estimated accurate: ~{int(total_accurate)}")
    print(f"Estimated errors: ~{int(total_errors)} ({total_errors/total_provs*100:.1f}%)")
    print(f"ESTIMATED ACCURACY: ~{total_accurate/total_provs*100:.1f}%")

    conn.close()


if __name__ == '__main__':
    main()
