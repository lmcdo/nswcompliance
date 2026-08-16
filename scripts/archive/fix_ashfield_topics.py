#!/usr/bin/env python3
"""
Fix Ashfield DCP provisions with None topic

Based on diagnostic:
- Chapter A: 38 None (21.8%)
- Chapter C: 41 None (19.2%)
- Chapter D: 83 None (41.9%)
- Total: 165 None topics

Usage:
    python scripts/fix_ashfield_topics.py --dry-run
    python scripts/fix_ashfield_topics.py
"""

import os
import re
from collections import defaultdict
from typing import Optional, Tuple

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

# Expanded keywords for Ashfield
TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard|building\s+line',
    'height': r'\bheight|storey|floor\s+level|building\s+height|FSR|floor\s+space\s+ratio',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space|off-street',
    'solar': r'\bsolar|overshadow|sunlight|daylight|northern\s+aspect',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation|visual\s+privacy',
    'landscaping': r'\blandscap|garden|planting|vegetation|planted|soft\s+landscap|deep\s+soil',
    'heritage': r'\bheritage|conservation|historic|contributory|HCA',
    'trees': r'\btree|canopy|arborist|significant\s+tree',
    'fencing': r'\bfenc|fence|front\s+boundary\s+treatment',
    'access': r'\baccess|entry|driveway|pedestrian|wheelchair|universal\s+access',
    'stormwater': r'\bstormwater|drainage|runoff|OSD|on-site\s+detention|WSUD',
    'waste': r'\bwaste|garbage|recycling|bin|refuse',
    'signage': r'\bsign|signage|advertising',
    'building_form': r'\bbulk|scale|massing|form|character|streetscape|built\s+form',
    'building_design': r'\bdesign|facade|articulation|materials|architectural|elevation',
    'open_space': r'\bopen\s+space|courtyard|private\s+open|communal\s+open|POS',
    'flooding': r'\bflood|inundation|flood\s+prone',
    'contamination': r'\bcontaminat|remediat|hazardous|site\s+audit',
    'safety': r'\bsafety|crime|cpted|surveillance|security',
    'residential': r'\bresidential|dwelling|apartment|house|unit',
    'commercial': r'\bcommercial|retail|shop|business',
    'industrial': r'\bindustrial|warehouse|factory|manufacturing',
    'mixed_use': r'\bmixed\s+use|mixed-use',
    'subdivision': r'\bsubdivision|lot\s+size|lot\s+width|minimum\s+lot',
    'density': r'\bdensity|FSR|floor\s+space|dwelling\s+yield',
    'sustainability': r'\bsustainab|BASIX|energy\s+efficien|environmental',
    'water': r'\bwater|rainwater|water\s+sensitive',
    'views': r'\bview|outlook|vista',
    'roofing': r'\broof|pitch|eaves',
    'site_analysis': r'\bsite\s+analysis|context\s+analysis|site\s+context',
    'precinct': r'\bprecinct|town\s+centre|neighborhood|neighbourhood',
    'general': r'\bobjective|purpose|aim|principle|guideline\s+applies',
}

# Part-specific default topics (when no keywords match)
PART_DEFAULTS = {
    'Chapter A': 'general',      # Miscellaneous/admin
    'Chapter C': 'sustainability',  # Sustainability chapter
    'Chapter D': 'precinct',     # Precinct guidelines
    'Chapter E1': 'heritage',    # Heritage (already assigned)
    'Chapter E2': 'precinct',    # Haberfield precinct
}


def get_db_connection():
    db_url = os.environ.get('DATABASE_URL')
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def extract_topic(text: str, part: str = None) -> Tuple[Optional[str], str]:
    """Extract topic using weighted keyword matching"""
    if not text:
        return (None, 'empty')

    text_lower = text.lower()

    # Score each topic
    scores = defaultdict(int)
    for topic, pattern in TOPIC_KEYWORDS.items():
        matches = re.findall(pattern, text_lower, re.IGNORECASE)
        if matches:
            scores[topic] = len(matches)

    if scores:
        # Get best topic
        best_topic = max(scores.items(), key=lambda x: x[1])[0]
        return (best_topic, 'keyword')

    # Check if it's a TOC, header, or very short text
    if is_toc_or_header(text):
        return (None, 'toc_header')

    # Use part default
    if part and part in PART_DEFAULTS:
        return (PART_DEFAULTS[part], 'part_default')

    return ('general', 'fallback')


