#!/usr/bin/env python3
"""
Insert NSW Apartment Design Guide Statutory Building Separation Standards
Uses safe db wrapper as per .claude guidelines
"""
import sys
sys.path.append('venv_linux/lib/python3.11/site-packages')
from db_safety_wrapper import get_safe_connection

print("=" * 80)
print("INSERTING ADG STATUTORY BUILDING SEPARATION STANDARDS")
print("=" * 80)
print("\nSource: NSW Apartment Design Guide - Part 3: Siting the Development")
print("Section: 3F-1 Visual Privacy - Design Criteria 1")
print("Legal Status: STATUTORY (Referenced by SEPP (Housing) 2021)")
print("URL: https://www.planning.nsw.gov.au/sites/default/files/2023-03/")
print("     apartment-design-guide-part-3-siting-the-development.pdf")
print("Page: 63\n")

# Initialize safe connection
conn = get_safe_connection()
conn.connect()
cur = conn.cursor()

# Check if setback_rules table exists
print("[1/4] Verifying setback_rules table exists...")
try:
    cur.execute("SELECT COUNT(*) FROM setback_rules LIMIT 1")
    print("[OK] setback_rules table found")
except Exception as e:
    print(f"[ERROR] setback_rules table not found: {e}")
    print("[INFO] Run migrations/create_setback_rules_table.sql first")
    conn.close()
    sys.exit(1)

# Standards to insert
adg_standards = [
    # Up to 12m (4 storeys) - Habitable rooms
    {
        'ref': 'ADG 3F-1',
        'boundary': 'side',
        'building_element': 'all',
        'dev_types': ['multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing'],
        'site_condition': ['building_height_up_to_12m'],
        'setback': 6.0,
        'room_type': 'habitable',
        'exceptions': 'Habitable rooms and balconies. Between buildings on same site: combine separations (6m + 6m = 12m). Gallery access = habitable space.',
        'height_desc': 'up to 12m (4 storeys)',
    },
    {
        'ref': 'ADG 3F-1',
        'boundary': 'rear',
        'building_element': 'all',
        'dev_types': ['multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing'],
        'site_condition': ['building_height_up_to_12m'],
        'setback': 6.0,
        'room_type': 'habitable',
        'exceptions': 'Habitable rooms and balconies. Between buildings on same site: combine separations (6m + 6m = 12m). Gallery access = habitable space.',
        'height_desc': 'up to 12m (4 storeys)',
    },
    # Up to 12m (4 storeys) - Non-habitable rooms
    {
        'ref': 'ADG 3F-1 (Non-habitable)',
        'boundary': 'side',
        'building_element': 'all',
        'dev_types': ['multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing'],
        'site_condition': ['building_height_up_to_12m'],
        'setback': 3.0,
        'room_type': 'non_habitable',
        'exceptions': 'Non-habitable rooms (bathrooms, laundries, storage). Between buildings on same site: combine separations.',
        'height_desc': 'up to 12m (4 storeys)',
    },
    {
        'ref': 'ADG 3F-1 (Non-habitable)',
        'boundary': 'rear',
        'building_element': 'all',
        'dev_types': ['multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing'],
        'site_condition': ['building_height_up_to_12m'],
        'setback': 3.0,
        'room_type': 'non_habitable',
        'exceptions': 'Non-habitable rooms (bathrooms, laundries, storage). Between buildings on same site: combine separations.',
        'height_desc': 'up to 12m (4 storeys)',
    },
    # 12m-25m (5-8 storeys) - Habitable rooms
    {
        'ref': 'ADG 3F-1',
        'boundary': 'side',
        'building_element': 'all',
        'dev_types': ['residential_flat_building', 'shop_top_housing'],
        'site_condition': ['building_height_12m_to_25m'],
        'setback': 9.0,
        'room_type': 'habitable',
        'exceptions': 'Habitable rooms and balconies. Between buildings on same site: combine separations (9m + 9m = 18m). Gallery access = habitable space.',
        'height_desc': 'up to 25m (5-8 storeys)',
    },
    {
        'ref': 'ADG 3F-1',
        'boundary': 'rear',
        'building_element': 'all',
        'dev_types': ['residential_flat_building', 'shop_top_housing'],
        'site_condition': ['building_height_12m_to_25m'],
        'setback': 9.0,
        'room_type': 'habitable',
        'exceptions': 'Habitable rooms and balconies. Between buildings on same site: combine separations (9m + 9m = 18m). Gallery access = habitable space.',
        'height_desc': 'up to 25m (5-8 storeys)',
    },
    # 12m-25m (5-8 storeys) - Non-habitable rooms
    {
        'ref': 'ADG 3F-1 (Non-habitable)',
        'boundary': 'side',
        'building_element': 'all',
        'dev_types': ['residential_flat_building', 'shop_top_housing'],
        'site_condition': ['building_height_12m_to_25m'],
        'setback': 4.5,
        'room_type': 'non_habitable',
        'exceptions': 'Non-habitable rooms (bathrooms, laundries, storage). Between buildings on same site: combine separations.',
        'height_desc': 'up to 25m (5-8 storeys)',
    },
    {
        'ref': 'ADG 3F-1 (Non-habitable)',
        'boundary': 'rear',
        'building_element': 'all',
        'dev_types': ['residential_flat_building', 'shop_top_housing'],
        'site_condition': ['building_height_12m_to_25m'],
        'setback': 4.5,
        'room_type': 'non_habitable',
        'exceptions': 'Non-habitable rooms (bathrooms, laundries, storage). Between buildings on same site: combine separations.',
        'height_desc': 'up to 25m (5-8 storeys)',
    },
    # Over 25m (9+ storeys) - Habitable rooms
    {
        'ref': 'ADG 3F-1',
        'boundary': 'side',
        'building_element': 'all',
        'dev_types': ['residential_flat_building'],
        'site_condition': ['building_height_over_25m'],
        'setback': 12.0,
        'room_type': 'habitable',
        'exceptions': 'Habitable rooms and balconies. Between buildings on same site: combine separations (12m + 12m = 24m). Gallery access = habitable space.',
        'height_desc': 'over 25m (9+ storeys)',
    },
    {
        'ref': 'ADG 3F-1',
        'boundary': 'rear',
        'building_element': 'all',
        'dev_types': ['residential_flat_building'],
        'site_condition': ['building_height_over_25m'],
        'setback': 12.0,
        'room_type': 'habitable',
        'exceptions': 'Habitable rooms and balconies. Between buildings on same site: combine separations (12m + 12m = 24m). Gallery access = habitable space.',
        'height_desc': 'over 25m (9+ storeys)',
    },
    # Over 25m (9+ storeys) - Non-habitable rooms
    {
        'ref': 'ADG 3F-1 (Non-habitable)',
        'boundary': 'side',
        'building_element': 'all',
        'dev_types': ['residential_flat_building'],
        'site_condition': ['building_height_over_25m'],
        'setback': 6.0,
        'room_type': 'non_habitable',
        'exceptions': 'Non-habitable rooms (bathrooms, laundries, storage). Between buildings on same site: combine separations.',
        'height_desc': 'over 25m (9+ storeys)',
    },
    {
        'ref': 'ADG 3F-1 (Non-habitable)',
        'boundary': 'rear',
        'building_element': 'all',
        'dev_types': ['residential_flat_building'],
        'site_condition': ['building_height_over_25m'],
        'setback': 6.0,
        'room_type': 'non_habitable',
        'exceptions': 'Non-habitable rooms (bathrooms, laundries, storage). Between buildings on same site: combine separations.',
        'height_desc': 'over 25m (9+ storeys)',
    },
]

