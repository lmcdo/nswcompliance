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
    # Chapter D has 13 Parts (source-verified 2026-07-29 against the adopted PDF's
    # per-page 'Part N – Name' running headers; R2 v1.1-2026-03-02). The previous
    # 8-entry manifest here used wrong names (locality names, incl. 'Haberfield'
    # which is chapter E2) and wrong ranges — the root cause of the unreliable
    # D-numbers in refs, the missing Part 9, and the bad auto-derived
    # dcp_precinct_localities names. Keys carry the Part number so refs and the
    # v2_precinct_id backfill ('Part N') stay aligned with dcp_precinct_boundaries.
    ("ashfield", "chapter-d-precinct-guidelines"): [
        ("D-Part1",  "Ashfield Town Centre",              3,  40),
        ("D-Part2",  "Ashfield East",                    41,  57),
        ("D-Part3",  "Ashfield West",                    58,  83),
        ("D-Part4",  "Croydon Town Centre",              84,  95),
        ("D-Part5",  "Neighbourhood Centre (B1) Zone",   96, 106),
        ("D-Part6",  "Enterprise Zone (B6) Parramatta Road", 107, 155),
        ("D-Part7",  "Enterprise Zone (B6) Hurlstone Park",  156, 168),
        ("D-Part8",  "SummerHill Town Centre",          169, 180),
        ("D-Part9",  "Summer Hill Flour Mills Site",    181, 182),
        ("D-Part10", "Edwards Street B4 Zone",          183, 187),
        ("D-Part11", "Industrial Zones",                188, 192),
        ("D-Part12", "55-63 Smith Street Summer Hill",  193, 196),
        ("D-Part13", "120C Old Canterbury Road",        197, 204),
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
    # ── Ku-ring-gai DCP Part 14 (Local Centres + specific sites), registered 2026-07-29.
    # Section ranges derived from each PDF's '14X.n' headings (incl. -separated
    # variants) with contiguous fill; page 1 TOC/cover as intro. One row per section,
    # matching the existing Ku-ring-gai granularity convention.
    ("ku_ring_gai", "section-b-part-14a-st-ives-local-centre"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14a_1", "St Ives Local Centre Context", 2, 2),
        ("14a_2", "Public Domain And Pedestrian Access", 3, 3),
        ("14a_3", "Proposed Community Infrastructure", 4, 5),
        ("14a_4", "Setbacks", 6, 6),
        ("14a_5", "Built Form", 7, 7),
        ("14a_6", "Building Entries, Car Parking And Service Access", 8, 8),
        ("14a_7", "Precinct S1: St Ives Shopping Village", 9, 13),
        ("14a_8", "Precinct S2: Stanley Street Shops", 14, 19),
        ("14a_9", "Precinct S3: Buildings In R4 Zones", 20, 22),
    ],
    ("ku_ring_gai", "section-b-part-14b-turramurra-local-centre"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14b_1", "Turramurra Local Centre Context", 2, 2),
        ("14b_2", "Public Domain And Pedestrian Access", 3, 3),
        ("14b_3", "Proposed Community Infrastructure", 4, 5),
        ("14b_4", "Setbacks", 6, 6),
        ("14b_5", "Built Form", 7, 7),
        ("14b_6", "Building Entries, Car Parking And Service Access", 8, 8),
        ("14b_7", "Environmental Protection And Bush Fire Protection", 9, 9),
        ("14b_8", "Precinct T1: Pacific Highway And Ray Street Retail Area", 10, 20),
        ("14b_9", "Precinct T2: Rohini Street And Eastern Road Retail Cent", 21, 22),
        ("14b_3", "Proposed Community Infrastructure", 23, 23),
        ("14b_9", "Precinct T2: Rohini Street And Eastern Road Retail Cent", 24, 26),
        ("14b_10", "Precinct T3: Kissing Point Road Retail Area", 27, 34),
        ("14b_11", "Precinct T4: Hillview Area", 35, 38),
    ],
    ("ku_ring_gai", "section-b-part-14c-pymble-local-centre"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14c_1", "Pymble Local Centre Context", 2, 2),
        ("14c_2", "Public Domain And Pedestrian Access", 3, 3),
        ("14c_3", "Proposed Community Infrastructure", 4, 5),
        ("14c_4", "Setbacks", 6, 6),
        ("14c_5", "Built Form", 7, 7),
        ("14c_6", "Building Entries, Car Parking And Service", 8, 8),
        ("14c_7", "Precinct 1: Grandview Street And Pacific", 9, 14),
    ],
    ("ku_ring_gai", "section-b-part-14d-gordon-local-centre"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14d_1", "Gordon Local Centre Context", 2, 2),
        ("14d_2", "Public Domain And Pedestrian Access", 3, 3),
        ("14d_3", "Proposed Community Infrastructure", 4, 5),
        ("14d_4", "Setbacks", 6, 7),
        ("14d_5", "Built Form", 8, 8),
        ("14d_6", "Building Entries, Car Parking And Service", 9, 9),
        ("14d_7", "Precinct G1: St Johns Avenue And Henry", 10, 15),
        ("14d_8", "Precinct G2: Pacific Highway Retail", 16, 21),
        ("14d_9", "Precinct G3: Civic Hub", 22, 27),
        ("14d_10", "Precinct G4: Mixed Use", 28, 33),
        ("14d_11", "Precinct G5: Buildings In R4 Zones", 34, 36),
    ],
    ("ku_ring_gai", "section-b-part-14e-lindfield-local-centre"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14e_1", "Lindfield Local Centre Context", 2, 2),
        ("14e_2", "Public Domain And Pedestrian Access", 3, 3),
        ("14e_3", "Proposed Community Infrastructure", 4, 6),
        ("14e_4", "Setbacks", 7, 8),
        ("14e_5", "Built Form", 9, 9),
        ("14e_6", "Building Entries, Car Parking And Service Access", 10, 10),
        ("14e_7", "Precinct L1: Balfour Street Retail Area", 11, 17),
        ("14e_8", "Precinct L2: Pacific Highway Retail Area", 18, 23),
        ("14e_9", "Precinct L3: Tryon Place Mixed Use Area", 24, 29),
        ("14e_10", "Precinct L4: Tryon Road And Lindfield Avenue Retail", 30, 42),
        ("14e_11", "Precinct L5: Lindfield Community Hub", 43, 55),
        ("14e_12", "Precinct L6: 259-271 Pacific Highway, Lindfield", 56, 64),
        ("14e_13", "Precinct L7: Buildings In R4 Zones", 65, 66),
        ("14e_14", "Precinct L8: Buildings In R4 Zones", 67, 70),
    ],
    ("ku_ring_gai", "section-b-part-14f-roseville-local-centre"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14f_1", "Roseville Local Centre Context", 2, 2),
        ("14f_2", "Public Domain And Pedestrian Access", 3, 3),
        ("14f_3", "Proposed Community Infrastructure", 4, 5),
        ("14f_4", "Setbacks", 6, 6),
        ("14f_5", "Built Form", 7, 7),
        ("14f_6", "Building Entries, Car Parking And Service", 8, 8),
        ("14f_7", "Precinct R1: Hill Street Shops", 9, 14),
        ("14f_8", "Precinct R2: Pacific Highway Shops", 15, 19),
        ("14f_9", "Precinct R3: Pacific Highway To Roseville Station", 20, 24),
    ],
    ("ku_ring_gai", "section-b-part-14g-pymble-business-park"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14g_1", "Urban Precinct", 2, 3),
        ("14g_2", "Public Domain And Pedestrian Access", 4, 5),
        ("14g_3", "Proposed Community Infrastructure", 6, 7),
        ("14g_4", "Building Setbacks", 8, 9),
        ("14g_5", "Built Form", 10, 12),
        ("14g_6", "Heritage", 13, 14),
        ("14g_7", "Shared On-Site Parking", 15, 16),
    ],
    ("ku_ring_gai", "section-b-part-14h-screen-australia-site"): [
        ("14h_1", "Urban Precinct", 1, 3),
        ("14h_2", "Public Domain And", 4, 5),
        ("14h_3", "Building Setbacks", 6, 8),
    ],
    ("ku_ring_gai", "section-b-part-14i-killara-golf-club"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14i_1", "Urban Precinct", 2, 4),
        ("14i_2", "Pedestrian And Vehicular Access", 5, 7),
        ("14i_3", "Building Setbacks", 8, 9),
        ("14i_4", "Built Form", 10, 11),
        ("14i_5", "Heritage", 12, 14),
    ],
    ("ku_ring_gai", "section-b-part-14j-holford-crescent-gordon"): [
        ("14j_1", "Building Setbacks", 1, 4),
    ],
    ("ku_ring_gai", "section-b-part-14k-45-47-tennyson-avenue-and-105-eastern-road-turramurra"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14k_1", "Urban Precinct", 2, 3),
        ("14k_2", "Pedestrian And Vehicular Access", 4, 5),
        ("14k_3", "Building Setbacks", 6, 7),
        ("14k_4", "Built Form", 8, 9),
        ("14k_5", "Public Domain", 10, 12),
    ],
    ("ku_ring_gai", "section-b-part-14l-62-and-64-66-pacific-highway-roseville"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14l_1", "Urban Precinct", 2, 3),
        ("14l_2", "Pedestrian And Vehicular Access", 4, 5),
        ("14l_3", "Building Setbacks", 6, 7),
        ("14l_4", "Built Form", 8, 9),
        ("14l_5", "Heritage", 10, 11),
        ("14l_6", "Public Domain", 12, 14),
    ],
    ("ku_ring_gai", "section-b-part-14m-47-warrane-road-roseville-chase"): [
        ("14m_1", "Urban Precinct", 1, 3),
        ("14m_2", "Public Domain, Pedestrian And", 4, 5),
        ("14m_3", "Building Setbacks", 6, 7),
    ],
    ("ku_ring_gai", "section-b-part-14n-8a-14-16-buckingham-road-killara"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14n_1", "Urban Precinct", 2, 3),
        ("14n_2", "Pedestrian And Vehicular Access", 4, 5),
        ("14n_3", "Building Setbacks", 6, 7),
        ("14n_4", "Built Form", 8, 9),
        ("14n_5", "Heritage", 10, 11),
    ],
    ("ku_ring_gai", "section-b-part-14o-pymble-golf-club"): [
        ("intro", "Cover and Introduction", 1, 1),
        ("14o_1", "Urban Precinct", 2, 3),
        ("14o_2", "Pedestrian And Vehicular Access", 4, 5),
        ("14o_3", "Building Setbacks", 6, 7),
        ("14o_4", "Built Form", 8, 9),
        ("14o_5", "Heritage", 10, 11),
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
    # Waverley DCP 2022: three-level split.
    # Level 1: numbered sub-sections like "1.1 DEMOLITION AND CONSTRUCTION"
    # Level 2: numbered sub-subsections like "7.2.1 Vehicle Access" (mixed case).
    #   Without this level these headings are swallowed as body text, so every
    #   Objectives/Controls block under 7.2.1..7.2.6 collides onto the parent
    #   7.2 ref — the ref-collision defect found by the 2026-07-28 fidelity
    #   sweep. Title must start with a letter to avoid matching numbered lists.
    # Level 3: Objectives/Controls keyword headings within each (sub-)subsection
    "waverley": [
        re.compile(r"(?m)^(\d+\.\d+)\s+([A-Z][A-Z0-9\s/&(),.-]+)$"),
        re.compile(r"(?m)^(\d+\.\d+\.\d+)\s+([A-Za-z][^\n]{0,80})$"),
        re.compile(
            r"(?m)^()(General Objectives|General Controls|Objectives|Controls"
            r"|Design Guidance|Performance Criteria|Prescriptive Controls)\s*$"
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
# Councils whose two-column body layout has NO reliable header-pair anchor
# (Objectives|Controls) to trigger COUNCIL_COLUMN_CONFIGS — read them with the
# geometric columnar reader instead (gutter found from word x-geometry, no
# per-council boundary_x). Added 2026-07-29 after the semantic sweep showed
# two-column reading-order interleave dropped whole sections (CoS 5.2.4 table,
# Ashfield ch.D setback legends, Marrickville part-2/9).
# hornsby added 2026-07-30: preflight SUSPECT triage confirmed genuine
# interleave — a "Note:" sidebar column mixed mid-sentence into the main body
# text on multiple pages (part-1-general pp11/21), same failure class as the
# councils above; no header-pair anchor exists so the geometric reader (not
# COUNCIL_COLUMN_CONFIGS) is the fit.
GEOMETRIC_COLUMN_COUNCILS = {"ashfield", "marrickville", "city_of_sydney", "hornsby"}


def _find_gutter(words: list[dict], page_width: float) -> float | None:
    """Return the x of a clear vertical two-column gutter, or None.

    Scans the central 40-60% band for the x that the fewest words straddle.
    A gutter is real only when <5% of words cross it AND each side holds >=25%
    of the words — otherwise the page is single-column (many words straddle
    centre) and the caller falls back to plain extraction. Pure."""
    if len(words) < 30 or page_width <= 0:
        return None
    lo, hi, step = page_width * 0.40, page_width * 0.60, max(1.0, page_width * 0.01)
    n = len(words)
    best_x, best_cross = None, None
    x = lo
    while x <= hi:
        cross = sum(1 for w in words if w["x0"] < x < w["x1"])
        if best_cross is None or cross < best_cross:
            best_cross, best_x = cross, x
        x += step
    if best_x is None or best_cross / n >= 0.05:
        return None
    left = sum(1 for w in words if (w["x0"] + w["x1"]) / 2 < best_x)
    if left / n < 0.25 or (n - left) / n < 0.25:
        return None
    return best_x


def _columnar_text(page: Any) -> str | None:
    """Read a two-column page in true reading order (full-width headings kept
    in place, then left column, then right column, per horizontal band).

    Returns None when the page is not clearly two-column, so the caller falls
    back to plain extract_text(). Band algorithm: group words into lines, a line
    that spans the gutter is a full-width break; runs of lines that don't span
    it between breaks are emitted left-then-right. Pure aside from extract_words().

    ⚠ FIXED 2026-09-09 (ashfield/chapter-d-precinct-guidelines, DQ-92): the
    original version required BOTH sides to hold words on the SAME 3px row
    band to register a line as two-column. Checked against the real PDF: real
    two-column body text almost never wraps that precisely in sync between
    columns, so nearly every row had content on only ONE side at its own
    band, `two_col` was false almost everywhere, and the page fell through to
    a plain top-to-bottom read — left- and right-column lines interleaved
    line-by-line in raw Y order, not grouped by column at all. A single-sided
    line is now accumulated into whichever side it falls on for the current
    run; a run only breaks (flush) on a line that genuinely STRADDLES the
    gutter — real full-width text, not just a momentarily-empty other side.

    A line counts as straddling either when one word's own span crosses the
    gutter, OR when both sides hold words but the gap between the rightmost
    left word and leftmost right word is too narrow to be a real column
    gutter (e.g. "5.2.4 Local Infrastructure" — separate words on both sides
    of cx, ordinary word-spacing between them, no individual word touching
    cx). Sol cross-review (HIGH 0.99, 2026-09-09) caught that this second
    case — the ONLY full-width test the pre-fix version had — was dropped
    entirely in the first version of this fix, which would have silently
    reordered every such heading into the column buffers."""
    from collections import defaultdict
    words = page.extract_words() or []
    W = float(page.width or 0)
    cx = _find_gutter(words, W)
    if cx is None:
        return None
    # ⚠ KNOWN PRE-EXISTING LIMITATION (Sol cross-review, HIGH 0.96, 2026-09-09,
    # against this restored check -- the threshold itself predates this fix,
    # not introduced by it): fixed at 30px / 5% of page width. A genuine
    # two-column page whose real gutter is narrower than that would have
    # every row misclassified as full-width, defeating the grouping this
    # function exists to do. Not observed on any real page sampled from the
    # four councils this function currently serves (ashfield, marrickville,
    # hornsby, city_of_sydney) -- their column gutters all measured wider
    # than this. A page-specific baseline derived from the page's own
    # repeated body-row gaps would be more robust; not built here. Logged,
    # not chased -- same discipline as the 98 unrecovered section numbers in
    # the marrickville TOC-guard fix.
    gap_min = max(30.0, W * 0.05)
    lines: dict[int, list[dict]] = defaultdict(list)
    for w in words:
        lines[round(w["top"] / 3.0)].append(w)

    def line_text(lw: list[dict]) -> str:
        return " ".join(w["text"] for w in sorted(lw, key=lambda w: w["x0"]))

    out: list[str] = []
    block: dict[str, list[list[dict]]] | None = None

    def flush() -> None:
        nonlocal block
        if block:
            out.extend(line_text(l) for l in block["left"])
            out.extend(line_text(l) for l in block["right"])
            block = None

    for _, lw in sorted(lines.items()):
        left = [w for w in lw if (w["x0"] + w["x1"]) / 2 < cx]
        right = [w for w in lw if (w["x0"] + w["x1"]) / 2 >= cx]
        word_straddle = any(w["x0"] < cx - 5 and w["x1"] > cx + 5 for w in lw)
        narrow_gap = False
        if left and right and not word_straddle:
            gap = min(w["x0"] for w in right) - max(w["x1"] for w in left)
            narrow_gap = gap < gap_min
        if word_straddle or narrow_gap:
            # Genuine full-width text (a heading, a table caption) — end
            # whatever two-column run was in progress, emit left-then-right,
            # then this line in its own Y position.
            flush()
            out.append(line_text(lw))
            continue
        if not left and not right:
            continue
        if block is None:
            block = {"left": [], "right": []}
        if left:
            block["left"].append(left)
        if right:
            block["right"].append(right)
    flush()
    return "\n".join(out)


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
    # ⚠ CORRECTED 2026-08-14 — the [A-Z]\d+ alternative was the primary defect.
    # It deliberately admitted "C8 Some control" / "O9 Some objective" as SECTION
    # headings. Those are clause markers, and COUNCIL_SUBSECTION_PATTERNS
    # ["marrickville"] level 2 already splits them, so admitting them here was
    # redundant — and harmful: it pushed ordinary body pages to 7–16 hits, over
    # the TOC page guard's >=5 threshold, which then blanked ALL section
    # detection on those pages. Measured: part2-s11-fencing holds 88 heading
    # matches in its text and only 4 sections survived; every clause collapsed
    # onto __preamble_*, losing the citable clause number. Woollahra's override
    # 20 lines below excludes O1/C1 for exactly this reason, from 2026-05.
    # Dotted-decimal only takes body pages to 1–4 hits (unsuppressed) while the
    # genuine contents page stays at 13 (still suppressed).
    "marrickville": re.compile(
        r'^(\d+(?:\.\d+)+)\s+([A-Z][^\n]+)$', re.MULTILINE
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

# Matches a "SECTION N" divider-page marker, e.g. a standalone line reading
# "SECTION 1" or "SECTION 5" (a section-title/divider page, distinct from a
# real body heading like "5.1 Dwelling mix"). Canterbury-Bankstown
# chapter-7-5 origin case (2026-09-05): pages 5, 8 and 82 each read
# "SECTION N\n<ALL-CAPS TITLE>\n<N.1 ... page#>\n<N.2 ... page#>\n..." -- a
# mini table-of-contents repeating only THAT section's own 2-4 child
# entries. The existing TOC-page guard below only fires at >=5 section-code
# matches (calibrated for the chapter's full TOC), so these divider pages
# (3-4 matches) slip through and get captured as the opening paragraph of
# sections 1.1/2.1/5.1 -- unrelated sibling titles and page numbers standing
# in for real provision text. Checked against the real PDF (not assumed):
# in every observed case the divider block is the page's ENTIRE text, so
# suppressing the whole page on this signal is safe.
_SECTION_DIVIDER_RE = re.compile(r'(?m)^\s*SECTION\s+\d+\s*$')

# A genuine running page-header repeats on (near-)every page of its own section
# (e.g. Marrickville's "2.1 Urban Design" atop every page of 2.1 and its
# children). A reused section number resurfacing many pages later (a
# document's own Appendices reusing the main body's numbering) is a NEW
# section, not a repeat -- see is_running_header_repeat. 2 pages of slack
# covers the ordinary case (a section spanning a blank/table-only page with no
# text match) without accepting a reuse many pages downstream.
_RUNNING_HEADER_MAX_GAP = 2


def is_running_header_repeat(
    current_number: str, new_code: str, page_num: int, last_confirmed_page: int
) -> bool:
    """True when a heading match for `new_code` on `page_num` is a repeat of the
    ALREADY-OPEN section's own running page-header, not a genuinely new section.

    A running header is either the exact same code, or a parent prefix of it
    (Marrickville prints "2.1 Urban Design" atop every page of 2.1 and its
    numbered children, e.g. "2.1.1.3"). That alone isn't enough, though: found
    live 2026-09-05 on marrickville/part7-s3-sex-industry, a document's own
    Appendices reuse the main body's numbering for unrelated later content --
    a real second heading, "7.3.7 Appendix 3 - Health standards...", appeared
    12+ pages after the original 7.3.7 opened, and treating it as a repeated
    header merged 7 real sections' worth of content (7.3.8-7.3.14) into the
    original section (which grew to 14,738 characters). A genuine running
    header repeats on (near-)every page of its own section, so the repeat is
    only honoured while the gap since it last confirmed itself stays small
    (_RUNNING_HEADER_MAX_GAP); a resurfacing many pages later is a new
    section, however it also captures. Pure -- no PDF I/O."""
    same_or_parent = (
        current_number == new_code or current_number.startswith(new_code + ".")
    )
    if not same_or_parent:
        return False
    return page_num - last_confirmed_page <= _RUNNING_HEADER_MAX_GAP


def classify_toc_or_divider_page(
    text: str, section_re: "re.Pattern[str]"
) -> tuple[bool, bool]:
    """Returns (suppress, discard) for a page that should not start a new
    section. Pure function, no PDF I/O, so it is unit-testable without a
    fixture PDF (this module's own convention: full extraction is validated
    against real council PDFs out of band; the decision logic is tested
    directly).

    suppress: True for either a full chapter TOC page (5+ section-code
    matches) or a section-DIVIDER mini-TOC page (a literal "SECTION N"
    marker near the top plus 2+ matches) -- this page must not start a new
    section.

    discard: True ONLY for the divider case. Sol cross-review (HIGH,
    confidence 0.98, 2026-09-05): suppressing heading detection alone does
    not remove the corrupt text -- the existing code unconditionally
    appends every non-heading page's text to whichever section is already
    open. For the chapter's own full TOC page this lands harmlessly inside
    'preamble' in every observed case (the TOC always appears before any
    real section exists, and preamble is already non-actionable --
    consistent with docs/DCP_EXTRACTION_KNOWN_PATTERNS.md §4's "do not
    delete, keep as navigational context"). A section-divider page fires
    MID-CHAPTER, so "whichever section is already open" is almost always a
    real, actionable one: verified live, chapter-7-5's page 8 divider
    landed inside section 1.2 (previously clean) and page 82's divider
    landed inside 4.6 (previously clean), corrupting two sections this fix
    was never meant to touch. So divider-page text must be discarded
    outright, not absorbed -- a page that is BOTH a full-TOC page and
    (incidentally) carries a "SECTION N" line keeps the existing,
    unchanged full-TOC behaviour (absorb), since that combination has
    never been observed and is out of this fix's scope."""
    toc_hits = len(section_re.findall(text))
    is_full_toc = toc_hits >= 5
    is_divider = (not is_full_toc) and toc_hits >= 2 and bool(
        _SECTION_DIVIDER_RE.search(text[:300])
    )
    return (is_full_toc or is_divider), is_divider


# Councils whose PDFs contain rotated figure/diagram labels (sidebar labels,
# figure callouts, diagram text) that pdfplumber extracts as reversed or
# garbled characters. Filtering to upright-only chars removes them.
# ashfield added 2026-07-29: chapter D carries a rotated 'Part N – <name>'
# side banner on every page, extracted reversed ('ertneC nwoT –1 traP').
UPRIGHT_ONLY_COUNCILS = {"ku_ring_gai", "ashfield"}


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


# A running section/chapter title some DCP PDF generators print sideways down a
# page's margin as individually-positioned UPRIGHT glyphs (one letter per short
# line) rather than one rotated text run — so pdfplumber's own rotation flag
# (upright=False, see _upright_only above) does not catch it; every glyph reports
# upright=True, only its stacked position gives it away. Found 2026-09-05 on
# marrickville/part7-s3-sex-industry page 25: 38 words all sharing one narrow
# x-band (x0=557.9/x1=572.0), top strictly increasing, spelling "7.3 Sex Industry
# and Adult Business Premises" one letter per line. Left in place, these letters
# interleave into the real body text between lines, which broke detection of the
# very next section heading (7.3.8 never appeared anywhere in the extracted text)
# and silently swallowed 7 real sections (7.3.8–7.3.14) into whichever section was
# still open (which grew to 14,738 chars). Not council-scoped: the geometric
# signature — several short, mostly-alphabetic words stacked at one fixed narrow
# x — does not occur in ordinary DCP prose, so this runs for every council.
_MARGIN_LABEL_MIN_RUN = 6        # fewer than this is plausible coincidence, not a label
_MARGIN_LABEL_MAX_WIDTH = 20.0   # a single glyph's word-bbox width, generously bounded
_MARGIN_LABEL_MAX_CHARS = 2      # each stacked "word" is one letter (occasionally two)
_MARGIN_LABEL_MIN_ALPHA_FRACTION = 0.7  # excludes a stacked NUMERIC column (page
                                         # numbers, a fee schedule) — that is real
                                         # content, not a label, and must survive.
# ⚠ x-band + short-word alone is NOT enough — measured live 2026-09-05 on this
# same PDF: a genuine Objectives list where every bullet starts "To ..." puts
# 20+ short, alphabetic "To" words at one identical (x0, x1), a false positive
# for the checks above. What actually separates a rotated running label from
# that list is VERTICAL CONTINUITY: a real label's glyphs are drawn back to
# back with no line-leading (gap ~0, up to ~6.5pt at the label's own word
# spaces — measured on the true positive), while separate paragraph lines
# (the "To" bullets) sit a full line-height apart (measured >=12.6pt on the
# same page). Require the run to be contiguous under this gap, not just
# same-column and short.
_MARGIN_LABEL_MAX_GAP = 8.0


def find_vertical_margin_label_band(words: list[dict]) -> tuple[float, float] | None:
    """Detect a running margin-title band: a CONTIGUOUS run of
    >=_MARGIN_LABEL_MIN_RUN short, mostly-alphabetic words sharing one narrow
    (x0, x1) pair with near-zero vertical gaps between them (stacked glyphs of
    one rotated string, not separate list-item lines that merely start with the
    same short word at the same indent). Returns (x0, x1) padded by 0.5pt on
    each side, or None when no such band exists. Pure — takes pdfplumber's own
    extract_words() output, no PDF I/O."""
    bands: dict[tuple[int, int], list[dict]] = {}
    for w in words:
        text = w.get("text") or ""
        if not text or len(text) > _MARGIN_LABEL_MAX_CHARS:
            continue
        x0, x1 = w.get("x0"), w.get("x1")
        if x0 is None or x1 is None or (x1 - x0) > _MARGIN_LABEL_MAX_WIDTH:
            continue
        bands.setdefault((round(x0), round(x1)), []).append(w)
    for ws in bands.values():
        ws = sorted(ws, key=lambda w: w["top"])
        best_run: list[dict] = []
        run = [ws[0]]
        for prev, cur in zip(ws, ws[1:]):
            if cur["top"] - prev["bottom"] <= _MARGIN_LABEL_MAX_GAP:
                run.append(cur)
            else:
                if len(run) > len(best_run):
                    best_run = run
                run = [cur]
        if len(run) > len(best_run):
            best_run = run
        if len(best_run) < _MARGIN_LABEL_MIN_RUN:
            continue
        alpha_count = sum(1 for w in best_run if w["text"].isalpha())
        if alpha_count / len(best_run) < _MARGIN_LABEL_MIN_ALPHA_FRACTION:
            continue
        return (
            min(w["x0"] for w in best_run) - 0.5,
            max(w["x1"] for w in best_run) + 0.5,
        )
    return None


def _strip_vertical_margin_label(page: Any) -> Any:
    """Return `page` with a detected running margin-title band's characters
    removed, else `page` unchanged. See find_vertical_margin_label_band."""
    band = find_vertical_margin_label_band(page.extract_words() or [])
    if band is None:
        return page
    bx0, bx1 = band
    return page.filter(
        lambda obj: obj.get("object_type") != "char" or not (bx0 <= obj.get("x0", -1) <= bx1)
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

    Runs for every council: strips a running margin-title band rendered as
    stacked upright glyphs (see _strip_vertical_margin_label) before anything
    else, so it can't corrupt column detection or heading matching downstream.
    """
    page = _strip_vertical_margin_label(page)

    if council in UPRIGHT_ONLY_COUNCILS:
        page = _upright_only(page)

    if not council or council not in COUNCIL_COLUMN_CONFIGS:
        # Geometric two-column reader for councils without a header-pair anchor.
        # Runs AFTER the upright filter so rotated banner words are already gone
        # (they otherwise scramble the gutter reading). Returns None on any page
        # that is not clearly two-column, falling back to plain extraction.
        if council in GEOMETRIC_COLUMN_COUNCILS:
            columnar = _columnar_text(page)
            if columnar is not None:
                return columnar
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
        # Set when the text layer proved garbled and OCR page texts were
        # fetched — _page_text then serves these instead of pdfplumber's.
        self.ocr_pages: list[str] | None = None

    def _page_text(self, page: Any, page_num: int) -> str:
        if self.ocr_pages and 0 < page_num <= len(self.ocr_pages):
            return self.ocr_pages[page_num - 1]
        return _extract_page_text(page, self.council)

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
        self._maybe_route_via_ocr()
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
                _clean_page_text(self._page_text(p, i + 1), self.council)
                for i, p in enumerate(pdf.pages)
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

                text = self._page_text(page, page_num)
                text = _clean_page_text(text, self.council)
                # OCR mode: tables arrive inline in the page text (flattened
                # markup) — pdfplumber's table finder reads the garbled layer.
                page_tables = [] if self.ocr_pages else (page.extract_tables() or [])

                section_re = COUNCIL_SECTION_RE_OVERRIDES.get(self.council, self.SECTION_RE)
                # TOC / section-divider page guard: skip all section detection on a
                # full chapter TOC page or a section's own mini-TOC divider page.
                # The full-TOC case is absorbed into the current (parent) section
                # (existing, unchanged behaviour); a divider page is DISCARDED
                # outright rather than absorbed, since it fires mid-chapter and
                # would otherwise corrupt whatever real section is currently open
                # (Sol cross-review, HIGH, 2026-09-05). See classify_toc_or_divider_page.
                _suppress, _discard_page = classify_toc_or_divider_page(text, section_re)
                if _discard_page:
                    continue

                # Councils in MULTI_HEADING_COUNCILS carry more than one heading
                # per page; split so each heading-delimited block runs through the
                # SAME single-match logic below. Element 0 is the text before the
                # first heading and belongs to the section still open from the
                # previous page. Every other council gets [text] — one segment,
                # behaviour bit-identical to before.
                _segments = (
                    split_page_at_headings(text, section_re)
                    if (self.council in MULTI_HEADING_COUNCILS and not _suppress)
                    else [text]
                )

                # Tables are extracted per PAGE, not per segment. Attach them to
                # the first segment that has an open section and then clear, or a
                # 3-heading page would attach the same tables three times.
                _page_tables_left = page_tables
                for text in _segments:
                    match = None if _suppress else section_re.search(text)
                    if match:
                        new_code = match.group(1)
                        if current and is_running_header_repeat(
                            current["section_number"], new_code,
                            page_num, current["last_confirmed_page"],
                        ):
                            current["last_confirmed_page"] = page_num
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
                            "last_confirmed_page": page_num,
                        }

                    if current:
                        current["content"] += f"\n\n{text}"
                        if page_num not in current["pages"]:
                            current["pages"].append(page_num)
                        for tbl in _page_tables_left:
                            html = self._table_to_html(tbl)
                            if html:
                                current["tables"].append({"html": html, "page": page_num})
                        _page_tables_left = []  # this page's tables are placed
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

    def _maybe_route_via_ocr(self) -> None:
        """OCR fallback trigger (#832): a garbled text layer means every reader
        of it produces junk — route the chapter through the OCR endpoint and
        let the SAME splitter run over clean page texts. Called from BOTH the
        sequential path (extract) and the page-range path (extract_by_page_ranges);
        before 2026-07-29 only extract() checked, so manifest-driven councils
        (all of Ku-ring-gai) silently kept garbled text layers."""
        if self.ocr_pages is not None or not os.getenv("MODAL_OCR_URL", "").strip():
            return
        with pdfplumber.open(self.pdf_path) as _pdf:
            _raw = [_extract_page_text(p, self.council) or "" for p in _pdf.pages]
        # Empty text layers are as unreadable as garbled ones: scanned pages
        # yield no text at all (Marrickville part9 chapters, 2026-07-29) and
        # previously never triggered OCR because the garble heuristic needs
        # doubled glyphs to exist.
        empty_frac = (sum(1 for t in _raw if len(t.strip()) < 40) / len(_raw)) if _raw else 0.0
        if text_layer_garbled(_raw):
            print("    [OCR] garbled text layer detected — fetching OCR page texts")
        elif empty_frac >= PREFLIGHT_EMPTY_RATIO:
            print(f"    [OCR] {empty_frac:.0%} of pages have no text layer (scanned) — fetching OCR page texts")
        else:
            return
        self.ocr_pages = fetch_ocr_page_texts(self.pdf_path, expected_pages=len(_raw))
        if self.ocr_pages:
            print(f"    [OCR] using OCR text for {len(self.ocr_pages)} pages")

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
        self._maybe_route_via_ocr()
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
                    text = self._page_text(page, page_num)
                    text = _clean_page_text(text, self.council)
                    content += f"\n\n{text}"
                    pages_included.append(page_num)
                    if not self.ocr_pages:
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


# ── Per-row fidelity gate (2026-07 review-queue triage findings) ────────────
# The 2026-07 backlog reached review with 105/307 rows garbled and NULL
# fidelity_status everywhere: pdfplumber reads letter-spaced running headers as
# doubled glyphs (CoS "GGEENNEERRAALL"), interleaves two-column text
# (Ku-ring-gai), keys provisions off bare years, and can collapse a 43k-char
# section into a 2.7k stub when tables migrate. Every queue row now carries an
# explicit fidelity verdict at insert time — garbage flags itself instead of
# waiting for a human to notice.

_GARBLE_RUN = re.compile(r"(?:([A-Za-z])\1){3,}")
_JUNK_REF = re.compile(r"^(?:19|20)\d{2}$|^R\d$|^table", re.IGNORECASE)

# DQ-97 cause 5 (ku_ring_gai/section-a-part-6-multi-dwelling, found live 2026-09-07):
# a diagram/figure-label bleed ("PPeedddeess)ttrriiaann PPaatthhwwaayy", "Pedestrian
# Pathway" with every letter doubled) sitting MID-PARAGRAPH inside otherwise-real
# site-layout guidance text. strip_garbled_header_lines only drops a whole LINE
# dominated (>60%) by _GARBLE_RUN hits -- surrounded by enough legitimate prose,
# the same garbage phrase never reaches that ratio and the line survives whole.
# These patterns strip the PHRASE itself, wherever it sits, instead of requiring
# it to dominate its line.
#
# TWO independent signals, combined because neither alone caught everything in
# the real fixture (row id 69816): the PDF glued "(continue" directly onto
# "PPeedddeess)" with no separating character, so a WHOLE-TOKEN check sees one
# 19-char token ("continuePPeedddeess") that is not entirely doubled and
# correctly leaves it alone.
#
# _GARBLE_RUN_TOLERANT is the same idea as the pre-existing _GARBLE_RUN but
# tolerates a TRIPLED glyph mid-run ("ddd" in "PPeedddeess", an extraction
# quirk) via \1+ instead of \1 -- _GARBLE_RUN's strict alternating-pair form
# stops at the triple and only ever finds a 6-char "PPeedd" fragment.
# Substring matches of this tolerant pattern are blanked at >=8 chars -- the
# SAME threshold _garble_evidence already trusts as strong evidence on its
# own regardless of word-boundary position (its own docstring: 'bookkeeping's
# genuine "ookkee" run is 6 chars, safely under this bar). Verified against
# the full real dcp_review_queue corpus (11,314 rows, all councils) before
# shipping: 24 distinct substring matches at 8+ chars, every one a real
# doubled/tripled word or word-fragment ('PPeedddeess'='Pedes', 'ttrriiaann'=
# 'trian', 'nnddssccaappee'='ndscape', 'sseeccoonnddaa'='seconda[ry]'...),
# zero false positives.
_GARBLE_RUN_TOLERANT = re.compile(r"(?:([A-Za-z])\1+)+")

# _WHOLE_TOKEN_GARBLE catches the shorter, standalone tokens the 8-char
# substring bar above deliberately excludes (6-7 chars, e.g. 'kkkuuu'='ku'
# tripled, 'aanndd'='and' doubled) -- safe at that shorter length only
# because it is anchored to the ENTIRE token (^...$), not a substring: no
# real English word is composed edge-to-edge of doubled-letter runs
# ('bookkeeper' starts 'b' and ends 'r', both single, so the anchored match
# fails at the first character; same for 'committee', 'possession', 'coffee',
# 'street', and every other real word checked, see
# tests/test_garbled_phrase_strip.py). Verified against the full real corpus:
# 19 distinct whole-token matches at 6+ chars, all genuine doubled/tripled
# words ('aaannnddd'='and' tripled, 'gggaaaiii'='gai', 'ppaatthhwwaayy'=
# 'pathway', 'ssttoorreeyy'='storey'...), zero false positives.
_WHOLE_TOKEN_GARBLE = re.compile(r"^(?:([A-Za-z])\1+)+$")

# _SPACED_GARBLE_RUN catches a THIRD rendering of the same underlying defect
# that neither pattern above can see at all: single letters doubled AND
# separated by whitespace, spelling a word letter-by-letter-doubled
# ("SS TT RR EE EE TT" = "STREET"). The space between each pair breaks both
# other patterns' adjacency requirement entirely -- 0 hits on this text from
# either, verified directly -- so this is a genuinely separate blind spot.
#
# UNLIKE the two patterns above, this one has no structural safety argument
# ("no real word is doubled edge-to-edge") -- it is a pure heuristic on
# consecutive-token count, and Sol cross-review (HIGH 0.98, on push) found a
# real coincidence a lower bar could hit: "Lots AA BB CC are subject to
# separate controls" is a plausible real identifier scheme, not garbage, and
# a 3-token threshold could not tell them apart. Requires 5+ consecutive
# doubled-single-letter tokens (raised from 3 after that finding) -- Sol's
# own "AA BB CC" (3 tokens) and its natural 4-token extension "AA BB CC DD"
# both now correctly fall below the bar (verified), while the real fixture
# ("SS TT RR EE EE TT", 6 tokens) stays comfortably above it with margin.
# Re-verified against the full real corpus at the new threshold: 3 hits, all
# ku_ring_gai, all the same real "SS TT RR EE EE TT" occurrence and its
# sub-spans -- the canterbury_bankstown 3-token fragments a lower bar also
# caught ("hh aa oo" / "aa UU uu" / "ee ll ee uu") now correctly fall out
# too, the same direction as Sol's fix, not assumed safe either.
_SPACED_GARBLE_RUN = re.compile(r"(?:\b([A-Za-z])\1\b[ \t]+){4,}\b([A-Za-z])\2\b")


def _strip_garbled_phrase_spans(text: str) -> str:
    """Blank out doubled-glyph PHRASES wherever they sit in `text`, not just
    whole lines they dominate -- see the three regexes above for what each
    catches and why every one is safe against real English. Replaces a match
    with a single space (never deletes outright) so the real words on either
    side of the garbage don't fuse into one ('...(continued) Bad Examples...'
    must not become '...(continuedBad Examples...' once the phrase between
    them is gone)."""
    text = _SPACED_GARBLE_RUN.sub(" ", text)
    text = _GARBLE_RUN_TOLERANT.sub(lambda m: " " if len(m.group(0)) >= 8 else m.group(0), text)

    def _blank_if_whole_token_garbled(m: re.Match) -> str:
        token = m.group(0)
        if len(token) >= 6 and _WHOLE_TOKEN_GARBLE.match(token):
            return " "
        return token

    return re.sub(r"[A-Za-z]+", _blank_if_whole_token_garbled, text)


# ── Preflight layout check (2026-07-29) ─────────────────────────────────────
# prior-art-checked: the guard's hits are SEPP markdown parsers (different
# corpus, post-extraction parsing); no existing pre-extraction layout detector
# exists — this extends this file's own fidelity toolkit in place.
# Structural problems (two-column bodies, rotated banners, garbled layers,
# empty text layers) previously surfaced only AFTER extraction, as schema_fail
# artifacts or interleaved text the post-gates flagged. The preflight measures
# the layout BEFORE any parse so the operator summary names the problem class
# up front and the chapter is flagged suspect even when downstream heuristics
# would miss it (e.g. the Ashfield PC|DS two-column interleave, 2026-07-29).

PREFLIGHT_TWO_COL_RATIO = 0.20   # >=20% of text pages two-column -> flag
PREFLIGHT_EMPTY_RATIO = 0.30     # >=30% of pages with no text layer -> flag

# A source PDF whose front matter carries a council repeal stamp ("Repealed by
# WDCP 2015 Amendment No. 13 on 12 October 2020") is an archive document, not
# the in-force chapter. Extracting one silently replaces current controls with
# repealed ones — 20/23 Woollahra chapters shipped exactly that way before the
# 2026-07-29 re-source. Unlike the layout flags above this is a HARD REJECT:
# extract_chapter refuses the chapter and keeps needs_extraction=TRUE so the
# fix is always a registry re-point, never an approval.
# Line-anchored so amendment-history prose deeper in a sentence ("...was
# repealed by Amendment 5") cannot false-positive; only front matter is read.
PREFLIGHT_REPEALED_PAGES = 4
_REPEALED_STAMP = re.compile(r"^\s*repealed\s+by\b", re.IGNORECASE)

# Councils whose two-column/margin layout handling is PROVEN by a full source
# fidelity sweep — the geometric detector still measures them, but the suspect
# flag is suppressed (Waverley: margin-note layout, 2026-07-28 sweep = zero
# missing provisions / zero wrong values). Add a council here only with that
# level of evidence.
# blacktown + georges_river added 2026-07-30: preflight SUSPECT triage —
# multiple body pages sampled (part-a-car-parking pp21/31; both georges_river
# chapters pp16/26) read as clean single-column prose in correct order. The
# geometric detector false-positives on their heavily indented
# lettered/numbered sub-item lists (a)/b)/1./2. hanging indents read as a
# second lateral band). No extraction change needed — flag was noise.
PREFLIGHT_TWO_COL_VERIFIED = {"waverley", "blacktown", "georges_river"}


def detect_two_column_words(word_spans: list[tuple[float, float]], page_width: float) -> bool:
    """True when a page's word x-spans form two lateral bands with a clear
    gutter: both halves carry >=25% of words and <5% of words cross the middle
    band. Pure — word_spans are (x0, x1) pairs."""
    if len(word_spans) < 30 or page_width <= 0:
        return False
    mid_lo, mid_hi = page_width * 0.42, page_width * 0.58
    left = right = crossing = 0
    for x0, x1 in word_spans:
        if x0 < mid_lo and x1 > mid_hi:
            crossing += 1  # spans the gutter — single-column prose
        elif (x0 + x1) / 2 < page_width * 0.5:
            left += 1
        else:
            right += 1
    n = len(word_spans)
    return left / n >= 0.25 and right / n >= 0.25 and crossing / n < 0.05


# prior-art-checked: guard hits (council-config.ts, intelligence_brief.py,
# document_finder.py, ...) are council/document lookups sharing only generic
# tokens — no existing repeal-stamp/front-matter currency detector anywhere in
# the pipeline; this extends the file's own preflight toolkit in place.
def detect_repealed_stamp(front_page_texts: list[str]) -> str | None:
    """Return the repeal-stamp line found in a document's front matter, or
    None. Pure — front_page_texts are the first PREFLIGHT_REPEALED_PAGES
    pages' texts."""
    for text in front_page_texts:
        for line in (text or "").splitlines():
            if _REPEALED_STAMP.match(line):
                return line.strip()[:120]
    return None


def preflight_layout(pdf_path, council: str) -> dict:
    """Measure layout hazards before parsing. Returns counts + flag booleans.
    Never raises — a preflight failure must not block extraction (the post
    gates still stand); it reports {} on any error."""
    try:
        two_col = rotated = garbled = empty = text_pages = 0
        front_texts: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            total = len(pdf.pages)
            for idx, page in enumerate(pdf.pages):
                if idx < PREFLIGHT_REPEALED_PAGES:
                    try:
                        front_texts.append(page.extract_text() or "")
                    except Exception:
                        front_texts.append("")
                try:
                    words = page.extract_words() or []
                except Exception:
                    words = []
                if len(words) < 12:
                    empty += 1
                    continue
                text_pages += 1
                spans = [(w["x0"], w["x1"]) for w in words]
                if detect_two_column_words(spans, float(page.width or 0)):
                    two_col += 1
                chars = page.chars or []
                if chars:
                    non_upright = sum(1 for c in chars if not c.get("upright", True))
                    if non_upright / len(chars) > 0.15:
                        rotated += 1
                if _garble_evidence(page.extract_text() or ""):
                    garbled += 1
        report = {
            "total_pages": total,
            "text_pages": text_pages,
            "two_column_pages": two_col,
            "rotated_pages": rotated,
            "garbled_pages": garbled,
            "empty_text_pages": empty,
        }
        report["two_column_fail"] = (
            text_pages > 0
            and two_col / text_pages >= PREFLIGHT_TWO_COL_RATIO
            and council not in PREFLIGHT_TWO_COL_VERIFIED
        )
        report["empty_layer_fail"] = (
            total > 0 and empty / total >= PREFLIGHT_EMPTY_RATIO
        )
        report["repealed_stamp"] = detect_repealed_stamp(front_texts)
        return report
    except Exception as exc:  # pragma: no cover - defensive
        print(f"    [preflight] skipped ({exc})")
        return {}

# ── OCR fallback (issue #832, Phase-0 passed 2026-07-28) ────────────────────
# When a chapter's PDF text layer is garbled (letter-spaced doubled glyphs,
# two-column interleave — classes NO text-layer reader can fix), page texts
# are fetched from the Unlimited-OCR Modal endpoint (pixels, not text layer)
# and fed to the SAME section splitter. Fail-visible: endpoint unset or
# unreachable → None → extraction proceeds on the text layer exactly as
# before, and the fidelity gates flag the rows.

_OCR_DET_TAG = re.compile(
    r"<\|det\|>\s*[a-z_]+\s*\[\d+(?:,\s*\d+){3}\]\s*<\|/det\|>"   # full unit: tag + block type + coords
    r"|<\|/?(?:det|image(?:_caption)?)\|>|\[\d+(?:,\s*\d+){3}\]"  # any stragglers
    # The model also labels a region it read as non-textual (a map, a photo,
    # a figure) with a bare [Non-Text] placeholder. Same class of block marker
    # as the tags above and equally not council text, but it was never stripped,
    # so it landed mid-sentence in real rules -- measured 2026-09-09: 44 rows in
    # dcp_review_queue carried it (0 live in regulatory_provisions; the fidelity
    # gate had flagged them). Hyphen-optional and scoped-case-insensitive
    # because the model is not consistent about either; the (?i:...) group
    # keeps that leniency off the alternatives above, which match exactly.
    r"|(?i:\[Non[- ]?Text\])"
)
_OCR_ROW_TAG = re.compile(r"</tr>|<tr[^>]*>", re.IGNORECASE)
_OCR_CELL = re.compile(r"</?t[dh][^>]*>", re.IGNORECASE)
_OCR_TABLE_TAG = re.compile(r"</?(?:table|tbody|thead)[^>]*>", re.IGNORECASE)


def _garble_evidence(text: str) -> bool:
    """True when doubled-glyph runs are strong evidence of a garbled layer.

    Legitimate English carries short doubled runs INSIDE longer words
    ('bookkeeping' = b·ookkee·ping — un-doubled letters on both sides; Sol
    review of PR #836). Doubling artifacts double whole tokens ('nneeww',
    'GGEENNEERRAALL'), so their runs sit at word boundaries. Evidence:
      - any run of 8+ chars (4+ doubled pairs), or
      - 2+ short runs that are word-boundary-adjacent (not word-internal).
    """
    t = text or ""
    boundary_runs = 0
    for m in _GARBLE_RUN.finditer(t):
        if len(m.group(0)) >= 8:
            return True
        before = t[m.start() - 1] if m.start() > 0 else " "
        after = t[m.end()] if m.end() < len(t) else " "
        if not (before.isalpha() and after.isalpha()):
            boundary_runs += 1
    return boundary_runs >= 2


def normalise_ocr_page(text: str) -> str:
    """Model output → plain text the section splitter understands: detection
    tags dropped, table markup flattened to ' | '-separated rows. Empty cells
    are PRESERVED as empty delimiters — collapsing them shifts values into
    the wrong column (Sol review of PR #836: a setback under Zone B must not
    read as Zone A's)."""
    t = _OCR_DET_TAG.sub("", text or "")
    t = _OCR_ROW_TAG.sub("\n", t)
    # Cell BOUNDARIES (</td><td>) become single pipes — an empty cell keeps
    # its slot ('Setback |  | 3m'), so values never shift columns.
    t = re.sub(r"</t[dh]>\s*<t[dh][^>]*>", " | ", t, flags=re.IGNORECASE)
    t = _OCR_CELL.sub("", t)
    t = _OCR_TABLE_TAG.sub("\n", t)
    t = re.sub(r"[ \t]+\n", "\n", t)
    return re.sub(r"\n{3,}", "\n\n", t).strip()


def text_layer_garbled(page_texts: list[str]) -> bool:
    """True when any page's text layer carries STRONG doubled-glyph evidence
    — the trigger for routing the chapter through OCR. A single short run on
    a page is not enough (legitimate words like 'bookkeeping' match the bare
    pattern)."""
    return any(_garble_evidence(t) for t in page_texts)


# ── OCR call bounds ──────────────────────────────────────────────────────────
# prior-art-checked: reuse not viable because no shared HTTP client exists —
# r2_monitor.py, intelligence_brief.py and generate_conveyancing_report.py each
# build their own requests call with their own scalar timeout, so there is
# nothing to extend; this bounds THIS file's own OCR call in place. (Those three
# carry the same scalar-timeout assumption and are noted in the plan as needing
# the same treatment — a shared client is a separate refactor, not this fix.)
#
# ⚠ A SCALAR requests timeout CANNOT BOUND THIS CALL. In requests, `timeout=N`
# is the maximum gap BETWEEN BYTES and resets on every byte received — it is not
# a total deadline. Measured 2026-08-14 on the live sweep: an ESTABLISHED socket
# to the Modal endpoint (54.156.152.125:443, one of the six A records for
# lawrence-mcdonell--ocr-pdf.modal.run) sat open for 2472s against timeout=1800
# and never fired, at 0.00s CPU. A server that dribbles anything holds the
# nightly extraction open forever, silently, looking exactly like work.
#
# Bounding it needs a STRUCTURAL change, not a smaller number:
#   OCR_CONNECT_TIMEOUT/OCR_READ_TIMEOUT — a dead socket still fails fast
#   OCR_TOTAL_DEADLINE                   — streamed read against a monotonic
#                                          clock, the only thing that caps total
#                                          duration in one thread
OCR_CONNECT_TIMEOUT = 30       # seconds to establish
OCR_READ_TIMEOUT = 120         # seconds of SILENCE before giving up
# ⚠ NOT enforceable in-thread — see the note in fetch_ocr_page_texts.
# Kept as the value an EXTERNAL (subprocess) cap should use.
OCR_TOTAL_DEADLINE = 600
OCR_MAX_BYTES = 256 * 1024 * 1024  # refuse an unbounded body


def fetch_ocr_page_texts(pdf_path, expected_pages: int) -> list[str] | None:
    """POST the PDF to the Modal OCR endpoint; return normalised per-page
    texts, or None on ANY failure (caller stays on the text layer). The
    response must carry EXACTLY expected_pages entries — a short response
    would serve OCR text for the wrong source pages (Sol review of PR #836).

    Bounded by OCR_TOTAL_DEADLINE wall-clock, not by requests' timeout — see
    the note above for why the latter cannot do it.
    """
    url = os.getenv("MODAL_OCR_URL", "").strip()
    token = os.getenv("MODAL_OCR_TOKEN", "").strip()
    if not url or not token:
        print("    [OCR] MODAL_OCR_URL/TOKEN not set — staying on text layer")
        return None
    try:
        import json as _json
        import time as _time

        import requests

        _t0 = _time.monotonic()
        with requests.post(
            url,
            data=open(pdf_path, "rb").read(),
            headers={"X-OCR-Token": token},
            timeout=(OCR_CONNECT_TIMEOUT, OCR_READ_TIMEOUT),
            stream=True,
        ) as resp:
            if resp.status_code != 200:
                print(f"    [OCR] endpoint returned {resp.status_code} — staying on text layer")
                return None
            # ⚠ TOTAL-DURATION BOUNDING IS NOT POSSIBLE HERE. THREE MECHANISMS
            # WERE BUILT AND MEASURED ON 2026-08-14; ALL THREE FAILED:
            #   1. iter_content(65536) + a clock between chunks — blocks until
            #      64KB accumulates, so the check never runs. A 2s deadline took
            #      100s against a server writing 1 byte per 0.2s, and only then
            #      because the server stopped.
            #   2. iter_content(None) — urllib3 read(None) reads to EOF, so it
            #      blocks forever. Strictly worse.
            #   3. A threading.Timer closing resp.raw underneath the blocked
            #      read — did not unblock it. On Windows, closing a socket from
            #      another thread does not reliably interrupt a blocked recv.
            # Any byte count blocks until that many bytes arrive, so the loop
            # body — wherever a clock would live — simply does not execute.
            #
            # WHAT IS BOUNDED HERE: silence. OCR_READ_TIMEOUT caps the gap
            # between bytes, which is the common real failure (the endpoint dies
            # or stops responding). That is worth having and the old scalar
            # timeout=1800 made it 30 minutes instead of 2.
            #
            # WHAT IS NOT: a server that dribbles forever. Bounding THAT needs an
            # external cap — run the fetch in a subprocess and kill it. See
            # P6.0 in ce-provisions-pipeline-repair-2026-08.md; the measurement
            # harness for the Marrickville gate is the reference implementation
            # (one subprocess per chapter, hard wall-clock cap, TIMEOUT recorded
            # and counted rather than dropped). Do not re-attempt an in-thread
            # deadline — it has been tried three ways and measured each time.
            chunks, size = [], 0
            for chunk in resp.iter_content(65536):
                if not chunk:
                    continue
                size += len(chunk)
                if size > OCR_MAX_BYTES:
                    print(f"    [OCR] response exceeded {OCR_MAX_BYTES:,} bytes — staying on text layer")
                    return None
                chunks.append(chunk)
            body = b"".join(chunks)
        _elapsed = _time.monotonic() - _t0
        # Always report duration: a hang you never timed is a hang you cannot see.
        print(f"    [OCR] endpoint responded in {_elapsed:.0f}s ({size:,} bytes)")
        pages = _json.loads(body.decode("utf-8", "replace")).get("pages")
        if not isinstance(pages, list) or not pages:
            print("    [OCR] endpoint returned no pages — staying on text layer")
            return None
        if len(pages) != expected_pages:
            print(f"    [OCR] page count mismatch ({len(pages)} vs {expected_pages} in PDF) — staying on text layer")
            return None
        return [normalise_ocr_page(p) for p in pages]
    except Exception as e:
        print(f"    [OCR] fetch failed ({e}) — staying on text layer")
        return None


def strip_garbled_header_lines(text: str | None) -> str | None:
    """Drop lines dominated by doubled-glyph runs (letter-spaced running
    headers whose text layer duplicates every glyph). Only whole LINES are
    removed, and only when the doubled run covers most of the line's letters —
    body text containing a legitimate 'LLoyd' or 'III' is untouched.

    Runs _strip_garbled_phrase_spans FIRST (DQ-97 cause 5) to also catch a
    doubled-glyph PHRASE that sits mid-paragraph, surrounded by enough real
    prose that it never dominates its line and so would otherwise survive
    this function entirely -- see that function's docstring."""
    if not text:
        return text
    text = _strip_garbled_phrase_spans(text)
    kept = []
    for line in text.splitlines():
        letters = sum(ch.isalpha() for ch in line)
        doubled = sum(len(m.group(0)) for m in _GARBLE_RUN.finditer(line))
        if letters >= 8 and doubled / max(letters, 1) > 0.6:
            continue
        kept.append(line)
    return "\n".join(kept)


# Reasons enqueue_review_changes will auto-reject a 'failed' row for, without a
# human click -- see the comment at its call site. Deliberately excludes
# section_collapsed and oversize_new_provision: those are SIZE heuristics that
# can legitimately fire on a genuine amendment, not certain-garbage detectors.
_AUTO_REJECT_REASONS = {"garbled_glyphs", "junk_ref", "emptied_by_strip"}


def classify_row_fidelity(ref: str | None, old_text: str | None,
                          new_text: str | None,
                          change_type: str = "changed") -> tuple[str, str | None]:
    """Verdict for one queue row: ('ok', None) or ('failed', reason).

    Checks (each proven against a real 2026-07 defect, plus Sol review of
    PR #830):
      garbled_glyphs — doubled-glyph runs survived the header strip
      junk_ref       — provision keyed off a bare year / zone code / 'table'
      emptied_by_strip — a non-removal whose stripped text is empty (the
                          extraction produced ONLY header garbage; approving
                          would erase the provision)
      section_collapsed — new text < 30% of a substantial old text (content
                          migrated to another key; approving would gut it)
      oversize_new_provision — a brand-new >20k-char provision (a mis-keyed
                          section split, not a genuine new clause)
    """
    reasons = []
    short = (ref or "").split("__")[-1]
    if _garble_evidence(new_text or ""):
        reasons.append("garbled_glyphs")
    if _JUNK_REF.match(short):
        reasons.append("junk_ref")
    if change_type != "removed" and new_text is not None and not new_text.strip():
        reasons.append("emptied_by_strip")
    if (old_text and new_text is not None and len(old_text) > 2000
            and len(new_text) < 0.3 * len(old_text)):
        reasons.append("section_collapsed")
    if not old_text and new_text and len(new_text) > 20000:
        reasons.append("oversize_new_provision")
    if reasons:
        return "failed", "+".join(reasons)
    return "ok", None


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
    pf = review_data.get("preflight") or {}
    if pf.get("two_column_fail"):
        return (f"preflight_two_column ({pf.get('two_column_pages')}/"
                f"{pf.get('text_pages')} text pages two-column — interleave likely)")
    if pf.get("empty_layer_fail"):
        return (f"preflight_empty_layer ({pf.get('empty_text_pages')}/"
                f"{pf.get('total_pages')} pages without text layer — scanned source)")
    return None


# Councils whose pages carry MORE THAN ONE section heading. _extract_sequential
# takes one heading per page (section_re.search), so on these the 2nd and 3rd
# headings are swallowed into the first heading's content and their clauses
# collide onto the wrong ref. Marrickville measured 2026-08-14: fixing only the
# SECTION_RE recovered 5 of ~10 real sections in part2-s11-fencing, because p5
# holds 2.11/2.11.1, p6 holds 2.11.3/2.11.4/2.11.4.1 and p9 holds 2.11/2.11.6.
#
# OPT-IN, default off. Every other council keeps the exact single-match path,
# so the blast radius of this change is one council. Leichhardt (same era and
# format, 3,600 served provisions) and Parramatta were probed read-only and
# extract correctly today — 8 and 644 real sections — so widening this is not
# justified by evidence and must not be done without measuring the council first.
MULTI_HEADING_COUNCILS = {"marrickville"}


def fidelity_gate_enabled() -> bool:
    """Whether to grade queued rows against their source PDF. Default ON.

    ⚠ This used to be gated on AI_EXTRACTION, and that was the wrong flag. Of the
    four AI_EXTRACTION sites, three are legitimate — it swaps the whole extractor
    for an LLM (~L1130), selects that path per council (~L2616), and runs
    coverage/truncation railguards that only mean anything for LLM output
    (~L2742). But the fidelity gate grades rows that are ALREADY QUEUED, and
    "does this text appear in the council's own document" is the same question
    whichever extractor produced the row.

    The cost of that coupling, measured 2026-08-14: of 19,649 review-queue rows
    ever written, **12 carry a fidelity_source_quote** — 0.06% — because
    AI_EXTRACTION is not set on the Railway dcp-extract service and nobody was
    going to enable an LLM extractor in production just to get verification.
    The one check that compares our output against the source has effectively
    never run.

    OPT-OUT, not opt-in. A verification that is off by default is exactly the
    shape this work exists to remove. Set DCP_FIDELITY_GATE=0 to disable, and
    only with a reason.
    """
    return os.getenv("DCP_FIDELITY_GATE", "").strip().lower() not in (
        "0", "false", "no", "off",
    )


def split_page_at_headings(text: str, section_re) -> list[str]:
    """Split one page's text into [pre-heading remainder, heading-1 block, ...].

    Element 0 is whatever precedes the first heading — it belongs to the section
    still open from the previous page, and is '' when the page opens on a
    heading. Each later element starts exactly at a heading match, so the
    caller's existing single-match logic works on it unchanged.

    Pure. Returns [text] when there is nothing to split, so the caller's
    behaviour is bit-identical to before on 0- and 1-heading pages.
    """
    matches = list(section_re.finditer(text))
    if len(matches) < 2:
        return [text]
    out = [text[: matches[0].start()]]
    for i, m in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        out.append(text[m.start(): end])
    return out


def suspect_alert_key(review_data: dict) -> str | None:
    """Stable identity of a SUSPECT condition: (content_hash, reason).

    None when the chapter is not suspect. Pure.

    Both halves are load-bearing (see migrations/066_suspect_alert_dedup.sql):
    hash alone would silence a chapter whose PDF is unchanged but whose failure
    MODE changed; reason alone would re-alert on every re-export of an
    identical document.
    """
    reason = suspect_reason(review_data)
    if not reason:
        return None
    return f"{review_data.get('content_hash') or 'nohash'}::{reason}"


def unalerted_suspects(suspect: list[dict], last_keys: dict) -> list[dict]:
    """Those whose condition is NEW or CHANGED since the last alert. Pure.

    `last_keys` maps (council, chapter_key) -> last_suspect_alert_key, absent or
    None meaning never alerted. Between 1 and 13 Aug 2026 the same two chapters
    alerted byte-identically every day because there was no such memory; the
    channel stopped being read, and the numeric-value-change alerts sharing it
    went unactioned for weeks.
    """
    fresh = []
    for ch in suspect:
        key = suspect_alert_key(ch)
        if key is None:
            continue
        if last_keys.get((ch.get("council"), ch.get("chapter_key"))) != key:
            fresh.append(ch)
    return fresh


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

# DQ-98 stability guard (registered .claude/DATA_QUALITY_TRACKER.md, 2026-09-07;
# real crash: Railway dcp-extract, 2026-09-06 03:21 UTC, exit -9/SIGKILL, on
# canterbury_bankstown/chapter-7-6-belmore-and-lakemba, 139,006,750 bytes).
# DCPExtractor and preflight_layout() each open the downloaded PDF with
# pdfplumber and hold every page's char/line/table/image objects in memory for
# the pass's lifetime; a file this large exhausts the container and the OS
# kills the WHOLE process — not just this chapter. Confirmed live 2026-09-08/09
# (three separate cron firings, all exit -9): the crash takes every OTHER
# chapter queued in the same run down with it, so none of that night's batch
# gets extracted, not only the oversized one.
# Same 30MB heuristic as scripts/dq_probe_oversized_pdf_oom_risk.py (kept as a
# separate literal, not imported — that script is a standalone advisory probe,
# not a module meant to be imported into the pipeline it's reporting on).
# This is NOT the DQ-98 fix (chunked extraction, not yet built, real design
# risk around clauses straddling a chunk boundary) — it only stops one
# oversized chapter from silently crash-looping the entire nightly batch.
# needs_extraction stays TRUE (existing failure convention below), so the
# chapter keeps surfacing here, loudly, every run until the real fix ships.
OVERSIZED_PDF_SKIP_BYTES = 30 * 1024 * 1024


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

        pdf_bytes = pdf_path.stat().st_size
        print(f"    Downloaded {pdf_bytes:,} bytes")

        if pdf_bytes > OVERSIZED_PDF_SKIP_BYTES:
            print(
                f"    [SKIP] {pdf_bytes:,} bytes exceeds the "
                f"{OVERSIZED_PDF_SKIP_BYTES:,}-byte OOM-risk threshold (DQ-98) — "
                f"skipping this chapter to protect the rest of tonight's batch. "
                f"needs_extraction stays TRUE; this chapter needs chunked "
                f"extraction (DQ-98, not yet built) to ever complete."
            )
            # Sol HIGH 0.96: a skipped chapter must leave a DB-visible,
            # distinct trace, not just a log line -- otherwise stale
            # regulatory content keeps being served with zero signal that a
            # source update was ever seen and silently dropped.
            # prior-art-checked: reuse not viable as a function call -- this
            # DELIBERATELY reuses the SAME last_suspect_alert_key/_at columns,
            # the SAME send_telegram() sender, and the SAME dedup-by-key idea
            # the existing suspect-alert block in main() already uses (below,
            # ~line 4040), but that block only fires for chapters that made
            # it through extract_chapter() successfully with review_data
            # populated -- an oversized-skip never reaches that point (it
            # returns before DCPExtractor even runs), so there is no shared
            # function to call into; inlining the same pattern here is the
            # only way to alert on a chapter that specifically never extracts.
            # A distinct "oversized_pdf" reason string so this can never
            # collide with an extraction-produced suspect_reason. Keyed to
            # content_hash (already on the registry row, reflects the CURRENT
            # source PDF regardless of extraction success) so a re-check of
            # the SAME too-big file doesn't re-alert every night -- the exact
            # failure mode unalerted_suspects() above was built to stop --
            # but a genuinely NEW oversized replacement does alert. Skipped
            # entirely under dry_run: that flag's whole contract is "no DB
            # writes".
            if not dry_run:
                # prior-art-checked: reuse not viable -- this fixes the
                # is_active filter on THIS SAME guard's own SELECT/UPDATE
                # (added a few commits ago on this branch), not a new query
                # against a different table; the flagged files' overlap is
                # shared domain vocabulary (chapter/registry/suspect), not a
                # reusable function for this specific read-then-conditionally
                # -write.
                # prior-art-checked: reuse not viable -- this is a third,
                # incremental hardening of the SAME guard block above on this
                # SAME branch (FOR UPDATE row-locking, added to close a race
                # Sol found in the immediately-prior is_active fix), not a new
                # transaction/extraction capability; the sepp_full_text_
                # extraction/* matches surfaced by the prior-art scan are an
                # unrelated one-off import pipeline, not something this
                # ongoing DCP chapter registry guard could reuse.
                # Sol MEDIUM 0.94: a chapter can be deactivated (is_active=FALSE)
                # between batch selection and this code running -- without the
                # filter, this block would still alert about and mutate an
                # inactive row's status for a chapter no longer served. Both
                # the read and the write are scoped to is_active=TRUE; if the
                # row isn't active any more, skip the alert AND the write
                # entirely rather than acting on stale membership.
                # Sol MEDIUM 0.98 (next push): the is_active check above still
                # left a time-of-check/time-of-use gap -- deactivation landing
                # between the SELECT and the Telegram send would still fire the
                # alert (already decided), even though the later UPDATE would
                # then correctly match zero rows. FOR UPDATE closes it: it row-
                # locks this one chapter from the SELECT through conn.commit(),
                # so a concurrent `is_active = FALSE` write on the SAME row
                # blocks until this transaction ends -- no other transaction
                # can flip this row's is_active while we're deciding on it.
                # Deliberately still send-then-write, not write-then-send (a
                # single atomic "UPDATE ... RETURNING" was considered and
                # rejected: it would mark the row alerted before the Telegram
                # call succeeds, silently swallowing a failed send instead of
                # retrying it next run -- the exact failure mode the EXISTING
                # suspect-alert block's own comment above warns against).
                skip_key = f"{chapter.get('content_hash') or 'nohash'}::oversized_pdf({pdf_bytes})"
                try:
                    _c = conn.cursor()
                    _c.execute(
                        "SELECT last_suspect_alert_key FROM dcp_chapter_registry "
                        "WHERE id = %s AND is_active = TRUE FOR UPDATE",
                        (chapter_id,),
                    )
                    row = _c.fetchone()
                    if row is None:
                        print(f"    [info] {council}/{chapter_key} no longer active — "
                              f"skip-status not recorded")
                        conn.rollback()
                    else:
                        if row[0] != skip_key:
                            try:
                                from run_monitors import send_telegram
                                send_telegram(
                                    f"⚠️ dcp-extract: {council}/{chapter_key} SKIPPED — "
                                    f"{pdf_bytes:,} bytes exceeds the {OVERSIZED_PDF_SKIP_BYTES:,}-"
                                    f"byte OOM-risk guard (DQ-98). Source content may be stale "
                                    f"until chunked extraction ships."
                                )
                            except Exception as exc:
                                print(f"    [warn] oversized-skip Telegram alert not sent: {exc}")
                        _c.execute(
                            "UPDATE dcp_chapter_registry "
                            "SET last_suspect_alert_key = %s, last_suspect_alert_at = NOW() "
                            "WHERE id = %s AND is_active = TRUE",
                            (skip_key, chapter_id),
                        )
                        conn.commit()  # releases the FOR UPDATE row lock
                    _c.close()
                except Exception as exc:
                    print(f"    [warn] could not record oversized-skip status: {exc}")
                    conn.rollback()
            return False, None

        # 2. Extract sections
        cur = conn.cursor()
        document_id = resolve_document_id(cur, council, chapter_key, dcp_name)
        print(f"    document_id: {document_id}")

        extractor = DCPExtractor(pdf_path, document_id, council=council)

        preflight = preflight_layout(pdf_path, council)
        if preflight:
            print(
                f"    Preflight: {preflight['text_pages']} text pages — "
                f"two-column {preflight['two_column_pages']}, rotated {preflight['rotated_pages']}, "
                f"garbled {preflight['garbled_pages']}, empty-layer {preflight['empty_text_pages']}"
            )
            if preflight.get("two_column_fail"):
                print("    [preflight] ⚠ TWO-COLUMN body layout — text-order interleave likely; "
                      "review output before approving")
            if preflight.get("empty_layer_fail"):
                print("    [preflight] ⚠ EMPTY TEXT LAYERS on many pages — scanned source; "
                      "OCR routing required for full coverage")
            if preflight.get("repealed_stamp"):
                # Hard reject — an archive document must never reach extraction,
                # let alone the review queue. needs_extraction stays TRUE so the
                # chapter keeps surfacing until the registry URL is re-pointed
                # at the in-force version (Woollahra failure class, 2026-07-29).
                print(f"    [preflight] ✗ REPEALED SOURCE: \"{preflight['repealed_stamp']}\"")
                print("    [preflight] chapter REJECTED — re-point council_url at the "
                      "in-force chapter, re-mirror, then re-run")
                cur.close()
                return False, None

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
                "preflight": preflight,
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
        # Only 'pending' rows are cleared — approved history is preserved.
        cur.execute(
            "DELETE FROM dcp_review_queue "
            "WHERE council = %s AND chapter_key = %s AND status = 'pending'",
            (council, chapter_key),
        )
        # Prior rejections are SUPERSEDED by this fresh extraction, not kept
        # blocking: the content hash is the source PDF's hash, so an
        # extractor-side fix re-extracts under the SAME hash and hash-scoped
        # blocking alone would wedge the chapter forever (Sol review of
        # PR #830). Rows stay in the table as labelled audit history.
        cur.execute(
            "UPDATE dcp_review_queue SET status = 'superseded' "
            "WHERE council = %s AND chapter_key = %s AND status = 'rejected'",
            (council, chapter_key),
        )
        for change_type, ref, old_t, new_t, old_p, new_p, has_num in rows:
            # Fidelity gate: strip doubled-glyph running headers, then verdict the row.
            # A row-level 'failed' verdict whose reason is EXCLUSIVELY one of the three
            # near-certain defect classes (garbled_glyphs/junk_ref/emptied_by_strip --
            # OCR-doubled glyphs, a bare year/zone code as the ref, or text that strips
            # to nothing) lands pre-rejected (status='rejected', reason attached)
            # instead of making a human click reject on something already diagnosed.
            # It still blocks the chapter's commit under the current content hash
            # (dcp_commit_approved's rejected+hash-match check) and the watchdog
            # still reports it -- only the manual click is removed.
            #
            # section_collapsed and oversize_new_provision stay 'pending' even when
            # 'failed' (Sol cross-review, MEDIUM 0.91): both are SIZE heuristics, not
            # content-garbage detectors -- a genuine large new schedule or a genuine
            # substantial restructure can trigger them, and classify_row_fidelity's own
            # test suite already carries a near-miss guard for this
            # (test_small_section_shrink_is_not_collapse). Auto-rejecting a heuristic
            # that can be right about a genuine amendment would remove it from the
            # pending-review workflow with no human ever seeing it.
            #
            # A chapter-level-only suspect_reason (count_drop/coverage_fail/schema_fail/
            # etc, with no row-level failure) still lands 'pending': that flag is about
            # missing/incomplete extraction, not bad content IN this row, and needs a
            # human's judgment on the whole batch -- there's nothing here to auto-reject.
            new_t = strip_garbled_header_lines(new_t)
            fidelity, row_reason = classify_row_fidelity(ref, old_t, new_t, change_type)
            merged_reason = "; ".join(x for x in (reason, row_reason) if x) or None
            reason_tags = set((row_reason or "").split("+")) if row_reason else set()
            auto_reject = fidelity == "failed" and reason_tags and reason_tags <= _AUTO_REJECT_REASONS
            row_status = "rejected" if auto_reject else "pending"
            cur.execute(
                """
                INSERT INTO dcp_review_queue
                    (council, chapter_key, document_id, ref_number, change_type,
                     old_text, new_text, old_page, new_page, has_numeric_change,
                     source_content_hash, suspect_reason, is_full_replace, status,
                     fidelity_status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (council, chapter_key, document_id, ref, change_type,
                 old_t, new_t, old_p, new_p, has_num, content_hash, merged_reason,
                 is_full_replace, row_status, fidelity),
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


# ── Fidelity gate integration (the --review post-enqueue grading pass) ───────
# prior-art-checked: not a new capability -- this extracts main()'s existing
# inline try/except block verbatim into a named function so it becomes
# independently testable (Sol cross-review, MEDIUM 0.99, 2026-09-09);
# gate_module.gate_chapter() and dcp_chapter_registry are both pre-existing
# and unchanged by this refactor, only relocated + given a stubbable seam.

def run_fidelity_gate(
    conn, s3, review_chapters: list[dict], gate_module
) -> tuple[int, int, int, list[tuple[str, str]]]:
    # prior-art-checked: not a new capability -- widens this same, already-
    # justified function's return contract (adds an unchecked-pairs list)
    # per Sol cross-review, HIGH 0.99 / MEDIUM 0.96, 2026-09-09. No new data
    # source, no new query beyond the one this function already ran.
    """Grade every chapter just enqueued by --review against its source PDF.

    Extracted from main()'s inline try/except block: the tuple-unpacking
    crash fix that motivated this file was only verified by calling
    gate_module.gate_chapter() directly, which cannot catch a SECOND
    unpacking regression at THIS call site -- only calling this function,
    with gate_module stubbed, can. gate_module is passed in (not imported
    here) so a test can substitute a fake with a literal 3-tuple return.

    Returns (grounded, flagged, skipped_not_actionable, unchecked) --
    unchecked lists every (council, chapter_key) pair that was enqueued
    this run but could NOT be graded (a malformed identifier, or no
    active registry row with a source PDF). Sol cross-review (HIGH 0.99 /
    MEDIUM 0.96): silently `continue`-ing on either case let a caller's
    success summary ("N grounded, M flagged") hide chapters that were
    never actually checked at all -- the caller is responsible for
    surfacing this list, not silently dropping it. A malformed identifier
    (missing/non-string council or chapter_key) is recorded here rather
    than raised, because one bad dict in review_chapters must not prevent
    every OTHER chapter in the same run from being graded.

    Raises on the first unexpected failure from gate_module.gate_chapter()
    itself -- callers keep the same advisory try/except they already had;
    this function's job is only to be independently testable and to make
    partial coverage visible, not to change the failure-handling contract."""
    pairs: set[tuple[str, str]] = set()
    unchecked: list[tuple[str, str]] = []
    for ch in review_chapters:
        council = ch.get("council")
        chapter_key = ch.get("chapter_key")
        if not isinstance(council, str) or not council or not isinstance(chapter_key, str) or not chapter_key:
            unchecked.append((str(council), str(chapter_key)))
            continue
        pairs.add((council, chapter_key))

    gcur = conn.cursor()
    g_tot = f_tot = s_tot = 0
    try:
        for g_council, g_chapter in sorted(pairs):
            gcur.execute(
                "SELECT r2_current_path FROM dcp_chapter_registry "
                "WHERE council=%s AND chapter_key=%s AND r2_current_path IS NOT NULL "
                "AND is_active = TRUE",
                (g_council, g_chapter),
            )
            r2row = gcur.fetchone()
            if not r2row:
                unchecked.append((g_council, g_chapter))
                continue
            # gate_chapter returns (grounded, flagged, skipped_not_actionable) as of
            # the 2026-09-07 auto-scoping fix (#1057) -- the pre-fix version of this
            # call site still expected a 2-tuple, so every --review run crashed here
            # (caught only by the caller's advisory try/except, which swallowed it as
            # "fidelity gate skipped"), leaving every freshly enqueued row ungraded.
            # Found live 2026-09-09 on a real ashfield re-extract.
            g, f, s = gate_module.gate_chapter(gcur, s3, g_council, g_chapter, r2row[0])
            conn.commit()
            g_tot += g
            f_tot += f
            s_tot += s
    finally:
        gcur.close()
    return g_tot, f_tot, s_tot, unchecked


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

        # prior-art-checked: reuse not viable as-is — this CALLS the existing grader
        # (dcp_fidelity_gate.gate_chapter) rather than reimplementing it; the flagged
        # sepp_full_text_extraction scripts are a different pipeline. Only the wiring is new.
        # Auto-grade the freshly enqueued rows against their source PDFs (fidelity gate), so
        # the reviewer sees only flagged rows with a source quote instead of the whole batch.
        # Lazy import dodges the circular import (dcp_fidelity_gate imports this module).
        # Advisory: a grading failure never fails the extract — the rows are still queued.
        # ⚠ Gated on fidelity_gate_enabled(), NOT on AI_EXTRACTION. See that
        # function: the old coupling meant this ran on 12 of 19,649 rows ever.
        # One R2 download + pdfplumber text extraction per chapter, via the RAW
        # page path — deliberately not the OCR-aware one, so this cannot inherit
        # the unbounded Modal call.
        if fidelity_gate_enabled():
            try:
                import dcp_fidelity_gate as _gate
                g_tot, f_tot, s_tot, unchecked = run_fidelity_gate(conn, s3, review_chapters, _gate)
                print(f"  Fidelity gate: {g_tot} grounded, {f_tot} flagged for human review, "
                      f"{s_tot} skipped (not actionable content).")
                # Sol cross-review HIGH 0.99, 2026-09-09: a chapter with no active
                # registry row (or a malformed identifier) was silently dropped —
                # the summary line above looked like a clean pass either way. Make
                # partial coverage visible instead of letting totals imply completeness.
                if unchecked:
                    # Sol cross-review LOW 0.99: this wording must match the query in
                    # run_fidelity_gate exactly -- it rejects an active row with a NULL
                    # r2_current_path too, not just a missing/inactive row.
                    print(f"  ⚠ {len(unchecked)} chapter(s) NOT graded (no matching active "
                          f"registry row with a source PDF, or a malformed identifier):")
                    for _c, _k in unchecked:
                        print(f"      - {_c}/{_k}")
            except Exception as exc:  # noqa: BLE001 — grading is advisory; keep the queued rows
                print(f"  [warn] fidelity gate skipped ({exc}); rows queued but ungraded.")

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

            # prior-art-checked: reuse not viable because no alert-state store
            # exists anywhere — grepped scripts/, services/, migrations/ and
            # DB_SCHEMA.md for alert_state/alert_log/last_alerted/notification/
            # dedup and every hit is unrelated (provision de-duplication, or the
            # word "suppressed" in report prose). dcp_watchdog.py has severity
            # tiers but no memory of what it has already said. This extends this
            # file's own alert path in place and stores state on the registry
            # row that already holds this chapter's operational state.
            #
            # Best-effort push so the quarterly run alerts, not just logs. Reuses
            # run_monitors.send_telegram (no-ops when TELEGRAM_* unset).
            #
            # Only NEW or CHANGED conditions are pushed. The console block above
            # still lists every suspect chapter every run — suppression applies
            # to the alert, not to the record. A still-true condition continues
            # to surface in the WEEKLY dcp_watchdog (which reports the same
            # review-blocked chapters, with their true age since 2026-08-14), so
            # suppressed is not silent. If that watchdog check is ever removed,
            # remove this suppression with it.
            fresh = []
            last_keys: dict = {}
            try:
                _c = conn.cursor()
                _c.execute(
                    "SELECT council, chapter_key, last_suspect_alert_key "
                    "FROM dcp_chapter_registry WHERE last_suspect_alert_key IS NOT NULL"
                )
                last_keys = {(a, b): k for a, b, k in _c.fetchall()}
                _c.close()
                fresh = unalerted_suspects(suspect, last_keys)
            except Exception as exc:
                # Never let dedup bookkeeping suppress a real alert: on ANY
                # failure fall back to alerting about everything.
                print(f"  [warn] suspect-alert dedup unavailable ({exc}) — alerting on all")
                fresh = suspect

            repeats = len(suspect) - len(fresh)
            if repeats:
                print(f"  [alert] {repeats} unchanged condition(s) suppressed "
                      f"(already alerted; still listed above and in the weekly watchdog)")

            alert = build_suspect_alert(args.council or "all", fresh) if fresh else None
            if alert:
                try:
                    from run_monitors import send_telegram
                    send_telegram(alert)
                except Exception as exc:  # never let alerting break the run
                    print(f"  [warn] SUSPECT Telegram alert not sent: {exc}")
                else:
                    # Record ONLY after a successful send, so a failed push
                    # re-alerts next run instead of being silently swallowed.
                    try:
                        _c = conn.cursor()
                        for ch in fresh:
                            _c.execute(
                                "UPDATE dcp_chapter_registry "
                                "SET last_suspect_alert_key = %s, last_suspect_alert_at = NOW() "
                                "WHERE council = %s AND chapter_key = %s",
                                (suspect_alert_key(ch), ch.get("council"), ch.get("chapter_key")),
                            )
                        conn.commit()
                        _c.close()
                    except Exception as exc:
                        print(f"  [warn] could not record suspect-alert keys: {exc}")

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
