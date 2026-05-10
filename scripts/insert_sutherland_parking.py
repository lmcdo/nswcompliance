#!/usr/bin/env python3
"""
Insert Sutherland Shire DCP 2015 parking controls into dcp_setback_controls.

Source: Sutherland Shire DCP 2015, Chapter 36 — Roads, Vehicular Access,
        Traffic, Parking and Bicycles, Table 1 — Car Parking Numbers
        Amendment 6 (adopted March 2021).
        OCR'd via Mistral OCR 2026-05-10 from JoinTheConversation portal.

Notes:
- Dwelling house has min 2, max 4 (only 2 visible from street).
- Secondary dwellings: no parking requirement (SEPP deferral).
- Dual occupancy: min 1 per dwelling, max 3.
- MDH rates apply to zones R2, R3, R4, B1, B2.
- RFB/Shop Top: R4 & R3 have bedroom-based rates; B1-B4 = 1 per unit flat.
- Boarding houses defer to SEPP (Affordable Rental Housing).
- Seniors housing defers to SEPP (Housing for Seniors).

Usage:
    python scripts/insert_sutherland_parking.py --dry-run
    python scripts/insert_sutherland_parking.py
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

LGA = "sutherland_shire"
DCP_VERSION = "v2015-amendment-6-mar2021"
EXTRACTION_METHOD = "mistral_ocr"
SOURCE_CHAPTER_KEY = "ch36-vehicular-access-traffic-parking"

PARKING_ROWS = [
    # ─ Dwelling House ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": 4,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum: 2 spaces per dwelling. Maximum: 4 spaces per dwelling. Only 2 spaces are to be evident when viewed from the street.",
        "section_ref": "ch36-table-1",
    },
    # ─ Dual Occupancy ─
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": 3,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum 1 space per dwelling. Maximum 3 spaces per dwelling. Only 2 spaces evident per development from street.",
        "section_ref": "ch36-table-1",
    },
    # ─ Multi Dwelling Housing (R2/R3/R4/B1/B2) ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": 3,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; zones R2, R3, R4, B1, B2",
        "applicability": "universal_residential",
        "source_text": "Minimum 1 space per 1 bed. Maximum: up to 3 spaces per dwelling.",
        "section_ref": "ch36-table-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": 3,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; zones R2, R3, R4, B1, B2",
        "applicability": "universal_residential",
        "source_text": "1.5 spaces per 2 bed. Maximum: up to 3 spaces per dwelling.",
        "section_ref": "ch36-table-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": 3,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; zones R2, R3, R4, B1, B2",
        "applicability": "universal_residential",
        "source_text": "2 spaces per 3 bed. Maximum: up to 3 spaces per dwelling.",
        "section_ref": "ch36-table-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; 4 or more dwellings",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 4 dwellings",
        "section_ref": "ch36-table-1",
    },
    # ─ Residential Flat Building / Shop Top Housing (R4 & R3) ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": 3,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; zones R4, R3",
        "applicability": "universal_residential",
        "source_text": "Minimum: 1 space per 1 bed. Maximum: up to 3 spaces per dwelling.",
        "section_ref": "ch36-table-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": 3,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; zones R4, R3",
        "applicability": "universal_residential",
        "source_text": "1.5 spaces per 2 bed. Maximum: up to 3 spaces per dwelling.",
        "section_ref": "ch36-table-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": 3,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; zones R4, R3",
        "applicability": "universal_residential",
        "source_text": "2 spaces per 3 bed. Maximum: up to 3 spaces per dwelling.",
        "section_ref": "ch36-table-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; zones R4, R3",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 4 units",
        "section_ref": "ch36-table-1",
    },
    # ─ Shop Top Housing (same rates as RFB per table) ─
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": 3,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; zones R4, R3",
        "applicability": "universal_residential",
        "source_text": "Minimum: 1 space per 1 bed (shop top housing, same as RFB). Maximum: up to 3.",
        "section_ref": "ch36-table-1",
    },
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": 3,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; zones R4, R3",
        "applicability": "universal_residential",
        "source_text": "1.5 spaces per 2 bed (shop top housing). Maximum: up to 3.",
        "section_ref": "ch36-table-1",
    },
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": 3,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; zones R4, R3",
        "applicability": "universal_residential",
        "source_text": "2 spaces per 3 bed (shop top housing). Maximum: up to 3.",
        "section_ref": "ch36-table-1",
    },
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; zones R4, R3",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 4 units (shop top housing)",
        "section_ref": "ch36-table-1",
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
                  f"min={row.get('value_min')} max={row.get('value_max')} "
                  f"unit={row['unit']}")
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
        print(f"\nSutherland parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
