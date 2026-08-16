#!/usr/bin/env python3
"""
Fix errors found in Ashfield and Marrickville manual review.

Ashfield: 7 errors from sample
Marrickville: 8 errors from sample
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

# Manual review findings
ASHFIELD_FIXES = {
    81179: 'building_design',  # was open_space, about design solutions
    80907: 'building_form',    # was open_space, about performance criteria
    81180: 'building_form',    # was open_space, about performance criteria
    87213: 'commercial',       # was open_space, about car showrooms (Part 11)
    76559: 'commercial',       # was open_space, about neighbourhood shops
    81385: 'building_design',  # was open_space, about design solutions
    87174: 'residential',      # was roofing, about residential flat buildings
}

MARRICKVILLE_FIXES = {
    78353: 'environmental',    # was signage, about biodiversity
    85909: 'signage',          # was safety, about principal tenants naming rights
    78369: 'energy',           # was stormwater, about energy certification
    78410: 'access',           # was setbacks, about access and mobility
    78345: 'signage',          # was safety, "Signs and Advertising Structures"
    85902: 'signage',          # was safety, "Signage must not extend"
    78370: 'energy',           # was stormwater, about energy efficiency
}


def apply_fixes(dry_run=True):
    db_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)

    all_fixes = {**ASHFIELD_FIXES, **MARRICKVILLE_FIXES}

    print("=" * 60)
    if dry_run:
        print("ASHFIELD & MARRICKVILLE FIXES - DRY RUN")
    else:
        print("ASHFIELD & MARRICKVILLE FIXES - APPLYING")
    print("=" * 60)

    print(f"\nAshfield fixes: {len(ASHFIELD_FIXES)}")
    print(f"Marrickville fixes: {len(MARRICKVILLE_FIXES)}")
    print(f"Total: {len(all_fixes)}")

    # Verify and show
    with conn.cursor() as cur:
        for pid, new_topic in all_fixes.items():
            cur.execute("""
                SELECT id, v2_topic, v2_dcp_part, document_id,
                       LEFT(provision_text, 60) as text_preview
                FROM regulatory_provisions
                WHERE id = %s
            """, (pid,))
            p = cur.fetchone()
            if p:
                council = 'Ashfield' if 'Ashfield' in (p['document_id'] or '') else 'Marrickville'
                print(f"\n  [{council}] ID {pid}: {p['v2_topic']} -> {new_topic}")
                print(f"     {p['text_preview']}...")

    if not dry_run:
        with conn.cursor() as cur:
            for pid, new_topic in all_fixes.items():
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id = %s
                """, (new_topic, pid))

        conn.commit()
        print(f"\n[OK] Updated {len(all_fixes)} provisions")
    else:
        print("\n[!] DRY RUN - No changes applied")

    conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    apply_fixes(dry_run=args.dry_run)
