#!/usr/bin/env python3
"""
Insert Penrith DCP 2014 landscaping controls into dcp_setback_controls.

Source: Penrith DCP 2014, Part D2 Residential Development
        s2.1.4 — Single dwellings: landscaped area by zone
        s2.2.8 — Dual occupancy: landscaped area by zone
        s2.4.8 — Multi dwelling housing: landscaped area by zone + communal open space
        s2.5.5 — Residential flat buildings: landscaped area by zone + communal open space

Zone-based minimum landscaped area:
  R1 General Residential: 40%
  R2 Low Density Residential: 50%
  R3 Medium Density Residential: 40%
  R4 High Density Residential: 35%

Usage:
    python scripts/insert_penrith_landscaping.py --dry-run
    python scripts/insert_penrith_landscaping.py
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

LGA = "penrith"
DCP_VERSION = "v2014"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "d2-landscaping"

LANDSCAPING_ROWS = [
    # ── Dwelling House (s2.1.4) ──
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "zone R1 General Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% landscaped area in R1 zone (Part D2, s2.1.4)",
        "section_ref": "d2-s2.1.4",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "zone R2 Low Density Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 50% landscaped area in R2 zone (Part D2, s2.1.4)",
        "section_ref": "d2-s2.1.4",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "zone R3 Medium Density Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% landscaped area in R3 zone (Part D2, s2.1.4)",
        "section_ref": "d2-s2.1.4",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "zone R4 High Density Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% landscaped area in R4 zone (Part D2, s2.1.4)",
        "section_ref": "d2-s2.1.4",
    },
    # ── Dual Occupancy (s2.2.8) ──
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "zone R1 General Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% landscaped area in R1 zone (Part D2, s2.2.8)",
        "section_ref": "d2-s2.2.8",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "zone R2 Low Density Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 50% landscaped area in R2 zone (Part D2, s2.2.8)",
        "section_ref": "d2-s2.2.8",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "zone R3 Medium Density Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% landscaped area in R3 zone (Part D2, s2.2.8)",
        "section_ref": "d2-s2.2.8",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "zone R4 High Density Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% landscaped area in R4 zone (Part D2, s2.2.8)",
        "section_ref": "d2-s2.2.8",
    },
    # ── Multi Dwelling Housing (s2.4.8) ──
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "zone R1 General Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% landscaped area in R1 zone (Part D2, s2.4.8)",
        "section_ref": "d2-s2.4.8",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "zone R3 Medium Density Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% landscaped area in R3 zone (Part D2, s2.4.8)",
        "section_ref": "d2-s2.4.8",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "zone R4 High Density Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% landscaped area in R4 zone (Part D2, s2.4.8)",
        "section_ref": "d2-s2.4.8",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "communal_open_space_min",
        "value_min": 10,
        "value_max": None,
        "unit": "% of landscaped area",
        "condition": "10+ dwellings; centrally located communal open space",
        "applicability": "universal_residential",
        "source_text": "10% of landscaped area as communal open space for 10+ dwellings (Part D2, s2.4.8)",
        "section_ref": "d2-s2.4.8",
    },
    # ── Residential Flat Building (s2.5.5) ──
    {
        "dev_type": "residential_flat_building",
        "control_type": "landscaping_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "zone R1 General Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 40% landscaped area in R1 zone (Part D2, s2.5.5)",
        "section_ref": "d2-s2.5.5",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "landscaping_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "zone R4 High Density Residential",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% landscaped area in R4 zone (Part D2, s2.5.5)",
        "section_ref": "d2-s2.5.5",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "communal_open_space_min",
        "value_min": 10,
        "value_max": None,
        "unit": "% of landscaped area",
        "condition": "10+ dwellings; centrally located communal open space",
        "applicability": "universal_residential",
        "source_text": "10% of landscaped area as communal open space for 10+ dwellings (Part D2, s2.5.5)",
        "section_ref": "d2-s2.5.5",
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
