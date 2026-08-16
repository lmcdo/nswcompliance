#!/usr/bin/env python3
"""
STEP 4: FIX MARRICKVILLE AND ASHFIELD

1. Marrickville Part 2: Extract section from document_id
2. Marrickville/Ashfield unknown parts: Classify or mark non-actionable
3. Apply part-based topic defaults

Run with --execute to actually make changes.
"""
import os
import sys
import re
import json
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

MARRICKVILLE_SECTION_TOPICS = {
    '1': 'urban_design',
    '3': 'site_analysis',
    '5': 'access',
    '6': 'privacy',
    '7': 'solar',
    '8': 'social_impact',
    '9': 'safety',
    '10': 'parking',
    '11': 'fencing',
    '12': 'signage',
    '13': 'biodiversity',
    '14': 'environmental',
    '16': 'energy',
    '17': 'wsud',
    '18': 'landscaping',
    '25': 'stormwater',
}


def extract_marrickville_section(document_id):
    """Extract section number from Marrickville document_id."""
    if not document_id:
        return None
    # Pattern: __2__10__ or _2_10_
    m = re.search(r'[_-]+2[_-]+(\d+)[_-]', document_id)
    if m:
        return m.group(1)
    return None


def is_garbage_text(text):
    """Check if text is garbage that shouldn't be actionable."""
    if not text:
        return True
    if 'Error! Reference source not found' in text:
        return True
    if text.strip().startswith('Marrickville Development Control Plan 2011'):
        return True
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='Actually make changes')
    args = parser.parse_args()

    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor()

    print("="*80)
    print("STEP 4: FIX MARRICKVILLE AND ASHFIELD")
    print("="*80)

    if not args.execute:
        print("\n*** DRY RUN - No changes will be made ***\n")

    topic_updates = []
    garbage_ids = []

    # --- MARRICKVILLE ---
    print("\n## MARRICKVILLE")

    # Part 2 - extract section from document_id
    cur.execute("""
        SELECT id, document_id, v2_topic, LEFT(provision_text, 100)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%marrickville%'
        AND v2_is_actionable = true
        AND v2_dcp_part = 'Part 2'
    """)

    part2 = cur.fetchall()
    print(f"\nPart 2 provisions: {len(part2)}")

    part2_fixed = 0
    part2_unfixable = 0
    for prov_id, doc_id, current_topic, text in part2:
        section = extract_marrickville_section(doc_id)
        if section and section in MARRICKVILLE_SECTION_TOPICS:
            new_topic = MARRICKVILLE_SECTION_TOPICS[section]
            if new_topic != current_topic:
                topic_updates.append((prov_id, current_topic, new_topic, f'section_2.{section}'))
            part2_fixed += 1
        else:
            part2_unfixable += 1

    print(f"  Can derive from document_id: {part2_fixed}")
    print(f"  Cannot derive: {part2_unfixable}")

    # Unknown part - check for garbage
    cur.execute("""
        SELECT id, document_id, LEFT(provision_text, 200)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%marrickville%'
        AND v2_is_actionable = true
        AND v2_dcp_part = 'unknown'
    """)

    unknown_m = cur.fetchall()
    print(f"\nUnknown part provisions: {len(unknown_m)}")

    for prov_id, doc_id, text in unknown_m:
        if is_garbage_text(text):
            garbage_ids.append(prov_id)

    print(f"  Garbage to mark non-actionable: {len(garbage_ids)}")

    # --- ASHFIELD ---
    print("\n## ASHFIELD")

    cur.execute("""
        SELECT id, document_id, v2_dcp_part, LEFT(provision_text, 100)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%ashfield%'
        AND v2_is_actionable = true
        AND v2_dcp_part = 'unknown'
    """)

    unknown_a = cur.fetchall()
    print(f"\nUnknown part provisions: {len(unknown_a)}")

    for prov_id, doc_id, part, text in unknown_a:
        if is_garbage_text(text):
            garbage_ids.append(prov_id)
        # Try to classify from document_id
        if 'Chapter_B' in (doc_id or ''):
            topic_updates.append((prov_id, None, 'public_domain', 'chapter_b'))

    # --- SUMMARY ---
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"\nTopic updates: {len(topic_updates)}")
    print(f"Garbage to mark non-actionable: {len(garbage_ids)}")

    if topic_updates[:5]:
        print("\nSample topic updates:")
        for prov_id, old, new, source in topic_updates[:5]:
            print(f"  ID {prov_id}: {old} -> {new} (from {source})")

    if args.execute:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'scripts/backups/step4_marrickville_ashfield_{timestamp}.json'
        os.makedirs('scripts/backups', exist_ok=True)

        backup_data = {
            'topic_updates': [(u[0], u[1], u[2]) for u in topic_updates],
            'garbage_ids': garbage_ids
        }
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f)
        print(f"\nBackup saved: {backup_file}")

        # Apply topic updates
        for prov_id, old, new, source in topic_updates:
            cur.execute("UPDATE regulatory_provisions SET v2_topic = %s WHERE id = %s", (new, prov_id))

        # Mark garbage non-actionable
        if garbage_ids:
            cur.execute("UPDATE regulatory_provisions SET v2_is_actionable = false WHERE id = ANY(%s)", (garbage_ids,))

        conn.commit()
        print(f"\nApplied {len(topic_updates)} topic updates")
        print(f"Marked {len(garbage_ids)} as non-actionable")

    conn.close()


if __name__ == '__main__':
    main()
