#!/usr/bin/env python3
"""
Insert Fairfield DCP 2024 landscaping controls into dcp_setback_controls.

Source: Fairfield City Wide Development Control Plan 2024
        Ch 5A.4.2 — Dwelling houses: 30% soft soil, 50% front yard landscaped
        Ch 6A.4.2 — Multi dwelling housing: 30% soft soil, 20% deep soil,
                     max 40% impervious
        Ch 6B.4.2 — Dual occupancy: 30% soft soil, 20% deep soil (min 4m width),
                     50% front yard landscaped, max 40% impervious
        Ch 7.5.5  — RFB: 25-30% open space
        Ch 7.8.1  — RFB: deep soil 25% of required open space

Usage:
    python scripts/insert_fairfield_landscaping.py --dry-run
    python scripts/insert_fairfield_landscaping.py
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

LGA = "fairfield"
DCP_VERSION = "v2024-current"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "landscaping-controls"

LANDSCAPING_ROWS = [
    # ── Dwelling House (Ch 5A.4.2) ──
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "soft soil zone, 50% must be in rear yard",
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of site as soft soil zone (Ch 5A.4.2)",
        "section_ref": "ch-5a-s4.2",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "front_setback_landscaping",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "of front yard area",
        "applicability": "universal_residential",
        "source_text": "Minimum 50% of front yard to be landscaped (Ch 5A.4.2)",
        "section_ref": "ch-5a-s4.2",
    },
    # ── Dual Occupancy (Ch 6B.4.2) ──
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "soft soil zone",
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of site as soft soil zone (Ch 6B.4.2)",
        "section_ref": "ch-6b-s4.2",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "deep_soil_min",
        "value_min": 20,
        "value_max": None,
        "unit": "%",
        "condition": "minimum width 4m",
        "applicability": "universal_residential",
        "source_text": "Minimum 20% deep soil with minimum width 4m (Ch 6B.4.2)",
        "section_ref": "ch-6b-s4.2",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "front_setback_landscaping",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "of front yard area",
        "applicability": "universal_residential",
        "source_text": "Minimum 50% of front yard to be landscaped (Ch 6B.4.2)",
        "section_ref": "ch-6b-s4.2",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 40,
        "unit": "% impervious",
        "condition": "including basements, driveways",
        "applicability": "universal_residential",
        "source_text": "No more than 40% impervious material including basements/driveways (Ch 6B.4.2)",
        "section_ref": "ch-6b-s4.2",
    },
    # ── Multi Dwelling Housing (Ch 6A.4.2) ──
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "soft soil zone",
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of site as soft soil zone (Ch 6A.4.2)",
        "section_ref": "ch-6a-s4.2",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "deep_soil_min",
        "value_min": 20,
        "value_max": None,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Minimum 20% of site as deep soil (Ch 6A.4.2)",
        "section_ref": "ch-6a-s4.2",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 40,
        "unit": "% impervious",
        "condition": "including paving",
        "applicability": "universal_residential",
        "source_text": "No more than 40% impervious material including paving (Ch 6A.4.2)",
        "section_ref": "ch-6a-s4.2",
    },
    # ── Residential Flat Building (Ch 7.5.5 + 7.8.1) ──
    {
        "dev_type": "residential_flat_building",
        "control_type": "landscaping_min",
        "value_min": 25,
        "value_max": 30,
        "unit": "%",
        "condition": "open space area",
        "applicability": "universal_residential",
        "source_text": "Open space generally 25-30% of site (Ch 7.5.5)",
        "section_ref": "ch-7-s5.5",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "deep_soil_min",
        "value_min": 25,
        "value_max": None,
        "unit": "% of open space",
        "condition": "adjoining deep soil of neighbouring properties where possible",
        "applicability": "universal_residential",
        "source_text": "Deep soil zone no less than 25% of required open space (Ch 7.8.1.1)",
        "section_ref": "ch-7-s8.1.1",
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
