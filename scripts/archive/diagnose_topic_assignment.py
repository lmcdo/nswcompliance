#!/usr/bin/env python3
"""
Diagnostic script for Leichhardt DCP topic assignment

Questions to answer:
1. What % of Part C Section 1 provisions have C markers?
2. Are C markers being extracted correctly?
3. Is keyword matching producing reasonable results?
4. What is the topic diversity and is it justified?

Usage:
    python scripts/diagnose_topic_assignment.py
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


# Leichhardt C markers -> topics (from layer_topic_tagger.py)
LEICHHARDT_C_TOPICS = {
    'C1': 'site_analysis',
    'C2': 'heritage',
    'C3': 'parking',
    'C4': 'building_form',
    'C5': 'roofing',
    'C6': 'landscaping',
    'C7': 'fencing',
    'C8': 'setbacks',
    'C9': 'trees',
    'C10': 'trees',
    'C11': 'trees',
    'C12': 'flooding',
    'C13': 'contamination',
    'C14': 'parking',
    'C15': 'parking',
    'C16': 'parking',
    'C17': 'parking',
    'C18': 'bicycle_parking',
    'C19': 'bicycle_parking',
    'C20': 'bicycle_parking',
    'C21': 'bicycle_parking',
    'C22': 'access',
    'C23': 'landscaping',
    'C24': 'building_design',
    'C25': 'building_design',
    'C26': 'open_space',
    'C27': 'building_design',
    'C28': 'building_design',
    'C29': 'privacy',
    'C30': 'solar',
    'C31': 'views',
    'C32': 'setbacks',
    'C33': 'height',
    'C34': 'building_form',
    'C35': 'building_form',
    'C36': 'safety',
    'C37': 'heritage',
    'C38': 'signage',
    'C39': 'signage',
    'C40': 'advertising',
    'C41': 'advertising',
    'C42': 'advertising',
    'C43': 'vehicle_access',
    'C44': 'vehicle_access',
    'C45': 'vehicle_access',
    'C46': 'vehicle_access',
    'C47': 'vehicle_access',
    'C48': 'vehicle_access',
    'C49': 'vehicle_access',
    'C50': 'vehicle_access',
    'C51': 'vehicle_access',
    'C52': 'vehicle_access',
    'C53': 'vehicle_access',
    'C54': 'vehicle_access',
    'C55': 'vehicle_access',
}

# Topic keywords for analysis (from layer_topic_tagger.py)
TOPIC_KEYWORDS = {
    'setbacks': r'\bsetback|boundary\s+distance|front\s+yard|rear\s+yard|side\s+yard',
    'height': r'\bheight|storey|floor\s+level|building\s+height',
    'parking': r'\bparking|car\s*space|garage|vehicle\s+space',
    'solar': r'\bsolar|overshadow|sunlight|daylight',
    'privacy': r'\bprivacy|overlooking|screen|window\s+separation',
    'landscaping': r'\blandscap|garden|planting|vegetation',
    'heritage': r'\bheritage|conservation|historic',
    'trees': r'\btree|canopy|vegetation',
    'fencing': r'\bfenc|fence|front\s+boundary\s+treatment',
    'access': r'\baccess|entry|driveway|pedestrian',
    'stormwater': r'\bstormwater|drainage|runoff',
    'waste': r'\bwaste|garbage|recycling|bin',
    'waste_management': r'\bwaste|garbage|recycling|bin',
    'signage': r'\bsign|signage|advertising',
    'building_form': r'\bbulk|scale|massing|form|character',
    'building_design': r'\bdesign|facade|articulation|materials',
    'open_space': r'\bopen\s+space|courtyard|private\s+open',
    'flooding': r'\bflood|inundation',
    'contamination': r'\bcontaminat|remediat',
    'safety': r'\bsafety|crime|cpted|surveillance',
    'roofing': r'\broof|pitch|eaves',
    'site_analysis': r'\bsite\s+analysis|context|surroundings',
    'bicycle_parking': r'\bbicycle|bike|cycling',
    'vehicle_access': r'\bvehicle\s+access|driveway|crossover',
    'advertising': r'\badvertis|billboard',
    'views': r'\bview|outlook|vista',
    'energy': r'\benergy|solar\s+panel|renewable|photovoltaic',
    'water': r'\bwater|rainwater|wsud',
}


def get_db_connection():
    """Get PostgreSQL database connection"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment")
    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def extract_c_marker(text: str) -> Optional[str]:
    """Extract C marker from text (same logic as layer_topic_tagger.py)"""
    if not text:
        return None
    match = re.match(r'^(C\d+)', text.strip())
    if match:
        return match.group(1)
    return None


