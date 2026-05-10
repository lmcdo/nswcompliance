#!/usr/bin/env python3
"""
Insert Canterbury-Bankstown landscaping controls into dcp_setback_controls.

Source: Canterbury-Bankstown DCP 2023, Chapter 5.1 (Former Bankstown LGA)
        Tables C1.1 and C1.2 — Site Coverage and Deep Soil Areas
        As amended August 2025.

Notes:
- Former Bankstown LGA has explicit site coverage maximums and deep soil minimums
  by lot size band.
- Former Canterbury LGA has front setback landscaping (45%) but no overall site
  landscaping % — not extracted (the 45% applies to setback area only, not site).
- Deep soil is by lot size: 15% (≤449sqm), 20% (450-599sqm), 25% (600+sqm).
- Site coverage maximum (inverse of landscaping): 60% (≤449), 50% (450-599), 40% (600+).

Usage:
    python scripts/insert_canterbury_bankstown_landscaping.py --dry-run
    python scripts/insert_canterbury_bankstown_landscaping.py
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

LGA = "canterbury_bankstown"
DCP_VERSION = "v2023-amendment-8-aug2025"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "cb-dcp-2023-ch5-1-bankstown"

LANDSCAPING_ROWS = [
    # ── Deep soil by lot size (Table C1.2 — former Bankstown LGA) ──
    {
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 15,
        "value_max": None,
        "unit": "%",
        "condition": "former Bankstown LGA; lot area ≤449 sqm",
        "applicability": "universal_residential",
        "source_text": "Minimum 15% deep soil for lots up to 449 sqm (CB DCP 2023 Table C1.2)",
        "section_ref": "ch5-1-c1",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 20,
        "value_max": None,
        "unit": "%",
        "condition": "former Bankstown LGA; lot area 450-599 sqm",
        "applicability": "universal_residential",
        "source_text": "Minimum 20% deep soil for lots 450-599 sqm (CB DCP 2023 Table C1.2)",
        "section_ref": "ch5-1-c1",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 25,
        "value_max": None,
        "unit": "%",
        "condition": "former Bankstown LGA; lot area 600+ sqm",
        "applicability": "universal_residential",
        "source_text": "Minimum 25% deep soil for lots 600+ sqm (CB DCP 2023 Table C1.2)",
        "section_ref": "ch5-1-c1",
    },
    # ── Maximum site coverage (Table C1.1 — former Bankstown LGA) ──
    {
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 60,
        "unit": "%",
        "condition": "former Bankstown LGA; lot area ≤449 sqm",
        "applicability": "universal_residential",
        "source_text": "Maximum 60% site coverage for lots up to 449 sqm (CB DCP 2023 Table C1.1)",
        "section_ref": "ch5-1-c1",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 50,
        "unit": "%",
        "condition": "former Bankstown LGA; lot area 450-599 sqm",
        "applicability": "universal_residential",
        "source_text": "Maximum 50% site coverage for lots 450-599 sqm (CB DCP 2023 Table C1.1)",
        "section_ref": "ch5-1-c1",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 40,
        "unit": "%",
        "condition": "former Bankstown LGA; lot area 600+ sqm",
        "applicability": "universal_residential",
        "source_text": "Maximum 40% site coverage for lots 600+ sqm (CB DCP 2023 Table C1.1)",
        "section_ref": "ch5-1-c1",
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
                  f"min={row.get('value_min')} max={row.get('value_max')} unit={row['unit']} "
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
                  f"min={row.get('value_min')} max={row.get('value_max')} unit={row['unit']}")
            inserted += 1

    if not args.dry_run:
        conn.commit()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (duplicates)")
    conn.close()


if __name__ == "__main__":
    main()
