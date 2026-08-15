#!/usr/bin/env python3
"""
Fix Leichhardt heritage provisions layer assignment - SUPABASE VERSION

Move heritage provisions from GENERIC/PRECINCT -> CONDITION
to match Ashfield and Marrickville architecture
"""
import psycopg2

# SUPABASE DATABASE
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
    print("LEICHHARDT HERITAGE LAYER FIX - SUPABASE")
    print("=" * 80)
    print()

    # Step 1: Check current state
    print("Step 1: Current state in Supabase")
    print("-" * 80)

    cur.execute("""
        SELECT v2_dcp_layer, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
        GROUP BY v2_dcp_layer
        ORDER BY v2_dcp_layer;
    """)

    current_state = cur.fetchall()
    print("Leichhardt Heritage provisions by layer:")
    total_before = 0
    for layer, count in current_state:
        print(f"  {layer:15s}: {count}")
        total_before += count
    print(f"  {'TOTAL':15s}: {total_before}")
    print()

    # Step 2: Provisions to move
    cur.execute("""
        SELECT v2_dcp_layer, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
          AND v2_dcp_layer IN ('generic', 'precinct', 'use_specific')
        GROUP BY v2_dcp_layer;
    """)

    to_move = cur.fetchall()
    total_to_move = sum(count for _, count in to_move)

    print("Step 2: Provisions to move")
    print("-" * 80)
    for layer, count in to_move:
        print(f"  {layer:15s}: {count} provisions -> CONDITION")
    print(f"\n  Total to move: {total_to_move}")
    print()

    if total_to_move == 0:
        print("No provisions need to be moved. Already correct!")
        cur.close()
        conn.close()
        return

    # Step 3: Execute update
    print(f"Step 3: Executing update for {total_to_move} provisions...")
    print("-" * 80)

    cur.execute("""
        UPDATE regulatory_provisions
        SET v2_dcp_layer = 'condition'
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
          AND v2_dcp_layer IN ('generic', 'precinct', 'use_specific');
    """)

    rows_updated = cur.rowcount
    conn.commit()

    print(f"  [OK] Updated {rows_updated} provisions in SUPABASE")
    print()

    # Step 4: Verify
    print("Step 4: Verification")
    print("-" * 80)

    cur.execute("""
        SELECT v2_dcp_layer, COUNT(*)
        FROM regulatory_provisions
        WHERE document_id LIKE '%Leichhardt%'
          AND v2_topic = 'Heritage'
          AND v2_is_actionable = true
        GROUP BY v2_dcp_layer
        ORDER BY v2_dcp_layer;
    """)

    final_state = cur.fetchall()
    print("Leichhardt Heritage provisions by layer (after fix):")
    total_after = 0
    for layer, count in final_state:
        print(f"  {layer:15s}: {count}")
        total_after += count
    print(f"  {'TOTAL':15s}: {total_after}")
    print()

    print("=" * 80)
    print("[COMPLETE] SUPABASE UPDATE COMPLETE")
    print("=" * 80)
    print()
    print("Refresh the UI to see changes!")
    print()

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
