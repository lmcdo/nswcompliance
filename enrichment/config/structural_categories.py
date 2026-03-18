"""
Structural category map — maps DCP hierarchy to excludable categories.

Used by SEE intake exclusion to safely determine which provisions can be
auto-excluded based on factual intake answers. Unlike v2_topic (inferred from
keywords, used for soft UI), structural categories are derived from the DCP's
own hierarchy and are deterministic, verifiable, and zero-inference.

Design decision DD-1 (2026-03-13): See plan for rationale.

Usage:
    from enrichment.config.structural_categories import get_structural_category
    cat = get_structural_category("marrickville", "part2-s25-stormwater", "Controls")
    # Returns "stormwater"

Rules:
    1. Only map sections that are STRUCTURALLY about an excludable topic.
    2. A provision in "Privacy" that mentions parking is NOT a parking provision.
    3. Unmapped provisions return None — never excluded (fail-open).
    4. When onboarding a new council, read the DCP table of contents and add
       entries here. Verify against the PDF.
"""
import re
from typing import Optional


# ---------------------------------------------------------------------------
# Excludable categories — must match intake.ts TRIGGER_TO_STRUCTURAL_CATEGORIES
# ---------------------------------------------------------------------------
# Only these categories can trigger auto-exclusion in the SEE intake system.
# Everything else stays in the active provision set.

EXCLUDABLE = {
    "stormwater", "drainage", "trees", "pool", "fencing", "parking",
    "signage", "flooding", "bushfire", "acoustic", "coastal",
    "biodiversity", "demolition", "contamination",
}


# ---------------------------------------------------------------------------
# Per-council structural category maps
# ---------------------------------------------------------------------------
# Two mapping styles:
#   1. chapter_key-only: "part2-s25-stormwater" → "stormwater"
#      Used when chapter_key alone identifies the topic.
#   2. (chapter_key, header_pattern): ("chapter-a-miscellaneous", r"(?i)fencing") → "fencing"
#      Used when a coarse chapter_key needs section_header to disambiguate.
#
# Convention: chapter_key maps take priority. Header patterns are only checked
# when no chapter_key-only match exists.

# Type aliases for clarity
ChapterMap = dict[str, str]                           # chapter_key → category
HeaderPatternMap = dict[tuple[str, str], str]          # (chapter_key, regex) → category

_CHAPTER_MAPS: dict[str, ChapterMap] = {}
_HEADER_MAPS: dict[str, HeaderPatternMap] = {}


# ── Marrickville ────────────────────────────────────────────────────────
# Clean structure: chapter_key slug IS the topic. All 60+ chapter keys are
# self-describing slugs from the DCP structure (Part 2.x, Part 3, Part 4.x,
# Part 8, Part 9 precincts). Verified against marrickville_config.py.
#
# Excludable categories: parking, fencing, signage, biodiversity, stormwater,
#   trees, flooding, contamination.
# Non-excludable (but mapped for UI grouping): access, design, site_analysis,
#   privacy, solar, safety, environmental, sustainability, landscaping, waste,
#   commercial, residential, industrial, heritage, precinct, subdivision,
#   statutory, guidelines, definitions.

