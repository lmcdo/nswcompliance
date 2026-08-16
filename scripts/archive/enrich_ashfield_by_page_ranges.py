"""
Enrich Ashfield precinct provisions using PDF page range mapping.

Based on text analysis of Part mentions, map provisions to Parts 1-13
using their pdf_page value.
"""

import os
import psycopg2
from dotenv import load_dotenv

load_dotenv('frontend-nextjs/.env.local')

def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('PGHOST'),
        database=os.getenv('PGDATABASE'),
        user=os.getenv('PGUSER'),
        password=os.getenv('PGPASSWORD'),
        port=os.getenv('PGPORT')
    )

# Define page range boundaries based on Part mention analysis
# Format: 'Part X': (start_page, end_page)
PAGE_RANGES = {
    'Part 1': (4, 41),      # Ashfield Town Centre (5 mentions, starts page 4)
    'Part 2': (42, 58),     # Ashfield East (2 mentions, starts page 42)
    'Part 3': (59, 84),     # Ashfield West (4 mentions, pages 59-65, gap to 84)
    'Part 4': (85, 107),    # Croydon Urban Village (5 mentions, pages 85-111)
    'Part 6': (108, 156),   # Parramatta Road Enterprise (25 mentions, pages 108-157)
    'Part 7': (157, 169),   # Hurlstone Park (1 mention, page 157)
    'Part 8': (170, 181),   # Summer Hill Urban Village (2 mentions, page 170)
    'Part 9': (182, 192),   # Summer Hill Flour Mill (3 mentions, pages 182-184)
    # Part 10: No mentions found - may not exist in this document
    'Part 12': (193, 196),  # Smith Street (actual mention at 193, not 170)
    'Part 13': (197, 197),  # 120C Old Canterbury (1 mention, page 197)
}

def enrich_ashfield():
    """Enrich Ashfield provisions using page range mapping."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("=" * 80)
    print("ASHFIELD PAGE RANGE ENRICHMENT")
    print("=" * 80)

    # Get all Ashfield provisions
    cur.execute("""
        SELECT id, pdf_page
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
        ORDER BY pdf_page, id;
    """)

    provisions = cur.fetchall()
    print(f"\nTotal provisions: {len(provisions)}")
    print(f"Page range: {provisions[0][1]} - {provisions[-1][1]}")

    # Track assignments
    part_counts = {part: 0 for part in PAGE_RANGES.keys()}
    unassigned = []

    print("\n" + "=" * 80)
    print("ASSIGNING PROVISIONS TO PARTS")
    print("=" * 80)

    for prov_id, page in provisions:
        assigned = False

        # Find which Part this page belongs to
        for part, (start, end) in PAGE_RANGES.items():
            if start <= page <= end:
                # Update provision with Part
                cur.execute("""
                    UPDATE regulatory_provisions
                    SET v2_precinct_id = %s
                    WHERE id = %s;
                """, (part, prov_id))

                part_counts[part] += 1
                assigned = True
                break

        if not assigned:
            unassigned.append((prov_id, page))

    conn.commit()

    # Print results
    print("\n" + "=" * 80)
    print("ENRICHMENT RESULTS")
    print("=" * 80)

    total_assigned = sum(part_counts.values())
    print(f"\n[OK] Total assigned: {total_assigned}/{len(provisions)} ({total_assigned/len(provisions)*100:.1f}%)")

    print("\nPart distribution:")
    for part in sorted(PAGE_RANGES.keys(), key=lambda x: int(x.split()[1])):
        start, end = PAGE_RANGES[part]
        count = part_counts[part]
        status = "[OK]" if count > 0 else "[NONE]"
        print(f"  {status} {part:8} (pages {start:3d}-{end:3d}): {count:3d} provisions")

    if unassigned:
        print(f"\n[WARN] Unassigned provisions: {len(unassigned)}")
        print("\nUnassigned pages:")
        for prov_id, page in unassigned[:10]:  # First 10
            print(f"  ID {prov_id}, page {page}")

    cur.close()
    conn.close()

    return total_assigned, len(unassigned)

def verify_enrichment():
    """Verify Ashfield enrichment."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("\n" + "=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    # Total Ashfield provisions
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true;
    """)
    total = cur.fetchone()[0]

    # Enriched
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
          AND v2_precinct_id IS NOT NULL;
    """)
    enriched = cur.fetchone()[0]

    percentage = (enriched / total * 100) if total > 0 else 0
    print(f"\nAshfield precinct provisions:")
    print(f"  Total: {total}")
    print(f"  Enriched: {enriched} ({percentage:.1f}%)")
    print(f"  Remaining: {total - enriched}")

    # Unique Parts
    cur.execute("""
        SELECT DISTINCT v2_precinct_id
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
          AND v2_precinct_id IS NOT NULL
        ORDER BY v2_precinct_id;
    """)

    parts = cur.fetchall()
    print(f"\nUnique Parts assigned: {len(parts)}")
    for part in parts:
        print(f"  - {part[0]}")

    cur.close()
    conn.close()

def main():
    """Main enrichment workflow."""
    print("=" * 80)
    print("ASHFIELD PAGE RANGE ENRICHMENT SCRIPT")
    print("=" * 80)
    print("\nThis script will map 133 Ashfield provisions to Parts 1-13")
    print("using PDF page ranges identified from text analysis.")
    print("\nPage range boundaries:")
    for part in sorted(PAGE_RANGES.keys(), key=lambda x: int(x.split()[1])):
        start, end = PAGE_RANGES[part]
        print(f"  {part}: Pages {start}-{end}")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return

    # Enrich
    assigned, unassigned = enrich_ashfield()

    # Verify
    verify_enrichment()

    print("\n" + "=" * 80)
    print("ENRICHMENT COMPLETE")
    print("=" * 80)
    print(f"\nResults:")
    print(f"  Assigned: {assigned} provisions")
    print(f"  Unassigned: {unassigned} provisions")

    if unassigned > 0:
        print(f"\nNote: {unassigned} provisions fall outside defined page ranges.")
        print("These may be in gaps between Parts or belong to Part 10 (not found).")

if __name__ == '__main__':
    main()
