#!/usr/bin/env python3
"""
Fix: Clear v2_precinct_id for Leichhardt heritage provisions

Heritage applies based on HCA (Heritage Conservation Area), NOT precinct.
Ashfield and Marrickville both have 100% NULL precinct_id for heritage.
Leichhardt incorrectly has 50% with precinct_id set.

This fix makes Leichhardt consistent with other councils.
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
    print("FIX: CLEAR v2_precinct_id FOR LEICHHARDT HERITAGE")
    print("=" * 80)
    print()

    # Step 1: Current state
    print("Step 1: Current state")
    print("-" * 80)

    cur.execute("""
        SELECT
            CASE WHEN v2_precinct_id IS NULL THEN 'NULL' ELSE 'HAS VALUE' END as status,
            COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
          AND v2_dcp_layer = 'condition'
        GROUP BY status;
    """)

    current_state = cur.fetchall()
    print("Leichhardt heritage by precinct_id status:")
    total_before = 0
    for status, count in current_state:
        print(f"  v2_precinct_id {status:10s}: {count}")
        total_before += count
    print(f"  {'TOTAL':21s}: {total_before}")
    print()

    # Step 2: Compare to other councils
    print("Step 2: Comparison (before fix)")
    print("-" * 80)

    for council in ['Ashfield', 'Marrickville', 'Leichhardt']:
        cur.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE v2_precinct_id IS NULL) as null_count,
                COUNT(*) as total
            FROM regulatory_provisions
            WHERE document_id LIKE '%{council}%'
              AND v2_topic = 'Heritage'
              AND v2_is_actionable = true
              AND v2_dcp_layer = 'condition';
        """)

        row = cur.fetchone()
        if row and row[1] > 0:
            pct = (row[0] / row[1] * 100)
            print(f"  {council:15s}: {row[0]:3d}/{row[1]:3d} NULL ({pct:5.1f}%)")
    print()

    # Step 3: Provisions to update
    print("Step 3: Provisions to clear")
    print("-" * 80)

    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
          AND v2_dcp_layer = 'condition'
          AND v2_precinct_id IS NOT NULL;
    """)

    to_clear = cur.fetchone()[0]
    print(f"  Provisions to clear: {to_clear}")
    print()

    if to_clear == 0:
        print("  No provisions need to be cleared. Already correct!")
        cur.close()
        conn.close()
        return

    # Step 4: Execute update
    print(f"Step 4: Executing update for {to_clear} provisions...")
    print("-" * 80)

    # Clear v2_precinct_id
    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_precinct_id = NULL
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
          AND v2_dcp_layer = 'condition'
          AND v2_precinct_id IS NOT NULL;
    """)

    rows_updated = cur.rowcount
    conn.commit()

    print(f"  [OK] Cleared v2_precinct_id for {rows_updated} provisions")
    print()

    # Step 5: Verify
    print("Step 5: Verification")
    print("-" * 80)

    cur.execute("""
        SELECT
            CASE WHEN v2_precinct_id IS NULL THEN 'NULL' ELSE 'HAS VALUE' END as status,
            COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
          AND v2_dcp_layer = 'condition'
        GROUP BY status;
    """)

    final_state = cur.fetchall()
    print("Leichhardt heritage by precinct_id status (after fix):")
    total_after = 0
    for status, count in final_state:
        print(f"  v2_precinct_id {status:10s}: {count}")
        total_after += count
    print(f"  {'TOTAL':21s}: {total_after}")
    print()

    # Step 6: Final comparison
    print("Step 6: Final comparison (after fix)")
    print("-" * 80)

    for council in ['Ashfield', 'Marrickville', 'Leichhardt']:
        cur.execute(f"""
            SELECT
                COUNT(*) FILTER (WHERE v2_precinct_id IS NULL) as null_count,
                COUNT(*) as total
            FROM regulatory_provisions
            WHERE document_id LIKE '%{council}%'
              AND v2_topic = 'Heritage'
              AND v2_is_actionable = true
              AND v2_dcp_layer = 'condition';
        """)

        row = cur.fetchone()
        if row and row[1] > 0:
            pct = (row[0] / row[1] * 100)
            status = "[OK]" if pct == 100.0 else "[!!]"
            print(f"  {status} {council:15s}: {row[0]:3d}/{row[1]:3d} NULL ({pct:5.1f}%)")
    print()

    print("=" * 80)
    print("[COMPLETE] HERITAGE PRECINCT_ID FIX COMPLETE")
    print("=" * 80)
    print()
    print("Expected results:")
    print("  - All 3 councils now have 100% NULL precinct_id for heritage")
    print("  - Heritage applies based on HCA, not precinct")
    print("  - API will now return ALL 107 Leichhardt heritage provisions")
    print("  - Consistent with Ashfield (905) and Marrickville (205)")
    print()
    print("Test with: 185 Parramatta Road, Annandale")
    print("  Expected: 107 heritage provisions (not 53)")
    print()

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
