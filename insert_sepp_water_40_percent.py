#!/usr/bin/env python3
"""
Insert manually curated structured requirements for SEPP (Sustainable Buildings) 2022
40% Water provision - Schedule 1 & 2 (Residential)
"""
import json
import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from db_safety_wrapper import get_safe_connection

# MANUALLY EXTRACTED from SEPP (Sustainable Buildings) 2022 - NSW Legislation
# 100% reliable, no AI interpretation

requirement_data = {
    "title": "40% Water Reduction Target",
    "description": "Minimum water efficiency standards for fixtures, hot water, and pools to achieve 40% reduction from baseline",
    "climate_zone": "56",
    "applies_to": "New BASIX buildings (Climate Zone 56)",
    "categories": [
        {
            "name": "Water Fixtures",
            "reference": "Schedule 2, Section 2.1",
            "legal_citation": "SEPP (Sustainable Buildings) 2022, Schedule 2, Part 1",
            "requirements": [
                {
                    "fixture": "Toilets",
                    "standard": "max 4L/flush OR 3-star WELS rating",
                    "mandatory": True,
                    "legal_text": "A toilet must have— (a) a flow rate of no more than 4 litres for a flush, or (b) at least a 3-star WELS water rating."
                },
                {
                    "fixture": "Showers/taps",
                    "standard": "max 9L/min OR 3-star WELS rating",
                    "mandatory": True,
                    "legal_text": "A shower and a tap must have— (a) a flow rate of no more than 9 litres per minute, or (b) at least a 3-star WELS water rating."
                }
            ]
        },
        {
            "name": "Hot Water Systems",
            "reference": "Schedule 2, Section 2",
            "legal_citation": "SEPP (Sustainable Buildings) 2022, Schedule 2, Part 1, Section 2",
            "requirements": [
                {
                    "option": "Solar system (gas/electric/wood-boosted)",
                    "mandatory": False,
                    "note": "One of the following options must be selected"
                },
                {
                    "option": "Electric storage with photovoltaic system",
                    "mandatory": False
                },
                {
                    "option": "Electric heat pump",
                    "mandatory": False
                },
                {
                    "option": "Gas storage or instantaneous system",
                    "mandatory": False
                },
                {
                    "option": "Wood combustion system",
                    "mandatory": False
                }
            ]
        },
        {
            "name": "Swimming Pools",
            "reference": "Schedule 2, Section 4",
            "legal_citation": "SEPP (Sustainable Buildings) 2022, Schedule 2, Part 1, Section 4",
            "requirements": [
                {
                    "requirement": "Pool covers required",
                    "mandatory": True,
                    "condition": "Area B only (Climate Zone 56 postcodes 2204, 2205, etc.)"
                },
                {
                    "requirement": "Rainwater tanks required (min 2000L connected to pool filter)",
                    "mandatory": True,
                    "condition": "Area B only"
                }
            ]
        }
    ],
    "full_text_available": True,
    "manually_curated": True,
    "curated_date": "2025-10-10",
    "source_url": "https://legislation.nsw.gov.au/view/html/inforce/current/epi-2022-0658"
}

print("Inserting structured SEPP requirement: 40% Water (Residential)...")
print(f"Categories: {len(requirement_data['categories'])} (Water Fixtures, Hot Water, Pools)")
print("Note: Lighting requirements moved to separate Energy & Lighting entry")

with get_safe_connection() as conn:
    cursor = conn.cursor()

    # Check if already exists
    cursor.execute("""
        SELECT id FROM sepp_structured_requirements
        WHERE sepp_id = %s AND schedule = %s
    """, ('sustainable_buildings_2022', '1_and_2'))

    existing = cursor.fetchone()
    if existing:
        print(f"Already exists (id={existing[0]}), updating...")
        cursor.execute("""
            UPDATE sepp_structured_requirements
            SET requirement_data = %s,
                updated_at = NOW()
            WHERE id = %s
        """, (json.dumps(requirement_data), existing[0]))
    else:
        print("Inserting new record...")
        cursor.execute("""
            INSERT INTO sepp_structured_requirements (
                sepp_id,
                sepp_name,
                schedule,
                schedule_name,
                section,
                section_name,
                development_type_category,
                requirement_data
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            'sustainable_buildings_2022',
            'State Environmental Planning Policy (Sustainable Buildings) 2022',
            '1_and_2',  # Both Schedule 1 and 2 apply to residential
            'Standards for erection of BASIX buildings and alterations',
            '2.1',
            'Part 1 Energy and water use',
            'residential',
            json.dumps(requirement_data)
        ))

    conn.commit()

    # Verify
    cursor.execute("""
        SELECT id, sepp_id, schedule,
               jsonb_array_length(requirement_data->'categories') as category_count
        FROM sepp_structured_requirements
        WHERE sepp_id = 'sustainable_buildings_2022'
    """)

    result = cursor.fetchone()
    print(f"\nSuccess!")
    print(f"  ID: {result[0]}")
    print(f"  SEPP: {result[1]}")
    print(f"  Schedule: {result[2]}")
    print(f"  Categories: {result[3]}")
    print("\nStructured SEPP requirement ready for API consumption")
