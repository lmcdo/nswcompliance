#!/usr/bin/env python3
"""
Insert City of Ryde DCP 2014 parking controls into dcp_setback_controls.

Source: City of Ryde DCP 2014, Part 9.3 — Parking Controls
        In force (current).
        Rates vary by density zone:
        - Low density (R2): dwelling house up to 2 spaces, dual occ 1 space/dwelling
        - Medium density (R3): MDH — 1 space 1-2 bed, 2 spaces 3+ bed, visitor 1:4
        - High density (R4): RFB — 0.6-1/1bed, 0.9-1.2/2bed, 1.4-1.6/3bed, visitor 1:5
        - Macquarie Park Corridor: reduced maximums — 0.6/1bed, 0.9/2bed, 1.4/3bed,
          visitor 1:10, car share 1:50

Usage:
    python scripts/insert_ryde_parking.py --dry-run
    python scripts/insert_ryde_parking.py
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

LGA = "ryde"
DCP_VERSION = "v2014-current"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "part-9.3-parking"

PARKING_ROWS = [
    # ── Dwelling House (Low Density R2) ──
    {"dev_type": "dwelling_house", "control_type": "car_parking", "value_min": 1, "value_max": 2,
     "unit": "spaces/dwelling", "condition": None,
     "applicability": "universal_residential",
     "source_text": "Up to 2 spaces per dwelling house (DCP 2014, Part 9.3, low density)",
     "section_ref": "part-9.3"},
    # ── Dual Occupancy ──
    {"dev_type": "dual_occupancy", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": None,
     "applicability": "universal_residential",
     "source_text": "1 space per dwelling for dual occupancy (DCP 2014, Part 9.3)",
     "section_ref": "part-9.3"},
    # ── Multi Dwelling Housing (Medium Density R3) ──
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "1-2 bedrooms",
     "applicability": "universal_residential",
     "source_text": "1 space per 1-2 bedroom dwelling (DCP 2014, Part 9.3, medium density)",
     "section_ref": "part-9.3"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3 or more bedrooms",
     "applicability": "universal_residential",
     "source_text": "2 spaces per 3+ bedroom dwelling (DCP 2014, Part 9.3, medium density)",
     "section_ref": "part-9.3"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 0.25, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "visitor parking",
     "applicability": "universal_residential",
     "source_text": "1 visitor space per 4 dwellings (DCP 2014, Part 9.3, medium density)",
     "section_ref": "part-9.3"},
    # ── Residential Flat Building (High Density R4) ──
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 0.6, "value_max": 1,
     "unit": "spaces/dwelling", "condition": "1 bedroom",
     "applicability": "universal_residential",
     "source_text": "0.6-1 space per 1-bedroom unit (DCP 2014, Part 9.3, high density)",
     "section_ref": "part-9.3"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 0.9, "value_max": 1.2,
     "unit": "spaces/dwelling", "condition": "2 bedrooms",
     "applicability": "universal_residential",
     "source_text": "0.9-1.2 spaces per 2-bedroom unit (DCP 2014, Part 9.3, high density)",
     "section_ref": "part-9.3"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 1.4, "value_max": 1.6,
     "unit": "spaces/dwelling", "condition": "3 or more bedrooms",
     "applicability": "universal_residential",
     "source_text": "1.4-1.6 spaces per 3+ bedroom unit (DCP 2014, Part 9.3, high density)",
     "section_ref": "part-9.3"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 0.2, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "visitor parking",
     "applicability": "universal_residential",
     "source_text": "1 visitor space per 5 dwellings (DCP 2014, Part 9.3, high density)",
     "section_ref": "part-9.3"},
    # ── Macquarie Park Corridor (special precinct — maximums) ──
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": None, "value_max": 0.6,
     "unit": "spaces/dwelling", "condition": "Macquarie Park Corridor, 1 bedroom",
     "applicability": "precinct_specific",
     "source_text": "Max 0.6 spaces per 1-bedroom unit in Macquarie Park Corridor (DCP 2014, Part 9.3)",
     "section_ref": "part-9.3"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": None, "value_max": 0.9,
     "unit": "spaces/dwelling", "condition": "Macquarie Park Corridor, 2 bedrooms",
     "applicability": "precinct_specific",
     "source_text": "Max 0.9 spaces per 2-bedroom unit in Macquarie Park Corridor (DCP 2014, Part 9.3)",
     "section_ref": "part-9.3"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": None, "value_max": 1.4,
     "unit": "spaces/dwelling", "condition": "Macquarie Park Corridor, 3 or more bedrooms",
     "applicability": "precinct_specific",
     "source_text": "Max 1.4 spaces per 3+ bedroom unit in Macquarie Park Corridor (DCP 2014, Part 9.3)",
     "section_ref": "part-9.3"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 0.1, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "Macquarie Park Corridor, visitor parking",
     "applicability": "precinct_specific",
     "source_text": "1 visitor space per 10 dwellings in Macquarie Park Corridor (DCP 2014, Part 9.3)",
     "section_ref": "part-9.3"},
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
            print(f"  DRY-RUN: {row['dev_type']} min={row.get('value_min')} max={row.get('value_max')} unit={row['unit']} cond={(row.get('condition') or '')[:50]}")
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
