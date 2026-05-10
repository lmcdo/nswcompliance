#!/usr/bin/env python3
"""
Insert Bayside DCP 2022 parking controls into dcp_setback_controls.

Source: Bayside DCP 2022, Section 3.5.3 On-site Car Parking Rates
        Table 3: Car Parking Rates (pages 60-66)
        Adopted 25 March 2026, Effective 17 April 2026, Amendment 2.
        OCR'd via Mistral OCR 2026-05-10.

Notes:
- Bayside is a merged council (former Botany Bay + Rockdale).
- RFB/Shop Top have reduced rates within 800m of a railway station
  (RMS Metropolitan Sub-Regional Centres rates).
- Affordable housing, boarding houses, group homes, co-living,
  seniors housing: all defer to SEPP Housing 2021 — no DCP rate.

Usage:
    python scripts/insert_bayside_parking.py --dry-run
    python scripts/insert_bayside_parking.py
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

LGA = "bayside"
DCP_VERSION = "v2022-amendment-2-apr2026"
EXTRACTION_METHOD = "mistral_ocr"
SOURCE_CHAPTER_KEY = "s3-5-traffic-parking-access"

PARKING_ROWS = [
    # ─ Dwelling House / Dual Occupancy ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling",
        "section_ref": "s3.5.3-table-3",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling",
        "section_ref": "s3.5.3-table-3",
    },
    # ─ Secondary Dwelling ─
    {
        "dev_type": "secondary_dwelling",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "secondary_dwelling_specific",
        "source_text": "1 space per dwelling",
        "section_ref": "s3.5.3-table-3",
    },
    # ─ Multi Dwelling Housing ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom or less",
        "applicability": "universal_residential",
        "source_text": "1 space per dwelling with 1 bedroom or less",
        "section_ref": "s3.5.3-table-3",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms or more",
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling with 2 bedrooms or more",
        "section_ref": "s3.5.3-table-3",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking",
        "applicability": "universal_residential",
        "source_text": "1 visitor parking space per 5 dwellings",
        "section_ref": "s3.5.3-table-3",
    },
    # ─ Residential Flat Buildings ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom or less",
        "applicability": "universal_residential",
        "source_text": "1 space per dwelling with 1 bedroom or less",
        "section_ref": "s3.5.3-table-3",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms or more",
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling with 2 bedrooms or more",
        "section_ref": "s3.5.3-table-3",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking",
        "applicability": "universal_residential",
        "source_text": "1 visitor parking space per 5 dwellings",
        "section_ref": "s3.5.3-table-3",
    },
    # ─ Shop Top Housing (same rates as RFB) ─
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom or less",
        "applicability": "universal_residential",
        "source_text": "1 space per dwelling with 1 bedroom or less (same rate as RFB per Table 3)",
        "section_ref": "s3.5.3-table-3",
    },
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms or more",
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling with 2 bedrooms or more (same rate as RFB per Table 3)",
        "section_ref": "s3.5.3-table-3",
    },
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking",
        "applicability": "universal_residential",
        "source_text": "1 visitor parking space per 5 dwellings (same rate as RFB per Table 3)",
        "section_ref": "s3.5.3-table-3",
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
            print(f"  SKIP dup: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} cond={(row.get('condition') or '')[:40]}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  DRY-RUN: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} max={row.get('value_max','')} "
                  f"unit={row['unit']} cond={(row.get('condition') or '')[:50]}")
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
            print(f"  INSERT: {row['dev_type']} {row['control_type']} "
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
        print(f"\nBayside parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
