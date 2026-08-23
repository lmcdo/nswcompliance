#!/usr/bin/env python3
"""DQ-15: Normalize topic case to Title Case across all councils."""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import psycopg2

LOCAL_DB = f"postgresql://{os.environ.get('DB_USER', 'postgres')}:{os.environ['DB_PASSWORD']}@{os.environ.get('DB_HOST', '127.0.0.1')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'nsw_planning')}"

def main():
    conn = psycopg2.connect(LOCAL_DB)
    cur = conn.cursor()

    print('=' * 60)
    print('DQ-15: NORMALIZING TOPIC CASE')
    print('=' * 60)

    # Get all unique topics with their counts
    cur.execute("""
        SELECT LOWER(v2_topic), array_agg(DISTINCT v2_topic), COUNT(*)
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
          AND v2_topic IS NOT NULL
        GROUP BY LOWER(v2_topic)
        HAVING COUNT(DISTINCT v2_topic) > 1
        ORDER BY COUNT(*) DESC
    """)

    case_issues = cur.fetchall()
    print(f'\nFound {len(case_issues)} topics with case variants')

    # Normalize to Title Case
    total_updated = 0
    for lower_topic, variants, count in case_issues:
        # Title case the topic
        normalized = lower_topic.title()
        
        # Handle special cases
        special_cases = {
            'Building_Form': 'Building Form',
            'Site_Analysis': 'Site Analysis', 
        }
        if normalized in special_cases:
            normalized = special_cases[normalized]
        
        print(f'\n  {variants} -> "{normalized}" ({count} provisions)')
        
        # Update all variants to normalized form
        for variant in variants:
            if variant != normalized:
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_topic = %s
                    WHERE v2_topic = %s
                """, (normalized, variant))
                updated = cur.rowcount
                total_updated += updated
                print(f'    Updated {updated} from "{variant}"')

    print(f'\n{"=" * 60}')
    print(f'Total provisions updated: {total_updated}')

    # Also fix building_form -> Building Form
    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_topic = 'Building Form'
        WHERE v2_topic = 'building_form'
    """)
    bf_updated = cur.rowcount
    if bf_updated > 0:
        print(f'Fixed building_form -> Building Form: {bf_updated}')
        total_updated += bf_updated

    # Commit
    conn.commit()
    print('\nChanges committed!')

    # Verify
    cur.execute("""
        SELECT LOWER(v2_topic), array_agg(DISTINCT v2_topic)
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
          AND v2_topic IS NOT NULL
        GROUP BY LOWER(v2_topic)
        HAVING COUNT(DISTINCT v2_topic) > 1
    """)
    remaining = cur.fetchall()
    if remaining:
        print(f'\nWARNING: Still have {len(remaining)} topics with variants')
        for r in remaining:
            print(f'  {r[0]}: {r[1]}')
    else:
        print('\nAll topics normalized successfully!')

    conn.close()

if __name__ == '__main__':
    main()
