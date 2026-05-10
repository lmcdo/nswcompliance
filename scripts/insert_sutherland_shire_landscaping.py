#!/usr/bin/env python3
"""
Insert Sutherland Shire landscaping controls into dcp_setback_controls.

Source: Sutherland Shire LEP 2015, Clause 6.14 — Landscaped areas in certain
        residential, employment, conservation and waterway zones.

Notes:
- Landscaping percentages set by LEP via Landscape Area Map.
- General residential rate is 45% (from council's key topics page).
- Dual occ/MDH in residential zones: 35% (from search results).
- Map-based variations exist but 45% is the standard R2 rate.

Usage:
    python scripts/insert_sutherland_shire_landscaping.py --dry-run
    python scripts/insert_sutherland_shire_landscaping.py
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
DCP_VERSION = "v2015-lep"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "ch36-vehicular-access-traffic-parking"  # existing key

LANDSCAPING_ROWS = [
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 45,
        "value_max": None,
        "unit": "%",
        "condition": "standard R2 rate; varies by Landscape Area Map (LEP cl 6.14)",
        "applicability": "universal_residential",
        "source_text": "Minimum 45% landscaped area for dwelling houses (Sutherland Shire LEP 2015 cl 6.14, Landscape Area Map)",
        "section_ref": "lep-cl-6-14",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "R2 zone; varies by Landscape Area Map (LEP cl 6.14)",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% landscaped area for dual occupancy (Sutherland Shire LEP 2015 cl 6.14)",
        "section_ref": "lep-cl-6-14",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "R2/R3 zones; varies by Landscape Area Map (LEP cl 6.14)",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% landscaped area for multi dwelling housing (Sutherland Shire LEP 2015 cl 6.14)",
        "section_ref": "lep-cl-6-14",
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
