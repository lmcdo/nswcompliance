#!/usr/bin/env python3
"""
Insert Waverley landscaping controls into dcp_setback_controls.

Source: Waverley DCP 2022, Part B3 — Landscaping, Biodiversity and Vegetation
        Preservation, Section 3.2.4 Tree Canopy.
        As amended (Amendment 5).

Notes:
- Waverley does not have percentage-based site landscaping minimums like other
  councils. Instead it uses tree canopy coverage targets and species composition.
- The 29% tree canopy target is the LGA-wide Community Strategic Plan target.
- Development must not reduce tree canopy and must provide replacement planting.
- 90% native species requirement for trees and shrubs.
- 50% local provenance for plantings.
- No "minimum X% landscaped area" control exists — the approach is qualitative
  canopy/species rather than quantitative site coverage.

Usage:
    python scripts/insert_waverley_landscaping.py --dry-run
    python scripts/insert_waverley_landscaping.py
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

LGA = "waverley"
DCP_VERSION = "v2022-amendment5"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "waverley-dcp-2022"

LANDSCAPING_ROWS = [
    {
        "dev_type": "dwelling_house",
        "control_type": "tree_canopy_min",
        "value_min": 29,
        "value_max": None,
        "unit": "%",
        "condition": "LGA-wide target; development must not reduce existing canopy",
        "applicability": "universal_residential",
        "source_text": "Minimum 29% tree canopy coverage — development must not result in loss of tree canopy (Waverley DCP 2022 B3 s3.2.4)",
        "section_ref": "b3-3-2-4",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "tree_canopy_min",
        "value_min": 29,
        "value_max": None,
        "unit": "%",
        "condition": "LGA-wide target; development must not reduce existing canopy",
        "applicability": "universal_residential",
        "source_text": "Minimum 29% tree canopy coverage — development must not result in loss of tree canopy (Waverley DCP 2022 B3 s3.2.4)",
        "section_ref": "b3-3-2-4",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "tree_canopy_min",
        "value_min": 29,
        "value_max": None,
        "unit": "%",
        "condition": "LGA-wide target; development must not reduce existing canopy",
        "applicability": "universal_residential",
        "source_text": "Minimum 29% tree canopy coverage — development must not result in loss of tree canopy (Waverley DCP 2022 B3 s3.2.4)",
        "section_ref": "b3-3-2-4",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "tree_canopy_min",
        "value_min": 29,
        "value_max": None,
        "unit": "%",
        "condition": "LGA-wide target; development must not reduce existing canopy",
        "applicability": "universal_residential",
        "source_text": "Minimum 29% tree canopy coverage — development must not result in loss of tree canopy (Waverley DCP 2022 B3 s3.2.4)",
        "section_ref": "b3-3-2-4",
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
