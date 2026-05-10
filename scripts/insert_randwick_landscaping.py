#!/usr/bin/env python3
"""
Insert Randwick landscaping controls into dcp_setback_controls.

Source: Randwick Comprehensive DCP 2013, Part C1 — Low Density Residential
        As amended April 2016.

Notes:
- Dwelling houses: 40% minimum landscaped area (from compliance table).
- This is the current operative DCP; draft DCP 2023 proposes changes but
  is not yet in force.

Usage:
    python scripts/insert_randwick_landscaping.py --dry-run
    python scripts/insert_randwick_landscaping.py
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

LGA = "randwick"
DCP_VERSION = "v2013-amendment-apr2016"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "b7-transport-traffic-parking-access"  # using existing key

LANDSCAPING_ROWS = [
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum 40% of site as landscaped area (Randwick DCP 2013 Part C1)",
        "section_ref": "c1-landscaping",
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
            print(f"  SKIP dup: {row['dev_type']} {row['control_type']}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  DRY-RUN: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} unit={row['unit']}")
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
    conn.close()


if __name__ == "__main__":
    main()
