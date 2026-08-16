#!/usr/bin/env python3
"""
Diagnostic script for Ashfield DCP topic assignment
"""

import os
import re
from collections import defaultdict
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

# Topic keywords for analysis
TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard',
    'height': r'\bheight|storey|floor\s+level|building\s+height|FSR',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space',
    'solar': r'\bsolar|overshadow|sunlight|daylight',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation',
    'landscaping': r'\blandscap|garden|planting|vegetation',
    'heritage': r'\bheritage|conservation|historic|contributory',
    'trees': r'\btree|canopy|arborist',
    'fencing': r'\bfenc|fence|front\s+boundary\s+treatment',
    'access': r'\baccess|entry|driveway|pedestrian',
    'stormwater': r'\bstormwater|drainage|runoff|OSD',
    'waste': r'\bwaste|garbage|recycling|bin',
    'signage': r'\bsign|signage',
    'building_form': r'\bbulk|scale|massing|form|character|streetscape',
    'building_design': r'\bdesign|facade|articulation|materials|architectural',
    'open_space': r'\bopen\s+space|courtyard|private\s+open',
    'flooding': r'\bflood|inundation',
    'contamination': r'\bcontaminat|remediat',
    'safety': r'\bsafety|crime|cpted|surveillance',
    'residential': r'\bresidential|dwelling|apartment',
    'commercial': r'\bcommercial|retail|shop',
    'industrial': r'\bindustrial|warehouse',
    'mixed_use': r'\bmixed\s+use',
    'subdivision': r'\bsubdivision|lot\s+size',
    'general': r'\bobjective|purpose|aim',
}


def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def find_keyword_matches(text: str) -> dict:
    if not text:
        return {}
    text_lower = text.lower()
    matches = {}
    for topic, pattern in TOPIC_KEYWORDS.items():
        found = re.findall(pattern, text_lower, re.IGNORECASE)
        if found:
            matches[topic] = len(found)
    return matches


def diagnose_ashfield(conn):
    """Full diagnostic of Ashfield DCP"""
    print("=" * 80)
    print("ASHFIELD DCP TOPIC ASSIGNMENT DIAGNOSTIC")
    print("=" * 80)

    with conn.cursor() as cur:
        # Get overall counts by part
        cur.execute("""
            SELECT v2_dcp_part, COUNT(*) as total,
                   COUNT(*) FILTER (WHERE v2_topic IS NULL) as none_count,
                   COUNT(DISTINCT v2_topic) as unique_topics
            FROM regulatory_provisions
            WHERE document_id ILIKE '%%Ashfield%%'
              AND is_current = TRUE
            GROUP BY v2_dcp_part
            ORDER BY v2_dcp_part
        """)
        parts = cur.fetchall()

    print(f"\nOverview by DCP Part:")
    print("-" * 70)
    print(f"{'Part':<25} {'Total':>8} {'None':>8} {'None%':>8} {'Topics':>8}")
    print("-" * 70)

    total_provisions = 0
    total_none = 0

    for p in parts:
        total_provisions += p['total']
        total_none += p['none_count']
        none_pct = p['none_count'] / p['total'] * 100 if p['total'] > 0 else 0
        print(f"{p['v2_dcp_part'] or 'unknown':<25} {p['total']:>8} {p['none_count']:>8} {none_pct:>7.1f}% {p['unique_topics']:>8}")

    print("-" * 70)
    print(f"{'TOTAL':<25} {total_provisions:>8} {total_none:>8} {total_none/total_provisions*100:>7.1f}%")

    # Analyze each major part
    for part_row in parts:
        part = part_row['v2_dcp_part']
        if not part or part == 'unknown':
            continue
        diagnose_part(conn, part)

    return parts


