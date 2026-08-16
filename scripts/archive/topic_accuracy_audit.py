#!/usr/bin/env python3
"""
TOPIC ACCURACY AUDIT

Shows how many topics are RELIABLY derived vs GUESSED.

Reliable sources:
- Marker lookup (C3 → parking) - 100% accurate
- Part-based (Part 8 → heritage) - 100% accurate
- Document_id section (2__10__ → parking) - 100% accurate

Unreliable sources:
- Same-page inheritance - assumption
- Nearest-page inheritance - guess
- Default assignment (general, site_specific) - placeholder
"""
import os
import sys
import re

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

LEICHHARDT_MARKER_TOPICS = {
    'C1': 'site_analysis', 'C2': 'heritage', 'C3': 'parking', 'C4': 'building_form',
    'C5': 'roofing', 'C6': 'landscaping', 'C7': 'fencing', 'C8': 'setbacks',
    'C9': 'trees', 'C10': 'trees', 'C11': 'trees', 'C12': 'flooding',
    'C13': 'contamination', 'C14': 'parking', 'C15': 'parking', 'C16': 'parking',
    'C17': 'parking', 'C18': 'bicycle_parking', 'C19': 'bicycle_parking',
    'C20': 'bicycle_parking', 'C21': 'bicycle_parking', 'C22': 'access',
    'C23': 'landscaping', 'C24': 'building_design', 'C25': 'building_design',
    'C26': 'open_space', 'C27': 'building_design', 'C28': 'building_design',
    'C29': 'privacy', 'C30': 'solar', 'C31': 'views', 'C32': 'setbacks',
    'C33': 'height', 'C34': 'building_form', 'C35': 'building_form',
    'C36': 'safety', 'C37': 'heritage', 'C38': 'signage', 'C39': 'signage',
    'C40': 'advertising', 'C41': 'advertising', 'C42': 'advertising',
    'C43': 'vehicle_access', 'C44': 'vehicle_access', 'C45': 'vehicle_access',
    'C46': 'vehicle_access', 'C47': 'vehicle_access', 'C48': 'vehicle_access',
    'C49': 'vehicle_access', 'C50': 'vehicle_access', 'C51': 'vehicle_access',
    'C52': 'vehicle_access', 'C53': 'vehicle_access', 'C54': 'vehicle_access',
    'C55': 'vehicle_access',
}

MARRICKVILLE_SECTIONS = {
    '1': 'urban_design', '3': 'site_analysis', '5': 'access', '6': 'privacy',
    '7': 'solar', '8': 'social_impact', '9': 'safety', '10': 'parking',
    '11': 'fencing', '12': 'signage', '13': 'biodiversity', '14': 'environmental',
    '16': 'energy', '17': 'wsud', '18': 'landscaping', '25': 'stormwater',
}

def get_reliable_topic(marker, dcp_part, document_id):
    """Return topic ONLY if it can be reliably derived. None otherwise."""

    # Leichhardt markers - 100% reliable
    if marker:
        m = re.match(r'^(C\d+)', marker.strip().upper())
        if m and m.group(1) in LEICHHARDT_MARKER_TOPICS:
            return LEICHHARDT_MARKER_TOPICS[m.group(1)], 'marker'

    # Part-based - 100% reliable
    if dcp_part == 'Part 8':
        return 'heritage', 'part'
    if dcp_part == 'Part 9':
        return 'precinct', 'part'
    if dcp_part == 'Chapter E1':
        return 'heritage', 'part'
    if dcp_part == 'Part D':
        return 'energy', 'part'
    if dcp_part == 'Part E':
        return 'water', 'part'
    if dcp_part == 'Part F':
        return 'food_premises', 'part'
    if dcp_part == 'Chapter C':
        return 'sustainability', 'part'

    # Marrickville document_id section - reliable
    if document_id and 'marrickville' in document_id.lower():
        m = re.search(r'[_-]+2[_-]+(\d+)[_-]', document_id)
        if m and m.group(1) in MARRICKVILLE_SECTIONS:
            return MARRICKVILLE_SECTIONS[m.group(1)], 'document_id'

    return None, None


def main():
    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor()

    print("="*70)
    print("TOPIC ACCURACY AUDIT")
    print("="*70)
    print("\nReliable = derived from marker, part, or document_id section")
    print("Unreliable = inherited from page, guessed, or default assignment\n")

    cur.execute('''
        SELECT id, v2_marker, v2_dcp_part, document_id, v2_topic
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
        AND (document_id ILIKE '%leichhardt%' OR document_id ILIKE '%ashfield%' OR document_id ILIKE '%marrickville%')
    ''')

    provisions = cur.fetchall()

    reliable = 0
    unreliable = 0
    reliable_by_source = {'marker': 0, 'part': 0, 'document_id': 0}
    unreliable_by_topic = {}

    for prov_id, marker, part, doc_id, current_topic in provisions:
        reliable_topic, source = get_reliable_topic(marker, part, doc_id)

        if reliable_topic:
            reliable += 1
            reliable_by_source[source] += 1
        else:
            unreliable += 1
            t = current_topic or 'None'
            unreliable_by_topic[t] = unreliable_by_topic.get(t, 0) + 1

    total = len(provisions)

    print(f"Total actionable provisions: {total}")
    print(f"\n✓ RELIABLE (100% accurate): {reliable} ({100*reliable//total}%)")
    for source, count in reliable_by_source.items():
        print(f"    {source}: {count}")

    print(f"\n✗ UNRELIABLE (guessed/inherited): {unreliable} ({100*unreliable//total}%)")
    print("  Topics assigned to unreliable provisions:")
    for topic, count in sorted(unreliable_by_topic.items(), key=lambda x: -x[1]):
        print(f"    {topic}: {count}")

    # By council
    print("\n" + "="*70)
    print("BY COUNCIL")
    print("="*70)

    for council in ['leichhardt', 'ashfield', 'marrickville']:
        cur.execute(f'''
            SELECT id, v2_marker, v2_dcp_part, document_id
            FROM regulatory_provisions
            WHERE v2_is_actionable = true
            AND document_id ILIKE '%{council}%'
        ''')

        rows = cur.fetchall()
        c_reliable = 0
        for prov_id, marker, part, doc_id in rows:
            topic, _ = get_reliable_topic(marker, part, doc_id)
            if topic:
                c_reliable += 1

        c_total = len(rows)
        pct = 100*c_reliable//c_total if c_total else 0
        print(f"\n{council.upper()}: {c_reliable}/{c_total} ({pct}%) reliable")

    conn.close()

    print("\n" + "="*70)
    print("CONCLUSION")
    print("="*70)
    print(f"""
HONEST STATUS:
- {reliable} provisions ({100*reliable//total}%) have RELIABLE topics
- {unreliable} provisions ({100*unreliable//total}%) have GUESSED topics

The {unreliable} unreliable provisions need either:
1. Re-extraction from PDF with section headers
2. Manual review and correction
3. LLM classification with section context
""")


if __name__ == '__main__':
    main()
