#!/usr/bin/env python3
"""
DCP Chapter Extraction Pipeline
================================
Queries dcp_chapter_registry for chapters with needs_extraction=TRUE,
downloads each chapter PDF from R2, extracts provisions with pdfplumber,
and updates the database atomically per chapter.

If a chapter fails, it rolls back — old provisions stay live and
needs_extraction stays TRUE so the next monitor run retries automatically.

Usage:
    python3 scripts/dcp_extract_changed.py               # extract all flagged chapters
    python3 scripts/dcp_extract_changed.py --council marrickville
    python3 scripts/dcp_extract_changed.py --dry-run     # extract but no DB writes
    python3 scripts/dcp_extract_changed.py --review      # extract to review file, no DB writes
    python3 scripts/dcp_extract_changed.py --council ku_ring_gai --review

Exit codes:
    0 = nothing to extract (no needs_extraction=TRUE rows)
    1 = at least one chapter was attempted and all failed
    2 = at least one chapter extracted successfully
"""

import argparse
import os
import re
import sys
import tempfile
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import boto3
import pdfplumber
import psycopg2
from dotenv import load_dotenv

# Enrichment pipeline — imported here so extraction + enrichment run as one command.
# sys.path is extended so this script can be run from any working directory.
sys.path.insert(0, str(Path(__file__).parent.parent))
from enrichment.pipeline import (
    run_actionability_classification,
    run_layer_tagging,
    run_applicability_tagging,
)

load_dotenv(Path(__file__).parent.parent / ".env")

R2_ACCOUNT_ID        = os.environ["R2_ACCOUNT_ID"]
R2_BUCKET_NAME       = os.environ["R2_BUCKET_NAME"]
R2_ACCESS_KEY_ID     = os.environ["R2_ACCESS_KEY_ID"]
R2_SECRET_ACCESS_KEY = os.environ["R2_SECRET_ACCESS_KEY"]
DATABASE_URL         = os.environ.get("DATABASE_URL") or os.environ["SUPABASE_DB_URL"]

R2_ENDPOINT = f"https://{R2_ACCOUNT_ID}.r2.cloudflarestorage.com"


# ── Council-specific page range configs ─────────────────────────────────────
# Used as fallback when SECTION_RE can't detect chapter boundaries (e.g., multi-line headers).
# Tuple format: (section_key, title, page_start, page_end)  — 1-indexed page numbers.

WAVERLEY_PAGE_RANGES: list[tuple[str, str, int, int]] = [
    # All page numbers are PDF physical pages (1-indexed), verified against pdfplumber output.
    # Pages 1–11: cover/TOC/policy — excluded.
    # Part B — General Controls
    ("B1",  "Waste",                                          12,  23),
    ("B2",  "Ecologically Sustainable Development",           24,  35),
    ("B3",  "Landscaping, Biodiversity and Vegetation",       36,  48),
    ("B4",  "Coastal Risk Management",                        49,  49),
    ("B5",  "Water Management",                               50,  61),
    ("B6",  "Accessibility and Adaptability",                 62,  66),
    ("B7",  "Transport",                                      67,  86),
    ("B8",  "Heritage",                                       87, 114),
    ("B9",  "Safety",                                        115, 116),
    ("B10", "Public Art",                                    117, 117),
    ("B11", "Design Excellence",                             118, 119),
    ("B12", "Subdivision",                                   120, 121),
    ("B13", "Excavation",                                    122, 124),
    ("B14", "Advertising and Signage",                       125, 135),
    ("B15", "Public Domain",                                 136, 146),
    ("B16", "Inter-War Buildings",                           147, 150),
    ("B17", "Social Impact Assessment",                      151, 151),
    # Pages 152–185: Part B annexures + Part C intro — excluded.
    # Part C — Residential Development
    ("C1",  "Low Density Residential",                       186, 218),
    ("C2",  "Other Residential Development",                 219, 249),
    # Page 250: Part D contents — excluded.
    # Part D — Commercial Development
    ("D1",  "Commercial and Retail Development",             251, 258),
    ("D2",  "Outdoor Dining",                                259, 259),
    # Pages 260–261: Part E intro/contents — excluded.
    # Part E — Site Specific Development
    ("E1",  "Bondi Junction",                                262, 315),
    ("E2",  "Bondi Beachfront Area",                         316, 338),
    ("E3",  "Local Village Centres",                         339, 373),
    ("E4",  "Special Character Areas",                       374, 379),
    ("E5",  "113 Macpherson Street Bronte",                  380, 385),
    ("E6",  "194-214 Oxford Street",                         386, 394),
    ("E7",  "Edina Estate",                                  395, 413),
    # Pages 414–458: Part E annexures — excluded.
    # Page 459: Part F contents — excluded.
    # Part F — Development Specific
    ("F1",  "Shared Residential Accommodation",              460, 461),
    ("F2",  "Tourist and Visitor Accommodation",             462, 465),
    ("F3",  "Child Care Centres",                            466, 466),
    ("F4",  "Places of Public Worship",                      467, 472),
    ("F5",  "Horticulture",                                  473, 473),
    # Pages 474+: Definitions — excluded.
]

COUNCIL_PAGE_RANGES: dict[str, list[tuple[str, str, int, int]]] = {
    "waverley": WAVERLEY_PAGE_RANGES,
}

