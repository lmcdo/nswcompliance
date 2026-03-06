"""
Woollahra DCP 2015 Configuration

Structure: per-chapter PDFs, chapter codes A1–E6.
Each chapter PDF has subsection headings of the form "B3.1 Site Coverage" or
"C1.2 Materials", where the chapter code prefix (B3, C1) is the key in `parts`.

Layer assignment:
  generic      — applies to all development regardless of zone or site conditions
  use_specific — applies to specific zones or development types
  condition    — only applies when a site condition flag is set (heritage, flood, etc.)

Source: https://www.woollahra.nsw.gov.au/Building-and-development/Development-rules

Amendment history:
  A2 repealed; C2/C3 were originally separate HCA chapters, subsequently replaced by B2
  (Neighbourhood HCAs); D3 repealed Dec 2023; C2 and C3 reinstated at current URLs.
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
        "A1": {"layer": "generic",      "topic": "general"},     # Introduction / preliminary
        "A3": {"layer": "generic",      "topic": "general"},     # Definitions

        # ── Part B — General Residential ────────────────────────────────────────
        "B1": {"layer": "use_specific", "topic": "residential"}, # Residential precincts
        "B2": {"layer": "condition",    "topic": "heritage"},    # Neighbourhood HCAs
        "B3": {"layer": "generic",      "topic": None},          # General dev controls (topic from text)
        "B4": {"layer": "use_specific", "topic": "residential"}, # Housing in accessible areas

        # ── Part C — Heritage Conservation Areas ────────────────────────────────
        "C1": {"layer": "condition",    "topic": "heritage"},    # Paddington HCA
        "C2": {"layer": "condition",    "topic": "heritage"},    # Woollahra HCA
        "C3": {"layer": "condition",    "topic": "heritage"},    # Watsons Bay HCA

        # ── Part D — Business & Mixed Use Centres ───────────────────────────────
        # D3 repealed Dec 2023.  D1/D2/D5/D6 are further centre chapters.
        "D1": {"layer": "use_specific", "topic": None},
        "D2": {"layer": "use_specific", "topic": None},
        "D4": {"layer": "use_specific", "topic": None},          # Edgecliff Centre
        "D5": {"layer": "use_specific", "topic": None},          # Double Bay Centre
        "D6": {"layer": "use_specific", "topic": None},          # Rose Bay Centre

        # ── Part E — General Controls for All Development ────────────────────────
        "E1": {"layer": "generic",   "topic": "parking"},
        "E2": {"layer": "condition", "topic": "environmental"},  # Stormwater & flood
        "E3": {"layer": "generic",   "topic": "landscaping"},    # Tree management
        "E4": {"layer": "condition", "topic": "environmental"},  # Contaminated land
        "E5": {"layer": "generic",   "topic": "general"},        # Waste management
        "E6": {"layer": "generic",   "topic": "sustainability"},
    },
}
