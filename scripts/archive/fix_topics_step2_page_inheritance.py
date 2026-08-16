#!/usr/bin/env python3
"""
STEP 2: PAGE-BASED TOPIC INHERITANCE

For Leichhardt Part C Section 1 provisions without markers:
- Find marked provisions on the same page
- Inherit topic from the marker

Run with --execute to actually make changes.
"""
import os
import sys
import re
import json
from datetime import datetime
from collections import defaultdict

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


def get_topic_from_marker(marker):
    """Get topic from marker string."""
    if not marker:
        return None
    m = re.match(r'^(C\d+)', marker.strip().upper())
    if m:
        return LEICHHARDT_MARKER_TOPICS.get(m.group(1))
    return None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='Actually make changes')
    args = parser.parse_args()

    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor()

    print("="*80)
    print("STEP 2: PAGE-BASED TOPIC INHERITANCE")
    print("="*80)

    if not args.execute:
        print("\n*** DRY RUN - No changes will be made ***\n")

    # Build page → topic mapping from marked provisions
    cur.execute("""
        SELECT pdf_page, v2_marker
        FROM regulatory_provisions
        WHERE document_id ILIKE '%leichhardt%'
        AND v2_is_actionable = true
        AND v2_dcp_part = 'Part C Section 1'
        AND v2_marker IS NOT NULL AND v2_marker != ''
        AND pdf_page IS NOT NULL
    """)

    page_topics = {}
    for page, marker in cur.fetchall():
        topic = get_topic_from_marker(marker)
        if topic and page:
            # If multiple markers on a page, keep first one found
            if page not in page_topics:
                page_topics[page] = topic

    print(f"Pages with markers: {len(page_topics)}")

    # Get unmarked provisions
    cur.execute("""
        SELECT id, pdf_page, v2_topic
        FROM regulatory_provisions
        WHERE document_id ILIKE '%leichhardt%'
        AND v2_is_actionable = true
        AND v2_dcp_part = 'Part C Section 1'
        AND (v2_marker IS NULL OR v2_marker = '')
        AND pdf_page IS NOT NULL
    """)

    unmarked = cur.fetchall()
    print(f"Unmarked provisions with pages: {len(unmarked)}")

    # Find which can inherit
    updates = []
    cannot_inherit = []

    for prov_id, page, current_topic in unmarked:
        if page in page_topics:
            new_topic = page_topics[page]
            if new_topic != current_topic:
                updates.append((prov_id, current_topic, new_topic, page))
        else:
            cannot_inherit.append((prov_id, page))

    print(f"\nCan inherit (will update): {len(updates)}")
    print(f"Cannot inherit (no marker on page): {len(cannot_inherit)}")

    if updates[:5]:
        print("\nSample updates:")
        for prov_id, old, new, page in updates[:5]:
            print(f"  ID {prov_id} (page {page}): {old} -> {new}")

    if cannot_inherit:
        pages_without = sorted(set(p for _, p in cannot_inherit))
        print(f"\nPages without markers: {pages_without[:20]}...")

    if args.execute and updates:
        # Create backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'scripts/backups/step2_inheritance_backup_{timestamp}.json'
        os.makedirs('scripts/backups', exist_ok=True)

        backup_data = {
            'updates': [(u[0], u[1], u[2]) for u in updates]
        }
        with open(backup_file, 'w') as f:
            json.dump(backup_data, f)
        print(f"\nBackup saved: {backup_file}")

        # Update
        for prov_id, old_topic, new_topic, page in updates:
            cur.execute("""
                UPDATE regulatory_provisions
                SET v2_topic = %s
                WHERE id = %s
            """, (new_topic, prov_id))

        conn.commit()
        print(f"\nUpdated {len(updates)} provisions")

    conn.close()


if __name__ == '__main__':
    main()
