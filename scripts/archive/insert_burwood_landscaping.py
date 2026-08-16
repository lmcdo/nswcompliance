#!/usr/bin/env python3
"""
Insert Burwood DCP landscaping controls into dcp_setback_controls.

Source: Burwood DCP (current, Amendment 13, effective 3 Nov 2025)
        Section 4.1.2.3 (RFB): 10% deep soil, 25-30% landscaped area
        Section 4.3.2.3 (Multi dwelling): 15% deep soil, 25% landscaped area
        Section 4.4.3.2 (Dual occ): 30% front setback soft landscaping, 67% max built area
        Section 4.5.3.9 (Dwelling house): landscaping controls (qualitative)

Usage:
    python scripts/insert_burwood_landscaping.py --dry-run
    python scripts/insert_burwood_landscaping.py
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

LGA = "burwood"
DCP_VERSION = "v2013-amendment-13-nov2025"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "s4-landscaping"

LANDSCAPING_ROWS = [
    # ── Residential Flat Building ──
    {
        "dev_type": "residential_flat_building",
        "control_type": "deep_soil_min",
        "value_min": 10,
        "value_max": None,
        "unit": "%",
        "condition": "minimum dimension 4m",
        "applicability": "universal_residential",
        "source_text": "Minimum 10% of site area as deep soil, min dimension 4m (Burwood DCP s4.1.2.3 P10)",
        "section_ref": "s4.1.2.3-P10",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "landscaping_min",
        "value_min": 25,
        "value_max": 30,
        "unit": "%",
        "condition": "inclusive of deep soil zone",
        "applicability": "universal_residential",
        "source_text": "25-30% of site to be landscaped, inclusive of deep soil zone (Burwood DCP s4.1.2.3 P11)",
        "section_ref": "s4.1.2.3-P11",
    },
    # ── Multi Dwelling Housing ──
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "deep_soil_min",
        "value_min": 15,
        "value_max": None,
        "unit": "%",
        "condition": "minimum dimension 4m x 4m",
        "applicability": "universal_residential",
        "source_text": "Minimum 15% of site area as deep soil, min dimension 4m x 4m (Burwood DCP s4.3.2.3 P12)",
        "section_ref": "s4.3.2.3-P12",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 25,
        "value_max": None,
        "unit": "%",
        "condition": "inclusive of deep soil zone",
        "applicability": "universal_residential",
        "source_text": "Minimum 25% of site to be landscaped, inclusive of deep soil zone (Burwood DCP s4.3.2.3 P15)",
        "section_ref": "s4.3.2.3-P15",
    },
    # ── Dual Occupancy ──
    {
        "dev_type": "dual_occupancy",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 67,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "Maximum Built Area 67% (Burwood DCP s4.4.3.2 P8)",
        "section_ref": "s4.4.3.2-P8",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "front_setback_landscaping",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "of front setback area, soft landscaping",
        "applicability": "universal_residential",
        "source_text": "Minimum 30% of front setback as soft landscaping (Burwood DCP s4.4.3.2 P14)",
        "section_ref": "s4.4.3.2-P14",
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
