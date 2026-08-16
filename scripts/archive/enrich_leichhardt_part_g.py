"""
Enrich Leichhardt Part G Section 1-12 provisions.

Strategy:
- 64 site-specific provisions (Sections 2-13) -> Map to specific precinct IDs via text matching
- 382 Section 1 Overview provisions -> Tag as 'PART_G_OVERVIEW' (universal site-specific principles)
"""

import os
import psycopg2
import re
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

# Map site names to precinct IDs (from boundaries table + text analysis)
SITE_KEYWORDS = {
    'C2.2.1.2': ['Annandale Street', 'Annandale St'],
    'C2.2.1.3': ['Johnston Street', 'Johnston St', '233 Johnston', '233A Johnston'],
    'C2.2.1.6': ['Nelson Street', 'Nelson St'],
    'C2.2.1.8': ['Camperdown Distinctive', 'Camperdown Ultimo Collaboration'],
    'C2.2.2.1': ['Darling Street Distinctive'],
    'C2.2.2.2': ['Balmain East'],
    'C2.2.2.6': ['Birchgrove', 'Wharf Road, Birchgrove'],
    'C2.2.3.2': ['West Leichhardt Distinctive'],
    'C2.2.3.5': ['Leichhardt Commercial Distinctive'],
    'C2.2.4.1': ['Catherine Street Distinctive'],
    'C2.2.5.4': ['Iron Cove', 'Rozelle Bay', 'Elkington Park'],
    'C2.2.5.5': ['Rozelle Commercial', '118-124 Terry Street'],
}

# Alternative: Use specific site addresses/names from Part G Sections 2-13
SITE_SPECIFIC_KEYWORDS = {
    'G2_OLD_AMPOL_ROBERT_ST': ['Old Ampol', 'Robert Street, Rozelle'],
    'G3_JANE_STREET': ['Jane Street', '16 Jane Street', '18 Jane Street'],
    'G4_WHARF_ROAD': ['Wharf Road, Birchgrove'],
    'G5_ANKA_TERRY_ST': ['Anka Site', 'Terry Street Rozelle', '118-124 Terry Street'],
    'G6_JOHNSTON_STREET': ['Johnston Street', '233 Johnston', '233A Johnston'],
    'G7_ALLEN_STREET': ['Allen Street'],
    'G8_NORTON_STREET': ['Norton Street'],
    'G9_MARION_STREET': ['Marion Street'],
    'G10_CHESTER_STREET': ['Chester Street'],
    'G11_LONSDALE_BRENAN': ['Lonsdale Street', 'Brenan Street'],
    'G12_PYRMONT_BRIDGE': ['Pyrmont Bridge Road'],
}

def enrich_part_g():
    """Enrich Leichhardt Part G Section 1-12 provisions."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("=" * 80)
    print("ENRICHING LEICHHARDT PART G SECTION 1-12 PROVISIONS")
    print("=" * 80)

    # Get all Part G Section 1-12 provisions
    cur.execute("""
        SELECT id, provision_text
        FROM regulatory_provisions
        WHERE document_id = 'Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
        ORDER BY id;
    """)

    provisions = cur.fetchall()
    print(f"\nTotal Part G Section 1-12 provisions: {len(provisions)}")

    # Track updates
    site_specific_count = 0
    overview_count = 0
    site_matches = {}

    print("\nAnalyzing provisions...")

    for prov_id, text in provisions:
        text_lower = text.lower() if text else ""
        matched = False
        matched_precinct = None

        # Try to match site-specific keywords
        for precinct_id, keywords in SITE_KEYWORDS.items():
            for keyword in keywords:
                if keyword.lower() in text_lower:
                    matched = True
                    matched_precinct = precinct_id
                    break
            if matched:
                break

        if matched and matched_precinct:
            # Update with specific precinct ID
            cur.execute("""
                UPDATE regulatory_provisions
                SET v2_precinct_id = %s
                WHERE id = %s;
            """, (matched_precinct, prov_id))

            site_specific_count += 1
            site_matches[matched_precinct] = site_matches.get(matched_precinct, 0) + 1
        else:
            # Section 1 Overview - universal site-specific principles
            cur.execute("""
                UPDATE regulatory_provisions
                SET v2_precinct_id = 'PART_G_OVERVIEW'
                WHERE id = %s;
            """, (prov_id,))

            overview_count += 1

    conn.commit()

    print("\n" + "=" * 80)
    print("ENRICHMENT RESULTS")
    print("=" * 80)

    print(f"\n[OK] Site-specific provisions: {site_specific_count}")
    if site_matches:
        print("\nPrecinct distribution:")
        for precinct_id in sorted(site_matches.keys()):
            print(f"  {precinct_id}: {site_matches[precinct_id]} provisions")

    print(f"\n[OK] Overview provisions (PART_G_OVERVIEW): {overview_count}")
    print(f"\nTotal enriched: {site_specific_count + overview_count} / {len(provisions)}")

    cur.close()
    conn.close()

    return site_specific_count, overview_count

def verify_enrichment():
    """Verify Part G enrichment."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    # Total Part G provisions
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id = 'Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true;
    """)
    total = cur.fetchone()[0]

    # Provisions with v2_precinct_id populated
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id = 'Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
          AND v2_precinct_id IS NOT NULL;
    """)
    enriched = cur.fetchone()[0]

    # Breakdown by type
    cur.execute("""
        SELECT v2_precinct_id, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id = 'Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
        GROUP BY v2_precinct_id
        ORDER BY v2_precinct_id;
    """)

    breakdown = cur.fetchall()
    print("\nPrecinct ID breakdown:")
    for precinct_id, count in breakdown:
        status = "[Overview]" if precinct_id == 'PART_G_OVERVIEW' else "[Site-specific]"
        print(f"  {status:15} {str(precinct_id):20} {count:4} provisions")

    print(f"\n[OK] Total enriched: {enriched} / {total} ({enriched/total*100:.1f}%)")

    cur.close()
    conn.close()

def main():
    """Main enrichment workflow."""
    print("=" * 80)
    print("LEICHHARDT PART G ENRICHMENT SCRIPT")
    print("=" * 80)
    print("\nThis script will enrich 446 Part G Section 1-12 provisions:")
    print("  - Site-specific provisions (Sections 2-13) -> Specific precinct IDs")
    print("  - Section 1 Overview provisions -> 'PART_G_OVERVIEW'")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return

    # Enrich Part G
    site_count, overview_count = enrich_part_g()

    # Verify results
    verify_enrichment()

    print("\n" + "=" * 80)
    print("ENRICHMENT COMPLETE")
    print("=" * 80)
    print(f"\nResults:")
    print(f"  Site-specific: {site_count} provisions")
    print(f"  Overview: {overview_count} provisions")
    print(f"\nNext step: Update API to include PART_G_OVERVIEW when property is in any Part G site")

if __name__ == '__main__':
    main()
