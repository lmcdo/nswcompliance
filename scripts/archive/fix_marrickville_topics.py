#!/usr/bin/env python3
"""
Fix Marrickville DCP topic issues.

Issues found:
- 164 None topics
- 35% wrong topic rate (578 provisions)
- Many 'safety' should be 'signage'
- Many 'stormwater' should be 'energy'
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
    'precinct': r'\bprecinct|town\s+centre|neighbourhood',
    'general': r'\bobjective|aim|purpose|principle',
    'energy': r'\benergy\s+efficien|renewable|thermal|insulation|NABERS|NatHERS',
    'environmental': r'\benvironmental|ecology|habitat|biodiversity',
    'wsud': r'\bWSUD|water\s+sensitive',
    'water': r'\bwater\s+management|rainwater|water\s+quality',
}


def get_best_topic(text):
    """Get best topic based on keyword scoring"""
    if not text:
        return None

    text_lower = text.lower()
    scores = {}

    for topic, pattern in TOPIC_KEYWORDS.items():
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            scores[topic] = len(matches)

    if not scores:
        return None

    return max(scores.items(), key=lambda x: x[1])[0]


def fix_marrickville(dry_run=True):
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    print("=" * 70)
    if dry_run:
        print("MARRICKVILLE FIX - DRY RUN")
    else:
        print("MARRICKVILLE FIX - APPLYING")
    print("=" * 70)

    # 1. Fix None topics
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, v2_dcp_part
            FROM regulatory_provisions
            WHERE document_id ILIKE '%%Marrickville%%'
              AND v2_topic IS NULL
              AND is_current = TRUE
        """)
        none_provs = cur.fetchall()

    print(f"\n1. NONE TOPICS: {len(none_provs)}")

    none_fixes = []
    for p in none_provs:
        topic = get_best_topic(p['provision_text'])
        if topic:
            none_fixes.append((p['id'], topic))
        else:
            # Default based on part
            part = p['v2_dcp_part'] or ''
            if 'Part 8' in part or 'Heritage' in part:
                none_fixes.append((p['id'], 'heritage'))
            else:
                none_fixes.append((p['id'], 'general'))

    print(f"   Fixes proposed: {len(none_fixes)}")

    # 2. Fix wrong topics (recalculate based on keywords)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, v2_dcp_part
            FROM regulatory_provisions
            WHERE document_id ILIKE '%%Marrickville%%'
              AND v2_topic IS NOT NULL
              AND is_current = TRUE
        """)
        all_provs = cur.fetchall()

    print(f"\n2. CHECKING {len(all_provs)} PROVISIONS FOR WRONG TOPICS")

    wrong_fixes = []
    for p in all_provs:
        text = p['provision_text'] or ''
        assigned = p['v2_topic']
        part = p['v2_dcp_part'] or ''

        # Skip Part 8 heritage (correct by definition)
        if 'Part 8' in part and assigned == 'heritage':
            continue

        # Get best topic from keywords
        best = get_best_topic(text)
        if not best:
            continue

        # Check if current assignment is wrong
        current_pattern = TOPIC_KEYWORDS.get(assigned)
        has_current = current_pattern and re.search(current_pattern, text.lower())

        if not has_current:
            # Current topic has no keywords, but another does
            scores = {}
            for topic, pattern in TOPIC_KEYWORDS.items():
                matches = re.findall(pattern, text.lower(), re.IGNORECASE)
                if matches:
                    scores[topic] = len(matches)

            if scores and assigned not in scores:
                best_topic = max(scores.items(), key=lambda x: x[1])
                if best_topic[1] >= 2:  # At least 2 keyword matches
                    wrong_fixes.append((p['id'], assigned, best_topic[0], best_topic[1]))

    print(f"   Wrong topic fixes: {len(wrong_fixes)}")

    # Show breakdown
    transitions = defaultdict(int)
    for _, old, new, _ in wrong_fixes:
        transitions[(old, new)] += 1

    print(f"\n   Top transitions:")
    for (old, new), count in sorted(transitions.items(), key=lambda x: -x[1])[:15]:
        print(f"      {old} -> {new}: {count}")

    if not dry_run:
        print("\n" + "=" * 70)
        print("APPLYING FIXES")
        print("=" * 70)

        with conn.cursor() as cur:
            # Apply None fixes
            for pid, topic in none_fixes:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id = %s
                """, (topic, pid))

            print(f"   Fixed {len(none_fixes)} None topics")

            # Apply wrong topic fixes
            for pid, _, new_topic, _ in wrong_fixes:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id = %s
                """, (new_topic, pid))

            print(f"   Fixed {len(wrong_fixes)} wrong topics")

        conn.commit()
        print("\n[OK] All fixes applied")

        # Verify
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as total,
                       COUNT(*) FILTER (WHERE v2_topic IS NULL) as none_count
                FROM regulatory_provisions
                WHERE document_id ILIKE '%%Marrickville%%'
                  AND is_current = TRUE
            """)
            r = cur.fetchone()
            print(f"\nVerification: {r['total']} total, {r['none_count']} None")
    else:
        print("\n[!] DRY RUN - No changes applied")

    conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    fix_marrickville(dry_run=args.dry_run)
