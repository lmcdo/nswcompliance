#!/usr/bin/env python3
"""
Fix topic naming inconsistencies.
Standardize topic names across all councils.
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

# Topic name standardization
TOPIC_RENAMES = {
    'waste_management': 'waste',  # Standardize to 'waste'
    'wsud': 'water',              # WSUD is water-related
    'site_analysis': 'general',   # Site analysis is general
    'mixed_use': 'residential',   # Mixed use often residential
}


def fix_naming(dry_run=True):
    conn = psycopg2.connect(os.environ['DATABASE_URL'], cursor_factory=RealDictCursor)

    print("=" * 70)
    if dry_run:
        print("TOPIC NAMING FIX - DRY RUN")
    else:
        print("TOPIC NAMING FIX - APPLYING")
    print("=" * 70)

    # Check current state
    print("\nCurrent topic distribution:")
    with conn.cursor() as cur:
        cur.execute("""
            SELECT v2_topic, COUNT(*) as count
            FROM regulatory_provisions
            WHERE document_id ILIKE '%%Leichhardt%%'
               OR document_id ILIKE '%%Ashfield%%'
               OR document_id ILIKE '%%Marrickville%%'
            GROUP BY v2_topic
            ORDER BY count DESC
        """)
        for row in cur.fetchall():
            if row['v2_topic'] in TOPIC_RENAMES:
                print(f"  {row['v2_topic']}: {row['count']} -> will rename to {TOPIC_RENAMES[row['v2_topic']]}")
            elif row['count'] < 20:
                print(f"  {row['v2_topic']}: {row['count']} (low count)")

    # Apply renames
    total_renamed = 0
    for old_name, new_name in TOPIC_RENAMES.items():
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as count
                FROM regulatory_provisions
                WHERE v2_topic = %s
                  AND is_current = TRUE
                  AND (document_id ILIKE '%%Leichhardt%%'
                       OR document_id ILIKE '%%Ashfield%%'
                       OR document_id ILIKE '%%Marrickville%%')
            """, (old_name,))
            count = cur.fetchone()['count']

        if count > 0:
            print(f"\n{old_name} -> {new_name}: {count} provisions")

            if not dry_run:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE regulatory_provisions
                        SET v2_topic = %s
                        WHERE v2_topic = %s
                          AND is_current = TRUE
                          AND (document_id ILIKE '%%Leichhardt%%'
                               OR document_id ILIKE '%%Ashfield%%'
                               OR document_id ILIKE '%%Marrickville%%')
                    """, (new_name, old_name))
                total_renamed += count

    if not dry_run:
        conn.commit()
        print(f"\n[OK] Renamed {total_renamed} provisions")
    else:
        print("\n[!] DRY RUN - No changes applied")

    conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    fix_naming(dry_run=args.dry_run)
