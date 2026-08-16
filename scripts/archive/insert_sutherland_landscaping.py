#!/usr/bin/env python3
"""
Insert Sutherland Shire DCP 2015 landscaping controls into dcp_setback_controls.

Source: Sutherland Shire DCP 2015 (Amendment 6, 2021)

Note: The primary landscaped area minimum (45% of site) is in the LEP 2015
      clause 6.14, NOT the DCP. That LEP control is delivered via the
      Planning Portal API and is not inserted here.

      The DCP adds front setback landscaping requirements:
      - At least 50% of area forward of building line must be landscaped

Usage:
    python scripts/insert_sutherland_landscaping.py --dry-run
    python scripts/insert_sutherland_landscaping.py
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

LGA = "sutherland_shire"
DCP_VERSION = "v2015-am6"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "landscaping-controls"

LANDSCAPING_ROWS = [
    # ── Dwelling House ──
    {
        "dev_type": "dwelling_house",
        "control_type": "front_setback_landscaping",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "of area forward of building line",
        "applicability": "universal_residential",
        "source_text": "At least 50% of the area forward of the building line must be landscaped area (DCP 2015)",
        "section_ref": "dcp-2015-landscaping",
    },
    # ── Dual Occupancy ──
    {
        "dev_type": "dual_occupancy",
        "control_type": "front_setback_landscaping",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "of area forward of building line",
        "applicability": "universal_residential",
        "source_text": "At least 50% of the area forward of the building line must be landscaped area (DCP 2015)",
        "section_ref": "dcp-2015-landscaping",
    },
    # ── Multi Dwelling Housing ──
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "front_setback_landscaping",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "of area forward of building line",
        "applicability": "universal_residential",
        "source_text": "At least 50% of the area forward of the building line must be landscaped area (DCP 2015)",
        "section_ref": "dcp-2015-landscaping",
    },
    # ── Residential Flat Building ──
    {
        "dev_type": "residential_flat_building",
        "control_type": "front_setback_landscaping",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "of area forward of building line",
        "applicability": "universal_residential",
        "source_text": "At least 50% of the area forward of the building line must be landscaped area (DCP 2015)",
        "section_ref": "dcp-2015-landscaping",
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

    for row in LANDSCAPING_ROWS:
        cur.execute("""
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s AND dev_type = %s AND control_type = %s
              AND COALESCE(condition, '') = COALESCE(%s, '')
              AND is_current = TRUE
        """, (LGA, row["dev_type"], row["control_type"],
              row.get("condition")))
        if cur.fetchone():
            print(f"  SKIP dup: {row['dev_type']} {row['control_type']} "
                  f"cond={(row.get('condition') or '')[:50]}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  DRY-RUN: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} max={row.get('value_max')} unit={row['unit']}")
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
                  f"min={row.get('value_min')} max={row.get('value_max')} unit={row['unit']}")
            inserted += 1

    if not args.dry_run:
        conn.commit()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (duplicates)")
    conn.close()


if __name__ == "__main__":
    main()
