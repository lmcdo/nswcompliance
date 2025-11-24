#!/usr/bin/env python3
"""
DQ-7 Fix Part 2: Commercial, Industrial, Special Use enrichment.

For provisions that don't have specific keywords, use zone-based inference:
- B zones (B1, B2, B3, B4) → commercial types
- IN zones (IN1, IN2) → industrial types
- Zone-neutral provisions → add to multiple categories
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2
import re

COMMERCIAL_TYPES = ['retail_premises', 'commercial_premises', 'office_premises', 'shop_top_housing']
INDUSTRIAL_TYPES = ['industrial_development', 'warehouse']
SPECIAL_USE = ['child_care_centre']

# Zone patterns
B_ZONES = ['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7']
IN_ZONES = ['IN1', 'IN2', 'IN3', 'IN4']


def main():
    print("=" * 70)
    print("DQ-7 FIX Part 2: Commercial/Industrial/Special Use")
    print("=" * 70)

    conn = psycopg2.connect('dbname=nsw_planning')
    cur = conn.cursor()

    # Strategy 1: Provisions with B zone applicability → commercial
    print("\n1. Adding commercial types to B-zone provisions...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['retail_premises', 'commercial_premises', 'office_premises', 'shop_top_housing']::text[]
        )
        WHERE v2_is_actionable = true
          AND v2_dcp_layer IN ('generic', 'use_specific')
          AND v2_applicable_zones && ARRAY['B1', 'B2', 'B3', 'B4', 'B5', 'B6', 'B7']::text[]
          AND NOT (v2_applicable_dev_types && ARRAY['retail_premises', 'commercial_premises']::text[])
    ''')
    b_zone_updated = cur.rowcount
    print(f"   Updated {b_zone_updated} B-zone provisions")

    # Strategy 2: Provisions with IN zone applicability → industrial
    print("\n2. Adding industrial types to IN-zone provisions...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['industrial_development', 'warehouse']::text[]
        )
        WHERE v2_is_actionable = true
          AND v2_dcp_layer IN ('generic', 'use_specific')
          AND v2_applicable_zones && ARRAY['IN1', 'IN2', 'IN3', 'IN4']::text[]
          AND NOT (v2_applicable_dev_types && ARRAY['industrial_development', 'warehouse']::text[])
    ''')
    in_zone_updated = cur.rowcount
    print(f"   Updated {in_zone_updated} IN-zone provisions")

    # Strategy 3: Part 5 Commercial sections explicitly
    print("\n3. Adding commercial to Part 5/Commercial provisions...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['retail_premises', 'commercial_premises', 'office_premises']::text[]
        )
        WHERE v2_is_actionable = true
          AND (document_id ILIKE '%Part 5%'
               OR document_id ILIKE '%5_0%'
               OR document_id ILIKE '%Commercial%'
               OR document_id ILIKE '%Section 4%')
          AND NOT (v2_applicable_dev_types && ARRAY['commercial_premises']::text[])
    ''')
    part5_updated = cur.rowcount
    print(f"   Updated {part5_updated} Part 5/Commercial provisions")

    # Strategy 4: Part 6 Industrial sections
    print("\n4. Adding industrial to Part 6/Industrial provisions...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['industrial_development', 'warehouse']::text[]
        )
        WHERE v2_is_actionable = true
          AND (document_id ILIKE '%Part 6%'
               OR document_id ILIKE '%6_0%'
               OR document_id ILIKE '%Industrial%')
          AND NOT (v2_applicable_dev_types && ARRAY['industrial_development']::text[])
    ''')
    part6_updated = cur.rowcount
    print(f"   Updated {part6_updated} Part 6/Industrial provisions")

    # Strategy 5: Child care - text-based
    print("\n5. Adding child_care_centre to child care provisions...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['child_care_centre']::text[]
        )
        WHERE v2_is_actionable = true
          AND (lower(provision_text) LIKE '%child care%'
               OR lower(provision_text) LIKE '%childcare%'
               OR lower(provision_text) LIKE '%early childhood%')
          AND NOT ('child_care_centre' = ANY(v2_applicable_dev_types))
    ''')
    childcare_updated = cur.rowcount
    print(f"   Updated {childcare_updated} child care provisions")

    # Strategy 6: Generic commercial/industrial keywords in text
    print("\n6. Adding based on text keywords...")

    # Parking, access, signage often apply to commercial
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['retail_premises', 'commercial_premises']::text[]
        )
        WHERE v2_is_actionable = true
          AND v2_topic IN ('parking', 'signage', 'access')
          AND v2_provision_type = 'control'
          AND v2_has_numeric_value = true
          AND NOT (v2_applicable_dev_types && ARRAY['commercial_premises']::text[])
    ''')
    topic_commercial = cur.rowcount
    print(f"   Added commercial to {topic_commercial} parking/signage/access provisions")

    # Remove duplicates from arrays
    print("\n7. Cleaning up duplicate dev_types...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = (
            SELECT ARRAY(SELECT DISTINCT unnest(v2_applicable_dev_types) ORDER BY 1)
        )
        WHERE v2_applicable_dev_types IS NOT NULL
    ''')

    # Check results
    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)

    dev_types = [
        'dwelling_house', 'secondary_dwelling', 'dual_occupancy',
        'multi_dwelling_housing', 'residential_flat_building',
        'retail_premises', 'commercial_premises', 'office_premises',
        'industrial_development', 'warehouse', 'boarding_house',
        'child_care_centre', 'shop_top_housing'
    ]

    for dt in dev_types:
        cur.execute('''
            SELECT COUNT(*) FROM regulatory_provisions
            WHERE v2_is_actionable = true
              AND v2_dcp_layer = 'generic'
              AND v2_provision_type = 'control'
              AND v2_has_numeric_value = true
              AND %s = ANY(v2_applicable_dev_types)
        ''', (dt,))
        count = cur.fetchone()[0]
        status = "OK" if count >= 20 else "LOW"
        print(f"   {dt}: {count} [{status}]")

    # Commit
    confirm = input("\nCommit changes? (y/n): ")
    if confirm.lower() == 'y':
        conn.commit()
        print("Changes committed!")
    else:
        conn.rollback()
        print("Changes rolled back.")

    conn.close()


if __name__ == "__main__":
    main()