# ── Per-chapter page ranges (for councils with per-chapter PDFs) ─────────────
# Key: (council, chapter_key) → page ranges within that chapter's PDF.
# Checked BEFORE COUNCIL_PAGE_RANGES — allows per-chapter config for councils
# that have separate PDFs per chapter (unlike Waverley which is one PDF).
COUNCIL_CHAPTER_RANGES: dict[tuple[str, str], list[tuple[str, str, int, int]]] = {
    # Ashfield DCP 2016: per-chapter PDFs, "Part X" structure.
    # Pages 1-3 of each chapter are cover/TOC — skip them.
    # Chapters G (Definitions), H (Amendments), preliminary are non-provision.
    ("ashfield", "chapter-a-miscellaneous"): [
        ("A-Part1",  "Site and Context Analysis",       4,   7),
        ("A-Part2",  "Good Design",                     8,  12),
        ("A-Part3",  "Flood Hazard",                   13,  23),
        ("A-Part4",  "Solar Access and Overshadowing",  24,  26),
        ("A-Part5",  "Landscaping",                    27,  30),
        ("A-Part6",  "Safety by Design",               31,  33),
        ("A-Part7",  "Access and Mobility",            34,  52),
        ("A-Part8",  "Parking",                        53,  89),
        ("A-Part9",  "Subdivision",                    90,  93),
        ("A-Part10", "Signs and Advertising",          94, 110),
        ("A-Part11", "Fencing",                       111, 113),
        ("A-Part12", "Telecommunications Facilities", 114, 116),
        ("A-Part13", "Development Near Rail Corridors", 117, 120),
        ("A-Part14", "Contaminated Land",             121, 123),
        ("A-Part15", "Stormwater Management",         124, 126),
    ],
    ("ashfield", "chapter-b-public-domain"): [
        # PDF TOC (page 3) lists 10 topics — multiple topics share pages (6,7,8,10).
        # Split into 7 distinct page groups so provisions spread across pages.
        ("B-intro",  "Introduction",                    1,   3),
        ("B-s1",     "Active Street Frontages",         4,   5),
        ("B-s2-3",   "Awnings and Street Trees",        6,   6),
        ("B-s4-5",   "Wind Effects and Reflectivity",   7,   7),
        ("B-s6-7",   "Public Domain Plan and Footways", 8,   8),
        ("B-s8",     "External Lighting",               9,   9),
        ("B-s9-10",  "Undergrounding and Public Art",  10,  10),
    ],
    ("ashfield", "chapter-c-sustainability"): [
        ("C-Part1",  "Building Sustainability",         3,   9),
        ("C-Part2",  "Water Sensitive Urban Design",   10,  12),
        ("C-Part3",  "Waste and Recycling",            13,  76),
        ("C-Part4",  "Tree Management",                77,  85),
        ("C-Part5",  "GreenWay",                       86,  90),
    ],
    ("ashfield", "chapter-d-precinct-guidelines"): [
        ("D-Part1",  "Ashfield Town Centre",            3,  42),
        ("D-Part2",  "Ashfield East",                  43,  59),
        ("D-Part3",  "Croydon South",                  60,  85),
        ("D-Part4",  "Haberfield",                     86, 111),
        ("D-Part5",  "Hurlstone Park",                112, 157),
        ("D-Part6",  "Summer Hill",                   158, 170),
        ("D-Part7",  "Ashfield South",                171, 181),
        ("D-Part8",  "Canterbury Road",               182, 204),
    ],
    ("ashfield", "chapter-e1-heritage"): [
        # E1 has 392 pages and high SECTION_RE hit rate (175%) — let regex handle it.
        # Include full range so page-range mode is used (skips cover pages 1-2).
        ("E1-Heritage", "Heritage Items and Conservation Areas", 3, 392),
    ],
    ("ashfield", "chapter-e2-haberfield"): [
        # 21 numbered sub-sections (2.2.1-2.2.21). Most on their own page.
        # Some sub-sections share a page — grouped into one range.
        # Verified from PDF via inspect_e2_sections.py (2026-03-31).
        ("E2-intro",   "Introduction",                          1,  2),
        ("E2-s2-1",    "Desired Future Character",              3,  4),
        ("E2-s2-2-3",  "General and Pattern of Development",    5,  5),
        ("E2-s2-4",    "Building Form",                         6,  6),
        ("E2-s2-5",    "Roof Forms",                            7,  7),
        ("E2-s2-6",    "Siting Setbacks and Levels",            8,  8),
        ("E2-s2-7",    "Walls",                                 9,  9),
        ("E2-s2-8-9",  "Chimneys and Joinery",                 10, 10),
        ("E2-s2-10",   "Windows and Doors",                    11, 11),
        ("E2-s2-11-12","Window Sunhoods and Verandahs",        12, 12),
        ("E2-s2-13",   "Garages and Carports",                 13, 13),
        ("E2-s2-14-15","Outbuildings and Colour Schemes",      14, 14),
        ("E2-s2-16",   "Fences and Gates",                     15, 15),
        ("E2-s2-17",   "Garden Elements",                      16, 16),
        ("E2-s2-18-19","Modern Technology and Commercial",     17, 18),
        ("E2-s2-20",   "Non-Conforming Houses",                19, 19),
        ("E2-s2-21",   "New Dwellings",                        20, 22),
    ],
    ("ashfield", "chapter-f-dev-category"): [
        ("F-Part1",  "Dwelling Houses and Dual Occupancies",  3,  28),
        ("F-Part2",  "Multi-Dwelling Housing",               29,  36),
        ("F-Part3",  "Residential Flat Buildings",           37,  49),
        ("F-Part4",  "Boarding Houses",                      50,  55),
        ("F-Part5",  "Commercial and Industrial",            56,  65),
        ("F-Part6",  "Childcare Centres",                    66,  72),
        ("F-Part7",  "Sex Industry",                         73,  78),
        ("F-Part8",  "Car Showrooms",                        79,  85),
    ],
    # ── Ku-ring-gai DCP 2024: per-chapter PDFs ───────────────────────────────
    # These chapters use alphanumeric section codes (4A.2, 5C.1, 19D.5 etc.)
    # which are NOT matched by SECTION_RE. Page ranges defined from PDF inspection.
    # Cover/TOC is page 1. Intro pages (1-2 or 1-4) skipped via "intro" section.
    ("ku_ring_gai", "section-a-part-3-subdivision"): [
        ("intro",  "Introduction",                          1,  3),
        ("3a_1",   "Lot Shape, Orientation and Design",     4,  4),
        ("3a_2",   "Minimum Lot Depth for Bush Fire Prone Land", 5,  8),
        ("3a_3",   "Building Footprint",                    9,  9),
        ("3a_4",   "Trees and Vegetation",                 10, 10),
        ("3a_5",   "Access",                               11, 13),
        ("3a_6",   "Infrastructure",                       14, 16),
        ("3b",     "Land Consolidation",                   17, 21),
        ("3c",     "Strata and Community Title Subdivision", 22, 22),
        ("3r",     "References",                           23, 24),
    ],
    ("ku_ring_gai", "section-a-part-4-dwelling-houses"): [
        ("intro",  "Introduction",                          1,  2),
        ("4a",     "Site Design",                           3,  3),
        ("4a_1",   "Local Character and Streetscape",       4, 10),
        ("4a_2",   "Building Setbacks",                    11, 11),
        ("4a_3",   "Built-Upon Area",                      12, 13),
        ("4a_4",   "Landscaping",                          14, 15),
        ("4b_1",   "Vehicle Access",                       16, 16),
        ("4b_2",   "Car Parking Provision",                17, 17),
        ("4b_3",   "Carports and Garages",                 18, 21),
        ("4c_1",   "Building Envelopes",                   22, 23),
        ("4c_2",   "Building Facades",                     24, 25),
        ("4c_3",   "First Floor Design and Roof Forms",    26, 27),
        ("4c_4",   "Private Open Space",                   28, 28),
        ("4c_5",   "Solar Access",                         29, 29),
        ("4c_6",   "Natural Ventilation",                  30, 30),
        ("4c_7",   "Ancillary Facilities",                 31, 36),
        ("4c_9",   "Waste Management",                     37, 37),
        ("4c_10",  "Materials and Finishes",               38, 38),
    ],
    ("ku_ring_gai", "section-a-part-4-1-secondary-dwellings"): [
        ("intro",    "Introduction",                        1,  3),
        ("4_1a_1",   "General",                             4,  4),
        ("4_1a_2",   "Site Layout",                         5,  6),
        ("4_1a_3",   "Building Setbacks and Separation",    7,  9),
        ("4_1b_1",   "Access",                             11, 13),
        ("4_1b_2",   "Car Parking Provision",              14, 15),
        ("4_1c_1",   "Solar Access",                       16, 16),
        ("4_1c_2",   "Private Open Space",                 17, 17),
        ("4_1c_3",   "Building Envelopes",                 18, 18),
        ("4_1c_4",   "Building and Room Sizes",            19, 19),
        ("4_1c_5",   "Building Appearance",                20, 20),
        ("4_1c_6",   "Building Services",                  21, 21),
        ("4_1c_7",   "Visual and Acoustic Privacy",        22, 24),
    ],
    ("ku_ring_gai", "section-a-part-5-dual-occupancy"): [
        ("intro",  "Introduction",                          1,  3),
        ("5a_1",   "Local Character and Streetscape",       4,  6),
        ("5a_2",   "Site Layout",                           7,  7),
        ("5a_3",   "Building Setbacks",                     8, 17),
        ("5a_4",   "Built-Upon Area",                      18, 19),
        ("5a_5",   "Landscaping",                          20, 23),
        ("5b_1",   "Vehicle Access",                       24, 26),
        ("5b_2",   "Car Parking Provision",                27, 27),
        ("5b_3",   "Carports and Garages",                 28, 31),
        ("5c_1",   "Building Envelopes",                   32, 33),
        ("5c_2",   "Building Facades",                     34, 36),
        ("5c_3",   "Dwelling Design and Layout",           37, 38),
        ("5c_4",   "Private Open Space",                   39, 39),
        ("5c_5",   "Solar Access",                         40, 40),
        ("5c_6",   "Natural Ventilation",                  41, 41),
        ("5c_7",   "Ancillary Facilities",                 42, 45),
        ("5c_8",   "Fencing",                              46, 47),
        ("5c_9",   "Waste Management",                     48, 48),
        ("5c_10",  "Materials and Finishes",               49, 50),
    ],
    ("ku_ring_gai", "section-a-part-7-residential-flat-buildings"): [
        ("intro",  "Introduction",                          1,  4),
        ("7a",     "Site Design",                           5,  5),
        ("7a_1",   "Local Character and Streetscape",       6,  7),
        ("7a_2",   "Site Layout",                           8,  9),
        ("7a_3",   "Building Setbacks",                    10, 13),
        ("7a_4",   "Building Separation",                  14, 14),
        ("7a_5",   "Site Coverage",                        15, 15),
        ("7a_6",   "Deep Soil Landscaping",                16, 19),
        ("7b_1",   "Car Parking Provision",                20, 21),
        ("7b_2",   "Bicycle Parking Provision",            22, 23),
        ("7c_1",   "SEPP Housing 2021 and Apartment Design Guide", 24, 24),
        ("7c_2",   "Communal Open Space",                  25, 26),
        ("7c_3",   "Ground Floor Apartments",              27, 28),
        ("7c_4",   "Apartment Mix and Accessibility",      29, 29),
        ("7c_5",   "Building Entries",                     30, 31),
        ("7c_6",   "Building Form and Facades",            32, 35),
        ("7c_7",   "Building Storeys",                     36, 36),
        ("7c_8",   "Top Storey Design and Roof Forms",     37, 37),
        ("7c_9",   "Laundry and Air Clothes Drying Facilities", 38, 38),
        ("7c_10",  "Fencing",                              39, 39),
        ("7c_11",  "Acoustic Privacy",                     40, 40),
        ("7c_12",  "Services",                             41, 41),
    ],
    ("ku_ring_gai", "section-a-part-8-mixed-use"): [
        ("intro",  "Introduction",                          1,  4),
        ("8a",     "Site Design",                           5,  5),
        ("8a_1",   "Local Character and Streetscape",       6,  7),
        ("8a_2",   "Site Layout",                           8,  9),
        ("8a_3",   "Building Setbacks",                    10, 10),
        ("8a_4",   "Building Separation",                  11, 12),
        ("8a_5",   "Wind Impact",                          13, 13),
        ("8a_6",   "Site Coverage",                        14, 14),
        ("8a_7",   "Deep Soil Landscaping",                15, 17),
        ("8b_1",   "Vehicle and Service Access and Loading Facilities", 18, 20),
        ("8b_2",   "Car Parking Provision",                21, 23),
        ("8b_3",   "Bicycle Parking and Support Facilities", 24, 25),
        ("8c_1",   "Solar Access and Daylight",            26, 27),
        ("8c_2",   "Natural Ventilation",                  28, 28),
        ("8c_3",   "Room Sizes",                           29, 30),
        ("8c_4",   "Apartment Mix and Accessibility",      31, 32),
        ("8c_5",   "Building Entries",                     33, 34),
        ("8c_6",   "Internal Common Circulation Areas",    35, 35),
        ("8c_7",   "Roof Forms and Podiums",               36, 36),
        ("8c_8",   "Communal Open Space",                  37, 38),
        ("8c_9",   "Building Facades and Articulation",    39, 43),
        ("8c_10",  "Ground Floor Commercial Uses",         44, 45),
        ("8c_11",  "Awnings",                              46, 46),
        ("8c_12",  "Colonnades",                           47, 47),
        ("8c_13",  "Internal Ceiling Heights",             48, 48),
        ("8c_14",  "Visual Privacy",                       49, 49),
        ("8c_15",  "Acoustic Privacy",                     50, 52),
        ("8c_16",  "Late Night Trading",                   53, 53),
        ("8c_17",  "External Air Clothes Drying Facilities", 54, 54),
        ("8c_18",  "Services",                             55, 55),
    ],
    ("ku_ring_gai", "section-a-part-9-non-residential"): [
        ("intro",  "Introduction",                          1,  2),
        ("9a",     "Site Design",                           3,  3),
        ("9a_1",   "Building Setbacks",                     4,  4),
        ("9a_2",   "Building Separation",                   5,  5),
        ("9a_3",   "Deep Soil Landscaping",                 6,  7),
        ("9b_1",   "Service Access and Loading Facilities",  8,  9),
        ("9b_2",   "Car Parking Provision",                10, 13),
        ("9b_3",   "Bicycle Parking Provision",            14, 15),
        ("9c_1",   "Solar Access",                         16, 16),
        ("9c_2",   "Natural Ventilation",                  17, 17),
        ("9c_3",   "Floor Depth",                          18, 18),
        ("9c_4",   "Building Entries",                     19, 20),
        ("9c_5",   "Internal Common Circulation",          21, 21),
        ("9c_6",   "Roof Forms, Terraces and Podiums",     22, 22),
        ("9c_7",   "Communal Open Space",                  23, 24),
        ("9c_8",   "Building Forms and Facades",           25, 25),
        ("9c_9",   "Corner and Landmark Building Articulation", 26, 26),
        ("9c_10",  "Ground Floor Frontage",                27, 28),
        ("9c_11",  "Awnings and Colonnades",               29, 29),
        ("9c_12",  "Internal Ceiling Heights",             30, 30),
        ("9c_13",  "Visual Privacy",                       31, 31),
        ("9c_14",  "Acoustic Privacy",                     32, 32),
        ("9c_15",  "Fencing",                              33, 33),
        ("9c_16",  "Services",                             34, 35),
    ],
    ("ku_ring_gai", "section-b-part-19-heritage"): [
        ("intro",   "Introduction",                         1,  4),
        ("19a",     "Subdivision and Site Consolidation",   5,  6),
        ("19a_2",   "Subdivision and Site Consolidation of a Heritage Item", 7, 8),
        ("19b",     "Demolition",                           9, 10),
        ("19b_2",   "Demolition Related to a Heritage Item", 11, 12),
        ("19c",     "Development within HCAs — Alterations, Additions and New Buildings", 13, 14),
        ("19c_1",   "Local Character and Streetscape",     15, 18),
        ("19c_2",   "Setbacks and Building Separation",    19, 19),
        ("19c_3",   "Gardens and Landscaping",             20, 20),
        ("19c_4",   "Access and Parking",                  21, 27),
        ("19c_6",   "Roof Forms and Structures Attached to Roofs", 28, 29),
        ("19c_7",   "Outbuildings and Garden Structures",  30, 30),
        ("19c_8",   "Fencing",                             31, 32),
        ("19c_9",   "Secondary Dwellings within HCAs",     33, 34),
        ("19d",     "Heritage Items",                      35, 36),
        ("19d_1",   "Adaptive Reuse",                      37, 37),
        ("19d_2",   "Setbacks and Building Separation",    38, 38),
        ("19d_3",   "Gardens and Landscaping",             39, 39),
        ("19d_4",   "Access and Parking",                  40, 41),
        ("19d_5",   "Building Design",                     42, 45),
        ("19d_6",   "Outbuildings and Garden Structures",  46, 46),
        ("19d_7",   "Roof Forms and Structures",           47, 47),
        ("19d_8",   "Fencing",                             48, 48),
        ("19e",     "Secondary Dwellings within HCAs and Heritage Items", 49, 50),
        ("19f",     "Development in the Vicinity of Heritage Items", 51, 59),
    ],
    ("ku_ring_gai", "section-c-part-24-water"): [
        ("intro",   "Introduction",                         1,  2),
        ("24a",     "Site Design for Water Management",     3,  3),
        ("24a_1",   "Development Type for Water Management", 4,  4),
        ("24a_2",   "Location of Development for Water Management", 5, 6),
        ("24a_3",   "Locating the Development on Site",     7, 11),
        ("24b_2",   "Stormwater Disposal from Location A and B Properties", 12, 17),
        ("24b_5",   "Stormwater Disposal from Location C and D Properties", 18, 29),
        ("24c_1",   "On-Site Stormwater Management — General", 30, 30),
        ("24c_2",   "Effective Stormwater Management Systems", 31, 32),
        ("24c_3",   "General Controls for On-Site Stormwater Management", 33, 35),
        ("24c_4",   "Mandatory Rainwater Tank",             36, 37),
        ("24c_5",   "Controls for On-Site Detention",       38, 39),
        ("24c_6",   "Stormwater Quality Control",           40, 42),
        ("24d_1",   "Existing Drainage Systems — General",  43, 43),
        ("24d_2",   "Flood Studies and Design Flood Standard", 44, 45),
        ("24d_3",   "Development Over or Adjacent to Natural Waterbody", 46, 47),
        ("24d_4",   "Development Over or Adjacent to Underground Pipeline", 48, 49),
        ("24d_5",   "Tennis Courts and Other Sporting Surfaces", 50, 50),
        ("24d_6",   "Fences",                              51, 51),
        ("24d_7",   "Swimming Pools and Spas",             52, 53),
        ("24e_1",   "Road and Trunk Drainage Design Procedures", 54, 59),
        ("24f_1",   "On-Site Wastewater Management",        60, 62),
        ("24r_1",   "Design of On-Site Detention Systems",  63, 67),
        ("24r_2",   "Design of Property and Interallotment Drainage Systems", 68, 74),
        ("24r_3",   "Flood Study Requirements",             75, 78),
        ("24r_4",   "Terms of Positive Covenants and Restrictions on Use", 79, 92),
    ],
}

# ── Within-section sub-section splitting patterns ────────────────────────────
# When a page-range section contains numbered sub-sections, these patterns
# split each section into multiple finer-grained provisions.
# Each pattern must have two capturing groups: (sub_number, sub_title).
# Patterns are applied in sequence — each splits the output of the previous level.
# Group 1 (sub_number) may be empty string for keyword-only headings (e.g. Objectives).
# Add new councils here — no other code changes required.
COUNCIL_SUBSECTION_PATTERNS: dict[str, list[re.Pattern]] = {
    # Waverley DCP 2022: two-level split.
    # Level 1: numbered sub-sections like "1.1 DEMOLITION AND CONSTRUCTION"
    # Level 2: Objectives/Controls keyword headings within each sub-section
    "waverley": [
        re.compile(r"(?m)^(\d+\.\d+)\s+([A-Z][A-Z0-9\s/&(),.-]+)$"),
        re.compile(
            r"(?m)^()(General Objectives|General Controls|Objectives|Controls"
            r"|Design Guidance|Performance Criteria)\s*$"
        ),
    ],
    # Marrickville DCP 2011: two-level split.
    # Level 1: "Objectives" / "Controls" keyword headings (standalone lines).
    # Level 2: O\d+ and C\d+ numbered markers at the start of a line.
    # Note: The Marrickville SECTION_RE also matches C\d+ as section codes, but
    # the TOC guard (5+ matches per page) fires on pages with many C-markers,
    # absorbing them into the parent section. The subsection patterns re-split
    # these accumulated controls into individual provisions.
    "marrickville": [
        re.compile(r"(?m)^()(Objectives?|Controls?)\s*$"),
        re.compile(r"(?m)^((?:O|C)\d+)\s+(.+)"),
    ],
    # Ashfield DCP 2016: two-level split.
    # Level 1: keyword headings (Performance Criteria, Design Solutions, etc.)
    # Level 2: PC/DS/O/C numbered markers within each keyword section.
    #   Heritage chapters use O1..O3 + C1..C54 (each on own line).
    #   Parking/Precinct chapters use two-column table format where PC starts
    #   the line and DS appears mid-line — splitting at line-start markers keeps
    #   each PC+DS pair together as one compliance unit.
    "ashfield": [
        re.compile(
            r"(?m)^()(Performance Criteria|Design Solutions?|Application"
            r"|Objectives?|Purpose|General Requirements)\s*$"
        ),
        re.compile(
            r"(?m)^((?:PC|DS|O|C)\d+(?:\.\d+)?)[.\s]+(.+?)$"
        ),
    ],
}


# ── Text cleanup patterns (per-council) ──────────────────────────────────────
# Lines matching any of these regexes are removed from extracted text.
# Used to filter out reversed PDF sidebar text, watermarks, etc.
COUNCIL_TEXT_CLEANUP: dict[str, list[re.Pattern]] = {
    "marrickville": [
        # Running page header: "Marrickville Development Control Plan 2011"
        # pdfplumber extracts the document title that runs across the top of every PDF page.
        re.compile(r'^Marrickville Development Control Plan'),  # document title line
        # Word cross-reference artifacts: "Error! Reference source not found."
        # Caused by broken hyperlinks in the Word source file used to produce the PDF.
        re.compile(r'Error!\s+Reference source not found'),
    ],
    "ashfield": [
        # Reversed sidebar text from rotated text boxes in Ashfield PDFs.
        # Each PDF has the chapter name reversed in a vertical sidebar.
        re.compile(r'suoenallecsiM'),      # Miscellaneous
        re.compile(r'ytilibaniatsuS'),      # Sustainability
        re.compile(r'senilediuG'),          # Guidelines
        re.compile(r'tcnicerP'),            # Precinct
        re.compile(r'niamoD'),              # Domain (Public Domain)
        re.compile(r'cilbuP'),              # Public
        re.compile(r'egatireH'),            # Heritage
        re.compile(r'dleifrebah'),          # Haberfield (case insensitive)
        re.compile(r'yrogetaC'),            # Category
        re.compile(r'tnempoleveD'),         # Development
        re.compile(r'retpahC'),             # Chapter
        re.compile(r'dleifhsA'),            # Ashfield
        re.compile(r'tseW'),               # West (in "Inner West")
        # Short reversed lines: "traP" = Part, etc.
        re.compile(r'^[a-z]{3,20}\s*$', re.MULTILINE),  # Pure lowercase-only lines (reversed words)
    ],
}


