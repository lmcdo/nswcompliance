#!/usr/bin/env python3
"""
Insert Liverpool DCP 2008 parking controls into dcp_setback_controls.

Source: Liverpool DCP 2008, Part 1 — Car Parking & Access
        Table 13: Car Parking, Servicing and Loading Provision (pages 84-88)
        Amendment 34 (Dec 2019).
        OCR'd via Mistral OCR 2026-05-10 from NSW Planning Portal S3 mirror.

Notes:
- Dwelling houses: flat 2 spaces (no bedroom differentiation).
- Multi dwelling housing & RFB share the same rate row in Table 13.
- Rates differentiated by dwelling size (m²) OR bedroom count.
- No secondary_dwelling rate listed — SEPP Housing 2021 deferral.
- Boarding houses: 1 per 2 bedrooms or 1 per 3 beds (whichever greater).

Usage:
    python scripts/insert_liverpool_parking.py --dry-run
    python scripts/insert_liverpool_parking.py
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

LGA = "liverpool"
DCP_VERSION = "v2008-amendment-34-dec2019"
EXTRACTION_METHOD = "mistral_ocr"
SOURCE_CHAPTER_KEY = "part-1-car-parking-access"

PARKING_ROWS = [
    # ─ Dwelling House ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "2 spaces",
        "section_ref": "table-13",
    },
    # ─ Multi Dwelling Housing ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "small dwelling (<65m2) or 1 bedroom",
        "applicability": "universal_residential",
        "source_text": "1 space per small dwelling (<65sqm) or 1 bedroom",
        "section_ref": "table-13",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "medium dwelling (65-110m2) or 2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1.5 spaces per medium dwelling (65-110sqm) or 2 bedrooms",
        "section_ref": "table-13",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "large dwelling (>110m2) or 3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 spaces per large dwelling (>110sqm) or 3 or more bedrooms",
        "section_ref": "table-13",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking",
        "applicability": "universal_residential",
        "source_text": "1 visitor car space for every 4 dwellings or part thereof",
        "section_ref": "table-13",
    },
    # ─ Residential Flat Building (same rate as MDH per Table 13) ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "small dwelling (<65m2) or 1 bedroom",
        "applicability": "universal_residential",
        "source_text": "1 space per small dwelling (<65sqm) or 1 bedroom (multi dwelling housing and residential flat buildings row)",
        "section_ref": "table-13",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "medium dwelling (65-110m2) or 2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1.5 spaces per medium dwelling (65-110sqm) or 2 bedrooms",
        "section_ref": "table-13",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "large dwelling (>110m2) or 3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 spaces per large dwelling (>110sqm) or 3 or more bedrooms",
        "section_ref": "table-13",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking",
        "applicability": "universal_residential",
        "source_text": "1 visitor car space for every 4 dwellings or part thereof",
        "section_ref": "table-13",
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
        print(f"\nLiverpool parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
