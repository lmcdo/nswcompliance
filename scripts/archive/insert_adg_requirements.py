#!/usr/bin/env python3
"""
Insert ADG Design Criteria into sepp_adg_requirements table.

Source: NSW Apartment Design Guide (March 2023)
- Part 3: Siting the Development (Pages 43-76)
- Part 4: Designing the Building (Pages 77-148)

This script extracts all Tier 1 Design Criteria with numeric standards.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

# Load environment variables
load_dotenv()
load_dotenv(os.path.join(os.path.dirname(__file__), '..', 'frontend-nextjs', '.env.local'))

DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("Error: Missing DATABASE_URL")
    sys.exit(1)

def get_connection():
    """Get database connection."""
    return psycopg2.connect(DATABASE_URL)

# Base URLs for source PDFs
PART_3_PDF = "apartment-design-guide-part-3-siting-the-development.pdf"
PART_3_URL = "https://www.planning.nsw.gov.au/sites/default/files/2023-03/apartment-design-guide-part-3-siting-the-development.pdf"
PART_4_PDF = "apartment-design-guide-part-4-designing-the-building.pdf"
PART_4_URL = "https://www.planning.nsw.gov.au/sites/default/files/2023-03/apartment-design-guide-part-4-designing-the-building.pdf"

ADG_REQUIREMENTS = [
    # ===========================================
    # PART 3: SITING THE DEVELOPMENT
    # ===========================================

    # Section 3D: Communal and Public Open Space
    {
        "section_code": "3D",
        "section_name": "Communal and Public Open Space",
        "criteria_number": 1,
        "criteria_id": "3D-1",
        "requirement_type": "design_criteria",
        "requirement_text": "Communal open space has a minimum area equal to 25% of the site.",
        "requirement_summary": "Communal open space: min 25% of site area",
        "has_numeric_standard": True,
        "numeric_value": 25,
        "numeric_unit": "percent",
        "numeric_comparator": "min",
        "secondary_value": None,
        "secondary_unit": None,
        "metric_category": "communal_open_space_min",
        "applies_to": ["site", "communal_areas"],
        "building_height_category": "all",
        "source_pdf": PART_3_PDF,
        "source_page": 54,
        "source_url": PART_3_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },
    {
        "section_code": "3D",
        "section_name": "Communal and Public Open Space",
        "criteria_number": 2,
        "criteria_id": "3D-2",
        "requirement_type": "design_criteria",
        "requirement_text": "Communal open space has a minimum dimension of 6m.",
        "requirement_summary": "Communal open space: min 6m dimension",
        "has_numeric_standard": True,
        "numeric_value": 6,
        "numeric_unit": "metres",
        "numeric_comparator": "min",
        "secondary_value": None,
        "secondary_unit": None,
        "metric_category": "communal_open_space_min",
        "applies_to": ["site", "communal_areas"],
        "building_height_category": "all",
        "source_pdf": PART_3_PDF,
        "source_page": 54,
        "source_url": PART_3_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # Section 3E: Deep Soil Zones
    {
        "section_code": "3E",
        "section_name": "Deep Soil Zones",
        "criteria_number": 1,
        "criteria_id": "3E-1",
        "requirement_type": "design_criteria",
        "requirement_text": "Deep soil zones are to have a minimum area equivalent to 7% of the site area.",
        "requirement_summary": "Deep soil: min 7% of site area",
        "has_numeric_standard": True,
        "numeric_value": 7,
        "numeric_unit": "percent",
        "numeric_comparator": "min",
        "secondary_value": None,
        "secondary_unit": None,
        "metric_category": "deep_soil",
        "applies_to": ["site"],
        "building_height_category": "all",
        "source_pdf": PART_3_PDF,
        "source_page": 58,
        "source_url": PART_3_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },
    {
        "section_code": "3E",
        "section_name": "Deep Soil Zones",
        "criteria_number": 2,
        "criteria_id": "3E-2",
        "requirement_type": "design_criteria",
        "requirement_text": "Deep soil zones have a minimum dimension of 6m.",
        "requirement_summary": "Deep soil: min 6m dimension",
        "has_numeric_standard": True,
        "numeric_value": 6,
        "numeric_unit": "metres",
        "numeric_comparator": "min",
        "secondary_value": None,
        "secondary_unit": None,
        "metric_category": "deep_soil",
        "applies_to": ["site"],
        "building_height_category": "all",
        "source_pdf": PART_3_PDF,
        "source_page": 58,
        "source_url": PART_3_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # Section 3F: Visual Privacy (Building Separation) - TIER 1 ONLY
    # Note: Full 12-row separation matrix exists in setback_rules table
    {
        "section_code": "3F",
        "section_name": "Visual Privacy",
        "criteria_number": 1,
        "criteria_id": "3F-1",
        "requirement_type": "design_criteria",
        "requirement_text": "Separation between windows and balconies is provided to ensure visual privacy is achieved. Minimum building separations are: Up to 4 storeys (12m): 6m habitable/3m non-habitable; 5-8 storeys (25m): 9m habitable/4.5m non-habitable; Over 9 storeys (25m+): 12m habitable/6m non-habitable.",
        "requirement_summary": "Building separation: 6-12m based on height",
        "has_numeric_standard": True,
        "numeric_value": 6,
        "numeric_unit": "metres",
        "numeric_comparator": "min",
        "secondary_value": 12,
        "secondary_unit": "metres",
        "metric_category": "building_separation",
        "applies_to": ["buildings", "windows", "balconies"],
        "building_height_category": "all",
        "source_pdf": PART_3_PDF,
        "source_page": 63,
        "source_url": PART_3_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # ===========================================
    # PART 4: DESIGNING THE BUILDING
    # ===========================================

    # Section 4A: Solar and Daylight Access
    {
        "section_code": "4A",
        "section_name": "Solar and Daylight Access",
        "criteria_number": 1,
        "criteria_id": "4A-1",
        "requirement_type": "design_criteria",
        "requirement_text": "Living rooms and private open spaces of at least 70% of apartments in a building receive a minimum of 2 hours direct sunlight between 9am and 3pm at mid-winter in the Sydney Metropolitan Area and in the Newcastle and Wollongong local government areas.",
        "requirement_summary": "70% of apartments: min 2hrs sun midwinter",
        "has_numeric_standard": True,
        "numeric_value": 70,
        "numeric_unit": "percent",
        "numeric_comparator": "min",
        "secondary_value": 2,
        "secondary_unit": "hours",
        "metric_category": "solar_access",
        "applies_to": ["apartments", "living_rooms", "private_open_space"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 79,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },
    {
        "section_code": "4A",
        "section_name": "Solar and Daylight Access",
        "criteria_number": 2,
        "criteria_id": "4A-2",
        "requirement_type": "design_criteria",
        "requirement_text": "In all other areas, living rooms and private open spaces of at least 70% of apartments in a building receive a minimum of 3 hours direct sunlight between 9am and 3pm at mid-winter.",
        "requirement_summary": "70% of apartments: min 3hrs sun midwinter (regional)",
        "has_numeric_standard": True,
        "numeric_value": 70,
        "numeric_unit": "percent",
        "numeric_comparator": "min",
        "secondary_value": 3,
        "secondary_unit": "hours",
        "metric_category": "solar_access",
        "applies_to": ["apartments", "living_rooms", "private_open_space"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 79,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },
    {
        "section_code": "4A",
        "section_name": "Solar and Daylight Access",
        "criteria_number": 3,
        "criteria_id": "4A-3",
        "requirement_type": "design_criteria",
        "requirement_text": "A maximum of 15% of apartments in a building receive no direct sunlight between 9am and 3pm at mid-winter.",
        "requirement_summary": "Max 15% of apartments with no sun",
        "has_numeric_standard": True,
        "numeric_value": 15,
        "numeric_unit": "percent",
        "numeric_comparator": "max",
        "secondary_value": None,
        "secondary_unit": None,
        "metric_category": "solar_access",
        "applies_to": ["apartments"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 79,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # Section 4B: Natural Ventilation
    {
        "section_code": "4B",
        "section_name": "Natural Ventilation",
        "criteria_number": 1,
        "criteria_id": "4B-1",
        "requirement_type": "design_criteria",
        "requirement_text": "At least 60% of apartments are naturally cross ventilated in the first 9 storeys of the building. Apartments at 10 storeys or greater are deemed to be cross ventilated only if any enclosure of the balconies at these levels allows adequate natural ventilation and cannot be fully enclosed.",
        "requirement_summary": "60% of apartments cross-ventilated (first 9 storeys)",
        "has_numeric_standard": True,
        "numeric_value": 60,
        "numeric_unit": "percent",
        "numeric_comparator": "min",
        "secondary_value": 9,
        "secondary_unit": "storeys",
        "metric_category": "natural_ventilation",
        "applies_to": ["apartments"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 85,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },
    {
        "section_code": "4B",
        "section_name": "Natural Ventilation",
        "criteria_number": 2,
        "criteria_id": "4B-2",
        "requirement_type": "design_criteria",
        "requirement_text": "Overall depth of a cross-over or cross-through apartment does not exceed 18m, measured glass line to glass line.",
        "requirement_summary": "Cross-through apartment max depth: 18m",
        "has_numeric_standard": True,
        "numeric_value": 18,
        "numeric_unit": "metres",
        "numeric_comparator": "max",
        "secondary_value": None,
        "secondary_unit": None,
        "metric_category": "natural_ventilation",
        "applies_to": ["apartments"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 85,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # Section 4C: Ceiling Heights
    {
        "section_code": "4C",
        "section_name": "Ceiling Heights",
        "criteria_number": 1,
        "criteria_id": "4C-1",
        "requirement_type": "design_criteria",
        "requirement_text": "Measured from finished floor level to finished ceiling level, minimum ceiling heights are: Habitable rooms: 2.7m; Non-habitable rooms: 2.4m; For 2 storey apartments: 2.7m main living area, 2.4m second floor; Attic spaces: 1.8m at edge, 2.7m at centre.",
        "requirement_summary": "Ceiling height: 2.7m habitable, 2.4m non-habitable",
        "has_numeric_standard": True,
        "numeric_value": 2.7,
        "numeric_unit": "metres",
        "numeric_comparator": "min",
        "secondary_value": 2.4,
        "secondary_unit": "metres",
        "metric_category": "ceiling_heights",
        "applies_to": ["apartments", "habitable_rooms", "non_habitable_rooms"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 91,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # Section 4D: Apartment Size and Layout
    {
        "section_code": "4D",
        "section_name": "Apartment Size and Layout",
        "criteria_number": 1,
        "criteria_id": "4D-1",
        "requirement_type": "design_criteria",
        "requirement_text": "Apartments are required to have the following minimum internal areas: Studio: 35m²; 1 bedroom: 50m²; 2 bedroom: 70m²; 3 bedroom: 90m². The minimum internal area includes only one bathroom. Additional bathrooms increase the minimum internal area by 5m² each.",
        "requirement_summary": "Min areas: Studio 35m², 1BR 50m², 2BR 70m², 3BR 90m²",
        "has_numeric_standard": True,
        "numeric_value": 35,
        "numeric_unit": "sqm",
        "numeric_comparator": "min",
        "secondary_value": 90,
        "secondary_unit": "sqm",
        "metric_category": "apartment_size",
        "applies_to": ["apartments"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 95,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },
    {
        "section_code": "4D",
        "section_name": "Apartment Size and Layout",
        "criteria_number": 2,
        "criteria_id": "4D-2",
        "requirement_type": "design_criteria",
        "requirement_text": "Every habitable room must have a window in an external wall with a total minimum glass area of not less than 10% of the floor area of the room. Depth of a habitable room is limited to a maximum of 2.5 x the ceiling height. In open plan layouts (where the living, dining and kitchen are combined), the maximum habitable room depth is 8m from a window.",
        "requirement_summary": "Room depth: max 2.5x ceiling height, open plan max 8m",
        "has_numeric_standard": True,
        "numeric_value": 2.5,
        "numeric_unit": "ratio",
        "numeric_comparator": "max",
        "secondary_value": 8,
        "secondary_unit": "metres",
        "metric_category": "apartment_layout",
        "applies_to": ["habitable_rooms"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 97,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },
    {
        "section_code": "4D",
        "section_name": "Apartment Size and Layout",
        "criteria_number": 3,
        "criteria_id": "4D-3",
        "requirement_type": "design_criteria",
        "requirement_text": "Bedrooms have a minimum area of 10m² for the master bedroom and 9m² for all other bedrooms (excluding wardrobe space). Bedrooms have a minimum dimension of 3m (excluding wardrobe space).",
        "requirement_summary": "Bedrooms: master 10m², others 9m², min 3m dimension",
        "has_numeric_standard": True,
        "numeric_value": 10,
        "numeric_unit": "sqm",
        "numeric_comparator": "min",
        "secondary_value": 9,
        "secondary_unit": "sqm",
        "metric_category": "bedroom_size",
        "applies_to": ["bedrooms"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 99,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },
    {
        "section_code": "4D",
        "section_name": "Apartment Size and Layout",
        "criteria_number": 4,
        "criteria_id": "4D-4",
        "requirement_type": "design_criteria",
        "requirement_text": "Living rooms or combined living/dining rooms have a minimum width of: Studio and 1 bedroom: 3.6m; 2 bedroom: 4m; 3+ bedroom: 4m.",
        "requirement_summary": "Living room width: Studio/1BR 3.6m, 2BR+ 4m",
        "has_numeric_standard": True,
        "numeric_value": 3.6,
        "numeric_unit": "metres",
        "numeric_comparator": "min",
        "secondary_value": 4,
        "secondary_unit": "metres",
        "metric_category": "apartment_layout",
        "applies_to": ["living_rooms"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 99,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # Section 4E: Private Open Space and Balconies
    {
        "section_code": "4E",
        "section_name": "Private Open Space and Balconies",
        "criteria_number": 1,
        "criteria_id": "4E-1",
        "requirement_type": "design_criteria",
        "requirement_text": "All apartments are required to have primary balconies as follows: Studio apartments: 4m² (no minimum dimension); 1 bedroom apartments: 8m² with minimum depth of 2m; 2 bedroom apartments: 10m² with minimum depth of 2m; 3+ bedroom apartments: 12m² with minimum depth of 2.4m.",
        "requirement_summary": "Balconies: Studio 4m², 1BR 8m²@2m, 2BR 10m²@2m, 3BR+ 12m²@2.4m",
        "has_numeric_standard": True,
        "numeric_value": 4,
        "numeric_unit": "sqm",
        "numeric_comparator": "min",
        "secondary_value": 12,
        "secondary_unit": "sqm",
        "metric_category": "private_open_space",
        "applies_to": ["apartments", "balconies"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 103,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },
    {
        "section_code": "4E",
        "section_name": "Private Open Space and Balconies",
        "criteria_number": 2,
        "criteria_id": "4E-2",
        "requirement_type": "design_criteria",
        "requirement_text": "For apartments at ground level or on a podium or similar structure, a private open space is provided instead of a balcony. It must have a minimum area of 15m² and minimum depth of 3m.",
        "requirement_summary": "Ground floor private open space: min 15m² @ 3m depth",
        "has_numeric_standard": True,
        "numeric_value": 15,
        "numeric_unit": "sqm",
        "numeric_comparator": "min",
        "secondary_value": 3,
        "secondary_unit": "metres",
        "metric_category": "private_open_space",
        "applies_to": ["ground_floor_apartments"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 103,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # Section 4F: Common Circulation and Spaces
    {
        "section_code": "4F",
        "section_name": "Common Circulation and Spaces",
        "criteria_number": 1,
        "criteria_id": "4F-1",
        "requirement_type": "design_criteria",
        "requirement_text": "The maximum number of apartments off a circulation core on a single level is 8.",
        "requirement_summary": "Max 8 apartments per circulation core per level",
        "has_numeric_standard": True,
        "numeric_value": 8,
        "numeric_unit": "units",
        "numeric_comparator": "max",
        "secondary_value": None,
        "secondary_unit": None,
        "metric_category": "common_circulation",
        "applies_to": ["circulation", "corridors"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 109,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },
    {
        "section_code": "4F",
        "section_name": "Common Circulation and Spaces",
        "criteria_number": 2,
        "criteria_id": "4F-2",
        "requirement_type": "design_criteria",
        "requirement_text": "For buildings of 10 storeys and over, the maximum number of apartments sharing a single lift is 40.",
        "requirement_summary": "Max 40 apartments per lift (10+ storeys)",
        "has_numeric_standard": True,
        "numeric_value": 40,
        "numeric_unit": "units",
        "numeric_comparator": "max",
        "secondary_value": 10,
        "secondary_unit": "storeys",
        "metric_category": "common_circulation",
        "applies_to": ["lifts", "circulation"],
        "building_height_category": "over_25m",
        "source_pdf": PART_4_PDF,
        "source_page": 109,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # Section 4G: Storage
    {
        "section_code": "4G",
        "section_name": "Storage",
        "criteria_number": 1,
        "criteria_id": "4G-1",
        "requirement_type": "design_criteria",
        "requirement_text": "In addition to storage in kitchens, bathrooms and bedrooms, the following storage is provided: Studio: 4m³; 1 bedroom: 6m³; 2 bedroom: 8m³; 3+ bedroom: 10m³. At least 50% of the required storage is to be located within the apartment.",
        "requirement_summary": "Storage: Studio 4m³, 1BR 6m³, 2BR 8m³, 3BR+ 10m³",
        "has_numeric_standard": True,
        "numeric_value": 4,
        "numeric_unit": "cubic_m",
        "numeric_comparator": "min",
        "secondary_value": 10,
        "secondary_unit": "cubic_m",
        "metric_category": "storage",
        "applies_to": ["apartments"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 115,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # Section 4J: Noise and Pollution
    {
        "section_code": "4J",
        "section_name": "Noise and Pollution",
        "criteria_number": 1,
        "criteria_id": "4J-1",
        "requirement_type": "design_criteria",
        "requirement_text": "In noisy or hostile environments where the noise levels exceed 60dB(A) at any time, habitable rooms should have mechanical ventilation or air conditioning to allow windows to be closed.",
        "requirement_summary": "Mechanical ventilation if noise >60dB(A)",
        "has_numeric_standard": True,
        "numeric_value": 60,
        "numeric_unit": "dBA",
        "numeric_comparator": "threshold",
        "secondary_value": None,
        "secondary_unit": None,
        "metric_category": "noise_pollution",
        "applies_to": ["apartments", "habitable_rooms"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 127,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # Section 4K: Apartment Mix
    {
        "section_code": "4K",
        "section_name": "Apartment Mix",
        "criteria_number": 1,
        "criteria_id": "4K-1",
        "requirement_type": "design_criteria",
        "requirement_text": "A range of apartment types and sizes is provided to cater for different household types now and into the future.",
        "requirement_summary": "Provide range of apartment types and sizes",
        "has_numeric_standard": False,
        "numeric_value": None,
        "numeric_unit": None,
        "numeric_comparator": None,
        "secondary_value": None,
        "secondary_unit": None,
        "metric_category": "apartment_mix",
        "applies_to": ["development"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 131,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },

    # Section 4U: Energy Efficiency
    {
        "section_code": "4U",
        "section_name": "Energy Efficiency",
        "criteria_number": 1,
        "criteria_id": "4U-1",
        "requirement_type": "design_criteria",
        "requirement_text": "Development applications for BASIX affected development demonstrate that each apartment achieves a maximum cooling load of: Single storey apartment - 35MJ/m²; Apartment with 2 or more storeys - 45MJ/m².",
        "requirement_summary": "Max cooling load: 35MJ/m² single storey, 45MJ/m² multi",
        "has_numeric_standard": True,
        "numeric_value": 35,
        "numeric_unit": "MJ_per_sqm",
        "numeric_comparator": "max",
        "secondary_value": 45,
        "secondary_unit": "MJ_per_sqm",
        "metric_category": "energy_efficiency",
        "applies_to": ["apartments"],
        "building_height_category": "all",
        "source_pdf": PART_4_PDF,
        "source_page": 143,
        "source_url": PART_4_URL,
        "authority_reference": "SEPP (Housing) 2021"
    },
]


def insert_requirements():
    """Insert all ADG requirements into the database."""
    print(f"Inserting {len(ADG_REQUIREMENTS)} ADG Design Criteria...")

    inserted = 0
    skipped = 0
    errors = 0

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    for req in ADG_REQUIREMENTS:
        try:
            # Check if already exists
            cur.execute("SELECT id FROM sepp_adg_requirements WHERE criteria_id = %s", (req['criteria_id'],))
            existing = cur.fetchone()

            if existing:
                print(f"  Skipping {req['criteria_id']} - already exists")
                skipped += 1
                continue

            # Insert the requirement
            cur.execute("""
                INSERT INTO sepp_adg_requirements (
                    section_code, section_name, criteria_number, criteria_id,
                    requirement_type, requirement_text, requirement_summary,
                    has_numeric_standard, numeric_value, numeric_unit, numeric_comparator,
                    secondary_value, secondary_unit, metric_category,
                    applies_to, building_height_category,
                    source_pdf, source_page, source_url, authority_reference
                ) VALUES (
                    %(section_code)s, %(section_name)s, %(criteria_number)s, %(criteria_id)s,
                    %(requirement_type)s, %(requirement_text)s, %(requirement_summary)s,
                    %(has_numeric_standard)s, %(numeric_value)s, %(numeric_unit)s, %(numeric_comparator)s,
                    %(secondary_value)s, %(secondary_unit)s, %(metric_category)s,
                    %(applies_to)s, %(building_height_category)s,
                    %(source_pdf)s, %(source_page)s, %(source_url)s, %(authority_reference)s
                )
            """, req)

            print(f"  [OK] Inserted {req['criteria_id']}: {req['requirement_summary']}")
            inserted += 1

        except Exception as e:
            print(f"  [ERR] Error inserting {req['criteria_id']}: {e}")
            errors += 1
            conn.rollback()

    conn.commit()
    cur.close()
    conn.close()

    print(f"\n{'='*60}")
    print(f"Summary:")
    print(f"  Inserted: {inserted}")
    print(f"  Skipped (existing): {skipped}")
    print(f"  Errors: {errors}")
    print(f"  Total: {len(ADG_REQUIREMENTS)}")

    return inserted, skipped, errors


def verify_insertion():
    """Verify the inserted data."""
    print("\nVerifying inserted data...")

    conn = get_connection()
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Count by section
    cur.execute("SELECT section_code FROM sepp_adg_requirements")
    rows = cur.fetchall()

    if rows:
        section_counts = {}
        for row in rows:
            section = row['section_code']
            section_counts[section] = section_counts.get(section, 0) + 1

        print("\nCounts by section:")
        for section in sorted(section_counts.keys()):
            print(f"  {section}: {section_counts[section]} criteria")

        print(f"\nTotal records: {len(rows)}")

    # Count numeric vs non-numeric
    cur.execute("SELECT COUNT(*) as cnt FROM sepp_adg_requirements WHERE has_numeric_standard = true")
    numeric_count = cur.fetchone()['cnt']
    print(f"  With numeric standards: {numeric_count}")

    cur.execute("SELECT COUNT(*) as cnt FROM sepp_adg_requirements WHERE has_numeric_standard = false")
    non_numeric_count = cur.fetchone()['cnt']
    print(f"  Without numeric standards: {non_numeric_count}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    print("=" * 60)
    print("NSW Apartment Design Guide - Design Criteria Insertion")
    print("=" * 60)
    print(f"Source: ADG March 2023 (Parts 3 & 4)")
    print(f"Authority: SEPP (Housing) 2021")
    print("=" * 60)

    inserted, skipped, errors = insert_requirements()

    if errors == 0:
        verify_insertion()
        print("\n[OK] ADG requirements successfully inserted!")
    else:
        print(f"\n[WARN] Completed with {errors} errors")
