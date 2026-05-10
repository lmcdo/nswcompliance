#!/usr/bin/env python3
"""
Insert Woollahra landscaping/deep soil controls into dcp_setback_controls.

Source: Woollahra DCP 2015, Chapter B3 — General Development Controls
        Section B3.7.1 (Landscaped area and private open space)
        As amended 2 December 2024.

Notes:
- Controls apply in R2 and R3 residential zones for development that
  alters building footprint/envelope.
- Tree canopy area and deep soil landscaped area are separate controls.
- Wolseley Road area has reduced requirements (30% vs 35%).
- Heritage conservation areas (C1 Paddington, C2 Woollahra, C3 Watsons Bay)
  have their own deep soil tables — not extracted here (precinct-specific).

Usage:
    python scripts/insert_woollahra_landscaping.py --dry-run
    python scripts/insert_woollahra_landscaping.py
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

LGA = "woollahra"
DCP_VERSION = "v2015-amended-dec2024"
EXTRACTION_METHOD = "text_extraction"
SOURCE_CHAPTER_KEY = "chapter-b3-general-development"

LANDSCAPING_ROWS = [
    # ── Tree canopy — dwelling houses, dual occ, semi-detached, attached ──
    {
        "dev_type": "dwelling_house",
        "control_type": "tree_canopy_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "R2/R3 zones; excludes Wolseley Road area",
        "applicability": "universal_residential",
        "source_text": "Tree canopy area at least 35% for dwelling houses (Woollahra DCP B3.7.1 C1a)",
        "section_ref": "b3-7-1",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "tree_canopy_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "R2/R3 zones; excludes Wolseley Road area",
        "applicability": "universal_residential",
        "source_text": "Tree canopy area at least 35% for dual occupancies (Woollahra DCP B3.7.1 C1a)",
        "section_ref": "b3-7-1",
    },

    # ── Tree canopy — RFB, MDH, other residential ──
    {
        "dev_type": "residential_flat_building",
        "control_type": "tree_canopy_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "R2/R3 zones",
        "applicability": "universal_residential",
        "source_text": "Tree canopy area at least 30% for RFB and other residential (Woollahra DCP B3.7.1 C1b)",
        "section_ref": "b3-7-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "tree_canopy_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "R2/R3 zones",
        "applicability": "universal_residential",
        "source_text": "Tree canopy area at least 30% for MDH and other residential (Woollahra DCP B3.7.1 C1b)",
        "section_ref": "b3-7-1",
    },

    # ── Deep soil — all residential (general) ──
    {
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "R2/R3 zones; excludes Wolseley Road area",
        "applicability": "universal_residential",
        "source_text": "35% deep soil landscaped area (Woollahra DCP B3.7.1 C2)",
        "section_ref": "b3-7-1",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "deep_soil_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "R2/R3 zones; excludes Wolseley Road area",
        "applicability": "universal_residential",
        "source_text": "35% deep soil landscaped area (Woollahra DCP B3.7.1 C2)",
        "section_ref": "b3-7-1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "deep_soil_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "R2/R3 zones; excludes Wolseley Road area",
        "applicability": "universal_residential",
        "source_text": "35% deep soil landscaped area (Woollahra DCP B3.7.1 C2)",
        "section_ref": "b3-7-1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "deep_soil_min",
        "value_min": 35,
        "value_max": None,
        "unit": "%",
        "condition": "R2/R3 zones; excludes Wolseley Road area",
        "applicability": "universal_residential",
        "source_text": "35% deep soil landscaped area (Woollahra DCP B3.7.1 C2)",
        "section_ref": "b3-7-1",
    },

    # ── Deep soil — Wolseley Road area (reduced) ──
    {
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "Wolseley Road area",
        "applicability": "universal_residential",
        "source_text": "30% deep soil in Wolseley Road area (Woollahra DCP B3.7.1 C2)",
        "section_ref": "b3-7-1",
    },

    # ── Front setback deep soil ──
    {
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "front setback area only",
        "applicability": "universal_residential",
        "source_text": "At least 40% of front setback is deep soil (Woollahra DCP B3.7.1 C3)",
        "section_ref": "b3-7-1",
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

    if not args.dry_run and inserted > 0:
        cur.execute("""
            SELECT dev_type, control_type, count(*) as n
            FROM dcp_setback_controls
            WHERE lga = %s AND control_type IN ('tree_canopy_min', 'deep_soil_min', 'landscaping_min')
              AND is_current = TRUE
            GROUP BY dev_type, control_type ORDER BY dev_type, control_type
        """, (LGA,))
        print(f"\nWoollahra landscaping controls:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['control_type']:20s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
