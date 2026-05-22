#!/usr/bin/env python3
"""
Gap-fill missing DCP controls for mid-volume LGAs + Inner West former councils.

Fills verified numeric values where DCP has them, literal DCP citations
(value_min=NULL) where the DCP defers or uses performance-based assessment,
and needs_review=TRUE where PDF extraction was blocked.

Councils: Ryde (178 DAs), Canada Bay (138), Strathfield (70), Burwood (39),
Ashfield, Leichhardt, Marrickville (Inner West former councils).

Usage:
    python scripts/insert_gap_fill_mid_volume.py --dry-run
    python scripts/insert_gap_fill_mid_volume.py
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

GAP_ROWS = [
    # ══════════════════════════════════════════════════════════════
    # RYDE (178 DAs/yr) — missing: deep_soil_min, max_site_coverage,
    #   landscaping_min
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "ryde",
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 35,
        "unit": "%",
        "condition": "35% of allotment area as deep soil; must include 8m x 8m "
                     "area in back yard + fully permeable front garden",
        "applicability": "universal_residential",
        "source_text": "City of Ryde DCP 2014 Part 3.3 s2.6.1 (Deep Soil Areas): "
                       "'Sites are to have a deep soil area that is at least 35% "
                       "of the area of the allotment.' 'The deep soil area must "
                       "include: i. an area with minimum dimensions of 8 m x 8 m "
                       "in the back yard; and ii. a front garden area which is to "
                       "be completely permeable with the exception of the driveway, "
                       "pedestrian path and garden walls.'",
        "section_ref": "s2.6.1",
        "source_chapter_key": "part-3.3-dwelling-houses",
        "dcp_version": "v2014-current",
        "needs_review": False,
    },
    {
        "lga": "ryde",
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_max": None,
        "unit": "%",
        "condition": "No DCP site coverage control; density controlled by FSR "
                     "0.5:1 (LEP 2014) + 35% deep soil + setbacks",
        "applicability": "universal_residential",
        "source_text": "City of Ryde DCP 2014 Part 3.3: No maximum site coverage "
                       "percentage for dwelling houses. Site bulk is controlled "
                       "indirectly through FSR of 0.5:1 (Ryde LEP 2014 s2.7), the "
                       "35% deep soil requirement (s2.6.1), and setback controls "
                       "(s2.8).",
        "section_ref": "part-3.3",
        "source_chapter_key": "part-3.3-dwelling-houses",
        "dcp_version": "v2014-current",
        "needs_review": False,
    },
    {
        "lga": "ryde",
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": None,
        "unit": "%",
        "condition": "No whole-of-site landscaping %; front garden hard paving "
                     "max 40% (s2.13). Deep soil 35% (s2.6.1) acts as proxy",
        "applicability": "universal_residential",
        "source_text": "City of Ryde DCP 2014 Part 3.3 s2.13 (Landscaping) "
                       "Control (e): 'Provide a landscaped front garden. Hard "
                       "paved areas are to be minimised, and at a maximum, are "
                       "to be no more than 40% of the front garden areas.' No "
                       "whole-of-site landscaping minimum percentage. The 35% "
                       "deep soil requirement (s2.6.1) serves as the primary "
                       "soft landscape control.",
        "section_ref": "s2.13",
        "source_chapter_key": "part-3.3-dwelling-houses",
        "dcp_version": "v2014-current",
        "needs_review": False,
    },

    # ══════════════════════════════════════════════════════════════
    # CANADA BAY (138 DAs/yr) — missing: deep_soil_min,
    #   max_site_coverage, landscaping_min
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "canada_bay",
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": None,
        "unit": "%",
        "condition": "Deep soil zones only apply to Part G (Local Centres) and "
                     "Part K (Special Precincts); not applicable to Part E "
                     "(Single Dwellings)",
        "applicability": "universal_residential",
        "source_text": "Canada Bay DCP 2020 Part L (Definitions): 'Deep soil "
                       "zones are areas of soil that are unencumbered by "
                       "buildings or structures...' 'Note: Deep soil zones only "
                       "apply where specified in Part G and K of this DCP.' "
                       "Part E (Single Dwellings) has no deep soil zone control.",
        "section_ref": "part-L-definitions",
        "source_chapter_key": "part-e-single-dwellings",
        "dcp_version": "v2020-current",
        "needs_review": False,
    },
    {
        "lga": "canada_bay",
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_max": None,
        "unit": "%",
        "condition": "No DCP site coverage control; defers entirely to Canada "
                     "Bay LEP 2013 clause 4.3A (mapped per lot)",
        "applicability": "universal_residential",
        "source_text": "Canada Bay DCP 2020 Part L (Definitions) — Site "
                       "Coverage: 'Note: Refer to the Canada Bay Local "
                       "Environmental Plan for definition.' Part E contains "
                       "zero mentions of 'site coverage'. Maximum site coverage "
                       "is controlled entirely by Canada Bay LEP 2013 clause "
                       "4.3A, mapped per lot.",
        "section_ref": "part-L-definitions",
        "source_chapter_key": "part-e-single-dwellings",
        "dcp_version": "v2020-current",
        "needs_review": False,
    },
    {
        "lga": "canada_bay",
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 35,
        "unit": "%",
        "condition": "35% of parent lot site area; 50% of front setback + 50% "
                     "of rear setback landscaped; areas <1.5mx1.5m excluded",
        "applicability": "universal_residential",
        "source_text": "Canada Bay DCP 2020 s E4.6 C4 Table E-A: Minimum "
                       "Landscaped Areas for Single dwellings — 35% of parent "
                       "lot site area, with 50% of front setback to be "
                       "landscaped, 50% of rear setback to be landscaped, and "
                       "40% in Biodiversity Corridor areas. C1: landscaping "
                       "<1.5m x 1.5m excluded. C2: side setback landscaping "
                       "excluded. Definition excludes areas above basements, "
                       "OSD tanks, synthetic turf, permeable paving, gravel, "
                       "and impervious surfaces.",
        "section_ref": "E4.6-C4",
        "source_chapter_key": "part-e-single-dwellings",
        "dcp_version": "v2020-current",
        "needs_review": False,
    },

    # ══════════════════════════════════════════════════════════════
    # STRATHFIELD (70 DAs/yr) — missing: front_setback, rear_setback,
    #   max_site_coverage, landscaping_min
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "strathfield",
        "dev_type": "dwelling_house",
        "control_type": "front_setback",
        "value_min": 9,
        "unit": "m",
        "condition": "Primary street setback 9m; may be reduced if predominant "
                     "setback in street block is less, or not less than existing",
        "applicability": "universal_residential",
        "source_text": "Strathfield Consolidated DCP 2005 Part A s10.3.1 "
                       "Control 1: 'Primary street setback: 9m.' Control 2: "
                       "A setback less than 9m may be considered where the "
                       "predominant front setback in the street block is less "
                       "than 9m, or the proposed setback is not less than the "
                       "existing dwelling's setback.",
        "section_ref": "s10.3.1",
        "source_chapter_key": "part-a-dwelling-houses",
        "dcp_version": "v2005-amendment-14-sep2020",
        "needs_review": False,
    },
    {
        "lga": "strathfield",
        "dev_type": "dwelling_house",
        "control_type": "rear_setback",
        "value_min": 6,
        "unit": "m",
        "condition": "Minimum 6m rear setback for dwelling; excludes "
                     "outbuildings (0.5m minimum)",
        "applicability": "universal_residential",
        "source_text": "Strathfield Consolidated DCP 2005 Part A s10.3.2 "
                       "Control 2: 'Rear setbacks for the dwelling are to be "
                       "a minimum of 6m to provide adequately sized outdoor "
                       "living areas and adequate deep soil areas for shading/"
                       "screening trees.' Excludes outbuildings which have "
                       "0.5m minimum.",
        "section_ref": "s10.3.2",
        "source_chapter_key": "part-a-dwelling-houses",
        "dcp_version": "v2005-amendment-14-sep2020",
        "needs_review": False,
    },
    {
        "lga": "strathfield",
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_max": None,
        "unit": "%",
        "condition": "No standalone site coverage control; bulk controlled by "
                     "FSR (SLEP 2012) + minimum landscaped area (Table 2)",
        "applicability": "universal_residential",
        "source_text": "Strathfield Consolidated DCP 2005 Part A: No maximum "
                       "site coverage percentage for dwelling houses. Appendix "
                       "1 lists no site coverage control. Bulk is controlled "
                       "through FSR (SLEP 2012 FSR Map, referenced s7.3 "
                       "Control 1 Table 1) combined with minimum landscaped "
                       "area requirements (s9.3.1 Table 2).",
        "section_ref": "part-a-appendix-1",
        "source_chapter_key": "part-a-dwelling-houses",
        "dcp_version": "v2005-amendment-14-sep2020",
        "needs_review": False,
    },
    {
        "lga": "strathfield",
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 10,
        "value_max": 45,
        "unit": "%",
        "condition": "Variable by lot size: 200-300m2=10%, 300-450m2=15%, "
                     "450-600m2=20%, 600-900m2=30%, 900-1500m2=40%, >1500m2=45%",
        "applicability": "universal_residential",
        "source_text": "Strathfield Consolidated DCP 2005 Part A s9.3.1 "
                       "Table 2: Minimum landscaped area as % of lot area — "
                       "200-300sqm: 10%, 300-450sqm: 15%, 450-600sqm: 20%, "
                       "600-900sqm: 30%, 900-1500sqm: 40%, over 1500sqm: 45%. "
                       "Appendix 1 also requires 50% of front setback as "
                       "minimum deep soil soft landscaping.",
        "section_ref": "s9.3.1",
        "source_chapter_key": "part-a-dwelling-houses",
        "dcp_version": "v2005-amendment-14-sep2020",
        "needs_review": False,
    },

    # ══════════════════════════════════════════════════════════════
    # BURWOOD (39 DAs/yr) — missing: rear_setback, landscaping_min
    # PDF inaccessible — flag for manual review
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "burwood",
        "dev_type": "dwelling_house",
        "control_type": "rear_setback",
        "value_min": None,
        "unit": "m",
        "condition": "Table 3 (Setback Requirements for Single Dwelling Houses) "
                     "contains rear setback — value not yet extracted",
        "applicability": "universal_residential",
        "source_text": "Burwood DCP 2013 Part 4 (Development in Residential "
                       "Areas) Table 3: Setback Requirements for Single "
                       "Dwelling Houses — contains rear setback value. PDF "
                       "access blocked (403/size limit). Amendment No. 13, "
                       "adopted 28 Oct 2025, effective 3 Nov 2025.",
        "section_ref": "part-4-table-3",
        "source_chapter_key": "part-4-residential",
        "dcp_version": "v2013-amendment-13-nov2025",
        "needs_review": True,
        "review_reason": "PDF inaccessible — rear setback value in Table 3 "
                         "needs manual extraction from Burwood DCP Part 4",
    },
    {
        "lga": "burwood",
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": None,
        "unit": "%",
        "condition": "Section 4.5.3.9 (Landscaped Areas) contains minimum — "
                     "value not yet extracted",
        "applicability": "universal_residential",
        "source_text": "Burwood DCP 2013 Part 4 s4.5.3.9 (Landscaped Areas): "
                       "Contains minimum landscaped area percentage for "
                       "dwelling houses. PDF access blocked (403/size limit). "
                       "Amendment No. 13, adopted 28 Oct 2025, effective "
                       "3 Nov 2025.",
        "section_ref": "s4.5.3.9",
        "source_chapter_key": "part-4-residential",
        "dcp_version": "v2013-amendment-13-nov2025",
        "needs_review": True,
        "review_reason": "PDF inaccessible — landscaping_min value in s4.5.3.9 "
                         "needs manual extraction from Burwood DCP Part 4",
    },

    # ══════════════════════════════════════════════════════════════
    # ASHFIELD (Inner West former) — missing: deep_soil_min,
    #   landscaping_min, max_site_coverage
    # DCP is deliberately performance-based for dwelling houses
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "ashfield",
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": None,
        "unit": "%",
        "condition": "Performance-based assessment; no numeric deep soil "
                     "control for dwelling houses",
        "applicability": "universal_residential",
        "source_text": "Ashfield DCP 2016 (CIWDCP 2016) Chapter F: The DCP "
                       "explicitly states it has 'minimal numerical, "
                       "prescriptive controls' for dwelling houses. The "
                       "approach is 'performance based' — 'each Development "
                       "Application is to respond to a Site Analysis and will "
                       "be assessed and determined on its own individual merits.' "
                       "No numeric deep soil minimum is prescribed.",
        "section_ref": "chapter-F",
        "source_chapter_key": "chapter-f-development-category",
        "dcp_version": "v2016-IWLEP2022-amendments",
        "needs_review": False,
    },
    {
        "lga": "ashfield",
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": None,
        "unit": "%",
        "condition": "Performance-based assessment; no numeric landscaping "
                     "minimum for dwelling houses",
        "applicability": "universal_residential",
        "source_text": "Ashfield DCP 2016 (CIWDCP 2016) Chapter F: Uses "
                       "performance-based assessment for dwelling houses with "
                       "'minimal numerical, prescriptive controls'. No minimum "
                       "landscaped area percentage is prescribed. Development "
                       "assessed on streetscape compatibility merits.",
        "section_ref": "chapter-F",
        "source_chapter_key": "chapter-f-development-category",
        "dcp_version": "v2016-IWLEP2022-amendments",
        "needs_review": False,
    },
    {
        "lga": "ashfield",
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_max": None,
        "unit": "%",
        "condition": "Performance-based assessment; no numeric site coverage "
                     "control for dwelling houses",
        "applicability": "universal_residential",
        "source_text": "Ashfield DCP 2016 (CIWDCP 2016) Chapter F: Uses "
                       "performance-based assessment for dwelling houses. No "
                       "maximum site coverage percentage is prescribed. 'No "
                       "design solution is provided for dwelling houses; "
                       "streetscape compatibility is assessed on merit.'",
        "section_ref": "chapter-F",
        "source_chapter_key": "chapter-f-development-category",
        "dcp_version": "v2016-IWLEP2022-amendments",
        "needs_review": False,
    },

    # ══════════════════════════════════════════════════════════════
    # LEICHHARDT (Inner West former) — missing: deep_soil_min,
    #   landscaping_min, max_site_coverage
    # Scanned image PDFs — flag for manual review
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "leichhardt",
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": None,
        "unit": "%",
        "condition": "DCP value exists but PDF is scanned image — not yet "
                     "extracted",
        "applicability": "universal_residential",
        "source_text": "Leichhardt DCP 2013 Part C Section 3 (Residential "
                       "Provisions): Contains deep soil controls by Distinctive "
                       "Neighbourhood. PDF is hosted as scanned image on Inner "
                       "West Council website — machine extraction not possible. "
                       "Amendment No. 13, with IWLEP 2022 amendments.",
        "section_ref": "part-C-s3",
        "source_chapter_key": "part-c-s3-residential",
        "dcp_version": "v2013-amendment-13-IWLEP2022",
        "needs_review": True,
        "review_reason": "Scanned image PDF — deep_soil_min value needs manual "
                         "extraction from Leichhardt DCP Part C Section 3",
    },
    {
        "lga": "leichhardt",
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": None,
        "unit": "%",
        "condition": "Qualitative: 'soft landscape areas must be included at "
                     "front and rear of site' — numeric value in scanned PDF",
        "applicability": "universal_residential",
        "source_text": "Leichhardt DCP 2013 Part C Section 3 (Residential "
                       "Provisions): Qualitative requirement that 'soft "
                       "landscape areas must be included at the front and "
                       "rear of the site' and 'landscaping should be "
                       "consolidated to support significant tree planting'. "
                       "Numeric percentage may exist in scanned image PDF "
                       "but could not be machine-extracted.",
        "section_ref": "part-C-s3",
        "source_chapter_key": "part-c-s3-residential",
        "dcp_version": "v2013-amendment-13-IWLEP2022",
        "needs_review": True,
        "review_reason": "Scanned image PDF — landscaping_min numeric value "
                         "needs manual extraction from Leichhardt DCP Part C S3",
    },
    {
        "lga": "leichhardt",
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_max": None,
        "unit": "%",
        "condition": "DCP value exists (place-based by Distinctive "
                     "Neighbourhood) but PDF is scanned image",
        "applicability": "universal_residential",
        "source_text": "Leichhardt DCP 2013 Part C Section 3 (Residential "
                       "Provisions): Site coverage controls are specified by "
                       "Distinctive Neighbourhood (place-based). PDF is "
                       "hosted as scanned image — machine extraction not "
                       "possible. Amendment No. 13, with IWLEP 2022 amendments.",
        "section_ref": "part-C-s3",
        "source_chapter_key": "part-c-s3-residential",
        "dcp_version": "v2013-amendment-13-IWLEP2022",
        "needs_review": True,
        "review_reason": "Scanned image PDF — max_site_coverage values by "
                         "neighbourhood need manual extraction from Leichhardt "
                         "DCP Part C Section 3",
    },

    # ══════════════════════════════════════════════════════════════
    # MARRICKVILLE (Inner West former) — missing: deep_soil_min,
    #   landscaping_min, max_site_coverage
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "marrickville",
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": None,
        "unit": "%",
        "condition": "No specific deep soil % for dwelling houses; s2.18 "
                     "references deep soil planting within landscaped area",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP 2011 s2.18 (Landscaping and Open "
                       "Spaces): References deep soil planting. s2.18.7 (C5): "
                       "'Landscaping over podiums or basement car parking must "
                       "not exceed 30% of the required total landscape area "
                       "component.' No specific deep soil zone percentage is "
                       "prescribed for dwelling houses.",
        "section_ref": "s2.18",
        "source_chapter_key": "s4.1-low-density-residential",
        "dcp_version": "v2011-amendment-18-IWLEP2022",
        "needs_review": False,
    },
    {
        "lga": "marrickville",
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": None,
        "unit": "%",
        "condition": "Front setback must be pervious landscape (s2.18.11.1 "
                     "C11); no whole-of-site numeric minimum confirmed",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP 2011 s2.18.11.1 C11: 'The entire "
                       "front setback must be of a pervious landscape with "
                       "the exception of driveways and pathways.' C12 "
                       "references '20% of the total site area' in the "
                       "context of private open space. No single whole-of-site "
                       "landscaping minimum percentage confirmed for dwelling "
                       "houses. PDF is scanned image — full values may exist "
                       "but could not be machine-extracted.",
        "section_ref": "s2.18.11.1",
        "source_chapter_key": "s4.1-low-density-residential",
        "dcp_version": "v2011-amendment-18-IWLEP2022",
        "needs_review": True,
        "review_reason": "Scanned image PDF — landscaping_min numeric value "
                         "may exist in Marrickville DCP s2.18 but could not "
                         "be machine-extracted",
    },
    {
        "lga": "marrickville",
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_max": None,
        "unit": "%",
        "condition": "Per Table 1 at s4.1.6.3 — values by allotment area but "
                     "PDF is scanned image",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP 2011 s4.1.6.3: 'Maximum site coverage "
                       "must be in accordance with Table 1.' Table 1 sets site "
                       "coverage by allotment area. PDF is scanned image — the "
                       "exact values from Table 1 could not be machine-extracted.",
        "section_ref": "s4.1.6.3",
        "source_chapter_key": "s4.1-low-density-residential",
        "dcp_version": "v2011-amendment-18-IWLEP2022",
        "needs_review": True,
        "review_reason": "Scanned image PDF — max_site_coverage Table 1 values "
                         "need manual extraction from Marrickville DCP s4.1.6.3",
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Gap-fill controls for mid-volume LGAs + Inner West"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Print what would be inserted without writing to DB",
    )
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    inserted = 0
    skipped = 0
    errors = 0

    for row in GAP_ROWS:
        lga = row["lga"]
        dev_type = row["dev_type"]
        control_type = row["control_type"]
        condition = row["condition"]

        # Dedup check
        condition_prefix = condition[:30]
        cur.execute(
            """
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s
              AND control_type = %s
              AND dev_type = %s
              AND condition LIKE %s
              AND is_current = TRUE
            """,
            (lga, control_type, dev_type, condition_prefix + "%"),
        )
        if cur.fetchone():
            skipped += 1
            if args.dry_run:
                print(f"  SKIP (exists): {lga} / {control_type} / {condition_prefix}...")
            continue

        # Determine value and column
        has_value_min = "value_min" in row
        has_value_max = "value_max" in row

        if has_value_min and has_value_max:
            # Both columns — need two-column INSERT
            val_min = row["value_min"]
            val_max = row["value_max"]
        elif has_value_min:
            val_min = row["value_min"]
            val_max = None
        else:
            val_min = None
            val_max = row.get("value_max")

        if args.dry_run:
            parts = []
            if val_min is not None:
                parts.append(f"min={val_min}")
            if val_max is not None:
                parts.append(f"max={val_max}")
            val_str = ", ".join(parts) if parts else "NULL"
            print(f"  INSERT: {lga} / {control_type} / {dev_type} / {val_str} {row['unit']}")
            print(f"          {condition[:80]}")
            inserted += 1
            continue

        try:
            cur.execute(
                """
                INSERT INTO dcp_setback_controls (
                    lga, dev_type, control_type, value_min, value_max, unit,
                    condition, applicability, source_text, section_ref,
                    source_chapter_key, dcp_version, is_current,
                    extraction_method, needs_review, review_reason
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, TRUE,
                    %s, %s, %s
                )
                """,
                (
                    lga,
                    dev_type,
                    control_type,
                    val_min,
                    val_max,
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
            print(f"  ERROR: {lga} / {control_type}: {e}")
            conn.rollback()

    if not args.dry_run and errors == 0:
        conn.commit()
        print(f"\nCommitted {inserted} rows.")
    elif args.dry_run:
        print(f"\n[DRY RUN] Would insert {inserted} rows, skip {skipped} existing.")
    else:
        print(f"\n{errors} errors — transaction rolled back. No rows written.")

    # Summary
    print(f"\n{'='*70}")
    print(f"{'LGA':<22} {'Control':<22} {'Value':>8} {'Status'}")
    print(f"{'-'*70}")
    for row in GAP_ROWS:
        val_min = row.get("value_min")
        val_max = row.get("value_max")
        if val_min is not None and val_max is not None:
            val_str = f"{val_min}-{val_max}"
        elif val_min is not None:
            val_str = f"{val_min}"
        elif val_max is not None:
            val_str = f"{val_max}"
        else:
            val_str = "NULL"
        if row.get("needs_review"):
            status = "REVIEW"
        elif val_min is None and val_max is None:
            status = "NO_RATE"
        else:
            status = "VERIFIED"
        print(f"{row['lga']:<22} {row['control_type']:<22} {val_str:>8} {status}")
    print(f"{'-'*70}")
    print(f"Total rows: {len(GAP_ROWS)}")
    print(f"Inserted: {inserted}, Skipped: {skipped}, Errors: {errors}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
