#!/usr/bin/env python3
"""
Insert Hornsby DCP 2024 parking controls into dcp_setback_controls.

Source: Hornsby DCP 2024, Part 1C — Car Parking
        Table 1C.2.1(d): On Site Car Parking Rates
        PDF: hdcp-part-1-final-23-june-2025.pdf (539 pages)
        OCR'd via Mistral OCR 2026-05-10 from NSW Planning Portal S3 mirror.

Notes:
- Hornsby has TOD-differentiated rates: sites <800m vs >800m from
  railway station. Low-density types (dwelling_house, secondary_dwelling,
  dual_occupancy) have identical rates in both columns.
- Medium density = multi_dwelling_housing; High density = residential_flat_building.
- High density <800m uses MAXIMUM rates (capping parking near stations).
- Secondary dwelling rates are explicitly listed (no SEPP deferral).

Usage:
    python scripts/insert_hornsby_parking.py --dry-run
    python scripts/insert_hornsby_parking.py
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

LGA = "hornsby"
DCP_VERSION = "v2024-jun2025"
EXTRACTION_METHOD = "mistral_ocr"
SOURCE_CHAPTER_KEY = "part-1-general"

PARKING_ROWS = [
    # ═══════════════════════════════════════════════════════════════
    # Dwelling House — same rate both TOD columns
    # ═══════════════════════════════════════════════════════════════
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "0-2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1 space per dwelling (0-2 bedrooms)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling (3 or more bedrooms)",
        "section_ref": "table-1c-2-1-d",
    },
    # ═══════════════════════════════════════════════════════════════
    # Secondary Dwelling — same rate both TOD columns
    # ═══════════════════════════════════════════════════════════════
    {
        "dev_type": "secondary_dwelling",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "0-2 bedrooms",
        "applicability": "secondary_dwelling_specific",
        "source_text": "1 space per dwelling (0-2 bedrooms)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "secondary_dwelling",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "secondary_dwelling_specific",
        "source_text": "2 spaces per dwelling (3 or more bedrooms)",
        "section_ref": "table-1c-2-1-d",
    },
    # ═══════════════════════════════════════════════════════════════
    # Attached Dual Occupancy — same rate both TOD columns
    # ═══════════════════════════════════════════════════════════════
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "0-2 bedrooms",
        "applicability": "universal_residential",
        "source_text": "1 space per dwelling (0-2 bedrooms)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms",
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling (3 or more bedrooms)",
        "section_ref": "table-1c-2-1-d",
    },
    # ═══════════════════════════════════════════════════════════════
    # Medium Density (multi_dwelling_housing) — <800m from station
    # ═══════════════════════════════════════════════════════════════
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.75,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "0-1 bedrooms; site <800m from railway station",
        "applicability": "universal_residential",
        "source_text": "0.75 spaces per dwelling (0-1 bed, sites <800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; site <800m from railway station",
        "applicability": "universal_residential",
        "source_text": "1 space per dwelling (2 bed, sites <800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; site <800m from railway station",
        "applicability": "universal_residential",
        "source_text": "1.5 spaces per dwelling (3+ bed, sites <800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.143,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; site <800m from railway station",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 7 dwellings (sites <800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    # ═══════════════════════════════════════════════════════════════
    # Medium Density (multi_dwelling_housing) — >800m from station
    # ═══════════════════════════════════════════════════════════════
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "0-1 bedrooms; site >800m from railway station",
        "applicability": "universal_residential",
        "source_text": "1 space per dwelling (0-1 bed, sites >800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.25,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; site >800m from railway station",
        "applicability": "universal_residential",
        "source_text": "1.25 spaces per dwelling (2 bed, sites >800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; site >800m from railway station",
        "applicability": "universal_residential",
        "source_text": "2 spaces per dwelling (3+ bed, sites >800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; site >800m from railway station",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 5 dwellings (sites >800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    # ═══════════════════════════════════════════════════════════════
    # High Density (residential_flat_building) — <800m from station
    # NOTE: These are MAXIMUM rates (capping parking near stations)
    # ═══════════════════════════════════════════════════════════════
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.4,
        "unit": "spaces/dwelling",
        "condition": "studio; site <800m from railway station",
        "applicability": "universal_residential",
        "source_text": "Maximum 0.4 spaces per studio (sites <800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.4,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; site <800m from railway station",
        "applicability": "universal_residential",
        "source_text": "Maximum 0.4 spaces per 1-bed dwelling (sites <800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 0.7,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; site <800m from railway station",
        "applicability": "universal_residential",
        "source_text": "Maximum 0.7 spaces per 2-bed dwelling (sites <800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": None,
        "value_max": 1.2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; site <800m from railway station",
        "applicability": "universal_residential",
        "source_text": "Maximum 1.2 spaces per 3+ bed dwelling (sites <800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.143,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; site <800m from railway station",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 7 dwellings (sites <800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    # ═══════════════════════════════════════════════════════════════
    # High Density (residential_flat_building) — >800m from station
    # ═══════════════════════════════════════════════════════════════
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; site >800m from railway station",
        "applicability": "universal_residential",
        "source_text": "1 space per 1-bed dwelling (sites >800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.25,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; site >800m from railway station",
        "applicability": "universal_residential",
        "source_text": "1.25 spaces per 2-bed dwelling (sites >800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; site >800m from railway station",
        "applicability": "universal_residential",
        "source_text": "2 spaces per 3+ bed dwelling (sites >800m from railway station)",
        "section_ref": "table-1c-2-1-d",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.2,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; site >800m from railway station",
        "applicability": "universal_residential",
        "source_text": "1 visitor space per 5 dwellings (sites >800m from railway station)",
        "section_ref": "table-1c-2-1-d",
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
                  f"min={row.get('value_min')} max={row.get('value_max')} "
                  f"cond={(row.get('condition') or '')[:50]}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  DRY-RUN: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} max={row.get('value_max')} "
                  f"unit={row['unit']} cond={(row.get('condition') or '')[:55]}")
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
            print(f"  INSERT: {row['dev_type']} "
                  f"min={row.get('value_min')} max={row.get('value_max')} "
                  f"unit={row['unit']}")
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
        print(f"\nHornsby parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