_CHAPTER_MAPS["marrickville"] = {
    # ── Part 1: Statutory Information ───────────────────────────────────
    "part1-statutory-info":              "statutory",
    "da-guidelines":                     "statutory",

    # ── Part 2: General Controls ─────────────────────────────────────────
    "part2-s01-urban-design":            "design",
    "part2-s03-site-context-analysis":   "site_analysis",
    "part2-s05-equity-access-mobility":  "access",
    "part2-s06-privacy":                 "privacy",
    "part2-s07-solar-access":            "solar",
    "part2-s09-community-safety":        "safety",
    "part2-s10-parking":                 "parking",        # EXCLUDABLE
    "part2-s11-fencing":                 "fencing",        # EXCLUDABLE
    "part2-s12-signs":                   "signage",        # EXCLUDABLE
    "part2-s13-biodiversity":            "biodiversity",   # EXCLUDABLE
    "part2-s14-unique-env-features":     "environmental",
    "part2-s16-energy-efficiency":       "sustainability",
    "part2-s17-water-sensitive":         "stormwater",     # EXCLUDABLE
    "part2-s18-landscaping":             "landscaping",
    "part2-s20-tree-management":         "trees",          # EXCLUDABLE
    "part2-s21-site-facilities-waste":   "waste",
    "part2-s22-flood-management":        "flooding",       # EXCLUDABLE
    "part2-s23-acid-sulfate":            "environmental",
    "part2-s24-contaminated-land":       "contamination",  # EXCLUDABLE
    "part2-s25-stormwater":              "stormwater",     # EXCLUDABLE
    "part2-s26-entertainment-precincts": "commercial",

    # ── Part 3: Subdivision ───────────────────────────────────────────────
    "part3-subdivision":                 "subdivision",

    # ── Part 4: Residential Development ──────────────────────────────────
    "part4-s1-low-density":              "residential",
    "part4-s2-multi-dwelling":           "residential",
    "part4-s3-boarding-houses":          "residential",

    # ── Part 5: Commercial & Mixed Use ────────────────────────────────────
    "part5-commercial-mixed-use":        "commercial",

    # ── Part 6: Industrial ────────────────────────────────────────────────
    "part6-industrial":                  "industrial",

    # ── Part 7: Specific Development Types ───────────────────────────────
    "part7-s1-childcare":                "residential",
    "part7-s3-sex-industry":             "commercial",

    # ── Part 2: additional sections ──────────────────────────────────────
    "part2-s08-social-impact":           "design",

    # ── Part 8: Heritage ─────────────────────────────────────────────────
    # Managed by HCA flags, not intake triggers — not excludable.
    "part8-heritage":                    "heritage",

    # ── Part 9: Precincts (48 precincts) ─────────────────────────────────
    # All part9-p* keys map to "precinct" — managed by precinct_id, not intake.
    "part9-p01-lewisham-north":          "precinct",
    "part9-p04-newtown-north":           "precinct",
    "part9-p05-lewisham-south":          "precinct",
    "part9-p06-petersham-south":         "precinct",
    "part9-p08-enmore-north":            "precinct",
    "part9-p10-dulwich-hill-north":      "precinct",
    "part9-p11-hoskins-park":            "precinct",
    "part9-p16-abergeldie":              "precinct",
    "part9-p17-new-canterbury-rd":       "precinct",
    "part9-p18-dulwich-hill-stn-north":  "precinct",
    "part9-p19-marrickville-rd-central": "precinct",
    "part9-p22-dulwich-hill-stn-south":  "precinct",
    "part9-p23-marrickville-stn-west":   "precinct",
    "part9-p25-st-peters-triangle":      "precinct",
    "part9-p26-barwon-park":             "precinct",
    "part9-p28-cooks-river-west":        "precinct",
    "part9-p30-the-warren":              "precinct",
    "part9-p35-parramatta-rd":           "precinct",
    "part9-p36-petersham-commercial":    "precinct",
    "part9-p38-dulwich-hill-commercial": "precinct",
    "part9-p39-marrickville-metro":      "precinct",
    "part9-p40-marrickville-tc-commercial": "precinct",
    "part9-p42-camperdown-north":        "precinct",
    "part9-p45-mcgill-st":               "precinct",
    "part9-p47-victoria-road":           "precinct",
    "part9-p48-mary-robert-edith":       "precinct",
    # Additional precinct keys found in DB (not in original audit)
    "part9-p02-petersham-north":         "precinct",
    "part9-p03-stanmore-north":          "precinct",
    "part9-p07-stanmore-south":          "precinct",
    "part9-p09-newington":               "precinct",
    "part9-p12-marrickville-park":       "precinct",
    "part9-p13-henson-park":             "precinct",
    "part9-p14-camdenville":             "precinct",
    "part9-p15-enmore-park":             "precinct",
    "part9-p20-marrickville-tc-north":   "precinct",
    "part9-p21-ness-park":               "precinct",
    "part9-p24-marrickville-tc-south":   "precinct",
    "part9-p27-barwon-park-south":       "precinct",
    "part9-p29-sw-marrickville":         "precinct",
    "part9-p31-unwins-bridge":           "precinct",
    "part9-p32-cooks-river-east":        "precinct",
    "part9-p33-princes-highway":         "precinct",
    "part9-p34-tempe-reserve":           "precinct",
    "part9-p37-king-st-enmore":          "precinct",
    "part9-p41-bridge-road":             "precinct",
    "part9-p43-sydney-steel":            "precinct",
    "part9-p44-carrington-road":         "precinct",
    "part9-p46-tempe-lands":             "precinct",
    "part9-intro":                       "statutory",

    # ── Part 10: Definitions ──────────────────────────────────────────────
    "part10-definitions":                "definitions",
}

