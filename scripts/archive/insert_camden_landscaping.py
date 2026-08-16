#!/usr/bin/env python3
"""
Insert Camden DCP 2019 landscaping controls into dcp_setback_controls.

Source: Camden DCP 2019, Part 2 Section 4.2.6 Landscaping
        All residential development types: minimum 30% landscaped area.
        Front setback: 40% of front setback area to be landscaped.
        RFB: maximum 50% site coverage (s4.8).

Usage:
    python scripts/insert_camden_landscaping.py --dry-run
    python scripts/insert_camden_landscaping.py
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

LGA = "camden"
DCP_VERSION = "v2019"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "s4-2-6-landscaping"

LANDSCAPING_ROWS = [
    # ── Dwelling House ──
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of site area to be landscaped (Camden DCP s4.2.6)",
        "section_ref": "s4.2.6",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "front_setback_landscaping",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "of front setback area",
        "applicability": "universal_residential",
        "source_text": "40% of front setback area to be landscaped (Camden DCP s4.2.6)",
        "section_ref": "s4.2.6",
    },
    # ── Dual Occupancy ──
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of site area to be landscaped (Camden DCP s4.3)",
        "section_ref": "s4.3",
    },
    # ── Multi Dwelling Housing ──
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of site area to be landscaped (Camden DCP s4.6)",
        "section_ref": "s4.6",
    },
    # ── Residential Flat Building ──
    {
        "dev_type": "residential_flat_building",
        "control_type": "landscaping_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of site area to be landscaped (Camden DCP s4.8)",
        "section_ref": "s4.8",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 50,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Maximum 50% site coverage for RFB (Camden DCP s4.8)",
        "section_ref": "s4.8",
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
