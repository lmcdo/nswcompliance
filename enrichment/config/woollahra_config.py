"""
Woollahra DCP 2015 Configuration

Structure (Parts A–G, per-chapter PDFs):
- Part A: Introduction / Preliminary — administrative, applies to ALL
- Part B: General Provisions — applies to ALL (setbacks, height, parking, etc.)
- Part C: Heritage Conservation Areas — condition-based (heritage items / HCAs only)
  - C1: Paddington HCA
  - C2: Woollahra HCA
  - C3: Watsons Bay HCA
  (additional HCA chapters follow same pattern)
- Part D: Business / Commercial — zone-filtered
- Part E: Special Uses & Infrastructure — zone/use-filtered
- Part F: Residential Development — zone-filtered
- Part G: Landscaping, Trees, and Open Space — generic

Source: https://www.woollahra.nsw.gov.au/Building-and-development/Development-rules/dcps-background
Registry pattern: per-chapter PDFs (one row per chapter in dcp_chapter_registry)
"""

WOOLLAHRA_CONFIG = {
    "council": "woollahra",
    "dcp_name": "Woollahra DCP 2015",
    # Section codes extracted from provision_text headings.
    # Exact match checked first (e.g., "C1"), then letter prefix (e.g., "C").
    "parts": {
        "A":  {"layer": "generic",      "topic": "general"},
        "B":  {"layer": "generic",      "topic": None},
        # Heritage Conservation Areas — all C chapters are condition-based
        "C":  {"layer": "condition",    "topic": "heritage"},
        "C1": {"layer": "condition",    "topic": "heritage"},   # Paddington HCA
        "C2": {"layer": "condition",    "topic": "heritage"},   # Woollahra HCA
        "C3": {"layer": "condition",    "topic": "heritage"},   # Watsons Bay HCA
        "D":  {"layer": "use_specific", "topic": None},
        "E":  {"layer": "use_specific", "topic": None},
        "F":  {"layer": "use_specific", "topic": None},
        "G":  {"layer": "generic",      "topic": "landscaping"},
    },
}