# Marrickville: no header patterns needed — chapter_key slugs are sufficient.
_HEADER_MAPS["marrickville"] = {}


# ── Woollahra ───────────────────────────────────────────────────────────
# Excellent structure: per-chapter PDFs, chapter_key IS the topic.

_CHAPTER_MAPS["woollahra"] = {
    "chapter-e1-parking-access": "parking",
    "chapter-e2-stormwater-flood": "stormwater",
    "chapter-e3-tree-management": "trees",
    # "chapter-e5-waste-management" — waste is not excludable via intake
    # "chapter-e6-sustainability" — not excludable
    # "chapter-c1/c2/c3" — heritage HCAs, managed by HCA flags not intake
    # "chapter-b1/b2/b3/b4" — residential/general, not excludable
}

# Woollahra header patterns for chapters that are mixed
_HEADER_MAPS["woollahra"] = {
    # chapter-b3 general development has fencing/signage subsections
    ("chapter-b3-general-development", r"(?i)fencing"): "fencing",
    ("chapter-b3-general-development", r"(?i)signage|advertising"): "signage",
    ("chapter-b3-general-development", r"(?i)swimming\s+pool"): "pool",
    # HCA chapters have parking/fencing subsections within heritage context
    # but these are heritage-contextual, not standalone — do NOT map them.
}


# ── Waverley ────────────────────────────────────────────────────────────
# Single chapter_key for entire DCP. Topic encoded in section_header:
# "Transport — On-Site Parking — Controls" → parking
# "Water Management — Flood Planning" → flooding
# "Signage — Controls" → signage

_CHAPTER_MAPS["waverley"] = {}  # no chapter-level mapping (single chapter)

_HEADER_MAPS["waverley"] = {
    ("waverley-dcp-2022", r"(?i)(?:^|\W)parking(?:\W|$)"): "parking",
    ("waverley-dcp-2022", r"(?i)(?:^|\W)signage(?:\W|$)"): "signage",
    ("waverley-dcp-2022", r"(?i)stormwater|water\s+management"): "stormwater",
    ("waverley-dcp-2022", r"(?i)flood"): "flooding",
    ("waverley-dcp-2022", r"(?i)(?:^|\W)tree(?:s|\W)"): "trees",
    ("waverley-dcp-2022", r"(?i)(?:^|\W)waste(?:\W|$)"): "waste",
    ("waverley-dcp-2022", r"(?i)contamina"): "contamination",
    ("waverley-dcp-2022", r"(?i)(?:^|\W)fenc"): "fencing",
    # "Transport" headers include parking — but only if "parking" appears
    # Generic "Transport" without "parking" is access/movement — not excludable
}


