#!/usr/bin/env python3
"""
Insert Camden DCP 2019 parking controls into dcp_setback_controls.

Source: Camden DCP 2019, Part 2 Section 2.18.2, Table 2-5
        Sections 4.2.7, 4.3, 4.4, 4.6 (Table 4-7), 4.8 (Table 4-9)

Usage:
    python scripts/insert_camden_parking.py --dry-run
    python scripts/insert_camden_parking.py
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

LGA = "camden"
DCP_VERSION = "v2019"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "s2-18-2-parking"

PARKING_ROWS = [
    # ─ Dwelling House ─
    {"dev_type": "dwelling_house", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "1-2 bedrooms",
     "applicability": "universal_residential", "source_text": "1 space per dwelling with 1-2 bedrooms",
     "section_ref": "s4.2.7-table-2-5"},
    {"dev_type": "dwelling_house", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3 or more bedrooms",
     "applicability": "universal_residential", "source_text": "2 spaces per dwelling with 3+ bedrooms",
     "section_ref": "s4.2.7-table-2-5"},
    # ─ Dual Occupancy ─
    {"dev_type": "dual_occupancy", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "1-2 bedrooms",
     "applicability": "universal_residential", "source_text": "1 space per dwelling with 1-2 bedrooms",
     "section_ref": "s4.3-table-2-5"},
    {"dev_type": "dual_occupancy", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3 or more bedrooms",
     "applicability": "universal_residential", "source_text": "2 spaces per dwelling with 3+ bedrooms",
     "section_ref": "s4.3-table-2-5"},
    # ─ Multi Dwelling Housing ─
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "1 bedroom",
     "applicability": "universal_residential", "source_text": "1 space per 1-bedroom dwelling",
     "section_ref": "s4.6-table-4-7"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 1.2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "2 bedrooms",
     "applicability": "universal_residential", "source_text": "1.2 spaces per 2-bedroom dwelling",
     "section_ref": "s4.6-table-4-7"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 1.5, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3 or more bedrooms",
     "applicability": "universal_residential", "source_text": "1.5 spaces per 3+ bedroom dwelling",
     "section_ref": "s4.6-table-4-7"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 0.2, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "visitor parking",
     "applicability": "universal_residential", "source_text": "1 visitor space per 5 dwellings",
     "section_ref": "s4.6-table-4-7"},
    # ─ Residential Flat Building ─
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "1 bedroom",
     "applicability": "universal_residential", "source_text": "1 space per 1-bedroom unit",
     "section_ref": "s4.8-table-4-9"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 1.2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "2 bedrooms",
     "applicability": "universal_residential", "source_text": "1.2 spaces per 2-bedroom unit",
     "section_ref": "s4.8-table-4-9"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 1.5, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3 or more bedrooms",
     "applicability": "universal_residential", "source_text": "1.5 spaces per 3+ bedroom unit",
     "section_ref": "s4.8-table-4-9"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 0.2, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "visitor parking",
     "applicability": "universal_residential", "source_text": "1 visitor space per 5 units",
     "section_ref": "s4.8-table-4-9"},
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
            print(f"  DRY-RUN: {row['dev_type']} min={row.get('value_min')} unit={row['unit']} cond={row.get('condition','')[:50]}")
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
