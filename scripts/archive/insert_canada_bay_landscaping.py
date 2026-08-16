#!/usr/bin/env python3
"""
Insert Canada Bay DCP landscaping controls into dcp_setback_controls.

Source: City of Canada Bay DCP (adopted 17 Jun 2025, effective 27 Jun 2025)
        Part E, Section E4.6, Table E-A — Low density residential
        Part F, Section F4.6, Table F-A — Medium/high density residential

Rates:
- DH / dual occ / secondary / semi-detached: 35% landscaped area,
  50% front setback, 50% rear setback
- MDH / RFB / terraces / manor house: 50% lot area minus 100sqm,
  35% front setback, 50% rear setback
- Common open space (MDH/RFB): 25% of site or 10sqm/dwelling (whichever greater)

Usage:
    python scripts/insert_canada_bay_landscaping.py --dry-run
    python scripts/insert_canada_bay_landscaping.py
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

LGA = "canada_bay"
DCP_VERSION = "v2025-jun2025"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "landscaping-controls"

LANDSCAPING_ROWS = [
    # ── Dwelling House (Part E, Table E-A) ──
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "of parent lot area; areas <1.5m x 1.5m excluded",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% of parent lot as landscaped area (Part E, Table E-A)",
        "section_ref": "part-e-s4.6",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "front_setback_landscaping",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "of front setback area",
        "applicability": "universal_residential",
        "source_text": "Minimum 50% of front setback landscaped (Part E, Table E-A)",
        "section_ref": "part-e-s4.6",
    },
    # ── Dual Occupancy (Part E, Table E-A) ──
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "of parent lot area; areas <1.5m x 1.5m excluded",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% of parent lot as landscaped area (Part E, Table E-A)",
        "section_ref": "part-e-s4.6",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "front_setback_landscaping",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "of front setback area",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% of front setback landscaped for dual occupancy (Part E, Table E-A)",
        "section_ref": "part-e-s4.6",
    },
    # ── Multi Dwelling Housing (Part F, Table F-A) ──
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 50,
        "value_max": None,
        "unit": "% of lot minus 100sqm",
        "condition": "areas <1.5m x 1.5m excluded",
        "applicability": "universal_residential",
        "source_text": "Minimum 50% of lot area minus 100sqm as landscaped area (Part F, Table F-A)",
        "section_ref": "part-f-s4.6",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "front_setback_landscaping",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "of front setback area",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% of front setback landscaped (Part F, Table F-A)",
        "section_ref": "part-f-s4.6",
    },
    # ── Residential Flat Building (Part F, Table F-A) ──
    {
        "dev_type": "residential_flat_building",
        "control_type": "landscaping_min",
        "value_min": 50,
        "value_max": None,
        "unit": "% of lot minus 100sqm",
        "condition": "areas <1.5m x 1.5m excluded",
        "applicability": "universal_residential",
        "source_text": "Minimum 50% of lot area minus 100sqm as landscaped area (Part F, Table F-A)",
        "section_ref": "part-f-s4.6",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "front_setback_landscaping",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "of front setback area",
        "applicability": "universal_residential",
        "source_text": "Minimum 35% of front setback landscaped (Part F, Table F-A)",
        "section_ref": "part-f-s4.6",
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
