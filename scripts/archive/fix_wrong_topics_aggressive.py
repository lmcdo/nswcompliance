#!/usr/bin/env python3
"""
Aggressive fix for wrong topics to push accuracy toward 98%.

Fix criteria:
1. Assigned topic has 0 keyword matches
2. Another topic has 2+ keyword matches
3. This is lower confidence than 3+ matches, but still reasonable
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

# Comprehensive keyword patterns
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
    """Get keyword match counts for all topics"""
    if not text:
        return {}
    scores = {}
    text_lower = text.lower()
    for topic, pattern in TOPIC_KEYWORDS.items():
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            scores[topic] = len(matches)
    return scores


def fix_all_councils(dry_run=True, min_matches=2):
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    print("=" * 70)
    if dry_run:
        print(f"WRONG TOPIC FIX (min {min_matches} matches) - DRY RUN")
    else:
        print(f"WRONG TOPIC FIX (min {min_matches} matches) - APPLYING")
    print("=" * 70)

    all_fixes = []

    for council in ['Leichhardt', 'Ashfield', 'Marrickville']:
        print(f"\n--- {council} ---")

        with conn.cursor() as cur:
            cur.execute("""
                SELECT id, provision_text, v2_topic, v2_dcp_part
                FROM regulatory_provisions
                WHERE document_id ILIKE %s
                  AND v2_topic IS NOT NULL
                  AND is_current = TRUE
            """, (f'%{council}%',))
            provisions = cur.fetchall()

        council_fixes = []

        for p in provisions:
            text = p['provision_text'] or ''
            assigned = p['v2_topic']
            part = p['v2_dcp_part'] or ''

            # Skip C markers (Leichhardt) and Chapter E1 heritage (Ashfield)
            if re.match(r'^C\d+', text.strip()):
                continue
            if part == 'Chapter E1' and assigned == 'heritage':
                continue

            scores = get_keyword_scores(text)

            # Check if assigned topic has keywords
            if assigned in scores:
                continue  # Has keywords for assigned topic - keep

            if not scores:
                continue  # No keywords found - can't fix automatically

            # Find best alternative
            best_topic, best_count = max(scores.items(), key=lambda x: x[1])

            # Fix if meets minimum threshold
            if best_count >= min_matches:
                council_fixes.append({
                    'id': p['id'],
                    'old_topic': assigned,
                    'new_topic': best_topic,
                    'confidence': best_count,
                    'council': council,
                })

        print(f"  Provisions checked: {len(provisions)}")
        print(f"  Fixes (>={min_matches} keyword matches): {len(council_fixes)}")

        # Show breakdown
        transitions = defaultdict(int)
        for f in council_fixes:
            transitions[(f['old_topic'], f['new_topic'])] += 1

        print(f"  Top transitions:")
        for (old, new), count in sorted(transitions.items(), key=lambda x: -x[1])[:10]:
            print(f"    {old} -> {new}: {count}")

        all_fixes.extend(council_fixes)

    print(f"\n" + "=" * 70)
    print(f"TOTAL FIXES: {len(all_fixes)}")
    print("=" * 70)

    # Confidence breakdown
    conf_2 = sum(1 for f in all_fixes if f['confidence'] == 2)
    conf_3plus = sum(1 for f in all_fixes if f['confidence'] >= 3)
    print(f"\nBy confidence:")
    print(f"  2 matches: {conf_2}")
    print(f"  3+ matches: {conf_3plus}")

    if not dry_run and all_fixes:
        print("\nApplying fixes...")
        with conn.cursor() as cur:
            for fix in all_fixes:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id = %s
                """, (fix['new_topic'], fix['id']))

        conn.commit()
        print(f"[OK] Applied {len(all_fixes)} fixes")
    else:
        print("\n[!] DRY RUN - No changes applied")

    conn.close()
    return all_fixes


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--min-matches', type=int, default=2)
    args = parser.parse_args()
    fix_all_councils(dry_run=args.dry_run, min_matches=args.min_matches)
