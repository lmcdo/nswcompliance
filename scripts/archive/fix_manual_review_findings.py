#!/usr/bin/env python3
"""
Fix issues found during manual review.

From 40 samples reviewed:
- No keywords found: 19/20 correct (95%)
- Wrong topic flagged: 13/20 correct (65%)

Actual errors to fix: 7 provisions
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

# Manual review findings - confirmed errors
FIXES = {
    # From "wrong topic" review
    80361: 'sustainability',  # was residential, about food production/community gardens
    79796: 'trees',           # was open_space, explicitly about trees
    80347: 'sustainability',  # was open_space, about sustainability
    80355: 'heritage',        # was food_premises, about industrial heritage
    80423: 'precinct',        # was residential, describes waterfront area
    80366: 'sustainability',  # was residential, about community gardens/permaculture
    80567: 'general',         # was open_space, background info about development proposals
}


def apply_fixes(dry_run=True):
    db_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)

    print("=" * 60)
    if dry_run:
        print("MANUAL REVIEW FIXES - DRY RUN")
    else:
        print("MANUAL REVIEW FIXES - APPLYING")
    print("=" * 60)

    print(f"\nFixes to apply: {len(FIXES)}")

    # Verify these exist and show current state
    with conn.cursor() as cur:
        for pid, new_topic in FIXES.items():
            cur.execute("""
                SELECT id, v2_topic, v2_dcp_part,
                       LEFT(provision_text, 80) as text_preview
                FROM regulatory_provisions
                WHERE id = %s
            """, (pid,))
            p = cur.fetchone()
            if p:
                print(f"\n  ID {pid}: {p['v2_topic']} -> {new_topic}")
                print(f"     Part: {p['v2_dcp_part']}")
                print(f"     Text: {p['text_preview']}...")
            else:
                print(f"\n  ID {pid}: NOT FOUND")

    if not dry_run:
        with conn.cursor() as cur:
            for pid, new_topic in FIXES.items():
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id = %s
                """, (new_topic, pid))

        conn.commit()
        print(f"\n[OK] Updated {len(FIXES)} provisions")
    else:
        print("\n[!] DRY RUN - No changes applied")

    conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    apply_fixes(dry_run=args.dry_run)