def find_keyword_matches(text: str) -> dict:
    """Find all keyword matches in text, return {topic: match_count}"""
    if not text:
        return {}

    text_lower = text.lower()
    matches = {}

    for topic, pattern in TOPIC_KEYWORDS.items():
        found = re.findall(pattern, text_lower, re.IGNORECASE)
        if found:
            matches[topic] = len(found)

    return matches


def diagnose_part_c_section_1(conn):
    """Diagnose Part C Section 1 topic assignment"""
    print("\n" + "=" * 80)
    print("PART C SECTION 1 - DIAGNOSTIC")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Leichhardt%'
              AND v2_dcp_part = 'Part C Section 1'
              AND is_current = TRUE
            ORDER BY pdf_page, id
        """)
        provisions = cur.fetchall()

    print(f"\nTotal provisions: {len(provisions)}")

    # Categorize by C marker presence
    with_markers = []
    without_markers = []

    for p in provisions:
        text = p['provision_text'].strip() if p['provision_text'] else ''
        marker = extract_c_marker(text)
        if marker:
            with_markers.append({**p, 'marker': marker})
        else:
            without_markers.append(p)

    print(f"\n1. C MARKER EXTRACTION RATE:")
    print(f"   With C markers: {len(with_markers)} ({len(with_markers)/len(provisions)*100:.1f}%)")
    print(f"   Without C markers: {len(without_markers)} ({len(without_markers)/len(provisions)*100:.1f}%)")

    # For provisions WITH markers: verify topic matches
    print(f"\n2. C MARKER -> TOPIC CORRECTNESS:")
    marker_match = 0
    marker_mismatch = []
    unknown_markers = []

    for p in with_markers:
        marker = p['marker']
        expected_topic = LEICHHARDT_C_TOPICS.get(marker)
        actual_topic = p['v2_topic']

        if expected_topic is None:
            unknown_markers.append((marker, p['id']))
        elif actual_topic == expected_topic:
            marker_match += 1
        else:
            marker_mismatch.append({
                'id': p['id'],
                'marker': marker,
                'expected': expected_topic,
                'actual': actual_topic,
                'text': p['provision_text'][:80] if p['provision_text'] else ''
            })

    valid_markers = len(with_markers) - len(unknown_markers)
    if valid_markers > 0:
        print(f"   Marker->Topic match rate: {marker_match}/{valid_markers} ({marker_match/valid_markers*100:.1f}%)")

    if unknown_markers:
        print(f"   Unknown markers (not in mapping): {len(unknown_markers)}")
        for marker, pid in unknown_markers[:5]:
            print(f"      {marker} (provision {pid})")

    if marker_mismatch:
        print(f"\n   MISMATCHES ({len(marker_mismatch)}):")
        for m in marker_mismatch[:5]:
            print(f"      ID {m['id']}: {m['marker']} -> expected '{m['expected']}', got '{m['actual']}'")
            print(f"         Text: {m['text']}...")

    # For provisions WITHOUT markers: show topic distribution
    print(f"\n3. KEYWORD FALLBACK QUALITY (provisions without C markers):")
    no_marker_topics = defaultdict(int)
    for p in without_markers:
        no_marker_topics[p['v2_topic'] or 'None'] += 1

    print(f"   Topic distribution:")
    for topic, count in sorted(no_marker_topics.items(), key=lambda x: -x[1]):
        pct = count / len(without_markers) * 100 if without_markers else 0
        print(f"      {topic}: {count} ({pct:.1f}%)")

    # Sample some keyword-assigned provisions to check quality
    print(f"\n   Sample provisions assigned by keyword (check quality):")
    for p in without_markers[:5]:
        text = p['provision_text'] or ''
        matches = find_keyword_matches(text)
        print(f"\n      ID {p['id']} -> assigned '{p['v2_topic']}'")
        print(f"      Text: {text[:100]}...")
        print(f"      Keyword matches: {matches}")

    # Overall topic distribution
    print(f"\n4. OVERALL TOPIC DISTRIBUTION:")
    all_topics = defaultdict(int)
    for p in provisions:
        all_topics[p['v2_topic'] or 'None'] += 1

    print(f"   {len(all_topics)} unique topics:")
    for topic, count in sorted(all_topics.items(), key=lambda x: -x[1]):
        pct = count / len(provisions) * 100
        print(f"      {topic}: {count} ({pct:.1f}%)")

    return {
        'total': len(provisions),
        'with_markers': len(with_markers),
        'without_markers': len(without_markers),
        'marker_match_rate': marker_match / valid_markers if valid_markers > 0 else 0,
        'unique_topics': len(all_topics),
        'mismatches': marker_mismatch
    }


def diagnose_part_c_section_2(conn):
    """Diagnose Part C Section 2 topic assignment"""
    print("\n" + "=" * 80)
    print("PART C SECTION 2 - DIAGNOSTIC")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Leichhardt%'
              AND v2_dcp_part = 'Part C Section 2'
              AND is_current = TRUE
            ORDER BY pdf_page, id
        """)
        provisions = cur.fetchall()

    print(f"\nTotal provisions: {len(provisions)}")

    # Check for any structural markers
    print(f"\n1. STRUCTURAL MARKER CHECK:")
    markers_found = defaultdict(int)
    for p in provisions:
        text = p['provision_text'] or ''
        # Check for C markers
        if re.match(r'^C\d+', text.strip()):
            markers_found['C marker'] += 1
        # Check for numbered sections
        if re.match(r'^\d+\.\d+', text.strip()):
            markers_found['Numbered section'] += 1
        # Check for lettered markers
        if re.match(r'^[A-Z]\d+', text.strip()):
            markers_found['Letter marker'] += 1

    if markers_found:
        print(f"   Structural markers found:")
        for marker_type, count in markers_found.items():
            print(f"      {marker_type}: {count}")
    else:
        print(f"   No structural markers found - relies entirely on keyword matching")

    # Topic distribution
    print(f"\n2. TOPIC DISTRIBUTION:")
    topics = defaultdict(int)
    for p in provisions:
        topics[p['v2_topic'] or 'None'] += 1

    print(f"   {len(topics)} unique topics:")
    for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
        pct = count / len(provisions) * 100
        print(f"      {topic}: {count} ({pct:.1f}%)")

    # Check keyword match quality
    print(f"\n3. KEYWORD MATCH ANALYSIS:")
    good_match = 0  # Assigned topic has keywords
    no_match = 0    # Assigned topic has NO keywords, but other topics do
    ambiguous = 0   # Multiple topics have keywords
    empty = 0       # No keywords found at all

    mismatch_examples = []

    for p in provisions:
        text = p['provision_text'] or ''
        assigned = p['v2_topic']
        matches = find_keyword_matches(text)

        if not matches:
            empty += 1
        elif assigned in matches:
            # Check if assigned topic has most keywords or is tied
            max_count = max(matches.values())
            if matches[assigned] == max_count:
                good_match += 1
            else:
                ambiguous += 1
        else:
            # Assigned topic has NO keywords but others do
            no_match += 1
            if len(mismatch_examples) < 10:
                mismatch_examples.append({
                    'id': p['id'],
                    'assigned': assigned,
                    'matches': matches,
                    'text': text[:100]
                })

    print(f"   Good match (assigned topic has keywords): {good_match} ({good_match/len(provisions)*100:.1f}%)")
    print(f"   No match (assigned has no keywords, others do): {no_match} ({no_match/len(provisions)*100:.1f}%)")
    print(f"   Ambiguous (multiple topics match): {ambiguous} ({ambiguous/len(provisions)*100:.1f}%)")
    print(f"   Empty (no keywords found): {empty} ({empty/len(provisions)*100:.1f}%)")

    if mismatch_examples:
        print(f"\n   MISMATCH EXAMPLES (assigned topic has no keywords):")
        for ex in mismatch_examples[:5]:
            print(f"\n      ID {ex['id']}: assigned '{ex['assigned']}'")
            print(f"      But keywords found: {ex['matches']}")
            print(f"      Text: {ex['text']}...")

    return {
        'total': len(provisions),
        'unique_topics': len(topics),
        'good_match': good_match,
        'no_match': no_match,
        'ambiguous': ambiguous,
        'empty': empty,
        'mismatch_examples': mismatch_examples
    }


