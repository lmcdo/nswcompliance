#!/usr/bin/env python3
"""
Fix Marrickville zone tagging for Parts 4-6

Part 4.1 Low Density → R2
Part 4.2 Multi-Dwelling → R3, R4
Part 5 Commercial → B1, B2, B4, B5, B6
Part 6 Industrial → IN1, IN2, IN3
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
    print("FIX MARRICKVILLE ZONE TAGGING")
    print("=" * 80)
    print()

    # Step 1: Current state
    print("Step 1: Current State")
    print("-" * 80)

    cur.execute("""
        SELECT v2_dcp_part, COUNT(*) as count, v2_applicable_zones
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Marrickville%'
          AND v2_dcp_part IN ('Part 4.1', 'Part 4.2', 'Part 5', 'Part 6')
          AND v2_is_actionable = true
        GROUP BY v2_dcp_part, v2_applicable_zones
        ORDER BY v2_dcp_part;
    """)

    current = cur.fetchall()
    print("Current tagging:")
    for row in current:
        print(f"  {row[0]:15s}: {row[1]:3d} provisions tagged {row[2]}")
    print()

    # Step 2: Apply fixes
    print("Step 2: Applying Zone Tags")
    print("-" * 80)

    updates = [
        ('Part 4.1', ['R2'], 'Low Density Residential'),
        ('Part 4.2', ['R3', 'R4'], 'Multi-Dwelling Housing'),
        ('Part 5', ['B1', 'B2', 'B4', 'B5', 'B6'], 'Commercial and Mixed Use'),
        ('Part 6', ['IN1', 'IN2', 'IN3'], 'Industrial Development')
    ]

    total_updated = 0

    for part, zones, description in updates:
        cur.execute("""
            UPDATE regulatory_provisions
            SET v2_applicable_zones = %s
            WHERE document_id ILIKE '%Marrickville%'
              AND v2_dcp_part = %s
              AND v2_is_actionable = true;
        """, (zones, part))

        rows = cur.rowcount
        total_updated += rows
        print(f"  {part:15s} -> {str(zones):30s} | {rows:3d} provisions updated")

    conn.commit()
    print()
    print(f"Total provisions updated: {total_updated}")
    print()

    # Step 3: Verify
    print("Step 3: Verification")
    print("-" * 80)

    cur.execute("""
        SELECT v2_dcp_part, COUNT(*) as count, v2_applicable_zones as zones
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Marrickville%'
          AND v2_dcp_part IN ('Part 4.1', 'Part 4.2', 'Part 5', 'Part 6')
          AND v2_is_actionable = true
        GROUP BY v2_dcp_part, v2_applicable_zones
        ORDER BY v2_dcp_part;
    """)

    verified = cur.fetchall()
    print("After fix:")
    for part, count, zones in verified:
        print(f"  {part:15s}: {count:3d} provisions tagged {zones}")
    print()

    # Step 4: Test query simulation
    print("Step 4: Zone Filter Simulation")
    print("-" * 80)

    test_zones = ['R2', 'R3', 'B1', 'IN1']

    for zone in test_zones:
        cur.execute("""
            SELECT v2_dcp_part, COUNT(*) as count
            FROM regulatory_provisions
            WHERE document_id ILIKE '%Marrickville%'
              AND v2_dcp_layer = 'use_specific'
              AND v2_is_actionable = true
              AND %s = ANY(v2_applicable_zones)
            GROUP BY v2_dcp_part
            ORDER BY v2_dcp_part;
        """, (zone,))

        results = cur.fetchall()
        parts = ', '.join([f"{part} ({count})" for part, count in results]) if results else "NONE"
        print(f"  Zone {zone:4s}: {parts}")

    print()
    print("=" * 80)
    print("[COMPLETE] Marrickville zone tagging fixed")
    print("=" * 80)
    print()
    print("Expected behavior:")
    print("  - R2 property: Gets Part 4.1 only (91 provisions)")
    print("  - R3 property: Gets Part 4.2 only (31 provisions)")
    print("  - B1 property: Gets Part 5 only (60 provisions)")
    print("  - IN1 property: Gets Part 6 only (58 provisions)")
    print()

    cur.close()
    conn.close()

if __name__ == '__main__':
    main()
