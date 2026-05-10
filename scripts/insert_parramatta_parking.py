#!/usr/bin/env python3
"""
Insert Parramatta DCP 2023 parking controls into dcp_setback_controls.

Source: Parramatta DCP 2023, Part 6, Table 6.2.1 Minimum car parking rates
        (downloaded from cityofparramatta.nsw.gov.au, 2026-05-10).

Notes:
- Two regimes based on transit proximity:
  1. NOT within 800m of train/light rail or 400m of transitway bus stop
  2. Within 800m of train/light rail or 400m of transitway bus stop
- Dwelling houses/dual occ: same rate regardless of transit proximity.
- Secondary dwellings: no additional parking required.
- Transit-proximate RFB/MDH/mixed use has lower rates and no studio rate listed.
- Boarding houses deferred to SEPP Housing 2021.

Usage:
    python scripts/insert_parramatta_parking.py --dry-run
    python scripts/insert_parramatta_parking.py
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

LGA = "parramatta"
DCP_VERSION = "v2023-current"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "part-6-traffic-and-transport"

PARKING_ROWS = [
    # ─ Dwelling House ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 or 2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "Dwelling houses: minimum 1 space per dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "Dwelling houses: 2 spaces per dwelling with 3 or more bedrooms (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },

    # ─ Dual Occupancy ─
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 or 2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "Dual occupancies: minimum 1 space per dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "Dual occupancies: 2 spaces per dwelling with 3 or more bedrooms (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },

    # ─ Secondary Dwelling ─
    {
        "dev_type": "secondary_dwelling",
        "control_type": "car_parking",
        "value_min": 0,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "no additional parking required",
        "applicability": "secondary_dwelling_specific",
        "source_text": "Secondary dwellings: no additional parking is required (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },

    # ═══════════════════════════════════════════════════════════════
    # NOT within 800m train/light rail or 400m transitway bus
    # ═══════════════════════════════════════════════════════════════

    # ─ RFB / MDH / Mixed Use — non-transit-proximate ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.6,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "RFB non-transit: studio 0.6 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "RFB non-transit: 1 bed 1 space/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.25,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "RFB non-transit: 2 bed 1.25 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 bedrooms; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "RFB non-transit: 3 bed 1.5 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "4 or more bedrooms; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "RFB non-transit: 4 bed 2 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "RFB non-transit: visitor 0.25 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },

    # ─ MDH — non-transit-proximate (same rates as RFB) ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.6,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "MDH non-transit: studio 0.6 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "MDH non-transit: 1 bed 1 space/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.25,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "MDH non-transit: 2 bed 1.25 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 bedrooms; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "MDH non-transit: 3 bed 1.5 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "4 or more bedrooms; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "MDH non-transit: 4 bed 2 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; not within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "MDH non-transit: visitor 0.25 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },

    # ═══════════════════════════════════════════════════════════════
    # WITHIN 800m train/light rail or 400m transitway bus
    # ═══════════════════════════════════════════════════════════════

    # ─ RFB — transit-proximate ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.6,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "RFB transit-proximate: 1 bed 0.6 spaces/unit (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.9,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "RFB transit-proximate: 2 bed 0.9 spaces/unit (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.4,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "RFB transit-proximate: 3 bed 1.4 spaces/unit (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "RFB transit-proximate: visitor 0.2 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },

    # ─ MDH — transit-proximate (same rates as RFB) ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.6,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "MDH transit-proximate: 1 bed 0.6 spaces/unit (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.9,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "MDH transit-proximate: 2 bed 0.9 spaces/unit (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.4,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "MDH transit-proximate: 3 bed 1.4 spaces/unit (Table 6.2.1)",
        "section_ref": "table-6.2.1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; within 800m train station or 400m transitway",
        "applicability": "universal_residential",
        "source_text": "MDH transit-proximate: visitor 0.2 spaces/dwelling (Table 6.2.1)",
        "section_ref": "table-6.2.1",
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
                  DCP_VERSION, EXTRACTION_METHOD, SOURCE_CHAPTER_KEY))
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
        print(f"\nParramatta parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