# ── Ashfield ────────────────────────────────────────────────────────────
# 6 chapter keys. chapter-a-miscellaneous and chapter-c-sustainability are
# catch-all chapters needing header patterns. The rest map cleanly at chapter level.
# section_header is 98% unique (provision-level text), so patterns must match
# the LEADING topic prefix (e.g., "Parking -- Figure 12 -- ..." → "parking").

_CHAPTER_MAPS["ashfield"] = {
    # ── Chapter B: Public Domain ──────────────────────────────────────────
    # 49 provisions — streetscape, footpath, public space controls
    "chapter-b-public-domain":          "design",

    # ── Chapter D: Precinct Guidelines ───────────────────────────────────
    # 570 provisions — precinct-specific controls (Ashfield TC, Hurlstone Park, etc.)
    "chapter-d-precinct-guidelines":    "precinct",

    # ── Chapter E1: Heritage ──────────────────────────────────────────────
    # 231 provisions — managed by HCA flags, not intake triggers
    "chapter-e1-heritage":              "heritage",

    # ── Chapter E2: Haberfield ────────────────────────────────────────────
    # 121 provisions — Haberfield HCA-specific controls
    "chapter-e2-haberfield":            "heritage",

    # NOTE: chapter-a-miscellaneous and chapter-c-sustainability omitted here —
    # they need header patterns to assign specific categories.
    # chapter-f-dev-category also uses header patterns for dev-type sub-sections.
}

_HEADER_MAPS["ashfield"] = {
    # ── chapter-a-miscellaneous: 288 provisions ──────────────────────────
    # Section headers have topic prefix: "Parking -- ...", "Fencing -- ..."
    # Pattern matches leading topic word (^ or after whitespace).
    ("chapter-a-miscellaneous", r"(?i)^parking"): "parking",
    ("chapter-a-miscellaneous", r"(?i)^fencing"): "fencing",
    ("chapter-a-miscellaneous", r"(?i)^flood"): "flooding",
    ("chapter-a-miscellaneous", r"(?i)^contaminated"): "contamination",
    ("chapter-a-miscellaneous", r"(?i)^signs?\b|^signage|^advertising"): "signage",
    ("chapter-a-miscellaneous", r"(?i)^tree\s+management|^tree\s+preservation"): "trees",
    ("chapter-a-miscellaneous", r"(?i)^stormwater|^water\s+sensitive|^drainage"): "stormwater",
    ("chapter-a-miscellaneous", r"(?i)^solar\s+access|^sunlight"): "solar",
    ("chapter-a-miscellaneous", r"(?i)^access\s+and\s+mobility|^equity|^disabled"): "access",
    ("chapter-a-miscellaneous", r"(?i)^safety|^crime\s+prevention"): "safety",
    ("chapter-a-miscellaneous", r"(?i)^site\s+and\s+context|^site\s+analysis"): "site_analysis",
    ("chapter-a-miscellaneous", r"(?i)^landscap"): "landscaping",
    ("chapter-a-miscellaneous", r"(?i)^good\s+design|^subdivision"): "design",
    ("chapter-a-miscellaneous", r"(?i)^telecommunications"): "sustainability",
    ("chapter-a-miscellaneous", r"(?i)^development\s+near\s+rail"): "acoustic",

    # ── chapter-c-sustainability: 196 provisions ─────────────────────────
    # Sub-sections: Waste and Recycling (~130), Tree Management (~25),
    # Building Sustainability (~7), GreenWay (~6), Water Sensitive (~5)
    ("chapter-c-sustainability", r"(?i)^waste|^recycl"): "waste",
    ("chapter-c-sustainability", r"(?i)^tree\s+management|^tree\s+preservation"): "trees",
    ("chapter-c-sustainability", r"(?i)^water\s+sensitive|^stormwater|^drainage"): "stormwater",
    ("chapter-c-sustainability", r"(?i)^building\s+sustainability|^energy|^greenway"): "sustainability",

    # ── chapter-f-dev-category: 223 provisions ───────────────────────────
    # Dev-type specific chapters — map to the residential/commercial category
    # based on section header prefix
    ("chapter-f-dev-category", r"(?i)^residential\s+flat|^apartment"): "residential",
    ("chapter-f-dev-category", r"(?i)^dwelling\s+house|^dual\s+occupan"): "residential",
    ("chapter-f-dev-category", r"(?i)^multi.dwelling"): "residential",
    ("chapter-f-dev-category", r"(?i)^commercial|^industrial"): "commercial",
    ("chapter-f-dev-category", r"(?i)^car\s+showroom"): "commercial",
    ("chapter-f-dev-category", r"(?i)^child\s*care"): "residential",
    ("chapter-f-dev-category", r"(?i)^boarding\s+house"): "residential",
    ("chapter-f-dev-category", r"(?i)^sex\s+industry"): "commercial",
    # Parking sub-sections within dev categories
    ("chapter-f-dev-category", r"(?i)(?:^|\W)parking|car\s*park"): "parking",
}


