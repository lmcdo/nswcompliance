"""
Enrich v2_precinct_id for Marrickville and Leichhardt only (skip Ashfield).

Focus on the 1,303 provisions that can be reliably extracted, skip the 133 Ashfield
provisions that require manual mapping.
"""

import os
import re
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

def extract_marrickville_precinct(document_id):
    """
    Extract precinct number from Marrickville document_id.

    Examples:
    - "Marrickville_DCP_2011_-_9_12_..." → "12_"
    - "Marrickville__DCP__2011__-__9__12__..." → "12_" (double underscores)
    - "Marrickville_DCP_2011_-_2_9_..." → "0_" (intro/community safety)
    """
    # Pattern 1: __9__XX__ or _9_XX_ (standard precinct format)
    match = re.search(r'[_]{1,2}9[_]{1,2}(\d+)[_]{1,2}', document_id)
    if match:
        return f"{match.group(1)}_"

    # Pattern 2: __2__9__ or _2_9_ (intro/community safety → precinct "0_")
    match = re.search(r'[_]{1,2}2[_]{1,2}9[_]{1,2}', document_id)
    if match:
        return "0_"

    # Pattern 3: __9.XX__ or _9.XX_ (dot separator for precincts 43, 48)
    match = re.search(r'[_]{1,2}9\.(\d+)[_]{1,2}', document_id)
    if match:
        return f"{match.group(1)}_"

    return None

def extract_leichhardt_precinct(document_id):
    """
    Extract precinct code from Leichhardt document_id.

    Examples:
    - "Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_1_..." → "C2.2.1.1"
    """
    # Pattern: C2_2_X_X (with underscores, needs conversion to dots)
    match = re.search(r'_C2_2_(\d+)_(\d+)_', document_id)
    if match:
        return f"C2.2.{match.group(1)}.{match.group(2)}"

    # The "Part G Section 1-12" document has provisions that belong to multiple precincts
    # but the document_id doesn't contain the precinct code. We'll need to map these manually
    # or use a different strategy (e.g., provision text analysis, PDF page ranges)
    # For now, skip these provisions.

    return None

def enrich_marrickville():
    """Enrich Marrickville precinct provisions."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("\n" + "=" * 80)
    print("ENRICHING MARRICKVILLE PRECINCT IDS")
    print("=" * 80)

    # Get all Marrickville precinct provisions
    cur.execute("""
        SELECT id, document_id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Marrickville%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true;
    """)

    provisions = cur.fetchall()
    print(f"\nFound {len(provisions)} Marrickville precinct provisions")

    # Track updates
    updated_count = 0
    failed_count = 0
    precinct_counts = {}

    for prov_id, document_id in provisions:
        precinct_id = extract_marrickville_precinct(document_id)

        if precinct_id:
            # Update the provision
            cur.execute("""
                UPDATE regulatory_provisions
                SET v2_precinct_id = %s
                WHERE id = %s;
            """, (precinct_id, prov_id))

            updated_count += 1
            precinct_counts[precinct_id] = precinct_counts.get(precinct_id, 0) + 1
        else:
            failed_count += 1
            print(f"  WARNING: Could not extract precinct from: {document_id}")

    conn.commit()

    print(f"\n[OK] Updated {updated_count} provisions")
    print(f"[FAILED] Failed {failed_count} provisions")

    if precinct_counts:
        print(f"\nPrecinct distribution ({len(precinct_counts)} unique precincts):")
        for precinct_id in sorted(precinct_counts.keys(), key=lambda x: int(x.replace('_', ''))):
            print(f"  {precinct_id}: {precinct_counts[precinct_id]} provisions")

    cur.close()
    conn.close()

    return updated_count, failed_count

def enrich_leichhardt():
    """Enrich Leichhardt precinct provisions."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("\n" + "=" * 80)
    print("ENRICHING LEICHHARDT PRECINCT IDS")
    print("=" * 80)

    # Get all Leichhardt precinct provisions
    cur.execute("""
        SELECT id, document_id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true;
    """)

    provisions = cur.fetchall()
    print(f"\nFound {len(provisions)} Leichhardt precinct provisions")

    # Track updates
    updated_count = 0
    failed_count = 0
    precinct_counts = {}

    for prov_id, document_id in provisions:
        precinct_id = extract_leichhardt_precinct(document_id)

        if precinct_id:
            # Update the provision
            cur.execute("""
                UPDATE regulatory_provisions
                SET v2_precinct_id = %s
                WHERE id = %s;
            """, (precinct_id, prov_id))

            updated_count += 1
            precinct_counts[precinct_id] = precinct_counts.get(precinct_id, 0) + 1
        else:
            failed_count += 1
            # Don't print every failure (447 provisions from Part G Section 1-12)

    conn.commit()

    print(f"\n[OK] Updated {updated_count} provisions")
    print(f"[FAILED] Failed {failed_count} provisions")
    print(f"  (Note: {failed_count} provisions from 'Part G Section 1-12' document need manual mapping)")

    if precinct_counts:
        print(f"\nPrecinct distribution ({len(precinct_counts)} unique precincts):")
        for precinct_id in sorted(precinct_counts.keys()):
            print(f"  {precinct_id}: {precinct_counts[precinct_id]} provisions")

    cur.close()
    conn.close()

    return updated_count, failed_count

