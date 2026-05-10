#!/usr/bin/env python3
"""
Insert Hornsby landscaping controls into dcp_setback_controls.

Source: Hornsby DCP 2013, Part 1C.3 — Landscaping
        Table 3.1.3-a: Minimum landscaped area by lot size
        As current.

Notes:
- Landscaped area requirements vary by lot size (6 bands).
- Deep soil requirements expressed as setback-based (not percentage) —
  not extracted here (would need a different unit).
- 50% of front setback must be deep soil landscaping — extracted as
  a separate deep_soil_min row with condition.

Usage:
    python scripts/insert_hornsby_landscaping.py --dry-run
    python scripts/insert_hornsby_landscaping.py
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
DCP_VERSION = "v2013-current"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "hornsby-dcp-2024-part3-residential"

LANDSCAPING_ROWS = [
    # ── Landscaped area by lot size (Table 3.1.3-a) ──
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 10,
        "value_max": None,
        "unit": "%",
        "condition": "lot area 200-299 sqm",
        "applicability": "universal_residential",
        "source_text": "Minimum 10% landscaped area for lots 200-299 sqm (Hornsby DCP Table 3.1.3-a)",
        "section_ref": "1c3",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 15,
        "value_max": None,
        "unit": "%",
        "condition": "lot area 300-449 sqm",
        "applicability": "universal_residential",
        "source_text": "Minimum 15% landscaped area for lots 300-449 sqm (Hornsby DCP Table 3.1.3-a)",
        "section_ref": "1c3",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 20,
        "value_max": None,
        "unit": "%",
        "condition": "lot area 450-599 sqm",
        "applicability": "universal_residential",
        "source_text": "Minimum 20% landscaped area for lots 450-599 sqm (Hornsby DCP Table 3.1.3-a)",
        "section_ref": "1c3",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "lot area 600-899 sqm",
        "applicability": "universal_residential",
        "source_text": "Minimum 30% landscaped area for lots 600-899 sqm (Hornsby DCP Table 3.1.3-a)",
        "section_ref": "1c3",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "lot area 900-1499 sqm",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% landscaped area for lots 900-1499 sqm (Hornsby DCP Table 3.1.3-a)",
        "section_ref": "1c3",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 45,
        "value_max": None,
        "unit": "%",
        "condition": "lot area 1500+ sqm",
        "applicability": "universal_residential",
        "source_text": "Minimum 45% landscaped area for lots 1500+ sqm (Hornsby DCP Table 3.1.3-a)",
        "section_ref": "1c3",
    },
    # ── Front setback deep soil ──
    {
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "front setback area only",
        "applicability": "universal_residential",
        "source_text": "50% of front setback must be deep soil landscaping (Hornsby DCP 1C.3)",
        "section_ref": "1c3",
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