# ── Leichhardt ──────────────────────────────────────────────────────────
# 12 chapter keys. Most are topical enough for direct mapping. Two coarse
# chapters (part-c-s1-general, part-c-s4-non-residential) need header patterns.
# part-c-s2-urban-character (182 provisions) is character/design — not excludable.
# part-g-s1-site-specific (99 provisions) is site-specific precinct controls.

_CHAPTER_MAPS["leichhardt"] = {
    # ── Part A: Introduction ─────────────────────────────────────────────
    "part-a-introduction":              "statutory",

    # ── Part B: Connections ───────────────────────────────────────────────
    "part-b-connections":               "design",

    # ── Part C.S2: Urban Character ────────────────────────────────────────
    # 182 provisions — design/character controls, not excludable
    "part-c-s2-urban-character":        "design",

    # ── Part C.S3: Residential ────────────────────────────────────────────
    # Contains setbacks, privacy, solar, fencing, dormers — mostly not excludable.
    # Flood and acoustic sub-sections handled by header patterns below.
    "part-c-s3-residential":            "residential",

    # ── Part C.S5: Entertainment Precincts ────────────────────────────────
    "part-c-s5-entertainment-precincts": "commercial",

    # ── Part D: Energy ────────────────────────────────────────────────────
    "part-d-energy":                    "sustainability",

    # ── Part E: Water ─────────────────────────────────────────────────────
    # All 17 provisions are flood/stormwater — whole chapter is excludable-mapped
    # via header patterns. Chapter-level catch-all for anything not header-matched:
    "part-e-water":                     "stormwater",

    # ── Part F: Food ──────────────────────────────────────────────────────
    "part-f-food":                      "commercial",

    # ── Appendix B: Building Typologies ──────────────────────────────────
    "appendix-b-building-typologies":   "design",

    # ── Part G: Site-Specific Controls ───────────────────────────────────
    # 99 provisions for specific sites/precincts
    "part-g-s1-site-specific":          "precinct",
    "part-g-s13-pyrmont-bridge-rd":     "precinct",

    # NOTE: part-c-s1-general and part-c-s4-non-residential intentionally
    # omitted here — they need header patterns to assign specific categories.
}

