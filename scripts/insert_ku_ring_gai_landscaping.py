#!/usr/bin/env python3
"""
Insert Ku-ring-gai landscaping/deep soil controls into dcp_setback_controls.

Source: Ku-ring-gai DCP 2016 (adopted 20 September 2016)
        Parts 4 (Dwelling Houses), 5 (Dual Occupancy), 6 (MDH),
        7 (RFB), 8 (Mixed Use)

Notes:
- Dwelling house: BUA (built-upon area) maxima are site-area dependent,
  not a simple landscaping minimum %. Omitted — would need a separate
  control_type (e.g. 'max_site_coverage') and site-area bands.
- Deep soil controls are percentage-based and suitable for extraction.
- Mixed use: same deep soil as RFB (Part 8A.6 references Part 7A.6).

Usage:
    python scripts/insert_ku_ring_gai_landscaping.py --dry-run
    python scripts/insert_ku_ring_gai_landscaping.py
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

LGA = "ku_ring_gai"
DCP_VERSION = "v2016-current"
EXTRACTION_METHOD = "text_extraction"

LANDSCAPING_ROWS = [
    # ── Dual Occupancy — Part 5A.5 ──
    {
        "dev_type": "dual_occupancy",
        "control_type": "landscaping_min",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "parent lot area minus 100sqm; each dwelling provides half",
        "applicability": "universal_residential",
        "source_text": "Dual occ: min landscaped area = 50% of parent lot minus 100sqm (KDCP Part 5A.5)",
        "section_ref": "part-5a-5",
        "source_chapter_key": "section-a-part-5-dual-occupancy",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "deep_soil_min",
        "value_min": 30,
        "value_max": None,
        "unit": "%",
        "condition": "min dimension 2m; suitable for tall tree planting",
        "applicability": "universal_residential",
        "source_text": "Dual occ: min 30% deep soil area per dwelling site (KDCP Part 5A.5)",
        "section_ref": "part-5a-5",
        "source_chapter_key": "section-a-part-5-dual-occupancy",
    },

    # ── Multi Dwelling Housing — Part 6A.5/6A.6 ──
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 40,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "MDH: max site coverage 40% (KDCP Part 6A.5)",
        "section_ref": "part-6a-5",
        "source_chapter_key": "section-a-part-6-multi-dwelling",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "deep_soil_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "within common areas only",
        "applicability": "universal_residential",
        "source_text": "MDH: min 40% deep soil landscaping within common areas (KDCP Part 6A.6)",
        "section_ref": "part-6a-6",
        "source_chapter_key": "section-a-part-6-multi-dwelling",
    },

    # ── Residential Flat Building — Part 7A.5/7A.6 ──
    {
        "dev_type": "residential_flat_building",
        "control_type": "max_site_coverage",
        "value_min": None,
        "value_max": 30,
        "unit": "%",
        "condition": None,
        "applicability": "universal_residential",
        "source_text": "RFB: max site coverage 30% (KDCP Part 7A.5)",
        "section_ref": "part-7a-5",
        "source_chapter_key": "section-a-part-7-residential-flat-buildings",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "deep_soil_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "site area less than 1800sqm",
        "applicability": "universal_residential",
        "source_text": "RFB: min 40% deep soil for sites <1800sqm (KDCP Part 7A.6)",
        "section_ref": "part-7a-6",
        "source_chapter_key": "section-a-part-7-residential-flat-buildings",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "deep_soil_min",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "site area 1800sqm or more",
        "applicability": "universal_residential",
        "source_text": "RFB: min 50% deep soil for sites >=1800sqm (KDCP Part 7A.6)",
        "section_ref": "part-7a-6",
        "source_chapter_key": "section-a-part-7-residential-flat-buildings",
    },

    # ── Mixed Use — Part 8A.6 (references RFB controls) ──
    {
        "dev_type": "mixed_use",
        "control_type": "deep_soil_min",
        "value_min": 40,
        "value_max": None,
        "unit": "%",
        "condition": "site area less than 1800sqm; R4 zone",
        "applicability": "universal_residential",
        "source_text": "Mixed use: min 40% deep soil for sites <1800sqm in R4 (KDCP Part 8A.6)",
        "section_ref": "part-8a-6",
        "source_chapter_key": "section-a-part-8-mixed-use",
    },
    {
        "dev_type": "mixed_use",
        "control_type": "deep_soil_min",
        "value_min": 50,
        "value_max": None,
        "unit": "%",
        "condition": "site area 1800sqm or more; R4 zone",
        "applicability": "universal_residential",
        "source_text": "Mixed use: min 50% deep soil for sites >=1800sqm in R4 (KDCP Part 8A.6)",
        "section_ref": "part-8a-6",
        "source_chapter_key": "section-a-part-8-mixed-use",
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
                  f"min={row.get('value_min')} max={row.get('value_max')} unit={row['unit']} "
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
                  DCP_VERSION, EXTRACTION_METHOD,
                  row.get("source_chapter_key", "section-c-part-22-parking")))
            print(f"  INSERT: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} max={row.get('value_max')} unit={row['unit']}")
            inserted += 1

    if not args.dry_run:
        conn.commit()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (duplicates)")

    if not args.dry_run and inserted > 0:
        cur.execute("""
            SELECT dev_type, control_type, count(*) as n
            FROM dcp_setback_controls
            WHERE lga = %s AND control_type IN ('landscaping_min', 'deep_soil_min', 'max_site_coverage')
              AND is_current = TRUE
            GROUP BY dev_type, control_type ORDER BY dev_type, control_type
        """, (LGA,))
        print(f"\nKu-ring-gai landscaping controls:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['control_type']:20s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
