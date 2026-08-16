"""
Fix TOC page ranges for TOC-based UI
Phase 1: Data Certification

Fixes:
1. Swap invalid page ranges (where start > end)
2. Calculate missing page_end values
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cur = conn.cursor()

    print("=" * 60)
    print("TOC PAGE RANGE FIXES")
    print("=" * 60)

    # Check current state
    print("\n1. CURRENT STATE")
    print("-" * 60)

    cur.execute("SELECT COUNT(*) FROM dcp_table_of_contents")
    total = cur.fetchone()[0]
    print(f"Total TOC entries: {total}")

    cur.execute("SELECT COUNT(*) FROM dcp_table_of_contents WHERE page_start > page_end")
    invalid = cur.fetchone()[0]
    print(f"Invalid (start > end): {invalid}")

    cur.execute("SELECT COUNT(*) FROM dcp_table_of_contents WHERE page_end IS NULL")
    null_end = cur.fetchone()[0]
    print(f"NULL page_end: {null_end}")

    # Fix 1: Swap invalid ranges
    print("\n2. FIX 1: Swap invalid page ranges")
    print("-" * 60)

    cur.execute("""
        UPDATE dcp_table_of_contents
        SET page_start = page_end, page_end = page_start
        WHERE page_start > page_end
        RETURNING id, section_number, page_start, page_end
    """)

    swapped = cur.fetchall()
    print(f"Swapped {len(swapped)} entries")
    if swapped and len(swapped) <= 10:
        for row in swapped:
            print(f"  {row[1]}: now p{row[2]}-{row[3]}")

    # Fix 2: Calculate missing page_end
    print("\n3. FIX 2: Calculate missing page_end")
    print("-" * 60)

    cur.execute("""
        WITH ordered AS (
            SELECT
                id,
                document_id,
                page_start,
                LEAD(page_start) OVER (
                    PARTITION BY document_id ORDER BY page_start
                ) as next_start
            FROM dcp_table_of_contents
        )
        UPDATE dcp_table_of_contents t
        SET page_end = o.next_start - 1
        FROM ordered o
        WHERE t.id = o.id
          AND t.page_end IS NULL
          AND o.next_start IS NOT NULL
        RETURNING t.id, t.section_number, t.page_start, t.page_end
    """)

    calculated = cur.fetchall()
    print(f"Calculated page_end for {len(calculated)} entries")

    # For remaining NULLs (last section in each doc), use max page from provisions
    cur.execute("""
        SELECT COUNT(*) FROM dcp_table_of_contents WHERE page_end IS NULL
    """)
    remaining_null = cur.fetchone()[0]
    print(f"Remaining NULL page_end: {remaining_null}")

    # Commit changes
    conn.commit()
    print("\nChanges committed.")

    # Verify final state
    print("\n4. FINAL STATE")
    print("-" * 60)

    cur.execute("SELECT COUNT(*) FROM dcp_table_of_contents WHERE page_start > page_end")
    invalid_after = cur.fetchone()[0]
    print(f"Invalid (start > end): {invalid_after}")

    cur.execute("SELECT COUNT(*) FROM dcp_table_of_contents WHERE page_end IS NULL")
    null_after = cur.fetchone()[0]
    print(f"NULL page_end: {null_after}")

    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE page_end IS NOT NULL AND page_start <= page_end) as valid
        FROM dcp_table_of_contents
    """)
    row = cur.fetchone()
    valid_pct = round(100 * row[1] / row[0], 1) if row[0] > 0 else 0
    print(f"Valid entries: {row[1]}/{row[0]} ({valid_pct}%)")

    # Check provision-TOC mapping
    print("\n5. PROVISION-TOC MAPPING TEST")
    print("-" * 60)

    cur.execute("""
        SELECT
            CASE
                WHEN p.document_id ILIKE '%marrickville%' THEN 'Marrickville'
                WHEN p.document_id ILIKE '%leichhardt%' THEN 'Leichhardt'
                WHEN p.document_id ILIKE '%ashfield%' THEN 'Ashfield'
                ELSE 'Other'
            END as council,
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE p.pdf_page IS NOT NULL) as has_page
        FROM regulatory_provisions p
        WHERE p.document_id NOT ILIKE '%State%'
          AND p.document_id NOT ILIKE '%Local%'
        GROUP BY 1
        ORDER BY 2 DESC
    """)

    for row in cur.fetchall():
        pct = round(100 * row[2] / row[1], 1) if row[1] > 0 else 0
        print(f"  {row[0]}: {row[2]}/{row[1]} have page ({pct}%)")

    conn.close()

    print("\n" + "=" * 60)
    print("CERTIFICATION RESULT")
    print("=" * 60)

    if invalid_after == 0 and valid_pct > 95:
        print("✓ PASSED - Data ready for TOC UI")
    else:
        print("✗ NEEDS ATTENTION")
        if invalid_after > 0:
            print(f"  - {invalid_after} invalid page ranges remain")
        if valid_pct < 95:
            print(f"  - Only {valid_pct}% valid (target: >95%)")

if __name__ == "__main__":
    main()
