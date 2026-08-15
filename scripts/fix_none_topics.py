#!/usr/bin/env python3
"""
Fix Leichhardt DCP provisions with None topic

Based on diagnostic findings:
- Part C Section 1: 93 provisions (15.7%) have None topic
- Part G: 119 provisions (23.5%) have None topic

Strategy:
1. Re-run keyword matching with expanded keywords
2. For provisions that still don't match, try secondary patterns
3. Assign 'general' as fallback for truly generic provisions

Usage:
    python scripts/fix_none_topics.py --dry-run  # Preview changes
    python scripts/fix_none_topics.py            # Apply changes
"""

import os
import re
import sys
from collections import defaultdict
from typing import Optional

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

# Load environment variables
script_dir = pathlib.Path(__file__).parent.absolute()
project_root = script_dir.parent
env_file = project_root / 'frontend-nextjs' / '.env.local'

if not env_file.exists():
    raise FileNotFoundError(f"Cannot find .env file at {env_file}")

load_dotenv(env_file, override=True)


# Expanded keyword patterns for better matching
TOPIC_KEYWORDS_EXPANDED = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard|building\s+line|rear\s+boundary|side\s+boundary',
    'height': r'\bheight|storey|floor\s+level|building\s+height|maximum\s+height|FSR|floor\s+space\s+ratio',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space|off-street\s+parking',
    'solar': r'\bsolar|overshadow|sunlight|daylight|sun\s+access|northern\s+aspect',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation|visual\s+privacy',
    'landscaping': r'\blandscap|garden|planting|vegetation|planted|greenery|soft\s+landscap',
    'heritage': r'\bheritage|conservation|historic|contributory|HCA|character\s+area',
    'trees': r'\btree|canopy|vegetation|arborist|deep\s+soil',
    'fencing': r'\bfenc|fence|front\s+boundary\s+treatment|boundary\s+fence',
    'access': r'\baccess|entry|driveway|pedestrian|wheelchair|disabled\s+access|universal\s+access',
    'stormwater': r'\bstormwater|drainage|runoff|OSD|on-site\s+detention',
    'waste': r'\bwaste|garbage|recycling|bin|refuse',
    'waste_management': r'\bwaste|garbage|recycling|bin|refuse',
    'signage': r'\bsign|signage',
    'building_form': r'\bbulk|scale|massing|form|character|built\s+form|streetscape',
    'building_design': r'\bdesign|facade|articulation|materials|architectural',
    'open_space': r'\bopen\s+space|courtyard|private\s+open|communal\s+open|POS|COS',
    'flooding': r'\bflood|inundation|flood\s+prone|flood\s+level',
    'contamination': r'\bcontaminat|remediat|hazardous',
    'safety': r'\bsafety|crime|cpted|surveillance|security',
    'roofing': r'\broof|pitch|eaves|gutter',
    'site_analysis': r'\bsite\s+analysis|context|surroundings|site\s+context',
    'bicycle_parking': r'\bbicycle|bike|cycling|bike\s+parking',
    'vehicle_access': r'\bvehicle\s+access|driveway|crossover|vehicular',
    'advertising': r'\badvertis|billboard|poster',
    'views': r'\bview|outlook|vista|outlook',
    'energy': r'\benergy|solar\s+panel|renewable|photovoltaic|thermal|insulation',
    'water': r'\bwater|rainwater|wsud|water\s+sensitive',
    'density': r'\bdensity|dwelling|lot\s+size|subdivision|minimum\s+lot',
    'mixed_use': r'\bmixed\s+use|commercial|retail|shop',
    'residential': r'\bresidential|dwelling|house|apartment',
    'general': r'\bobjective|aim|purpose|principle',  # Very generic terms
}

