#!/usr/bin/env python3
"""
Insert Georges River DCP 2021 parking controls into dcp_setback_controls.

Source: Georges River DCP 2021, Table 3 — Car parking rates
        From "Car parking rates in the Draft Georges River DCP 2020" PDF
        (rates adopted by Council 27 April 2020, carried into GRDCP 2021).
        OCR'd via Mistral OCR 2026-05-10.

Notes:
- Georges River is a merged council (former Hurstville + Kogarah).
- Rates sourced from combination of Hurstville DCP No.1 and Kogarah DCP.
- Secondary dwellings: no additional parking required (SEPP deferral).
- Boarding houses: defer to SEPP (Affordable Rental Housing / Housing 2021).
- Multi dwelling housing has separate rates for terraces vs non-terraces.
- RFB near stations (<800m): ADG/SEPP 65 overrides DCP rates.
- Dual occupancy: "1 garage space and 1 driveway space per dwelling" = 2 total.

Usage:
    python scripts/insert_georges_river_parking.py --dry-run
    python scripts/insert_georges_river_parking.py
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

LGA = "georges_river"
DCP_VERSION = "v2021"
EXTRACTION_METHOD = "mistral_ocr"
SOURCE_CHAPTER_KEY = "part-3-general-planning-considerations"

PARKING_ROWS = [
    # ─ Dwelling House ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1-2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1 space per 1 and 2 beds",
        "section_ref": "table-3",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 spaces per 3 beds or more",
        "section_ref": "table-3",
    },
    # ─ Dual Occupancy ─
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "1 garage space and 1 driveway space per dwelling",
        "section_ref": "table-3",
    },
    # ─ Multi Dwelling Housing (terraces) ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "terraces",
        "applicability": "universal_residential",
        "source_text": "1 space per dwelling (terraces)",
        "section_ref": "table-3",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; terraces; 5 or more dwellings",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 5 units or part thereof (terraces)",
        "section_ref": "table-3",
    },
    # ─ Multi Dwelling Housing (excluding terraces) ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "excluding terraces",
        "applicability": "universal_residential",
        "source_text": "1.5 spaces per dwelling (excluding terraces)",
        "section_ref": "table-3",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; excluding terraces; 5 or more dwellings",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 5 units or part thereof (excluding terraces)",
        "section_ref": "table-3",
    },
    # ─ Residential Flat Building ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio, 1 or 2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1 space per studio, 1 and 2 beds",
        "section_ref": "table-3",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 spaces per 3 beds or more",
        "section_ref": "table-3",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; 5 or more dwellings",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 5 units or part thereof",
        "section_ref": "table-3",
    },
    # ─ Shop Top Housing (same rates as RFB per table) ─
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio, 1 or 2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1 space per studio, 1 and 2 beds (shop-top housing)",
        "section_ref": "table-3",
    },
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 spaces per 3 beds or more (shop-top housing)",
        "section_ref": "table-3",
    },
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; 5 or more dwellings",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 5 units or part thereof (shop-top housing)",
        "section_ref": "table-3",
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
                  f"min={row.get('value_min')} max={row.get('value_max','')} "
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
                  DCP_VERSION, EXTRACTION_METHOD, SOURCE_CHAPTER_KEY))
            print(f"  INSERT: {row['dev_type']} "
                  f"min={row.get('value_min')} unit={row['unit']}")
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
        print(f"\nGeorges River parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
