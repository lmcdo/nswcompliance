#!/usr/bin/env python3
"""
Insert Georges River landscaping controls into dcp_setback_controls.

Source: Georges River LEP 2021, Clause 6.12 — Landscaped areas in certain
        residential and conservation zones.

Notes:
- Landscaping percentages are set by the LEP (not DCP). The DCP cross-references
  LEP cl 6.12. We store these here with extraction_method='manual' and source_text
  citing the LEP clause for full user traceability.
- Foreshore Scenic Protection Area (FSPA) has higher requirements.
- R3/R4 zones have fixed rates independent of dev type.

Usage:
    python scripts/insert_georges_river_landscaping.py --dry-run
    python scripts/insert_georges_river_landscaping.py
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

LGA = "georges_river"
DCP_VERSION = "v2021-lep"
EXTRACTION_METHOD = "manual"
SOURCE_CHAPTER_KEY = "part-3-general-planning-considerations"

LANDSCAPING_ROWS = [
    # ── Dwelling houses ──
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 20,
        "value_max": None,
        "unit": "%",
        "condition": "outside Foreshore Scenic Protection Area",
        "applicability": "universal_residential",
        "source_text": "Minimum 20% landscaped area for dwelling houses outside FSPA (Georges River LEP 2021 cl 6.12)",
        "section_ref": "lep-cl-6-12",
    },
    {
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 25,
        "value_max": None,
        "unit": "%",
        "condition": "within Foreshore Scenic Protection Area",
        "applicability": "universal_residential",
        "source_text": "Minimum 25% landscaped area for dwelling houses in FSPA (Georges River LEP 2021 cl 6.12)",
        "section_ref": "lep-cl-6-12",
    },
    # ── Dual occupancy / semi-detached ──
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 25,
        "value_max": None,
        "unit": "%",
        "condition": "outside Foreshore Scenic Protection Area",
        "applicability": "universal_residential",
        "source_text": "Minimum 25% landscaped area for dual occupancy outside FSPA (Georges River LEP 2021 cl 6.12)",
        "section_ref": "lep-cl-6-12",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "within Foreshore Scenic Protection Area",
        "applicability": "universal_residential",
        "source_text": "Minimum 30% landscaped area for dual occupancy in FSPA (Georges River LEP 2021 cl 6.12)",
        "section_ref": "lep-cl-6-12",
    },
    # ── R3 Medium Density zone (MDH, RFB) ──
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "landscaping_min",
        "value_min": 20,
        "value_max": None,
        "unit": "%",
        "condition": "R3 Medium Density Residential zone",
        "applicability": "universal_residential",
        "source_text": "Minimum 20% landscaped area in R3 zone (Georges River LEP 2021 cl 6.12)",
        "section_ref": "lep-cl-6-12",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "landscaping_min",
        "value_min": 20,
        "value_max": None,
        "unit": "%",
        "condition": "R3 Medium Density Residential zone",
        "applicability": "universal_residential",
        "source_text": "Minimum 20% landscaped area in R3 zone (Georges River LEP 2021 cl 6.12)",
        "section_ref": "lep-cl-6-12",
    },
    # ── R4 High Density zone ──
    {
        "dev_type": "residential_flat_building",
        "control_type": "landscaping_min",
        "value_min": 10,
        "value_max": None,
        "unit": "%",
        "condition": "R4 High Density Residential zone",
        "applicability": "universal_residential",
        "source_text": "Minimum 10% landscaped area in R4 zone (Georges River LEP 2021 cl 6.12)",
        "section_ref": "lep-cl-6-12",
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
