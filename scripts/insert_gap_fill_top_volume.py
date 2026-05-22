#!/usr/bin/env python3
"""
Gap-fill missing DCP controls for top-volume LGAs.

Fills verified numeric values where DCP has them, and literal DCP citations
(value_min=NULL) where the DCP defers, uses different terminology, or controls
density via LEP FSR rather than DCP site coverage.

Priority order: Blacktown (888 DAs), Northern Beaches (822), The Hills (750),
City of Sydney (326), Camden (324), Randwick (305).

Usage:
    python scripts/insert_gap_fill_top_volume.py --dry-run
    python scripts/insert_gap_fill_top_volume.py
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

EXTRACTION_METHOD = "manual"

GAP_ROWS = [
    # ══════════════════════════════════════════════════════════════
    # BLACKTOWN (888 DAs/yr) — missing: max_site_coverage
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "blacktown",
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_max": 60,
        "unit": "%",
        "condition": "Maximum 60% site coverage; upper storey sub-limits apply "
                     "(<=40% for lots <=375m2, <=35% for lots >375m2)",
        "applicability": "universal_residential",
        "source_text": "Blacktown DCP 2015 Part C s3.5.1: Maximum site coverage of "
                       "60% of total site area for dwelling houses. Upper storey "
                       "limitations: maximum 40% for allotments 375m2 or less, "
                       "maximum 35% for allotments greater than 375m2.",
        "section_ref": "s3.5.1",
        "source_chapter_key": "part-c-development-residential",
        "dcp_version": "v2015-current",
        "needs_review": False,
    },

    # ══════════════════════════════════════════════════════════════
    # NORTHERN BEACHES (822 DAs/yr) — missing: deep_soil_min
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "northern_beaches",
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": None,
        "unit": "%",
        "condition": "No separate deep soil control; equivalent is 40% landscaped "
                     "open space (Control D1). Warringah DCP does not use 'deep "
                     "soil zone' terminology for dwelling houses",
        "applicability": "universal_residential",
        "source_text": "Warringah DCP 2011 Control D1 'Landscaped Open Space and "
                       "Bushland Setting': requires 40% of the site to be maintained "
                       "as landscaped open space. No separately quantified 'deep soil "
                       "zone' percentage for dwelling houses — deep soil is embedded "
                       "in the landscaped open space requirement.",
        "section_ref": "D1",
        "source_chapter_key": "warringah-dcp-2011-full",
        "dcp_version": "v2011-amendment-3-feb2013",
        "needs_review": False,
    },

    # ══════════════════════════════════════════════════════════════
    # THE HILLS (750 DAs/yr) — missing: max_site_coverage,
    #   landscaping_min, deep_soil_min
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "the_hills",
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_max": 60,
        "unit": "%",
        "condition": "Maximum 60% of total site area; dwelling footprint sub-limit "
                     "of 45% of site area. E4 Environmental Living / pink-shaded "
                     "land: maximum 30%",
        "applicability": "universal_residential",
        "source_text": "The Hills DCP 2012 Part B Section 2 (Residential): Maximum "
                       "site coverage of 60% of total site area for all residential "
                       "zones. Dwelling building footprint must be no more than 45% "
                       "of site area. Exception: E4 Environmental Living zone and "
                       "land shown pink on Map Sheets — maximum 30%.",
        "section_ref": "part-b-s2-residential",
        "source_chapter_key": "part-b-s2-residential",
        "dcp_version": "v2012-aug2024",
        "needs_review": False,
    },
    {
        "lga": "the_hills",
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 40,
        "unit": "%",
        "condition": "Minimum 40% of total site area as landscape area",
        "applicability": "universal_residential",
        "source_text": "The Hills DCP 2012 Part B Section 2 (Residential): Minimum "
                       "40% of total site area must be provided as landscape area "
                       "for residential development.",
        "section_ref": "part-b-s2-residential",
        "source_chapter_key": "part-b-s2-residential",
        "dcp_version": "v2012-aug2024",
        "needs_review": False,
    },
    {
        "lga": "the_hills",
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": None,
        "unit": "%",
        "condition": "No separate deep soil control; DCP uses 'landscaped area' "
                     "(40% of site) which subsumes deep soil requirement",
        "applicability": "universal_residential",
        "source_text": "The Hills DCP 2012 Part B Section 2 (Residential): Uses "
                       "'landscaped area' terminology (minimum 40% of site) rather "
                       "than a separately quantified 'deep soil zone'. Deep soil "
                       "planting is implied within the landscaping requirement but "
                       "not given its own numeric minimum.",
        "section_ref": "part-b-s2-residential",
        "source_chapter_key": "part-b-s2-residential",
        "dcp_version": "v2012-aug2024",
        "needs_review": False,
    },

    # ══════════════════════════════════════════════════════════════
    # CITY OF SYDNEY (326 DAs/yr) — missing: max_site_coverage
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "city_of_sydney",
        "dev_type": "dwelling_house",
        "control_type": "max_site_coverage",
        "value_max": None,
        "unit": "%",
        "condition": "No general DCP site coverage control; density controlled by "
                     "FSR in Sydney LEP 2012. Rosebery Estate precinct only: "
                     "50% regular lots, 65% corner lots (s5.6.2)",
        "applicability": "universal_residential",
        "source_text": "Sydney DCP 2012: No general maximum site coverage control "
                       "for dwelling houses across the LGA. Site density is "
                       "controlled through Floor Space Ratio (FSR) set in Sydney "
                       "LEP 2012 per zone/precinct. The only DCP site coverage "
                       "control is precinct-specific: Section 5.6.2 Rosebery Estate "
                       "— 50% for regular allotments, 65% for corner lots.",
        "section_ref": "s4.1-s5.6.2",
        "source_chapter_key": "section-4-dcp-2012",
        "dcp_version": "v2012-amendment-2023",
        "needs_review": False,
    },

    # ══════════════════════════════════════════════════════════════
    # CAMDEN (324 DAs/yr) — missing: rear_setback, car_parking,
    #   deep_soil_min, landscaping_min
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "camden",
        "dev_type": "dwelling_house",
        "control_type": "rear_setback",
        "value_min": 4,
        "unit": "m",
        "condition": "Single storey: 4m rear setback",
        "applicability": "universal_residential",
        "source_text": "Camden DCP 2019 Part 4 Table 4-2: Rear setback — single "
                       "storey dwelling: minimum 4m.",
        "section_ref": "part-4-table-4-2",
        "source_chapter_key": "part-4-residential-dwelling-controls",
        "dcp_version": "v2019-current",
        "needs_review": False,
    },
    {
        "lga": "camden",
        "dev_type": "dwelling_house",
        "control_type": "rear_setback",
        "value_min": 6,
        "unit": "m",
        "condition": "Two storey (two-storey component): 6m rear setback",
        "applicability": "universal_residential",
        "source_text": "Camden DCP 2019 Part 4 Table 4-2: Rear setback — two "
                       "storey dwelling (two-storey component): minimum 6m.",
        "section_ref": "part-4-table-4-2",
        "source_chapter_key": "part-4-residential-dwelling-controls",
        "dcp_version": "v2019-current",
        "needs_review": False,
    },
    {
        "lga": "camden",
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 1,
        "unit": "spaces/dwelling",
        "condition": "1-2 bedroom dwelling: minimum 1 car space",
        "applicability": "universal_residential",
        "source_text": "Camden DCP 2019 Part 4 Parking, Garages and Site Access: "
                       "1-2 bedroom dwelling — minimum 1 car parking space. At "
                       "least 1 space must be behind the building line where "
                       "accessed from the front boundary.",
        "section_ref": "part-4-parking",
        "source_chapter_key": "part-4-residential-dwelling-controls",
        "dcp_version": "v2019-current",
        "needs_review": False,
    },
    {
        "lga": "camden",
        "dev_type": "dwelling_house",
        "control_type": "car_parking",
        "value_min": 2,
        "unit": "spaces/dwelling",
        "condition": "3+ bedroom dwelling: minimum 2 car spaces",
        "applicability": "universal_residential",
        "source_text": "Camden DCP 2019 Part 4 Parking, Garages and Site Access: "
                       "3 or more bedroom dwelling — minimum 2 car parking spaces. "
                       "At least 1 space must be behind the building line where "
                       "accessed from the front boundary.",
        "section_ref": "part-4-parking",
        "source_chapter_key": "part-4-residential-dwelling-controls",
        "dcp_version": "v2019-current",
        "needs_review": False,
    },
    {
        "lga": "camden",
        "dev_type": "dwelling_house",
        "control_type": "landscaping_min",
        "value_min": 30,
        "unit": "%",
        "condition": "Minimum 30% of site area as landscaped area; areas <1.5m "
                     "wide excluded; min 40% of front setback landscaped",
        "applicability": "universal_residential",
        "source_text": "Camden DCP 2019 Part 4 Landscaped Area: Minimum 30% of "
                       "site area must be landscaped area. Areas less than 1.5m "
                       "wide are excluded from calculation. Minimum 40% of front "
                       "setback (from building line) must be landscaped.",
        "section_ref": "part-4-landscaping",
        "source_chapter_key": "part-4-residential-dwelling-controls",
        "dcp_version": "v2019-current",
        "needs_review": False,
    },
    {
        "lga": "camden",
        "dev_type": "dwelling_house",
        "control_type": "deep_soil_min",
        "value_min": None,
        "unit": "%",
        "condition": "No separate deep soil control; DCP uses 'landscaped area' "
                     "(30% of site). Deep soil planting areas must be provided "
                     "within landscaped area but no separate numeric minimum",
        "applicability": "universal_residential",
        "source_text": "Camden DCP 2019 Part 4: Uses 'landscaped area' terminology "
                       "(minimum 30% of site). States sufficient area for 'deep "
                       "soil planting areas' must be provided within the landscaped "
                       "area but gives no separate numeric minimum for deep soil.",
        "section_ref": "part-4-landscaping",
        "source_chapter_key": "part-4-residential-dwelling-controls",
        "dcp_version": "v2019-current",
        "needs_review": False,
    },

    # ══════════════════════════════════════════════════════════════
    # RANDWICK (305 DAs/yr) — missing: rear_setback
    # ══════════════════════════════════════════════════════════════
    {
        "lga": "randwick",
        "dev_type": "dwelling_house",
        "control_type": "rear_setback",
        "value_min": 8,
        "unit": "m",
        "condition": "25% of allotment depth or 8m, whichever is lesser; does not "
                     "apply to corner allotments",
        "applicability": "universal_residential",
        "source_text": "Randwick Comprehensive DCP 2013 Part C1 s3.3.3 Rear "
                       "Setbacks: 'The minimum rear setback must be 25% of "
                       "allotment depth or 8m, whichever is the lesser.' Rear "
                       "setback controls do not apply to corner allotments. "
                       "Garages, carports, outbuildings, pools, above-ground "
                       "tanks, and unroofed decks/terraces may encroach upon "
                       "the required rear setback.",
        "section_ref": "C1-s3.3.3",
        "source_chapter_key": "part-c1-low-density-residential",
        "dcp_version": "v2013-current",
        "needs_review": False,
    },
]


def main() -> None:
    parser = argparse.ArgumentParser(description="Gap-fill controls for top-volume LGAs")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be inserted without writing to DB")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    inserted = 0
    skipped = 0
    errors = 0

    for row in GAP_ROWS:
        lga = row["lga"]
        dev_type = row["dev_type"]
        control_type = row["control_type"]
        condition = row["condition"]

        # Dedup check
        condition_prefix = condition[:30]
        cur.execute(
            """
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s
              AND control_type = %s
              AND dev_type = %s
              AND condition LIKE %s
              AND is_current = TRUE
            """,
            (lga, control_type, dev_type, condition_prefix + "%"),
        )
        if cur.fetchone():
            skipped += 1
            if args.dry_run:
                print(f"  SKIP (exists): {lga} / {control_type} / {condition_prefix}...")
            continue

        # Determine which value column to use
        val = row.get("value_min") if row.get("value_min") is not None else row.get("value_max")
        val_col = "value_min" if "value_min" in row else "value_max"

        if args.dry_run:
            val_str = f"{val}" if val is not None else "NULL"
            print(f"  INSERT: {lga} / {control_type} / {dev_type} / {val_str} {row['unit']}")
            print(f"          {condition[:80]}")
            inserted += 1
            continue

        try:
            cur.execute(
                f"""
                INSERT INTO dcp_setback_controls (
                    lga, dev_type, control_type, {val_col}, unit,
                    condition, applicability, source_text, section_ref,
                    source_chapter_key, dcp_version, is_current,
                    extraction_method, needs_review, review_reason
                ) VALUES (
                    %s, %s, %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, TRUE,
                    %s, %s, %s
                )
                """,
                (
                    lga,
                    dev_type,
                    control_type,
                    val,
                    row["unit"],
                    condition,
                    row.get("applicability", "universal_residential"),
                    row["source_text"],
                    row["section_ref"],
                    row["source_chapter_key"],
                    row["dcp_version"],
                    EXTRACTION_METHOD,
                    row.get("needs_review", False),
                    row.get("review_reason"),
                ),
            )
            inserted += 1
        except Exception as e:
            errors += 1
            print(f"  ERROR: {lga} / {control_type}: {e}")
            conn.rollback()

    if not args.dry_run and errors == 0:
        conn.commit()
        print(f"\nCommitted {inserted} rows.")
    elif args.dry_run:
        print(f"\n[DRY RUN] Would insert {inserted} rows, skip {skipped} existing.")
    else:
        print(f"\n{errors} errors — transaction rolled back. No rows written.")

    # Summary
    print(f"\n{'='*70}")
    print(f"{'LGA':<22} {'Control':<22} {'Value':>8} {'Status'}")
    print(f"{'-'*70}")
    for row in GAP_ROWS:
        val = row.get("value_min") if row.get("value_min") is not None else row.get("value_max")
        val_str = f"{val}" if val is not None else "NULL"
        status = "REVIEW" if row.get("needs_review") else ("NO_RATE" if val is None else "VERIFIED")
        print(f"{row['lga']:<22} {row['control_type']:<22} {val_str:>8} {status}")
    print(f"{'-'*70}")
    print(f"Total rows: {len(GAP_ROWS)}")
    print(f"Inserted: {inserted}, Skipped: {skipped}, Errors: {errors}")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
