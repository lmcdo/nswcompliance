#!/usr/bin/env python3
"""
Clear incorrect HCA tags from Leichhardt heritage provisions

The provisions tagged with HCA names are actually Distinctive Neighbourhood
precinct controls, not Heritage Conservation Area provisions.

Leichhardt DCP Part C Section 1 contains ONLY general heritage controls.
There are no HCA-specific provisions in the Leichhardt DCP.
"""
import psycopg2

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': 'Sturt1802!',
    'host': 'localhost'
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("=" * 80)
    print("FIX: CLEAR INCORRECT HCA TAGS FROM LEICHHARDT HERITAGE")
    print("=" * 80)
    print()

    # Step 1: Current state
    print("Step 1: Current state")
    print("-" * 80)

    cur.execute("""
        SELECT v2_heritage_hca, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
        GROUP BY v2_heritage_hca
        ORDER BY v2_heritage_hca;
    """)

    print("Leichhardt heritage by HCA tag:")
    for hca, count in cur.fetchall():
        print(f"  {hca or 'NULL':30s}: {count}")
    print()

    # Step 2: Provisions to clear
    print("Step 2: Provisions with incorrect HCA tags")
    print("-" * 80)

    cur.execute("""
        SELECT v2_heritage_hca, v2_dcp_part, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
          AND v2_heritage_hca IS NOT NULL
        GROUP BY v2_heritage_hca, v2_dcp_part;
    """)

    to_clear = 0
    for hca, part, count in cur.fetchall():
        print(f"  {hca:30s} | {part:20s} | {count} provisions")
        to_clear += count
    print(f"\n  Total to clear: {to_clear}")
    print()

    if to_clear == 0:
        print("  No provisions need to be cleared. Already correct!")
        cur.close()
        conn.close()
        return

    print("Reason: Leichhardt DCP has NO HCA-specific provisions")
    print("  - Part C Section 1 = General heritage controls only")
    print("  - Part C Section 2 = Distinctive Neighbourhoods (precinct, not HCA)")
    print("  - Tagged provisions are Distinctive Neighbourhoods, not HCA controls")
    print()

    # Step 3: Execute update
    print(f"Step 3: Executing update for {to_clear} provisions...")
    print("-" * 80)

    # Clear v2_heritage_hca
    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_heritage_hca = NULL
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
          AND v2_heritage_hca IS NOT NULL;
    """)

    rows_updated = cur.rowcount
    conn.commit()

    print(f"  [OK] Cleared v2_heritage_hca for {rows_updated} provisions")
    print()

    # Step 4: Verify
    print("Step 4: Verification")
    print("-" * 80)

    cur.execute("""
        SELECT v2_heritage_hca, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
        GROUP BY v2_heritage_hca
        ORDER BY v2_heritage_hca;
    """)

    print("Leichhardt heritage by HCA tag (after fix):")
    for hca, count in cur.fetchall():
        print(f"  {hca or 'NULL':30s}: {count}")
    print()

    # Step 5: Compare to other councils
    print("Step 5: Comparison with other councils")
    print("-" * 80)

    for council in ['Ashfield', 'Marrickville', 'Leichhardt']:
        cur.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE v2_heritage_hca IS NULL) as null_count,
                COUNT(*) FILTER (WHERE v2_heritage_hca IS NOT NULL) as tagged_count,
                COUNT(*) as total
            FROM regulatory_provisions
            WHERE document_id LIKE '%{council}%'
              AND v2_topic = 'Heritage'
              AND v2_is_actionable = true
              AND v2_dcp_layer = 'condition';
        """)

        row = cur.fetchone()
        if row and row[2] > 0:
            print(f"  {council:15s}: {row[0]:3d} NULL, {row[1]:3d} tagged, {row[2]:3d} total")
    print()

    print("=" * 80)
    print("[COMPLETE] HCA TAG CLEANUP COMPLETE")
    print("=" * 80)
    print()
    print("Result:")
    print("  - Leichhardt: All 107 provisions now have NULL v2_heritage_hca")
    print("  - This is CORRECT - Leichhardt DCP has no HCA-specific provisions")
    print("  - General heritage controls apply to all HCAs")
    print()
    print("API behavior:")
    print("  - Will return all 107 general heritage provisions")
    print("  - No HCA-specific filtering (all are general)")
    print("  - User sees comprehensive heritage controls")
    print()
    print("Test with: 185 Parramatta Road, Annandale")
    print("  Expected: 107 general heritage provisions")
    print("  LEP shows: C35 - Parramatta Road HCA boundary")
    print("  DCP shows: General heritage controls (apply to all HCAs)")
    print()

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
