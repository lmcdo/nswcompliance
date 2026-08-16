#!/usr/bin/env python3
"""
Map the LLM-extracted categories to topics.

The extraction_outputs/*.json files have:
- source_provision_id: links to regulatory_provisions.id
- category: LLM-assigned category like "building_height", "setback_front"

We can use this to update v2_topic for those provisions!
"""
import json
import os
import sys

sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv('frontend-nextjs/.env.local')
import psycopg2

# Map extraction categories to topics
CATEGORY_TO_TOPIC = {
    # Height
    'building_height': 'height',
    'building_height_r1': 'height',
    'building_height_r2': 'height',
    'building_height_b1': 'height',
    'building_wall_height': 'height',

    # Setbacks
    'setback_front': 'setbacks',
    'setback_front_r1': 'setbacks',
    'setback_front_r2': 'setbacks',
    'setback_side': 'setbacks',
    'setback_rear': 'setbacks',

    # Parking
    'parking': 'parking',
    'parking_accessible': 'parking',
    'parking_accessible_r1': 'parking',
    'parking_rate': 'parking',

    # Landscaping
    'landscaping': 'landscaping',
    'landscaping_front_yard': 'landscaping',
    'landscaping_front_yard_r2': 'landscaping',
    'landscaping_deep_soil': 'landscaping',
    'landscaping_open_space_private': 'open_space',

    # Building form/design
    'building_materials': 'building_design',
    'building_depth': 'building_form',
    'building_depth_r2': 'building_form',
    'building_separation': 'building_form',
    'building_separation_r1': 'building_form',
    'design_excellence': 'building_design',

    # Fencing
    'fencing_front': 'fencing',
    'fencing_front_r1': 'fencing',

    # Stormwater
    'stormwater_management': 'stormwater',

    # Privacy
    'acoustic_privacy': 'privacy',
    'visual_privacy': 'privacy',

    # Solar
    'solar_access': 'solar',
    'overshadowing': 'solar',

    # FSR
    'floor_space_ratio': 'building_form',

    # Site
    'site_area': 'general',
    'subdivision_lot_size': 'general',
    'subdivision_lot_size_r2': 'general',

    # Other
    'driveway_width': 'vehicle_access',
}


def main():
    conn = psycopg2.connect(os.getenv('SUPABASE_DB_URL'))
    cur = conn.cursor()

    print("="*70)
    print("MAPPING EXTRACTION CATEGORIES TO TOPICS")
    print("="*70)

    output_dir = 'extraction_outputs'
    all_mappings = []  # (provision_id, category, topic)

    for filename in os.listdir(output_dir):
        if not filename.endswith('.json'):
            continue
        filepath = os.path.join(output_dir, filename)

        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            reqs = data.get('requirements', [])
            if not reqs:
                continue

            for r in reqs:
                prov_id = r.get('source_provision_id')
                category = r.get('category')
                if prov_id and category:
                    topic = CATEGORY_TO_TOPIC.get(category)
                    if topic:
                        all_mappings.append((prov_id, category, topic))

        except Exception as e:
            print(f'{filename}: {e}')

    print(f"\nTotal mappings from extraction files: {len(all_mappings)}")

    # Get unique provision IDs
    unique_ids = set(m[0] for m in all_mappings)
    print(f"Unique provision IDs: {len(unique_ids)}")

    # Check how many of these are currently "unreliable"
    # (provisions that were guessed via page inheritance)
    cur.execute('''
        SELECT id, v2_topic, v2_marker
        FROM regulatory_provisions
        WHERE id = ANY(%s)
    ''', (list(unique_ids),))

    provisions = {r[0]: (r[1], r[2]) for r in cur.fetchall()}

    has_marker = 0
    no_marker = 0
    would_change = 0

    for prov_id, category, new_topic in all_mappings:
        if prov_id in provisions:
            current_topic, marker = provisions[prov_id]
            if marker:
                has_marker += 1
            else:
                no_marker += 1
                if current_topic != new_topic:
                    would_change += 1

    print(f"\nProvisions with extraction data:")
    print(f"  Already have marker (reliable): {has_marker}")
    print(f"  No marker (currently guessed): {no_marker}")
    print(f"  Would change topic: {would_change}")

    # Show category distribution
    print(f"\nCategory → Topic mapping coverage:")
    unmapped = {}
    for prov_id, category, topic in all_mappings:
        if not topic:
            unmapped[category] = unmapped.get(category, 0) + 1

    if unmapped:
        print("  Unmapped categories:")
        for cat, cnt in sorted(unmapped.items(), key=lambda x: -x[1]):
            print(f"    {cat}: {cnt}")

    conn.close()


if __name__ == '__main__':
    main()
