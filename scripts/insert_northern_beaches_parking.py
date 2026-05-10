#!/usr/bin/env python3
"""
Insert Northern Beaches parking controls into dcp_setback_controls.

Source: Warringah DCP 2011 (as amended 7 May 2016), Appendix 1
        (downloaded from NSW Planning Portal S3 mirror, 2026-05-10).

Notes:
- The Warringah DCP applies to the former Warringah area of Northern Beaches.
  Pittwater and Manly areas have separate DCPs (not extracted here).
- Simple minimum rates, no transit-proximity differentiation.
- No secondary_dwelling listed — SEPP Housing 2021 deferral.
- Boarding houses/group homes: "comparisons with similar developments" (not a fixed rate).

Usage:
    python scripts/insert_northern_beaches_parking.py --dry-run
    python scripts/insert_northern_beaches_parking.py
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

LGA = "northern_beaches"
DCP_VERSION = "v2011-warringah-amended-may2016"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "warringah-appendix-1-car-parking"

PARKING_ROWS = [
    # ─ Dwelling House ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "former Warringah area",
        "applicability": "universal_residential",
        "source_text": "Dwelling house: 2 spaces per dwelling (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },

    # ─ Dual Occupancy ─
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "former Warringah area",
        "applicability": "universal_residential",
        "source_text": "Dual occupancy: 2 spaces per dwelling (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },

    # ─ Multi Dwelling Housing ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; former Warringah area",
        "applicability": "universal_residential",
        "source_text": "MDH: 1 space per 1 bedroom dwelling (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; former Warringah area",
        "applicability": "universal_residential",
        "source_text": "MDH: 1.2 spaces per 2 bedroom dwelling (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; former Warringah area",
        "applicability": "universal_residential",
        "source_text": "MDH: 1.5 spaces per 3 bedroom dwelling (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; former Warringah area",
        "applicability": "universal_residential",
        "source_text": "MDH: 1 visitor space per 5 units (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },

    # ─ Residential Flat Building ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; former Warringah area",
        "applicability": "universal_residential",
        "source_text": "RFB: 1 space per 1 bedroom dwelling (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; former Warringah area",
        "applicability": "universal_residential",
        "source_text": "RFB: 1.2 spaces per 2 bedroom dwelling (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; former Warringah area",
        "applicability": "universal_residential",
        "source_text": "RFB: 1.5 spaces per 3 bedroom dwelling (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; former Warringah area",
        "applicability": "universal_residential",
        "source_text": "RFB: 1 visitor space per 5 units (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },

    # ─ Shop Top Housing (residential component) ─
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; former Warringah area; residential component",
        "applicability": "universal_residential",
        "source_text": "Shop-top: 1 space per 1 bed (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 1.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; former Warringah area; residential component",
        "applicability": "universal_residential",
        "source_text": "Shop-top: 1.2 spaces per 2 bed (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; former Warringah area; residential component",
        "applicability": "universal_residential",
        "source_text": "Shop-top: 1.5 spaces per 3 bed (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
    },
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; former Warringah area; residential component",
        "applicability": "universal_residential",
        "source_text": "Shop-top: 1 visitor per 5 units (Warringah DCP Appendix 1)",
        "section_ref": "appendix-1",
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
                  f"min={row.get('value_min')} unit={row['unit']} "
                  f"cond={(row.get('condition') or '')[:55]}")
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
            print(f"  INSERT: {row['dev_type']} min={row.get('value_min')} unit={row['unit']}")
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
        print(f"\nNorthern Beaches parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