def _clean_page_text(text: str, council: str | None) -> str:
    """Remove council-specific garbage lines from extracted page text."""
    if not council or council not in COUNCIL_TEXT_CLEANUP:
        return text
    patterns = COUNCIL_TEXT_CLEANUP[council]
    lines = text.split('\n')
    cleaned = []
    for line in lines:
        if any(pat.search(line) for pat in patterns):
            continue
        cleaned.append(line)
    return '\n'.join(cleaned)


# ── Per-council column layout configs ────────────────────────────────────────
# KRG DCP 2024 has a two-column Objectives | Controls layout on many pages.
# Column boundary confirmed from PDF inspection (2026-03-14):
#   Page width: 595 (A4)
#   'Objectives' header at x0=56.7, 'Controls' header at x0=209.8 (same y)
#   Column boundary: x=195 (midpoint between ~180 and ~209)
COUNCIL_COLUMN_CONFIGS: dict[str, dict] = {
    "ku_ring_gai": {
        # Left column (Objectives): x=0–195
        # Right column (Controls):  x=195–595
        "boundary_x": 195,
        # These keyword pairs trigger column-aware extraction when found
        # at the same Y-coordinate (within 5 px) on a page
        "left_header": "Objectives",
        "right_header": "Controls",
    },
    "woollahra": {
        # Woollahra DCP 2015: per-chapter PDFs. Sections use a two-column table:
        # left column = Objectives (O1, O2...), right column = Controls (C1, C2...).
        # Column boundary confirmed from PDF inspection (2026-03-14):
        #   Page width: 595 (A4)
        #   'Objectives' header at x0≈75, 'Controls' header at x0≈290–301 (same y)
        #   Boundary: x=285 (just before Controls column starts)
        "boundary_x": 285,
        "left_header": "Objectives",
        "right_header": "Controls",
        # Woollahra's two-column layout ONLY appears on pages that explicitly have
        # the Objectives/Controls header row. Pages without that header are single-column
        # (intro text, figure pages etc.). Do NOT apply the continuation-page split.
        "no_continuation": True,
    },
}

# Per-council SECTION_RE overrides.
# KRG section headings always have dotted notation (e.g., "12.1 Signage Design").
# Bare integers like "1 To ensure..." are objective/control item lines, not section
# headings — the default SECTION_RE matches them as sections after column splitting.
COUNCIL_SECTION_RE_OVERRIDES: dict[str, re.Pattern] = {
    "ku_ring_gai": re.compile(
        r'^([A-Z]?\d+\.\d+(?:\.\d+)*)\s+([A-Z][^\n]+)$', re.MULTILINE
    ),
    # Marrickville DCP 2011: every PDF page starts with a running header that includes
    # the page number followed by the section title fragment, e.g.:
    #   "1\nDevelopment\nApplication\nGuidelines"
    # The default SECTION_RE matches "1 Development" (when text is joined) as a section
    # heading, creating false sections with bare integer numbers.
    # Marrickville's real section headings are either:
    #   - Dotted decimal: "2.1 Urban Design", "8.2.3.9 Some title"
    #   - Letter-prefixed: "C8 Some control", "O9 Some objective"
    # Override to require at least one dot OR a letter prefix, preventing page-number
    # artifacts from being extracted as sections.
    "marrickville": re.compile(
        r'^([A-Z]\d+(?:\.\d+)*|\d+(?:\.\d+)+)\s+([A-Z][^\n]+)$', re.MULTILINE
    ),
    # Woollahra DCP 2015: section codes are letter + digit + dot + digit(s), e.g.
    # "B3.1 Introduction", "B3.2.3 Side setbacks", "E1.4 Parking rates".
    # Single-letter-digit codes like O1, O2, C1, C2 are objective/control item labels
    # within the two-column table — NOT section headings.
    # Breadcrumb text "3.2.3 Side setbacks" (digit-only dotted codes from the breadcrumb
    # header) must also be excluded from section detection.
    # Override: require letter + digit + at least one dotted segment (e.g. B3.1, B3.2.3).
    "woollahra": re.compile(
        r'^([A-Z]\d+\.\d[\d.]*)\s+([A-Z][^\n]+)$', re.MULTILINE
    ),
}


# Matches a line that starts with a section code (e.g. "2.1", "2.2 Public Domain",
# "B3", "O9").  Used in the heading-continuation look-ahead to stop appending
# lines once a new section code is detected following the matched heading.
_STANDALONE_SECTION_CODE_RE = re.compile(
    r'^([A-Z]?\d+(?:\.\d+)+)\b'   # e.g. "2.1", "2.2 Public Domain", "4.1.3"
    r'|^([A-Z]\d+(?:\.\d+)*)\b'   # e.g. "B3", "O9", "C1.2"
)


# Councils whose PDFs contain rotated figure/diagram labels (sidebar labels,
# figure callouts, diagram text) that pdfplumber extracts as reversed or
# garbled characters. Filtering to upright-only chars removes them.
UPRIGHT_ONLY_COUNCILS = {"ku_ring_gai"}


# ── TOC-driven extraction ────────────────────────────────────────────────────
# Some chapters (heritage conservation areas with margin watermarks, mixed
# numbering conventions) defeat body-heading detection — the section codes are
# corrupted by interleaved sidebar text, or the council's SECTION_RE override
# doesn't fit this chapter's numbering. For these, the chapter's own table of
# contents is the authoritative section list, lives away from the body noise, and
# carries clean codes. We parse it, locate each code in the body, and extract by
# those page ranges (reusing extract_by_page_ranges + COUNCIL_SUBSECTION_PATTERNS).
#
# Gated to councils known to need it, AND only applied when sequential detection
# clearly disagrees with the TOC — so working chapters keep sequential extraction.
TOC_DRIVEN_COUNCILS = {"woollahra", "leichhardt"}

# A TOC line: section code, title, then dotted leaders / spacing, then a page number.
_TOC_LINE_RE = re.compile(r'^\s*([A-Z]?\d+(?:\.\d+)*)\s+(.+?)[.\s]{2,}\d{1,3}\s*$')


def parse_toc_entries(page_texts: list[str], max_scan: int = 12) -> list[tuple[str, str]]:
    """Parse a chapter's table of contents into an ordered, de-duplicated list of
    (section_code, title). Pure — operates on already-extracted page texts. Only
    the first ``max_scan`` pages are scanned (the TOC sits at the front)."""
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for txt in page_texts[:max_scan]:
        for line in txt.split("\n"):
            m = _TOC_LINE_RE.match(line.strip())
            if not m:
                continue
            code = m.group(1)
            title = re.sub(r"\s{2,}", " ", m.group(2)).strip()
            title = re.sub(r"[.\s]+$", "", title)   # trailing dotted-leader remnants
            if code and title and code not in seen:
                seen.add(code)
                out.append((code, title))
    return out


def _toc_page_indexes(page_texts: list[str], min_lines: int = 3) -> list[int]:
    """Indexes of pages that look like a TOC (>= min_lines TOC-style lines), so the
    body search starts AFTER them rather than matching codes on the TOC page itself."""
    idxs = []
    for i, txt in enumerate(page_texts):
        n = sum(1 for ln in txt.split("\n") if _TOC_LINE_RE.match(ln.strip()))
        if n >= min_lines:
            idxs.append(i)
    return idxs


def dedupe_ascending(located: list[tuple[str, str, int]]) -> list[tuple[str, str, int]]:
    """Keep only entries whose body page is non-decreasing in document order. Pure."""
    out: list[tuple[str, str, int]] = []
    last = 0
    for code, title, page in located:
        if page >= last:
            out.append((code, title, page))
            last = page
    return out


def build_toc_ranges(
    located: list[tuple[str, str, int]], total_pages: int
) -> list[tuple[str, str, int, int]]:
    """Turn located (code, title, start_page) entries into contiguous
    (code, title, start_page, end_page) ranges for extract_by_page_ranges. Pure."""
    ranges: list[tuple[str, str, int, int]] = []
    for i, (code, title, sp) in enumerate(located):
        ep = located[i + 1][2] - 1 if i + 1 < len(located) else total_pages
        ranges.append((code, title, sp, max(ep, sp)))
    return ranges


def toc_disagrees_with_sequential(
    sequential_codes: list[str], toc_codes: list[str],
    min_count_ratio: float = 0.6, min_overlap_ratio: float = 0.6,
) -> bool:
    """Decide whether to override sequential extraction with the TOC. True when the
    sequential result clearly doesn't match the TOC — too few sections, OR the codes
    it found are mostly absent from the TOC (the Leichhardt control-label case). Pure."""
    toc_set = {c for c in toc_codes}
    if len(toc_set) < 3:
        return False
    seq_set = {c for c in sequential_codes if c != "preamble"}
    if not seq_set:
        return True  # nothing real detected -> TOC wins
    if len(seq_set) < min_count_ratio * len(toc_set):
        return True
    overlap = len(seq_set & toc_set)
    if overlap < min_overlap_ratio * len(seq_set):
        return True
    return False


# ── Provision diff helpers ───────────────────────────────────────────────────

def _normalize_for_diff(text: str) -> str:
    """
    Normalize provision text for comparison only — collapses formatting
    differences that don't represent content changes (whitespace, unicode
    variants). Never used for storage.
    """
    if not text:
        return ""
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _extract_numbers(text: str) -> list[str]:
    """Extract all numeric values (with optional units) from provision text."""
    return re.findall(
        r'\b\d+(?:\.\d+)?(?:\s*m\b|\s*mm\b|\s*%|\s*sqm\b|\s*ha\b)?', text
    )


def _upright_only(page: Any) -> Any:
    """Return a pdfplumber page filtered to only upright characters.

    Rotated characters (sideways sidebar labels, reversed figure callouts)
    have upright=False in pdfplumber's character dict. Filtering them out
    prevents garbled text like 'htaptoof teerts' (reversed 'footpath streets')
    from appearing in extracted provision content.
    """
    return page.filter(
        lambda obj: obj.get("upright", True) if obj.get("object_type") == "char" else True
    )


def _extract_page_text(page: Any, council: str | None) -> str:
    """
    Extract text from a PDF page, handling two-column layouts for councils
    that use side-by-side Objectives | Controls structure.

    For councils with a column config: detects the two-column header pair
    at the same Y-coordinate and crops the page into left/right halves.
    Extracts each column top-to-bottom, then concatenates left + right so
    the full Objectives text precedes the full Controls text.

    Falls back to plain extract_text() for pages without two-column layout
    and for all other councils.

    For councils in UPRIGHT_ONLY_COUNCILS: filters to upright characters
    before extraction to remove rotated sidebar labels and figure callouts.
    """
    if council in UPRIGHT_ONLY_COUNCILS:
        page = _upright_only(page)

    if not council or council not in COUNCIL_COLUMN_CONFIGS:
        return page.extract_text() or ""

    cfg = COUNCIL_COLUMN_CONFIGS[council]
    left_hdr = cfg["left_header"]
    right_hdr = cfg["right_header"]

    # Check if this page has the two-column layout by looking for the
    # header pair (e.g. "Objectives" and "Controls") at the same Y level.
    words = page.extract_words()
    left_words  = [w for w in words if w["text"] == left_hdr]
    right_words = [w for w in words if w["text"] == right_hdr]

    # Find matching header pairs at the same Y level (within 5 px).
    # Track both the top and bottom of each matched pair so we can crop
    # the column content to START below the header labels (not at their top).
    matching_pairs: list[tuple[float, float]] = []  # (top, bottom) of header pair
    for lw in left_words:
        for rw in right_words:
            if abs(lw["top"] - rw["top"]) < 5:
                pair_top = min(lw["top"], rw["top"])
                pair_bottom = max(lw["bottom"], rw["bottom"])
                matching_pairs.append((pair_top, pair_bottom))

    if not matching_pairs:
        # Check if this is a continuation two-column page (content spans two
        # columns but the "Objectives"/"Controls" headers don't repeat).
        # Skip this check for councils where two-column layout is ONLY on pages
        # that explicitly carry the Objectives/Controls header row.
        if cfg.get("no_continuation"):
            return page.extract_text() or ""
        bx = cfg["boundary_x"]
        right_col_words = [w for w in words if w["x0"] >= bx]
        if len(right_col_words) >= 3:
            left_text  = page.crop((0, 0, bx,         page.height)).extract_text() or ""
            right_text = page.crop((bx, 0, page.width, page.height)).extract_text() or ""
            parts = [t.strip() for t in [left_text, right_text] if t.strip()]
            return "\n\n".join(parts)
        return page.extract_text() or ""

    # Split Y: full-width content above the column headers, two-column below.
    # Use pair_top for the header_text upper crop (excludes headers themselves).
    # Use pair_bottom to start column crops so header labels are dropped entirely.
    split_y = min(p[0] for p in matching_pairs)        # top of topmost header pair
    col_start_y = min(p[1] for p in matching_pairs)    # bottom of topmost header pair
    bx = cfg["boundary_x"]

    # Full-width section heading area (strictly above the column headers).
    # Subtract 0.5px so pdfplumber's inclusive boundary doesn't pull in
    # the "Objectives"/"Controls" words that sit exactly at split_y.
    header_text = page.crop((0, 0, page.width, split_y - 0.5)).extract_text() or ""

    # Two-column content area (below the Objectives/Controls header labels)
    left_text  = page.crop((0,   col_start_y, bx,         page.height)).extract_text() or ""
    right_text = page.crop((bx,  col_start_y, page.width, page.height)).extract_text() or ""

    # Format: heading first, then left (Objectives), then right (Controls)
    parts = [t.strip() for t in [header_text, left_text, right_text] if t.strip()]
    return "\n\n".join(parts)


# ── PDF Extraction ──────────────────────────────────────────────────────────