def diagnose_part_d(conn):
    """Diagnose Part D topic assignment (should be fixed already)"""
    print("\n" + "=" * 80)
    print("PART D - VERIFICATION (should be fixed)")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Leichhardt%'
              AND v2_dcp_part = 'Part D'
              AND is_current = TRUE
            ORDER BY pdf_page, id
        """)
        provisions = cur.fetchall()

    print(f"\nTotal provisions: {len(provisions)}")

    # Topic distribution
    topics = defaultdict(int)
    for p in provisions:
        topics[p['v2_topic'] or 'None'] += 1

    print(f"\nTopic distribution:")
    for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
        print(f"   {topic}: {count}")

    # Check by page range
    energy_pages = [p for p in provisions if 2 <= (p['pdf_page'] or 0) <= 5]
    waste_pages = [p for p in provisions if 6 <= (p['pdf_page'] or 0) <= 15]

    print(f"\nBy section:")
    print(f"   Pages 2-5 (Energy): {len(energy_pages)} provisions")
    energy_topics = defaultdict(int)
    for p in energy_pages:
        energy_topics[p['v2_topic'] or 'None'] += 1
    for t, c in energy_topics.items():
        print(f"      {t}: {c}")

    print(f"   Pages 6-15 (Waste): {len(waste_pages)} provisions")
    waste_topics = defaultdict(int)
    for p in waste_pages:
        waste_topics[p['v2_topic'] or 'None'] += 1
    for t, c in waste_topics.items():
        print(f"      {t}: {c}")

    return {
        'total': len(provisions),
        'energy_section': len(energy_pages),
        'waste_section': len(waste_pages),
        'topic_distribution': dict(topics)
    }


def diagnose_part_e(conn):
    """Diagnose Part E topic assignment"""
    print("\n" + "=" * 80)
    print("PART E - DIAGNOSTIC")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Leichhardt%'
              AND v2_dcp_part = 'Part E'
              AND is_current = TRUE
            ORDER BY pdf_page, id
        """)
        provisions = cur.fetchall()

    print(f"\nTotal provisions: {len(provisions)}")

    # Topic distribution
    topics = defaultdict(int)
    for p in provisions:
        topics[p['v2_topic'] or 'None'] += 1

    print(f"\nTopic distribution:")
    for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
        print(f"   {topic}: {count}")

    # Check if 'water' is appropriate by looking at keywords
    print(f"\nKeyword validation:")
    water_kw = 0
    other_kw = 0
    for p in provisions:
        text = p['provision_text'] or ''
        matches = find_keyword_matches(text)
        if 'water' in matches or 'stormwater' in matches:
            water_kw += 1
        elif matches:
            other_kw += 1

    print(f"   With water keywords: {water_kw}")
    print(f"   With other keywords (no water): {other_kw}")

    return {
        'total': len(provisions),
        'topic_distribution': dict(topics)
    }