def verify_enrichment():
    """Verify enrichment results."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

    total_enriched = 0
    total_provisions = 0

    for council in ['Marrickville', 'Leichhardt', 'Ashfield']:
        # Total precinct provisions
        cur.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
              AND v2_dcp_layer = 'precinct'
              AND v2_is_actionable = true;
        """, (f'%{council}%',))
        total = cur.fetchone()[0]

        # Provisions with v2_precinct_id populated
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
        status = "[OK]" if percentage == 100 else ("[WARN]" if percentage > 0 else "[SKIP]")

        print(f"\n{council}:")
        print(f"  Total: {total} provisions")
        print(f"  Enriched: {enriched} provisions ({percentage:.1f}%)")
        print(f"  Status: {status}")

        total_enriched += enriched
        total_provisions += total

    print(f"\n{'='*80}")
    print(f"TOTAL ENRICHED: {total_enriched} / {total_provisions} provisions ({total_enriched/total_provisions*100:.1f}%)")
    print(f"{'='*80}")

    cur.close()
    conn.close()

def main():
    """Main enrichment workflow."""
    print("=" * 80)
    print("PRECINCT ID ENRICHMENT SCRIPT V2")
    print("=" * 80)
    print("\nThis script will populate v2_precinct_id for:")
    print("  - Marrickville: 686 provisions (expected ~100% success)")
    print("  - Leichhardt: 617 provisions (expected ~27% success)")
    print("  - Ashfield: SKIPPED (133 provisions need manual mapping)")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return

    # Enrich Marrickville and Leichhardt
    m_updated, m_failed = enrich_marrickville()
    l_updated, l_failed = enrich_leichhardt()

    # Verify results
    verify_enrichment()

    print("\n" + "=" * 80)
    print("ENRICHMENT COMPLETE")
    print("=" * 80)
    print(f"\nResults:")
    print(f"  Marrickville: {m_updated} provisions enriched ({m_failed} failed)")
    print(f"  Leichhardt: {l_updated} provisions enriched ({l_failed} failed)")
    print(f"  Ashfield: Skipped (needs manual mapping)")
    print(f"\nNext steps:")
    print(f"  1. Leichhardt 'Part G Section 1-12' document needs PDF page-based mapping")
    print(f"  2. Ashfield Chapter D needs provision text analysis or manual assignment")
    print(f"  3. Precinct filtering now works for {m_updated + l_updated} provisions")

if __name__ == '__main__':
    main()