_HEADER_MAPS["leichhardt"] = {
    # ── part-c-s1-general: 63 provisions, each has a specific topic header ──
    ("part-c-s1-general", r"(?i)(?:^|\W)parking|car\s*park"): "parking",
    ("part-c-s1-general", r"(?i)(?:^|\W)fenc"): "fencing",
    ("part-c-s1-general", r"(?i)swimming\s+pool"): "pool",
    ("part-c-s1-general", r"(?i)(?:^|\W)signage|advertising"): "signage",
    ("part-c-s1-general", r"(?i)(?:^|\W)tree|canopy|prescribed\s+tree"): "trees",
    ("part-c-s1-general", r"(?i)acoustic|noise"): "acoustic",
    ("part-c-s1-general", r"(?i)contamina"): "contamination",
    ("part-c-s1-general", r"(?i)heritage"): "heritage",
    ("part-c-s1-general", r"(?i)landscap"): "landscaping",
    ("part-c-s1-general", r"(?i)waste|recycl"): "waste",
    ("part-c-s1-general", r"(?i)solar|sunlight"): "solar",
    ("part-c-s1-general", r"(?i)privacy"): "privacy",
    ("part-c-s1-general", r"(?i)stormwater|drainage"): "stormwater",
    ("part-c-s1-general", r"(?i)flood"): "flooding",
    # Additional non-excludable topics (UI grouping only)
    ("part-c-s1-general", r"(?i)^safety|^crime\s+prevention|^CPTED"): "safety",
    ("part-c-s1-general", r"(?i)^equity|^access\s+and\s+mobility|^disabled"): "access",
    ("part-c-s1-general", r"(?i)^site\s+and\s+context|^SITE\s+AND\s+CONTEXT"): "site_analysis",
    ("part-c-s1-general", r"(?i)^demolition"): "demolition",       # EXCLUDABLE
    ("part-c-s1-general", r"(?i)^subdivision"): "subdivision",
    ("part-c-s1-general", r"(?i)^open\s+space"): "design",
    ("part-c-s1-general", r"(?i)^green\s+roof|^green\s+wall|^green\s+living"): "sustainability",
    ("part-c-s1-general", r"(?i)^site\s+facilit"): "waste",
    ("part-c-s1-general", r"(?i)^alterations|^corner\s+site|^minor\s+architectural|^laneway|^foreshore|^rock\s+face|^structures\s+in"): "design",
    ("part-c-s1-general", r"(?i)^general\s+provisions"): "statutory",
    ("part-c-s1-general", r"(?i)^planning\s+certif|^access\s+to\s+council"): "statutory",
    # Contamination remediation stages (section headers are stage names)
    ("part-c-s1-general", r"(?i)^stage\s+[1-4]|^remediation|^independent\s+site\s+aud|^initial\s+eval|^development\s+controls\s+for\s+rem"): "contamination",

    # ── part-c-s4-non-residential: 52 provisions ─────────────────────────
    ("part-c-s4-non-residential", r"(?i)(?:^|\W)parking|car\s*park"): "parking",
    ("part-c-s4-non-residential", r"(?i)(?:^|\W)signage|advertising"): "signage",
    ("part-c-s4-non-residential", r"(?i)waste|recycl"): "waste",
    ("part-c-s4-non-residential", r"(?i)child\s+care"): "residential",
    ("part-c-s4-non-residential", r"(?i)outdoor\s+dining"): "commercial",
    # Dev-type specific controls → commercial (non-excludable)
    ("part-c-s4-non-residential", r"(?i)^licensed\s+prem|^sex\s+serv|^vehicle\s+repair|^vehicle\s+sales|^home\s+based|^market|^specialised\s+retail|^medical\s+centre|^shopfront|^creative\s+ind|^mixed\s+use|^recreational\s+facilit|^industrial\s+dev|^B7\s+BUSINESS"): "commercial",
    ("part-c-s4-non-residential", r"(?i)^elevation|^site\s+layout|^interface\s+amen|^building\s+elev"): "design",
    ("part-c-s4-non-residential", r"(?i)^ecologically|^sustainable"): "sustainability",
    ("part-c-s4-non-residential", r"(?i)^objectives\s+for\s+non"): "statutory",

    # ── part-e-water: flood/stormwater disambiguation ─────────────────────
    ("part-e-water", r"(?i)flood"): "flooding",
    ("part-e-water", r"(?i)stormwater|drainage|water\s+sensitive"): "stormwater",

    # ── part-c-s3-residential: acoustic + flood sub-sections ─────────────
    ("part-c-s3-residential", r"(?i)acoustic|noise"): "acoustic",
    ("part-c-s3-residential", r"(?i)flood"): "flooding",
    ("part-c-s3-residential", r"(?i)fenc"): "fencing",
    ("part-c-s3-residential", r"(?i)solar|sunlight"): "solar",
    ("part-c-s3-residential", r"(?i)privacy"): "privacy",
}