def diagnose_part_g(conn):
    """Diagnose Part G topic assignment"""
    print("\n" + "=" * 80)
    print("PART G - DIAGNOSTIC")
    print("=" * 80)

    with conn.cursor() as cur:
        cur.execute("""
            SELECT id, provision_text, v2_topic, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Leichhardt%'
              AND v2_dcp_part = 'Part G'
              AND is_current = TRUE
            ORDER BY pdf_page, id
        """)
        provisions = cur.fetchall()

    print(f"\nTotal provisions: {len(provisions)}")

    # Topic distribution
    topics = defaultdict(int)
    for p in provisions:
        topics[p['v2_topic'] or 'None'] += 1

    print(f"\nTopic distribution ({len(topics)} unique topics):")
    for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
        pct = count / len(provisions) * 100 if provisions else 0
        print(f"   {topic}: {count} ({pct:.1f}%)")

    # Check keyword match quality
    print(f"\nKeyword match analysis:")
    good_match = 0
    no_match = 0

    for p in provisions:
        text = p['provision_text'] or ''
        assigned = p['v2_topic']
        matches = find_keyword_matches(text)

        if assigned in matches:
            good_match += 1
        elif matches:
            no_match += 1

    if provisions:
        print(f"   Good match: {good_match} ({good_match/len(provisions)*100:.1f}%)")
        print(f"   Mismatch: {no_match} ({no_match/len(provisions)*100:.1f}%)")

    return {
        'total': len(provisions),
        'unique_topics': len(topics),
        'topic_distribution': dict(topics)
    }


