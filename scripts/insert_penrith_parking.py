#!/usr/bin/env python3
"""
Insert Penrith DCP 2014 parking controls into dcp_setback_controls.

Source: Penrith DCP 2014, C10 Transport, Access and Parking
        Table C10.2: Car Parking Rates (pages 17-20)
        Current as of February 2026 amendment.
        OCR'd via Mistral OCR 2026-05-10.

Usage:
    python scripts/insert_penrith_parking.py --dry-run   # preview
    python scripts/insert_penrith_parking.py              # insert
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

LGA = "penrith"
DCP_VERSION = "v2014-amended-feb-2026"
EXTRACTION_METHOD = "mistral_ocr"
SOURCE_CHAPTER_KEY = "c10-transport-access-parking"

# ── Parking rows from Table C10.2 ───────────────────────────────
PARKING_ROWS = [
    # ─ Residential ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling - stack or tandem parking acceptable",
        "section_ref": "c10-s10.5.1-table-c10.2",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling (2 or more bedrooms) - stack or tandem parking acceptable",
        "section_ref": "c10-s10.5.1-table-c10.2",
    },
    # Multi Dwelling Housing — tiered by bedroom count
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom",
        "applicability": "universal_residential",
        "source_text": "1 car space per 1 bedroom",
        "section_ref": "c10-s10.5.1-table-c10.2",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1.5 car spaces per 2 bedrooms or part thereof",
        "section_ref": "c10-s10.5.1-table-c10.2",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 car spaces per 3 or more bedrooms",
        "section_ref": "c10-s10.5.1-table-c10.2",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; 5 or more dwellings",
        "applicability": "universal_residential",
        "source_text": "1 space for every 5 dwellings (or part thereof)",
        "section_ref": "c10-s10.5.1-table-c10.2",
    },
    # Residential Flat Buildings — tiered by bedroom count
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 or 2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1 space per 1 or 2 bedrooms",
        "section_ref": "c10-s10.5.1-table-c10.2",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 spaces per 3 or more bedrooms",
        "section_ref": "c10-s10.5.1-table-c10.2",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; 5 or more dwellings",
        "applicability": "universal_residential",
        "source_text": "1 space per every 5 dwellings, or part thereof",
        "section_ref": "c10-s10.5.1-table-c10.2",
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
        # Dedup check
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

    # Post-insert summary
    if not args.dry_run and inserted > 0:
        cur.execute("""
            SELECT dev_type, count(*) as n
            FROM dcp_setback_controls
            WHERE lga = %s AND control_type = 'car_parking' AND is_current = TRUE
            GROUP BY dev_type ORDER BY dev_type
        """, (LGA,))
        print(f"\nPenrith parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