class DCPExtractor:
    """Extract provisions from a single DCP chapter PDF using pdfplumber."""

    # Matches section numbers like "4.1.5", "2", "B1", or "C1.2" followed by a Title-cased heading.
    # [A-Z]? makes the letter prefix optional so both numeric-only and letter-prefixed
    # section codes (e.g. Waverley's "B1 WASTE", "C1 Low Density") are matched.
    SECTION_RE = re.compile(r'^([A-Z]?\d+(?:\.\d+)*)\s+([A-Z][^\n]+)$', re.MULTILINE)

    def __init__(self, pdf_path: Path, document_id: str, council: str | None = None):
        self.pdf_path = pdf_path
        self.document_id = document_id
        self.council = council
        self.page_count: int = 0

    def extract(self) -> list[dict[str, Any]]:
        """Top-level extraction: sequential body-heading detection, with a
        TOC-driven override for configured councils whose body headings are
        unreliable. The override only fires when sequential detection clearly
        disagrees with the chapter's table of contents, so well-behaved chapters
        (even within those councils) keep the sequential result.

        When AI_EXTRACTION=1, all of the above is bypassed in favour of an LLM
        document extractor that reads any layout with no per-council config
        (ce-ai-extraction-decision-2026-07). The result is the same section-dict
        shape, so the downstream diff/enqueue/guard pipeline is unchanged."""
        if os.getenv("AI_EXTRACTION", "").strip().lower() in ("1", "true", "yes"):
            from scripts.ai_extractor import ai_extract_chapter
            return ai_extract_chapter(self.pdf_path, self.council)
        sections = self._extract_sequential()
        if self.council in TOC_DRIVEN_COUNCILS:
            override = self._maybe_toc_override(sections)
            if override is not None:
                return override
        return sections

    def _maybe_toc_override(
        self, sequential: list[dict[str, Any]]
    ) -> list[dict[str, Any]] | None:
        """Return a TOC-driven section list when it should replace the sequential
        result, else None. Reads the chapter's own TOC for the authoritative section
        list, locates each code in the body (after the TOC pages), and extracts by
        those page ranges."""
        with pdfplumber.open(self.pdf_path) as pdf:
            total = len(pdf.pages)
            page_texts = [
                _clean_page_text(_extract_page_text(p, self.council), self.council)
                for p in pdf.pages
            ]
        entries = parse_toc_entries(page_texts)
        seq_codes = [(s.get("section_number") or "") for s in sequential]
        if not toc_disagrees_with_sequential(seq_codes, [c for c, _ in entries]):
            return None

        body_start = (max(_toc_page_indexes(page_texts)) + 1) if _toc_page_indexes(page_texts) else 0
        located: list[tuple[str, str, int]] = []
        for code, title in entries:
            pat = re.compile(r"(?m)^\s*" + re.escape(code) + r"(?:\b|\s)")
            for i in range(body_start, total):
                if pat.search(page_texts[i]):
                    located.append((code, title, i + 1))
                    break
        located = dedupe_ascending(located)
        if len(located) < 3:
            return None
        ranges = build_toc_ranges(located, total)
        subpats = COUNCIL_SUBSECTION_PATTERNS.get(self.council)
        toc_sections = self.extract_by_page_ranges(ranges, subpats)
        print(f"    [TOC] overrode sequential ({len([s for s in sequential if s.get('section_number') != 'preamble'])} "
              f"sections) with TOC-driven extraction ({len(toc_sections)} sections, {len(located)} TOC anchors)")
        return toc_sections

    def _extract_sequential(self) -> list[dict[str, Any]]:
        """
        Return list of section dicts:
            section_number, section_title, content, tables, page_start, page_end, pages
        """
        sections: list[dict[str, Any]] = []
        current: dict[str, Any] | None = None

        with pdfplumber.open(self.pdf_path) as pdf:
            total = len(pdf.pages)
            self.page_count = total
            for page_num, page in enumerate(pdf.pages, start=1):
                print(f"    page {page_num}/{total}", end="\r")

                text = _extract_page_text(page, self.council)
                text = _clean_page_text(text, self.council)
                page_tables = page.extract_tables() or []

                section_re = COUNCIL_SECTION_RE_OVERRIDES.get(self.council, self.SECTION_RE)
                # TOC page guard: if the page contains 5+ section-code matches it is
                # almost certainly a chapter table-of-contents page (list of sub-sections
                # with titles). Extracting sections from a TOC page produces false sections
                # whose content is just the TOC list. Skip all section detection on these
                # pages; their text is absorbed into the current (parent) section.
                _toc_hits = len(section_re.findall(text))
                if _toc_hits >= 5:
                    match = None
                else:
                    match = section_re.search(text)
                if match:
                    new_code = match.group(1)
                    if current and (
                        current["section_number"] == new_code
                        or current["section_number"].startswith(new_code + ".")
                    ):
                        # Running page header: either the same section code, or a parent
                        # prefix (e.g. Marrickville prints "2.1 Urban Design" at the top
                        # of every page in 2.1 and its sub-sections 2.1.1.3, 2.1.2.2
                        # etc.). Don't start a new section for the parent code while
                        # already inside a child of that section.
                        match = None
                if match:
                    if current:
                        current["page_end"] = page_num - 1
                        sections.append(current)
                    title = match.group(2).strip()
                    # ── Heading continuation fix ──────────────────────────────
                    # Some PDFs (e.g. Marrickville) wrap long section titles
                    # across lines: the regex captures only the first line
                    # (e.g. "Urban" instead of "Urban Design").  Look at up to
                    # 2 lines immediately after the match end and append any
                    # that look like title continuations (not blank, not a new
                    # section code, not a bare page number).
                    _after = text[match.end():]
                    # Split on newlines; the first element is often empty because
                    # the match ends just before a '\n' — skip leading empty entries
                    # so we look at the actual lines that follow the heading.
                    _extra_lines = _after.split('\n')
                    _continuations = 0
                    _saw_first_nonempty = False
                    for _extra in _extra_lines[:10]:
                        _stripped = _extra.strip()
                        if not _stripped:
                            if _saw_first_nonempty:
                                # True blank line after content — stop
                                break
                            # Leading empty from trailing newline of match — skip
                            continue
                        _saw_first_nonempty = True
                        if _STANDALONE_SECTION_CODE_RE.match(_stripped):
                            # Looks like a new section code — stop
                            break
                        if re.match(r'^\d+$', _stripped):
                            # Bare page number — stop
                            break
                        if len(_stripped) > 50:
                            # Long line — real content, not a title continuation
                            break
                        if re.match(r'^[a-z]', _stripped):
                            # Starts with lowercase — could be a conjunction in a title
                            # (e.g. "and", "or", "of") or sentence content.
                            # Allow short conjunctions (≤5 chars) as title continuations;
                            # stop on any longer lowercase word (sentence content).
                            if len(_stripped) > 5:
                                break
                            # Short lowercase word — treat as title conjunction, continue
                        if re.match(r'^(Appendix|Part|Chapter|Section|Note|See|Where)\b', _stripped):
                            # Structural keyword — end of heading, start of appendix/note
                            break
                        if '\u2013' in _stripped or '\u2014' in _stripped or ' - ' in _stripped:
                            # En-dash or em-dash signals a descriptive sub-clause, not a title word
                            break
                        if _continuations >= 4:
                            # Cap at 4 extra lines (handles multi-word wrapped titles)
                            break
                        title = title + ' ' + _stripped
                        _continuations += 1
                    current = {
                        "section_number": match.group(1),
                        "section_title": title,
                        "content": "",
                        "tables": [],
                        "page_start": page_num,
                        "page_end": page_num,
                        "pages": [page_num],
                    }

                if current:
                    current["content"] += f"\n\n{text}"
                    if page_num not in current["pages"]:
                        current["pages"].append(page_num)
                    for tbl in page_tables:
                        html = self._table_to_html(tbl)
                        if html:
                            current["tables"].append({"html": html, "page": page_num})
                else:
                    # Pre-section preamble (TOC, cover, etc.)
                    if not sections or sections[-1].get("section_number") != "preamble":
                        sections.append({
                            "section_number": "preamble",
                            "section_title": "Document Information",
                            "content": text,
                            "tables": [],
                            "page_start": page_num,
                            "page_end": page_num,
                            "pages": [page_num],
                        })
                    else:
                        sections[-1]["content"] += f"\n\n{text}"
                        sections[-1]["page_end"] = page_num
                        if page_num not in sections[-1]["pages"]:
                            sections[-1]["pages"].append(page_num)

            if current:
                current["page_end"] = total
                sections.append(current)

        print()  # clear progress line
        return sections

    def extract_by_page_ranges(
        self,
        ranges: list[tuple[str, str, int, int]],
        subsection_patterns: list[re.Pattern] | None = None,
    ) -> list[dict[str, Any]]:
        """
        Extract sections using explicit page-range config.
        Used when SECTION_RE cannot detect chapter boundaries (e.g. multi-line headers).

        Args:
            ranges:               list of (section_key, title, page_start, page_end) — 1-indexed
            subsection_patterns:  optional list of regexes (two groups: sub_num, sub_title).
                                  Applied in sequence — each pattern splits the output of
                                  the previous level, enabling multi-level granularity.
                                  Group 1 (sub_num) may be empty for keyword-only headings.
                                  Configured per-council in COUNCIL_SUBSECTION_PATTERNS.
        """
        sections: list[dict[str, Any]] = []
        with pdfplumber.open(self.pdf_path) as pdf:
            self.page_count = len(pdf.pages)
            for section_key, title, page_start, page_end in ranges:
                content = ""
                tables: list[dict] = []
                pages_included: list[int] = []
                clipped_end = min(page_end, self.page_count)
                for page_num in range(page_start, clipped_end + 1):
                    page = pdf.pages[page_num - 1]
                    text = _extract_page_text(page, self.council)
                    text = _clean_page_text(text, self.council)
                    content += f"\n\n{text}"
                    pages_included.append(page_num)
                    for tbl in page.extract_tables() or []:
                        html = self._table_to_html(tbl)
                        if html:
                            tables.append({"html": html, "page": page_num})

                if subsection_patterns:
                    # First pattern splits the raw page-range content
                    sub_secs = split_content_at_subsections(
                        content, section_key, title, page_start, clipped_end,
                        tables, subsection_patterns[0],
                    )
                    # Subsequent patterns split each result of the previous level.
                    # Non-actionable sections (intro/objectives) are still passed
                    # to deeper levels — they may contain sub-markers (e.g. Heritage
                    # O/C markers inside an "Objectives" section) that need splitting.
                    # Each sub-provision gets its own actionability assessment.
                    for pattern in subsection_patterns[1:]:
                        further_split: list[dict[str, Any]] = []
                        for sec in sub_secs:
                            further = split_content_at_subsections(
                                sec["content"],
                                sec["section_number"],
                                sec["section_title"],
                                sec["page_start"],
                                sec["page_end"],
                                sec["tables"],
                                pattern,
                                parent_text_heading=sec.get("text_heading"),
                            )
                            further_split.extend(further)
                        sub_secs = further_split
                    sections.extend(sub_secs)
                else:
                    sections.append({
                        "section_number": section_key,
                        "section_title":  title,
                        "content":        content,
                        "tables":         tables,
                        "page_start":     page_start,
                        "page_end":       clipped_end,
                        "pages":          pages_included,
                    })
        print()
        return sections

    def _table_to_html(self, table_data: list[list[str | None]]) -> str:
        """Convert pdfplumber table data to clean HTML."""
        if not table_data or len(table_data) < 2:
            return ""

        html = "<table>\n"
        first_row = table_data[0]
        is_header = all(
            cell and len(str(cell).strip()) < 50
            for cell in first_row
            if cell
        )

        if is_header:
            html += "<thead>\n<tr>\n"
            for cell in first_row:
                html += f"  <th>{(cell or '').strip()}</th>\n"
            html += "</tr>\n</thead>\n<tbody>\n"
            data_rows = table_data[1:]
        else:
            html += "<tbody>\n"
            data_rows = table_data

        for row in data_rows:
            html += "<tr>\n"
            for cell in row:
                html += f"  <td>{(cell or '').strip()}</td>\n"
            html += "</tr>\n"

        html += "</tbody>\n</table>"
        return html

    @staticmethod
    def clean_content(content: str) -> str:
        content = re.sub(r'\n{3,}', '\n\n', content)
        content = re.sub(r'\nPage \d+\n', '\n', content)
        content = re.sub(r'[ \t]+', ' ', content)
        return content.strip()


_TOC_DOTTED_LEADER_RE = re.compile(r'\.{5,}')


def _strip_toc_lines(content: str) -> str:
    """
    Remove TOC dotted-leader lines from provision content.

    When a DCP chapter starts with an in-chapter Table of Contents page
    (e.g. "2.3 Site and Context Analysis ......... 1"), pdfplumber extracts
    those lines as provision content.  This function removes every line that
    contains 5 or more consecutive dots (the dotted leader pattern), leaving
    only the substantive provision text.

    Triggered only when more than 3 such lines are present in the content block
    (a single dotted line could be a legitimate ellipsis or divider).
    """
    lines = content.split('\n')
    dotted = [l for l in lines if _TOC_DOTTED_LEADER_RE.search(l)]
    if len(dotted) <= 3:
        return content
    cleaned = [l for l in lines if not _TOC_DOTTED_LEADER_RE.search(l)]
    return '\n'.join(cleaned)


_TOC_TITLE_CLEANUP_RE = re.compile(r'\s*\.{5,}.*$')


def _clean_toc_title(title: str) -> str:
    """Strip dotted leaders and trailing page numbers from a section title.

    Titles that were matched from a TOC line (e.g. "Urban Design ......... 1")
    need the dotted leader and trailing page number removed so the heading in
    the provision text is clean (e.g. "Urban Design").
    """
    return _TOC_TITLE_CLEANUP_RE.sub('', title).strip()


def build_provision_text(section: dict[str, Any]) -> str:
    content = DCPExtractor.clean_content(section["content"])
    content = _strip_toc_lines(content)
    if section["section_number"] != "preamble":
        # text_heading overrides the default heading so sub-section provisions start
        # with the parent code (e.g. "B1 Waste —") which the LayerTopicTagger needs
        # to extract the correct section code via progressive prefix stripping.
        raw_title = section.get("text_heading") or f"{section['section_number']} {section['section_title']}"
        heading = _clean_toc_title(raw_title)
        full_text = f"# {heading}\n\n{content}"
    else:
        full_text = content
    if section["tables"]:
        full_text += "\n\n---\n\n"
        for j, tbl in enumerate(section["tables"]):
            full_text += f"\n\n**Table {j + 1}** (Page {tbl['page']})\n\n{tbl['html']}\n\n"
    return full_text


def build_ref_number(document_id: str, section_number: str) -> str:
    if section_number == "preamble":
        return f"{document_id}__preamble"
    return f"{document_id}__{section_number.replace('.', '_')}"


