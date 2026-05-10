#!/usr/bin/env python3
"""
Insert Woollahra DCP 2015 parking controls into dcp_setback_controls.

Source: Woollahra DCP 2015, Chapter E1 Parking and Access, Table 1
        (as amended, May 2024 version).

Notes:
- Woollahra uses MAXIMUM parking rates (not minimum), stored as value_max.
- Low density residential (dwelling house, dual occ, semi-detached): max 2 spaces.
- RFB/MDH/manor house: max per bedroom count (studio=0.5, 1bd=1, 2bd=1.5, 3+bd=2).
- Mixed use residential: lower rates (1bd/studio=0.5, 2bd=1, 3+bd=1.5).
- Visitor: 0.25 spaces per dwelling (standalone), 0.2 for mixed use.
- No secondary_dwelling rate listed — SEPP Housing 2021 deferral.

Usage:
    python scripts/insert_woollahra_parking.py --dry-run
    python scripts/insert_woollahra_parking.py
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

LGA = "woollahra"
DCP_VERSION = "v2015-amended-may2024"
EXTRACTION_METHOD = "mistral_ocr"
SOURCE_CHAPTER_KEY = "chapter-e1-parking-and-access"

PARKING_ROWS = [
    # ─ Dwelling House (max 2 spaces) ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Dwelling house: 2 spaces (maximum)",
        "section_ref": "table-1",
    },
    # ─ Dual Occupancy (max 2 per dwelling) ─
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Dual occupancy: 2 spaces per dwelling (maximum)",
        "section_ref": "table-1",
    },
    # ─ Multi Dwelling Housing ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.5,
        "unit": "spaces/dwelling",
        "condition": "studio apartment",
        "applicability": "universal_residential",
        "source_text": "Studio apartment: 0.5 space (maximum)",
        "section_ref": "table-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom",
        "applicability": "universal_residential",
        "source_text": "1 bedroom: 1 space (maximum)",
        "section_ref": "table-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1.5,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 bedrooms: 1.5 spaces (maximum)",
        "section_ref": "table-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "3 or more bedrooms: 2 spaces (maximum)",
        "section_ref": "table-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.25,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking",
        "applicability": "universal_residential",
        "source_text": "Visitors: 0.25 spaces (maximum)",
        "section_ref": "table-1",
    },
    # ─ Residential Flat Building (same rates as MDH per Table 1) ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.5,
        "unit": "spaces/dwelling",
        "condition": "studio apartment",
        "applicability": "universal_residential",
        "source_text": "Studio apartment: 0.5 space (maximum) — RFB/MDH/manor house row",
        "section_ref": "table-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom",
        "applicability": "universal_residential",
        "source_text": "1 bedroom: 1 space (maximum)",
        "section_ref": "table-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1.5,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 bedrooms: 1.5 spaces (maximum)",
        "section_ref": "table-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "3 or more bedrooms: 2 spaces (maximum)",
        "section_ref": "table-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.25,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking",
        "applicability": "universal_residential",
        "source_text": "Visitors: 0.25 spaces (maximum)",
        "section_ref": "table-1",
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
              AND COALESCE(value_max::text, '') = COALESCE(%s::text, '')
              AND is_current = TRUE
        """, (LGA, row["dev_type"], row["control_type"],
              row.get("condition"), row.get("value_max")))
        if cur.fetchone():
            print(f"  SKIP dup: {row['dev_type']} "
                  f"max={row.get('value_max')} cond={(row.get('condition') or '')[:50]}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  DRY-RUN: {row['dev_type']} {row['control_type']} "
                  f"max={row.get('value_max')} unit={row['unit']} "
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
            print(f"  INSERT: {row['dev_type']} max={row.get('value_max')} unit={row['unit']}")
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
        print(f"\nWoollahra parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
