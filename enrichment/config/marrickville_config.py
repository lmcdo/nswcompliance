"""
Marrickville DCP 2011 Configuration

Structure:
- Part 1: Statutory Information - administrative, applies to ALL
- Part 2.x: General Controls - applies to ALL (parking, fencing, landscaping, etc.)
- Part 3: Subdivision - applies to ALL
- Part 4.1: Low Density Residential - R2 zones, dwelling houses
- Part 4.2: Multi Dwelling Housing & RFBs - R3+ zones, multi dwelling
- Part 4.3: Boarding Houses - boarding house dev type
- Part 5: Commercial & Mixed Use - B zones
- Part 6: Industrial Development - IN zones
- Part 7.1: Childcare Centres - childcare dev type
- Part 7.3: Sex Industry - sex services dev type
- Part 8: Heritage - HERITAGE SITES ONLY
- Part 9.x: Precincts (48 precincts) - PRECINCT SPECIFIC

Document_id patterns in database:
- "Marrickville_DCP_2011_-_X.X_Name" (single underscore)
- "Marrickville__DCP__2011__-__X__X__Name" (double underscore variant)
"""

# Inner West LEP 2022 zone codes (Marrickville area)
# Only zones that actually exist in the former Marrickville LGA boundaries.
# Generic NSW constants (R5, B5-B8, IN3-IN4, E1/E3/E4) removed.
RESIDENTIAL_ZONES = ['R1', 'R2', 'R3', 'R4']
BUSINESS_ZONES = ['B1', 'B2', 'B4']
INDUSTRIAL_ZONES = ['IN1', 'IN2']
SPECIAL_ZONES = ['SP1', 'SP2']
RECREATION_ZONES = ['RE1', 'RE2']
ENVIRONMENT_ZONES = ['E2']
MIXED_USE_ZONES = ['MU1']

ALL_ZONES = ['ALL']
ALL_DEV_TYPES = ['ALL']

