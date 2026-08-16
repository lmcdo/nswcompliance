#!/usr/bin/env python3
"""
Insert Burwood DCP parking controls into dcp_setback_controls.

Source: Burwood DCP (current, Amendment 13, effective 3 Nov 2025)
        Table 4 — Car Parking Rates in Residential Zones (pp.163-165)
        Applies to R1, R2, R3 zones.

Rates:
- Dwelling house / dual occ / secondary dwelling: 1 space per dwelling (minimum)
- Multi dwelling / RFB / shop top: 1 space per unit ≤2 bed, 2 spaces per 3+ bed unit
  Visitor: 1 space per 5 units (min AND max)
  Studio/bedsitter counted as half a unit for visitor calc.

Usage:
    python scripts/insert_burwood_parking.py --dry-run
    python scripts/insert_burwood_parking.py
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

LGA = "burwood"
DCP_VERSION = "v2013-amendment-13-nov2025"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "s4-table-4-parking"

PARKING_ROWS = [
    # ─ Dwelling House ─
    {"dev_type": "dwelling_house", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": None,
     "applicability": "universal_residential", "source_text": "1 space per dwelling (Table 4)",
     "section_ref": "table-4"},
    # ─ Dual Occupancy ─
    {"dev_type": "dual_occupancy", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": None,
     "applicability": "universal_residential", "source_text": "1 space per dwelling (Table 4)",
     "section_ref": "table-4"},
    # ─ Secondary Dwelling ─
    {"dev_type": "secondary_dwelling", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": None,
     "applicability": "secondary_dwelling_specific", "source_text": "1 space per dwelling (Table 4)",
     "section_ref": "table-4"},
    # ─ Multi Dwelling Housing ─
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "up to 2 bedrooms",
     "applicability": "universal_residential", "source_text": "1 space per unit up to 2 bedrooms (Table 4)",
     "section_ref": "table-4"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3 or more bedrooms",
     "applicability": "universal_residential", "source_text": "2 spaces per 3 or more bedroom unit (Table 4)",
     "section_ref": "table-4"},
    {"dev_type": "multi_dwelling_housing", "control_type": "car_parking", "value_min": 0.2, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "visitor parking",
     "applicability": "universal_residential", "source_text": "1 visitor space per 5 units (Table 4)",
     "section_ref": "table-4"},
    # ─ Residential Flat Building ─
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "up to 2 bedrooms",
     "applicability": "universal_residential", "source_text": "1 space per unit up to 2 bedrooms (Table 4)",
     "section_ref": "table-4"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3 or more bedrooms",
     "applicability": "universal_residential", "source_text": "2 spaces per 3 or more bedroom unit (Table 4)",
     "section_ref": "table-4"},
    {"dev_type": "residential_flat_building", "control_type": "car_parking", "value_min": 0.2, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "visitor parking",
     "applicability": "universal_residential", "source_text": "1 visitor space per 5 units (Table 4)",
     "section_ref": "table-4"},
    # ─ Shop Top Housing ─
    {"dev_type": "shop_top_housing", "control_type": "car_parking", "value_min": 1, "value_max": None,
     "unit": "spaces/dwelling", "condition": "up to 2 bedrooms",
     "applicability": "universal_residential", "source_text": "1 space per unit up to 2 bedrooms (Table 4, same as RFB)",
     "section_ref": "table-4"},
    {"dev_type": "shop_top_housing", "control_type": "car_parking", "value_min": 2, "value_max": None,
     "unit": "spaces/dwelling", "condition": "3 or more bedrooms",
     "applicability": "universal_residential", "source_text": "2 spaces per 3 or more bedroom unit (Table 4, same as RFB)",
     "section_ref": "table-4"},
    {"dev_type": "shop_top_housing", "control_type": "car_parking", "value_min": 0.2, "value_max": None,
     "unit": "visitor_spaces/dwelling", "condition": "visitor parking",
     "applicability": "universal_residential", "source_text": "1 visitor space per 5 units (Table 4, same as RFB)",
     "section_ref": "table-4"},
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
