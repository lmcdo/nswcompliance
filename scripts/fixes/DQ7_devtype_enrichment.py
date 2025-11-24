#!/usr/bin/env python3
"""
DQ-7 Fix: Dev-Type Enrichment

Systematically re-tags provisions with appropriate dev_types based on:
1. DCP section/document_id patterns
2. Provision content keywords
3. Existing dev_type arrays (expand, don't replace)

Target: 20-60 CDC provisions per dev_type
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2
from typing import List, Set

# Dev-type mapping rules by DCP section pattern
SECTION_DEVTYPE_MAPPING = {
    # Marrickville Part 4.1 - Low Density Residential
    'Part 4.1': ['dwelling_house', 'secondary_dwelling', 'dual_occupancy'],
    '4.1': ['dwelling_house', 'secondary_dwelling', 'dual_occupancy'],
    '4_1': ['dwelling_house', 'secondary_dwelling', 'dual_occupancy'],
    'Low_Density': ['dwelling_house', 'secondary_dwelling', 'dual_occupancy'],
    'Low Density': ['dwelling_house', 'secondary_dwelling', 'dual_occupancy'],

    # Marrickville Part 4.2 - Multi-dwelling
    'Part 4.2': ['multi_dwelling_housing', 'residential_flat_building', 'dual_occupancy'],
    '4.2': ['multi_dwelling_housing', 'residential_flat_building', 'dual_occupancy'],
    '4_2': ['multi_dwelling_housing', 'residential_flat_building', 'dual_occupancy'],
    'Multi_Dwelling': ['multi_dwelling_housing', 'residential_flat_building'],
    'Multi Dwelling': ['multi_dwelling_housing', 'residential_flat_building'],

    # Marrickville Part 5 - Commercial
    'Part 5': ['retail_premises', 'commercial_premises', 'office_premises', 'shop_top_housing'],
    '5_0': ['retail_premises', 'commercial_premises', 'office_premises'],
    'Commercial': ['retail_premises', 'commercial_premises', 'office_premises'],

    # Marrickville Part 6 - Industrial
    'Part 6': ['industrial_development', 'warehouse', 'light_industry'],
    '6_0': ['industrial_development', 'warehouse'],
    'Industrial': ['industrial_development', 'warehouse'],

    # Leichhardt Section 3 - Residential
    'Section 3': ['dwelling_house', 'secondary_dwelling', 'dual_occupancy', 'multi_dwelling_housing'],
    'Section_3': ['dwelling_house', 'secondary_dwelling', 'dual_occupancy', 'multi_dwelling_housing'],

    # Leichhardt Section 4 - Non-Residential
    'Section 4': ['retail_premises', 'commercial_premises', 'office_premises', 'industrial_development'],
    'Section_4': ['retail_premises', 'commercial_premises', 'office_premises'],

    # Ashfield Chapter F - Development Category (residential focus)
    'Chapter F': ['dwelling_house', 'secondary_dwelling', 'dual_occupancy', 'multi_dwelling_housing'],
    'Chapter_F': ['dwelling_house', 'secondary_dwelling', 'dual_occupancy'],
}

# Keyword-based dev_type inference
KEYWORD_DEVTYPE_MAPPING = {
    'dwelling house': ['dwelling_house'],
    'dwelling-house': ['dwelling_house'],
    'single dwelling': ['dwelling_house'],
    'detached dwelling': ['dwelling_house'],

    'secondary dwelling': ['secondary_dwelling'],
    'granny flat': ['secondary_dwelling'],
    'ancillary dwelling': ['secondary_dwelling'],

    'dual occupancy': ['dual_occupancy'],
    'dual-occupancy': ['dual_occupancy'],

    'multi dwelling': ['multi_dwelling_housing'],
    'multi-dwelling': ['multi_dwelling_housing'],
    'townhouse': ['multi_dwelling_housing'],
    'town house': ['multi_dwelling_housing'],
    'villa': ['multi_dwelling_housing'],

    'residential flat': ['residential_flat_building'],
    'apartment': ['residential_flat_building'],
    'unit development': ['residential_flat_building'],

    'retail': ['retail_premises'],
    'shop': ['retail_premises', 'shop_top_housing'],
    'commercial premises': ['commercial_premises'],
    'commercial development': ['commercial_premises'],

    'office': ['office_premises'],

    'industrial': ['industrial_development'],
    'warehouse': ['warehouse'],
    'factory': ['industrial_development'],

    'boarding house': ['boarding_house'],

    'child care': ['child_care_centre'],
    'childcare': ['child_care_centre'],

    'shop top': ['shop_top_housing'],
    'mixed use': ['shop_top_housing', 'residential_flat_building'],
}

# ALL residential types for generic residential provisions
ALL_RESIDENTIAL = [
    'dwelling_house', 'secondary_dwelling', 'dual_occupancy',
    'multi_dwelling_housing', 'residential_flat_building', 'boarding_house'
]

# ALL commercial types
ALL_COMMERCIAL = ['retail_premises', 'commercial_premises', 'office_premises', 'shop_top_housing']

# ALL industrial types
ALL_INDUSTRIAL = ['industrial_development', 'warehouse', 'light_industry']


def get_devtypes_from_document(document_id: str) -> Set[str]:
    """Infer dev_types from document_id patterns."""
    if not document_id:
        return set()

    result = set()
    doc_lower = document_id.lower()

    for pattern, dev_types in SECTION_DEVTYPE_MAPPING.items():
        if pattern.lower() in doc_lower:
            result.update(dev_types)

    return result


def get_devtypes_from_text(text: str) -> Set[str]:
    """Infer dev_types from provision text keywords."""
    if not text:
        return set()

    result = set()
    text_lower = text.lower()

    for keyword, dev_types in KEYWORD_DEVTYPE_MAPPING.items():
        if keyword in text_lower:
            result.update(dev_types)

    return result


def expand_all_tag(current_devtypes: List[str], document_id: str, text: str) -> List[str]:
    """
    Expand 'ALL' tag to specific dev_types based on context.
    """
    if 'ALL' not in current_devtypes:
        return current_devtypes

    # Remove ALL and add specific types
    result = set(dt for dt in current_devtypes if dt != 'ALL')

    # Infer from document
    result.update(get_devtypes_from_document(document_id))

    # Infer from text
    result.update(get_devtypes_from_text(text))

    # If still empty after inference, use residential as default (most common)
    if not result:
        result.update(ALL_RESIDENTIAL)

    return sorted(list(result))


def enrich_devtypes(current_devtypes: List[str], document_id: str, text: str) -> List[str]:
    """
    Enrich dev_types array by adding inferred types.
    Never removes existing types, only adds.
    """
    result = set(current_devtypes or [])

    # Handle ALL expansion
    if 'ALL' in result:
        return expand_all_tag(list(result), document_id, text)

    # Add inferred types from document_id
    result.update(get_devtypes_from_document(document_id))

    # Add inferred types from text (only if provision is short enough to be specific)
    if text and len(text) < 500:
        result.update(get_devtypes_from_text(text))

    return sorted(list(result))


def main():
    print("=" * 70)
    print("DQ-7 FIX: Dev-Type Enrichment")
    print("=" * 70)

    conn = psycopg2.connect('dbname=nsw_planning')
    cur = conn.cursor()

    # Get current state
    print("\n1. Current dev_type coverage (CDC provisions):")
    dev_types_to_check = [
        'dwelling_house', 'secondary_dwelling', 'dual_occupancy',
        'multi_dwelling_housing', 'residential_flat_building',
        'retail_premises', 'commercial_premises', 'office_premises',
        'industrial_development', 'warehouse', 'boarding_house',
        'child_care_centre', 'shop_top_housing'
    ]

    before_counts = {}
    for dt in dev_types_to_check:
        cur.execute('''
            SELECT COUNT(*) FROM regulatory_provisions
            WHERE v2_is_actionable = true
              AND v2_dcp_layer = 'generic'
              AND v2_provision_type = 'control'
              AND v2_has_numeric_value = true
              AND %s = ANY(v2_applicable_dev_types)
        ''', (dt,))
        before_counts[dt] = cur.fetchone()[0]
        print(f"   {dt}: {before_counts[dt]}")

    # Fetch provisions to enrich
    print("\n2. Fetching provisions to enrich...")
    cur.execute('''
        SELECT id, document_id, provision_text, v2_applicable_dev_types
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
          AND v2_dcp_layer = 'generic'
    ''')
    provisions = cur.fetchall()
    print(f"   Found {len(provisions)} generic provisions")

    # Process each provision
    print("\n3. Enriching dev_types...")
    updates = 0
    for i, (prov_id, doc_id, text, current_devtypes) in enumerate(provisions):
        if i % 2000 == 0:
            print(f"   Processed {i}/{len(provisions)}...")

        current = current_devtypes or []
        enriched = enrich_devtypes(current, doc_id, text)

        # Only update if changed
        if set(enriched) != set(current):
            cur.execute('''
                UPDATE regulatory_provisions
                SET v2_applicable_dev_types = %s
                WHERE id = %s
            ''', (enriched, prov_id))
            updates += 1

    print(f"\n   Updated {updates} provisions")

    # Check new state
    print("\n4. New dev_type coverage (CDC provisions):")
    after_counts = {}
    for dt in dev_types_to_check:
        cur.execute('''
            SELECT COUNT(*) FROM regulatory_provisions
            WHERE v2_is_actionable = true
              AND v2_dcp_layer = 'generic'
              AND v2_provision_type = 'control'
              AND v2_has_numeric_value = true
              AND %s = ANY(v2_applicable_dev_types)
        ''', (dt,))
        after_counts[dt] = cur.fetchone()[0]
        change = after_counts[dt] - before_counts[dt]
        status = "OK" if after_counts[dt] >= 20 else "LOW"
        print(f"   {dt}: {before_counts[dt]} -> {after_counts[dt]} (+{change}) [{status}]")

    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    ok_count = sum(1 for dt in dev_types_to_check if after_counts[dt] >= 20)
    print(f"Dev types with adequate coverage (>=20): {ok_count}/{len(dev_types_to_check)}")

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