MARRICKVILLE_CONFIG = {
    "council": "marrickville",
    "dcp_name": "Marrickville DCP 2011",

    # Document patterns mapped to applicability
    "parts": {
        # Part 1 - Statutory Information
        "1": {
            "description": "Statutory Information - Administrative matters",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Part 2.x - General Controls (various sub-sections)
        "2_1": {
            "description": "Urban Design",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_3": {
            "description": "Site Context Analysis",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_5": {
            "description": "Equity of Access and Mobility",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_6": {
            "description": "Acoustic and Visual Privacy",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_7": {
            "description": "Solar Access and Overshadowing",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_8": {
            "description": "Social Impact Assessment",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_9": {
            "description": "Community Safety",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_10": {
            "description": "Parking",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_11": {
            "description": "Fencing",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_12": {
            "description": "Signs and Advertising Structures",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ["signage", "advertising_structure"] + ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_13": {
            "description": "Biodiversity",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_14": {
            "description": "Unique Environmental Features",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_16": {
            "description": "Energy Efficiency",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_17": {
            "description": "Water Sensitive Urban Design",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_18": {
            "description": "Landscaping and Open Spaces",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },
        "2_25": {
            "description": "Stormwater Management",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
        },

        # Part 3 - Subdivision
        "3": {
            "description": "Subdivision, Amalgamation, Movement Network",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ["subdivision"],
            "site_conditions": None,
        },

        # Part 4.1 - Low Density Residential
        "4.1": {
            "description": "Low Density Residential Development",
            "applicable_zones": ['R2'],
            "applicable_dev_types": ["dwelling_house", "secondary_dwelling", "dual_occupancy"],
            "site_conditions": None,
        },
        "4_1": {
            "description": "Low Density Residential Development",
            "applicable_zones": ['R2'],
            "applicable_dev_types": ["dwelling_house", "secondary_dwelling", "dual_occupancy"],
            "site_conditions": None,
        },

        # Part 4.2 - Multi Dwelling Housing and RFBs
        "4.2": {
            "description": "Multi Dwelling Housing and Residential Flat Buildings",
            "applicable_zones": ['R3', 'R4'],
            "applicable_dev_types": ["multi_dwelling_housing", "residential_flat_building", "attached_dwelling"],
            "site_conditions": None,
        },
        "4_2": {
            "description": "Multi Dwelling Housing and Residential Flat Buildings",
            "applicable_zones": ['R3', 'R4'],
            "applicable_dev_types": ["multi_dwelling_housing", "residential_flat_building", "attached_dwelling"],
            "site_conditions": None,
        },

        # Part 4.3 - Boarding Houses
        "4.3": {
            "description": "Boarding Houses",
            "applicable_zones": RESIDENTIAL_ZONES + BUSINESS_ZONES,
            "applicable_dev_types": ["boarding_house"],
            "site_conditions": None,
        },
        "4_3": {
            "description": "Boarding Houses",
            "applicable_zones": RESIDENTIAL_ZONES + BUSINESS_ZONES,
            "applicable_dev_types": ["boarding_house"],
            "site_conditions": None,
        },

        # Part 5 - Commercial and Mixed Use
        "5": {
            "description": "Commercial and Mixed Use Development",
            "applicable_zones": BUSINESS_ZONES + MIXED_USE_ZONES,
            "applicable_dev_types": ["commercial_premises", "retail_premises", "office_premises", "shop_top_housing", "mixed_use"],
            "site_conditions": None,
        },
        "5_0": {
            "description": "Commercial and Mixed Use Development",
            "applicable_zones": BUSINESS_ZONES + MIXED_USE_ZONES,
            "applicable_dev_types": ["commercial_premises", "retail_premises", "office_premises", "shop_top_housing", "mixed_use"],
            "site_conditions": None,
        },

        # Part 6 - Industrial Development
        "6": {
            "description": "Industrial Development",
            "applicable_zones": INDUSTRIAL_ZONES,
            "applicable_dev_types": ["industrial_development", "warehouse", "light_industry", "heavy_industry"],
            "site_conditions": None,
        },
        "6_0": {
            "description": "Industrial Development",
            "applicable_zones": INDUSTRIAL_ZONES,
            "applicable_dev_types": ["industrial_development", "warehouse", "light_industry", "heavy_industry"],
            "site_conditions": None,
        },

        # Part 7.1 - Childcare Centres
        "7.1": {
            "description": "Childcare Centres",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ["child_care_centre", "centre_based_childcare"],
            "site_conditions": None,
        },
        "7_1": {
            "description": "Childcare Centres",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ["child_care_centre", "centre_based_childcare"],
            "site_conditions": None,
        },

        # Part 7.3 - Sex Industry
        "7.3": {
            "description": "Sex Industry and Adult Business Premises",
            "applicable_zones": ['B4', 'IN1', 'IN2'],
            "applicable_dev_types": ["sex_services_premises", "restricted_premises"],
            "site_conditions": None,
        },

        # Part 8 - Heritage
        "8": {
            "description": "Heritage",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": ["heritage"],  # Only show if property has heritage listing
        },
        "8.0": {
            "description": "Heritage",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": ["heritage"],
        },

        # Part 9 - Precincts (general intro)
        "9_0": {
            "description": "Precincts - Introduction",
            "applicable_zones": ALL_ZONES,
            "applicable_dev_types": ALL_DEV_TYPES,
            "site_conditions": None,
            "is_precinct_specific": True,
        },
    },

    # Precinct mapping (Part 9.x)
    # Each precinct has its own specific requirements
    "precincts": {
        "9_1": {"name": "Lewisham North", "precinct_number": 1},
        "9_2": {"name": "Petersham North", "precinct_number": 2},
        "9_3": {"name": "Stanmore North", "precinct_number": 3},
        "9_4": {"name": "Newtown North and Camperdown", "precinct_number": 4},
        "9_5": {"name": "Lewisham South", "precinct_number": 5},
        "9_6": {"name": "Petersham South", "precinct_number": 6},
        "9_7": {"name": "Stanmore South", "precinct_number": 7},
        "9_8": {"name": "Enmore North and Newtown Central", "precinct_number": 8},
        "9_9": {"name": "Newington", "precinct_number": 9},
        "9_10": {"name": "Dulwich Hill North", "precinct_number": 10},
        "9_11": {"name": "Hoskins Park", "precinct_number": 11},
        "9_12": {"name": "Marrickville Park and Morton Park", "precinct_number": 12},
        "9_13": {"name": "Henson Park", "precinct_number": 13},
        "9_14": {"name": "Camdenville", "precinct_number": 14},
        "9_15": {"name": "Enmore Park", "precinct_number": 15},
        "9_16": {"name": "Abergeldie Estate", "precinct_number": 16},
        "9_17": {"name": "New Canterbury Road West", "precinct_number": 17},
        "9_18": {"name": "Dulwich Hill Station North", "precinct_number": 18},
        "9_19": {"name": "Marrickville Road Central", "precinct_number": 19},
        "9_20": {"name": "Marrickville Town Centre North", "precinct_number": 20},
        "9_21": {"name": "Ness Park", "precinct_number": 21},
        "9_22": {"name": "Dulwich Hill Station South", "precinct_number": 22},
        "9_23": {"name": "Marrickville Station West", "precinct_number": 23},
        "9_24": {"name": "Marrickville Town Centre South", "precinct_number": 24},
        "9_25": {"name": "St Peters Triangle", "precinct_number": 25},
        "9_26": {"name": "Barwon Park", "precinct_number": 26},
        "9_27": {"name": "Barwon Park South", "precinct_number": 27},
        "9_28": {"name": "Cooks River West", "precinct_number": 28},
        "9_29": {"name": "South Western Marrickville", "precinct_number": 29},
        "9_30": {"name": "The Warren", "precinct_number": 30},
        "9_31": {"name": "Unwins Bridge Road", "precinct_number": 31},
        "9_32": {"name": "Cooks River East", "precinct_number": 32},
        "9_33": {"name": "Princes Highway", "precinct_number": 33},
        "9_34": {"name": "Tempe Reserve", "precinct_number": 34},
        "9_35": {"name": "Parramatta Road", "precinct_number": 35},
        "9_36": {"name": "Petersham Commercial", "precinct_number": 36},
        "9_37": {"name": "King Street and Enmore Road Commercial", "precinct_number": 37},
        "9_38": {"name": "Dulwich Hill Commercial", "precinct_number": 38},
        "9_39": {"name": "Marrickville Metro", "precinct_number": 39},
        "9_40": {"name": "Marrickville Town Centre Commercial", "precinct_number": 40},
        "9_41": {"name": "Bridge Road", "precinct_number": 41},
        "9_42": {"name": "Camperdown North", "precinct_number": 42},
        "9_43": {"name": "Sydney Steel", "precinct_number": 43},
        "9_44": {"name": "Carrington Road", "precinct_number": 44},
        "9_45": {"name": "McGill Street", "precinct_number": 45},
        "9_46": {"name": "Tempe Lands", "precinct_number": 46},
        "9_47": {"name": "Victoria Road", "precinct_number": 47},
        "9_48": {"name": "Mary Robert and Edith Street", "precinct_number": 48},
    },

    # Precincts all share these common settings
    "precinct_defaults": {
        "applicable_zones": ALL_ZONES,  # Zone filtering done by precinct boundary
        "applicable_dev_types": ALL_DEV_TYPES,
        "site_conditions": None,
        "is_precinct_specific": True,
    },
}
