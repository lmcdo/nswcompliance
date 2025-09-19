#!/usr/bin/env python3
"""
Fix missing zones - Add comprehensive NSW Standard Instrument permissions
Especially R1 and other major zones that were missed
"""

import sqlite3

def add_missing_nsw_standard_zones():
    """Add comprehensive NSW Standard Instrument permissions for missing zones"""
    print("=== Adding Missing NSW Standard Zones ===")

    # Comprehensive NSW Standard Instrument permissions
    comprehensive_nsw_permissions = {
        'R1': {
            'dwelling_house': 'permitted',
            'dual_occupancy': 'prohibited',  # Generally not allowed in R1
            'multi_dwelling_housing': 'prohibited',
            'residential_flat_building': 'prohibited',
            'retail_premises': 'prohibited',
            'office_premises': 'prohibited',
            'warehouse': 'prohibited',
            'general_industry': 'prohibited',
            'home_occupation': 'permitted',
            'home_business': 'consent'
        },
        'R5': {  # Large Lot Residential
            'dwelling_house': 'permitted',
            'dual_occupancy': 'consent',
            'secondary_dwelling': 'consent',
            'rural_workers_dwelling': 'consent',
            'retail_premises': 'prohibited',
            'warehouse': 'prohibited',
            'general_industry': 'prohibited'
        },
        'B3': {  # Commercial Core - should have more permissions
            'retail_premises': 'permitted',
            'office_premises': 'permitted',
            'restaurant': 'permitted',
            'hotel': 'permitted',
            'residential_flat_building': 'consent',
            'warehouse': 'consent',
            'entertainment_facility': 'consent',
            'medical_centre': 'permitted'
        },
        'B4': {  # Mixed Use
            'retail_premises': 'permitted',
            'office_premises': 'permitted',
            'restaurant': 'permitted',
            'residential_flat_building': 'permitted',
            'dwelling_house': 'consent',
            'warehouse': 'consent',
            'medical_centre': 'permitted'
        },
        'B5': {  # Business Development
            'office_premises': 'permitted',
            'light_industry': 'permitted',
            'warehouse': 'permitted',
            'retail_premises': 'consent',
            'restaurant': 'consent',
            'residential_accommodation': 'prohibited'
        },
        'B6': {  # Enterprise Corridor
            'office_premises': 'permitted',
            'light_industry': 'permitted',
            'warehouse': 'permitted',
            'retail_premises': 'consent',
            'general_industry': 'consent',
            'residential_accommodation': 'prohibited'
        },
        'IN2': {  # Light Industrial
            'light_industry': 'permitted',
            'warehouse': 'permitted',
            'office_premises': 'permitted',
            'retail_premises': 'consent',
            'general_industry': 'consent',
            'dwelling_house': 'prohibited',
            'residential_flat_building': 'prohibited'
        },
        'E1': {  # National Parks and Nature Reserves - very restrictive
            'environmental_facility': 'permitted',
            'information_and_education_facility': 'consent',
            'dwelling_house': 'prohibited',
            'retail_premises': 'prohibited',
            'warehouse': 'prohibited',
            'general_industry': 'prohibited'
        },
        'E2': {  # Environmental Conservation - should be more restrictive
            'dwelling_house': 'consent',
            'environmental_facility': 'permitted',
            'extensive_agriculture': 'permitted',
            'retail_premises': 'prohibited',
            'warehouse': 'prohibited',
            'general_industry': 'prohibited'
        },
        'E3': {  # Environmental Management
            'dwelling_house': 'consent',
            'rural_industry': 'consent',
            'extensive_agriculture': 'permitted',
            'environmental_facility': 'permitted',
            'retail_premises': 'prohibited',
            'general_industry': 'prohibited'
        },
        'RE1': {  # Public Recreation
            'recreation_facility_outdoor': 'permitted',
            'information_and_education_facility': 'consent',
            'restaurant': 'consent',
            'dwelling_house': 'prohibited',
            'retail_premises': 'prohibited',
            'warehouse': 'prohibited'
        },
        'RE2': {  # Private Recreation
            'recreation_facility_indoor': 'permitted',
            'recreation_facility_outdoor': 'permitted',
            'restaurant': 'consent',
            'dwelling_house': 'prohibited',
            'retail_premises': 'prohibited'
        },
        'RU1': {  # Primary Production
            'extensive_agriculture': 'permitted',
            'dwelling_house': 'permitted',
            'rural_workers_dwelling': 'permitted',
            'farm_building': 'permitted',
            'retail_premises': 'prohibited',
            'general_industry': 'prohibited'
        },
        'SP1': {  # Special Activities
            'air_transport_facility': 'permitted',
            'port_facility': 'permitted',
            'retail_premises': 'consent',
            'dwelling_house': 'prohibited'
        },
        'SP2': {  # Infrastructure
            'electricity_generating_works': 'permitted',
            'utility_installation': 'permitted',
            'dwelling_house': 'prohibited',
            'retail_premises': 'prohibited'
        }
    }

    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()

    total_added = 0

    for zone, permissions in comprehensive_nsw_permissions.items():
        zone_added = 0
        print(f"\nAdding permissions for {zone}:")

        for dev_type, permission in permissions.items():
            try:
                cursor.execute("""
                INSERT OR IGNORE INTO development_permissions
                (zone, development_type, permission_status, lep_name,
                 extraction_method, confidence_score, source_type)
                VALUES (?, ?, ?, 'NSW Standard Instrument LEP', 'nsw_standard_comprehensive', 1.0, 'nsw_standard')
                """, (zone, dev_type, permission))

                if cursor.rowcount > 0:
                    zone_added += 1
                    total_added += 1
            except sqlite3.Error as e:
                print(f"[WARN] Error inserting {zone}/{dev_type}: {e}")

        print(f"  Added {zone_added} permissions for {zone}")

    conn.commit()
    conn.close()

    print(f"\n[SUCCESS] Added {total_added} comprehensive NSW Standard permissions")
    return total_added

def verify_zone_coverage():
    """Verify comprehensive zone coverage"""
    print("\n=== Verification: Zone Coverage After Fix ===")

    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()

    # Check R1 specifically
    cursor.execute("""
    SELECT development_type, permission_status
    FROM development_permissions
    WHERE zone = 'R1'
    ORDER BY permission_status, development_type
    """)
    r1_permissions = cursor.fetchall()

    print(f"R1 zone now has {len(r1_permissions)} permissions:")
    for dev_type, status in r1_permissions:
        print(f"  {dev_type}: {status}")

    # Check total combinations
    cursor.execute("SELECT COUNT(*) FROM development_permissions")
    total = cursor.fetchone()[0]
    print(f"\nTotal combinations now: {total}")

    # Check zones with >5 permissions (indicating good coverage)
    cursor.execute("""
    SELECT zone, COUNT(*) as count
    FROM development_permissions
    GROUP BY zone
    HAVING count >= 5
    ORDER BY count DESC
    """)
    well_covered_zones = cursor.fetchall()

    print(f"\nZones with good coverage (≥5 permissions): {len(well_covered_zones)}")
    for zone, count in well_covered_zones:
        print(f"  {zone}: {count} permissions")

    conn.close()

if __name__ == '__main__':
    added_count = add_missing_nsw_standard_zones()
    verify_zone_coverage()
    print(f"\n[COMPLETE] Fixed missing zones - added {added_count} permissions")