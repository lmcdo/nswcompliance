#!/usr/bin/env python3
"""
Fix Leichhardt heritage provisions layer assignment

Move heritage provisions from GENERIC/PRECINCT → CONDITION
to match Ashfield and Marrickville architecture
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
    print("LEICHHARDT HERITAGE LAYER FIX")
    print("=" * 80)
    print()

    # Step 1: Check current state
    print("Step 1: Current state")
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

    # Step 2: Preview changes
    print("Step 2: Provisions to be moved")
    print("-" * 80)

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
    total_to_move = 0
    for layer, count in to_move:
        print(f"  {layer:15s}: {count} provisions -> CONDITION")
        total_to_move += count

    print(f"\n  Total to move: {total_to_move}")
    print()

    if total_to_move == 0:
        print("No provisions need to be moved. Already correct!")
        cur.close()
        conn.close()
        return

    # Step 3: Execute update (auto-confirmed)
    print(f"\nStep 3: Executing update for {total_to_move} provisions...")
    print("-" * 80)

    # Update provisions
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

    print(f"  [OK] Updated {rows_updated} provisions")
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

    # Step 5: Compare to other councils
    print("Step 5: Comparison with other councils")
    print("-" * 80)

    cur.execute("""
        SELECT
            CASE
                WHEN document_id LIKE '%Ashfield%' THEN 'Ashfield'
                WHEN document_id LIKE '%Marrickville%' THEN 'Marrickville'
                WHEN document_id LIKE '%Leichhardt%' THEN 'Leichhardt'
            END as council,
            v2_dcp_layer,
            COUNT(*)
        FROM regulatory_provisions
        WHERE v2_topic = 'Heritage'
          AND v2_is_actionable = true
          AND (document_id LIKE '%Ashfield%' OR document_id LIKE '%Marrickville%' OR document_id LIKE '%Leichhardt%')
        GROUP BY council, v2_dcp_layer
        ORDER BY council, v2_dcp_layer;
    """)

    print("Heritage provisions by council and layer:")
    for council, layer, count in cur.fetchall():
        if council:
            print(f"  {council:15s} {layer:15s}: {count}")

    print()
    print("=" * 80)
    print("[COMPLETE] LEICHHARDT HERITAGE LAYER FIX COMPLETE")
    print("=" * 80)
    print()
    print("Expected results:")
    print("  - Leichhardt heritage now in CONDITION layer (like Ashfield/Marrickville)")
    print("  - Heritage badge (yellow dot) will now show")
    print("  - HCA filtering will work")
    print("  - Topic filtering will work")
    print()
    print("Test with: 185 Parramatta Road, Annandale")
    print("  Expected: 106 heritage provisions in CONDITION layer")
    print()

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