# ── City of Sydney ─────────────────────────────────────────────────────
# Per-section PDFs. Section 3 (General Provisions) contains many topics
# identifiable by section_header. Sections 1, 2, 5, 6 are either
# administrative, precinct-specific, or site-specific — not excludable.

_CHAPTER_MAPS["city_of_sydney"] = {}  # section keys too coarse

_HEADER_MAPS["city_of_sydney"] = {
    # Section 3: General Provisions — main topic-specific controls
    ("section-3-general-provisions", r"(?i)(?:^|\W)parking|car\s*park"): "parking",
    ("section-3-general-provisions", r"(?i)(?:^|\W)signage|signs?\b|advertising"): "signage",
    ("section-3-general-provisions", r"(?i)(?:^|\W)tree|canopy"): "trees",
    ("section-3-general-provisions", r"(?i)(?:^|\W)fenc"): "fencing",
    ("section-3-general-provisions", r"(?i)swimming\s+pool|pools?"): "pool",
    ("section-3-general-provisions", r"(?i)stormwater|water\s+management"): "stormwater",
    ("section-3-general-provisions", r"(?i)flood"): "flooding",
    ("section-3-general-provisions", r"(?i)contamina"): "contamination",
    ("section-3-general-provisions", r"(?i)acoustic|noise"): "acoustic",
    # Section 4: Development Types — some have topic-specific subsections
    ("section-4-development-types", r"(?i)(?:^|\W)parking|car\s*park"): "parking",
    ("section-4-development-types", r"(?i)(?:^|\W)signage|advertising"): "signage",
}


# ── Ku-ring-gai ─────────────────────────────────────────────────────────
# Single consolidated DCP 2024. Chapter_key encodes the topic directly
# for the dedicated topic chapters — no header disambiguation needed.

_CHAPTER_MAPS["ku_ring_gai"] = {
    "section-a-part-12-signage":       "signage",
    "section-a-part-13-trees":         "trees",
    "section-b-part-15-contamination": "contamination",
    "section-b-part-16-bushfire":      "bushfire",
    "section-b-part-17-riparian":      "stormwater",   # riparian = waterway/drainage controls
    "section-b-part-18-biodiversity":  "biodiversity",
    "section-c-part-22-parking":       "parking",
    "section-c-part-24-water":         "stormwater",
}

_HEADER_MAPS["ku_ring_gai"] = {}  # chapter_key alone is sufficient


# ---------------------------------------------------------------------------
# Lookup function
# ---------------------------------------------------------------------------

def get_structural_category(
    council: str,
    chapter_key: str,
    section_header: Optional[str],
) -> Optional[str]:
    """
    Determine the structural category of a provision from its DCP position.

    Returns an excludable category string (e.g., "parking", "stormwater")
    or None if the provision has no excludable structural category.

    This is used for SEE intake exclusion — provisions with None are never
    auto-excluded, regardless of their v2_topic tag.
    """
    council = council.lower() if council else ""

    # 1. Check chapter-key-only map (fast path)
    chapter_map = _CHAPTER_MAPS.get(council, {})
    if chapter_key in chapter_map:
        return chapter_map[chapter_key]

    # 2. Check (chapter_key, header_pattern) map
    header_map = _HEADER_MAPS.get(council, {})
    if section_header:
        for (ck, pattern), category in header_map.items():
            if ck == chapter_key and re.search(pattern, section_header):
                return category

    return None
