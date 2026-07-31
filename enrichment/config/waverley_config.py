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

# Standard NSW zone codes for Waverley LEP 2012, current as of the 26 April
# 2023 NSW Employment Zones Reform (DQ-30, .claude/DATA_QUALITY_TRACKER.md).
# Confirmed against lep_zone_coverage: Waverley's real current zones are
# C2, E1, E2, MU1, R2, R3, R4, RE1, RE2, SP2 — ZERO B-zones. BUSINESS_ZONES
# previously hardcoded the retired codes (B1, B2, B4); values here are each
# legacy code's real current equivalent (see
# enrichment/config/zone_taxonomy.py): B1,B2->E1; B4->MU1.
RESIDENTIAL_ZONES = ["R2", "R3", "R4"]
LOW_DENSITY_ZONES = ["R2"]
MEDIUM_HIGH_DENSITY_ZONES = ["R3", "R4"]
BUSINESS_ZONES    = ["E1", "E2"]
MIXED_USE_ZONES   = ["MU1"]
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
        # DQ-30: "C" and "D" previously had a single entry each, collapsing
        # the distinction this file's own header has always documented (C1
        # Low Density vs C2 Medium-High Density; D1 Commercial vs D2 Mixed
        # Use) — a C1 (Low Density, should be R2-only) provision was tagged
        # with R3/R4 too, and vice versa. C1/C2 map directly to the NSW
        # Standard Instrument's own zone names (R2 IS "Low Density
        # Residential", R3/R4 ARE "Medium/High Density Residential" — not an
        # interpretation, the official zone name). D2 (MU1) is equally direct
        # ("Mixed Use" is the zone's official name). D1's exact zone split
        # (E1 Local Centre vs E2 Commercial Centre) is NOT independently
        # source-verified beyond this file's own "Commercial Premises"
        # description — both are included as the more inclusive reading;
        # narrow this if the source DCP text is checked. "C"/"D" remain as
        # fallbacks for a heading with no C1/C2/D1/D2 sub-code.
        "C": {
            "description":       "Residential Development",
            "layer":             "use_specific",
            "applicable_zones":  RESIDENTIAL_ZONES,
        },
        "C1": {
            "description":       "Low Density Residential",
            "layer":             "use_specific",
            "applicable_zones":  LOW_DENSITY_ZONES,
        },
        "C2": {
            "description":       "Medium to High Density Residential",
            "layer":             "use_specific",
            "applicable_zones":  MEDIUM_HIGH_DENSITY_ZONES,
        },
        "D": {
            "description":       "Non-Residential Development",
            "layer":             "use_specific",
            "applicable_zones":  BUSINESS_ZONES + MIXED_USE_ZONES,
        },
        "D1": {
            "description":       "Commercial Premises",
            "layer":             "use_specific",
            "applicable_zones":  BUSINESS_ZONES,
        },
        "D2": {
            "description":       "Mixed Use",
            "layer":             "use_specific",
            "applicable_zones":  MIXED_USE_ZONES,
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