print(f"\n[2/4] Inserting {len(adg_standards)} ADG statutory standards...")
print("-" * 80)

inserted = 0
for i, std in enumerate(adg_standards, 1):
    source_text = f"Minimum required separation distances from buildings to the side and rear boundaries: Building height {std['height_desc']} - {std['room_type'].title()} rooms: {std['setback']}m"

    notes = f"STATUTORY REQUIREMENT under SEPP (Housing) 2021. Source: https://www.planning.nsw.gov.au/sites/default/files/2023-03/apartment-design-guide-part-3-siting-the-development.pdf (Page 63, Design Criteria 1)"

    try:
        cur.execute("""
            INSERT INTO setback_rules (
                ref_number,
                boundary_type,
                storey_level,
                building_element,
                development_type,
                site_condition,
                lga,
                setback_meters,
                qualifier,
                measurement_from,
                can_overhang,
                exceptions,
                document_type,
                document_name,
                priority,
                source_text,
                rationale,
                extraction_confidence,
                manual_verified,
                notes
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
        """, (
            std['ref'],
            std['boundary'],
            'all',  # Applies to all upper floors
            std['building_element'],
            std['dev_types'],
            std['site_condition'],
            'NSW',  # State-wide
            std['setback'],
            'minimum',
            'boundary',
            False,
            std['exceptions'],
            'SEPP',
            'NSW Apartment Design Guide - Part 3: Siting the Development - Section 3F-1 Visual Privacy',
            1,  # Priority 1 (SEPP level)
            source_text,
            'To ensure visual privacy is achieved between apartments and neighbouring properties.',
            1.0,
            True,  # Manually verified from official NSW Planning PDF
            notes
        ))

        print(f"  [{i}/{len(adg_standards)}] {std['height_desc']:25s} | {std['boundary']:4s} | {std['room_type']:12s} | {std['setback']}m")
        inserted += 1

    except Exception as e:
        print(f"  [ERROR] Failed to insert standard {i}: {e}")

conn.commit()

print(f"\n[OK] Inserted {inserted}/{len(adg_standards)} standards")

# Verification
print("\n[3/4] Verifying insertion...")
cur.execute("""
    SELECT
        COUNT(*) as total_rules,
        COUNT(DISTINCT site_condition) as height_categories,
        COUNT(DISTINCT boundary_type) as boundary_types
    FROM setback_rules
    WHERE ref_number = 'ADG 3F-1'
""")

result = cur.fetchone()
total, height_cats, boundary_types = result

print(f"[OK] ADG 3F-1 Standards:")
print(f"  - Total rules: {total}")
print(f"  - Height categories: {height_cats}")
print(f"  - Boundary types: {boundary_types}")

# Show summary by height category
print("\n[4/4] Summary by building height:")
print("-" * 80)
cur.execute("""
    SELECT
        site_condition,
        building_element,
        boundary_type,
        setback_meters,
        development_type
    FROM setback_rules
    WHERE ref_number = 'ADG 3F-1'
    ORDER BY setback_meters DESC, site_condition, boundary_type
""")

for row in cur.fetchall():
    condition, element, boundary, setback, dev_types = row
    condition_str = condition[0] if condition else 'unknown'  # site_condition is an array
    height_label = condition_str.replace('building_height_', '').replace('_', ' ')
    element_label = 'Habitable' if element == 'all' else 'Non-habitable'
    print(f"  {height_label:20s} | {element_label:13s} | {boundary:4s} | {setback}m")

conn.close()

print("\n" + "=" * 80)
print("INSERTION COMPLETE")
print("=" * 80)
print("\nThese are STATUTORY requirements referenced by SEPP (Housing) 2021.")
print("They will now be returned in setback queries for multi-dwelling developments.")
