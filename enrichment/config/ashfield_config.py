"""
Ashfield DCP 2016 Configuration

Structure:
- Chapter A: Miscellaneous - administrative, applies to ALL
- Chapter B: Public Domain - public works, applies to ALL
- Chapter C: Sustainability - environmental controls, applies to ALL dev types
- Chapter D: Precinct Guidelines - PRECINCT SPECIFIC (filtered by precinct matching)
- Chapter E1: Heritage - HERITAGE SITES ONLY (filtered by site condition)
- Chapter F: Development Categories - DEV TYPE SPECIFIC

The document_id patterns in database:
- "Inner West Ashfield DCP 2016 - Chapter X..."
- "Ashfield_DCP_2016_Chapter_F_Part_X"
- "Inner_West_Ashfield_DCP_2016___Chapter_D..."
"""

# Inner West LEP 2022 zone codes (Ashfield area), current as of the 26 April
# 2023 NSW Employment Zones Reform (DQ-30, .claude/DATA_QUALITY_TRACKER.md).
# Confirmed against lep_zone_coverage: Inner West has ZERO B-zones and ZERO
# IN-zones today — the constants below previously hardcoded the retired
# codes (B1/B2/B4, IN1/IN2), which stopped matching any real property after
# the reform. Values here are each legacy code's real current equivalent
# (see enrichment/config/zone_taxonomy.py): B1,B2->E1; B4->MU1; IN1,IN2->E4.
# Only zones that actually exist in the former Ashfield LGA boundaries.
# Generic NSW constants (R5, B5-B8, IN3-IN4, E2/E3/E5) removed — they
# produced false-positive tags on provisions that can never apply.
RESIDENTIAL_ZONES = ['R1', 'R2', 'R3', 'R4']
BUSINESS_ZONES = ['E1', 'MU1']
INDUSTRIAL_ZONES = ['E4']
SPECIAL_ZONES = ['SP1', 'SP2']
RECREATION_ZONES = ['RE1', 'RE2']
MIXED_USE_ZONES = ['MU1']

ALL_ZONES = ['ALL']
ALL_DEV_TYPES = ['ALL']

ASHFIELD_CONFIG = {
    "council": "ashfield",
    "dcp_name": "Ashfield DCP 2016",

    # Document patterns mapped to applicability
    "chapters": {
        # Chapter A - Miscellaneous: General administrative provisions
        # Applies to all zones and all development types
        "Chapter A": {
            "description": "Miscellaneous - General administrative controls",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Chapter B - Public Domain: Public works requirements
        # Applies to all zones, primarily for development affecting public areas
        "Chapter B": {
            "description": "Public Domain - Requirements for public domain works",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Chapter C - Sustainability: Environmental and sustainability controls
        # Applies to all development across all zones
        "Chapter C": {
            "description": "Sustainability - Environmental and sustainability controls",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Chapter D - Precinct Guidelines: Area-specific controls
        # These provisions apply to specific precincts only
        # Filtering is done by precinct boundary matching, not zone
        "Chapter D": {
            "description": "Precinct Guidelines - Area-specific controls",
            "applicable_zones": ALL_ZONES,  # Zone filtering handled by precinct matching
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
            "is_precinct_specific": True,  # Flag for special handling
        },

        # Chapter E1 - Heritage: Heritage conservation controls
        # Only applies to properties identified as heritage items or in heritage areas
        "Chapter E1": {
            "description": "Heritage - Conservation area and heritage item controls",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": ["heritage"],  # Only show if property has heritage listing
        },

        # Chapter F - Development Categories: Dev type specific controls
        # Note: In database, these appear as "Ashfield_DCP_2016_Chapter_F_Part_X"
        # F1: Dwelling Houses, F2: Dual Occupancy, F3: Multi Dwelling, etc.
        "Chapter F": {
            "description": "Development Categories - Type-specific controls",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,  # Default, override by part below
            "site_conditions": None,
        },
    },

    # More specific patterns for Chapter F parts (dev type specific)
    "chapter_f_parts": {
        "Part_1": {
            "description": "F1 - Dwelling Houses",
            "applicable_dev_types": ["dwelling_house", "secondary_dwelling"],
            "applicable_zones": RESIDENTIAL_ZONES,
        },
        "Part_2": {
            "description": "F2 - Dual Occupancy",
            "applicable_dev_types": ["dual_occupancy"],
            "applicable_zones": ['R2', 'R3', 'R4'],
        },
        "Part_3": {
            "description": "F3 - Multi Dwelling Housing",
            "applicable_dev_types": ["multi_dwelling_housing", "attached_dwelling"],
            "applicable_zones": ['R3', 'R4'],
        },
        "Part_4": {
            "description": "F4 - Residential Flat Buildings",
            "applicable_dev_types": ["residential_flat_building", "shop_top_housing"],
            "applicable_zones": ['R3', 'R4', 'E1', 'MU1'],
        },
        "Part_5": {
            "description": "F5 - Boarding Houses",
            "applicable_dev_types": ["boarding_house"],
            "applicable_zones": RESIDENTIAL_ZONES + BUSINESS_ZONES,
        },
        "Part_6": {
            "description": "F6 - Commercial Development",
            "applicable_dev_types": ["commercial_premises", "retail_premises", "office_premises"],
            "applicable_zones": BUSINESS_ZONES,
        },
        "Part_7": {
            "description": "F7 - Industrial Development",
            "applicable_dev_types": ["industrial_development", "warehouse", "light_industry"],
            "applicable_zones": INDUSTRIAL_ZONES,
        },
        "Part_8": {
            "description": "F8 - Child Care Centres",
            "applicable_dev_types": ["child_care_centre", "centre_based_childcare"],
            "applicable_zones": ALL_ZONES,
        },
        "Part_9": {
            "description": "F9 - Sex Services Premises",
            "applicable_dev_types": ["sex_services_premises"],
            "applicable_zones": ['E4', 'MU1'],
        },
        "Part_10": {
            "description": "F10 - Other Development",
            "applicable_dev_types": ALL_DEV_TYPES,
            "applicable_zones": ALL_ZONES,
        },
    },
}