def split_content_at_subsections(
    content: str,
    parent_key: str,
    parent_title: str,
    page_start: int,
    page_end: int,
    tables: list,
    pattern: re.Pattern,
    parent_text_heading: str | None = None,
) -> list[dict[str, Any]]:
    """
    Split a page-range section into finer-grained sub-section provisions.

    Each match of `pattern` (two groups: sub_number, sub_title) becomes its own
    provision.  Text before the first match becomes the intro provision if non-empty.
    All sub-provisions inherit page_start — intra-section page boundaries are not
    tracked at extraction time.

    Group 1 (sub_number) may be an empty string for keyword-only headings such as
    "Objectives" or "Controls" — in that case the sub_title is used for the key slug.

    parent_text_heading: when set (second-level splits), carries the heading built
    by the first-level split so deep provisions chain correctly, e.g.:
        "B1 Waste — 1.1 Demolition And Construction — Controls"

    Returns a single-element list (the original section dict) when the pattern finds
    no matches, so callers can safely call this unconditionally for every page range.
    """
    # Keyword headings that are aspirational/descriptive only — not actionable controls
    NON_ACTIONABLE_KEYWORDS = {"Objectives", "General Objectives"}

    matches = list(pattern.finditer(content))
    if not matches:
        # No split found — pass through parent's actionability (default True)
        return [{
            "section_number":   parent_key,
            "section_title":    parent_title,
            "content":          content,
            "tables":           tables,
            "page_start":       page_start,
            "page_end":         page_end,
            "pages":            [],
            **({"text_heading": parent_text_heading} if parent_text_heading else {}),
        }]

    result: list[dict[str, Any]] = []

    # Intro provision: context/description text before the first sub-heading — never actionable
    intro_text = content[:matches[0].start()].strip()
    if intro_text:
        result.append({
            "section_number":   parent_key,
            "section_title":    parent_title,
            "content":          intro_text,
            "tables":           tables,   # All tables stay with the intro provision
            "page_start":       page_start,
            "page_end":         page_end,
            "pages":            [],
            "v2_is_actionable": False,
            **({"text_heading": parent_text_heading} if parent_text_heading else {}),
        })

    # Base heading for building child headings (chains across split levels)
    base_heading = parent_text_heading or f"{parent_key} {parent_title}"

    for i, match in enumerate(matches):
        sub_num   = match.group(1)          # e.g. "1.1" or "" for Objectives/Controls
        sub_title = match.group(2).strip()  # e.g. "DEMOLITION AND CONSTRUCTION"
        end  = matches[i + 1].start() if i + 1 < len(matches) else len(content)
        body = content[match.end():end].strip()

        # Unique key: numbered sub-sections use dots→underscores ("B1_1_1"),
        # keyword headings use slugified title ("B1_1_1_objectives").
        if sub_num:
            sub_key = f"{parent_key}_{sub_num.replace('.', '_')}"
            text_heading = f"{base_heading} \u2014 {sub_num} {sub_title.title()}"
        else:
            sub_key = f"{parent_key}_{sub_title.lower().replace(' ', '_')}"
            text_heading = f"{base_heading} \u2014 {sub_title.title()}"

        # Objectives (and any other non-actionable keywords) are descriptive goals,
        # not controls — mark them non-actionable.
        is_actionable = sub_title not in NON_ACTIONABLE_KEYWORDS

        result.append({
            "section_number":   sub_key,
            "section_title":    f"{parent_title} \u2014 {sub_title.title()}",
            "content":          body,
            "tables":           [],
            "page_start":       page_start,
            "page_end":         page_end,
            "pages":            [],
            "text_heading":     text_heading,
            "v2_is_actionable": is_actionable,
        })

    return result


# ── Database helpers ────────────────────────────────────────────────────────

def resolve_document_id(cur, council: str, chapter_key: str, dcp_name: str) -> str:
    """
    Try to find an existing document_id used by provisions from this chapter.
    Fall back to constructing one from dcp_name + chapter_key.
    """
    cur.execute(
        """
        SELECT DISTINCT document_id
        FROM regulatory_provisions
        WHERE source_council = %s
          AND source_chapter_key = %s
          AND document_id IS NOT NULL
        LIMIT 1
        """,
        (council, chapter_key),
    )
    row = cur.fetchone()
    if row:
        return row[0]

    # Construct: 'Marrickville DCP 2011' + 'part2-s10-parking'
    # → 'Marrickville_DCP_2011__part2_s10_parking'
    base = re.sub(r'\s+', '_', dcp_name.strip())
    chapter_slug = chapter_key.replace('-', '_')
    return f"{base}__{chapter_slug}"


# prior-art-checked: reuse not viable because this EXTENDS this file's own
# fetch_pending_chapters/diff_provisions detector (the only DCP provision-diff in the
# repo); the guard's matches (shadow_detector, transport_proximity_detector) are
# unrelated satellite products sharing only generic words.
def _pending_chapters_sql(council_filter: str | None, all_chapters: bool = False,
                          chapter_filter: str | None = None) -> tuple[str, list]:
    """Build the chapter-selection query (pure, testable).

    all_chapters=False (default): the legacy reactive trigger — only chapters the
    byte-change monitor flagged (needs_extraction=TRUE).

    all_chapters=True: re-extract EVERY active TEXT-DCP chapter and diff vs the
    approved baseline — the scheduled re-extract-all cadence. Robust to PDF re-exports
    that the needs_extraction byte-signal false-positives on (plan
    ce-dcp-targeted-semantic-detection-2026-06). is_active + r2_current_path always required.
    In this mode the chapter must ALSO already have current provisions, so the
    quarterly run only re-checks real text DCPs and skips spatial/map "chapters"
    (e.g. city_of_sydney's sheet-NNN-*-map rows) that carry an r2_current_path but no
    extractable text and would 404 / extract empty every run. First extractions (no
    provisions yet) are handled by the reactive needs_extraction path, which keeps no
    such filter.
    """
    conds = ["is_active = TRUE", "r2_current_path IS NOT NULL"]
    if not all_chapters:
        conds.insert(0, "needs_extraction = TRUE")
    else:
        conds.append(
            "EXISTS (SELECT 1 FROM regulatory_provisions rp "
            "WHERE rp.source_council = dcp_chapter_registry.council "
            "AND rp.source_chapter_key = dcp_chapter_registry.chapter_key "
            "AND rp.is_current = TRUE)"
        )
    params: list = []
    if council_filter:
        conds.append("council = %s")
        params.append(council_filter)
    # prior-art-checked: reuse not viable because this is this module's own DCP chapter
    # registry query builder; the flagged matches are unrelated frontend provision-display
    # components. Adding a single-chapter filter to enable a targeted re-extraction.
    if chapter_filter:
        conds.append("chapter_key = %s")
        params.append(chapter_filter)
    query = (
        "SELECT id, council, chapter_key, chapter_label, "
        "r2_current_path, r2_version_label, dcp_name, content_hash "
        "FROM dcp_chapter_registry WHERE " + " AND ".join(conds)
        + " ORDER BY council, sort_order"
    )
    return query, params


def fetch_pending_chapters(cur, council_filter: str | None, all_chapters: bool = False,
                           chapter_filter: str | None = None) -> list[dict]:
    query, params = _pending_chapters_sql(council_filter, all_chapters, chapter_filter)
    cur.execute(query, params)
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


# ── Provision diff ──────────────────────────────────────────────────────────

# Count-drop fail-loud guard (false-negative tail). A re-extraction that yields
# far fewer provisions than the approved baseline is almost always a broken parse,
# truncated/scanned PDF, or partial fetch — NOT a genuine amendment. The commit
# path already ABORTs on this (see the provision-count gate in extract_chapter),
# but on the unattended quarterly --all --review run such a chapter would otherwise
# be enqueued as an ordinary large diff a human might rubber-stamp. is_count_drop
# makes it a first-class 'count_drop' status so the review run flags it loudly and
# the commit path can never full-replace (wipe) on it.
#
# Thresholds mirror the existing extract_chapter count gate (prev_count > 20 and
# new_count < 75% of prev_count). total_new == 0 is intentionally EXCLUDED — a
# genuine spatial/map chapter legitimately extracts no text and is classified
# 'map_change'; count_drop is specifically "extracted SOME, but far too few".
COUNT_DROP_MIN_BASELINE = 20
COUNT_DROP_RATIO = 0.75


def is_count_drop(total_old: int, total_new: int) -> bool:
    """True when a re-extraction lost a suspicious share of provisions.

    Guards the false-negative tail: total_old must be a meaningful baseline
    (> COUNT_DROP_MIN_BASELINE) and total_new must be > 0 (zero = map_change,
    handled separately) but below COUNT_DROP_RATIO of the baseline.
    """
    if total_old <= COUNT_DROP_MIN_BASELINE:
        return False
    if total_new <= 0:
        return False
    return total_new < total_old * COUNT_DROP_RATIO


# Schema gate (false-negative tail, complements count_drop). A re-extraction can
# have the right provision COUNT but garbage CONTENT — equation-editor noise, Word
# cross-reference errors, table-of-contents leaders, or two-column merge. These are
# unambiguous extraction-FAILURE signatures: they appear at ~0% in a clean extract,
# so gating on them is high-precision and won't cry wolf on benign formatting quirks
# (bare page numbers, hash headers, short provisions — deliberately EXCLUDED).
SERIOUS_ARTIFACT_LABELS = frozenset({
    "latex_tokens",
    "word_cross_references",
    "toc_dotted_leaders",
    "two_col_interleave",
    "two_col_numeric",
})
SCHEMA_FAIL_MIN_PROVISIONS = 10
SCHEMA_FAIL_RATIO = 0.10


def is_schema_fail(total_provisions: int, serious_flagged: int) -> bool:
    """True when too many provisions carry a serious extraction-failure artifact.

    Conservative by design (min provisions floor + >10% ratio) because serious
    artifacts are ~0% in a clean extraction, so this stays high-precision and does
    not re-introduce the cry-wolf problem the detector cadence was built to fix.
    """
    if total_provisions < SCHEMA_FAIL_MIN_PROVISIONS:
        return False
    if total_provisions <= 0:
        return False
    return serious_flagged / total_provisions > SCHEMA_FAIL_RATIO


def suspect_reason(review_data: dict) -> str | None:
    """Return a short SUSPECT reason for a review chapter, or None if it looks fine.

    A chapter is suspect when its diff flagged a count_drop, its extraction failed
    the schema gate, OR (AI path) it dropped TOC sections / truncated provisions.
    Pure — drives both the operator summary and the alert.
    """
    diff = review_data.get("diff") or {}
    if diff.get("status") == "count_drop":
        return (f"count_drop ({diff.get('total_new')} extracted vs "
                f"{diff.get('total_old')} baseline)")
    if review_data.get("schema_fail"):
        return (f"schema_fail ({review_data.get('serious_artifact_provisions')}/"
                f"{review_data.get('total_provisions')} provisions with serious artifacts)")
    if review_data.get("coverage_fail"):
        return (f"coverage_fail ({review_data.get('coverage_missing')}/"
                f"{review_data.get('coverage_toc')} TOC sections missing)")
    if review_data.get("truncation_fail"):
        return (f"truncation_fail ({review_data.get('truncation_flagged')}/"
                f"{review_data.get('total_provisions')} provisions truncated)")
    return None


def build_suspect_alert(council: str, suspect: list[dict]) -> str | None:
    """Format a Telegram alert body for SUSPECT chapters, or None if none.

    Pure (no I/O) so it is unit-testable; the thin sender wraps it.
    """
    lines = [(s.get("council"), s.get("chapter_key"), suspect_reason(s)) for s in suspect]
    lines = [(c, k, r) for c, k, r in lines if r]
    if not lines:
        return None
    body = [f"🚨 DCP extract: {len(lines)} SUSPECT chapter(s) for '{council}' — review before approving:"]
    for c, k, r in lines:
        body.append(f"• [{c}] {k}: {r}")
    body.append("These are likely broken extractions, not amendments. Check the source PDF.")
    return "\n".join(body)


