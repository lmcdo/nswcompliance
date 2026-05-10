#!/usr/bin/env python3
"""
Insert Campbelltown DCP 2015 parking controls into dcp_setback_controls.

Source: Campbelltown (Sustainable City) DCP 2015, Volume 1 Part 3
        (Low and Medium Density Residential) and Part 4 (RFB/Mixed Use).
        Updated 02/09/2024.
        OCR'd via Mistral OCR 2026-05-10.

Notes:
- Rates are scattered across dev-type sections, not a single table.
- Dwelling house: 1 undercover space (18m² for 1-2 bed, 36m² for 3+ bed).
- Dual occupancy, semi-detached, attached dwellings: 1 single garage each.
- Multi dwelling housing: 1 garage/space + 1 visitor per 3 units.
- RFB: 1 space per dwelling + 1 additional per 4 dwellings + 1 visitor per 10.
- Manor houses: 1 space per dwelling; studios <400m from station exempt.
- No secondary_dwelling rate listed — SEPP Housing 2021 deferral.
- Boarding houses defer to SEPP.

Usage:
    python scripts/insert_campbelltown_parking.py --dry-run
    python scripts/insert_campbelltown_parking.py
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

LGA = "campbelltown"
DCP_VERSION = "v2015-updated-sep2024"
EXTRACTION_METHOD = "mistral_ocr"
SOURCE_CHAPTER_KEY = "part-3-low-medium-density-residential"

PARKING_ROWS = [
    # ─ Dwelling House ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1-2 bedrooms; max undercover area 18m2",
        "applicability": "universal_residential",
        "source_text": "A dwelling house shall be provided with an undercover car parking area which is restricted to a maximum of 18m2 for 1-2 bedroom dwellings",
        "section_ref": "s3-6-1-4",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; max undercover area 36m2",
        "applicability": "universal_residential",
        "source_text": "A dwelling house shall be provided with an undercover car parking area which is restricted to a maximum of 36m2 for dwellings proposing 3 or more bedrooms",
        "section_ref": "s3-6-1-4",
    },
    # ─ Dual Occupancy ─
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Each dwelling that is part of a dual occupancy development shall be provided with a minimum of one (1) single garage",
        "section_ref": "s3-6-3-3",
    },
    # ─ Multi Dwelling Housing ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Each multi dwelling housing unit shall be provided with a minimum of one single garage or car parking space",
        "section_ref": "s3-7-2-5",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.333,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; 3 or more dwellings",
        "applicability": "universal_residential",
        "source_text": "One (1) external additional visitor car parking space shall be provided for every three (3) units (or part thereof)",
        "section_ref": "s3-7-2-5",
    },
    # ─ Residential Flat Building ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Each dwelling shall be provided with a minimum of one car parking space",
        "section_ref": "s4-3-4",
        "source_chapter_key_override": "part-4-rfb-mixed-use",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "additional space; every 4 dwellings",
        "applicability": "universal_residential",
        "source_text": "An additional car parking space for every 4 dwellings (or part thereof)",
        "section_ref": "s4-3-4",
        "source_chapter_key_override": "part-4-rfb-mixed-use",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.1,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; 10 or more dwellings",
        "applicability": "universal_residential",
        "source_text": "An additional visitor car parking space for every 10 dwellings (or part thereof)",
        "section_ref": "s4-3-4",
        "source_chapter_key_override": "part-4-rfb-mixed-use",
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
        chapter_key = row.pop("source_chapter_key_override", SOURCE_CHAPTER_KEY)

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
                  DCP_VERSION, EXTRACTION_METHOD, chapter_key))
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
        print(f"\nCampbelltown parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
