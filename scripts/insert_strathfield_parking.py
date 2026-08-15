#!/usr/bin/env python3
"""
Insert Strathfield DCP 2005 parking controls into dcp_setback_controls.

Source: Strathfield Consolidated DCP 2005 (as amended 28 Jul 2015)
        Part A s11.3.2 — Dwelling houses: 2 spaces (1 for lots <15m wide)
        Part B s7.0 — Dual occupancy: 1 space per dwelling ≤150sqm GFA,
                       2 spaces per dwelling >150sqm GFA
        Part C s2.4 — Multiple-unit housing:
                       1 bed = 1 space, 2 bed = 1.5 spaces, 3+ bed = 2 spaces
                       Visitor: 1 space per 5 dwellings

Usage:
    python scripts/insert_strathfield_parking.py --dry-run
    python scripts/insert_strathfield_parking.py
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

LGA = "strathfield"
DCP_VERSION = "v2005-amended-jul2015"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "parking-controls"

PARKING_ROWS = [
    # ─ Dwelling House (Part A s11.3.2) ─
    {"dev_type": "dwelling_house", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": None,
     "applicability": "universal_residential",
     "source_text": "2 car parking spaces behind front building line for all new dwellings (Part A s11.3.2)",
     "section_ref": "part-a-s11.3.2"},
    # ─ Dual Occupancy (Part B s7.0) ─
    {"dev_type": "dual_occupancy", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "GFA 150sqm or less",
     "applicability": "universal_residential",
     "source_text": "1 space per dwelling with GFA 150sqm or less (Part B s7.0)",
     "section_ref": "part-b-s7.0"},
    {"dev_type": "dual_occupancy", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "GFA exceeding 150sqm",
     "applicability": "universal_residential",
     "source_text": "2 spaces per dwelling with GFA exceeding 150sqm (Part B s7.0)",
     "section_ref": "part-b-s7.0"},
    # ─ Multi Dwelling Housing (Part C s2.4) ─
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "1 bedroom",
     "applicability": "universal_residential",
     "source_text": "1 space per 1-bedroom dwelling (Part C s2.4)",
     "section_ref": "part-c-s2.4"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 1.5, "value_max": None,
     "unit": "spaces/dwelling", "condition": "2 bedrooms",
     "applicability": "universal_residential",
     "source_text": "1.5 spaces per 2-bedroom dwelling (Part C s2.4)",
     "section_ref": "part-c-s2.4"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3 or more bedrooms",
     "applicability": "universal_residential",
     "source_text": "2 spaces per 3+ bedroom dwelling (Part C s2.4)",
     "section_ref": "part-c-s2.4"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 0.2, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "visitor parking",
     "applicability": "universal_residential",
     "source_text": "1 visitor space per 5 dwellings (Part C s2.4)",
     "section_ref": "part-c-s2.4"},
    # ─ Residential Flat Building (Part C s2.4 — same rates as multi dwelling) ─
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "1 bedroom",
     "applicability": "universal_residential",
     "source_text": "1 space per 1-bedroom unit (Part C s2.4)",
     "section_ref": "part-c-s2.4"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 1.5, "value_max": None,
     "unit": "spaces/dwelling", "condition": "2 bedrooms",
     "applicability": "universal_residential",
     "source_text": "1.5 spaces per 2-bedroom unit (Part C s2.4)",
     "section_ref": "part-c-s2.4"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3 or more bedrooms",
     "applicability": "universal_residential",
     "source_text": "2 spaces per 3+ bedroom unit (Part C s2.4)",
     "section_ref": "part-c-s2.4"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 0.2, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "visitor parking",
     "applicability": "universal_residential",
     "source_text": "1 visitor space per 5 dwellings (Part C s2.4)",
     "section_ref": "part-c-s2.4"},
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
