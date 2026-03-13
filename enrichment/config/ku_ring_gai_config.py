"""
Ku-ring-gai Development Control Plan 2024 Configuration

Structure: Single consolidated DCP (adopted March 2024) with three sections:
  Section A — Residential & General (Parts 1–13)
  Section B — Character Areas & Environmental (Parts 15–20)
  Section C — Design & Technical Standards (Parts 21–25)

Per-Part PDFs uploaded as separate chapters. Parts 10, 11, and 14A-14O
(Child Care, Sex Industry, 15 precinct PDFs) excluded from initial onboarding.

chapter_topics keys are substrings matched against document_id.lower().
document_id pattern: "ku_ring_gai_dcp_2024__{chapter_key_underscored}"
Hyphens in chapter_key are normalised to underscores in document_id.

Note: "part_4_1" must appear before any "part_4" key in the dict to prevent
the shorter key matching Part 4.1 documents first.

Source: https://www.krg.nsw.gov.au/Development/Planning-controls/Development-Control-Plan
"""

KU_RING_GAI_CONFIG = {
    "council": "ku_ring_gai",
    "dcp_name": "Ku-ring-gai DCP 2024",
    "chapter_topics": {
        # ── Part 1 ──────────────────────────────────────────────────────────
        "part_1_introduction":          {"layer": "generic",      "topic": None},
        # ── Section A: Residential & General ────────────────────────────────
        "part_2_site_analysis":         {"layer": "generic",      "topic": None},
        "part_3_subdivision":           {"layer": "generic",      "topic": None},
        # Part 4.1 MUST appear before part_4 (substring collision prevention)
        "part_4_1_secondary_dwellings": {"layer": "use_specific", "topic": "residential"},
        "part_4_dwelling_houses":       {"layer": "use_specific", "topic": "residential"},
        "part_5_dual_occupancy":        {"layer": "use_specific", "topic": "residential"},
        "part_6_multi_dwelling":        {"layer": "use_specific", "topic": "residential"},
        "part_7_residential_flat":      {"layer": "use_specific", "topic": "residential"},
        "part_8_mixed_use":             {"layer": "use_specific", "topic": None},
        "part_9_non_residential":       {"layer": "use_specific", "topic": None},
        "part_12_signage":              {"layer": "generic",      "topic": "signage"},
        "part_13_trees":                {"layer": "generic",      "topic": "trees"},
        # ── Section B: Character Areas & Environmental ───────────────────────
        "part_15_contamination":        {"layer": "generic",      "topic": "contamination"},
        "part_16_bushfire":             {"layer": "generic",      "topic": "bushfire"},
        "part_17_riparian":             {"layer": "generic",      "topic": "stormwater"},
        "part_18_biodiversity":         {"layer": "generic",      "topic": "biodiversity"},
        "part_19_heritage":             {"layer": "generic",      "topic": None},
        "part_20_rail_roads":           {"layer": "generic",      "topic": "acoustic"},
        # ── Section C: Design & Technical Standards ───────────────────────────
        "part_21_site_design":          {"layer": "generic",      "topic": None},
        "part_22_parking":              {"layer": "generic",      "topic": "parking"},
        "part_23_building_design":      {"layer": "generic",      "topic": None},
        "part_24_water":                {"layer": "generic",      "topic": "stormwater"},
        "part_25_waste":                {"layer": "generic",      "topic": None},
    },
}
