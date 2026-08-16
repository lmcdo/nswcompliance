#!/usr/bin/env python3
"""
Insert The Hills Shire DCP 2012 parking controls into dcp_setback_controls.

Source: The Hills DCP 2012, Part C Section 1 — Parking
        In force 19 August 2024.
        Residential rates from parking table:
        - 1 bedroom: 1 space
        - 2, 3, or 4 bedrooms: 2 spaces
        - Visitor: 2 spaces per 5 dwellings (rounded up to next whole number)

Note: Part C Section 1 applies to all residential development types
      (dwelling house, dual occupancy, multi dwelling housing, RFB).
      The DCP states "car parking shall be provided on-site in accordance
      with the requirements contained within Part C Section 1 – Parking."

Usage:
    python scripts/insert_hills_shire_parking.py --dry-run
    python scripts/insert_hills_shire_parking.py
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

LGA = "the_hills_shire"
DCP_VERSION = "v2012-aug2024"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "part-c-s1-parking"

# All dev types share the same rate structure per Part C Section 1
DEV_TYPES = [
    ("dwelling_house", "universal_residential"),
    ("dual_occupancy", "universal_residential"),
    ("multi_dwelling_housing", "universal_residential"),
    ("residential_flat_building", "universal_residential"),
]

PARKING_ROWS = []
for dev_type, applicability in DEV_TYPES:
    PARKING_ROWS.extend([
        {"dev_type": dev_type, "control_type": "car_parking", "value_min": 1, "value_max": None,
         "unit": "spaces/dwelling", "condition": "1 bedroom",
         "applicability": applicability,
         "source_text": "1 space per 1-bedroom dwelling (Part C s1 parking table)",
         "section_ref": "part-c-s1"},
        {"dev_type": dev_type, "control_type": "car_parking", "value_min": 2, "value_max": None,
         "unit": "spaces/dwelling", "condition": "2-4 bedrooms",
         "applicability": applicability,
         "source_text": "2 spaces per dwelling with 2, 3, or 4 bedrooms (Part C s1 parking table)",
         "section_ref": "part-c-s1"},
    ])
    # Visitor parking only for multi-dwelling and RFB
    if dev_type in ("multi_dwelling_housing", "residential_flat_building"):
        PARKING_ROWS.append(
            {"dev_type": dev_type, "control_type": "car_parking", "value_min": 0.4, "value_max": None,
             "unit": "visitor_spaces/dwelling", "condition": "visitor parking",
             "applicability": applicability,
             "source_text": "2 visitor spaces per 5 dwellings, rounded up (Part C s1 parking table)",
             "section_ref": "part-c-s1"},
        )


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