# Secondary patterns - check if provision is about a specific topic based on context
SECONDARY_PATTERNS = {
    'height': r'(\d+\.?\d*)\s*(m|metres?|meters?)\s*(maximum|min|height)',
    'setbacks': r'(\d+\.?\d*)\s*(m|metres?|meters?)\s*(setback|from\s+boundary)',
    'parking': r'(\d+)\s*(car\s*space|parking\s*space)',
    'landscaping': r'(\d+)\s*%\s*(landscap|deep\s+soil|pervious)',
    'open_space': r'(\d+)\s*(sqm|m2|square\s+metres?)\s*(open\s+space|POS)',
    'density': r'(\d+)\s*(sqm|m2)\s*(per\s+dwelling|minimum\s+lot)',
}


def get_db_connection():
    """Get PostgreSQL database connection"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment")
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def extract_topic_expanded(text: str) -> Optional[str]:
    """Extract topic using expanded keyword matching"""
    if not text:
        return None

    text_lower = text.lower()
    earliest_topic = None
    earliest_pos = len(text) + 1

    for topic, pattern in TOPIC_KEYWORDS_EXPANDED.items():
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match and match.start() < earliest_pos:
            earliest_pos = match.start()
            earliest_topic = topic

    return earliest_topic


def extract_topic_secondary(text: str) -> Optional[str]:
    """Extract topic using secondary patterns (numbers + context)"""
    if not text:
        return None

    text_lower = text.lower()

    for topic, pattern in SECONDARY_PATTERNS.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            return topic

    return None


def determine_topic(provision: dict) -> tuple:
    """
    Determine best topic for a provision.

    Returns:
        (topic, method) where method is 'expanded_keyword', 'secondary_pattern', or 'general_fallback'
    """
    text = provision.get('provision_text', '')

    # Try expanded keywords first
    topic = extract_topic_expanded(text)
    if topic:
        return (topic, 'expanded_keyword')

    # Try secondary patterns
    topic = extract_topic_secondary(text)
    if topic:
        return (topic, 'secondary_pattern')

    # Check if it's a table of contents or header (assign None, don't fix)
    if is_toc_or_header(text):
        return (None, 'toc_or_header')

    # Fallback to 'general' for truly generic provisions
    return ('general', 'general_fallback')


def is_toc_or_header(text: str) -> bool:
    """Check if text is table of contents or section header"""
    if not text:
        return True

    text_lower = text.lower().strip()

    # Table of contents patterns
    if '...' in text and any(x in text_lower for x in ['page', 'section', 'chapter']):
        return True

    # Very short text (likely header)
    if len(text_lower) < 20:
        return True

    # Section header patterns
    if re.match(r'^(section|chapter|part)\s+\d', text_lower):
        return True

    return False


def analyze_none_topics(conn):
    """Analyze provisions with None topics"""
    print("=" * 80)
    print("ANALYZING PROVISIONS WITH NONE TOPICS")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, v2_dcp_part, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Leichhardt%'
              AND v2_topic IS NULL
              AND is_current = TRUE
            ORDER BY v2_dcp_part, pdf_page, id
        """)
        provisions = cur.fetchall()

    print(f"\nTotal provisions with None topic: {len(provisions)}")

    # Group by part
    by_part = defaultdict(list)
    for p in provisions:
        by_part[p['v2_dcp_part']].append(p)

    print(f"\nBy DCP Part:")
    for part, items in sorted(by_part.items()):
        print(f"   {part}: {len(items)}")

    # Analyze what topics we can assign
    proposed_fixes = []
    cant_fix = []

    for p in provisions:
        topic, method = determine_topic(p)
        if topic:
            proposed_fixes.append({
                'id': p['id'],
                'part': p['v2_dcp_part'],
                'proposed_topic': topic,
                'method': method,
                'text': p['provision_text'][:100] if p['provision_text'] else ''
            })
        else:
            cant_fix.append(p)

    print(f"\nProposed fixes: {len(proposed_fixes)}")
    print(f"Cannot determine topic: {len(cant_fix)}")

    # Show fix breakdown by method
    by_method = defaultdict(int)
    for fix in proposed_fixes:
        by_method[fix['method']] += 1

    print(f"\nFix method breakdown:")
    for method, count in sorted(by_method.items(), key=lambda x: -x[1]):
        print(f"   {method}: {count}")

    # Show fix breakdown by proposed topic
    by_topic = defaultdict(int)
    for fix in proposed_fixes:
        by_topic[fix['proposed_topic']] += 1

    print(f"\nProposed topic distribution:")
    for topic, count in sorted(by_topic.items(), key=lambda x: -x[1]):
        print(f"   {topic}: {count}")

    return provisions, proposed_fixes, cant_fix


