#!/usr/bin/env python3
"""
Insert Waverley DCP 2022 parking controls into dcp_setback_controls.

Source: Waverley DCP 2022, Part B7 Transport, Table 4 Car Parking Rates
        (as amended, current version downloaded 2026-05-10).

Notes:
- Waverley uses MAXIMUM parking rates (not minimum), stored as value_max.
- Two parking zones: Zone 1 (higher accessibility) and Zone 2.
- Low density residential (dwelling houses, dual occ): max 1 (≤2bed), max 2 (≥3bed).
- Medium density (3-19 dwellings): multi dwelling housing rates.
- High density (20+ dwellings): residential flat building rates.
- Minimum for medium/high density is 0 (no minimum requirement).
- No secondary_dwelling rate listed — SEPP Housing 2021 deferral.
- Visitor parking: 7+ units = 1 per 7 (Zone 1), 5+ units = 1 per 5 (Zone 2).

Usage:
    python scripts/insert_waverley_parking.py --dry-run
    python scripts/insert_waverley_parking.py
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

LGA = "waverley"
DCP_VERSION = "v2022-current"
EXTRACTION_METHOD = "mistral_ocr"
SOURCE_CHAPTER_KEY = "part-b7-transport"

PARKING_ROWS = [
    # ─ Low Density Residential (dwelling house) ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms or less",
        "applicability": "universal_residential",
        "source_text": "Low Density Residential: ≤2 Bedrooms – Maximum 1 (both zones)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "Low Density Residential: ≥3 Bedrooms – Maximum 2 (both zones)",
        "section_ref": "table-4",
    },
    # ─ Dual Occupancy (same low density rate) ─
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms or less",
        "applicability": "universal_residential",
        "source_text": "Low Density Residential: ≤2 Bedrooms – Maximum 1 (both zones)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "Low Density Residential: ≥3 Bedrooms – Maximum 2 (both zones)",
        "section_ref": "table-4",
    },
    # ─ Multi Dwelling Housing (medium density, 3-19 dwellings) ─
    # Zone 1
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0,
        "unit": "spaces/dwelling",
        "condition": "studio; Parking Zone 1; 3-19 dwellings",
        "applicability": "universal_residential",
        "source_text": "Medium density residential: Studio Maximum 0 (Zone 1)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.4,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; Parking Zone 1; 3-19 dwellings",
        "applicability": "universal_residential",
        "source_text": "Medium density residential: 1 bedroom Maximum 0.4 (Zone 1)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.7,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; Parking Zone 1; 3-19 dwellings",
        "applicability": "universal_residential",
        "source_text": "Medium density residential: 2 bedroom Maximum 0.7 (Zone 1)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1.2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; Parking Zone 1; 3-19 dwellings",
        "applicability": "universal_residential",
        "source_text": "Medium density residential: 3 bedroom+ Maximum 1.2 (Zone 1)",
        "section_ref": "table-4",
    },
    # Zone 2
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0,
        "unit": "spaces/dwelling",
        "condition": "studio; Parking Zone 2; 3-19 dwellings",
        "applicability": "universal_residential",
        "source_text": "Medium density residential: Studio Maximum 0 (Zone 2)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1.0,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; Parking Zone 2; 3-19 dwellings",
        "applicability": "universal_residential",
        "source_text": "Medium density residential: 1 bedroom Maximum 1.0 (Zone 2)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1.2,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; Parking Zone 2; 3-19 dwellings",
        "applicability": "universal_residential",
        "source_text": "Medium density residential: 2 bedroom Maximum 1.2 (Zone 2)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1.5,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; Parking Zone 2; 3-19 dwellings",
        "applicability": "universal_residential",
        "source_text": "Medium density residential: 3 bedroom+ Maximum 1.5 (Zone 2)",
        "section_ref": "table-4",
    },
    # Visitor parking (MDH)
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.143,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; Parking Zone 1; 7+ units (3-6 units = 0)",
        "applicability": "universal_residential",
        "source_text": "7+ Units – 1 space per 7 units (Zone 1); 3-6 Units – 0 spaces",
        "section_ref": "table-4",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.2,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; Parking Zone 2; 5+ units (3-4 units = 0)",
        "applicability": "universal_residential",
        "source_text": "5+ Units – 1 space per 5 units (Zone 2); 3-4 Units – 0 spaces",
        "section_ref": "table-4",
    },
    # ─ Residential Flat Building (high density, 20+ dwellings) ─
    # Zone 1
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0,
        "unit": "spaces/dwelling",
        "condition": "studio; Parking Zone 1; 20+ dwellings",
        "applicability": "universal_residential",
        "source_text": "High density residential: Studio Maximum 0 (Zone 1)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.4,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; Parking Zone 1; 20+ dwellings",
        "applicability": "universal_residential",
        "source_text": "High density residential: 1 bedroom Maximum 0.4 (Zone 1)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.7,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; Parking Zone 1; 20+ dwellings",
        "applicability": "universal_residential",
        "source_text": "High density residential: 2 bedroom Maximum 0.7 (Zone 1)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1.2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; Parking Zone 1; 20+ dwellings",
        "applicability": "universal_residential",
        "source_text": "High density residential: 3 bedroom+ Maximum 1.2 (Zone 1)",
        "section_ref": "table-4",
    },
    # Zone 2
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0,
        "unit": "spaces/dwelling",
        "condition": "studio; Parking Zone 2; 20+ dwellings",
        "applicability": "universal_residential",
        "source_text": "High density residential: Studio Maximum 0 (Zone 2)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.6,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; Parking Zone 2; 20+ dwellings",
        "applicability": "universal_residential",
        "source_text": "High density residential: 1 bedroom Maximum 0.6 (Zone 2)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.9,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; Parking Zone 2; 20+ dwellings",
        "applicability": "universal_residential",
        "source_text": "High density residential: 2 bedroom Maximum 0.9 (Zone 2)",
        "section_ref": "table-4",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1.4,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; Parking Zone 2; 20+ dwellings",
        "applicability": "universal_residential",
        "source_text": "High density residential: 3 bedroom+ Maximum 1.4 (Zone 2)",
        "section_ref": "table-4",
    },
    # Visitor parking (RFB) - same rates as MDH
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.143,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; Parking Zone 1; 7+ units (3-6 units = 0)",
        "applicability": "universal_residential",
        "source_text": "7+ Units – 1 space per 7 units (Zone 1); 3-6 Units – 0 spaces",
        "section_ref": "table-4",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.2,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; Parking Zone 2; 5+ units (3-4 units = 0)",
        "applicability": "universal_residential",
        "source_text": "5+ Units – 1 space per 5 units (Zone 2); 3-4 Units – 0 spaces",
        "section_ref": "table-4",
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
        print(f"\nWaverley parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
