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

# Inner West LEP 2022 zone codes (Leichhardt area), current as of the 26
# April 2023 NSW Employment Zones Reform (DQ-30,
# .claude/DATA_QUALITY_TRACKER.md). Confirmed against lep_zone_coverage:
# Inner West has ZERO B-zones and ZERO IN-zones today — the constants below
# previously hardcoded the retired codes (B1/B2/B4, IN1/IN2), which stopped
# matching any real property after the reform. Values here are each legacy
# code's real current equivalent (see enrichment/config/zone_taxonomy.py):
# B1,B2->E1; B4->MU1; IN1,IN2->E4.
# Only zones that actually exist in the former Leichhardt LGA boundaries.
# Generic NSW constants (R4-R5, B3/B5-B8, IN3-IN4, E2/E3/E5) removed.
RESIDENTIAL_ZONES = ['R1', 'R2', 'R3']
BUSINESS_ZONES = ['E1', 'MU1']
INDUSTRIAL_ZONES = ['E4']
SPECIAL_ZONES = ['SP1', 'SP2']
RECREATION_ZONES = ['RE1', 'RE2']
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

        # ── Added 2026-09-21: nine ingested documents had NO config entry ──────
        # Measured on live regulatory_provisions: 871 served leichhardt rows carried
        # v2_dev_type_source='no_config', meaning nothing matched and they fell
        # through to ALL development types. Not a bug -- the config was written for
        # the documents that existed when it was written, and the corpus grew past
        # it. Nothing checks that an ingested document resolves to a config key, so
        # the gap was invisible: the fallthrough is SAFE (shows everything) rather
        # than broken, and only DQ-33 counts it.
        #
        # Each scope below is read from the document's own provisions, not its
        # title. Where title and content did not agree unambiguously the entry says
        # ALL, because narrowing hides controls and a hidden binding control is the
        # liability -- the same direction of risk retag_applicability_slug_docids
        # states. config_all is an honest state and is NOT no_config: it means the
        # config says all, rather than nothing matched.

        # C3 provisions are residential built form: "C3.2 Building envelope",
        # "C3.6 Visual engagement with the public realm - Retaining walls".
        "Part C Section 3": {
            "description": "Residential development - built form and amenity",
            "applicable_zones": RESIDENTIAL_ZONES + MIXED_USE_ZONES,
            "applicable_dev_types": [
                "dwelling_house", "dual_occupancy", "attached_dwelling",
                "multi_dwelling_housing", "residential_flat_building",
                "secondary_dwelling", "boarding_house", "shop_top_housing",
            ],
            "site_conditions": None,
        },

        # C4 is unambiguously non-residential: "C4.19 Objectives for vehicle repair
        # stations", "C4.10 Parking compliance for industrial development",
        # "C4.15 Location of facilities with potential adverse amenity impacts".
        "Part C Section 4": {
            "description": "Non-residential development - commercial and industrial",
            "applicable_zones": BUSINESS_ZONES + INDUSTRIAL_ZONES + MIXED_USE_ZONES,
            "applicable_dev_types": [
                "commercial_premises", "retail_premises", "office_premises",
                "industrial_development", "light_industry", "heavy_industry",
                "warehouse", "food_and_drink_premises", "mixed_use",
            ],
            "site_conditions": None,
        },

        # Entertainment precincts. NOT narrowed: its controls are noise impacts
        # ("C5.3 Noise impact from other sources, such as road and rail"), which
        # bind neighbouring development as much as the venue itself.
        "Part C Section 5": {
            "description": "Entertainment precincts - amenity and noise",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Terrace typologies -- but its section headers span C4 and C6, so the
        # appendix is referenced from more than one Part. ALL rather than guess.
        "Appendix B": {
            "description": "Building typologies - referenced from multiple Parts",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Waste collection vehicle access and turning circles: any development
        # that generates waste, which is all of it.
        "Appendix D": {
            "description": "Waste management template - collection access",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Flood and water: "1% AEP Flood Event Extent", "Precautions to Minimise
        # Flood Risk". Site condition, not development type.
        "Appendix E": {
            "description": "Water and flood guidelines",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Arboricultural reports and pruning limits apply to any DA affecting a
        # tree, regardless of what is being built.
        "Tree Management Technical Manual": {
            "description": "Tree management - arboricultural reports and pruning",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # A precinct amendment covering building design and water management for
        # George and Upward Streets. Precinct-scoped, not development-scoped.
        "Amendment 1": {
            "description": "George and Upward Streets precinct amendment",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
            "is_precinct_specific": True,
        },

        # Licensed premises: extended trading hours, venue parking rates.
        "Amendment 7": {
            "description": "Licensed premises - trading hours and parking",
            "applicable_zones": BUSINESS_ZONES + MIXED_USE_ZONES,
            "applicable_dev_types": [
                "food_and_drink_premises", "restaurant", "cafe",
                "take_away_food", "commercial_premises",
            ],
            "site_conditions": None,
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
