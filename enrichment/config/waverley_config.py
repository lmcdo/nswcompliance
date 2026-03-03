"""
Waverley DCP 2022 Configuration

Structure (Parts A–F, 490 pages, Amendment 5):
- Part A: Preliminary — administrative, applies to ALL
- Part B: General Provisions — applies to ALL (B1–B17 topics)
  - B8: Heritage — condition-based (heritage items and HCAs only)
- Part C: Residential Development — zone-filtered
  - C1: Low Density Residential
  - C2: Medium to High Density Residential
- Part D: Non-Residential Development — zone-filtered
  - D1: Commercial Premises
  - D2: Mixed Use
- Part E: Site-Specific Provisions — precinct-filtered
  - E1: Bondi Junction Centre
  - E2: Bondi Beachfront Area
  - E3: Local Village Centres
  - E4: Special Character Areas
  - E5: 113 Macpherson Street, Bronte
  - E6: 194-214 Oxford Street Bondi Junction
  - E7: Edina Estate
- Part F: Development-Specific Controls — type-filtered
  - F1: Shared Residential Accommodation
  - F2: Tourist and Visitor Accommodation
  - F3: Child Care Centres
  - F4: Places of Public Worship
  - F5: Horticulture

Source PDF: waverley/Waverley_DCP_2022_Full_Version_Amendment5.pdf
Registry key: waverley/waverley-dcp-2022
"""

# Standard NSW zone codes for Waverley LEP 2012
RESIDENTIAL_ZONES = ["R2", "R3", "R4"]
BUSINESS_ZONES    = ["B1", "B2", "B4"]
MIXED_USE_ZONES   = ["B4"]
SPECIAL_ZONES     = ["SP1", "SP2"]
ALL_ZONES         = ["ALL"]

# Part B section codes → topic slugs
WAVERLEY_PART_B_TOPICS: dict[str, str] = {
    "B1":  "waste",
    "B2":  "sustainability",
    "B3":  "landscaping",
    "B4":  "coastal",
    "B5":  "water",
    "B6":  "accessibility",
    "B7":  "transport",
    "B8":  "heritage",
    "B9":  "safety",
    "B10": "public_art",
    "B11": "design_excellence",
    "B12": "subdivision",
    "B13": "excavation",
    "B14": "signage",
    "B15": "public_domain",
    "B16": "inter_war_buildings",
    "B17": "social_impact",
}

# Part E precinct codes → human-readable names
WAVERLEY_PRECINCTS: dict[str, str] = {
    "E1": "Bondi Junction Centre",
    "E2": "Bondi Beachfront Area",
    "E3": "Local Village Centres",
    "E4": "Special Character Areas",
    "E5": "113 Macpherson Street, Bronte",
    "E6": "194-214 Oxford Street Bondi Junction",
    "E7": "Edina Estate",
}

WAVERLEY_CONFIG = {
    "council": "waverley",
    "dcp_name": "Waverley DCP 2022",
    "parts": {
        "A": {
            "description":     "Preliminary",
            "layer":           "generic",
            "site_conditions": None,
        },
        "B": {
            "description":     "General Provisions",
            "layer":           "generic",
            "site_conditions": None,
        },
        "B8": {
            "description":     "Heritage",
            "layer":           "condition",
            "site_conditions": ["heritage"],
        },
        "C": {
            "description":       "Residential Development",
            "layer":             "use_specific",
            "applicable_zones":  RESIDENTIAL_ZONES,
        },
        "D": {
            "description":       "Non-Residential Development",
            "layer":             "use_specific",
            "applicable_zones":  BUSINESS_ZONES,
        },
        "E": {
            "description":           "Site-Specific Provisions",
            "layer":                 "precinct",
            "is_precinct_specific":  True,
        },
        "F": {
            "description":     "Development-Specific Controls",
            "layer":           "use_specific",
            "site_conditions": None,
        },
    },
    "precincts": WAVERLEY_PRECINCTS,
    "part_b_topics": WAVERLEY_PART_B_TOPICS,
}
