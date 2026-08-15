#!/usr/bin/env python3
"""
Fix provisions with wrong topic assignments.

Based on analysis:
- Leichhardt: 130 wrong topics
- Ashfield: 9 wrong topics

Strategy: Re-assign based on strongest keyword match.
"""

import os
import re
from collections import defaultdict
from typing import Optional, Dict, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

# IMPROVED keywords - more comprehensive
IMPROVED_KEYWORDS = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard|building\s+line|rear\s+boundary|side\s+boundary',
    'height': r'\bheight\b|storey|floor\s+level|building\s+height|maximum\s+height',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space|off-street\s+parking',
    'solar': r'\bsolar\s+access|overshadow|sunlight|daylight|northern\s+aspect',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation|visual\s+privacy',
    'landscaping': r'\blandscap|garden|planting|soft\s+landscap|deep\s+soil|greenery',
    'heritage': r'\bheritage|conservation\s+area|historic|contributory|HCA|significance',
    'trees': r'\btree\b|canopy|arborist|significant\s+tree',
    'fencing': r'\bfenc|fence|front\s+boundary\s+treatment',
    'access': r'\baccess\b|entry|driveway|pedestrian|wheelchair|universal\s+access|adaptable',
    'stormwater': r'\bstormwater|drainage|runoff|OSD|on-site\s+detention|WSUD',
    'waste': r'\bwaste|garbage|recycling|bin|refuse',
    'waste_management': r'\bwaste|garbage|recycling|bin|refuse',
    'signage': r'\bsign\b|signage',
    'building_form': r'\bbulk|scale|massing|built\s+form|streetscape|character',
    'building_design': r'\bfacade|articulation|materials|architectural|elevation|structural',
    'open_space': r'\bopen\s+space|courtyard|private\s+open|communal\s+open|POS',
    'flooding': r'\bflood|inundation|flood\s+prone|flood\s+planning|flood\s+level',
    'contamination': r'\bcontaminat|remediat|hazardous|site\s+audit',
    'safety': r'\bsafety|crime|cpted|surveillance|security',
    'roofing': r'\broof|pitch|eaves|gutter',
    'site_analysis': r'\bsite\s+analysis|context\s+analysis|site\s+context',
    'bicycle_parking': r'\bbicycle|bike\s+parking|cycling',
    'vehicle_access': r'\bvehicle\s+access|crossover|vehicular',
    'advertising': r'\badvertis|billboard|poster',
    'views': r'\bview\b|outlook|vista|view\s+sharing',
    'energy': r'\benergy\s+efficien|renewable|photovoltaic|thermal|insulation',
    'water': r'\bwater\s+management|rainwater\s+tank|water\s+sensitive|water\s+efficien',
    'residential': r'\bresidential|dwelling|apartment|house|housing|unit',
    'commercial': r'\bcommercial|retail|shop\b|business\s+premises',
    'industrial': r'\bindustrial|warehouse|factory|manufacturing',
    'mixed_use': r'\bmixed\s+use|mixed-use',
    'density': r'\bdensity|lot\s+size|minimum\s+lot|subdivision\s+pattern',
    'precinct': r'\bprecinct|town\s+centre|neighbourhood|urban\s+village',
    'sustainability': r'\bsustainab|BASIX|green\s+star|environmental\s+performance',
    'environmental': r'\benvironmental|ecology|habitat|threatened\s+species|biodiversity',
    'site_specific': r'\bsite\s+specific|masterplan|specific\s+controls',
    'general': r'\bobjective|aim\b|purpose|principle|guideline\s+applies|this\s+section',
    'food_premises': r'\bfood\s+premises|restaurant|cafe|takeaway|commercial\s+kitchen',
}


def get_db_connection():
    return psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)


def get_keyword_scores(text: str) -> Dict[str, int]:
    """Get keyword match scores for all topics"""
    if not text:
        return {}
    scores = {}
    text_lower = text.lower()
    for topic, pattern in IMPROVED_KEYWORDS.items():
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            scores[topic] = len(matches)
    return scores


