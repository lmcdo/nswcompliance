#!/usr/bin/env python3
"""
Insert Fairfield DCP 2024 parking controls into dcp_setback_controls.

Source: Fairfield City Wide Development Control Plan 2024
        Ch 5A.3.1 — Dwelling houses: 3 spaces (2 behind building line)
        Ch 6A.3.1 — Multi dwelling housing: 1 space/1-2 bed, 1.5-2 spaces/3+ bed
                     (rate depends on distance to railway/bus), visitor 0.25/dwelling
        Ch 6B.3.1 — Dual occupancy: 2 spaces/dwelling (3 if lot >450sqm & >11m wide)
        Ch 7.6.1  — RFB: 1 space/dwelling, visitor 1 per 4 dwellings

Usage:
    python scripts/insert_fairfield_parking.py --dry-run
    python scripts/insert_fairfield_parking.py
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

LGA = "fairfield"
DCP_VERSION = "v2024-current"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "parking-controls"

PARKING_ROWS = [
    # ── Dwelling House (Ch 5A.3.1) ──
    {"dev_type": "dwelling_house", "control_type": "car_parking", "value_min": 3, "value_max": None,
     "unit": "spaces/dwelling", "condition": "2 of 3 spaces behind building line",
     "applicability": "universal_residential",
     "source_text": "3 car spaces onsite, 2 behind building line (Ch 5A.3.1)",
     "section_ref": "ch-5a-s3.1"},
    # ── Dual Occupancy (Ch 6B.3.1) ──
    {"dev_type": "dual_occupancy", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "1 behind building line",
     "applicability": "universal_residential",
     "source_text": "2 spaces per dwelling, 1 behind building line (Ch 6B.3.1)",
     "section_ref": "ch-6b-s3.1"},
    {"dev_type": "dual_occupancy", "control_type": "car_parking", "value_min": 3, "value_max": None,
     "unit": "spaces/dwelling", "condition": "lot >450sqm and >11m wide",
     "applicability": "universal_residential",
     "source_text": "3 spaces per dwelling for lots >450sqm with 11m+ width (Ch 6B.3.1)",
     "section_ref": "ch-6b-s3.1"},
    # ── Multi Dwelling Housing (Ch 6A.3.1) ──
    # Location A: <400m from railway/major bus station
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "1-2 bedrooms or <110sqm, <400m from station",
     "applicability": "universal_residential",
     "source_text": "1 space per 1-2 bed dwelling <400m from station (Ch 6A.3.1 Location A)",
     "section_ref": "ch-6a-s3.1"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 1.5, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3+ bedrooms or >110sqm, <400m from station",
     "applicability": "universal_residential",
     "source_text": "1.5 spaces per 3+ bed dwelling <400m from station (Ch 6A.3.1 Location A)",
     "section_ref": "ch-6a-s3.1"},
    # Location B: >400m from railway/major bus station
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "1-2 bedrooms or <110sqm, >400m from station",
     "applicability": "universal_residential",
     "source_text": "1 space per 1-2 bed dwelling >400m from station (Ch 6A.3.1 Location B)",
     "section_ref": "ch-6a-s3.1"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3+ bedrooms or >110sqm, >400m from station",
     "applicability": "universal_residential",
     "source_text": "2 spaces per 3+ bed dwelling >400m from station (Ch 6A.3.1 Location B)",
     "section_ref": "ch-6a-s3.1"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 0.25, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "visitor parking",
     "applicability": "universal_residential",
     "source_text": "0.25 visitor spaces per dwelling (Ch 6A.3.1)",
     "section_ref": "ch-6a-s3.1"},
    # ── Residential Flat Building (Ch 7.6.1) ──
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": None,
     "applicability": "universal_residential",
     "source_text": "1 space per dwelling (Ch 7.6.1)",
     "section_ref": "ch-7-s6.1"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 0.25, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "visitor parking, >2 dwellings",
     "applicability": "universal_residential",
     "source_text": "1 visitor space per 4 dwellings where >2 dwellings proposed (Ch 7.6.1)",
     "section_ref": "ch-7-s6.1"},
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
            print(f"  SKIP dup: {row['dev_type']} min={row.get('value_min')} cond={row.get('condition','')[:40]}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  DRY-RUN: {row['dev_type']} min={row.get('value_min')} unit={row['unit']} cond={(row.get('condition') or '')[:50]}")
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
            inserted += 1

    if not args.dry_run:
        conn.commit()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (duplicates)")
    conn.close()


if __name__ == "__main__":
    main()
