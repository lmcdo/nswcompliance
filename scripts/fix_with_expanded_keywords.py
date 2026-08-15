#!/usr/bin/env python3
"""
Fix remaining errors with expanded keyword patterns.
More aggressive keyword matching for edge cases.
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

# EXPANDED keyword patterns - more aggressive
TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard|building\s+line|side\s+boundary|rear\s+boundary|front\s+boundary',
    'height': r'\bheight|storey|floor\s+level|building\s+height|FSR|floor\s+space|gross\s+floor',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space|bicycle|cycling|motorcycle',
    'solar': r'\bsolar|overshadow|sunlight|daylight|north\s+facing|sun\s+access',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation|visual\s+privacy',
    'landscaping': r'\blandscap|garden|planting|vegetation|deep\s+soil|soft\s+landscap',
    'heritage': r'\bheritage|conservation|historic|contributory|character\s+area|historic\s+character',
    'trees': r'\btree|canopy|arborist|vegetation\s+management',
    'fencing': r'\bfenc|fence|boundary\s+treatment',
    'access': r'\baccess|entry|driveway|pedestrian|mobility|wheelchair|ramp|disabled',
    'stormwater': r'\bstormwater|drainage|runoff|OSD|on\-site\s+detention',
    'waste': r'\bwaste|garbage|recycling|bin|refuse|rubbish',
    'signage': r'\bsign\b|signage|advertising\s+structure|illuminated|neon',
    'building_form': r'\bbulk|scale|massing|streetscape|built\s+form|building\s+envelope',
    'building_design': r'\bfacade|articulation|materials|architectural|external\s+appearance|finish',
    'open_space': r'\bopen\s+space|courtyard|private\s+open|communal\s+open|recreation',
    'flooding': r'\bflood|inundation|flood\s+planning',
    'contamination': r'\bcontaminat|remediat|hazardous|asbestos',
    'safety': r'\bsafety|crime|cpted|surveillance|lighting\s+security',
    'residential': r'\bresidential|dwelling|apartment|house|dual\s+occupancy|multi\s+dwelling|terrace',
    'commercial': r'\bcommercial|retail|shop\b|business\s+premises',
    'industrial': r'\bindustrial|warehouse|manufacturing|factory',
    'precinct': r'\bprecinct|town\s+centre|neighbourhood|character\s+area|locality|suburban',
    'general': r'\bobjective|aim|purpose|principle|context|background|introduction',
    'energy': r'\benergy|renewable|thermal|insulation|NABERS|NatHERS|BASIX|greenhouse',
    'environmental': r'\benvironmental|ecology|habitat|biodiversity|flora|fauna|native',
    'water': r'\bwater\s+management|rainwater|water\s+quality|WSUD|water\s+sensitive|water\s+conservation',
    # Add missing topics
    'views': r'\bview|vista|outlook|sightline',
    'mixed_use': r'\bmixed\s+use|mixed-use|commercial\s+residential',
    'density': r'\bdensity|lot\s+size|subdivision|minimum\s+lot',
    'food_premises': r'\bfood\s+premises|restaurant|cafe|takeaway|eating',
    'roofing': r'\broof|roofing|eaves|gutters',
    'site_specific': r'\bsite\s+specific|special\s+provisions|clause\s+\d',
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


def fix_all_councils(dry_run=True):
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    print("=" * 70)
    if dry_run:
        print("EXPANDED KEYWORD FIX - DRY RUN")
    else:
        print("EXPANDED KEYWORD FIX - APPLYING")
    print("=" * 70)

    all_fixes = []
    still_wrong = 0
    still_no_kw = 0

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

            # Skip C markers and part defaults
            if re.match(r'^C\d+', text.strip()):
                continue
            if part == 'Chapter E1' and assigned == 'heritage':
                continue

            scores = get_keyword_scores(text)

            if assigned in scores:
                continue  # Good - has keywords for assigned topic

            if not scores:
                still_no_kw += 1
                continue

            # Find best alternative (only fix if 2+ matches)
            best_topic, best_count = max(scores.items(), key=lambda x: x[1])
            if best_count >= 2:
                council_fixes.append({
                    'id': p['id'],
                    'old_topic': assigned,
                    'new_topic': best_topic,
                    'confidence': best_count,
                })
            else:
                still_wrong += 1

        print(f"  Fixes: {len(council_fixes)}")
        all_fixes.extend(council_fixes)

        # Show transitions
        transitions = defaultdict(int)
        for f in council_fixes:
            transitions[(f['old_topic'], f['new_topic'])] += 1
        for (old, new), count in sorted(transitions.items(), key=lambda x: -x[1])[:5]:
            print(f"    {old} -> {new}: {count}")

    print(f"\n" + "=" * 70)
    print(f"TOTAL FIXES: {len(all_fixes)}")
    print(f"Still wrong (1 kw match): {still_wrong}")
    print(f"Still no keywords: {still_no_kw}")
    print(f"Remaining for AI: {still_wrong + still_no_kw}")
    print("=" * 70)

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


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    fix_all_councils(dry_run=args.dry_run)
