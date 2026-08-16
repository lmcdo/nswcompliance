#!/usr/bin/env python3
"""Fix remaining Ashfield None topics (Chapter D headers/precinct names)"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
import pathlib

env_file = pathlib.Path(__file__).parent.parent / 'frontend-nextjs' / '.env.local'
load_dotenv(env_file, override=True)

# Manual assignments for remaining Chapter D provisions
# All are section headers or precinct names -> 'precinct'
MANUAL_ASSIGNMENTS = {
    87220: 'general',     # Using this Guideline - intro text
    87263: 'precinct',    # Part 2 Ashfield East
    87284: 'general',     # Development Servicing - heading
    87301: 'building_form', # PC3. Buildings are: - performance criteria
    87318: 'precinct',    # Croydon Urban Village
    87345: 'general',     # To provide additional guidelines
    87365: 'precinct',    # The Existing Corridor
    87408: 'precinct',    # Section 3: WestConnex
    87416: 'precinct',    # Residual Land Management
    87433: 'precinct',    # Summer Hill Urban Village
    87449: 'precinct',    # Summer Hill Flour Mill Site
    87455: 'precinct',    # Edwards Street B4 Zone
    87467: 'general',     # PC5. Development Servicing
    87472: 'general',     # How to use this Guideline
    87492: 'precinct',    # 120C Old Canterbury Road
}


def apply_fixes(dry_run=True):
    db_url = os.environ.get('DATABASE_URL')
    conn = psycopg2.connect(db_url, cursor_factory=RealDictCursor)

    print("=" * 60)
    if dry_run:
        print("MANUAL FIX - DRY RUN")
    else:
        print("MANUAL FIX - APPLYING")
    print("=" * 60)

    print(f"\nAssignments: {len(MANUAL_ASSIGNMENTS)}")
    for pid, topic in MANUAL_ASSIGNMENTS.items():
        print(f"  {pid} -> {topic}")

    if not dry_run:
        with conn.cursor() as cur:
            for pid, topic in MANUAL_ASSIGNMENTS.items():
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE id = %s
                      AND document_id ILIKE '%%Ashfield%%'
                """, (topic, pid))

        conn.commit()
        print(f"\n[OK] Updated {len(MANUAL_ASSIGNMENTS)} provisions")

        # Verify
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as none_count
                FROM regulatory_provisions
                WHERE document_id ILIKE '%%Ashfield%%'
                  AND v2_topic IS NULL
                  AND is_current = TRUE
            """)
            result = cur.fetchone()
            print(f"\nRemaining None topics: {result['none_count']}")
    else:
        print("\n[!] DRY RUN - No changes applied")

    conn.close()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()
    apply_fixes(dry_run=args.dry_run)
