#!/usr/bin/env python3
"""
Second pass of manual fixes with expanded rules.
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


def determine_topic(text, current_topic, part, scores):
    """Expanded rule-based classification."""
    text_lower = text.lower()

    # Table of contents, appendix, section references -> general
    if re.search(r'appendix|\.{3,}\s*\d|^\d+\.\d+\.\d+\s', text_lower):
        return 'general' if current_topic != 'general' else None

    # "This part applies to" / "This chapter" -> general
    if re.search(r'this (part|chapter|section|dcp|development control plan) (applies|complements|provides)', text_lower):
        return 'general' if current_topic != 'general' else None

    # Site descriptions
    if re.search(r'the site (is|has|was|contains|comprises)|lot \d+ (dp|sec)|being lot', text_lower):
        return 'site_specific' if current_topic != 'site_specific' else None

    # Precinct maps/descriptions
    if re.search(r'map of precinct|precinct \d+|see (the )?attached map', text_lower):
        return 'precinct' if current_topic != 'precinct' else None

    # Sustainability objectives
    if re.search(r'sustainab|BASIX|NatHERS|NABERS|greenhouse|carbon', text_lower):
        return 'sustainability' if current_topic != 'sustainability' else None

    # Room dimensions (residential)
    if re.search(r'\d+\s*sqm|square metre|room (size|dimension)|bedroom|living room|bathroom', text_lower):
        return 'residential' if current_topic != 'residential' else None

    # Noise/acoustic -> safety or general
    if re.search(r'noise level|acoustic|decibel|dB', text_lower):
        return 'safety' if current_topic != 'safety' else None

    # Roof-related
    if re.search(r'\broof\b|roofing|eaves|gutter|parapet|dormer', text_lower):
        if 'heritage' not in text_lower and 'sign' not in text_lower:
            return 'roofing' if current_topic != 'roofing' else None

    # Food premises
    if re.search(r'food (premises|business)|restaurant|cafe|takeaway|cooking|kitchen.*commercial', text_lower):
        return 'food_premises' if current_topic != 'food_premises' else None

    # Vehicle access
    if re.search(r'vehic(le|ular) access|driveway|crossover|garage entry', text_lower):
        return 'access' if current_topic != 'access' else None

    # Bicycle parking
    if re.search(r'bicycle|bike|cycling', text_lower) and 'parking' not in current_topic:
        return 'parking' if current_topic != 'parking' else None

    # Controls/standards references -> general
    if re.search(r'performance (criteria|standard)|development standard|control\s+\d', text_lower):
        if len(text) < 200:  # Short references
            return 'general' if current_topic != 'general' else None

    # Historical/church/civic descriptions -> heritage or precinct
    if re.search(r'church|convent|civic|town hall|historical', text_lower):
        if 'heritage' not in scores:
            return 'precinct' if current_topic != 'precinct' else None

    # If single keyword match, use it
    if len(scores) == 1:
        topic = list(scores.keys())[0]
        if topic != current_topic:
            return topic

    return None


def main(dry_run=True):
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    print("=" * 70)
    if dry_run:
        print("MANUAL FIX V2 - DRY RUN")
    else:
        print("MANUAL FIX V2 - APPLYING")
    print("=" * 70)

    fixes = []
    reviewed = 0

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

            if current in scores:
                continue

            reviewed += 1
            new_topic = determine_topic(text, current, part, scores)

            if new_topic:
                fixes.append({
                    'id': p['id'],
                    'old_topic': current,
                    'new_topic': new_topic,
                    'council': council,
                })

    print(f"\nProvisions reviewed: {reviewed}")
    print(f"Fixes identified: {len(fixes)}")

    transitions = defaultdict(int)
    for f in fixes:
        transitions[(f['old_topic'], f['new_topic'])] += 1

    print("\nTransitions:")
    for (old, new), count in sorted(transitions.items(), key=lambda x: -x[1])[:20]:
        print(f"  {old} -> {new}: {count}")

    if not dry_run and fixes:
        print("\nApplying fixes...")
        with conn.cursor() as cur:
            for fix in fixes:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id = %s
                """, (fix['new_topic'], fix['id']))
        conn.commit()
        print(f"[OK] Applied {len(fixes)} fixes")
    else:
        print("\n[!] DRY RUN - No changes applied")

    conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    main(dry_run=args.dry_run)