def apply_fixes(conn, proposed_fixes, dry_run=True):
    """Apply the proposed topic fixes"""
    print("\n" + "=" * 80)
    if dry_run:
        print("DRY RUN - PREVIEWING CHANGES")
    else:
        print("APPLYING CHANGES TO DATABASE")
    print("=" * 80)

    if not proposed_fixes:
        print("\nNo fixes to apply.")
        return

    print(f"\nWill update {len(proposed_fixes)} provisions")

    # Show sample fixes
    print(f"\nSample fixes (first 10):")
    for fix in proposed_fixes[:10]:
        print(f"\n   ID {fix['id']} ({fix['part']})")
        print(f"   Proposed: '{fix['proposed_topic']}' (via {fix['method']})")
        print(f"   Text: {fix['text']}...")

    if not dry_run:
        print("\nUpdating database...")

        with conn.cursor() as cur:
            # Update in batches by topic
            by_topic = defaultdict(list)
            for fix in proposed_fixes:
                by_topic[fix['proposed_topic']].append(fix['id'])

            total_updated = 0
            for topic, ids in by_topic.items():
                placeholders = ','.join(['%s'] * len(ids))
                cur.execute(f"""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id IN ({placeholders})
                      AND document_id ILIKE %s
                """, (topic, *ids, '%Leichhardt%'))
                total_updated += cur.rowcount
                print(f"   Updated {cur.rowcount} provisions to '{topic}'")

            conn.commit()
            print(f"\n[OK] Total updated: {total_updated}")

    else:
        print("\n[!] DRY RUN - No changes applied. Run without --dry-run to apply changes.")


def verify_fixes(conn):
    """Verify the fixes were applied correctly"""
    print("\n" + "=" * 80)
    print("POST-FIX VERIFICATION")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT v2_dcp_part, COUNT(*) as total,
                   COUNT(*) FILTER (WHERE v2_topic IS NULL) as none_count
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Leichhardt%'
              AND is_current = TRUE
            GROUP BY v2_dcp_part
            ORDER BY v2_dcp_part
        """)
        results = cur.fetchall()

    print(f"\nNone topic counts by part:")
    for r in results:
        pct = r['none_count'] / r['total'] * 100 if r['total'] > 0 else 0
        print(f"   {r['v2_dcp_part']}: {r['none_count']}/{r['total']} ({pct:.1f}%) None")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Fix Leichhardt None topics')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without updating database')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze, do not fix')
    parser.add_argument('--include-general', action='store_true',
                       help='Include general_fallback fixes (conservative mode excludes these)')

    args = parser.parse_args()

    conn = None
    try:
        conn = get_db_connection()
        print("Connected to database")

        # Analyze
        provisions, proposed_fixes, cant_fix = analyze_none_topics(conn)

        # Conservative mode: exclude general_fallback unless explicitly requested
        if not args.include_general:
            original_count = len(proposed_fixes)
            proposed_fixes = [f for f in proposed_fixes if f['method'] != 'general_fallback']
            excluded = original_count - len(proposed_fixes)
            if excluded > 0:
                print(f"\n[CONSERVATIVE MODE] Excluded {excluded} general_fallback fixes")
                print(f"  (use --include-general to include them)")

        if not args.analyze_only:
            # Apply fixes
            apply_fixes(conn, proposed_fixes, dry_run=args.dry_run)

            # Verify
            if not args.dry_run:
                verify_fixes(conn)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    main()
