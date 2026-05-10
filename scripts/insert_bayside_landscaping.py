#!/usr/bin/env python3
"""
Insert Bayside landscaping controls into dcp_setback_controls.

Source: Bayside DCP 2022, Part 4B — Multi Dwelling Housing
        Section 4B.2.8 Deep Soil Planting
        As current (effective 10 April 2023).

Notes:
- Multi dwelling housing: minimum 35% deep soil, max 45% site coverage.
- Deep soil distribution: 50% at rear, 30% in front setback.
- No dwelling_house-specific DCP landscaping % found — Bayside LEP
  may control this (similar to Georges River using LEP clause 6.12).

Usage:
    python scripts/insert_bayside_landscaping.py --dry-run
    python scripts/insert_bayside_landscaping.py
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

LGA = "bayside"
DCP_VERSION = "v2022-current"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "s3-5-traffic-parking-access"  # using existing key from parking

LANDSCAPING_ROWS = [
    # ── Multi dwelling housing ──
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "deep_soil_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "50% at rear, 30% in front setback",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% of site as deep soil planting area (Bayside DCP Part 4B C25)",
        "section_ref": "4b-2-8",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 45,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Maximum 45% site coverage for multi dwelling housing (Bayside DCP Part 4B C2)",
        "section_ref": "4b-2-1",
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
