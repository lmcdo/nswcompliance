"""
Enrich v2_precinct_id for all precinct layer provisions.

This script extracts precinct IDs from document_id patterns and populates
the v2_precinct_id column for 1,436 precinct provisions across 3 councils.

Patterns:
- Marrickville: "Marrickville_DCP_2011_-_9_12_..." → "12_"
- Leichhardt: "Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_1_..." → "C2.2.1.1"
- Ashfield: Single document, extract from provision context → "Part 1", "Part 2", etc.
"""

import os
import re
import psycopg2
from dotenv import load_dotenv

# Load environment variables
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
    - "Marrickville_DCP_2011_-_9_1_Lewisham..." → "1_"
    - "Marrickville_DCP_2011_-_9.43_Sydney_Steel..." → "43_"
    - "Marrickville_DCP_2011_-_9.48_Mary_Robert..." → "48_"
    """
    # Pattern 1: __9__XX__ (double underscores)
    match = re.search(r'__9__(\d+)__', document_id)
    if match:
        return f"{match.group(1)}_"

    # Pattern 2: _9_XX_ (single underscores)
    match = re.search(r'_9_(\d+)_', document_id)
    if match:
        return f"{match.group(1)}_"

    # Pattern 3: _9.XX_ or __9.XX__ (dot separator for precincts 43, 48)
    match = re.search(r'[_]{1,2}9\.(\d+)[_]{1,2}', document_id)
    if match:
        return f"{match.group(1)}_"

    return None

def extract_leichhardt_precinct(document_id):
    """
    Extract precinct code from Leichhardt document_id.

    Examples:
    - "Leichhardt_DCP_2013_Part_C_Section_2_C2_2_1_1_Young_Street..." → "C2.2.1.1"
    - "Leichhardt_DCP_2013_Part_C_Section_2_C2_2_2_3_Gladstone_Park..." → "C2.2.2.3"
    """
    # Pattern: C2_2_X_X (with underscores, needs conversion to dots)
    match = re.search(r'_C2_2_(\d+)_(\d+)_', document_id)
    if match:
        return f"C2.2.{match.group(1)}.{match.group(2)}"

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
    print(f"\nPrecinct distribution:")
    for precinct_id in sorted(precinct_counts.keys(), key=lambda x: int(x.replace('_', ''))):
        print(f"  {precinct_id}: {precinct_counts[precinct_id]} provisions")

    cur.close()
    conn.close()

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
            print(f"  WARNING: Could not extract precinct from: {document_id}")

    conn.commit()

    print(f"\n[OK] Updated {updated_count} provisions")
    print(f"[FAILED] Failed {failed_count} provisions")
    print(f"\nPrecinct distribution:")
    for precinct_id in sorted(precinct_counts.keys()):
        print(f"  {precinct_id}: {precinct_counts[precinct_id]} provisions")

    cur.close()
    conn.close()

def enrich_ashfield():
    """
    Enrich Ashfield precinct provisions.

    Ashfield is tricky - all 133 provisions are in one document.
    We need to check v2_dcp_part or provision_text to determine which Part.
    """
    conn = get_db_connection()
    cur = conn.cursor()

    print("\n" + "=" * 80)
    print("ENRICHING ASHFIELD PRECINCT IDS")
    print("=" * 80)

    # Get all Ashfield precinct provisions with their v2_dcp_part
    cur.execute("""
        SELECT id, document_id, v2_dcp_part, heading, provision_text
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Ashfield%'
          AND v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
        ORDER BY id;
    """)

    provisions = cur.fetchall()
    print(f"\nFound {len(provisions)} Ashfield precinct provisions")

    # Sample first few to understand structure
    print("\nSample provisions (first 10):")
    for i, (prov_id, doc_id, part, heading, text) in enumerate(provisions[:10]):
        text_preview = text[:100] if text else "None"
        print(f"\n{i+1}. ID: {prov_id}")
        print(f"   Part: {part}")
        print(f"   Heading: {heading}")
        print(f"   Text: {text_preview}...")

    # Try to extract Part number from v2_dcp_part or heading
    updated_count = 0
    failed_count = 0
    precinct_counts = {}

    for prov_id, doc_id, part, heading, text in provisions:
        precinct_id = None

        # Strategy 1: Check v2_dcp_part for "Part X"
        if part:
            match = re.search(r'Part\s+(\d+)', part, re.IGNORECASE)
            if match:
                part_num = match.group(1)
                precinct_id = f"Part {part_num}"

        # Strategy 2: Check heading for "Part X"
        if not precinct_id and heading:
            match = re.search(r'Part\s+(\d+)', heading, re.IGNORECASE)
            if match:
                part_num = match.group(1)
                precinct_id = f"Part {part_num}"

        # Strategy 3: Check provision text for "Part X"
        if not precinct_id and text:
            match = re.search(r'Part\s+(\d+)', text[:200], re.IGNORECASE)
            if match:
                part_num = match.group(1)
                precinct_id = f"Part {part_num}"

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
            print(f"  WARNING: Could not extract Part from provision {prov_id}")
            print(f"    Part: {part}")
            print(f"    Heading: {heading}")

    conn.commit()

    print(f"\n[OK] Updated {updated_count} provisions")
    print(f"[FAILED] Failed {failed_count} provisions")

    if precinct_counts:
        print(f"\nPrecinct distribution:")
        for precinct_id in sorted(precinct_counts.keys(), key=lambda x: int(re.search(r'\d+', x).group())):
            print(f"  {precinct_id}: {precinct_counts[precinct_id]} provisions")

    cur.close()
    conn.close()

def verify_enrichment():
    """Verify enrichment results."""
    conn = get_db_connection()
    cur = conn.cursor()

    print("\n" + "=" * 80)
    print("VERIFICATION SUMMARY")
    print("=" * 80)

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
        status = "[OK]" if percentage == 100 else "[WARN]"

        print(f"\n{council}:")
        print(f"  Total: {total} provisions")
        print(f"  Enriched: {enriched} provisions ({percentage:.1f}%)")
        print(f"  Status: {status}")

    # Overall summary
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE v2_dcp_layer = 'precinct'
          AND v2_is_actionable = true
          AND v2_precinct_id IS NOT NULL;
    """)
    total_enriched = cur.fetchone()[0]

    print(f"\n{'='*80}")
    print(f"TOTAL ENRICHED: {total_enriched} / 1436 provisions ({total_enriched/1436*100:.1f}%)")
    print(f"{'='*80}")

    cur.close()
    conn.close()

def main():
    """Main enrichment workflow."""
    print("=" * 80)
    print("PRECINCT ID ENRICHMENT SCRIPT")
    print("=" * 80)
    print("\nThis script will populate v2_precinct_id for 1,436 precinct provisions")
    print("across Marrickville (686), Leichhardt (617), and Ashfield (133).")
    print("\nPress Ctrl+C to cancel, or Enter to continue...")

    try:
        input()
    except KeyboardInterrupt:
        print("\n\nCancelled by user.")
        return

    # Enrich each council
    enrich_marrickville()
    enrich_leichhardt()
    enrich_ashfield()

    # Verify results
    verify_enrichment()

    print("\n" + "=" * 80)
    print("ENRICHMENT COMPLETE")
    print("=" * 80)

if __name__ == '__main__':
    main()
