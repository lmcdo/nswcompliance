#!/usr/bin/env python3
"""
Fix ALL Leichhardt heritage issues in SUPABASE

1. Move heritage from generic/precinct -> condition layer
2. Clear v2_precinct_id for all heritage provisions
3. Clear v2_heritage_hca (no HCA-specific provisions in Leichhardt)
"""
import psycopg2

DB_CONFIG = {
    'dbname': 'postgres',
    'user': 'postgres.llzdrxywpziewrzudwhj',
    'password': 'eDDIYq8ottiaO9ll',
    'host': 'aws-1-ap-southeast-2.pooler.supabase.com',
    'port': 5432
}

def main():
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    print("=" * 80)
    print("FIX ALL LEICHHARDT HERITAGE ISSUES - SUPABASE")
    print("=" * 80)
    print()

    # Step 1: Current state
    print("Step 1: Current state")
    print("-" * 80)

    cur.execute("""
        SELECT
            v2_dcp_layer,
            v2_is_actionable,
            COUNT(*) FILTER (WHERE v2_precinct_id IS NOT NULL) as with_precinct,
            COUNT(*) FILTER (WHERE v2_precinct_id IS NULL) as without_precinct,
            COUNT(*) as total
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND LOWER(v2_topic) = 'heritage'
        GROUP BY v2_dcp_layer, v2_is_actionable
        ORDER BY v2_dcp_layer, v2_is_actionable;
    """)

    print("Leichhardt heritage provisions:")
    for layer, actionable, with_p, without_p, total in cur.fetchall():
        actionable_str = "actionable" if actionable else "not actionable"
        print(f"  {layer:15s} | {actionable_str:15s} | precinct_id: {with_p:2d} yes, {without_p:2d} no | total: {total}")
    print()

    # Step 2: Execute fixes
    print("Step 2: Executing fixes...")
    print("-" * 80)

    # Fix 1: Move to condition layer
    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_dcp_layer = 'condition'
        WHERE document_id LIKE '%Leichhardt%'
          AND LOWER(v2_topic) = 'heritage'
          AND v2_dcp_layer IN ('generic', 'precinct', 'use_specific');
    """)
    layer_updates = cur.rowcount
    print(f"  [OK] Moved {layer_updates} provisions to CONDITION layer")

    # Fix 2: Clear v2_precinct_id
    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_precinct_id = NULL
        WHERE document_id LIKE '%Leichhardt%'
          AND LOWER(v2_topic) = 'heritage'
          AND v2_precinct_id IS NOT NULL;
    """)
    precinct_clears = cur.rowcount
    print(f"  [OK] Cleared v2_precinct_id for {precinct_clears} provisions")

    # Fix 3: Clear v2_heritage_hca
    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_heritage_hca = NULL
        WHERE document_id LIKE '%Leichhardt%'
          AND LOWER(v2_topic) = 'heritage'
          AND v2_heritage_hca IS NOT NULL;
    """)
    hca_clears = cur.rowcount
    print(f"  [OK] Cleared v2_heritage_hca for {hca_clears} provisions")

    conn.commit()
    print()

    # Step 3: Verify
    print("Step 3: Verification")
    print("-" * 80)

    cur.execute("""
        SELECT
            v2_dcp_layer,
            v2_is_actionable,
            COUNT(*) FILTER (WHERE v2_precinct_id IS NOT NULL) as with_precinct,
            COUNT(*) FILTER (WHERE v2_heritage_hca IS NOT NULL) as with_hca,
            COUNT(*) as total
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND LOWER(v2_topic) = 'heritage'
        GROUP BY v2_dcp_layer, v2_is_actionable
        ORDER BY v2_dcp_layer, v2_is_actionable;
    """)

    print("After fixes:")
    total_actionable = 0
    for layer, actionable, with_p, with_h, total in cur.fetchall():
        actionable_str = "actionable" if actionable else "not actionable"
        print(f"  {layer:15s} | {actionable_str:15s} | precinct: {with_p}, hca: {with_h} | total: {total}")
        if actionable:
            total_actionable += total

    print(f"\n  Total actionable heritage: {total_actionable}")
    print()

    # Step 4: Comparison with other councils
    print("Step 4: Comparison with other councils")
    print("-" * 80)

    for council in ['Ashfield', 'Marrickville', 'Leichhardt']:
        cur.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE v2_dcp_layer = 'condition') as condition_layer,
                COUNT(*) FILTER (WHERE v2_precinct_id IS NULL) as null_precinct,
                COUNT(*) as total
            FROM regulatory_provisions
            WHERE document_id LIKE '%{council}%'
              AND LOWER(v2_topic) = 'heritage'
              AND v2_is_actionable = true;
        """)

        row = cur.fetchone()
        if row and row[2] > 0:
            print(f"  {council:15s}: {row[0]:3d} in condition, {row[1]:3d} null precinct_id, {row[2]:3d} total")
    print()

    print("=" * 80)
    print("[COMPLETE] ALL FIXES APPLIED TO SUPABASE")
    print("=" * 80)
    print()
    print(f"Result: {total_actionable} Leichhardt heritage provisions now in CONDITION layer")
    print("  - All have v2_precinct_id = NULL (heritage based on HCA, not precinct)")
    print("  - All have v2_heritage_hca = NULL (no HCA-specific provisions in Leichhardt)")
    print()
    print("API will now return all provisions for any Leichhardt address in an HCA")
    print()
    print("Next: Refresh UI at 185 Parramatta Road to see changes!")
    print()

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
