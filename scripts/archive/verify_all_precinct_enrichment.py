"""
Complete verification of precinct enrichment across all councils.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')

def get_db_connection():
    """Create database connection using environment variables."""
    return psycopg2.connect(
        host=os.getenv('PGHOST'),
        database=os.getenv('PGDATABASE'),
        user=os.getenv('PGUSER'),
        password=os.getenv('PGPASSWORD'),
        port=os.getenv('PGPORT')
    )

def main():
    """Complete verification report."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("=" * 80)
    print("COMPLETE PRECINCT ENRICHMENT VERIFICATION")
    print("=" * 80)

    # Overall summary
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true;
    """)
    total_precinct = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
          AND v2_precinct_id IS NOT NULL;
    """)
    total_enriched = cur.fetchone()[0]

    print(f"\nOVERALL STATUS:")
    print(f"  Total precinct provisions: {total_precinct}")
    print(f"  Enriched: {total_enriched} ({total_enriched/total_precinct*100:.1f}%)")
    print(f"  Remaining: {total_precinct - total_enriched}")

    # By council
    print("\n" + "=" * 80)
    print("BY COUNCIL")
    print("=" * 80)

    for council in ['Marrickville', 'Leichhardt', 'Ashfield']:
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
              AND v2_dcp_layer = 'precinct'
              AND v2_is_actionable = true;
        """, (f'%{council}%',))
        total = cur.fetchone()[0]

        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
              AND v2_dcp_layer = 'precinct'
              AND v2_is_actionable = true
              AND v2_precinct_id IS NOT NULL;
        """, (f'%{council}%',))
        enriched = cur.fetchone()[0]

        percentage = (enriched / total * 100) if total > 0 else 0
        status = "[OK]" if percentage == 100 else ("[PARTIAL]" if percentage > 0 else "[NONE]")

        print(f"\n{council}:")
        print(f"  Status: {status}")
        print(f"  Total: {total} provisions")
        print(f"  Enriched: {enriched} ({percentage:.1f}%)")
        print(f"  Remaining: {total - enriched}")

    # Leichhardt breakdown
    print("\n" + "=" * 80)
    print("LEICHHARDT DETAILED BREAKDOWN")
    print("=" * 80)

    # Individual documents
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND document_id LIKE '%C2_2_%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
          AND v2_precinct_id IS NOT NULL;
    """)
    individual_docs = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id = 'Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
          AND v2_precinct_id IS NOT NULL;
    """)
    part_g_enriched = cur.fetchone()[0]

    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id = 'Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
          AND v2_precinct_id = 'PART_G_OVERVIEW';
    """)
    part_g_overview = cur.fetchone()[0]

    print(f"\nIndividual documents (C2_2_X_X): {individual_docs} provisions")
    print(f"Part G Section 1-12: {part_g_enriched} provisions")
    print(f"  - Site-specific: {part_g_enriched - part_g_overview} provisions")
    print(f"  - Overview (PART_G_OVERVIEW): {part_g_overview} provisions")

    # Unique precinct IDs
    print("\n" + "=" * 80)
    print("UNIQUE PRECINCT IDS")
    print("=" * 80)

    for council in ['Marrickville', 'Leichhardt', 'Ashfield']:
        cur.execute("""
            SELECT COUNT(DISTINCT v2_precinct_id)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
              AND v2_dcp_layer = 'precinct'
              AND v2_is_actionable = true
              AND v2_precinct_id IS NOT NULL;
        """, (f'%{council}%',))
        unique_precincts = cur.fetchone()[0]

        print(f"{council}: {unique_precincts} unique precinct IDs")

    print("\n" + "=" * 80)
    print("VERIFICATION COMPLETE")
    print("=" * 80)

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
