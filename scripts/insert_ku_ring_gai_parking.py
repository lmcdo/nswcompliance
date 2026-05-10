#!/usr/bin/env python3
"""
Insert Ku-ring-gai DCP 2016 parking controls into dcp_setback_controls.

Source: Ku-ring-gai DCP 2016 (as amended)
  - Part 22R.1 Car Parking Rates (pp22-14 to 22-20) — general minimum rates
  - Part 4B.2 (p4-17) — dwelling houses: 2 spaces
  - Part 5B.2 (p5-14) — secondary dwellings: 1 hardstand space
  - Part 6B.2 (p6-19) — multi dwelling housing near station: min/max ranges
  - Part 7B.1 (p7-20) — residential flat buildings near station: min/max ranges
  - Part 8B.2 (p8-22) — mixed use near station: min/max ranges

Notes:
- Ku-ring-gai has TWO parking regimes:
  1. Within 400m of a railway station: min/max ranges (from per-dev-type chapters)
  2. All other locations: minimum rates from Part 22R.1
- Part 22R.1 rates are MINIMUM rates (standard council pattern).
- Station-proximate rates have both min AND max (excess counts as GFA).
- Source chapter key is 'section-c-part-22-parking' (the centralised Part 22R).
  Station-proximate rows use source_chapter_key_override to point to the
  relevant dev-type chapter.
- No secondary_dwelling rate listed — SEPP Housing 2021 deferral for
  secondary dwellings, but KRG actually has Part 5B.2 (1 hardstand space).

Usage:
    python scripts/insert_ku_ring_gai_parking.py --dry-run
    python scripts/insert_ku_ring_gai_parking.py
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
SOURCE_CHAPTER_KEY = "section-c-part-22-parking"

PARKING_ROWS = [
    # ═══════════════════════════════════════════════════════════════
    # PART 22R.1 — General minimum rates (all locations)
    # ═══════════════════════════════════════════════════════════════

    # ─ Dwelling House ─
    {
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "single occupancy dwelling",
        "applicability": "universal_residential",
        "source_text": "Dwelling-houses: 2 spaces for single occupancy (Part 22R.1)",
        "section_ref": "22R.1",
    },

    # ─ Dual Occupancy ─
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "under 125m2 GFA per dwelling",
        "applicability": "universal_residential",
        "source_text": "Dual occupancy under 125m2: 1 space per dwelling (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "dual_occupancy",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "125m2 or more GFA per dwelling",
        "applicability": "universal_residential",
        "source_text": "Dual occupancy over 125m2: 2 spaces per dwelling (Part 22R.1)",
        "section_ref": "22R.1",
    },

    # ─ Secondary Dwelling (Part 5B.2) ─
    {
        "dev_type": "secondary_dwelling",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "open hardstand only; min 2.5m x 5.4m",
        "applicability": "secondary_dwelling_specific",
        "source_text": "Secondary dwellings: 1 open hardstand space, min 2.5m x 5.4m (Part 5B.2)",
        "section_ref": "5B.2",
        "source_chapter_key_override": "section-a-part-4-1-secondary-dwellings",
    },

    # ─ Multi Dwelling Housing — Part 22R.1 general rates ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "MDH 1 bedroom unit: 1 space (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.25,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "MDH 2 bedroom unit: minimum 1.25 spaces per unit (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "MDH 3 bedroom unit: minimum 1.5 spaces per unit (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "MDH visitor: 1 space per 4 units (Part 22R.1)",
        "section_ref": "22R.1",
    },

    # ─ RFB — Part 22R.1 general rates ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB studio: 0.5 spaces per unit (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB 1 bedroom: 1 space per unit (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.25,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB 2 bedroom: 1.25 spaces per unit (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB 3 bedroom: 2 spaces per unit (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB visitor: 1 space per 4 units (Part 22R.1)",
        "section_ref": "22R.1",
    },

    # ═══════════════════════════════════════════════════════════════
    # STATION-PROXIMATE RATES — within 400m of railway station
    # These have min/max ranges; excess above max counts as GFA
    # ═══════════════════════════════════════════════════════════════

    # ─ MDH within 400m of station (Part 6B.2, Control 10) ─
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": 1,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "MDH within 400m station: 1 bedroom min 1, max 1 (Part 6B.2 Control 10)",
        "section_ref": "6B.2",
        "source_chapter_key_override": "section-a-part-6-multi-dwelling",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": 1.5,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "MDH within 400m station: 2 bedroom min 1, max 1.5 (Part 6B.2 Control 10)",
        "section_ref": "6B.2",
        "source_chapter_key_override": "section-a-part-6-multi-dwelling",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "MDH within 400m station: 3+ bedroom min 1, max 2 (Part 6B.2 Control 10)",
        "section_ref": "6B.2",
        "source_chapter_key_override": "section-a-part-6-multi-dwelling",
    },
    {
        "dev_type": "multi_dwelling_housing",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": 0.25,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "MDH within 400m station: visitor 1 space per 4 dwellings (Part 6B.2 Control 12)",
        "section_ref": "6B.2",
        "source_chapter_key_override": "section-a-part-6-multi-dwelling",
    },

    # ─ RFB within 400m of station (Part 7B.1, Control 9) ─
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0,
        "value_max": 0.5,
        "unit": "spaces/dwelling",
        "condition": "studio; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB within 400m station: studio min 0, max 0.5 (Part 7B.1 Control 9)",
        "section_ref": "7B.1",
        "source_chapter_key_override": "section-a-part-7-residential-flat-buildings",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.6,
        "value_max": 1,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB within 400m station: 1 bedroom min 0.6, max 1 (Part 7B.1 Control 9)",
        "section_ref": "7B.1",
        "source_chapter_key_override": "section-a-part-7-residential-flat-buildings",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": 1.25,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB within 400m station: 2 bedroom min 1, max 1.25 (Part 7B.1 Control 9)",
        "section_ref": "7B.1",
        "source_chapter_key_override": "section-a-part-7-residential-flat-buildings",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 1.4,
        "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB within 400m station: 3+ bedroom min 1.4, max 2 (Part 7B.1 Control 9)",
        "section_ref": "7B.1",
        "source_chapter_key_override": "section-a-part-7-residential-flat-buildings",
    },
    {
        "dev_type": "residential_flat_building",
        "control_type": "car_parking",
        "value_min": 0.167,
        "value_max": 0.167,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB within 400m station: visitor 1 space per 6 apartments (Part 7B.1 Control 11)",
        "section_ref": "7B.1",
        "source_chapter_key_override": "section-a-part-7-residential-flat-buildings",
    },

    # ─ Mixed Use (residential component) within 400m of station (Part 8B.2, Control 15) ─
    {
        "dev_type": "mixed_use",
        "control_type": "car_parking",
        "value_min": 0,
        "value_max": 0.5,
        "unit": "spaces/dwelling",
        "condition": "studio; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "Mixed use within 400m station: studio min 0, max 0.5 (Part 8B.2 Control 15)",
        "section_ref": "8B.2",
        "source_chapter_key_override": "section-a-part-8-mixed-use",
    },
    {
        "dev_type": "mixed_use",
        "control_type": "car_parking",
        "value_min": 0.6,
        "value_max": 1,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "Mixed use within 400m station: 1 bedroom min 0.6, max 1 (Part 8B.2 Control 15)",
        "section_ref": "8B.2",
        "source_chapter_key_override": "section-a-part-8-mixed-use",
    },
    {
        "dev_type": "mixed_use",
        "control_type": "car_parking",
        "value_min": 0.9,
        "value_max": 1.25,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "Mixed use within 400m station: 2 bedroom min 0.9, max 1.25 (Part 8B.2 Control 15)",
        "section_ref": "8B.2",
        "source_chapter_key_override": "section-a-part-8-mixed-use",
    },
    {
        "dev_type": "mixed_use",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": 2,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "Mixed use within 400m station: 3+ bedroom min 1, max 2 (Part 8B.2 Control 15)",
        "section_ref": "8B.2",
        "source_chapter_key_override": "section-a-part-8-mixed-use",
    },
    {
        "dev_type": "mixed_use",
        "control_type": "car_parking",
        "value_min": 0.167,
        "value_max": 0.167,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "Mixed use within 400m station: visitor 1 space per 6 apartments (Part 8B.2 Control 16)",
        "section_ref": "8B.2",
        "source_chapter_key_override": "section-a-part-8-mixed-use",
    },

    # ─ Mixed Use — Part 22R.1 general rates (same as RFB) ─
    {
        "dev_type": "mixed_use",
        "control_type": "car_parking",
        "value_min": 0.5,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "studio; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB/mixed use studio: 0.5 spaces per unit (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "mixed_use",
        "control_type": "car_parking",
        "value_min": 1,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "1 bedroom; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB/mixed use 1 bedroom: 1 space per unit (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "mixed_use",
        "control_type": "car_parking",
        "value_min": 1.25,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "2 bedrooms; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB/mixed use 2 bedroom: 1.25 spaces per unit (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "mixed_use",
        "control_type": "car_parking",
        "value_min": 2,
        "value_max": None,
        "unit": "spaces/dwelling",
        "condition": "3 or more bedrooms; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB/mixed use 3 bedroom: 2 spaces per unit (Part 22R.1)",
        "section_ref": "22R.1",
    },
    {
        "dev_type": "mixed_use",
        "control_type": "car_parking",
        "value_min": 0.25,
        "value_max": None,
        "unit": "visitor_spaces/dwelling",
        "condition": "visitor parking; not within 400m of railway station",
        "applicability": "universal_residential",
        "source_text": "RFB/mixed use visitor: 1 space per 4 units (Part 22R.1)",
        "section_ref": "22R.1",
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

    for row in PARKING_ROWS:
        chapter_key = row.pop("source_chapter_key_override", SOURCE_CHAPTER_KEY)

        cur.execute("""
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s AND dev_type = %s AND control_type = %s
              AND COALESCE(condition, '') = COALESCE(%s, '')
              AND COALESCE(value_min::text, '') = COALESCE(%s::text, '')
              AND is_current = TRUE
        """, (LGA, row["dev_type"], row["control_type"],
              row.get("condition"), row.get("value_min")))
        if cur.fetchone():
            print(f"  SKIP dup: {row['dev_type']} "
                  f"min={row.get('value_min')} cond={(row.get('condition') or '')[:50]}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  DRY-RUN: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} max={row.get('value_max')} "
                  f"unit={row['unit']} cond={(row.get('condition') or '')[:55]}")
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
                  DCP_VERSION, EXTRACTION_METHOD, chapter_key))
            print(f"  INSERT: {row['dev_type']} min={row.get('value_min')} "
                  f"max={row.get('value_max')} unit={row['unit']}")
            inserted += 1

    if not args.dry_run:
        conn.commit()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (duplicates)")

    if not args.dry_run and inserted > 0:
        cur.execute("""
            SELECT dev_type, count(*) as n
            FROM dcp_setback_controls
            WHERE lga = %s AND control_type = 'car_parking' AND is_current = TRUE
            GROUP BY dev_type ORDER BY dev_type
        """, (LGA,))
        print(f"\nKu-ring-gai parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30s} {r['n']} rows")

    conn.close()


if __name__ == "__main__":
    main()
