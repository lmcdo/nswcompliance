#!/usr/bin/env python3
"""
Insert Strathfield DCP 2005 landscaping controls into dcp_setback_controls.

Source: Strathfield Consolidated DCP 2005 (as amended 28 Jul 2015)
        Part A s9.3 — Dwelling houses: landscaped area per Table 2 (image — not extractable)
                       Front setback: 50% deep soil soft landscaping (s3.3.3)
        Part B s5.0 — Dual occupancy: 40% landscaped open space
        Part C s2.3 — Multiple-unit housing:
                       RFB: 35% landscaped area (60% of which must be soft)
                       Townhouse/villa: 40% landscaped area (70% soft)
                       Deep soil: 35% of required landscaped area

Usage:
    python scripts/insert_strathfield_landscaping.py --dry-run
    python scripts/insert_strathfield_landscaping.py
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

LGA = "strathfield"
DCP_VERSION = "v2005-amended-jul2015"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "landscaping-controls"

LANDSCAPING_ROWS = [
    # ── Dwelling House ──
    {
        "dev_type": "dwelling_house",
        "control_type": "front_setback_landscaping",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "of front setback area, deep soil soft landscaping",
        "applicability": "universal_residential",
        "source_text": "At least 50% of frontage must be deep soil soft landscaping (Part A s3.3.3)",
        "section_ref": "part-a-s3.3.3",
    },
    # ── Dual Occupancy ──
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum 40% of site area to be landscaped open space (Part B s5.0)",
        "section_ref": "part-b-s5.0",
    },
    # ── Multi Dwelling Housing (townhouse/villa) ──
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "70% of landscaped area must be soft landscaping",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% landscaped area for townhouses/villas, 70% must be soft (Part C s2.3)",
        "section_ref": "part-c-s2.3",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "deep_soil_min",
        "value_min": 35,
        "value_max": None,
        "unit": "% of landscaped area",
        "condition": "contiguous, suitable for large tree planting",
        "applicability": "universal_residential",
        "source_text": "At least 35% of required landscaped area as deep soil (Part C s2.3)",
        "section_ref": "part-c-s2.3",
    },
    # ── Residential Flat Building ──
    {
        "dev_type": "residential_flat_building",
        "control_type": "landscaping_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "60% of landscaped area must be soft landscaping",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% landscaped area for RFB, 60% must be soft (Part C s2.3)",
        "section_ref": "part-c-s2.3",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "deep_soil_min",
        "value_min": 35,
        "value_max": None,
        "unit": "% of landscaped area",
        "condition": "contiguous, suitable for large tree planting",
        "applicability": "universal_residential",
        "source_text": "At least 35% of required landscaped area as deep soil (Part C s2.3)",
        "section_ref": "part-c-s2.3",
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