def get_best_topic(text: str, current_topic: str) -> Tuple[Optional[str], str, Dict]:
    """
    Determine best topic for text.

    Returns (new_topic, reason, scores)
    """
    scores = get_keyword_scores(text)

    if not scores:
        return (None, 'no_keywords', scores)

    # Check if current topic has any matches
    current_score = scores.get(current_topic, 0)

    # Get best scoring topic
    best_topic, best_score = max(scores.items(), key=lambda x: x[1])

    # Only change if:
    # 1. Current topic has 0 matches AND
    # 2. Best alternative has 2+ matches
    if current_score == 0 and best_score >= 2:
        return (best_topic, 'wrong_topic', scores)

    # Or if best has significantly more matches (3+ more)
    if best_score >= current_score + 3 and best_topic != current_topic:
        return (best_topic, 'better_match', scores)

    return (None, 'keep_current', scores)


def fix_wrong_topics(dry_run=True):
    """Find and fix wrong topic assignments"""
    conn = get_db_connection()

    print("=" * 80)
    if dry_run:
        print("FIX WRONG TOPICS - DRY RUN")
    else:
        print("FIX WRONG TOPICS - APPLYING CHANGES")
    print("=" * 80)

    # Get all provisions with topics
    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, v2_dcp_part, document_id
            FROM regulatory_provisions
            WHERE (document_id ILIKE '%%Leichhardt%%' OR document_id ILIKE '%%Ashfield%%')
              AND v2_topic IS NOT NULL
              AND is_current = TRUE
        """)
        provisions = cur.fetchall()

    print(f"\nAnalyzing {len(provisions)} provisions...")

    # Find provisions that need fixing
    fixes = []

    for p in provisions:
        text = p['provision_text'] or ''
        current = p['v2_topic']

        # Skip C marker provisions (they're correct)
        if re.match(r'^C\d+', text.strip()):
            continue

        # Skip heritage chapter (hardcoded correctly)
        if p['v2_dcp_part'] == 'Chapter E1':
            continue

        new_topic, reason, scores = get_best_topic(text, current)

        if new_topic and new_topic != current:
            fixes.append({
                'id': p['id'],
                'part': p['v2_dcp_part'],
                'council': 'Leichhardt' if 'Leichhardt' in p['document_id'] else 'Ashfield',
                'current': current,
                'new': new_topic,
                'reason': reason,
                'scores': scores,
                'text': text[:100]
            })

    print(f"\nFound {len(fixes)} provisions to fix")

    # Summarize by council
    by_council = defaultdict(list)
    for f in fixes:
        by_council[f['council']].append(f)

    for council, items in by_council.items():
        print(f"\n{council}: {len(items)} fixes")

    # Summarize by current -> new topic
    transitions = defaultdict(int)
    for f in fixes:
        transitions[(f['current'], f['new'])] += 1

    print(f"\nTopic transitions:")
    for (old, new), count in sorted(transitions.items(), key=lambda x: -x[1])[:20]:
        print(f"  {old} -> {new}: {count}")

    # Show examples
    print(f"\nExamples:")
    for f in fixes[:10]:
        print(f"\n  ID {f['id']} ({f['part']})")
        print(f"    {f['current']} -> {f['new']} ({f['reason']})")
        print(f"    Scores: {dict(sorted(f['scores'].items(), key=lambda x: -x[1])[:5])}")
        print(f"    Text: {f['text']}...")

    if not dry_run and fixes:
        print("\n" + "=" * 80)
        print("APPLYING CHANGES")
        print("=" * 80)

        with conn.cursor() as cur:
            for f in fixes:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id = %s
                """, (f['new'], f['id']))

        conn.commit()
        print(f"\n[OK] Updated {len(fixes)} provisions")
    else:
        print("\n[!] DRY RUN - No changes applied")

    conn.close()
    return fixes


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    fix_wrong_topics(dry_run=args.dry_run)
