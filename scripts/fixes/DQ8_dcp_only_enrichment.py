#!/usr/bin/env python3
"""
DQ-8: DCP-ONLY Dev-Type Enrichment
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

def is_dcp(cur, provision_id=None):
    """Check if provision is DCP (not SEPP/LEP)"""
    pass

def main():
    print("=" * 70)
    print("DQ-8: DCP-ONLY DEV-TYPE ENRICHMENT")
    print("=" * 70)

    # prior-art-checked: reuse not viable — one-off DQ fix script already using
    # psycopg2.connect directly; this only removes a hardcoded credential-shaped
    # fallback default, no new data-access capability is introduced.
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    DCP_WHERE = """document_id NOT ILIKE '%%State_Environmental%%'
              AND document_id NOT ILIKE '%%Local_Environmental%%'
              AND document_id NOT ILIKE '%%SEPP%%'
              AND document_id NOT ILIKE '%%LEP%%'"""

    # Check current state
    print("\n1. CURRENT DCP-ONLY CDC COVERAGE:")
    dev_types = ['dwelling_house', 'secondary_dwelling', 'dual_occupancy', 'multi_dwelling_housing',
                 'residential_flat_building', 'retail_premises', 'commercial_premises', 'office_premises',
                 'industrial_development', 'warehouse', 'boarding_house', 'child_care_centre', 'shop_top_housing']

    before = {}
    for dt in dev_types:
        cur.execute("""SELECT COUNT(*) FROM regulatory_provisions
            WHERE v2_is_actionable = true
              AND document_id NOT ILIKE '%%State_Environmental%%'
              AND document_id NOT ILIKE '%%Local_Environmental%%'
              AND document_id NOT ILIKE '%%SEPP%%' AND document_id NOT ILIKE '%%LEP%%'
              AND %s = ANY(v2_applicable_dev_types)
              AND v2_provision_type = 'control' AND v2_has_numeric_value = true""", (dt,))
        before[dt] = cur.fetchone()[0]
        print(f"   {dt}: {before[dt]}")

    # Marrickville enrichment
    print("\n2. ENRICHING MARRICKVILLE...")
    mappings = [
        ('%4.1%', ['dwelling_house', 'secondary_dwelling', 'dual_occupancy']),
        ('%4_1%', ['dwelling_house', 'secondary_dwelling', 'dual_occupancy']),
        ('%Low_Density%', ['dwelling_house', 'secondary_dwelling', 'dual_occupancy']),
        ('%4.2%', ['multi_dwelling_housing', 'residential_flat_building', 'dual_occupancy']),
        ('%4_2%', ['multi_dwelling_housing', 'residential_flat_building', 'dual_occupancy']),
        ('%Multi_Dwelling%', ['multi_dwelling_housing', 'residential_flat_building']),
        ('%Part 5%', ['retail_premises', 'commercial_premises', 'office_premises', 'shop_top_housing']),
        ('%5_0%', ['retail_premises', 'commercial_premises', 'office_premises']),
        ('%Part 6%', ['industrial_development', 'warehouse']),
        ('%6_0%', ['industrial_development', 'warehouse']),
        ('%Part 7%', ['child_care_centre']),
    ]

    for pattern, types in mappings:
        cur.execute("""UPDATE regulatory_provisions
            SET v2_applicable_dev_types = array_cat(COALESCE(v2_applicable_dev_types, ARRAY[]::text[]), %s::text[])
            WHERE v2_is_actionable = true
              AND document_id NOT ILIKE '%%State_Environmental%%' AND document_id NOT ILIKE '%%Local_Environmental%%'
              AND document_id NOT ILIKE '%%SEPP%%' AND document_id NOT ILIKE '%%LEP%%'
              AND document_id ILIKE %s
              AND document_id ILIKE '%%marrickville%%'
              AND NOT (v2_applicable_dev_types && %s::text[])""", (types, pattern, types))
        if cur.rowcount > 0:
            print(f"   {pattern}: {cur.rowcount}")

    # Leichhardt enrichment
    print("\n3. ENRICHING LEICHHARDT...")
    leich_mappings = [
        ('%Section_3%', ['dwelling_house', 'secondary_dwelling', 'dual_occupancy', 'multi_dwelling_housing']),
        ('%Section 3%', ['dwelling_house', 'secondary_dwelling', 'dual_occupancy', 'multi_dwelling_housing']),
        ('%Section_4%', ['retail_premises', 'commercial_premises', 'office_premises']),
    ]
    for pattern, types in leich_mappings:
        cur.execute("""UPDATE regulatory_provisions
            SET v2_applicable_dev_types = array_cat(COALESCE(v2_applicable_dev_types, ARRAY[]::text[]), %s::text[])
            WHERE v2_is_actionable = true
              AND document_id NOT ILIKE '%%State_Environmental%%' AND document_id NOT ILIKE '%%Local_Environmental%%'
              AND document_id NOT ILIKE '%%SEPP%%' AND document_id NOT ILIKE '%%LEP%%'
              AND document_id ILIKE %s
              AND document_id ILIKE '%%leichhardt%%'
              AND NOT (v2_applicable_dev_types && %s::text[])""", (types, pattern, types))
        if cur.rowcount > 0:
            print(f"   {pattern}: {cur.rowcount}")

    # Ashfield enrichment
    print("\n4. ENRICHING ASHFIELD...")
    ash_mappings = [
        ('%Chapter_F%', ['dwelling_house', 'secondary_dwelling', 'dual_occupancy', 'multi_dwelling_housing']),
        ('%Chapter F%', ['dwelling_house', 'secondary_dwelling', 'dual_occupancy']),
        ('%Chapter_C%', ['dwelling_house', 'secondary_dwelling', 'dual_occupancy', 'multi_dwelling_housing']),
    ]
    for pattern, types in ash_mappings:
        cur.execute("""UPDATE regulatory_provisions
            SET v2_applicable_dev_types = array_cat(COALESCE(v2_applicable_dev_types, ARRAY[]::text[]), %s::text[])
            WHERE v2_is_actionable = true
              AND document_id NOT ILIKE '%%State_Environmental%%' AND document_id NOT ILIKE '%%Local_Environmental%%'
              AND document_id NOT ILIKE '%%SEPP%%' AND document_id NOT ILIKE '%%LEP%%'
              AND document_id ILIKE %s
              AND document_id ILIKE '%%ashfield%%'
              AND NOT (v2_applicable_dev_types && %s::text[])""", (types, pattern, types))
        if cur.rowcount > 0:
            print(f"   {pattern}: {cur.rowcount}")

    # Generic Part 2 → all residential
    print("\n5. ENRICHING GENERIC PART 2...")
    all_res = ['dwelling_house', 'secondary_dwelling', 'dual_occupancy', 'multi_dwelling_housing', 'residential_flat_building', 'boarding_house']
    cur.execute("""UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(COALESCE(v2_applicable_dev_types, ARRAY[]::text[]), %s::text[])
        WHERE v2_is_actionable = true
          AND document_id NOT ILIKE '%%State_Environmental%%' AND document_id NOT ILIKE '%%Local_Environmental%%'
          AND document_id NOT ILIKE '%%SEPP%%' AND document_id NOT ILIKE '%%LEP%%'
          AND (document_id ILIKE '%%Part 2%%' OR document_id ILIKE '%%Part_2%%' OR document_id ILIKE '%%2.%%')
          AND v2_dcp_layer = 'generic'
          AND NOT (v2_applicable_dev_types && %s::text[])""", (all_res, all_res))
    print(f"   Part 2 generic: {cur.rowcount}")

    # Parking → all types
    print("\n6. ENRICHING PARKING...")
    all_types = all_res + ['retail_premises', 'commercial_premises', 'office_premises', 'industrial_development', 'warehouse', 'child_care_centre', 'shop_top_housing']
    cur.execute("""UPDATE regulatory_provisions
        SET v2_applicable_dev_types = array_cat(COALESCE(v2_applicable_dev_types, ARRAY[]::text[]), %s::text[])
        WHERE v2_is_actionable = true
          AND document_id NOT ILIKE '%%State_Environmental%%' AND document_id NOT ILIKE '%%Local_Environmental%%'
          AND document_id NOT ILIKE '%%SEPP%%' AND document_id NOT ILIKE '%%LEP%%'
          AND v2_topic = 'parking'
          AND NOT (v2_applicable_dev_types && %s::text[])""", (all_types, all_types))
    print(f"   Parking: {cur.rowcount}")

    # Text-based
    print("\n7. TEXT-BASED ENRICHMENT...")
    text_maps = [
        ('dwelling house', ['dwelling_house']),
        ('secondary dwelling', ['secondary_dwelling']),
        ('granny flat', ['secondary_dwelling']),
        ('dual occupancy', ['dual_occupancy']),
        ('multi dwelling', ['multi_dwelling_housing']),
        ('townhouse', ['multi_dwelling_housing']),
        ('apartment', ['residential_flat_building']),
        ('shop top', ['shop_top_housing']),
        ('child care', ['child_care_centre']),
        ('boarding house', ['boarding_house']),
    ]
    for kw, types in text_maps:
        cur.execute("""UPDATE regulatory_provisions
            SET v2_applicable_dev_types = array_cat(COALESCE(v2_applicable_dev_types, ARRAY[]::text[]), %s::text[])
            WHERE v2_is_actionable = true
              AND document_id NOT ILIKE '%%State_Environmental%%' AND document_id NOT ILIKE '%%Local_Environmental%%'
              AND document_id NOT ILIKE '%%SEPP%%' AND document_id NOT ILIKE '%%LEP%%'
              AND lower(provision_text) LIKE %s
              AND NOT (v2_applicable_dev_types && %s::text[])""", (types, f'%{kw}%', types))
        if cur.rowcount > 0:
            print(f"   '{kw}': {cur.rowcount}")

    # Dedup
    print("\n8. DEDUPLICATING...")
    cur.execute("""UPDATE regulatory_provisions
        SET v2_applicable_dev_types = (SELECT ARRAY(SELECT DISTINCT unnest(v2_applicable_dev_types) ORDER BY 1))
        WHERE v2_applicable_dev_types IS NOT NULL
          AND document_id NOT ILIKE '%%State_Environmental%%' AND document_id NOT ILIKE '%%Local_Environmental%%'""")

    # Results
    print("\n" + "=" * 70)
    print("RESULTS - DCP-ONLY CDC COVERAGE")
    print("=" * 70)

    after = {}
    for dt in dev_types:
        cur.execute("""SELECT COUNT(*) FROM regulatory_provisions
            WHERE v2_is_actionable = true
              AND document_id NOT ILIKE '%%State_Environmental%%'
              AND document_id NOT ILIKE '%%Local_Environmental%%'
              AND document_id NOT ILIKE '%%SEPP%%' AND document_id NOT ILIKE '%%LEP%%'
              AND %s = ANY(v2_applicable_dev_types)
              AND v2_provision_type = 'control' AND v2_has_numeric_value = true""", (dt,))
        after[dt] = cur.fetchone()[0]
        change = after[dt] - before[dt]
        status = "OK" if after[dt] >= 20 else "LOW"
        print(f"   {dt}: {before[dt]} -> {after[dt]} (+{change}) [{status}]")

    print("\nBY COUNCIL:")
    for council in ['marrickville', 'leichhardt', 'ashfield']:
        cur.execute("""SELECT COUNT(*) FROM regulatory_provisions
            WHERE v2_is_actionable = true AND document_id ILIKE %s
              AND document_id NOT ILIKE '%%State_Environmental%%' AND document_id NOT ILIKE '%%Local_Environmental%%'
              AND v2_provision_type = 'control' AND v2_has_numeric_value = true""", (f'%{council}%',))
        print(f"   {council}: {cur.fetchone()[0]}")

    confirm = input("\nCommit? (y/n): ")
    if confirm.lower() == 'y':
        conn.commit()
        print("Committed!")
    else:
        conn.rollback()
        print("Rolled back.")
    conn.close()

if __name__ == "__main__":
    main()
