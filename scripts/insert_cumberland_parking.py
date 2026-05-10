#!/usr/bin/env python3
"""
Insert Cumberland DCP 2021 parking controls into dcp_setback_controls.

Source: Cumberland DCP 2021, Part G3 — Traffic, Parking, Transport and Access
        Table 1: Parking rates (pages G46-G47)
        OCR'd via Mistral OCR 2026-05-10.

Notes:
- Cumberland only lists rates for: dwelling_house, RFB/shop_top_housing,
  boarding_house in the residential section.
- Dual occupancy, multi_dwelling_housing, secondary_dwelling are NOT
  separately listed — they inherit from dwelling_house rate or SEPP provisions.
- RFB and shop_top_housing share the same rate schedule.

Usage:
    python scripts/insert_cumberland_parking.py --dry-run
    python scripts/insert_cumberland_parking.py
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

LGA = "cumberland"
DCP_VERSION = "v2021"
EXTRACTION_METHOD = "mistral_ocr"
SOURCE_CHAPTER_KEY = "part-g3-traffic-parking"

PARKING_ROWS = [
    # ─ Dwelling House ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": "minimum 1 covered, maximum 2 covered; stacked for same dwelling only",
        "applicability": "universal_residential",
        "source_text": "Minimum 1 covered space / dwelling house. Maximum of 2 covered spaces / dwelling house. Stacked parking may be provided only for use by the same dwelling.",
        "section_ref": "part-g3-s3-table-1",
    },
    # ─ Residential Flat Buildings (studio/1-2 bed) ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio, 1 or 2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1 space / dwelling",
        "section_ref": "part-g3-s3-table-1",
    },
    # ─ RFB (3+ bed) ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "1.5 space / dwelling",
        "section_ref": "part-g3-s3-table-1",
    },
    # ─ RFB visitor ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking",
        "applicability": "universal_residential",
        "source_text": "0.25 space / dwelling",
        "section_ref": "part-g3-s3-table-1",
    },
    # ─ Shop Top Housing (studio/1-2 bed) — same as RFB ─
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio, 1 or 2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1 space / dwelling (same rate as RFB per Table 1)",
        "section_ref": "part-g3-s3-table-1",
    },
    # ─ Shop Top Housing (3+ bed) ─
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "1.5 space / dwelling (same rate as RFB per Table 1)",
        "section_ref": "part-g3-s3-table-1",
    },
    # ─ Shop Top Housing visitor ─
    {
        "dev_type": "shop_top_housing",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking",
        "applicability": "universal_residential",
        "source_text": "0.25 space / dwelling (same rate as RFB per Table 1)",
        "section_ref": "part-g3-s3-table-1",
    },
    # ─ Boarding House ─
    {
        "dev_type": "boarding_house",
        "control_type": "car_parking",
        "value_min": 0.5,
        "value_max": None,
        "unit": "spaces/room",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "0.5 space / room",
        "section_ref": "part-g3-s3-table-1",
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
        print(f"\nCumberland parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