def diff_provisions(
    new_sections: list[dict],
    council: str,
    chapter_key: str,
    document_id: str,
    cur,
) -> dict:
    """
    Compare newly extracted provisions against current DB provisions.

    Returns:
        {
          "status": "ok" | "count_drop" | "restructure" | "regeneration_artifact" | "map_change",
          "changed": [...],    # {ref_number, old_text, new_text, has_numeric_change, old_page, new_page}
          "added": [...],      # {ref_number, new_text, new_page}
          "removed": [...],    # {ref_number, old_text}
          "renumbered": [...], # {old_ref_number, new_ref_number, text}
          "page_shift": int | None,
          "unchanged_count": int,
          "total_old": int,    # baseline provision count (is_current) for this chapter
          "total_new": int,    # provisions in the fresh extraction
        }
    """
    # Fetch current DB provisions for this chapter
    cur.execute(
        """
        SELECT ref_number, provision_text, pdf_page
        FROM regulatory_provisions
        WHERE source_council = %s
          AND source_chapter_key = %s
          AND is_current = TRUE
        ORDER BY pdf_page, ref_number
        """,
        (council, chapter_key),
    )
    old_provisions = {
        row[0]: {"text": row[1], "page": row[2]}
        for row in cur.fetchall()
    }

    # Build new provisions map from extracted sections
    new_provisions = {}
    for section in new_sections:
        ref = build_ref_number(document_id, section["section_number"])
        text = build_provision_text(section)
        new_provisions[ref] = {"text": text, "page": section["page_start"]}

    result: dict = {
        "status": "ok",
        "changed": [], "added": [], "removed": [],
        "renumbered": [], "page_shift": None,
        "unchanged_count": 0,
        "total_old": len(old_provisions), "total_new": len(new_provisions),
    }

    matched_old: set[str] = set()
    matched_new: set[str] = set()

    # Match by ref_number first
    for ref, new_prov in new_provisions.items():
        if ref in old_provisions:
            old_prov = old_provisions[ref]
            matched_old.add(ref)
            matched_new.add(ref)
            if _normalize_for_diff(old_prov["text"]) == _normalize_for_diff(new_prov["text"]):
                result["unchanged_count"] += 1
            else:
                old_nums = _extract_numbers(old_prov["text"] or "")
                new_nums = _extract_numbers(new_prov["text"] or "")
                result["changed"].append({
                    "ref_number": ref,
                    "old_text": old_prov["text"],
                    "new_text": new_prov["text"],
                    "has_numeric_change": old_nums != new_nums,
                    "old_page": old_prov["page"],
                    "new_page": new_prov["page"],
                })

    # Unmatched provisions — candidates for removal or renumbering
    unmatched_old = {r: old_provisions[r] for r in old_provisions if r not in matched_old}
    unmatched_new = {r: new_provisions[r] for r in new_provisions if r not in matched_new}

    # Fuzzy match unmatched — catches renumbering (>90% char similarity)
    used_old: set[str] = set()
    used_new: set[str] = set()
    for new_ref, new_prov in unmatched_new.items():
        best_old_ref = None
        best_score = 0.0
        new_norm = _normalize_for_diff(new_prov["text"] or "")
        for old_ref, old_prov in unmatched_old.items():
            if old_ref in used_old:
                continue
            old_norm = _normalize_for_diff(old_prov["text"] or "")
            shorter = min(len(new_norm), len(old_norm))
            if shorter == 0:
                continue
            sample = min(200, shorter)
            matches = sum(1 for a, b in zip(new_norm[:sample], old_norm[:sample]) if a == b)
            score = matches / sample
            if score > 0.9 and score > best_score:
                best_score = score
                best_old_ref = old_ref
        if best_old_ref:
            result["renumbered"].append({
                "old_ref_number": best_old_ref,
                "new_ref_number": new_ref,
                "text": new_prov["text"],
            })
            used_old.add(best_old_ref)
            used_new.add(new_ref)

    for old_ref, old_prov in unmatched_old.items():
        if old_ref not in used_old:
            result["removed"].append({"ref_number": old_ref, "old_text": old_prov["text"]})

    for new_ref, new_prov in unmatched_new.items():
        if new_ref not in used_new:
            result["added"].append({"ref_number": new_ref, "new_text": new_prov["text"], "new_page": new_prov["page"]})

    # Anomaly detection
    total_old = len(old_provisions)
    total_new = len(new_provisions)
    total_changes = len(result["changed"]) + len(result["added"]) + len(result["removed"])
    result["total_old"] = total_old
    result["total_new"] = total_new

    # Count-drop guard runs FIRST: a suspicious provision loss would otherwise be
    # misread as 'restructure', which on the commit path triggers a full-replace
    # (wipe). Flag it distinctly so the commit path skips and the review run alerts.
    if is_count_drop(total_old, total_new):
        result["status"] = "count_drop"
    elif total_old > 0 and total_changes / total_old > 0.5:
        # >50% of provisions changed/added/removed — wholesale restructure or extraction failure
        result["status"] = "restructure"
    elif len(result["changed"]) > 0 and len(result["changed"]) > 0.3 * total_old:
        # >30% provisions changed but each diff is tiny — Waverley-style PDF regeneration
        avg_diff = sum(
            abs(len(c["new_text"] or "") - len(c["old_text"] or ""))
            for c in result["changed"]
        ) / len(result["changed"])
        if avg_diff < 25:
            result["status"] = "regeneration_artifact"
    elif total_changes == 0 and result["unchanged_count"] == 0 and total_old > 0:
        # PDF hash changed but zero text extracted — spatial/map document
        result["status"] = "map_change"

    # Page shift: all changed provisions have the same non-zero page offset
    if result["changed"]:
        offsets = [
            c["new_page"] - c["old_page"]
            for c in result["changed"]
            if c["old_page"] is not None and c["new_page"] is not None
        ]
        if offsets and len(set(offsets)) == 1 and offsets[0] != 0:
            result["page_shift"] = offsets[0]

    return result


