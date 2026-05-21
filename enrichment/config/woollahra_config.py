"""
Woollahra DCP 2015 Configuration

Structure: per-chapter PDFs, chapter codes A1–F3.
Each chapter PDF has subsection headings of the form "B3.1 Site Coverage" or
"C1.2 Materials", where the chapter code prefix (B3, C1) is the key in `parts`.

Layer assignment:
  generic      — applies to all development regardless of zone or site conditions
  use_specific — applies to specific zones or development types
  condition    — only applies when a site condition flag is set (heritage, flood, etc.)

Zone mapping:
  Woollahra LEP 2014 zones: R2, R3, B1, B2, B4, SP2, RE1, RE2, E2, E3.
  No R1/R4/R5, no B3/B5-B7. Zone assignments below reflect the LEP zoning map.

Source: https://www.woollahra.nsw.gov.au/Building-and-development/Development-rules

Amendment history:
  A2 repealed; C2/C3 were originally separate HCA chapters, subsequently replaced by B2
  (Neighbourhood HCAs); D3 NOT repealed (still in DB); C2 and C3 reinstated at current
  URLs. D5 (Double Bay) not yet in DB. E7/E8/F1/F3 added from extraction.
"""

BASE_URL = "https://www.woollahra.nsw.gov.au/files/assets/public/plans-policies-publications/development-control-plans"

WOOLLAHRA_CONFIG = {
    "council": "woollahra",
    "dcp_name": "Woollahra DCP 2015",

    # Section codes are extracted from the markdown heading injected by the extractor:
    #   "# B3.1 Site Coverage\n\n..." → code "B3.1" → stripped to "B3" → lookup here.
    # Exact match is tried first, then progressive strip, then single-letter prefix.
    "parts": {
        # ── Part A — Introduction & Definitions ─────────────────────────────────
        "A1": {
            "layer": "generic",
            "topic": "general",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "A3": {
            "layer": "generic",
            "topic": "general",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },

        # ── Part B — General Residential ────────────────────────────────────────
        "B1": {
            "layer": "use_specific",
            "topic": "residential",
            "applicable_zones": ["R2", "R3"],
            "applicable_dev_types": [
                "dwelling_house", "secondary_dwelling", "dual_occupancy",
                "semi_detached_dwelling", "multi_dwelling_housing",
                "residential_flat_building",
            ],
        },
        "B2": {
            "layer": "condition",
            "topic": "heritage",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["heritage"],
        },
        "B3": {
            "layer": "generic",
            "topic": None,  # topic from text
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "B4": {
            "layer": "use_specific",
            "topic": "residential",
            "applicable_zones": ["R3"],
            "applicable_dev_types": [
                "multi_dwelling_housing", "residential_flat_building",
                "boarding_house", "shop_top_housing",
            ],
        },

        # ── Part C — Heritage Conservation Areas ────────────────────────────────
        "C1": {
            "layer": "condition",
            "topic": "heritage",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["heritage"],
        },
        "C2": {
            "layer": "condition",
            "topic": "heritage",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["heritage"],
        },
        "C3": {
            "layer": "condition",
            "topic": "heritage",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["heritage"],
        },

        # ── Part D — Business & Mixed Use Centres ───────────────────────────────
        "D1": {
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["B1"],
            "applicable_dev_types": [
                "commercial_premises", "retail_premises", "office_premises",
                "food_and_drink_premises",
            ],
        },
        "D2": {
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["B4"],
            "applicable_dev_types": [
                "commercial_premises", "shop_top_housing",
                "residential_flat_building",
            ],
        },
        "D3": {
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["B1", "B2", "B4"],
            "applicable_dev_types": ["ALL"],
        },
        "D4": {
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["B4"],
            "applicable_dev_types": [
                "commercial_premises", "shop_top_housing",
                "residential_flat_building",
            ],
        },
        "D5": {
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["B2"],
            "applicable_dev_types": [
                "commercial_premises", "retail_premises", "office_premises",
            ],
        },
        "D6": {
            "layer": "use_specific",
            "topic": "commercial",
            "applicable_zones": ["B1"],
            "applicable_dev_types": [
                "commercial_premises", "retail_premises",
                "food_and_drink_premises",
            ],
        },

        # ── Part E — General Controls for All Development ────────────────────────
        "E1": {
            "layer": "generic",
            "topic": "parking",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "E2": {
            "layer": "condition",
            "topic": "environmental",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["flood"],
        },
        "E3": {
            "layer": "generic",
            "topic": "landscaping",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "E4": {
            "layer": "condition",
            "topic": "environmental",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
            "site_conditions": ["contamination"],
        },
        "E5": {
            "layer": "generic",
            "topic": "waste",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "E6": {
            "layer": "generic",
            "topic": "sustainability",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "E7": {
            "layer": "generic",
            "topic": "signage",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },
        "E8": {
            "layer": "generic",
            "topic": "accessibility",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["ALL"],
        },

        # ── Part F — Land Use Specific Controls ─────────────────────────────────
        "F1": {
            "layer": "use_specific",
            "topic": "child_care",
            "applicable_zones": ["ALL"],
            "applicable_dev_types": ["child_care_centre"],
        },
        "F3": {
            "layer": "use_specific",
            "topic": "licensed_premises",
            "applicable_zones": ["B1", "B2", "B4"],
            "applicable_dev_types": ["food_and_drink_premises"],
        },
    },
}
