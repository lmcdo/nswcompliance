#!/usr/bin/env python3
"""
Insert Liverpool landscaping controls into dcp_setback_controls.

Source: Liverpool DCP 2008, Part 8 — Dwelling Houses (300-900sqm, R1/R2/R3)
        Table 1: Minimum Landscaped Area
        As amended December 2019 (Amendment 34).

Notes:
- Landscaping varies by lot size: 25% (300-599sqm), 30% (600-899sqm).
- At least 50% must be behind building line.
- Only applies to lots 300-900sqm in R1/R2/R3 zones.

Usage:
    python scripts/insert_liverpool_landscaping.py --dry-run
    python scripts/insert_liverpool_landscaping.py
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

LGA = "liverpool"
DCP_VERSION = "v2008-amendment-34-dec2019"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "part-2-residential"

LANDSCAPING_ROWS = [
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 25,
        "value_max": None,
        "unit": "%",
        "condition": "lot area 300-599 sqm; R1/R2/R3 zones; 50% behind building line",
        "applicability": "universal_residential",
        "source_text": "Minimum 25% landscaped area for lots 300-599 sqm (Liverpool DCP Part 8 Table 1)",
        "section_ref": "part8-table1",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "lot area 600-899 sqm; R1/R2/R3 zones; 50% behind building line",
        "applicability": "universal_residential",
        "source_text": "Minimum 30% landscaped area for lots 600-899 sqm (Liverpool DCP Part 8 Table 1)",
        "section_ref": "part8-table1",
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
            print(f"  INSERT: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} unit={row['unit']}")
            inserted += 1

    if not args.dry_run:
        conn.commit()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (duplicates)")
    conn.close()


if __name__ == "__main__":
    main()
