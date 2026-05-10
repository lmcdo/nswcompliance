#!/usr/bin/env python3
"""
Insert Inner West parking controls from three former council DCPs.

Inner West Council was formed by merging Ashfield, Leichhardt, and
Marrickville councils. Each has a separate DCP still in force:

1. Comprehensive Inner West DCP 2016 (former Ashfield area)
   - Chapter A, Table 3: Car Parking Rates
   - Simple minimum rates

2. Leichhardt DCP 2013
   - Part C Section 1, Table C4: General Vehicle Parking Rates
   - Min/max ranges for residential, with visitor min/max

3. Marrickville DCP 2011
   - Part 2.10, Table 1: Onsite car parking requirements
   - Three parking areas (1=most constrained, 3=least constrained)
   - Very low rates in Area 1 (transit-rich)

Notes:
- Each row tagged with condition prefix identifying which DCP applies.
- Leichhardt uses MAXIMUM rates (like Waverley/Woollahra).
- Marrickville Area 1 has NO visitor parking for RFB.
- Secondary dwellings: Ashfield & Marrickville = 1 combined with principal.
  Leichhardt = nil minimum, max 2 (same as dwelling house).

Usage:
    python scripts/insert_inner_west_parking.py --dry-run
    python scripts/insert_inner_west_parking.py
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

LGA = "inner_west"
EXTRACTION_METHOD = "text_extraction"

PARKING_ROWS = [
    # ═══════════════════════════════════════════════════════════════
    # ASHFIELD AREA — Comprehensive Inner West DCP 2016 Chapter A Table 3
    # ═══════════════════════════════════════════════════════════════

    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 1, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "former Ashfield area; preferably 2",
        "applicability": "universal_residential",
        "source_text": "Ashfield DCP Table 3: 1 space per dwelling (preferably 2)",
        "section_ref": "table-3",
        "dcp_version": "v2016-iw-comprehensive",
        "source_chapter_key": "ashfield-chapter-a-miscellaneous",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "former Ashfield area; plus 1 per 5x 2-bed units + 1 per 2x 3-bed units",
        "applicability": "universal_residential",
        "source_text": "Ashfield DCP Table 3: MDH 1 space/unit + 1/5 for 2-bed + 1/2 for 3-bed",
        "section_ref": "table-3",
        "dcp_version": "v2016-iw-comprehensive",
        "source_chapter_key": "ashfield-chapter-a-miscellaneous",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.2, "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; former Ashfield area",
        "applicability": "universal_residential",
        "source_text": "Ashfield DCP Table 3: MDH visitor 1 per 5 units",
        "section_ref": "table-3",
        "dcp_version": "v2016-iw-comprehensive",
        "source_chapter_key": "ashfield-chapter-a-miscellaneous",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "former Ashfield area; B1/B2/B4 zones",
        "applicability": "universal_residential",
        "source_text": "Ashfield DCP Table 3: RFB minimum 1 space for all dwellings",
        "section_ref": "table-3",
        "dcp_version": "v2016-iw-comprehensive",
        "source_chapter_key": "ashfield-chapter-a-miscellaneous",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.25, "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; former Ashfield area",
        "applicability": "universal_residential",
        "source_text": "Ashfield DCP Table 3: RFB visitor 1 per 4 dwellings",
        "section_ref": "table-3",
        "dcp_version": "v2016-iw-comprehensive",
        "source_chapter_key": "ashfield-chapter-a-miscellaneous",
    },

    # ═══════════════════════════════════════════════════════════════
    # LEICHHARDT AREA — Leichhardt DCP 2013, Part C, Table C4
    # Uses min/max ranges
    # ═══════════════════════════════════════════════════════════════

    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": None, "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": "former Leichhardt area; maximum rate",
        "applicability": "universal_residential",
        "source_text": "Leichhardt DCP Table C4: dwelling house max 2 spaces",
        "section_ref": "table-c4",
        "dcp_version": "v2013-leichhardt",
        "source_chapter_key": "leichhardt-part-c-section-1",
    },
    # RFB/MDH rates (Leichhardt doesn't distinguish MDH from RFB in Table C4)
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None, "value_max": 0.5,
        "unit": "spaces/dwelling",
        "condition": "studio; former Leichhardt area; maximum rate",
        "applicability": "universal_residential",
        "source_text": "Leichhardt DCP Table C4: studio max 0.5/dwelling",
        "section_ref": "table-c4",
        "dcp_version": "v2013-leichhardt",
        "source_chapter_key": "leichhardt-part-c-section-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.333, "value_max": 0.5,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; former Leichhardt area",
        "applicability": "universal_residential",
        "source_text": "Leichhardt DCP Table C4: 1 bed min 1/3, max 0.5/dwelling",
        "section_ref": "table-c4",
        "dcp_version": "v2013-leichhardt",
        "source_chapter_key": "leichhardt-part-c-section-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.5, "value_max": 1,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; former Leichhardt area",
        "applicability": "universal_residential",
        "source_text": "Leichhardt DCP Table C4: 2 bed min 0.5, max 1/dwelling",
        "section_ref": "table-c4",
        "dcp_version": "v2013-leichhardt",
        "source_chapter_key": "leichhardt-part-c-section-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1, "value_max": 1.2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; former Leichhardt area",
        "applicability": "universal_residential",
        "source_text": "Leichhardt DCP Table C4: 3+ bed min 1, max 1.2/dwelling",
        "section_ref": "table-c4",
        "dcp_version": "v2013-leichhardt",
        "source_chapter_key": "leichhardt-part-c-section-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.091, "value_max": 0.125,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; former Leichhardt area",
        "applicability": "universal_residential",
        "source_text": "Leichhardt DCP Table C4: visitor min 1/11, max 0.125/dwelling",
        "section_ref": "table-c4",
        "dcp_version": "v2013-leichhardt",
        "source_chapter_key": "leichhardt-part-c-section-1",
    },

    # ═══════════════════════════════════════════════════════════════
    # MARRICKVILLE AREA — Marrickville DCP 2011, Part 2.10, Table 1
    # Three parking areas
    # ═══════════════════════════════════════════════════════════════

    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 1, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "former Marrickville area; all parking areas",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: 1 per dwelling house (all areas)",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },

    # RFB Area 1 (most constrained — transit-rich)
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.2, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio; former Marrickville Parking Area 1",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 1 studio 0.2/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.4, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; former Marrickville Parking Area 1",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 1 1bed 0.4/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.8, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; former Marrickville Parking Area 1",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 1 2bed 0.8/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.1, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; former Marrickville Parking Area 1",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 1 3+bed 1.1/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    # RFB Area 2
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.4, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio; former Marrickville Parking Area 2",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 2 studio 0.4/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.5, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; former Marrickville Parking Area 2",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 2 1bed 0.5/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; former Marrickville Parking Area 2",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 2 2bed 1.0/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.2, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; former Marrickville Parking Area 2",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 2 3+bed 1.2/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.1, "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; former Marrickville Parking Area 2",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 2 visitor 0.1/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    # RFB Area 3
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.6, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio; former Marrickville Parking Area 3",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 3 studio 0.6/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.8, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; former Marrickville Parking Area 3",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 3 1bed 0.8/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.2, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; former Marrickville Parking Area 3",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 3 2bed 1.2/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.2, "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; former Marrickville Parking Area 3",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 3 3+bed 1.2/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.1, "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; former Marrickville Parking Area 3",
        "applicability": "universal_residential",
        "source_text": "Marrickville DCP Table 1: RFB Area 3 visitor 0.1/dwelling",
        "section_ref": "table-1",
        "dcp_version": "v2011-marrickville",
        "source_chapter_key": "marrickville-part-2-10-parking",
    },
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    inserted = 0
    skipped = 0

    for row in PARKING_ROWS:
        dcp_version = row.pop("dcp_version")
        chapter_key = row.pop("source_chapter_key")

        cur.execute("""
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s AND dev_type = %s AND control_type = %s
              AND COALESCE(condition, '') = COALESCE(%s, '')
              AND COALESCE(value_min::text, '') = COALESCE(%s::text, '')
              AND is_current = TRUE
        """, (LGA, row["dev_type"], row["control_type"],
              row.get("condition"), row.get("value_min")))
        if cur.fetchone():
            print(f"  SKIP dup: {row['dev_type']} "
                  f"min={row.get('value_min')} cond={(row.get('condition') or '')[:50]}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  DRY-RUN: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} max={row.get('value_max')} "
                  f"unit={row['unit']} cond={(row.get('condition') or '')[:55]}")
        else:
            cur.execute("""
                INSERT INTO dcp_setback_controls
                  (lga, dev_type, control_type, value_min, value_max, unit,
                   condition, applicability, source_text, section_ref,
                   dcp_version, is_current, extraction_method, source_chapter_key)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s,%s)
            """, (LGA, row["dev_type"], row["control_type"],
                  row.get("value_min"), row.get("value_max"), row["unit"],
                  row.get("condition"), row["applicability"],
                  row["source_text"], row["section_ref"],
                  dcp_version, EXTRACTION_METHOD, chapter_key))
            print(f"  INSERT: {row['dev_type']} min={row.get('value_min')} "
                  f"max={row.get('value_max')} unit={row['unit']}")
            inserted += 1

    if not args.dry_run:
        conn.commit()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (duplicates)")

    if not args.dry_run and inserted > 0:
        cur.execute("""
            SELECT dev_type, count(*) as n
            FROM dcp_setback_controls
            WHERE lga = %s AND control_type = 'car_parking' AND is_current = TRUE
            GROUP BY dev_type ORDER BY dev_type
        """, (LGA,))
        print(f"\nInner West parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