def _insert_provision_changes(
    cur,
    diff: dict,
    council: str,
    chapter_key: str,
    version: str,
    now: datetime,
) -> None:
    """Write provision_changes rows for all deltas in a diff result."""
    change_type_map = {
        "restructure": "restructure",
        "regeneration_artifact": "regeneration_artifact",
        "map_change": "map_change",
    }
    status_change_type = change_type_map.get(diff["status"])

    def ins(change_type, ref_number, old_text=None, new_text=None,
            old_ref=None, has_numeric=False, old_page=None, new_page=None):
        cur.execute(
            """
            INSERT INTO provision_changes (
                changed_at, council, chapter_key, dcp_version,
                ref_number, change_type,
                old_text, new_text, old_ref_number,
                has_numeric_change, old_pdf_page, new_pdf_page
            ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (now, council, chapter_key, version,
             ref_number, change_type,
             old_text, new_text, old_ref,
             has_numeric, old_page, new_page),
        )

    # For anomaly statuses write a single summary row
    if status_change_type in ("regeneration_artifact", "map_change"):
        ins(status_change_type, "_summary")
        return

    page_shift = diff.get("page_shift")

    for c in diff["changed"]:
        ct = "page_shift" if (page_shift and not c["has_numeric_change"]
                              and _normalize_for_diff(c["old_text"] or "") == _normalize_for_diff(c["new_text"] or ""))  \
             else "changed"
        ins(ct, c["ref_number"],
            old_text=c["old_text"], new_text=c["new_text"],
            has_numeric=c["has_numeric_change"],
            old_page=c["old_page"], new_page=c["new_page"])

    for a in diff["added"]:
        ins("added", a["ref_number"], new_text=a["new_text"], new_page=a.get("new_page"))

    for r in diff["removed"]:
        ins("removed", r["ref_number"], old_text=r["old_text"])

    for rn in diff["renumbered"]:
        ins("renumbered", rn["new_ref_number"],
            old_text=rn["text"], new_text=rn["text"],
            old_ref=rn["old_ref_number"])

    if status_change_type == "restructure":
        ins("restructure", "_summary")


def _auto_verify_controls(
    cur, conn, council: str, chapter_key: str,
    reason: str, *, commit: bool = True,
) -> None:
    """Auto-verify control rows when extraction confirms no value changes.

    Updates last_verified_at and clears needs_review if it was set.
    This suppresses false-alarm alerts from PDF republishes/reformats
    that don't change any numeric control values.
    """
    cur.execute(
        """
        UPDATE dcp_setback_controls
        SET needs_review    = FALSE,
            review_reason   = NULL,
            last_verified_at = NOW(),
            reviewed_at     = CASE WHEN needs_review THEN NOW() ELSE reviewed_at END
        WHERE lga               = %s
          AND source_chapter_key = %s
          AND is_current         = TRUE
        """,
        (council, chapter_key),
    )
    verified = cur.rowcount
    if verified > 0:
        print(f"    [CONTROLS] Auto-verified {verified} rows ({reason})")
    if commit:
        conn.commit()


# ── Per-chapter extraction ──────────────────────────────────────────────────

def extract_chapter(
    chapter: dict,
    s3,
    conn,
    dry_run: bool,
    review: bool = False,
) -> tuple[bool, dict | None]:
    """
    Download PDF, extract provisions, commit atomically.
    Returns (success, review_data).

    review_data is populated when review=True and contains per-chapter
    extracted text samples + artifact check results for human inspection.
    Old provisions stay live on failure (rollback keeps them).
    """
    council     = chapter["council"]
    chapter_key = chapter["chapter_key"]
    chapter_id  = chapter["id"]
    r2_path     = chapter["r2_current_path"]
    version     = chapter["r2_version_label"] or "unknown"
    dcp_name    = chapter["dcp_name"]

    print(f"\n  [{council}/{chapter_key}]")
    print(f"    r2: {r2_path}")

    with tempfile.TemporaryDirectory() as tmpdir:
        pdf_path = Path(tmpdir) / f"{chapter_key}.pdf"

        # 1. Download from R2
        print(f"    Downloading from R2...")
        try:
            s3.download_file(R2_BUCKET_NAME, r2_path, str(pdf_path))
        except Exception as exc:
            print(f"    [ERROR] R2 download failed: {exc}")
            return False, None

        print(f"    Downloaded {pdf_path.stat().st_size:,} bytes")

        # 2. Extract sections
        cur = conn.cursor()
        document_id = resolve_document_id(cur, council, chapter_key, dcp_name)
        print(f"    document_id: {document_id}")

        extractor = DCPExtractor(pdf_path, document_id, council=council)

        # If a page-range config exists for this council/chapter, use it directly.
        # This handles DCPs where SECTION_RE matches TOC entries instead of real
        # section headings (e.g. Waverley: 297 TOC hits vs ~24 real sections).
        # Per-chapter ranges checked first (for councils with separate chapter PDFs).
        page_ranges = COUNCIL_CHAPTER_RANGES.get((council, chapter_key))
        if page_ranges is None:
            page_ranges = COUNCIL_PAGE_RANGES.get(council)
        subsection_patterns = COUNCIL_SUBSECTION_PATTERNS.get(council)
        # When AI extraction is on it reads any layout, so bypass the per-council
        # page-range/regex config entirely and use extract() (which dispatches to the
        # LLM at DCPExtractor.extract). Otherwise a council WITH a page-range config
        # (e.g. ashfield) would silently run the old regex despite AI_EXTRACTION=1.
        ai_on = os.getenv("AI_EXTRACTION", "").strip().lower() in ("1", "true", "yes")
        if page_ranges and not ai_on:
            try:
                sections = extractor.extract_by_page_ranges(page_ranges, subsection_patterns)
            except Exception as exc:
                print(f"    [ERROR] Page-range extraction failed: {exc}")
                cur.close()
                return False, None
            table_count = sum(len(s["tables"]) for s in sections)
            print(f"    Page-range extraction: {len(sections)} sections, {table_count} tables")
        else:
            try:
                sections = extractor.extract()
            except Exception as exc:
                print(f"    [ERROR] PDF extraction failed: {exc}")
                cur.close()
                return False, None

            # Apply subsection patterns to the default extraction path too.
            # (extract_by_page_ranges handles this internally; the default path does not.)
            # Skip when AI is on — the LLM already returns split provisions; re-splitting
            # its output with the regex patterns would mangle it.
            if subsection_patterns and sections and not ai_on:
                expanded: list[dict] = []
                for sec in sections:
                    sub_secs = split_content_at_subsections(
                        sec["content"],
                        sec["section_number"],
                        sec["section_title"],
                        sec["page_start"],
                        sec["page_end"],
                        sec["tables"],
                        subsection_patterns[0],
                    )
                    for pattern in subsection_patterns[1:]:
                        further: list[dict] = []
                        for s in sub_secs:
                            further.extend(split_content_at_subsections(
                                s["content"],
                                s["section_number"],
                                s["section_title"],
                                s["page_start"],
                                s["page_end"],
                                s["tables"],
                                pattern,
                                parent_text_heading=s.get("text_heading"),
                            ))
                        sub_secs = further
                    expanded.extend(sub_secs)
                sections = expanded

            table_count = sum(len(s["tables"]) for s in sections)
            print(f"    Extracted: {len(sections)} sections, {table_count} tables")

            if not sections:
                print(f"    [WARN] No sections extracted — skipping chapter")
                cur.close()
                return False, None

            # Sanity gate: require at least 1 section per 30 pages of PDF.
            # For short PDFs (≤30 pages), 1 section is legitimate (e.g. a
            # single-topic chapter like Ku-ring-gai secondary dwellings).
            min_sections = max(1, extractor.page_count // 30)
            if len(sections) < min_sections:
                verdict = "WARN" if (dry_run or review) else "ABORT"
                print(
                    f"    [{verdict}] {len(sections)} sections from "
                    f"{extractor.page_count}-page PDF (min {min_sections})"
                )
                if not dry_run and not review:
                    cur.close()
                    return False, None

        if dry_run or review:
            if dry_run:
                print(f"    [dry-run] Would soft-delete old provisions and insert {len(sections)} new ones")

            if not review:
                cur.close()
                return True, None

            # ── Build review data ─────────────────────────────────────────
            # Run diff before closing cursor so we can show before/after
            review_diff = diff_provisions(sections, council, chapter_key, document_id, cur)
            cur.close()

            # Import artifact checker from verify script
            from scripts.verify_dcp_formatting import check_provision

            provision_texts = [build_provision_text(s) for s in sections]
            non_preamble = [
                (s, t) for s, t in zip(sections, provision_texts)
                if s["section_number"] != "preamble"
            ]

            # Pick 3 sample sections: first, middle, last
            samples = []
            if non_preamble:
                idxs = sorted({0, len(non_preamble) // 2, len(non_preamble) - 1})
                for i in idxs:
                    sec, txt = non_preamble[i]
                    samples.append({
                        "section_number": sec["section_number"],
                        "title": sec.get("title", ""),
                        "pages": f"{sec.get('page_start', '?')}–{sec.get('page_end', '?')}",
                        "text": txt,
                    })

            # Artifact check across all provision texts
            from collections import Counter as _Counter
            artifact_counts: _Counter = _Counter()
            flagged_samples: _Counter = _Counter()
            serious_flagged = 0
            for txt in provision_texts:
                labels, lines = check_provision(txt)
                artifact_counts.update(labels)
                flagged_samples.update(lines)
                if set(labels) & SERIOUS_ARTIFACT_LABELS:
                    serious_flagged += 1

            schema_fail = is_schema_fail(len(provision_texts), serious_flagged)

            # AI-path railguards (absolute-quality; only when AI extraction is on).
            # LLMs can silently drop whole sections or truncate a provision mid-text.
            coverage_fail = truncation_fail = False
            coverage_toc = coverage_missing = truncation_flagged = 0
            if os.getenv("AI_EXTRACTION", "").strip().lower() in ("1", "true", "yes"):
                from scripts.ai_extractor import (
                    coverage_gap, truncation_rate, toc_codes_from_pdf,
                    COVERAGE_MISS_RATIO, TRUNCATION_RATIO,
                )
                toc = toc_codes_from_pdf(pdf_path)
                extracted_codes = {
                    s["section_number"] for s in sections
                    if s.get("section_number") != "preamble"
                }
                cov_ratio, missing = coverage_gap(extracted_codes, toc)
                coverage_toc, coverage_missing = len(toc), len(missing)
                coverage_fail = cov_ratio > COVERAGE_MISS_RATIO
                trunc_ratio, truncation_flagged = truncation_rate(provision_texts)
                truncation_fail = (
                    len(provision_texts) >= SCHEMA_FAIL_MIN_PROVISIONS
                    and trunc_ratio > TRUNCATION_RATIO
                )

            return True, {
                "council": council,
                "chapter_key": chapter_key,
                "section_count": len(sections),
                "table_count": table_count,
                "sections": [
                    {
                        "key": s["section_number"],
                        "title": s.get("title", ""),
                        "pages": f"{s.get('page_start', '?')}–{s.get('page_end', '?')}",
                    }
                    for s in sections
                ],
                "samples": samples,
                "artifact_counts": dict(artifact_counts),
                "artifact_samples": dict(flagged_samples.most_common(5)),
                "total_provisions": len(provision_texts),
                "serious_artifact_provisions": serious_flagged,
                "schema_fail": schema_fail,
                "coverage_fail": coverage_fail,
                "coverage_missing": coverage_missing,
                "coverage_toc": coverage_toc,
                "truncation_fail": truncation_fail,
                "truncation_flagged": truncation_flagged,
                "document_id": document_id,
                "content_hash": chapter.get("content_hash"),
                "diff": review_diff,
            }

        # 3. Provision count gate — before touching the DB.
        # A large drop almost always means a scanned PDF, extraction failure, or
        # format change — not a genuine DCP amendment. Never silently commit.
        #
        # COUNT query and soft-delete both use strict source_chapter_key = %s.
        # Previously included OR source_chapter_key IS NULL, which inflated counts
        # to the entire council's legacy provision total and caused first_extraction
        # to wipe all NULL-keyed (legacy) provisions across every chapter. Legacy
        # NULL provisions are preserved until explicitly migrated per-chapter.
        try:
            count_cur = conn.cursor()
            count_cur.execute(
                """
                SELECT COUNT(*) FROM regulatory_provisions
                WHERE source_council = %s
                  AND source_chapter_key = %s
                  AND is_current = TRUE
                """,
                (council, chapter_key),
            )
            prev_count = count_cur.fetchone()[0]
            count_cur.close()
        except Exception:
            prev_count = 0

        new_count = len(sections)
        print(f"    Provision count: {prev_count} existing -> {new_count} new")

        if prev_count > 20 and new_count < prev_count * 0.75:
            verdict = "WARN" if (dry_run or review) else "ABORT"
            print(
                f"    [{verdict}] Count dropped {prev_count} -> {new_count} "
                f"({new_count/prev_count:.0%}). Likely scanned PDF or format change."
            )
            if not dry_run and not review:
                print(f"    Skipping DB commit for {chapter_key} — investigate before re-extracting.")
                return False, None

        if new_count == 0:
            verdict = "WARN" if (dry_run or review) else "ABORT"
            print(f"    [{verdict}] No sections extracted — likely empty or scanned PDF.")
            if not dry_run and not review:
                return False, None

        # 4. Diff against current DB provisions
        now = datetime.now(timezone.utc)
        page_start = sections[0]["page_start"]
        page_end   = sections[-1]["page_end"]

        diff = diff_provisions(sections, council, chapter_key, document_id, cur)
        status = diff["status"]

        n_changed  = len(diff["changed"])
        n_added    = len(diff["added"])
        n_removed  = len(diff["removed"])
        n_renamed  = len(diff["renumbered"])
        n_same     = diff["unchanged_count"]
        page_shift = diff.get("page_shift")

        print(f"    Diff: {n_same} unchanged, {n_changed} changed, "
              f"{n_added} added, {n_removed} removed, {n_renamed} renumbered"
              + (f", page_shift={page_shift:+d}" if page_shift else "")
              + f"  [status={status}]")

        # Anomaly gates — abort before touching DB
        if status == "count_drop":
            # Fail-loud, fail-safe: the extraction lost a suspicious share of
            # provisions vs the approved baseline. NEVER full-replace on this (it
            # would wipe real provisions from a broken parse). Retain
            # needs_extraction for retry and surface as a failure.
            print(f"    [SKIP] count_drop — extracted {diff.get('total_new')} provisions "
                  f"vs {diff.get('total_old')} baseline "
                  f"(<{int(COUNT_DROP_RATIO*100)}%). Likely broken parse/scanned PDF, "
                  f"NOT an amendment. Refusing to replace; investigate before re-extract.")
            cur.close()
            return False, None

        if status == "regeneration_artifact":
            print(f"    [SKIP] regeneration_artifact — PDF re-exported with no substantive "
                  f"changes ({n_changed} tiny diffs across {n_same + n_changed} provisions). "
                  f"No DB update.")
            if not dry_run and not review:
                _auto_verify_controls(cur, conn, council, chapter_key,
                                      "regeneration_artifact")
            cur.close()
            return True, None   # not a failure — just nothing to commit

        if status == "map_change":
            print(f"    [SKIP] map_change — PDF hash changed but zero text extracted. "
                  f"Flag for manual spatial review.")
            if not dry_run and not review:
                _auto_verify_controls(cur, conn, council, chapter_key,
                                      "map_change")
            cur.close()
            return True, None

        if status == "restructure":
            print(f"    [WARN] restructure — >50% provisions unmatched. "
                  f"Falling back to full replace. Manual review recommended.")
            # Fall through to full replace below

        # Determine whether this is a first-time extraction (no existing provisions)
        first_extraction = (n_same == 0 and n_changed == 0 and n_removed == 0
                            and n_renamed == 0)

        if not dry_run and not review:
            try:
                if status == "restructure" or first_extraction:
                    # Full replace: soft-delete all existing + bulk insert.
                    # Strict source_chapter_key = %s only — never wipe NULL-keyed
                    # (legacy) provisions, which belong to other chapters not yet
                    # migrated. First extraction has no existing provisions to delete.
                    cur.execute(
                        """
                        UPDATE regulatory_provisions
                        SET is_current = FALSE
                        WHERE source_council = %s
                          AND is_current = TRUE
                          AND source_chapter_key = %s
                        """,
                        (council, chapter_key),
                    )
                    soft_deleted = cur.rowcount
                    print(f"    Soft-deleted {soft_deleted} old provisions (full replace)")

                    inserted = 0
                    for section in sections:
                        ref_number     = build_ref_number(document_id, section["section_number"])
                        provision_text = build_provision_text(section)
                        is_preamble    = section["section_number"] == "preamble"
                        # v2_is_actionable:
                        #   False — preamble/structural non-actionable
                        #   NULL  — let ActionableClassifier decide
                        v2_actionable  = False if is_preamble else section.get("v2_is_actionable", None)
                        cur.execute(
                            """
                            INSERT INTO regulatory_provisions (
                                document_id, ref_number, section_header,
                                provision_text, pdf_page, pdf_source_file,
                                page_range, extraction_method,
                                source_chapter_key, source_council,
                                is_current, v2_is_actionable
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,'pdfplumber-ci',%s,%s,TRUE,%s)
                            """,
                            (
                                document_id, ref_number, section["section_title"],
                                provision_text, section["page_start"], chapter_key,
                                section.get("pages", [section["page_start"]]),
                                chapter_key, council, v2_actionable,
                            ),
                        )
                        inserted += 1
                    print(f"    [OK] Inserted {inserted} provisions (full replace)")

                else:
                    # Targeted update — only touch what changed
                    updated = inserted = removed = renamed = 0

                    for c in diff["changed"]:
                        cur.execute(
                            """
                            UPDATE regulatory_provisions
                            SET provision_text   = %s,
                                pdf_page         = %s,
                                v2_is_actionable = NULL
                            WHERE source_council    = %s
                              AND source_chapter_key = %s
                              AND ref_number         = %s
                              AND is_current         = TRUE
                            """,
                            (c["new_text"], c["new_page"], council, chapter_key, c["ref_number"]),
                        )
                        updated += 1

                    for a in diff["added"]:
                        section = next(
                            (s for s in sections
                             if build_ref_number(document_id, s["section_number"]) == a["ref_number"]),
                            None,
                        )
                        if section is None:
                            continue
                        is_preamble   = section["section_number"] == "preamble"
                        v2_actionable = False if is_preamble else section.get("v2_is_actionable", None)
                        cur.execute(
                            """
                            INSERT INTO regulatory_provisions (
                                document_id, ref_number, section_header,
                                provision_text, pdf_page, pdf_source_file,
                                page_range, extraction_method,
                                source_chapter_key, source_council,
                                is_current, v2_is_actionable
                            ) VALUES (%s,%s,%s,%s,%s,%s,%s,'pdfplumber-ci',%s,%s,TRUE,%s)
                            """,
                            (
                                document_id, a["ref_number"], section["section_title"],
                                a["new_text"], section["page_start"], chapter_key,
                                section.get("pages", [section["page_start"]]),
                                chapter_key, council, v2_actionable,
                            ),
                        )
                        inserted += 1

                    for r in diff["removed"]:
                        cur.execute(
                            """
                            UPDATE regulatory_provisions
                            SET is_current = FALSE
                            WHERE source_council     = %s
                              AND source_chapter_key = %s
                              AND ref_number         = %s
                              AND is_current         = TRUE
                            """,
                            (council, chapter_key, r["ref_number"]),
                        )
                        removed += 1

                    for rn in diff["renumbered"]:
                        cur.execute(
                            """
                            UPDATE regulatory_provisions
                            SET ref_number = %s
                            WHERE source_council     = %s
                              AND source_chapter_key = %s
                              AND ref_number         = %s
                              AND is_current         = TRUE
                            """,
                            (rn["new_ref_number"], council, chapter_key, rn["old_ref_number"]),
                        )
                        renamed += 1

                    print(f"    [OK] Targeted update: {updated} updated, {inserted} inserted, "
                          f"{removed} removed, {renamed} renamed")

                # Write provision_changes audit rows (skip for first-time extractions)
                if not first_extraction:
                    _insert_provision_changes(cur, diff, council, chapter_key, version, now)

                # Mark chapter extracted in registry
                cur.execute(
                    """
                    UPDATE dcp_chapter_registry
                    SET needs_extraction        = FALSE,
                        last_extracted_at       = %s,
                        last_extracted_version  = %s,
                        page_start              = %s,
                        page_end                = %s,
                        provisions_extracted_from_hash = %s
                    WHERE id = %s
                    """,
                    (now, version, page_start, page_end,
                     chapter.get("content_hash"), chapter_id),
                )

                # Smart control flagging: only flag for review when provision
                # changes include numeric value changes (setbacks, heights, areas).
                # Text-only changes (rewording, pagination, formatting) auto-verify
                # the control rows instead of creating false alarm alerts.
                if not first_extraction:
                    has_numeric = any(
                        c.get("has_numeric_change") for c in diff["changed"]
                    )
                    has_structural = n_added > 0 or n_removed > 0
                    if has_numeric or (status == "restructure" and has_structural):
                        # Substantive change — flag for human review
                        reason = ("numeric_value_changed" if has_numeric
                                  else "structural_change")
                        cur.execute(
                            """
                            UPDATE dcp_setback_controls
                            SET needs_review   = TRUE,
                                review_reason  = %s,
                                reviewed_at    = NULL
                            WHERE lga               = %s
                              AND source_chapter_key = %s
                              AND is_current         = TRUE
                              AND needs_review       = FALSE
                            """,
                            (reason, council, chapter_key),
                        )
                        flagged = cur.rowcount
                        if flagged > 0:
                            print(f"    [CONTROLS] Flagged {flagged} rows for review "
                                  f"(reason={reason})")
                    else:
                        # Non-substantive change — auto-verify controls
                        _auto_verify_controls(cur, conn, council, chapter_key,
                                              "text_only_change", commit=False)

                conn.commit()

            except Exception as exc:
                conn.rollback()
                print(f"    [ERROR] DB transaction failed — rolled back: {exc}")
                cur.close()
                return False, None

        cur.close()
        return True, None


# ── Review queue ─────────────────────────────────────────────────────────────

def enqueue_review_changes(conn, review_chapters: list[dict]) -> int:
    """Insert detected provision changes into dcp_review_queue for human review.

    This is the inbox for the governance gate: --review extracts in memory and
    enqueues the diff; a human approves via the review UI before anything commits
    to regulatory_provisions. No provision is committed here.

    Idempotent per chapter: existing pending rows for a (council, chapter_key) are
    cleared and re-inserted, so re-running --review refreshes the queue rather than
    duplicating. Only changed/added/removed items are enqueued (page-only shifts
    and unchanged provisions are not). Returns the number of rows enqueued.
    """
    cur = conn.cursor()
    total = 0
    for ch in review_chapters:
        diff = ch.get("diff") or {}
        council = ch.get("council")
        chapter_key = ch.get("chapter_key")
        document_id = ch.get("document_id")
        content_hash = ch.get("content_hash")

        rows: list[tuple] = []
        for c in diff.get("changed", []):
            rows.append((
                "changed", c.get("ref_number"), c.get("old_text"), c.get("new_text"),
                c.get("old_page"), c.get("new_page"), bool(c.get("has_numeric_change")),
            ))
        for a in diff.get("added", []):
            rows.append((
                "added", a.get("ref_number"), None, a.get("new_text"),
                None, a.get("new_page"), False,
            ))
        for r in diff.get("removed", []):
            rows.append((
                "removed", r.get("ref_number"), r.get("old_text"), None,
                None, None, False,
            ))

        if not rows:
            continue

        # Guard verdict for the whole chapter (count_drop / schema_fail / coverage_fail /
        # truncation_fail), stored on every row so the review UI can flag the chapter.
        reason = suspect_reason(ch)

        # Full re-extraction vs targeted amendment — drives whether the commit worker
        # blanket-replaces the chapter or updates only the changed refs. A restructure or
        # an empty baseline (total_old == 0) is a full replace; anything else is targeted.
        is_full_replace = (
            diff.get("status") == "restructure" or int(diff.get("total_old") or 0) == 0
        )

        # Refresh: drop stale pending rows for this chapter, then insert fresh.
        # Only 'pending' rows are cleared — approved/rejected history is preserved.
        cur.execute(
            "DELETE FROM dcp_review_queue "
            "WHERE council = %s AND chapter_key = %s AND status = 'pending'",
            (council, chapter_key),
        )
        for change_type, ref, old_t, new_t, old_p, new_p, has_num in rows:
            cur.execute(
                """
                INSERT INTO dcp_review_queue
                    (council, chapter_key, document_id, ref_number, change_type,
                     old_text, new_text, old_page, new_page, has_numeric_change,
                     source_content_hash, suspect_reason, is_full_replace, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
                """,
                (council, chapter_key, document_id, ref, change_type,
                 old_t, new_t, old_p, new_p, has_num, content_hash, reason, is_full_replace),
            )
            total += 1

    conn.commit()
    cur.close()
    return total


# ── Review file writer ───────────────────────────────────────────────────────

def write_review_file(council: str, chapters: list[dict]) -> Path:
    """
    Write a human-readable review file for manual inspection before committing.

    Format per chapter:
      - Section list with page ranges
      - 3 sample provision texts (first / middle / last non-preamble section)
      - Artifact check counts

    Returns the path of the written file.
    """
    reviews_dir = Path(__file__).parent.parent / "reviews"
    reviews_dir.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M")
    out_path = reviews_dir / f"{council}_{ts}.txt"

    DIVIDER = "=" * 72
    SEP     = "-" * 72
    ARTIFACT_LABELS = [
        "hash_prefix_numbered_items",
        "hash_prefix_headers",
        "two_col_interleave",
        "two_col_numeric",
        "latex_tokens",
        "word_cross_references",
        "bare_page_numbers",
        "toc_dotted_leaders",
        "short_provision",
    ]
    # Which artifact labels signal extraction-level bugs (not fixable by format config)
    EXTRACTION_BUG_LABELS = {
        "hash_prefix_numbered_items",
        "hash_prefix_headers",
        "two_col_interleave",
        "latex_tokens",
        "word_cross_references",
    }

    lines: list[str] = []
    lines.append(DIVIDER)
    lines.append(f"EXTRACTION REVIEW — {council.upper()}")
    lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"Chapters reviewed: {len(chapters)}")
    lines.append(DIVIDER)
    lines.append("")
    lines.append("When you are satisfied, commit with:")
    lines.append(f"  python scripts/dcp_extract_changed.py --council {council}")
    lines.append("")

    for ch in chapters:
        chapter_key = ch["chapter_key"]
        lines.append(DIVIDER)
        lines.append(f"CHAPTER: {chapter_key}")
        lines.append(f"  {ch['section_count']} sections  |  {ch['table_count']} tables  |  {ch['total_provisions']} provisions")
        if ch.get("schema_fail"):
            lines.append(f"  ⚠ SUSPECT SCHEMA — {ch.get('serious_artifact_provisions')}/"
                         f"{ch.get('total_provisions')} provisions carry serious extraction-failure "
                         f"artifacts; likely a broken parse. DO NOT approve without checking the source PDF.")
        lines.append("")

        # Diff summary (if available)
        diff = ch.get("diff")
        if diff:
            ds = diff["status"]
            status_label = {
                "ok": "ok",
                "count_drop": (
                    f"⚠ SUSPECT COUNT DROP — extracted {diff.get('total_new')} vs "
                    f"{diff.get('total_old')} baseline; likely broken parse, DO NOT approve "
                    f"without checking the source PDF"
                ),
                "restructure": "RESTRUCTURE (full replace needed)",
                "regeneration_artifact": "REGENERATION ARTIFACT (no substantive changes)",
                "map_change": "MAP/SPATIAL CHANGE (no text to extract)",
            }.get(ds, ds)
            lines.append(f"  DIFF SUMMARY  [{status_label}]")
            lines.append(f"    {diff['unchanged_count']} unchanged  |  "
                         f"{len(diff['changed'])} changed  |  "
                         f"{len(diff['added'])} added  |  "
                         f"{len(diff['removed'])} removed  |  "
                         f"{len(diff['renumbered'])} renumbered"
                         + (f"  page_shift={diff['page_shift']:+d}" if diff.get("page_shift") else ""))

            # Numeric changes first
            numeric = [c for c in diff["changed"] if c["has_numeric_change"]]
            if numeric:
                lines.append("")
                lines.append(f"  *** NUMERIC CHANGES ({len(numeric)}) — review carefully:")
                for c in numeric[:10]:
                    lines.append(f"    {c['ref_number']}:")
                    lines.append(f"      WAS: {(c['old_text'] or '')[:120]}")
                    lines.append(f"      NOW: {(c['new_text'] or '')[:120]}")
                if len(numeric) > 10:
                    lines.append(f"    ... and {len(numeric) - 10} more numeric changes")

            # Other changed provisions
            other_changed = [c for c in diff["changed"] if not c["has_numeric_change"]]
            if other_changed:
                lines.append("")
                lines.append(f"  Changed provisions ({len(other_changed)}):")
                for c in other_changed[:5]:
                    lines.append(f"    {c['ref_number']}:")
                    lines.append(f"      WAS: {(c['old_text'] or '')[:100]}")
                    lines.append(f"      NOW: {(c['new_text'] or '')[:100]}")
                if len(other_changed) > 5:
                    lines.append(f"    ... and {len(other_changed) - 5} more")

            if diff["added"]:
                lines.append("")
                lines.append(f"  Added ({len(diff['added'])}):")
                for a in diff["added"][:5]:
                    lines.append(f"    {a['ref_number']}: {(a['new_text'] or '')[:100]}")
                if len(diff["added"]) > 5:
                    lines.append(f"    ... and {len(diff['added']) - 5} more")

            if diff["removed"]:
                lines.append("")
                lines.append(f"  Removed ({len(diff['removed'])}):")
                for r in diff["removed"][:5]:
                    lines.append(f"    {r['ref_number']}: {(r['old_text'] or '')[:100]}")
                if len(diff["removed"]) > 5:
                    lines.append(f"    ... and {len(diff['removed']) - 5} more")

            if diff["renumbered"]:
                lines.append("")
                lines.append(f"  Renumbered ({len(diff['renumbered'])}):")
                for rn in diff["renumbered"][:5]:
                    lines.append(f"    {rn['old_ref_number']} → {rn['new_ref_number']}")
                if len(diff["renumbered"]) > 5:
                    lines.append(f"    ... and {len(diff['renumbered']) - 5} more")

            lines.append("")

        # Section list
        lines.append("  SECTIONS:")
        for sec in ch["sections"]:
            title = sec["title"] or "(untitled)"
            lines.append(f"    [{sec['key']:20s}]  pp {sec['pages']:12s}  {title}")
        lines.append("")

        # Artifact check
        art = ch["artifact_counts"]
        total = ch["total_provisions"]
        has_bugs = any(art.get(l, 0) > 0 for l in EXTRACTION_BUG_LABELS)
        lines.append("  ARTIFACT CHECK:")
        for label in ARTIFACT_LABELS:
            count = art.get(label, 0)
            if count == 0:
                continue
            pct = count / total * 100 if total else 0
            flag = " ← EXTRACTION BUG" if label in EXTRACTION_BUG_LABELS else " (format config)"
            lines.append(f"    {label:<35s} {count:>4}/{total}  ({pct:.0f}%){flag}")
        if not any(art.get(l, 0) > 0 for l in ARTIFACT_LABELS):
            lines.append("    (none detected)")
        if has_bugs:
            lines.append("")
            lines.append("  ⚠  EXTRACTION BUGS DETECTED — do not commit without fixing.")
            lines.append("     See docs/DCP_EXTRACTION_KNOWN_PATTERNS.md for fix guidance.")
        lines.append("")

        # Sample provisions
        lines.append("  SAMPLE PROVISIONS:")
        for i, sample in enumerate(ch["samples"]):
            label = ["first", "middle", "last"][i] if i < 3 else f"sample {i+1}"
            lines.append(f"  {SEP}")
            lines.append(f"  [{label}]  {sample['section_number']}  —  {sample['title']}  (pp {sample['pages']})")
            lines.append(f"  {SEP}")
            # Wrap text at 80 chars, indent 4 spaces, cap at ~60 lines
            text = sample["text"]
            raw_lines = text.split("\n")
            shown = 0
            for raw in raw_lines:
                if shown >= 60:
                    lines.append("    ... [truncated — open PDF for full text]")
                    break
                lines.append(f"    {raw}")
                shown += 1
            lines.append("")

    # Overall summary
    lines.append(DIVIDER)
    lines.append("OVERALL SUMMARY")
    lines.append(DIVIDER)
    total_sections = sum(c["section_count"] for c in chapters)
    total_provisions = sum(c["total_provisions"] for c in chapters)
    lines.append(f"  Chapters  : {len(chapters)}")
    lines.append(f"  Sections  : {total_sections}")
    lines.append(f"  Provisions: {total_provisions}")
    lines.append("")

    # Aggregate artifact counts
    from collections import Counter as _Counter
    agg: _Counter = _Counter()
    for c in chapters:
        agg.update(c["artifact_counts"])
    bug_chapters = [c["chapter_key"] for c in chapters
                    if any(c["artifact_counts"].get(l, 0) > 0 for l in EXTRACTION_BUG_LABELS)]
    if bug_chapters:
        lines.append("  CHAPTERS WITH EXTRACTION BUGS:")
        for chk in bug_chapters:
            lines.append(f"    • {chk}")
        lines.append("")
        lines.append("  DO NOT commit — fix extraction issues first.")
    else:
        lines.append("  No extraction bugs detected across all chapters.")
        lines.append("")
        lines.append("  Ready to commit:")
        lines.append(f"    python scripts/dcp_extract_changed.py --council {council}")

    lines.append("")

    out_path.write_text("\n".join(lines), encoding="utf-8")
    return out_path


# ── Main ────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="DCP chapter extraction pipeline")
    parser.add_argument("--council", help="Filter to specific council")
    parser.add_argument("--chapter", help="Filter to a single chapter_key (for a targeted re-extraction/retry)")
    parser.add_argument("--dry-run", action="store_true", help="Extract but no DB writes")
    parser.add_argument(
        "--review",
        action="store_true",
        help=(
            "Extract to memory only — write a human-readable review file with section "
            "lists, sample provision texts, and artifact checks. No DB writes. "
            "Inspect the file, then re-run without --review to commit."
        ),
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "Re-extract EVERY active chapter and diff vs the approved baseline, not "
            "just byte-change-flagged ones — the scheduled re-extract-all detector "
            "cadence. Pair with --review for the quarterly run."
        ),
    )
    args = parser.parse_args()

    s3 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=R2_ACCESS_KEY_ID,
        aws_secret_access_key=R2_SECRET_ACCESS_KEY,
        region_name="auto",
    )
    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    print("=" * 60)
    print(f"DCP Extraction Pipeline — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if args.review:
        print("REVIEW MODE — no DB writes, generates review file for inspection")
    elif args.dry_run:
        print("DRY RUN")
    print("=" * 60)

    try:
        cur = conn.cursor()
        chapters = fetch_pending_chapters(cur, args.council, all_chapters=args.all,
                                          chapter_filter=args.chapter)
        cur.close()
    except Exception as exc:
        print(f"[ERROR] Could not query dcp_chapter_registry: {exc}")
        conn.close()
        sys.exit(1)

    if not chapters:
        print("Nothing to extract — no chapters with needs_extraction=TRUE.")
        conn.close()
        sys.exit(0)

    print(f"Found {len(chapters)} chapter(s) to extract:")
    for ch in chapters:
        print(f"  [{ch['council']}] {ch['chapter_key']}")

    succeeded = 0
    failed    = 0
    review_chapters: list[dict] = []

    for chapter in chapters:
        ok, review_data = extract_chapter(
            chapter, s3, conn,
            dry_run=args.dry_run,
            review=args.review,
        )
        if ok:
            succeeded += 1
            if review_data is not None:
                review_chapters.append(review_data)
        else:
            failed += 1

    if args.review and review_chapters:
        review_path = write_review_file(args.council or "all", review_chapters)
        queued = enqueue_review_changes(conn, review_chapters)
        print(f"\n{'='*60}")
        print(f"REVIEW FILE WRITTEN")
        print(f"{'='*60}")
        print(f"\n  {review_path}")
        print(f"  Enqueued {queued} change(s) to dcp_review_queue for human review.")
        print(f"\n  Open this file and inspect section lists + sample provision texts.")
        print(f"  When satisfied, commit with:")
        print(f"    python scripts/dcp_extract_changed.py --council {args.council or '<council>'}")

        # Fail-loud: name any SUSPECT chapters (count_drop OR schema_fail) so the
        # unattended quarterly run surfaces them — in the run log AND via Telegram.
        # These are NOT auto-committed and must be checked against the source PDF
        # before approval — they are usually a broken parse, not a real amendment.
        suspect = [ch for ch in review_chapters if suspect_reason(ch)]
        if suspect:
            print(f"\n  {'!'*58}")
            print(f"  🚨 {len(suspect)} chapter(s) flagged SUSPECT (possible extraction failure):")
            for ch in suspect:
                print(f"     - [{ch.get('council')}] {ch.get('chapter_key')}: {suspect_reason(ch)}")
            print(f"  Do NOT approve these without checking the source PDF.")
            print(f"  {'!'*58}")

            # Best-effort push so the quarterly run alerts, not just logs. Reuses
            # run_monitors.send_telegram (no-ops when TELEGRAM_* unset).
            alert = build_suspect_alert(args.council or "all", suspect)
            if alert:
                try:
                    from run_monitors import send_telegram
                    send_telegram(alert)
                except Exception as exc:  # never let alerting break the run
                    print(f"  [warn] SUSPECT Telegram alert not sent: {exc}")

        conn.close()
        sys.exit(2)  # exit 2 = review file written, triggers workflow quality gate

    conn.close()

    print(f"\n{'='*60}")
    print("EXTRACTION SUMMARY")
    print(f"{'='*60}")
    print(f"  Chapters attempted : {len(chapters)}")
    print(f"  Succeeded          : {succeeded}")
    print(f"  Failed             : {failed}")

    if succeeded == 0:
        print("\n  All chapters failed. Failed chapters retain needs_extraction=TRUE for retry.")
        sys.exit(1)

    if failed > 0:
        print(f"\n  {failed} chapter(s) failed — retained needs_extraction=TRUE for retry.")

    # ── Quality gate ─────────────────────────────────────────────────────────
    # Non-fatal check — provisions are already committed at this point.
    # Gate thresholds: granularity ≥50%, text_quality ≥95%, duplicates ≥95%, pages ≥90%
    print(f"\n{'='*60}")
    print("QUALITY GATE")
    print(f"{'='*60}")

    try:
        from scripts.dcp_quality_report import check_gate
        gate_council = args.council or None
        passed, failures = check_gate(council_filter=gate_council)
        if not passed:
            print("\n  Quality gate FAILED (non-fatal — provisions already committed).")
            for f in failures:
                print(f"    • {f}")
            print("\n  Fix data quality issues before relying on these provisions.")
        else:
            print("\n  Quality gate PASSED — proceeding to enrichment.")
    except Exception as exc:
        print(f"\n  Quality gate ERROR (non-fatal): {exc}")
        passed = False

    # ── Enrichment pipeline ──────────────────────────────────────────────────
    # Run automatically after any successful extraction so new provisions are
    # fully enriched without needing a separate manual command.
    # Phase order is mandatory: actionability must run before layer/applicability
    # because those phases filter WHERE v2_is_actionable = TRUE.
    if passed:
        print(f"\n{'='*60}")
        print("ENRICHMENT PIPELINE")
        print(f"{'='*60}")

        print("\n[1/3] Actionability classification...")
        run_actionability_classification(batch_size=500)

        print("\n[2/3] Layer + topic tagging...")
        run_layer_tagging(batch_size=500)

        print("\n[3/3] Applicability tagging...")
        run_applicability_tagging(batch_size=500)
    else:
        print("\n  Skipping enrichment — quality gate did not pass.")

    sys.exit(2)


if __name__ == "__main__":
    main()
