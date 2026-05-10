#!/usr/bin/env python3
"""
Insert Campbelltown landscaping controls into dcp_setback_controls.

Source: Campbelltown (Sustainable City) DCP 2015
        3.6.3.6 (Dual Occupancy) and 3.6.4.6 (Semi-Detached)
        As current.

Notes:
- Dual occupancy and semi-detached: minimum 20% deep soil landscaped area.
- Max 30% impervious surface in front setback (expressed as max_site_coverage
  for front setback area).
- No dwelling_house-specific landscaping percentage found in Part 3.

Usage:
    python scripts/insert_campbelltown_landscaping.py --dry-run
    python scripts/insert_campbelltown_landscaping.py
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

LGA = "campbelltown"
DCP_VERSION = "v2015-current"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "campbelltown-dcp-part3-low-medium"

LANDSCAPING_ROWS = [
    # ── Dual occupancy ──
    {
        "dev_type": "dual_occupancy",
        "control_type": "deep_soil_min",
        "value_min": 20,
        "value_max": None,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum 20% of site area as deep soil landscaping (Campbelltown DCP 3.6.3.6)",
        "section_ref": "3-6-3-6",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 30,
        "unit": "%",
        "condition": "front setback area only; impervious surface",
        "applicability": "universal_residential",
        "source_text": "Maximum 30% impervious surface in front setback (Campbelltown DCP 3.6.3.6)",
        "section_ref": "3-6-3-6",
    },
    # ── Semi-detached ──
    {
        "dev_type": "semi_detached",
        "control_type": "deep_soil_min",
        "value_min": 20,
        "value_max": None,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum 20% of site area as deep soil landscaping (Campbelltown DCP 3.6.4.6)",
        "section_ref": "3-6-4-6",
    },
    {
        "dev_type": "semi_detached",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 30,
        "unit": "%",
        "condition": "front setback area only; impervious surface",
        "applicability": "universal_residential",
        "source_text": "Maximum 30% impervious surface in front setback (Campbelltown DCP 3.6.4.6)",
        "section_ref": "3-6-4-6",
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
