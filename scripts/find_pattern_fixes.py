#!/usr/bin/env python3
"""
Find pattern-based fixes for remaining provisions without AI.
Look for systematic patterns that can be fixed programmatically.
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
    print("PATTERN ANALYSIS FOR REMAINING PROVISIONS")
    print("=" * 70)

    remaining = []

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

            remaining.append({
                'id': p['id'],
                'council': council,
                'part': part,
                'topic': assigned,
                'text': text,
                'scores': scores,
            })

    print(f"\nRemaining provisions: {len(remaining)}")

    # Pattern 1: Part-based reassignment
    # If a provision is in a specific part, assign based on part name
    print("\n--- PATTERN 1: PART-BASED FIXES ---")

    part_fixes = []
    part_patterns = {
        'Part 8': 'heritage',  # Heritage chapter
        'Heritage': 'heritage',
        'Part 6': 'parking',   # Parking chapter
        'Parking': 'parking',
        'Part 7': 'waste',     # Waste chapter
        'Waste': 'waste',
        'Signage': 'signage',
        'Part D': 'waste',     # Part D Section 2 is waste
    }

    for p in remaining:
        part = p['part'] or ''
        for pattern, topic in part_patterns.items():
            if pattern.lower() in part.lower() and p['topic'] != topic:
                part_fixes.append({
                    'id': p['id'],
                    'old_topic': p['topic'],
                    'new_topic': topic,
                    'reason': f"Part contains '{pattern}'",
                })
                break

    print(f"  Part-based fixes: {len(part_fixes)}")
    transitions = defaultdict(int)
    for f in part_fixes:
        transitions[(f['old_topic'], f['new_topic'])] += 1
    for (old, new), count in sorted(transitions.items(), key=lambda x: -x[1])[:10]:
        print(f"    {old} -> {new}: {count}")

    # Pattern 2: Single keyword match (be more aggressive)
    print("\n--- PATTERN 2: SINGLE KEYWORD FIXES ---")

    single_kw_fixes = []
    for p in remaining:
        if len(p['scores']) == 1:
            # Only one topic has keywords - use it
            topic = list(p['scores'].keys())[0]
            if topic != p['topic']:
                single_kw_fixes.append({
                    'id': p['id'],
                    'old_topic': p['topic'],
                    'new_topic': topic,
                    'reason': f"Single keyword match: {topic}",
                })

    print(f"  Single keyword fixes: {len(single_kw_fixes)}")
    transitions = defaultdict(int)
    for f in single_kw_fixes:
        transitions[(f['old_topic'], f['new_topic'])] += 1
    for (old, new), count in sorted(transitions.items(), key=lambda x: -x[1])[:10]:
        print(f"    {old} -> {new}: {count}")

    # Pattern 3: Short provisions -> likely headers, keep as general
    print("\n--- PATTERN 3: SHORT PROVISIONS ---")

    short_no_change = 0
    short_to_general = []
    for p in remaining:
        if len(p['text']) < 100 and not p['scores']:
            if p['topic'] != 'general':
                short_to_general.append({
                    'id': p['id'],
                    'old_topic': p['topic'],
                    'new_topic': 'general',
                    'reason': 'Short provision, no keywords',
                })
            else:
                short_no_change += 1

    print(f"  Short provisions already 'general': {short_no_change}")
    print(f"  Short provisions to change to 'general': {len(short_to_general)}")

    # Total fixable
    all_fixes = part_fixes + single_kw_fixes
    # Don't include short_to_general as that might make things worse

    print(f"\n" + "=" * 70)
    print(f"TOTAL PATTERN-BASED FIXES: {len(all_fixes)}")
    print("=" * 70)

    # Deduplicate
    seen_ids = set()
    unique_fixes = []
    for f in all_fixes:
        if f['id'] not in seen_ids:
            seen_ids.add(f['id'])
            unique_fixes.append(f)

    print(f"Unique fixes (after dedup): {len(unique_fixes)}")

    conn.close()

    return unique_fixes


if __name__ == '__main__':
    main()
