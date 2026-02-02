#!/usr/bin/env python3
"""
Fix Leichhardt DCP Part D topic tagging

Part D has two sections with different topics:
- Section 1 (pages 2-5): Energy Management → topic='energy'
- Section 2 (pages 6-15): Resource Recovery & Waste → topic='waste_management'

Currently all 96 provisions are tagged as 'energy', but 63 are waste/recycling.

Usage:
    python scripts/fix_leichhardt_part_d_topics.py --dry-run  # Preview changes
    python scripts/fix_leichhardt_part_d_topics.py           # Apply changes
"""

import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Load environment variables
import pathlib
script_dir = pathlib.Path(__file__).parent.absolute()
project_root = script_dir.parent
env_file = project_root / 'frontend-nextjs' / '.env.local'

print(f"Loading env from: {env_file}")
print(f"Env file exists: {env_file.exists()}")

if not env_file.exists():
    raise FileNotFoundError(f"Cannot find .env file at {env_file}")

load_dotenv(env_file, override=True)


def get_db_connection():
    """Get PostgreSQL database connection"""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        raise ValueError("DATABASE_URL not found in environment")

    return psycopg2.connect(db_url, cursor_factory=RealDictCursor)


def analyze_part_d(conn):
    """Analyze current state of Part D provisions"""
    print("=" * 80)
    print("ANALYZING LEICHHARDT PART D PROVISIONS")
    print("=" * 80)

    with conn.cursor() as cur:
        # Get all Part D provisions
        cur.execute("""
            SELECT id, provision_text, v2_topic, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Leichhardt%'
              AND v2_dcp_part = 'Part D'
              AND is_current = TRUE
            ORDER BY pdf_page
        """)

        provisions = cur.fetchall()
        print(f"\nTotal Part D provisions: {len(provisions)}")

        # Count by current topic
        topics = {}
        for p in provisions:
            topic = p['v2_topic'] or 'None'
            topics[topic] = topics.get(topic, 0) + 1

        print("\nCurrent topic distribution:")
        for topic, count in sorted(topics.items(), key=lambda x: -x[1]):
            print(f"  {topic}: {count}")

        # Count by page range (to determine section)
        energy_pages = [p for p in provisions if 2 <= p['pdf_page'] <= 5]
        waste_pages = [p for p in provisions if 6 <= p['pdf_page'] <= 15]
        other_pages = [p for p in provisions if p['pdf_page'] < 2 or p['pdf_page'] > 15]

        print(f"\nPage distribution:")
        print(f"  Pages 2-5 (Energy Section 1): {len(energy_pages)} provisions")
        print(f"  Pages 6-15 (Waste Section 2): {len(waste_pages)} provisions")
        print(f"  Other pages: {len(other_pages)} provisions")

        # Check for waste/recycling keywords in provisions
        waste_keywords = ['waste', 'recycling', 'recyclable', 'rubbish', 'bin', 'disposal',
                          'SWMMP', 'resource recovery', 'minimisation']
        energy_keywords = ['energy', 'solar', 'renewable', 'photovoltaic', 'heating', 'cooling',
                           'thermal', 'electricity', 'power']

        print(f"\nContent analysis (pages 6-15, should be waste):")
        waste_mentions = 0
        energy_mentions = 0
        for p in waste_pages:
            text = p['provision_text'].lower()
            has_waste = any(kw in text for kw in waste_keywords)
            has_energy = any(kw in text for kw in energy_keywords)
            if has_waste:
                waste_mentions += 1
            if has_energy and not has_waste:
                energy_mentions += 1

        if waste_pages:
            print(f"  Provisions with waste keywords: {waste_mentions}/{len(waste_pages)} ({waste_mentions/len(waste_pages)*100:.1f}%)")
            print(f"  Provisions with ONLY energy keywords: {energy_mentions}/{len(waste_pages)} ({energy_mentions/len(waste_pages)*100:.1f}%)")

    return provisions


def fix_part_d_topics(conn, dry_run=True):
    """Fix Part D topic assignments based on page number"""
    print("\n" + "=" * 80)
    if dry_run:
        print("DRY RUN - PREVIEWING CHANGES (no database updates)")
    else:
        print("APPLYING CHANGES TO DATABASE")
    print("=" * 80)

    with conn.cursor() as cur:
        # Get all Part D provisions
        cur.execute("""
            SELECT id, provision_text, v2_topic, pdf_page
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Leichhardt%'
              AND v2_dcp_part = 'Part D'
              AND is_current = TRUE
            ORDER BY pdf_page
        """)

        provisions = cur.fetchall()

        # Categorize by page number
        waste_updates = []   # Pages 6-15

        for p in provisions:
            page = p['pdf_page']
            current_topic = p['v2_topic']

            if 6 <= page <= 15:
                # Section 2: Resource Recovery & Waste Management
                if current_topic != 'waste_management':
                    waste_updates.append(p['id'])

        energy_count = len([p for p in provisions if 2 <= p['pdf_page'] <= 5])

        print(f"\nChanges to apply:")
        print(f"  Keep as 'energy' (pages 2-5): {energy_count} provisions")
        print(f"  Change to 'waste_management' (pages 6-15): {len(waste_updates)} provisions")
        print(f"  No change needed: {len(provisions) - len(waste_updates)} provisions")

        if not dry_run and waste_updates:
            print("\nUpdating database...")

            # Update waste provisions (use IN clause instead of ANY for better compatibility)
            placeholders = ','.join(['%s'] * len(waste_updates))
            cur.execute(f"""
                UPDATE regulatory_provisions
                SET v2_topic = 'waste_management'
                WHERE id IN ({placeholders})
                  AND document_id ILIKE %s
                  AND v2_dcp_part = %s
            """, (*waste_updates, '%Leichhardt%', 'Part D'))

            conn.commit()

            print(f"[OK] Updated {len(waste_updates)} provisions to 'waste_management'")
            print("\nDatabase update complete!")

        elif dry_run:
            print("\n[!] DRY RUN - No changes applied. Run without --dry-run to apply changes.")
            print(f"\nSample provisions that would be changed to 'waste_management':")
            sample_waste = [p for p in provisions if p['id'] in waste_updates[:5]]
            for p in sample_waste:
                print(f"\n  ID {p['id']} (page {p['pdf_page']})")
                print(f"  Current topic: {p['v2_topic']}")
                print(f"  Text: {p['provision_text'][:120]}...")


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Fix Leichhardt Part D topic tagging')
    parser.add_argument('--dry-run', action='store_true',
                       help='Preview changes without updating database')
    parser.add_argument('--analyze-only', action='store_true',
                       help='Only analyze current state, do not fix')

    args = parser.parse_args()

    conn = None
    try:
        conn = get_db_connection()

        # Always analyze first
        analyze_part_d(conn)

        if not args.analyze_only:
            # Apply fixes
            fix_part_d_topics(conn, dry_run=args.dry_run)

            # Re-analyze after changes
            if not args.dry_run:
                print("\n" + "=" * 80)
                print("POST-FIX VERIFICATION")
                analyze_part_d(conn)

    except Exception as e:
        print(f"\n❌ Error: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        if conn:
            conn.close()


if __name__ == '__main__':
    main()
