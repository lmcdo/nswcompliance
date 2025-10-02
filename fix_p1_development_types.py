#!/usr/bin/env python3
"""
Fix PRP-P1: Extract development types from extracted_text
Populate the missing development_types field (86% empty)
"""

from db_config import get_connection
import re
import json

# NSW Standard Instrument development types mapping
DEVELOPMENT_TYPE_PATTERNS = {
    'dwelling_house': r'\bdwelling\s+house[s]?\b',
    'dual_occupancy': r'\bdual\s+occupanc(?:y|ies)\b',
    'multi_dwelling_housing': r'\bmulti\s+dwelling\s+housing\b',
    'residential_flat_building': r'\bresidential\s+flat\s+building[s]?\b',
    'shop': r'\bshop[s]?\b',
    'retail_premises': r'\bretail\s+premises\b',
    'office_premises': r'\boffice\s+premises\b',
    'commercial_premises': r'\bcommercial\s+premises\b',
    'business_premises': r'\bbusiness\s+premises\b',
    'industrial_premises': r'\bindustrial\s+premises\b',
    'warehouse': r'\bwarehouse[s]?\b',
    'light_industry': r'\blight\s+industr(?:y|ies)\b',
    'food_and_drink_premises': r'\bfood\s+and\s+drink\s+premises\b',
    'restaurant': r'\brestaurant[s]?\b',
    'cafe': r'\bcaf[eé][s]?\b',
    'hotel': r'\bhotel[s]?\b',
    'pub': r'\bpub[s]?\b',
    'child_care_centre': r'\bchild\s+care\s+centre[s]?\b',
    'educational_establishment': r'\beducational\s+establishment[s]?\b',
    'school': r'\bschool[s]?\b',
    'health_services_facility': r'\bhealth\s+services?\s+facilit(?:y|ies)\b',
    'hospital': r'\bhospital[s]?\b',
    'community_facility': r'\bcommunity\s+facilit(?:y|ies)\b',
    'place_of_public_worship': r'\bplace[s]?\s+of\s+public\s+worship\b',
    'recreation_facility': r'\brecreation\s+facilit(?:y|ies)\b',
    'entertainment_facility': r'\bentertainment\s+facilit(?:y|ies)\b',
    'tourist_and_visitor_accommodation': r'\btourist\s+and\s+visitor\s+accommodation\b',
    'serviced_apartment': r'\bserviced\s+apartment[s]?\b',
    'boarding_house': r'\bboarding\s+house[s]?\b',
    'car_park': r'\bcar\s+park[s]?\b',
    'vehicle_repair_station': r'\bvehicle\s+repair\s+station[s]?\b',
    'service_station': r'\bservice\s+station[s]?\b',
}

def extract_development_types(text):
    """Extract development types from regulatory text"""
    if not text:
        return []

    text_lower = text.lower()
    found_types = []

    for dev_type, pattern in DEVELOPMENT_TYPE_PATTERNS.items():
        if re.search(pattern, text_lower, re.IGNORECASE):
            found_types.append(dev_type)

    return found_types

def fix_p1_development_types():
    conn = get_connection()
    cur = conn.cursor()

    print("=" * 70)
    print("FIX PRP-P1: EXTRACT DEVELOPMENT TYPES")
    print("=" * 70)

    # Get all records with empty development_types
    cur.execute("""
        SELECT id, extracted_text
        FROM permissibility_analysis
        WHERE development_types IS NULL OR development_types = '' OR development_types = 'null'
    """)

    empty_records = cur.fetchall()
    print(f"\nRecords with empty development_types: {len(empty_records)}")

    updated_count = 0
    skipped_count = 0

    for record_id, extracted_text in empty_records:
        # Extract development types
        dev_types = extract_development_types(extracted_text)

        if dev_types:
            # Store as JSON array
            dev_types_json = json.dumps(dev_types)

            cur.execute("""
                UPDATE permissibility_analysis
                SET development_types = %s
                WHERE id = %s
            """, (dev_types_json, record_id))

            updated_count += 1

            if updated_count <= 10:  # Show first 10 examples
                print(f"\n  Updated ID {record_id}:")
                print(f"    Text: {extracted_text[:80]}...")
                print(f"    Types: {dev_types}")
        else:
            skipped_count += 1

    conn.commit()

    # Verify results
    cur.execute("""
        SELECT COUNT(*)
        FROM permissibility_analysis
        WHERE development_types IS NOT NULL AND development_types != '' AND development_types != 'null'
    """)
    populated_after = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM permissibility_analysis")
    total = cur.fetchone()[0]

    percentage = (populated_after / total * 100) if total > 0 else 0

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    print(f"  Updated: {updated_count} records")
    print(f"  Skipped (no types found): {skipped_count} records")
    print(f"  Populated after fix: {populated_after}/{total} ({percentage:.1f}%)")

    if percentage >= 60:
        print("\n[PASS] Development types extraction successful")
        print("RECOMMENDATION: Proceed with P1 validation")
    else:
        print("\n[WARN] Many records still missing development types")
        print("RECOMMENDATION: Manual review of skipped records")

    conn.close()

if __name__ == "__main__":
    fix_p1_development_types()