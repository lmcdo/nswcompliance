#!/usr/bin/env python3
"""
Link Ashfield Chapter E1 heritage provisions to specific HCAs

Ashfield embeds HCA codes in provision text as "C## [HCA Name] Heritage Conservation Area"
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

def extract_hca_code(text):
    """Extract C-code from provision text like 'C30 Hammond Park Estate...'"""
    # Pattern: C## followed by space and uppercase letter (start of HCA name)
    match = re.search(r'\b(C\d{2,3})\s+[A-Z]', text)
    if match:
        return match.group(1)
    return None

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    print("=" * 80)
    print("LINK ASHFIELD HERITAGE PROVISIONS TO HCAs")
    print("=" * 80)
    print()

    # Get provisions that mention HCA names
    cur.execute("""
        SELECT id, provision_text
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_part = 'Chapter E1'
          AND v2_topic = 'heritage'
          AND v2_is_actionable = true
          AND provision_text ~ 'C[0-9]{2,3}\s+[A-Z].*Heritage Conservation'
        ORDER BY id;
    """)

    provisions = cur.fetchall()
    print(f"Provisions with HCA references: {len(provisions)}")
    print()

    updated_count = 0
    matched_count = 0
    no_match_count = 0

    hca_stats = {}

    for prov in provisions:
        c_code = extract_hca_code(prov['provision_text'])

        if c_code:
            # Look up db_slug by h_id
            cur.execute("""
                SELECT h_id, h_name, db_slug
                FROM heritage_conservation_areas
                WHERE h_id = %s;
            """, (c_code,))

            result = cur.fetchone()

            if result:
                # Update provision
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_heritage_hca = %s
                    WHERE id = %s;
                """, (result['db_slug'], prov['id']))

                updated_count += 1
                matched_count += 1

                # Track stats
                if c_code not in hca_stats:
                    hca_stats[c_code] = {
                        'name': result['h_name'],
                        'slug': result['db_slug'],
                        'count': 0
                    }
                hca_stats[c_code]['count'] += 1
            else:
                no_match_count += 1
                if no_match_count <= 5:
                    print(f"  No match for {c_code}: {prov['provision_text'][:80]}...")

    conn.commit()

    print(f"\nResults:")
    print(f"  Updated: {updated_count} provisions")
    print(f"  Matched HCA codes: {matched_count}")
    print(f"  No match: {no_match_count}")
    print()

    print("Provisions by HCA:")
    for c_code in sorted(hca_stats.keys(), key=lambda x: int(x[1:])):
        hca = hca_stats[c_code]
        print(f"  {c_code}: {hca['count']:2d} provisions -> {hca['slug'][:50]}")

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
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_part = 'Chapter E1'
          AND v2_topic = 'heritage'
          AND v2_is_actionable = true;
    """)

    stats = cur.fetchone()
    print()
    print(f"Chapter E1 heritage provisions:")
    print(f"  With v2_heritage_hca: {stats['with_hca']}")
    print(f"  Without v2_heritage_hca: {stats['without_hca']} (general controls)")
    print(f"  Total: {stats['total']}")
    print()

    print("=" * 80)
    print("[COMPLETE]")
    print("=" * 80)

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
