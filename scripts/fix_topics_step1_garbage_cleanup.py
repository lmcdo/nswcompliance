#!/usr/bin/env python3
"""
STEP 1: GARBAGE CLEANUP

Mark non-control provisions as v2_is_actionable = false:
- TOC entries (contain "......")
- Intro paragraphs that aren't controls
- "Error! Reference source not found" entries
- Part A introduction content

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

def is_garbage(text, dcp_part):
    """Determine if a provision is garbage (not a real control)."""
    if not text:
        return True, 'empty'

    text = text.strip()

    # TOC entries
    if '......' in text:
        return True, 'toc'

    # Section headers
    if text.startswith('SECTION') and 'PROVISIONS' in text:
        return True, 'section_header'

    # Error extraction artifacts
    if 'Error! Reference source not found' in text:
        return True, 'extraction_error'

    # Part A intro (should already be unknown part)
    if dcp_part == 'unknown' and text.startswith('A1.'):
        return True, 'part_a_intro'

    # Generic DCP intro text
    intro_patterns = [
        r'^This Development Control Plan (is|does|applies|complements)',
        r'^The following Plans are repealed',
        r'^Subject to clause',
        r'^A reference in this',
    ]
    for pattern in intro_patterns:
        if re.match(pattern, text):
            return True, 'intro_text'

    # Figure/table references only (not controls)
    if re.match(r'^(Figure|FIGURE|Table|TABLE)\s+\w+:', text):
        return True, 'figure_table_ref'

    return False, None


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--execute', action='store_true', help='Actually make changes')
    args = parser.parse_args()

    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor()

    print("="*80)
    print("STEP 1: GARBAGE CLEANUP")
    print("="*80)

    if not args.execute:
        print("\n*** DRY RUN - No changes will be made ***\n")

    # Get all actionable provisions
    cur.execute("""
        SELECT id, v2_dcp_part, LEFT(provision_text, 500)
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
        AND (document_id ILIKE '%leichhardt%'
             OR document_id ILIKE '%ashfield%'
             OR document_id ILIKE '%marrickville%')
    """)

    provisions = cur.fetchall()
    print(f"Total actionable provisions: {len(provisions)}")

    garbage_by_type = {}
    garbage_ids = []

    for prov_id, dcp_part, text in provisions:
        is_garb, garb_type = is_garbage(text, dcp_part)
        if is_garb:
            if garb_type not in garbage_by_type:
                garbage_by_type[garb_type] = []
            garbage_by_type[garb_type].append((prov_id, text[:60] if text else ''))
            garbage_ids.append(prov_id)

    print(f"\nGarbage found: {len(garbage_ids)}")
    print("\nBy type:")
    for garb_type, items in sorted(garbage_by_type.items(), key=lambda x: -len(x[1])):
        print(f"  {garb_type}: {len(items)}")
        for prov_id, preview in items[:2]:
            print(f"    ID {prov_id}: {preview}...")

    if args.execute and garbage_ids:
        # Create backup
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_file = f'scripts/backups/step1_garbage_backup_{timestamp}.json'
        os.makedirs('scripts/backups', exist_ok=True)

        cur.execute("""
            SELECT id, v2_is_actionable FROM regulatory_provisions
            WHERE id = ANY(%s)
        """, (garbage_ids,))
        backup_data = {'ids': garbage_ids, 'original_values': {str(r[0]): r[1] for r in cur.fetchall()}}

        with open(backup_file, 'w') as f:
            json.dump(backup_data, f)
        print(f"\nBackup saved: {backup_file}")

        # Update
        cur.execute("""
            UPDATE regulatory_provisions
            SET v2_is_actionable = false
            WHERE id = ANY(%s)
        """, (garbage_ids,))

        conn.commit()
        print(f"\nUpdated {len(garbage_ids)} provisions to v2_is_actionable = false")

    # Verify new counts
    cur.execute("""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE v2_is_actionable = true
        AND (document_id ILIKE '%leichhardt%'
             OR document_id ILIKE '%ashfield%'
             OR document_id ILIKE '%marrickville%')
    """)
    new_count = cur.fetchone()[0]
    print(f"\nActionable provisions after cleanup: {new_count}")

    conn.close()


if __name__ == '__main__':
    main()
