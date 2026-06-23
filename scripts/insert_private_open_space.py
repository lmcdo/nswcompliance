#!/usr/bin/env python3
"""
Insert private open space requirements from council DCPs into dcp_setback_controls.

Private open space (POS) is the minimum outdoor area each dwelling must provide
for exclusive private use (balconies, courtyards, yards). Values are per dwelling
and vary by dev type and floor level.

Sources verified per council from DCP text extracted in regulatory_provisions:
  - Northern Beaches (Warringah DCP 2011): DH 1-2 bed 35m2/3m, DH 3+ bed 60m2/5m, upper 10m2/2.5m
  - Hornsby (DCP 2024): 6-9m lot 16m2/3m, 10m+ lot 24m2/3m
  - Ku-ring-gai (DCP 2024): DH 50m2/5m depth, secondary dwelling 25m2/3m
  - Parramatta (Epping SC DCP): Studio 4m2/2m, 1-bed 8m2/2m, 2-bed 10m2/2m, 3+ bed 12m2/2.4m, ground 15m2/3m
  - Waverley (DCP 2022): Courtyard 25m2/3m, dual occ 5mx5m POS area
  - Woollahra (DCP 2015 Watsons Bay): Ground level 35m2/3m, principal area 16m2/4m
  - City of Sydney (DCP 2012): Ground 25m2/4m, upper 10m2/2m
  - Leichhardt (DCP 2013): DH ground 3mx3m, balcony 2.5m width
  - Marrickville (DCP 2011): DH 45m2 or 20% site/3m, secondary 4mx4m, MDH ground 4mx4m, upper 8m2/2m
  - Blacktown (DCP 2015): DH 6mx4m area, composite 2.5m min dim
  - Penrith (DCP 2014): Secondary dwelling 24m2/4m width
  - Ashfield (Inner West DCP 2016): Courtyard 20m2/3.5m width
  - Cumberland (DCP 2021): Section 2.8 exists, needs PDF verification for numerics

Councils marked needs_review=TRUE have no extracted provision text with numeric
POS values and require PDF-level verification.

Usage:
    python scripts/insert_private_open_space.py --dry-run
    python scripts/insert_private_open_space.py
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
# Per-council private open space data.
# Each entry: lga, dev_type, value_min, unit, condition, source_text,
#   section_ref, dcp_version, source_chapter_key, needs_review
#
# Multiple rows per council where different dev types have different
# POS requirements.
# ─────────────────────────────────────────────────────────────────────

POS_ROWS = [
    # ══════════════════════════════════════════════════════════════
    # VERIFIED — values confirmed from extracted DCP provision text
    # ══════════════════════════════════════════════════════════════

    # ── Northern Beaches (Warringah DCP 2011) ──
    {
        "lga": "northern_beaches", "dev_type": "dwelling_house",
        "value_min": 35, "unit": "m2", "needs_review": False,
        "condition": "1-2 bedroom dwelling house; min dimension 3m",
        "source_text": "DH 1-2 bed: 35m2 min dim 3m (Warringah DCP 2011)",
        "section_ref": "d18-private-open-space",
        "dcp_version": "v2011", "source_chapter_key": "warringah-dcp-2011-full",
    },
    {
        "lga": "northern_beaches", "dev_type": "dwelling_house",
        "value_min": 60, "unit": "m2", "needs_review": False,
        "condition": "3+ bedroom dwelling house; min dimension 5m",
        "source_text": "DH 3+ bed: 60m2 min dim 5m (Warringah DCP 2011)",
        "section_ref": "d18-private-open-space",
        "dcp_version": "v2011", "source_chapter_key": "warringah-dcp-2011-full",
    },
    {
        "lga": "northern_beaches", "dev_type": "residential_flat_building",
        "value_min": 10, "unit": "m2", "needs_review": False,
        "condition": "Upper level unit (MDH/RFB); min dimension 2.5m",
        "source_text": "MDH/RFB upper level: 10m2 min dim 2.5m (Warringah DCP 2011)",
        "section_ref": "d18-private-open-space",
        "dcp_version": "v2011", "source_chapter_key": "warringah-dcp-2011-full",
    },

    # ── Hornsby (DCP 2024 s3.1.4) ──
    {
        "lga": "hornsby", "dev_type": "dwelling_house",
        "value_min": 16, "unit": "m2", "needs_review": False,
        "condition": "Lot width 6-9m at building line; min dimension 3m",
        "source_text": "Table 3.1.4-a: 6-9m lot width — 16m2 POS, min dim 3m (Hornsby DCP 2024)",
        "section_ref": "3-1-4-open-space",
        "dcp_version": "v2024", "source_chapter_key": "hornsby-dcp-2024-part3-residential",
    },
    {
        "lga": "hornsby", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": False,
        "condition": "Lot width 10m or larger at building line; min dimension 3m",
        "source_text": "Table 3.1.4-a: 10m+ lot width — 24m2 POS, min dim 3m (Hornsby DCP 2024)",
        "section_ref": "3-1-4-open-space",
        "dcp_version": "v2024", "source_chapter_key": "hornsby-dcp-2024-part3-residential",
    },

    # ── Ku-ring-gai (DCP 2024) ──
    {
        "lga": "ku_ring_gai", "dev_type": "dwelling_house",
        "value_min": 50, "unit": "m2", "needs_review": False,
        "condition": "Dwelling house; min depth 5m",
        "source_text": "DH: 50m2 min depth 5m (Ku-ring-gai DCP 2024 Part 4)",
        "section_ref": "4c-private-open-space",
        "dcp_version": "v2024", "source_chapter_key": "ku-ring-gai-dcp-2024-section-a",
    },
    {
        "lga": "ku_ring_gai", "dev_type": "secondary_dwelling",
        "value_min": 25, "unit": "m2", "needs_review": False,
        "condition": "Secondary dwelling; min dimension 3m",
        "source_text": "Secondary dwelling: 25m2 min dim 3m (Ku-ring-gai DCP 2024 Part 4.1)",
        "section_ref": "4-1-secondary-dwellings",
        "dcp_version": "v2024", "source_chapter_key": "ku-ring-gai-dcp-2024-section-a",
    },

    # ── Parramatta (Epping Strategic Centre DCP) ──
    {
        "lga": "parramatta", "dev_type": "residential_flat_building",
        "value_min": 4, "unit": "m2", "needs_review": False,
        "condition": "Studio apartment; min width 2m (Epping SC)",
        "source_text": "Table 8.1.1.2.7.1: Studio — 4m2 POS, min width 2m (Parramatta DCP 2023 Epping SC)",
        "section_ref": "8-1-1-2-7-private-open-space",
        "dcp_version": "v2023", "source_chapter_key": "parramatta-dcp-2023-full",
    },
    {
        "lga": "parramatta", "dev_type": "residential_flat_building",
        "value_min": 8, "unit": "m2", "needs_review": False,
        "condition": "1-bedroom unit; min width 2m (Epping SC)",
        "source_text": "Table 8.1.1.2.7.1: 1 bed — 8m2 POS, min width 2m (Parramatta DCP 2023 Epping SC)",
        "section_ref": "8-1-1-2-7-private-open-space",
        "dcp_version": "v2023", "source_chapter_key": "parramatta-dcp-2023-full",
    },
    {
        "lga": "parramatta", "dev_type": "residential_flat_building",
        "value_min": 10, "unit": "m2", "needs_review": False,
        "condition": "2-bedroom unit; min width 2m (Epping SC)",
        "source_text": "Table 8.1.1.2.7.1: 2 bed — 10m2 POS, min width 2m (Parramatta DCP 2023 Epping SC)",
        "section_ref": "8-1-1-2-7-private-open-space",
        "dcp_version": "v2023", "source_chapter_key": "parramatta-dcp-2023-full",
    },
    {
        "lga": "parramatta", "dev_type": "residential_flat_building",
        "value_min": 12, "unit": "m2", "needs_review": False,
        "condition": "3+ bedroom unit; min width 2.4m (Epping SC)",
        "source_text": "Table 8.1.1.2.7.1: 3+ bed — 12m2 POS, min width 2.4m (Parramatta DCP 2023 Epping SC)",
        "section_ref": "8-1-1-2-7-private-open-space",
        "dcp_version": "v2023", "source_chapter_key": "parramatta-dcp-2023-full",
    },
    {
        "lga": "parramatta", "dev_type": "residential_flat_building",
        "value_min": 15, "unit": "m2", "needs_review": False,
        "condition": "Ground level apartment; min width 3m (Epping SC)",
        "source_text": "Table 8.1.1.2.7.1: Ground level — 15m2 POS, min width 3m (Parramatta DCP 2023 Epping SC)",
        "section_ref": "8-1-1-2-7-private-open-space",
        "dcp_version": "v2023", "source_chapter_key": "parramatta-dcp-2023-full",
    },

    # ── Waverley (DCP 2022) ──
    {
        "lga": "waverley", "dev_type": "dwelling_house",
        "value_min": 25, "unit": "m2", "needs_review": False,
        "condition": "Each dwelling; minimum POS for recreation (C1.1.9(e))",
        "source_text": "Each dwelling is to have a minimum of 25m2 of private open space capable of being used for recreation (Waverley DCP 2022 C1.1.9(e))",
        "section_ref": "c1-1-9-landscaping-open-space",
        "dcp_version": "v2022", "source_chapter_key": "waverley-dcp-2022",
    },
    {
        "lga": "waverley", "dev_type": "multi_dwelling_housing",
        "value_min": 25, "unit": "m2", "needs_review": False,
        "condition": "Courtyard min 25m2 area, min width and depth 3m (C2.2.11)",
        "source_text": "Private courtyards must have minimum 25m2 area, minimum width and depth of 3m (Waverley DCP 2022 C2.2.11)",
        "section_ref": "c2-2-11-private-open-space",
        "dcp_version": "v2022", "source_chapter_key": "waverley-dcp-2022",
    },
    {
        "lga": "waverley", "dev_type": "dual_occupancy",
        "value_min": 25, "unit": "m2", "needs_review": False,
        "condition": "Dual occupancy: each dwelling min 25m2 POS; total open space min 130m2 with 5m x 5m POS adjacent to living area (C1.1.9(f))",
        "source_text": "Each dwelling in dual occ min 130m2 open space including POS having minimum 5m x 5m adjacent to living area (Waverley DCP 2022 C1.1.9(f))",
        "section_ref": "c1-1-9-landscaping-open-space",
        "dcp_version": "v2022", "source_chapter_key": "waverley-dcp-2022",
    },

    # ── Woollahra (DCP 2015 — Watsons Bay HCA C3.5.6) ──
    {
        "lga": "woollahra", "dev_type": "dwelling_house",
        "value_min": 35, "unit": "m2", "needs_review": False,
        "condition": "Ground level dwelling; min dim 3m; principal area min 16m2 with min dim 4m (Watsons Bay HCA C3.5.6)",
        "source_text": "Each ground level dwelling POS min 35m2 with min dim 3m; principal area min 16m2 min dim 4m (Woollahra DCP 2015 C3.5.6)",
        "section_ref": "c3-5-6-landscaping-pos",
        "dcp_version": "v2015", "source_chapter_key": "woollahra-dcp-2015-chapter-c3",
    },

    # ── City of Sydney (DCP 2012 s4.2.3.8) ──
    {
        "lga": "city_of_sydney", "dev_type": "residential_flat_building",
        "value_min": 25, "unit": "m2", "needs_review": False,
        "condition": "Ground level dwelling; min dimension 4m; max gradient 1:20 (s4.2.3.8(6)(a))",
        "source_text": "Ground level dwellings: 25sqm with min dim 4m (Sydney DCP 2012 s4.2.3.8(6)(a))",
        "section_ref": "4-2-3-8-private-open-space",
        "dcp_version": "v2012", "source_chapter_key": "section-4-development-types",
    },
    {
        "lga": "city_of_sydney", "dev_type": "residential_flat_building",
        "value_min": 10, "unit": "m2", "needs_review": False,
        "condition": "Upper level unit; min dimension 2m; up to 25% may have juliet balconies only (s4.2.3.8(6)(b))",
        "source_text": "Upper level units: 10sqm with min dim 2m (Sydney DCP 2012 s4.2.3.8(6)(b))",
        "section_ref": "4-2-3-8-private-open-space",
        "dcp_version": "v2012", "source_chapter_key": "section-4-development-types",
    },

    # ── Leichhardt (DCP 2013) ──
    {
        "lga": "leichhardt", "dev_type": "dwelling_house",
        "value_min": 9, "unit": "m2", "needs_review": False,
        "condition": "DH ground floor; min 3m x 3m",
        "source_text": "DH ground: 3m x 3m private open space (Leichhardt DCP 2013 Part B)",
        "section_ref": "b-pos-dwelling",
        "dcp_version": "v2013", "source_chapter_key": "leichhardt-dcp-2013-part-c-s3",
    },
    {
        "lga": "leichhardt", "dev_type": "residential_flat_building",
        "value_min": 8, "unit": "m2", "needs_review": False,
        "condition": "RFB/mixed use; balcony/deck min dim 2m; min width 2.5m",
        "source_text": "RFB/mixed: 8sqm deck/balcony min dim 2m, min width 2.5m (Leichhardt DCP 2013)",
        "section_ref": "g8-7-pos",
        "dcp_version": "v2013", "source_chapter_key": "leichhardt-dcp-2013-part-g-s1",
    },

    # ── Marrickville (DCP 2011 s2.18) ──
    {
        "lga": "marrickville", "dev_type": "dwelling_house",
        "value_min": 45, "unit": "m2", "needs_review": False,
        "condition": "Greater of 45m2 or 20% of site area; min dimension 3m; not in front setback (C12)",
        "source_text": "Greater of 45m2 or 20% total site area, min dim 3m (Marrickville DCP 2011 s2.18 C12)",
        "section_ref": "2-18-2-c12-pos",
        "dcp_version": "v2011", "source_chapter_key": "part2-s18-landscaping",
    },
    {
        "lga": "marrickville", "dev_type": "secondary_dwelling",
        "value_min": 16, "unit": "m2", "needs_review": False,
        "condition": "Secondary dwelling (attached or detached); min 4m x 4m (C14)",
        "source_text": "Secondary dwelling: min 4m x 4m POS (Marrickville DCP 2011 s2.18 C14)",
        "section_ref": "2-18-2-c14-pos",
        "dcp_version": "v2011", "source_chapter_key": "part2-s18-landscaping",
    },
    {
        "lga": "marrickville", "dev_type": "multi_dwelling_housing",
        "value_min": 16, "unit": "m2", "needs_review": False,
        "condition": "Ground level unit; min 4m x 4m; accessible from principal living area; max gradient 1:10 (C20)",
        "source_text": "MDH ground level: min 4m x 4m POS accessible from living area (Marrickville DCP 2011 s2.18 C20)",
        "section_ref": "2-18-2-c20-pos",
        "dcp_version": "v2011", "source_chapter_key": "part2-s18-landscaping",
    },
    {
        "lga": "marrickville", "dev_type": "residential_flat_building",
        "value_min": 8, "unit": "m2", "needs_review": False,
        "condition": "Upper level dwelling; deck/balcony min area 8m2, min width 2m; accessible from principal living area (C23)",
        "source_text": "Upper level: min 8m2 deck/balcony min width 2m (Marrickville DCP 2011 s2.18 C23)",
        "section_ref": "2-18-2-c23-pos",
        "dcp_version": "v2011", "source_chapter_key": "part2-s18-landscaping",
    },

    # ── Blacktown (DCP 2015 Part C s3.5) ──
    {
        "lga": "blacktown", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": False,
        "condition": "Min 6m x 4m for one principal area; composite areas min 2.5m perpendicular to wall",
        "source_text": "Min horizontal dims 6m x 4m for one area; composite min 2.5m perp to wall (Blacktown DCP 2015 Part C s3.5)",
        "section_ref": "3-5-private-open-space",
        "dcp_version": "v2015", "source_chapter_key": "blacktown-dcp-2015-part-c",
    },

    # ── Penrith (DCP 2014 Part D2) ──
    {
        "lga": "penrith", "dev_type": "secondary_dwelling",
        "value_min": 24, "unit": "m2", "needs_review": False,
        "condition": "Secondary dwelling; min width 4m",
        "source_text": "Secondary dwelling: 24m2 min width 4m (Penrith DCP 2014 Part D2)",
        "section_ref": "d2-secondary-dwelling-pos",
        "dcp_version": "v2014", "source_chapter_key": "penrith-dcp-2014-part-d2",
    },

    # ── Ashfield (Inner West DCP 2016 Chapter A) ──
    {
        "lga": "ashfield", "dev_type": "dwelling_house",
        "value_min": 20, "unit": "m2", "needs_review": False,
        "condition": "Courtyard; min width 3.5m",
        "source_text": "20m2 courtyard min width 3.5m (Inner West DCP Ashfield 2016)",
        "section_ref": "a-pos-courtyard",
        "dcp_version": "v2016", "source_chapter_key": "chapter-a-miscellaneous",
    },

    # ══════════════════════════════════════════════════════════════
    # NEEDS REVIEW — section exists or standard NSW pattern assumed
    # ══════════════════════════════════════════════════════════════

    # Cumberland — s2.8 exists but no numeric values in extracted text
    {
        "lga": "cumberland", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "DCP s2.8 Private Open Space exists; assumed standard min — verify against PDF",
        "source_text": "Cumberland DCP Part B s2.8 Private Open Space (needs PDF verification for numeric values)",
        "section_ref": "2-8-private-open-space",
        "dcp_version": "v2021", "source_chapter_key": "cumberland-dcp-part-b-residential",
    },

    # Campbelltown — s3.6.3.4 exists but text is garbled from PDF extraction
    {
        "lga": "campbelltown", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "DCP s3.6.3.4 Private Open Space exists; garbled text — verify against PDF",
        "source_text": "Campbelltown DCP 2015 s3.6.3.4 Private Open Space (needs PDF verification — garbled extraction)",
        "section_ref": "3-6-3-4-private-open-space",
        "dcp_version": "v2015", "source_chapter_key": "campbelltown-dcp-part3-low-medium",
    },

    # Georges River — no numeric POS in extracted text
    {
        "lga": "georges_river", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Georges River DCP 2021",
        "source_text": "Assumed 24m2 standard pattern (Georges River DCP 2021 — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2021", "source_chapter_key": "part-3-general-planning-considerations",
    },

    # ── Councils with no DCP provision data at all ──
    {
        "lga": "camden", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Camden DCP",
        "source_text": "Assumed 24m2 standard pattern (Camden DCP — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2013", "source_chapter_key": "camden-dcp-residential",
    },
    {
        "lga": "canterbury_bankstown", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Canterbury Bankstown DCP",
        "source_text": "Assumed 24m2 standard pattern (Canterbury Bankstown DCP — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2023", "source_chapter_key": "canterbury-bankstown-dcp-residential",
    },
    {
        "lga": "bayside", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Bayside DCP 2022",
        "source_text": "Assumed 24m2 standard pattern (Bayside DCP 2022 — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2022", "source_chapter_key": "bayside-dcp-2022-residential",
    },
    {
        "lga": "canada_bay", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Canada Bay DCP",
        "source_text": "Assumed 24m2 standard pattern (Canada Bay DCP — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2015", "source_chapter_key": "canada-bay-dcp-residential",
    },
    {
        "lga": "fairfield", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Fairfield DCP 2013",
        "source_text": "Assumed 24m2 standard pattern (Fairfield DCP 2013 — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2013", "source_chapter_key": "fairfield-dcp-2013-residential",
    },
    {
        "lga": "liverpool", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Liverpool DCP 2008",
        "source_text": "Assumed 24m2 standard pattern (Liverpool DCP 2008 — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2008", "source_chapter_key": "liverpool-dcp-2008-residential",
    },
    {
        "lga": "randwick", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Randwick DCP 2013",
        "source_text": "Assumed 24m2 standard pattern (Randwick DCP 2013 — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2013", "source_chapter_key": "randwick-dcp-2013-residential",
    },
    {
        "lga": "ryde", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Ryde DCP 2014",
        "source_text": "Assumed 24m2 standard pattern (Ryde DCP 2014 — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2014", "source_chapter_key": "ryde-dcp-2014-residential",
    },
    {
        "lga": "strathfield", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Strathfield DCP",
        "source_text": "Assumed 24m2 standard pattern (Strathfield DCP — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2005", "source_chapter_key": "strathfield-dcp-residential",
    },
    {
        "lga": "sutherland_shire", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Sutherland Shire DCP",
        "source_text": "Assumed 24m2 standard pattern (Sutherland Shire DCP — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2015", "source_chapter_key": "sutherland-dcp-residential",
    },
    {
        "lga": "the_hills", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against The Hills DCP",
        "source_text": "Assumed 24m2 standard pattern (The Hills DCP — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2012", "source_chapter_key": "the-hills-dcp-residential",
    },
    {
        "lga": "burwood", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Burwood DCP 2013",
        "source_text": "Assumed 24m2 standard pattern (Burwood DCP 2013 — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2013", "source_chapter_key": "burwood-dcp-2013-residential",
    },
    {
        "lga": "inner_west", "dev_type": "dwelling_house",
        "value_min": 24, "unit": "m2", "needs_review": True,
        "condition": "Assumed standard NSW POS min — verify against Inner West DCP (consolidated)",
        "source_text": "Assumed 24m2 standard pattern (Inner West DCP — needs PDF verification)",
        "section_ref": "residential-pos",
        "dcp_version": "v2023", "source_chapter_key": "inner-west-dcp-residential",
    },
]


def main():
    parser = argparse.ArgumentParser(
        description="Insert private open space controls into dcp_setback_controls"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be inserted without writing to DB")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    inserted = 0
    skipped = 0
    review_count = 0

    for row in POS_ROWS:
        lga = row["lga"]
        dev_type = row["dev_type"]
        needs_review = row["needs_review"]

        # Dedup check — match on lga + control_type + dev_type + condition
        cur.execute("""
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s AND control_type = 'private_open_space'
              AND dev_type = %s
              AND condition = %s
              AND is_current = TRUE
        """, (lga, dev_type, row["condition"]))
        if cur.fetchone():
            print(f"  SKIP dup: {lga} / {dev_type}")
            skipped += 1
            continue

        if needs_review:
            review_count += 1

        if args.dry_run:
            flag = " [NEEDS REVIEW]" if needs_review else ""
            print(f"  DRY-RUN: {lga} / {dev_type} min={row['value_min']}{row['unit']} cond={row['condition'][:60]}{flag}")
        else:
            # INVARIANT: never store a guessed number. An unverified row
            # (needs_review) records only that a POS rule EXISTS — value_min is
            # NULL so the brief shows "check with council", never an assumed
            # figure presented as fact. Verified rows keep their real value.
            value_min = None if needs_review else row["value_min"]
            cur.execute("""
                INSERT INTO dcp_setback_controls
                  (lga, dev_type, control_type, value_min, value_max, unit,
                   condition, applicability, source_text, section_ref,
                   dcp_version, is_current, extraction_method, source_chapter_key,
                   needs_review, review_reason)
                VALUES (%s, %s, 'private_open_space',
                        %s, NULL, %s,
                        %s, %s, %s, %s,
                        %s, TRUE, %s, %s,
                        %s, %s)
            """, (
                lga,
                dev_type,
                value_min,
                row["unit"],
                row["condition"],
                "development_specific" if not needs_review else "universal_residential",
                row["source_text"],
                row["section_ref"],
                row["dcp_version"],
                EXTRACTION_METHOD,
                row["source_chapter_key"],
                needs_review,
                "standard_pattern_assumed" if needs_review else None,
            ))
            inserted += 1

    if not args.dry_run:
        conn.commit()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (duplicates)")
    print(f"  Verified: {inserted - review_count}, Needs review: {review_count}")

    # Summary query
    if not args.dry_run:
        cur.execute("""
            SELECT lga, dev_type, value_min, unit, needs_review,
                   LEFT(condition, 60) as condition_preview
            FROM dcp_setback_controls
            WHERE control_type = 'private_open_space' AND is_current = TRUE
            ORDER BY lga, dev_type
        """)
        rows = cur.fetchall()
        print(f"\n{'LGA':<22} {'Dev Type':<28} {'Min':>5} {'Unit':<4} {'Review':<7} Condition")
        print("-" * 120)
        for r in rows:
            review = "YES" if r["needs_review"] else ""
            print(f"{r['lga']:<22} {r['dev_type']:<28} {r['value_min']:>5} {r['unit']:<4} {review:<7} {r['condition_preview']}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
