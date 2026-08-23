#!/usr/bin/env python3
"""
Link Marrickville Part 8 heritage provisions to specific HCAs

Based on extraction: 38 HCAs in Part 8, each in section 8.2.X
Links provisions to heritage_conservation_areas.db_slug
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import re

DB_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres.llzdrxywpziewrzudwhj',
    'password': os.environ['DB_PASSWORD'],
    'host': 'aws-1-ap-southeast-2.pooler.supabase.com',
    'port': 5432
}

# Mapping from DCP HCA number to db_slug (from heritage_conservation_areas table)
HCA_MAPPING = {
    '1': 'the_abergeldie_estate_heritage_conservation_area',
    '2': 'hca_2',
    '3': 'hca_3',
    '4': 'railway_street_petersham_heritage_conservation_area',
    '5': 'hca_5',
    '6': 'hca_6',
    '7': 'hca_7',
    '8': 'hca_8',
    '9': 'hca_9',
    '10': 'hca_10',
    '11': 'hca_11',
    '12': 'hca_12',
    # '13': NO MATCH
    '14': 'hca_14',
    '15': 'hca_15',
    '16': 'hca_16',
    '17': 'kingston_south_heritage_conservation_area',
    '18': 'petersham_south_norwood_estate_heritage_conservation_area',
    '19': 'hca_19',
    '20': 'audley_street_south_bayswater_estate_heritage_conservation_area',
    '21': 'hca_21',
    '22': 'hca_22',
    '23': 'hca_23',
    # '24': NO MATCH
    '25': 'hca_25',
    '26': 'hca_26',
    '27': 'hca_27',
    '28': 'hca_28',
    '29': 'south_dulwich_hill_heritage_conservation_area',
    '30': 'hca_30',
    '31': 'hca_31',
    '32': 'hca_32',
    '33': 'hca_33',
    '34': 'hca_34',
    '35': 'hca_35',
    # '36': NO MATCH
    # '37': NO MATCH
    # '38': NO MATCH
}

def extract_hca_number(text):
    """Extract HCA number from provision text"""
    # Pattern: "Heritage Conservation Area - HCA X" or "HCA X"
    pattern = r'(?:Heritage Conservation Area|HCA)\s*[-–]\s*HCA\s*(\d+)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        return match.group(1)
    return None

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("=" * 80)
    print("LINK MARRICKVILLE HERITAGE PROVISIONS TO HCAs")
    print("=" * 80)
    print()

    # Get all Part 8 heritage provisions
    cur.execute("""
        SELECT id, provision_text, v2_heritage_hca
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Marrickville%'
          AND v2_dcp_part = 'Part 8'
          AND v2_topic = 'heritage'
          AND v2_is_actionable = true
        ORDER BY id;
    """)

    provisions = cur.fetchall()
    print(f"Total Part 8 heritage provisions: {len(provisions)}")
    print()

    # Process each provision
    hca_counts = {}
    updated_count = 0
    skipped_count = 0
    no_match_count = 0

    for prov in provisions:
        hca_num = extract_hca_number(prov['provision_text'])

        if hca_num:
            if hca_num in HCA_MAPPING:
                db_slug = HCA_MAPPING[hca_num]

                # Update provision
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_heritage_hca = %s
                    WHERE id = %s;
                """, (db_slug, prov['id']))

                updated_count += 1

                # Track counts
                if hca_num not in hca_counts:
                    hca_counts[hca_num] = 0
                hca_counts[hca_num] += 1

            else:
                # HCA number found but no matching db_slug
                no_match_count += 1
        else:
            # No HCA number in text (general provision)
            skipped_count += 1

    conn.commit()

    print(f"Results:")
    print(f"  Updated: {updated_count} provisions")
    print(f"  Skipped (no HCA reference): {skipped_count} provisions")
    print(f"  No match in mapping: {no_match_count} provisions")
    print()

    print("Provisions by HCA:")
    for hca_num in sorted(hca_counts.keys(), key=int):
        count = hca_counts[hca_num]
        slug = HCA_MAPPING[hca_num]
        print(f"  HCA {hca_num:2s}: {count:3d} provisions -> {slug}")

    print()

    # Verify
    print("=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE v2_heritage_hca IS NOT NULL) as with_hca,
            COUNT(*) FILTER (WHERE v2_heritage_hca IS NULL) as without_hca,
            COUNT(*) as total
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Marrickville%'
          AND v2_dcp_part = 'Part 8'
          AND v2_topic = 'heritage'
          AND v2_is_actionable = true;
    """)

    stats = cur.fetchone()
    print()
    print(f"Part 8 heritage provisions:")
    print(f"  With v2_heritage_hca: {stats['with_hca']}")
    print(f"  Without v2_heritage_hca: {stats['without_hca']} (general controls)")
    print(f"  Total: {stats['total']}")
    print()

    # Show distinct HCA slugs
    cur.execute("""
        SELECT DISTINCT v2_heritage_hca, COUNT(*) as count
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Marrickville%'
          AND v2_dcp_part = 'Part 8'
          AND v2_topic = 'heritage'
          AND v2_is_actionable = true
          AND v2_heritage_hca IS NOT NULL
        GROUP BY v2_heritage_hca
        ORDER BY v2_heritage_hca
        LIMIT 10;
    """)

    print("Sample HCA slugs:")
    for row in cur.fetchall():
        print(f"  {row['v2_heritage_hca']:50s}: {row['count']} provisions")

    print()
    print("=" * 80)
    print("[COMPLETE]")
    print("=" * 80)

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
