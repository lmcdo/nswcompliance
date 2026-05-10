#!/usr/bin/env python3
"""
Insert Canterbury-Bankstown parking controls from DCP 2023 Chapter 3.2.

Source: Canterbury-Bankstown DCP 2023, Chapter 3.2 Parking (Amended August 2025)
OCR: Mistral OCR 2026-05-10, pages 6-13 (Off-Street Parking Schedule)

Usage:
    python scripts/insert_cb_parking.py --dry-run
    python scripts/insert_cb_parking.py
"""
import os, sys, argparse
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

LGA = "canterbury_bankstown"
DCP_VERSION = "v2023-amendment-8-aug2025"
SOURCE_CHAPTER_KEY = "ch3-2-parking"
EXTRACTION_METHOD = "mistral_ocr"

# Residential parking rates from OCR pages 6-12
# Each dict = one row in dcp_setback_controls
PARKING_ROWS = [
    # --- Dwelling houses ---
    dict(dev_type="dwelling_house", control_type="car_parking",
         value_min=2, unit="spaces/dwelling", condition=None,
         applicability="universal_residential",
         source_text="Dwelling houses: 2 car spaces",
         section_ref="ch3-2-s2-schedule"),

    # --- Secondary dwellings ---
    dict(dev_type="secondary_dwelling", control_type="car_parking",
         value_min=1, unit="spaces/dwelling", condition=None,
         applicability="secondary_dwelling_specific",
         source_text="Secondary dwellings: 1 car space",
         section_ref="ch3-2-s2-schedule"),

    # --- Dual occupancy / semi-detached ---
    dict(dev_type="dual_occupancy", control_type="car_parking",
         value_min=1, unit="spaces/dwelling", condition="2 or less bedrooms",
         applicability="universal_residential",
         source_text="Dual occupancies/semi-detached dwellings: 1 car space per 2 or less bedrooms",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="dual_occupancy", control_type="car_parking",
         value_min=2, unit="spaces/dwelling", condition="3 or more bedrooms",
         applicability="universal_residential",
         source_text="Dual occupancies/semi-detached dwellings: 2 car spaces per 3 or more bedrooms",
         section_ref="ch3-2-s2-schedule"),

    # --- Attached dwellings ---
    dict(dev_type="attached_dwelling", control_type="car_parking",
         value_min=1, unit="spaces/dwelling", condition="studio or 1 bedroom",
         applicability="universal_residential",
         source_text="Attached dwellings: Studio or 1 bedroom: 1 car space per dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="attached_dwelling", control_type="car_parking",
         value_min=1.5, unit="spaces/dwelling", condition="2 bedroom",
         applicability="universal_residential",
         source_text="Attached dwellings: 2 bedroom: 1.5 car space per dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="attached_dwelling", control_type="car_parking",
         value_min=2, unit="spaces/dwelling", condition="3 bedroom or more",
         applicability="universal_residential",
         source_text="Attached dwellings: 3 bedroom or more: 2 car spaces per dwelling",
         section_ref="ch3-2-s2-schedule"),

    # --- Multi dwelling housing / terraces ---
    dict(dev_type="multi_dwelling_housing", control_type="car_parking",
         value_min=1, unit="spaces/dwelling", condition="studio or 1 bedroom",
         applicability="universal_residential",
         source_text="Multi dwelling housing: Studio or 1 bedroom: 1 car space per dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="multi_dwelling_housing", control_type="car_parking",
         value_min=1.5, unit="spaces/dwelling", condition="2 bedroom",
         applicability="universal_residential",
         source_text="Multi dwelling housing: 2 bedroom: 1.5 car space per dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="multi_dwelling_housing", control_type="car_parking",
         value_min=2, unit="spaces/dwelling", condition="3 bedroom or more",
         applicability="universal_residential",
         source_text="Multi dwelling housing: 3 bedroom or more: 2 car spaces per dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="multi_dwelling_housing", control_type="car_parking",
         value_min=0.2, unit="visitor_spaces/dwelling", condition="visitor parking",
         applicability="universal_residential",
         source_text="Multi dwelling housing: 1 visitor car space per 5 dwellings",
         section_ref="ch3-2-s2-schedule"),

    # --- Residential flat buildings (Zones R4, E1, E3) ---
    dict(dev_type="residential_flat_building", control_type="car_parking",
         value_min=1, unit="spaces/dwelling", condition="1 bedroom; Zones R4, E1, E3",
         applicability="universal_residential",
         source_text="RFB Zones R4, E1, E3: 1 car space per 1 bedroom dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="residential_flat_building", control_type="car_parking",
         value_min=1.2, unit="spaces/dwelling", condition="2 bedroom; Zones R4, E1, E3",
         applicability="universal_residential",
         source_text="RFB Zones R4, E1, E3: 1.2 car spaces per 2 bedroom dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="residential_flat_building", control_type="car_parking",
         value_min=1.5, unit="spaces/dwelling", condition="3+ bedroom; Zones R4, E1, E3",
         applicability="universal_residential",
         source_text="RFB Zones R4, E1, E3: 1.5 car spaces per 3 or more bedroom dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="residential_flat_building", control_type="car_parking",
         value_min=0.2, unit="visitor_spaces/dwelling", condition="visitor; Zones R4, E1, E3",
         applicability="universal_residential",
         source_text="RFB Zones R4, E1, E3: 1 visitor car space per 5 dwellings",
         section_ref="ch3-2-s2-schedule"),

    # --- RFB (Zones E2, MU1) — range-based ---
    dict(dev_type="residential_flat_building", control_type="car_parking",
         value_min=1, value_max=3, unit="spaces/dwelling",
         condition="Zones E2, MU1 (min 1, max 3)",
         applicability="universal_residential",
         source_text="RFB Zones E2, MU1: Minimum 1 car space and maximum 3 car spaces per dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="residential_flat_building", control_type="car_parking",
         value_min=0.2, unit="visitor_spaces/dwelling", condition="visitor; Zones E2, MU1",
         applicability="universal_residential",
         source_text="RFB Zones E2, MU1: 1 visitor car space per 5 dwellings",
         section_ref="ch3-2-s2-schedule"),

    # --- Boarding houses ---
    dict(dev_type="boarding_house", control_type="car_parking",
         value_min=0.5, unit="spaces/room", condition="per boarding room; plus 1 space per resident employee",
         applicability="universal_residential",
         source_text="Boarding houses: 0.5 car spaces per boarding room; and 1 car space for each person employed in connection with the development and who is resident on the site",
         section_ref="ch3-2-s2-schedule"),

    # --- Shop top housing (former Bankstown LGA) ---
    # Zone R4
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=1, unit="spaces/commercial_premise",
         condition="former Bankstown LGA; Zone R4; plus RFB rate for residential",
         applicability="universal_residential",
         source_text="Shop top housing former Bankstown Zone R4: 1 car space per commercial premises/health services facility in addition to RFB parking",
         section_ref="ch3-2-s2-schedule"),
    # Zone E1
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=1, unit="spaces/dwelling",
         condition="former Bankstown LGA; Zone E1",
         applicability="universal_residential",
         source_text="Shop top housing former Bankstown Zone E1: 1 car space per dwelling",
         section_ref="ch3-2-s2-schedule"),
    # Zone MU1
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=1, value_max=3, unit="spaces/dwelling",
         condition="former Bankstown LGA; Zone MU1 (min 1, max 3); plus 1 visitor per 5 dwellings",
         applicability="universal_residential",
         source_text="Shop top housing former Bankstown Zone MU1: Minimum 1 car space and maximum 3 car spaces per dwelling; and 1 visitor car space per 5 dwellings",
         section_ref="ch3-2-s2-schedule"),

    # --- Shop top housing (former Canterbury LGA) — centre-specific rates ---
    # Belmore, Campsie, Canterbury, Lakemba
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=0.25, unit="spaces/dwelling",
         condition="former Canterbury LGA; Belmore/Campsie/Canterbury/Lakemba centres; studio",
         applicability="universal_residential",
         source_text="Shop top housing former Canterbury Belmore/Campsie/Canterbury/Lakemba: Studio: 0.25 car space per dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=0.8, unit="spaces/dwelling",
         condition="former Canterbury LGA; Belmore/Campsie/Canterbury/Lakemba centres; 1 bedroom",
         applicability="universal_residential",
         source_text="Shop top housing former Canterbury Belmore/Campsie/Canterbury/Lakemba: 1 bedroom: 0.8 car space per dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=1, unit="spaces/dwelling",
         condition="former Canterbury LGA; Belmore/Campsie/Canterbury/Lakemba centres; 2+ bedroom; no visitor parking required",
         applicability="universal_residential",
         source_text="Shop top housing former Canterbury Belmore/Campsie/Canterbury/Lakemba: 2 bedroom: 1 car space; 3+ bedroom: 1 car space; Visitor: not required",
         section_ref="ch3-2-s2-schedule"),

    # Earlwood, Hurlstone Park, Narwee, Punchbowl, Wiley Park
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=0.5, unit="spaces/dwelling",
         condition="former Canterbury LGA; Earlwood/Hurlstone Park/Narwee/Punchbowl/Wiley Park; studio",
         applicability="universal_residential",
         source_text="Shop top housing former Canterbury Earlwood etc: Studio: 0.5 car space per dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=1, unit="spaces/dwelling",
         condition="former Canterbury LGA; Earlwood/Hurlstone Park/Narwee/Punchbowl/Wiley Park; 1-3+ bedroom; visitor: 0.15/dwelling",
         applicability="universal_residential",
         source_text="Shop top housing former Canterbury Earlwood etc: 1 bed: 1 space; 2 bed: 1 space; 3+ bed: 1 space; Visitor: 0.15 per dwelling",
         section_ref="ch3-2-s2-schedule"),

    # Other locations former Canterbury
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=0.67, unit="spaces/dwelling",
         condition="former Canterbury LGA; other locations; studio",
         applicability="universal_residential",
         source_text="Shop top housing former Canterbury other: Studio: 0.67 car space per dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=1, unit="spaces/dwelling",
         condition="former Canterbury LGA; other locations; 1 bedroom",
         applicability="universal_residential",
         source_text="Shop top housing former Canterbury other: 1 bedroom: 1 car space per dwelling",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=1.2, unit="spaces/dwelling",
         condition="former Canterbury LGA; other locations; 2 bedroom (0.2 space as common property)",
         applicability="universal_residential",
         source_text="Shop top housing former Canterbury other: 2 bedroom: 1.2 car space per dwelling (the 0.2 space to remain as common property)",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="shop_top_housing", control_type="car_parking",
         value_min=2, unit="spaces/dwelling",
         condition="former Canterbury LGA; other locations; 3+ bedroom; visitor: 0.2/dwelling",
         applicability="universal_residential",
         source_text="Shop top housing former Canterbury other: 3+ bedroom: 2 car spaces; Visitor: 0.2 per dwelling",
         section_ref="ch3-2-s2-schedule"),

    # --- Seniors housing ---
    dict(dev_type="seniors_housing", control_type="car_parking",
         value_min=0.1, unit="spaces/bed",
         condition="residential care facility (0.067 if dementia-only); plus 1 space per 2 on-duty staff; plus 1 ambulance space",
         applicability="universal_residential",
         source_text="Seniors housing residential care: 1 car space per 10 beds (or 1 per 15 for dementia); 1 per 2 on-duty staff; 1 ambulance space",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="seniors_housing", control_type="car_parking",
         value_min=0.5, unit="spaces/bedroom",
         condition="self-contained dwellings (non-social housing provider)",
         applicability="universal_residential",
         source_text="Seniors housing self-contained: 0.5 car space per bedroom (non-social housing provider)",
         section_ref="ch3-2-s2-schedule"),
    dict(dev_type="seniors_housing", control_type="car_parking",
         value_min=0.2, unit="spaces/dwelling",
         condition="self-contained dwellings (social housing provider)",
         applicability="universal_residential",
         source_text="Seniors housing self-contained: 1 car space per 5 dwellings (social housing provider)",
         section_ref="ch3-2-s2-schedule"),

    # --- Group homes ---
    dict(dev_type="group_home", control_type="car_parking",
         value_min=2, unit="spaces/dwelling", condition=None,
         applicability="universal_residential",
         source_text="Group homes: 2 car spaces",
         section_ref="ch3-2-s2-schedule"),
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
        # Deduplicate check
        cur.execute("""
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s AND dev_type = %s AND control_type = %s
              AND COALESCE(condition,'') = COALESCE(%s,'')
              AND COALESCE(value_min::text,'') = COALESCE(%s::text,'')
              AND is_current = TRUE
        """, (LGA, row["dev_type"], row["control_type"],
              row.get("condition"), row.get("value_min")))
        if cur.fetchone():
            print(f"  SKIP dup: {row['dev_type']} {row['control_type']} min={row.get('value_min')} cond={(row.get('condition') or '')[:40]}")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  DRY-RUN: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} max={row.get('value_max','')} "
                  f"unit={row['unit']} cond={(row.get('condition') or '')[:50]}")
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
            inserted += 1
            print(f"  INSERT: {row['dev_type']} {row['control_type']} "
                  f"min={row.get('value_min')} unit={row['unit']}")

    if not args.dry_run and inserted > 0:
        conn.commit()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (duplicates)")

    # Summary
    if not args.dry_run:
        cur.execute("""
            SELECT dev_type, count(*) as rows
            FROM dcp_setback_controls
            WHERE lga = %s AND control_type = 'car_parking' AND is_current = TRUE
            GROUP BY dev_type
            ORDER BY dev_type
        """, (LGA,))
        print(f"\nCanterbury-Bankstown parking controls by dev_type:")
        for r in cur.fetchall():
            print(f"  {r['dev_type']:30} {r['rows']} rows")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
