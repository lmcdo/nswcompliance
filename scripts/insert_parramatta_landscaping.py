#!/usr/bin/env python3
"""
Insert Parramatta landscaping controls into dcp_setback_controls.

Source: Parramatta DCP 2023 Amendment 4, Part 3 — Residential Development
        Sections 3.3.1.4, 3.3.2.4, 3.4.1.5, 3.4.2.4, 3.5.1.4
        As current.

Notes:
- Consistent pattern across all residential dev types:
  30% deep soil minimum + 40% landscaping minimum (including deep soil).
- RFB/apartments also have 30% deep soil (per ADG requirement).
- Deep soil location requirements (50% rear, 15-20% front) captured in condition.

Usage:
    python scripts/insert_parramatta_landscaping.py --dry-run
    python scripts/insert_parramatta_landscaping.py
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

LGA = "parramatta"
DCP_VERSION = "v2023-amendment4"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "parramatta-dcp-2023-full"

LANDSCAPING_ROWS = [
    # ── Dwelling houses (Section 3.3.1.4) ──
    {
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "50% at rear, 15% at front",
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of total site area as deep soil (Parramatta DCP 2023 s3.3.1.4 C.01)",
        "section_ref": "3-3-1-4",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "including deep soil zone",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% of total site area as landscaping including deep soil (Parramatta DCP 2023 s3.3.1.4 C.02)",
        "section_ref": "3-3-1-4",
    },
    # ── Secondary dwelling / dual occupancy (Section 3.3.2.4) ──
    {
        "dev_type": "dual_occupancy",
        "control_type": "deep_soil_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "50% at rear, 20% at front",
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of total site area as deep soil (Parramatta DCP 2023 s3.3.2.4 C.01)",
        "section_ref": "3-3-2-4",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "including deep soil zone",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% of total site area as landscaping including deep soil (Parramatta DCP 2023 s3.3.2.4 C.02)",
        "section_ref": "3-3-2-4",
    },
    # ── Multi dwelling housing (Section 3.4.1.5) ──
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "deep_soil_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of total site area as deep soil (Parramatta DCP 2023 s3.4.1.5 C.01)",
        "section_ref": "3-4-1-5",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "including deep soil zone",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% of total site area as landscaping including deep soil (Parramatta DCP 2023 s3.4.1.5 C.02)",
        "section_ref": "3-4-1-5",
    },
    # ── Terraces (Section 3.4.2.4) ──
    {
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "terraces; 50% at rear, 15% at front",
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of total site area as deep soil for terraces (Parramatta DCP 2023 s3.4.2.4 C.01)",
        "section_ref": "3-4-2-4",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "terraces; including deep soil zone",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% of total site area as landscaping for terraces (Parramatta DCP 2023 s3.4.2.4 C.02)",
        "section_ref": "3-4-2-4",
    },
    # ── Residential flat buildings (Section 3.5.1.4) ──
    {
        "dev_type": "residential_flat_building",
        "control_type": "deep_soil_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "50% at rear; min dimension 4m (or 6m for sites >1500sqm)",
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of total site area as deep soil (Parramatta DCP 2023 s3.5.1.4 C.01)",
        "section_ref": "3-5-1-4",
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