def print_summary(results):
    """Print overall summary and recommendations"""
    print("\n" + "=" * 80)
    print("SUMMARY & RECOMMENDATIONS")
    print("=" * 80)

    print("\n1. PART C SECTION 1:")
    r = results.get('part_c_section_1', {})
    marker_rate = r.get('with_markers', 0) / r.get('total', 1) * 100
    match_rate = r.get('marker_match_rate', 0) * 100

    if marker_rate > 80 and match_rate > 95:
        print(f"   STATUS: LIKELY CORRECT")
        print(f"   - {marker_rate:.1f}% provisions have C markers")
        print(f"   - {match_rate:.1f}% marker->topic match rate")
        print(f"   ACTION: No changes needed")
    elif marker_rate > 80 and match_rate < 80:
        print(f"   STATUS: MARKER EXTRACTION ISSUE")
        print(f"   - {marker_rate:.1f}% provisions have C markers")
        print(f"   - Only {match_rate:.1f}% marker->topic match rate")
        print(f"   ACTION: Debug C marker -> topic mapping")
    else:
        print(f"   STATUS: RELIES ON KEYWORD FALLBACK")
        print(f"   - Only {marker_rate:.1f}% provisions have C markers")
        print(f"   ACTION: Review keyword-assigned topics for quality")

    print(f"\n2. PART C SECTION 2:")
    r = results.get('part_c_section_2', {})
    total = r.get('total', 1)
    good = r.get('good_match', 0)
    no_match = r.get('no_match', 0)

    mismatch_rate = no_match / total * 100 if total > 0 else 0
    if mismatch_rate > 20:
        print(f"   STATUS: POTENTIAL ISSUES")
        print(f"   - {no_match}/{total} ({mismatch_rate:.1f}%) provisions have mismatched topics")
        print(f"   ACTION: Review mismatch examples, consider fixes")
    else:
        print(f"   STATUS: ACCEPTABLE")
        print(f"   - Only {mismatch_rate:.1f}% mismatch rate")
        print(f"   ACTION: No urgent changes needed")

    print(f"\n3. PART D:")
    r = results.get('part_d', {})
    dist = r.get('topic_distribution', {})
    if 'waste_management' in dist and 'energy' in dist:
        print(f"   STATUS: FIXED")
        print(f"   - Energy: {dist.get('energy', 0)}, Waste: {dist.get('waste_management', 0)}")
        print(f"   ACTION: None needed")
    else:
        print(f"   STATUS: MAY NEED REVIEW")
        print(f"   - Distribution: {dist}")

    print(f"\n4. PART E:")
    r = results.get('part_e', {})
    dist = r.get('topic_distribution', {})
    print(f"   - Distribution: {dist}")
    print(f"   ACTION: Verify 'water' is appropriate for this part")

    print(f"\n5. PART G:")
    r = results.get('part_g', {})
    print(f"   - {r.get('unique_topics', 0)} unique topics across {r.get('total', 0)} provisions")
    print(f"   ACTION: Review if topic diversity is appropriate")


def main():
    """Run all diagnostics"""
    print("=" * 80)
    print("LEICHHARDT DCP TOPIC ASSIGNMENT DIAGNOSTIC")
    print("=" * 80)

    conn = None
    try:
        conn = get_db_connection()
        print("Connected to database")

        results = {}

        results['part_c_section_1'] = diagnose_part_c_section_1(conn)
        results['part_c_section_2'] = diagnose_part_c_section_2(conn)
        results['part_d'] = diagnose_part_d(conn)
        results['part_e'] = diagnose_part_e(conn)
        results['part_g'] = diagnose_part_g(conn)

        print_summary(results)

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
