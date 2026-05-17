#!/usr/bin/env python3
"""
Insert Northern Beaches landscaping controls into dcp_setback_controls.

Source: Warringah DCP 2011 (as amended May 2016)
        Part B5 — Site Coverage (DCP Map Site Coverage)
        Part G3 — Belrose Corridor

Notes:
- Site coverage controls are map-based (DCP Map Site Coverage).
- Residential areas typically show 40% max site coverage on the map
  (= 60% landscaped open space), but varies by locality.
- Belrose Corridor explicitly states 40% minimum landscaped open space.
- Bushland Setting areas require 50% minimum landscaped open space.
- Deep soil: side and rear setback areas must be landscaped and free of
  above/below ground structures.

Usage:
    python scripts/insert_northern_beaches_landscaping.py --dry-run
    python scripts/insert_northern_beaches_landscaping.py
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

LGA = "northern_beaches"
DCP_VERSION = "v2011-warringah-amended-may2016"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "warringah-appendix-1-car-parking"  # existing key

LANDSCAPING_ROWS = [
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "Belrose Corridor; other areas vary per DCP Map Site Coverage",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% landscaped open space (Warringah DCP 2011 G3 Belrose Corridor cl.15; general residential per DCP Map)",
        "section_ref": "g3-belrose-corridor",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "Bushland Setting areas (per DCP Map)",
        "applicability": "universal_residential",
        "source_text": "Minimum 50% site area as landscaped open space in Bushland Setting (Warringah DCP 2011 B5 Landscaped Open Space)",
        "section_ref": "b5-landscaped-open-space",
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
