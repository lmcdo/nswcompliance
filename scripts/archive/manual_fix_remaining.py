#!/usr/bin/env python3
"""
Manual review and fix of remaining provisions.
Analyze each provision and assign correct topic.
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
    """
    Determine the correct topic based on text content analysis.
    Returns new topic or None if current is correct.
    """
    text_lower = text.lower()

    # Rule-based classification

    # Table of contents / appendix references -> general
    if re.search(r'appendix|table of contents|\.{3,}|\d+\.\d+\.\d+', text_lower):
        return 'general' if current_topic != 'general' else None

    # Site descriptions -> site_specific
    if re.search(r'the site is known as|the site has an area|lot \d+ dp|being lot', text_lower):
        return 'site_specific' if current_topic != 'site_specific' else None

    # Roof-related -> roofing
    if re.search(r'\broof\b|roofing|eaves|gutter|parapet', text_lower) and 'heritage' not in text_lower:
        return 'roofing' if current_topic != 'roofing' else None

    # View/outlook -> views
    if re.search(r'\bview\b|vista|outlook|sightline', text_lower):
        return 'views' if current_topic != 'views' else None

    # Food premises -> food_premises
    if re.search(r'food premises|restaurant|cafe|takeaway|eating establishment', text_lower):
        return 'food_premises' if current_topic != 'food_premises' else None

    # Density/subdivision -> density
    if re.search(r'\bdensity\b|lot size|subdivision|minimum lot', text_lower):
        return 'density' if current_topic != 'density' else None

    # Mixed use -> mixed_use
    if re.search(r'mixed.use|mixed-use', text_lower):
        return 'mixed_use' if current_topic != 'mixed_use' else None

    # Contamination references in signage provisions
    if current_topic == 'signage' and 'contamina' in text_lower:
        return 'contamination'

    # Parking references in signage provisions
    if current_topic == 'signage' and 'parking' in text_lower and 'sign' not in text_lower:
        return 'parking'

    # Water chapter provisions
    if 'Part E' in part and current_topic == 'water':
        return None  # Keep as water

    # Building form for character/streetscape
    if re.search(r'character|streetscape|built form|building envelope', text_lower):
        if current_topic not in ['building_form', 'precinct', 'heritage']:
            return 'building_form'

    # If has single strong keyword match, use it
    if len(scores) == 1:
        topic = list(scores.keys())[0]
        if topic != current_topic:
            return topic

    # If current topic has no keywords but another does, consider change
    if scores and current_topic not in scores:
        # Pick the one with most matches
        best = max(scores.items(), key=lambda x: x[1])
        if best[1] >= 2:
            return best[0]

    return None  # Keep current


def main(dry_run=True):
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    print("=" * 70)
    if dry_run:
        print("MANUAL FIX REMAINING - DRY RUN")
    else:
        print("MANUAL FIX REMAINING - APPLYING")
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

            # Skip C markers and part defaults
            if re.match(r'^C\d+', text.strip()):
                continue
            if part == 'Chapter E1' and current == 'heritage':
                continue

            scores = get_keyword_scores(text)

            # Only review provisions without keyword match
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

    # Show transitions
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
