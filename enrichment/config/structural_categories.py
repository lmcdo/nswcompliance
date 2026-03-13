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
# Clean structure: chapter_key slug IS the topic for topic-specific chapters.
# Precinct chapters (part9-*) are precinct-specific — no excludable category.

_CHAPTER_MAPS["marrickville"] = {
    "part2-s25-stormwater": "stormwater",
    # "part2-s18-landscaping" — not excludable (landscaping always applies)
    # "part8-heritage" — not excludable (managed by HCA flags, not intake)
    # "part3-subdivision" — not excludable
}

# Marrickville sections within general chapters that are structurally about a topic
_HEADER_MAPS["marrickville"] = {
    # part2-s05 has a dedicated "Car parking" section header
    ("part2-s05-equity-access-mobility", r"(?i)^car\s+parking$"): "parking",
}


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
# Mixed: chapter-a-miscellaneous contains many topics. section_header is key.

_CHAPTER_MAPS["ashfield"] = {}  # chapter keys too coarse

_HEADER_MAPS["ashfield"] = {
    ("chapter-a-miscellaneous", r"(?i)^fencing"): "fencing",
    ("chapter-a-miscellaneous", r"(?i)^parking"): "parking",
    ("chapter-a-miscellaneous", r"(?i)^flood"): "flooding",
    ("chapter-a-miscellaneous", r"(?i)^contaminated"): "contamination",
    ("chapter-a-miscellaneous", r"(?i)^signage"): "signage",
    ("chapter-a-miscellaneous", r"(?i)^tree\s+management"): "trees",
    ("chapter-c-sustainability", r"(?i)^tree\s+management"): "trees",
    ("chapter-c-sustainability", r"(?i)^water\s+sensitive"): "stormwater",
    # Heritage chapters (e1, e2) managed by HCA flags — not mapped here
}


# ── Leichhardt ──────────────────────────────────────────────────────────
# Coarse chapter keys. Section headers are uppercase topic names within
# the general chapters (part-c-s1-general has PARKING, FENCING, etc.)

_CHAPTER_MAPS["leichhardt"] = {}  # chapter keys too coarse

_HEADER_MAPS["leichhardt"] = {
    # part-c-s1-general contains many topic-specific sections
    ("part-c-s1-general", r"(?i)(?:^|\W)parking|car\s*park"): "parking",
    ("part-c-s1-general", r"(?i)(?:^|\W)fenc"): "fencing",
    ("part-c-s1-general", r"(?i)swimming\s+pool"): "pool",
    ("part-c-s1-general", r"(?i)(?:^|\W)signage|advertising"): "signage",
    ("part-c-s1-general", r"(?i)(?:^|\W)tree|canopy|prescribed\s+tree"): "trees",
    ("part-c-s1-general", r"(?i)acoustic"): "acoustic",
    ("part-c-s1-general", r"(?i)contamina"): "contamination",
    # part-c-s4-non-residential has similar topic sections
    ("part-c-s4-non-residential", r"(?i)(?:^|\W)parking|car\s*park"): "parking",
    ("part-c-s4-non-residential", r"(?i)(?:^|\W)signage"): "signage",
    ("part-c-s4-non-residential", r"(?i)child\s+care"): "childcare",  # not excludable but mapped for completeness
    # part-e-water contains flood/stormwater
    ("part-e-water", r"(?i)flood"): "flooding",
    ("part-e-water", r"(?i)stormwater"): "stormwater",
    # part-c-s3-residential has acoustic, flood sections
    ("part-c-s3-residential", r"(?i)acoustic"): "acoustic",
    ("part-c-s3-residential", r"(?i)flood"): "flooding",
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