def is_toc_or_header(text: str) -> bool:
    """Check if text is TOC or section header"""
    if not text:
        return True

    text = text.strip()

    # Very short
    if len(text) < 30:
        return True

    # TOC patterns
    if '...' in text and ('page' in text.lower() or re.search(r'\d+$', text)):
        return True

    # Just a title
    if re.match(r'^[A-Z][a-z\s]+$', text) and len(text) < 50:
        return True

    return False


def analyze_and_fix(conn, dry_run=True):
    """Analyze and fix Ashfield None topics"""
    print("=" * 80)
    if dry_run:
        print("ASHFIELD TOPIC FIX - DRY RUN")
    else:
        print("ASHFIELD TOPIC FIX - APPLYING CHANGES")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_dcp_part, v2_topic, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE '%%Ashfield%%'
              AND v2_topic IS NULL
              AND is_current = TRUE
            ORDER BY v2_dcp_part, pdf_page, id
        """)
        provisions = cur.fetchall()

    print(f"\nTotal None topics: {len(provisions)}")

    # Group by part
    by_part = defaultdict(list)
    for p in provisions:
        by_part[p['v2_dcp_part'] or 'unknown'].append(p)

    print(f"\nBy part:")
    for part, items in sorted(by_part.items()):
        print(f"   {part}: {len(items)}")

    # Determine fixes
    fixes = []
    cant_fix = []

    for p in provisions:
        topic, method = extract_topic(p['provision_text'], p['v2_dcp_part'])
        if topic:
            fixes.append({
                'id': p['id'],
                'part': p['v2_dcp_part'],
                'topic': topic,
                'method': method,
                'text': (p['provision_text'] or '')[:80]
            })
        else:
            cant_fix.append(p)

    print(f"\nProposed fixes: {len(fixes)}")
    print(f"Cannot fix (TOC/headers): {len(cant_fix)}")

    # Breakdown by method
    by_method = defaultdict(int)
    for f in fixes:
        by_method[f['method']] += 1
    print(f"\nFix methods:")
    for method, count in sorted(by_method.items(), key=lambda x: -x[1]):
        print(f"   {method}: {count}")

    # Breakdown by topic
    by_topic = defaultdict(int)
    for f in fixes:
        by_topic[f['topic']] += 1
    print(f"\nProposed topics:")
    for topic, count in sorted(by_topic.items(), key=lambda x: -x[1]):
        print(f"   {topic}: {count}")

    # Show samples
    print(f"\nSample fixes:")
    for f in fixes[:10]:
        print(f"\n   ID {f['id']} ({f['part']})")
        print(f"   -> {f['topic']} (via {f['method']})")
        print(f"   Text: {f['text']}...")

    if not dry_run and fixes:
        print("\n" + "=" * 80)
        print("APPLYING CHANGES")
        print("=" * 80)

        with conn.cursor() as cur:
            # Group by topic for efficiency
            topic_groups = defaultdict(list)
            for f in fixes:
                topic_groups[f['topic']].append(f['id'])

            total_updated = 0
            for topic, ids in topic_groups.items():
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(f"""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id IN ({placeholders})
                      AND document_id ILIKE '%%Ashfield%%'
                """, [topic] + ids)
                total_updated += cur.rowcount
                print(f"   Updated {cur.rowcount} provisions to '{topic}'")

        conn.commit()
        print(f"\n[OK] Total updated: {total_updated}")

        # Verify
        verify_fixes(conn)
    else:
        print("\n[!] DRY RUN - No changes applied")


def verify_fixes(conn):
    """Verify fixes were applied"""
    print("\n" + "=" * 80)
    print("POST-FIX VERIFICATION")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT v2_dcp_part, COUNT(*) as total,
                   COUNT(*) FILTER (WHERE v2_topic IS NULL) as none_count
            FROM regulatory_provisions
            WHERE document_id ILIKE '%%Ashfield%%'
              AND is_current = TRUE
            GROUP BY v2_dcp_part
            ORDER BY v2_dcp_part
        """)
        results = cur.fetchall()

    print(f"\nNone topic counts by part:")
    for r in results:
        pct = r['none_count'] / r['total'] * 100 if r['total'] > 0 else 0
        status = "OK" if pct < 5 else "NEEDS REVIEW"
        print(f"   {r['v2_dcp_part'] or 'unknown'}: {r['none_count']}/{r['total']} ({pct:.1f}%) {status}")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    conn = None
    try:
        conn = get_db_connection()
        analyze_and_fix(conn, dry_run=args.dry_run)
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    main()
