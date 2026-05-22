#!/usr/bin/env python3
"""
Insert bicycle parking requirements from council DCPs into dcp_setback_controls.

Every council gets a row. Three categories:
  1. Verified numeric rate (value_min set, needs_review=False)
  2. No requirement for residential (value_min=NULL, condition explains)
  3. Defers to external standard (value_min=NULL, source_text has literal DCP quote)

Usage:
    python scripts/insert_bicycle_parking.py --dry-run
    python scripts/insert_bicycle_parking.py
"""
import argparse
import os
import sys
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

EXTRACTION_METHOD = "manual"

# ─────────────────────────────────────────────────────────────────────
# Per-council bicycle parking data.
# Each entry is a dict with fields matching dcp_setback_controls columns.
# Rows for councils already in DB (city_of_sydney, leichhardt) are skipped
# by the dedup check.
#
# value_min=None means the DCP has no numeric rate — the source_text
# contains the literal DCP position (defer to standard / no requirement).
# ─────────────────────────────────────────────────────────────────────

BICYCLE_ROWS = [
    # ══════════════════════════════════════════════════════════════
    # VERIFIED NUMERIC RATES
    # ══════════════════════════════════════════════════════════════

    # --- Woollahra (E1.6.2 Table 4) ---
    {
        "lga": "woollahra",
        "dev_type": "residential_flat_building",
        "value_min": 1,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per dwelling; secure locker or room per AS2890.3",
        "source_text": "Woollahra DCP 2015 E1.6.2 Table 4: Residential accommodation — "
                       "Residents/Employees: 1 per dwelling. Residential uses with individual "
                       "garages or secure storage spaces for each dwelling that can accommodate "
                       "a Class 1 bike locker under AS2890.3.",
        "section_ref": "E1.6.2-table-4",
        "source_chapter_key": "chapter-e1-parking-access",
        "dcp_version": "v2015-amended-may2025",
        "needs_review": False,
    },
    {
        "lga": "woollahra",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 10 dwellings; bicycle rack per AS2890.3",
        "source_text": "Woollahra DCP 2015 E1.6.2 Table 4: Residential accommodation — "
                       "Customers/Visitors: 1 per 10 dwellings.",
        "section_ref": "E1.6.2-table-4",
        "source_chapter_key": "chapter-e1-parking-access",
        "dcp_version": "v2015-amended-may2025",
        "needs_review": False,
    },

    # --- Parramatta (9.9.3.2 Table 9.9.3.1) ---
    {
        "lga": "parramatta",
        "dev_type": "residential_flat_building",
        "value_min": 1,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per dwelling; Class B lockers per AS2890.3",
        "source_text": "Parramatta DCP 2023 s9.9.3.2 Table 9.9.3.1: Residential accommodation "
                       "— Residents/Employees Bicycle Parking Spaces: 1 per dwelling.",
        "section_ref": "s9.9.3.2-table-9.9.3.1",
        "source_chapter_key": "parramatta-dcp-2023-full",
        "dcp_version": "v2023-amendment-4",
        "needs_review": False,
    },
    {
        "lga": "parramatta",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 10 dwellings; Class C rails per AS2890.3",
        "source_text": "Parramatta DCP 2023 s9.9.3.2 Table 9.9.3.1: Residential accommodation "
                       "— Visitors: 1 per 10 dwellings.",
        "section_ref": "s9.9.3.2-table-9.9.3.1",
        "source_chapter_key": "parramatta-dcp-2023-full",
        "dcp_version": "v2023-amendment-4",
        "needs_review": False,
    },

    # --- Ku-ring-gai (7B.2) ---
    {
        "lga": "ku_ring_gai",
        "dev_type": "residential_flat_building",
        "value_min": 1,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per dwelling; individual locker or secure room per AS2890.3",
        "source_text": "Ku-ring-gai DCP 2024 s7B.2: Onsite secure bicycle parking — "
                       "Residents: 1 bicycle parking space per dwelling within the residential "
                       "car park area — in the form of an individual locker or secure room "
                       "as per AS2890.3.",
        "section_ref": "s7B.2",
        "source_chapter_key": "section-a-part-7-residential-flat-buildings",
        "dcp_version": "v2024",
        "needs_review": False,
    },
    {
        "lga": "ku_ring_gai",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 10 dwellings; bicycle rack per AS2890.3",
        "source_text": "Ku-ring-gai DCP 2024 s7B.2: Onsite secure bicycle parking — "
                       "Visitors: 1 bicycle parking space per 10 units or part thereof "
                       "within the visitor car park area — in the form of a bicycle parking "
                       "device or rack as per AS2890.3.",
        "section_ref": "s7B.2",
        "source_chapter_key": "section-a-part-7-residential-flat-buildings",
        "dcp_version": "v2024",
        "needs_review": False,
    },

    # --- Bayside (s3.5.4 C1) ---
    {
        "lga": "bayside",
        "dev_type": "residential_flat_building",
        "value_min": 1,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per dwelling for MDH/RFB/shop-top/serviced apartments/BTR",
        "source_text": "Bayside DCP 2022 s3.5.4 C1: Multi Dwelling Housing/Residential Flat "
                       "Buildings/Shop Top Housing/Serviced Apartments/Build-To-Rent Housing: "
                       "(a) 1 bicycle space per dwelling (for residents).",
        "section_ref": "s3.5.4-C1",
        "source_chapter_key": "s3-5-traffic-parking-access",
        "dcp_version": "v2022-amendment-2-apr2026",
        "needs_review": False,
    },
    {
        "lga": "bayside",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 10 dwellings for MDH/RFB/shop-top/serviced apartments/BTR",
        "source_text": "Bayside DCP 2022 s3.5.4 C1: Multi Dwelling Housing/Residential Flat "
                       "Buildings/Shop Top Housing/Serviced Apartments/Build-To-Rent Housing: "
                       "(b) 1 bicycle space per 10 dwellings (for visitors).",
        "section_ref": "s3.5.4-C1",
        "source_chapter_key": "s3-5-traffic-parking-access",
        "dcp_version": "v2022-amendment-2-apr2026",
        "needs_review": False,
    },

    # --- Randwick (B7 Table 3) ---
    {
        "lga": "randwick",
        "dev_type": "residential_flat_building",
        "value_min": 0.5,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per 2 units for shop-top/MDH/RFB",
        "source_text": "Randwick DCP 2013 B7 Table 3: Shop top housing, multi dwelling housing, "
                       "residential flat buildings — Residents/Employees: 1 bike space per 2 units.",
        "section_ref": "B7-table-3",
        "source_chapter_key": "b7-transport-traffic-parking-access",
        "dcp_version": "v2013-amendment-apr2016",
        "needs_review": False,
    },
    {
        "lga": "randwick",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 10 units for shop-top/MDH/RFB",
        "source_text": "Randwick DCP 2013 B7 Table 3: Shop top housing, multi dwelling housing, "
                       "residential flat buildings — Customers/Visitors: 1 per 10 units.",
        "section_ref": "B7-table-3",
        "source_chapter_key": "b7-transport-traffic-parking-access",
        "dcp_version": "v2013-amendment-apr2016",
        "needs_review": False,
    },

    # --- Canada Bay (B3.11 Table B-G) ---
    {
        "lga": "canada_bay",
        "dev_type": "residential_flat_building",
        "value_min": 1,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per dwelling; secure storage facility",
        "source_text": "Canada Bay DCP Part B B3.11 Table B-G: Residential — "
                       "Resident/Staff Bicycle storage facility: 1 per dwelling.",
        "section_ref": "B3.11-table-BG",
        "source_chapter_key": "part-c-table-cb-parking",
        "dcp_version": "v2020-current",
        "needs_review": False,
    },
    {
        "lga": "canada_bay",
        "dev_type": "residential_flat_building",
        "value_min": 0.2,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 2 per 10 dwellings; bicycle parking facility",
        "source_text": "Canada Bay DCP Part B B3.11 Table B-G: Residential — "
                       "Visitor Bicycle parking facility: 2 per 10 dwellings.",
        "section_ref": "B3.11-table-BG",
        "source_chapter_key": "part-c-table-cb-parking",
        "dcp_version": "v2020-current",
        "needs_review": False,
    },

    # --- Ashfield (A-Part8 Table 2) ---
    {
        "lga": "ashfield",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per 10 flats in communal area if no lockable garage",
        "source_text": "Ashfield DCP 2016 A-Part8 Table 2: Flats — "
                       "Employees/Occupants: 1 per 10 flats in an accessible communal area "
                       "if no lockable garage provided.",
        "section_ref": "A-Part8-table-2",
        "source_chapter_key": "chapter-a-miscellaneous",
        "dcp_version": "v2016-IW-LEP-2022-amendments",
        "needs_review": False,
    },
    {
        "lga": "ashfield",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 10 flats in communal area",
        "source_text": "Ashfield DCP 2016 A-Part8 Table 2: Flats — "
                       "Visitors/Customers: 1 per 10 flats in an accessible communal area.",
        "section_ref": "A-Part8-table-2",
        "source_chapter_key": "chapter-a-miscellaneous",
        "dcp_version": "v2016-IW-LEP-2022-amendments",
        "needs_review": False,
    },

    # --- Marrickville (2.10 Table 5) ---
    {
        "lga": "marrickville",
        "dev_type": "residential_flat_building",
        "value_min": 0.5,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per 2 units",
        "source_text": "Marrickville DCP 2011 s2.10 Table 5: Residential flat buildings — "
                       "Bicycle parking spaces: 1 per 2 units for residents + 1 per 10 units "
                       "for visitors.",
        "section_ref": "s2.10-table-5",
        "source_chapter_key": "part2-s10-parking",
        "dcp_version": "v2011-amended-nov2022",
        "needs_review": False,
    },
    {
        "lga": "marrickville",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 10 units",
        "source_text": "Marrickville DCP 2011 s2.10 Table 5: Residential flat buildings — "
                       "Bicycle parking spaces: 1 per 10 units for visitors.",
        "section_ref": "s2.10-table-5",
        "source_chapter_key": "part2-s10-parking",
        "dcp_version": "v2011-amended-nov2022",
        "needs_review": False,
    },

    # --- Hornsby (Table 1.3.2-e) ---
    {
        "lga": "hornsby",
        "dev_type": "residential_flat_building",
        "value_min": 0.2,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per 5 units; secure, safe and undercover area",
        "source_text": "Hornsby DCP 2024 Part 1 General Table 1.3.2-e: Medium and High "
                       "Density Residential Development — 1 space per 5 units for residents "
                       "to be located in a safe, secure and undercover area.",
        "section_ref": "s1.3.2-table-1.3.2-e",
        "source_chapter_key": "hornsby-dcp-2024-part1-general",
        "dcp_version": "v2024-june2025",
        "needs_review": False,
    },
    {
        "lga": "hornsby",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 10 units",
        "source_text": "Hornsby DCP 2024 Part 1 General Table 1.3.2-e: Medium and High "
                       "Density Residential Development — 1 space per 10 units for visitors.",
        "section_ref": "s1.3.2-table-1.3.2-e",
        "source_chapter_key": "hornsby-dcp-2024-part1-general",
        "dcp_version": "v2024-june2025",
        "needs_review": False,
    },

    # --- Waverley (s7.2.6 Table 5) ---
    {
        "lga": "waverley",
        "dev_type": "residential_flat_building",
        "value_min": 1.25,
        "unit": "spaces/1bed_dwelling",
        "condition": "Residents: 1.25 per 1-bed dwelling + 0.25 per additional bedroom; "
                     "max 30% vertical/stacked; rounded up to nearest whole number",
        "source_text": "Waverley DCP 2022 Part B s7.2.6 Table 5: Residential Development — "
                       "All residential development: A minimum of 1.25 spaces per 1 bedroom "
                       "dwelling and an additional 0.25 spaces for each additional bedroom in "
                       "each dwelling (rounded up to the nearest whole number for residential "
                       "flat buildings and shop top housing). A maximum of 30% may be vertical "
                       "or tiered/stacked spaces or be supplied by Security Level A spaces. "
                       "Note: DCP control (a) cross-references 'Table 4' but the table caption "
                       "reads 'Table 5 Bicycle parking rates' — Table 4 is car parking.",
        "section_ref": "s7.2.6-table-5",
        "source_chapter_key": "waverley-dcp-2022",
        "dcp_version": "v2022-amendment-5",
        "needs_review": False,
    },
    {
        "lga": "waverley",
        "dev_type": "residential_flat_building",
        "value_min": 0.2,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 5 dwellings; security level C; for 3+ dwelling developments",
        "source_text": "Waverley DCP 2022 Part B s7.2.6 Table 5: Medium and High Density "
                       "(3+ dwellings) — Visitor: 1 space per 5 dwellings (security level C).",
        "section_ref": "s7.2.6-table-5",
        "source_chapter_key": "waverley-dcp-2022",
        "dcp_version": "v2022-amendment-5",
        "needs_review": False,
    },

    # --- Georges River (s3.13 Table 2) ---
    {
        "lga": "georges_river",
        "dev_type": "residential_flat_building",
        "value_min": 0.333,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per 3 dwellings; rounded up to nearest whole number",
        "source_text": "Georges River DCP 2021 s3.13 Table 2: Bicycle Parking Requirements "
                       "(minimum) — Residential flat building: 1 space per 3 dwellings. "
                       "Also applies to shop-top housing/mixed use development (residential "
                       "component). Totals rounded up to nearest whole number (0.5 or greater). "
                       "Design standard: AS2890.3.",
        "section_ref": "s3.13-table-2",
        "source_chapter_key": "part-3-general-planning-considerations",
        "dcp_version": "v2021",
        "needs_review": False,
    },
    {
        "lga": "georges_river",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 10 dwellings; rounded up to nearest whole number",
        "source_text": "Georges River DCP 2021 s3.13 Table 2: Bicycle Parking Requirements "
                       "(minimum) — Residential flat building: 1 space per 10 dwellings "
                       "(visitors). Design standard: AS2890.3.",
        "section_ref": "s3.13-table-2",
        "source_chapter_key": "part-3-general-planning-considerations",
        "dcp_version": "v2021",
        "needs_review": False,
    },

    # --- Liverpool (Part 1 Table 13) ---
    {
        "lga": "liverpool",
        "dev_type": "residential_flat_building",
        "value_min": 0.5,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per 2 units",
        "source_text": "Liverpool DCP 2008 Part 1 Table 13 (p.91): Bicycle Parking Provision "
                       "— multi dwelling housing: 1 space per 2 units for residents. "
                       "Confirmed from council traffic referral letter.",
        "section_ref": "part-1-table-13",
        "source_chapter_key": "part-1-car-parking-access",
        "dcp_version": "v2008-amendment-34-dec2019",
        "needs_review": False,
    },
    {
        "lga": "liverpool",
        "dev_type": "residential_flat_building",
        "value_min": 0.1,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 10 units",
        "source_text": "Liverpool DCP 2008 Part 1 Table 13 (p.91): Bicycle Parking Provision "
                       "— multi dwelling housing: 1 space per 10 units for visitors. "
                       "Confirmed from council traffic referral letter.",
        "section_ref": "part-1-table-13",
        "source_chapter_key": "part-1-car-parking-access",
        "dcp_version": "v2008-amendment-34-dec2019",
        "needs_review": False,
    },

    # --- Campbelltown (Part 4 RFB) ---
    {
        "lga": "campbelltown",
        "dev_type": "residential_flat_building",
        "value_min": 0.2,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per 5 dwellings within common property; storage-area-based",
        "source_text": "Campbelltown (Sustainable City) DCP 2015 Part 4 (Residential Flat "
                       "Buildings and Mixed-Use Development): 1 bicycle storage space per 5 "
                       "dwellings within common property. No separate visitor rate stated.",
        "section_ref": "part-4-rfb",
        "source_chapter_key": "campbelltown-dcp-part4-rfb-mixed-use",
        "dcp_version": "v2015-updated-sep2024",
        "needs_review": False,
    },

    # --- The Hills / Showground Precinct (Table 9/13) ---
    {
        "lga": "the_hills",
        "dev_type": "residential_flat_building",
        "value_min": 0.333,
        "unit": "spaces/dwelling",
        "condition": "Residents: 1 per 3 apartments (minimum); Showground Precinct DCP rate "
                     "(general LGA rate in Part C s1 Table 3 — PDF access blocked)",
        "source_text": "The Hills DCP 2012 — Showground Station Precinct DCP (Sept 2018) "
                       "Table 9/13: Residents: 1 space per 3 apartments (minimum). "
                       "General LGA bicycle rates are in DCP 2012 Part C Section 1 Table 3 "
                       "but that PDF was server-blocked at time of extraction.",
        "section_ref": "showground-table-9-13",
        "source_chapter_key": "the-hills-showground-precinct-dcp",
        "dcp_version": "v2012-aug2024",
        "needs_review": True,
        "review_reason": "Showground precinct rate confirmed; general LGA Part C s1 Table 3 "
                         "rate not yet verified (PDF blocked)",
    },
    {
        "lga": "the_hills",
        "dev_type": "residential_flat_building",
        "value_min": 0.083,
        "unit": "spaces/dwelling",
        "condition": "Visitors: 1 per 12 apartments (minimum); Showground Precinct DCP rate",
        "source_text": "The Hills DCP 2012 — Showground Station Precinct DCP (Sept 2018) "
                       "Table 9/13: Visitors: 1 space per 12 apartments (minimum).",
        "section_ref": "showground-table-9-13",
        "source_chapter_key": "the-hills-showground-precinct-dcp",
        "dcp_version": "v2012-aug2024",
        "needs_review": True,
        "review_reason": "Showground precinct rate confirmed; general LGA Part C s1 Table 3 "
                         "rate not yet verified (PDF blocked)",
    },

    # ══════════════════════════════════════════════════════════════
    # NO REQUIREMENT FOR RESIDENTIAL
    # ══════════════════════════════════════════════════════════════

    # --- Canterbury-Bankstown ---
    {
        "lga": "canterbury_bankstown",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "unit": "spaces/dwelling",
        "condition": "No bicycle parking requirement for residential development",
        "source_text": "Canterbury-Bankstown DCP 2023 Ch3.2: Bicycle parking column shows "
                       "'Not applicable' for all residential types (dwelling house, dual "
                       "occupancy, secondary dwelling, multi-dwelling housing, residential "
                       "flat building, shop-top housing, seniors housing, boarding house).",
        "section_ref": "ch3.2",
        "source_chapter_key": "chapter-3-general-controls",
        "dcp_version": "v2023-amendment-11",
        "needs_review": False,
    },

    # --- Blacktown ---
    {
        "lga": "blacktown",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "unit": "spaces/dwelling",
        "condition": "No requirement to provide bicycle parking for residential development",
        "source_text": "Blacktown DCP 2015 Part C has no requirement to provide bicycle "
                       "parking for residential development. Confirmed via DA traffic "
                       "assessment (DA-17-01311): 'Blacktown DCP 2015 has no requirement "
                       "to provide bicycle parking.'",
        "section_ref": "part-c-residential",
        "source_chapter_key": "part-c-development-residential",
        "dcp_version": "v2015-current",
        "needs_review": False,
    },

    # ══════════════════════════════════════════════════════════════
    # DEFERS TO EXTERNAL STANDARD — no DCP-specific numeric rate
    # ══════════════════════════════════════════════════════════════

    # --- Burwood ---
    {
        "lga": "burwood",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "unit": "spaces/dwelling",
        "condition": "Defers to Austroads Guides (1999) and Planning Guidelines for "
                     "Walking and Cycling (2004); no DCP-specific residential rate",
        "source_text": "Burwood DCP 2013 s4 Parking: 'Standards for the number of bicycle "
                       "parking facilities and number of showers/lockers for different land "
                       "uses are provided in Cycling Aspects of Austroads Guides (1999) and "
                       "Planning Guidelines for Walking and Cycling (2004).' No specific "
                       "residential rate table in DCP.",
        "section_ref": "s4-parking-bicycle",
        "source_chapter_key": "s4-table-4-parking",
        "dcp_version": "v2013-amendment-13-nov2025",
        "needs_review": False,
    },

    # --- Fairfield ---
    {
        "lga": "fairfield",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "unit": "spaces/dwelling",
        "condition": "Defers to AS 2890:3:1993; no DCP-specific residential rate",
        "source_text": "Fairfield DCP 2024 Ch12.3.3: 'Bicycle parking/storage facilities "
                       "should be provided in accordance with the provisions of Australian "
                       "Standard 2890:3:1993.' No specific numeric residential rate table.",
        "section_ref": "ch12.3.3",
        "source_chapter_key": "parking-controls",
        "dcp_version": "v2024-current",
        "needs_review": False,
    },

    # --- Cumberland ---
    {
        "lga": "cumberland",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "unit": "spaces/dwelling",
        "condition": "Defers to AS2890.3 for developments >1000m2 GFA; no per-dwelling "
                     "residential rate. RFBs defer to ADG/SEPP 65",
        "source_text": "Cumberland DCP (Auburn DCP 2010 incorporated) s3.1 Parking and "
                       "Loading: 'All developments over 1,000 m2 GFA must provide bicycle "
                       "racks in accordance with AS2890.3 — Bicycle Parking Facilities.' "
                       "Only precinct-specific rate: Newington Small Village mixed-use — "
                       "1 bicycle storage area per 5 residential units. General RFBs defer "
                       "to ADG/SEPP 65 with no per-dwelling rate.",
        "section_ref": "s3.1-table-1",
        "source_chapter_key": "part-g3-traffic-parking",
        "dcp_version": "v2021",
        "needs_review": False,
    },

    # --- Ryde ---
    {
        "lga": "ryde",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "unit": "spaces/dwelling",
        "condition": "No per-dwelling residential rate; DCP specifies 10% of car spaces "
                     "for non-residential >600m2 GFA only",
        "source_text": "Ryde DCP 2014 s2.7: 'Provide bicycle parking equivalent to 10% of "
                       "the required car spaces' for buildings >600m2 GFA, excluding dwelling "
                       "houses and multi-unit housing. No explicit per-dwelling residential "
                       "bicycle rate.",
        "section_ref": "s2.7",
        "source_chapter_key": "part-9.3-parking",
        "dcp_version": "v2014-current",
        "needs_review": False,
    },

    # --- Penrith ---
    {
        "lga": "penrith",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "unit": "spaces/dwelling",
        "condition": "Defers to NSW Planning Guidelines for Walking and Cycling (2004); "
                     "soft requirement ('should'); no DCP-specific residential rate",
        "source_text": "Penrith DCP 2014 C10.7 Bicycle Facilities, Control 2c: 'Applicants "
                       "should comply with the suggested bicycle parking provision rates for "
                       "different land use types in the document Planning Guidelines for "
                       "Walking and Cycling (NSW Government 2004).' Soft requirement — no "
                       "specific per-dwelling rate for residential flat buildings.",
        "section_ref": "C10.7-control-2c",
        "source_chapter_key": "c10-transport-access-parking",
        "dcp_version": "v2014-current",
        "needs_review": False,
    },

    # --- Strathfield ---
    {
        "lga": "strathfield",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "unit": "spaces/dwelling",
        "condition": "Qualitative requirement only: 'suitable facilities must be provided'; "
                     "no numeric rate",
        "source_text": "Strathfield CDCP 2005 Part C (Multiple Unit Housing) Control 10: "
                       "'Suitable facilities for accommodating bicycle parking in all "
                       "residential flat buildings must be provided.' No specific numeric "
                       "rate — blanket qualitative requirement only.",
        "section_ref": "part-c-control-10",
        "source_chapter_key": "parking-controls",
        "dcp_version": "v2005-amended-jul2015",
        "needs_review": False,
    },

    # --- Northern Beaches (Warringah) ---
    {
        "lga": "northern_beaches",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "unit": "spaces/dwelling",
        "condition": "Defers to NSW Bicycle Guidelines, AS2890.3, Austroads Part 11; "
                     "no numeric residential rate table",
        "source_text": "Warringah DCP 2011 Part C3/C4: References NSW Bicycle Guidelines "
                       "Part 11, AS 2890.3, NSW Planning Guidelines for Walking and Cycling "
                       "Part 7.6, and Austroads Guide Part 11. No numeric rate table exists "
                       "for residential development.",
        "section_ref": "C3-C4",
        "source_chapter_key": "warringah-dcp-2011-full",
        "dcp_version": "v2011-amendment-3-feb2013",
        "needs_review": False,
    },

    # --- Sutherland Shire ---
    {
        "lga": "sutherland_shire",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "unit": "spaces/dwelling",
        "condition": "Indirect rate: 1 per 10 car parking spaces for non-exempt uses; "
                     "no per-dwelling residential rate. Draft Amendment 6 (March 2026) "
                     "may add medium/high density rates",
        "source_text": "Sutherland Shire DCP 2015 Ch36 s5.2: Bicycle parking applies to "
                       "'All Development, Except Dwelling Houses, Dual Occupancies, and "
                       "Multi Dwelling Housing' at 1 space per 10 car parking spaces. RFBs "
                       "not explicitly excluded but no per-dwelling rate given. Design must "
                       "comply with AS2890.3. Draft Amendment 6 (adopted March 2026) "
                       "introduces medium/high density residential bicycle parking — specific "
                       "rates not yet published.",
        "section_ref": "ch36-s5.2",
        "source_chapter_key": "ch36-vehicular-access-traffic-parking",
        "dcp_version": "v2015-amendment-6-mar2021",
        "needs_review": False,
    },

    # --- Camden ---
    {
        "lga": "camden",
        "dev_type": "residential_flat_building",
        "value_min": None,
        "unit": "spaces/dwelling",
        "condition": "Not yet extracted — DCP parking section needs review",
        "source_text": "Camden DCP bicycle parking rate not yet extracted from DCP parking "
                       "section. Requires PDF-level review.",
        "section_ref": "parking-bicycle",
        "source_chapter_key": "parking-controls",
        "dcp_version": "v2019-current",
        "needs_review": True,
        "review_reason": "Bicycle rate not yet extracted from Camden DCP",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Insert bicycle parking controls")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be inserted without writing to DB")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    inserted = 0
    skipped = 0
    errors = 0

    for row in BICYCLE_ROWS:
        lga = row["lga"]
        dev_type = row["dev_type"]
        condition = row["condition"]

        # Dedup check: (lga, control_type, dev_type, condition prefix, is_current)
        condition_prefix = condition[:30]
        cur.execute(
            """
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s
              AND control_type = 'bicycle_parking'
              AND dev_type = %s
              AND condition LIKE %s
              AND is_current = TRUE
            """,
            (lga, dev_type, condition_prefix + "%"),
        )
        if cur.fetchone():
            skipped += 1
            if args.dry_run:
                print(f"  SKIP (exists): {lga} / {condition_prefix}...")
            continue

        if args.dry_run:
            v = row["value_min"]
            val_str = f"{v}" if v is not None else "NULL"
            review_flag = " [NEEDS REVIEW]" if row.get("needs_review") else ""
            print(f"  INSERT: {lga} / {val_str} {row['unit']}{review_flag}")
            print(f"          {condition}")
            inserted += 1
            continue

        try:
            cur.execute(
                """
                INSERT INTO dcp_setback_controls (
                    lga, dev_type, control_type, value_min, unit,
                    condition, applicability, source_text, section_ref,
                    source_chapter_key, dcp_version, is_current,
                    extraction_method, needs_review, review_reason
                ) VALUES (
                    %s, %s, 'bicycle_parking', %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, TRUE,
                    %s, %s, %s
                )
                """,
                (
                    lga,
                    dev_type,
                    row["value_min"],
                    row["unit"],
                    condition,
                    row.get("applicability", "universal_residential"),
                    row["source_text"],
                    row["section_ref"],
                    row["source_chapter_key"],
                    row["dcp_version"],
                    EXTRACTION_METHOD,
                    row.get("needs_review", False),
                    row.get("review_reason"),
                ),
            )
            inserted += 1
        except Exception as e:
            errors += 1
            print(f"  ERROR: {lga} / {dev_type}: {e}")
            conn.rollback()

    if not args.dry_run and errors == 0:
        conn.commit()
        print(f"\nCommitted {inserted} rows.")
    elif args.dry_run:
        print(f"\n[DRY RUN] Would insert {inserted} rows, skip {skipped} existing.")
    else:
        print(f"\n{errors} errors — transaction rolled back. No rows written.")

    # Summary table
    print(f"\n{'='*70}")
    print(f"{'LGA':<25} {'Value':>8} {'Status':<12} {'Source'}")
    print(f"{'-'*70}")
    verified = 0
    null_rows = 0
    review = 0
    for row in BICYCLE_ROWS:
        # Skip visitor rows in summary (show one line per council)
        if "Visitor" in row["condition"]:
            continue
        nr = row.get("needs_review", False)
        v = row["value_min"]
        if nr:
            review += 1
            status = "REVIEW"
        elif v is None:
            null_rows += 1
            status = "NO_RATE"
        else:
            verified += 1
            status = "VERIFIED"
        val_str = f"{v}" if v is not None else "NULL"
        ref = row["section_ref"]
        print(f"{row['lga']:<25} {val_str:>8} {status:<12} {ref}")
    print(f"{'-'*70}")
    print(f"Total rows: {len(BICYCLE_ROWS)}")
    print(f"  Verified numeric: {verified} councils")
    print(f"  No rate / defers: {null_rows} councils")
    print(f"  Needs review:     {review} councils")
    print(f"Inserted: {inserted}, Skipped: {skipped}, Errors: {errors}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
