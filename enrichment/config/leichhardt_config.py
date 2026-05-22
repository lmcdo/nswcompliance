"""
Leichhardt DCP 2013 Configuration

Structure:
- Part A: Introduction - administrative, applies to ALL
- Part B: (Not heavily populated in database)
- Part C Section 1: Place - general built form controls, applies to ALL
- Part C Section 2: Distinctive Neighbourhoods - PRECINCT SPECIFIC
- Part D: Energy - sustainability, applies to ALL dev types
- Part E: Water - water management, applies to ALL dev types
- Part F: Food - FOOD PREMISES ONLY
- Part G: Neighbourhoods - PRECINCT SPECIFIC

Document_id patterns in database:
- "Leichhardt DCP 2013 - X - Part Y..."
- "Leichhardt_DCP_2013_Part_C_Section_2_C2_2_X_X_Neighbourhood_Name"
"""

# Inner West LEP 2022 zone codes (Leichhardt area)
# Only zones that actually exist in the former Leichhardt LGA boundaries.
# Generic NSW constants (R4-R5, B3-B8, IN3-IN4, E1/E3/E4) removed.
RESIDENTIAL_ZONES = ['R1', 'R2', 'R3']
BUSINESS_ZONES = ['B1', 'B2', 'B4']
INDUSTRIAL_ZONES = ['IN1', 'IN2']
SPECIAL_ZONES = ['SP1', 'SP2']
RECREATION_ZONES = ['RE1', 'RE2']
ENVIRONMENT_ZONES = ['E2']
MIXED_USE_ZONES = ['MU1']

ALL_ZONES = ['ALL']
ALL_DEV_TYPES = ['ALL']

LEICHHARDT_CONFIG = {
    "council": "leichhardt",
    "dcp_name": "Leichhardt DCP 2013",

    # Document patterns mapped to applicability
    "parts": {
        # Part A - Introduction: General administrative provisions
        "Part A": {
            "description": "Introduction - Administrative and procedural matters",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Part B - (sparse in database, appears to be intro/definitions)
        "Part B": {
            "description": "General Provisions",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Part C Section 1 - Place: General built form and character controls
        # These apply to ALL development, setting baseline standards
        "Part C Section 1": {
            "description": "Place - General built form and streetscape controls",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Part C Section 2 - Distinctive Neighbourhoods: Precinct-specific
        # Each neighbourhood has specific character requirements
        # Filtering done by precinct boundary matching
        "Part C Section 2": {
            "description": "Distinctive Neighbourhoods - Area-specific controls",
            "applicable_zones": ALL_ZONES,  # Zone filtering by precinct matching
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
            "is_precinct_specific": True,
        },

        # Part D - Energy: Sustainability and energy efficiency
        # Applies to all development types
        "Part D": {
            "description": "Energy - Energy efficiency and sustainability",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Part E - Water: Water management and WSUD
        # Applies to all development types
        "Part E": {
            "description": "Water - Water sensitive urban design",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Part F - Food: Food premises specific controls
        # Only applies to food-related development
        "Part F": {
            "description": "Food - Food premises requirements",
            "applicable_zones": BUSINESS_ZONES + INDUSTRIAL_ZONES,
            "applicable_dev_types": ["food_and_drink_premises", "restaurant", "cafe", "take_away_food"],
            "site_conditions": None,
        },

        # Part G - Neighbourhoods: Area-specific controls
        # Precinct-specific requirements
        "Part G": {
            "description": "Neighbourhoods - Precinct-specific controls",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
            "is_precinct_specific": True,
        },
    },

    # Distinctive Neighbourhood patterns (from Part C Section 2)
    # These are precinct-specific and inherit from the precinct system
    "neighbourhoods": {
        # Annandale area (C2.2.1.x)
        "Young_Street": {"precinct_name": "Young Street", "suburb": "Annandale"},
        "Annandale_Street": {"precinct_name": "Annandale Street", "suburb": "Annandale"},
        "Johnston_Street": {"precinct_name": "Johnston Street", "suburb": "Annandale"},
        "Trafalgar_Street": {"precinct_name": "Trafalgar Street", "suburb": "Annandale"},
        "Nelson_Street": {"precinct_name": "Nelson Street", "suburb": "Annandale"},
        "Camperdown": {"precinct_name": "Camperdown", "suburb": "Camperdown"},

        # Balmain area (C2.2.2.x)
        "Darling_Street": {"precinct_name": "Darling Street", "suburb": "Balmain"},
        "Gladstone_Park": {"precinct_name": "Gladstone Park", "suburb": "Balmain"},

        # Leichhardt area (C2.2.3.x)
        "Excelsior_Estate": {"precinct_name": "Excelsior Estate", "suburb": "Leichhardt"},
        "West_Leichhardt": {"precinct_name": "West Leichhardt", "suburb": "Leichhardt"},
        "Piperston": {"precinct_name": "Piperston", "suburb": "Leichhardt"},
        "Helsarmel": {"precinct_name": "Helsarmel", "suburb": "Leichhardt"},
        "Leichhardt_Commercial": {"precinct_name": "Leichhardt Commercial", "suburb": "Leichhardt"},

        # Lilyfield area (C2.2.4.x)
        "Catherine_Street": {"precinct_name": "Catherine Street", "suburb": "Lilyfield"},
        "Nanny_Goat_Hill": {"precinct_name": "Nanny Goat Hill", "suburb": "Lilyfield"},
        "Leichhardt_Park": {"precinct_name": "Leichhardt Park", "suburb": "Lilyfield"},
        "Iron_Cove_Parklands": {"precinct_name": "Iron Cove Parklands", "suburb": "Lilyfield"},

        # Rozelle area (C2.2.5.x)
        "The_Valley": {"precinct_name": "The Valley", "suburb": "Rozelle"},
        "Easton_Park": {"precinct_name": "Easton Park", "suburb": "Rozelle"},
        "Callan_Park": {"precinct_name": "Callan Park", "suburb": "Rozelle"},
        "Iron_Cove": {"precinct_name": "Iron Cove", "suburb": "Rozelle"},
        "Rozelle_Commercial": {"precinct_name": "Rozelle Commercial", "suburb": "Rozelle"},
        "Robert_Street_Industrial": {"precinct_name": "Robert Street Industrial", "suburb": "Rozelle"},
    },
}