def diagnose_part(conn, part: str):
    """Diagnose a specific part"""
    print(f"\n{'='*80}")
    print(f"{part} - DETAILED ANALYSIS")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE '%%Ashfield%%'
              AND v2_dcp_part = %s
              AND is_current = TRUE
            ORDER BY pdf_page, id
        """, (part,))
        provisions = cur.fetchall()

    print(f"\nTotal provisions: {len(provisions)}")

    # Topic distribution
    topics = defaultdict(int)
    for p in provisions:
        topics[p['v2_topic'] or 'None'] += 1

    print(f"\nTopic distribution ({len(topics)} unique):")
    for topic, count in sorted(topics.items(), key=lambda x: -x[1])[:15]:
        pct = count / len(provisions) * 100
        print(f"   {topic}: {count} ({pct:.1f}%)")

    # Check for structural markers
    print(f"\nStructural marker check:")
    markers = defaultdict(int)
    for p in provisions:
        text = (p['provision_text'] or '').strip()
        if re.match(r'^[A-Z]\d+', text):
            markers['Letter+Number (e.g., A1, B2)'] += 1
        elif re.match(r'^\d+\.\d+', text):
            markers['Section number (e.g., 1.2)'] += 1
        elif re.match(r'^O\d+', text, re.IGNORECASE):
            markers['Objective (O1, O2)'] += 1
        elif re.match(r'^C\d+', text, re.IGNORECASE):
            markers['Control (C1, C2)'] += 1
        elif re.match(r'^P\d+', text, re.IGNORECASE):
            markers['Performance (P1, P2)'] += 1

    if markers:
        for marker_type, count in markers.items():
            print(f"   {marker_type}: {count}")
    else:
        print("   No structural markers found")

    # Keyword match analysis for None topics
    none_provisions = [p for p in provisions if p['v2_topic'] is None]
    if none_provisions:
        print(f"\nNone topic analysis ({len(none_provisions)} provisions):")

        could_assign = 0
        topic_suggestions = defaultdict(int)

        for p in none_provisions:
            matches = find_keyword_matches(p['provision_text'])
            if matches:
                could_assign += 1
                best_topic = max(matches.items(), key=lambda x: x[1])[0]
                topic_suggestions[best_topic] += 1

        print(f"   Could assign via keywords: {could_assign}/{len(none_provisions)}")
        if topic_suggestions:
            print(f"   Suggested topics:")
            for topic, count in sorted(topic_suggestions.items(), key=lambda x: -x[1])[:10]:
                print(f"      {topic}: {count}")

        # Show samples
        print(f"\n   Sample None provisions:")
        for p in none_provisions[:5]:
            text = (p['provision_text'] or '')[:100].replace('\n', ' ')
            matches = find_keyword_matches(p['provision_text'])
            print(f"\n   ID {p['id']} (page {p['pdf_page']})")
            print(f"      Text: {text}...")
            print(f"      Keywords: {matches if matches else 'None found'}")

    # Keyword mismatch analysis
    assigned_provisions = [p for p in provisions if p['v2_topic'] is not None]
    if assigned_provisions:
        good_match = 0
        mismatch = 0
        mismatch_examples = []

        for p in assigned_provisions:
            matches = find_keyword_matches(p['provision_text'])
            assigned = p['v2_topic']

            if assigned in matches:
                good_match += 1
            elif matches:
                mismatch += 1
                if len(mismatch_examples) < 5:
                    mismatch_examples.append({
                        'id': p['id'],
                        'assigned': assigned,
                        'matches': matches,
                        'text': (p['provision_text'] or '')[:80]
                    })

        print(f"\nKeyword match analysis (assigned provisions):")
        print(f"   Good match: {good_match}/{len(assigned_provisions)} ({good_match/len(assigned_provisions)*100:.1f}%)")
        print(f"   Mismatch: {mismatch}/{len(assigned_provisions)} ({mismatch/len(assigned_provisions)*100:.1f}%)")

        if mismatch_examples:
            print(f"\n   Mismatch examples:")
            for ex in mismatch_examples[:3]:
                print(f"\n   ID {ex['id']}: assigned '{ex['assigned']}'")
                print(f"      Keywords found: {ex['matches']}")
                print(f"      Text: {ex['text']}...")


def main():
    conn = None
    try:
        conn = get_db_connection()
        print("Connected to database\n")
        diagnose_ashfield(conn)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    main()
