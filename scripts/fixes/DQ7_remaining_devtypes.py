#!/usr/bin/env python3
"""
DQ-7 Fix Part 3: Remaining dev-types that are still LOW.

Targets:
- office_premises: 12 -> 20+
- industrial_development: 10 -> 20+
- warehouse: 5 -> 20+
- child_care_centre: 1 -> 10+
- shop_top_housing: 13 -> 20+
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

def main():
    print("=" * 70)
    print("DQ-7 FIX Part 3: Remaining Dev-Types")
    print("=" * 70)

    conn = psycopg2.connect('dbname=nsw_planning')
    cur = conn.cursor()

    # Strategy 1: Office - add to any provision mentioning office, business, professional
    print("\n1. Enriching office_premises...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['office_premises']::text[]
        )
        WHERE v2_is_actionable = true
          AND v2_dcp_layer IN ('generic', 'use_specific')
          AND (lower(provision_text) LIKE '%office%'
               OR lower(provision_text) LIKE '%business premises%'
               OR lower(provision_text) LIKE '%professional%'
               OR lower(document_id) LIKE '%commercial%'
               OR lower(document_id) LIKE '%business%')
          AND NOT ('office_premises' = ANY(v2_applicable_dev_types))
    ''')
    office_updated = cur.rowcount
    print(f"   Updated {office_updated} office provisions")

    # Strategy 2: Industrial - broader text matching
    print("\n2. Enriching industrial_development...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['industrial_development']::text[]
        )
        WHERE v2_is_actionable = true
          AND v2_dcp_layer IN ('generic', 'use_specific')
          AND (lower(provision_text) LIKE '%industrial%'
               OR lower(provision_text) LIKE '%manufacturing%'
               OR lower(provision_text) LIKE '%factory%'
               OR lower(provision_text) LIKE '%heavy vehicle%'
               OR lower(document_id) LIKE '%industrial%'
               OR lower(document_id) LIKE '%employment%')
          AND NOT ('industrial_development' = ANY(v2_applicable_dev_types))
    ''')
    industrial_updated = cur.rowcount
    print(f"   Updated {industrial_updated} industrial provisions")

    # Strategy 3: Warehouse - storage, logistics, distribution
    print("\n3. Enriching warehouse...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['warehouse']::text[]
        )
        WHERE v2_is_actionable = true
          AND v2_dcp_layer IN ('generic', 'use_specific')
          AND (lower(provision_text) LIKE '%warehouse%'
               OR lower(provision_text) LIKE '%storage%'
               OR lower(provision_text) LIKE '%distribution%'
               OR lower(provision_text) LIKE '%logistics%'
               OR lower(provision_text) LIKE '%loading%')
          AND NOT ('warehouse' = ANY(v2_applicable_dev_types))
    ''')
    warehouse_updated = cur.rowcount
    print(f"   Updated {warehouse_updated} warehouse provisions")

    # Strategy 4: Child care - broader matching including education
    print("\n4. Enriching child_care_centre...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['child_care_centre']::text[]
        )
        WHERE v2_is_actionable = true
          AND v2_dcp_layer IN ('generic', 'use_specific')
          AND (lower(provision_text) LIKE '%child%care%'
               OR lower(provision_text) LIKE '%childcare%'
               OR lower(provision_text) LIKE '%early childhood%'
               OR lower(provision_text) LIKE '%preschool%'
               OR lower(provision_text) LIKE '%kindergarten%'
               OR lower(document_id) LIKE '%child%'
               OR lower(document_id) LIKE '%education%')
          AND NOT ('child_care_centre' = ANY(v2_applicable_dev_types))
    ''')
    childcare_updated = cur.rowcount
    print(f"   Updated {childcare_updated} child care provisions")

    # Strategy 5: Shop top housing - mixed use, above shops, B zones with residential
    print("\n5. Enriching shop_top_housing...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['shop_top_housing']::text[]
        )
        WHERE v2_is_actionable = true
          AND v2_dcp_layer IN ('generic', 'use_specific')
          AND (lower(provision_text) LIKE '%shop top%'
               OR lower(provision_text) LIKE '%shop-top%'
               OR lower(provision_text) LIKE '%mixed use%'
               OR lower(provision_text) LIKE '%mixed-use%'
               OR lower(provision_text) LIKE '%above shop%'
               OR lower(provision_text) LIKE '%residential above%'
               OR (v2_applicable_zones && ARRAY['B1', 'B2', 'B4']::text[]
                   AND v2_applicable_dev_types && ARRAY['residential_flat_building', 'dwelling_house']::text[]))
          AND NOT ('shop_top_housing' = ANY(v2_applicable_dev_types))
    ''')
    shoptop_updated = cur.rowcount
    print(f"   Updated {shoptop_updated} shop top housing provisions")

    # Strategy 6: Generic provisions that apply to ALL non-residential should include office/industrial
    print("\n6. Adding office/industrial to commercial-tagged generic provisions...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['office_premises', 'industrial_development', 'warehouse']::text[]
        )
        WHERE v2_is_actionable = true
          AND v2_dcp_layer = 'generic'
          AND v2_provision_type = 'control'
          AND v2_has_numeric_value = true
          AND (v2_applicable_dev_types && ARRAY['commercial_premises', 'retail_premises']::text[])
          AND NOT (v2_applicable_dev_types && ARRAY['office_premises']::text[])
    ''')
    generic_commercial = cur.rowcount
    print(f"   Updated {generic_commercial} generic commercial provisions")

    # Strategy 7: Parking provisions apply to ALL dev types
    print("\n7. Adding all dev types to parking provisions...")
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(
            v2_applicable_dev_types,
            ARRAY['office_premises', 'industrial_development', 'warehouse', 'child_care_centre', 'shop_top_housing']::text[]
        )
        WHERE v2_is_actionable = true
          AND v2_topic = 'parking'
          AND v2_provision_type = 'control'
          AND v2_has_numeric_value = true
    ''')
    parking_updated = cur.rowcount
    print(f"   Updated {parking_updated} parking provisions")

    # Clean up duplicates
    print("\n8. Cleaning up duplicate dev_types...")
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

    all_ok = True
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
        threshold = 10 if dt == 'child_care_centre' else 20
        status = "OK" if count >= threshold else "LOW"
        if status == "LOW":
            all_ok = False
        print(f"   {dt}: {count} [{status}]")

    print("\n" + "=" * 70)
    if all_ok:
        print("ALL DEV TYPES MEET THRESHOLDS!")
    else:
        print("Some dev types still below threshold - may need manual review")
    print("=" * 70)

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
