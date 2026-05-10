#!/usr/bin/env python3
"""
Insert Randwick DCP 2013 parking controls into dcp_setback_controls.

Source: Randwick DCP 2013, Section B7 Transport, Traffic, Parking and Access
        Table 1: Vehicle Parking Rates (pages 174-177 of consolidated PDF)
        Amendment adopted 12 Apr 2016.
        OCR'd via Mistral OCR 2026-05-10 from NSW Planning Portal S3 mirror.

Notes:
- Dwelling houses/dual occupancies/semi-detached/attached dwellings share
  the same rate row in the DCP table.
- Multi dwelling housing and residential flat buildings share the same rate
  row (1 space per 2 studios, 1 per 1-bed, 1.2 per 2-bed, 1.5 per 3+bed,
  1 visitor per 4 dwellings).
- Boarding houses defer to SEPP (Affordable Rental Housing SEPP / Housing 2021).
- Seniors housing defers to SEPP (Housing for Seniors or People with a Disability).
- No secondary_dwelling rate listed — SEPP Housing 2021 deferral.

Usage:
    python scripts/insert_randwick_parking.py --dry-run
    python scripts/insert_randwick_parking.py
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

LGA = "randwick"
DCP_VERSION = "v2013-amendment-apr2016"
EXTRACTION_METHOD = "mistral_ocr"
SOURCE_CHAPTER_KEY = "b7-transport-traffic-parking-access"

PARKING_ROWS = [
    # ─ Dwelling House ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "up to 2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1 space per dwelling house with up to 2 bedrooms",
        "section_ref": "b7-table-1",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling house with 3 or more bedrooms",
        "section_ref": "b7-table-1",
    },
    # ─ Dual Occupancy (same rate as dwelling house per table) ─
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "up to 2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1 space per dwelling with up to 2 bedrooms (dwelling houses/dual occupancies row)",
        "section_ref": "b7-table-1",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling with 3 or more bedrooms (dwelling houses/dual occupancies row)",
        "section_ref": "b7-table-1",
    },
    # ─ Multi Dwelling Housing ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio",
        "applicability": "universal_residential",
        "source_text": "1 space per 2 studio",
        "section_ref": "b7-table-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom",
        "applicability": "universal_residential",
        "source_text": "1 space per 1 bedroom apartments (over 40 m2)",
        "section_ref": "b7-table-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1.2 spaces per 2 bedroom apartments",
        "section_ref": "b7-table-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "1.5 spaces per 3 or more bedroom apartments",
        "section_ref": "b7-table-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; 4 or more dwellings",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 4 dwellings (but none where development is less than 4 dwellings)",
        "section_ref": "b7-table-1",
    },
    # ─ Residential Flat Building (same rate as MDH per table) ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio",
        "applicability": "universal_residential",
        "source_text": "1 space per 2 studio (multi dwelling housing and residential flat buildings row)",
        "section_ref": "b7-table-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom",
        "applicability": "universal_residential",
        "source_text": "1 space per 1 bedroom apartments (over 40 m2)",
        "section_ref": "b7-table-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1.2 spaces per 2 bedroom apartments",
        "section_ref": "b7-table-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "1.5 spaces per 3 or more bedroom apartments",
        "section_ref": "b7-table-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; 4 or more dwellings",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 4 dwellings (but none where development is less than 4 dwellings)",
        "section_ref": "b7-table-1",
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
        print(f"\nRandwick parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
