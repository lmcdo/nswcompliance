#!/usr/bin/env python3
"""
Insert solar access hour requirements from council DCPs into dcp_setback_controls.

Solar access is one of the most standardised DCP controls in NSW. Most councils
require 3 hours of direct sunlight between 9am–3pm on 21 June (mid-winter
solstice) to living areas and private open space. Some councils set higher
thresholds (4 hours) or use different time windows.

Sources verified per council from DCP PDFs and published DCP text:
  - Camden: DCP s4.2.8 — 3h, 9am–3pm, 21 June
  - Canterbury-Bankstown: DCP Ch5 — 3h, 8am–4pm living / 9am–5pm POS (equinox for POS)
  - Ku-ring-gai: DCP Part 4C.5 — 4h, 9am–3pm, 21 June
  - Hornsby: DCP Sunlight Access — 3h, 9am–3pm, 22 June
  - Penrith: DCP Part D2 — 3h, 9am–3pm, 22 June
  - City of Sydney: DCP Section 4 — 2h, 9am–3pm, 21 June
  - Georges River: Hurstville DCP DS6.1 — 3h, 9am–3pm, 22 June
  - Sutherland Shire: LEP 2015 — 4h, 9am–3pm, 21 June
  - The Hills Shire: DCP Part B s3.11 — 4h (RFBs), 9am–3pm, 21 June
  - Randwick: DCP 2013 — 3h, 8am–4pm, 21 June
  - Fairfield: DCP 2013 — 3h, 9am–3pm, mid-winter
  - Blacktown: DCP 2015 — 4h, 9am–3pm, 21 June

Councils marked needs_review=TRUE have the standard 3h/9am–3pm/21 June pattern
applied based on the dominant NSW standard but require PDF-level verification.

Usage:
    python scripts/insert_solar_access_hours.py --dry-run
    python scripts/insert_solar_access_hours.py
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

# ─────────────────────────────────────────────────────────────────────
# Per-council solar access data.
# Each entry: (lga, value_min, condition, source_text, section_ref,
#              dcp_version, source_chapter_key, needs_review)
#
# needs_review=True means the standard pattern was applied but the
# specific DCP section has not been PDF-verified yet.
# ─────────────────────────────────────────────────────────────────────

SOLAR_ROWS = [
    # ══════════════════════════════════════════════════════════════
    # VERIFIED — values confirmed from DCP text
    # ══════════════════════════════════════════════════════════════

    # Ashfield — Inner West DCP (Ashfield) 2016, Chapter A Part 4
    {
        "lga": "ashfield", "value_min": 3, "needs_review": False,
        "condition": "9am–3pm 21 June to living areas and 50% of POS; must not reduce solar to adjoining properties below 3h",
        "source_text": "A minimum of 3 hours of direct sunlight between 9am and 3pm at the winter solstice to living areas and principal private open space (Chapter A Part 4)",
        "section_ref": "a-part4-solar-access",
        "dcp_version": "v2016", "source_chapter_key": "ashfield-dcp-2016-chapter-a",
    },
    # Leichhardt — Inner West DCP (Leichhardt) 2013, Part B s4
    {
        "lga": "leichhardt", "value_min": 3, "needs_review": False,
        "condition": "9am–3pm 21 June to habitable rooms and POS; not reduce adjoining below 3h",
        "source_text": "Minimum 3 hours direct sunlight between 9am and 3pm on 21 June to habitable rooms and private open space (Part B Section 4)",
        "section_ref": "b-s4-solar-access",
        "dcp_version": "v2013", "source_chapter_key": "leichhardt-dcp-2013-part-b",
    },
    # Marrickville — Inner West DCP (Marrickville) 2011, Part 2.7
    {
        "lga": "marrickville", "value_min": 3, "needs_review": False,
        "condition": "9am–3pm 21 June to living areas and 50% of POS of subject and adjoining dwellings",
        "source_text": "A minimum of 3 hours of direct sunlight between 9am and 3pm at the winter solstice to at least one living area and 50% of required POS (Part 2 Section 2.7)",
        "section_ref": "part2-s2.7-solar",
        "dcp_version": "v2011", "source_chapter_key": "marrickville-dcp-2011-part-2",
    },
    # Camden — DCP s4.2.8
    {
        "lga": "camden", "value_min": 3, "needs_review": False,
        "condition": "9am–3pm 21 June to at least one living area and 50% of POS of subject and adjoining dwellings",
        "source_text": "A minimum of 3 hours of direct sunlight between 9am and 3pm at the winter solstice (21 June) to at least one living area and 50% of POS (s4.2.8)",
        "section_ref": "s4.2.8",
        "dcp_version": "v2019", "source_chapter_key": "camden-dcp-s4-residential",
    },
    # Canterbury-Bankstown — DCP 2023 Ch5 (living areas: 8am–4pm; POS: equinox 9am–5pm)
    {
        "lga": "canterbury_bankstown", "value_min": 3, "needs_review": False,
        "condition": "8am–4pm mid-winter solstice to living areas; 50% of POS must receive 3h between 9am–5pm at the equinox",
        "source_text": "Living areas: 3 hours between 8am and 4pm at mid-winter solstice. POS: 50% must receive 3 hours between 9am and 5pm at the equinox (Ch5)",
        "section_ref": "ch5-residential",
        "dcp_version": "v2023", "source_chapter_key": "cb-dcp-2023-ch5",
    },
    # Ku-ring-gai — DCP Part 4C.5 (4 hours — higher standard)
    {
        "lga": "ku_ring_gai", "value_min": 4, "needs_review": False,
        "condition": "9am–3pm 21 June to north-facing windows, all living areas, and principal POS including pools and patios; must maintain 4h to adjoining properties",
        "source_text": "A minimum of 4 hours of direct sunlight between 9am and 3pm on 21 June to living areas and principal private open space (Part 4C.5)",
        "section_ref": "part4c-s5",
        "dcp_version": "v2024", "source_chapter_key": "krg-dcp-2024-part4c",
    },
    # Hornsby — DCP 2024 Sunlight Access section
    {
        "lga": "hornsby", "value_min": 3, "needs_review": False,
        "condition": "9am–3pm 22 June to 50% of required POS; must maintain to 50% of adjoining POS",
        "source_text": "3 hours unobstructed sunlight between 9am and 3pm on 22 June to 50% of required principal private open space (DCP 2024)",
        "section_ref": "s3-sunlight-access",
        "dcp_version": "v2024-jun2025", "source_chapter_key": "hornsby-dcp-2024-part3",
    },
    # Penrith — DCP 2014 Part D2
    {
        "lga": "penrith", "value_min": 3, "needs_review": False,
        "condition": "9am–3pm 22 June to 50% of required POS; must maintain to 50% of adjoining POS",
        "source_text": "3 hours direct sunlight between 9am and 3pm on 22 June to 50% of required principal private open space (Part D2)",
        "section_ref": "d2-solar-access",
        "dcp_version": "v2014-feb2026", "source_chapter_key": "penrith-dcp-2014-part-d2",
    },
    # City of Sydney — DCP 2012 Section 4 (2 hours — lower standard)
    {
        "lga": "city_of_sydney", "value_min": 2, "needs_review": False,
        "condition": "9am–3pm 21 June to at least 1m² of living room windows and 50% of minimum POS; must not increase overshadowing where already <2h",
        "source_text": "A minimum of 2 hours of direct sunlight between 9am and 3pm at mid-winter to living room windows and 50% of required POS (Section 4)",
        "section_ref": "section4-solar",
        "dcp_version": "v2012", "source_chapter_key": "sydney-dcp-2012-section4",
    },
    # Georges River — Hurstville DCP DS6.1
    {
        "lga": "georges_river", "value_min": 3, "needs_review": False,
        "condition": "9am–3pm 22 June to main living area windows and adjoining POS",
        "source_text": "3 hours direct sunlight between 9am and 3pm on 22 June to windows of main living areas and adjoining principal private open space (DS6.1)",
        "section_ref": "ds6.1",
        "dcp_version": "v-hurstville", "source_chapter_key": "georges-river-hurstville-dcp",
    },
    # Sutherland Shire — LEP 2015 (4 hours — higher, and notably in LEP)
    {
        "lga": "sutherland_shire", "value_min": 4, "needs_review": False,
        "condition": "9am–3pm 21 June to at least 50% of outdoor POS at ground level",
        "source_text": "4 hours of direct sunlight between 9am and 3pm on 21 June to at least 50% of outdoor private open space at ground level (LEP 2015)",
        "section_ref": "lep-schedule-solar",
        "dcp_version": "v-lep-2015", "source_chapter_key": "sutherland-lep-2015",
    },
    # The Hills Shire — DCP 2012 Part B s3.11 (4 hours for RFBs)
    {
        "lga": "the_hills", "value_min": 4, "needs_review": False,
        "condition": "9am–3pm 21 June to windows of primary living areas (residential flat buildings)",
        "source_text": "4 hours of direct sunlight to windows of primary living areas between 9am and 3pm on 21 June (Part B s3.11, RFBs)",
        "section_ref": "part-b-s3.11",
        "dcp_version": "v2012", "source_chapter_key": "the-hills-dcp-2012-part-b",
    },
    # Randwick — DCP 2013 (wider time window: 8am–4pm)
    {
        "lga": "randwick", "value_min": 3, "needs_review": False,
        "condition": "8am–4pm 21 June to POS of neighbouring dwellings; must not increase overshadowing",
        "source_text": "3 hours direct sunlight between 8am and 4pm on 21 June to private open space of neighbouring dwellings (DCP 2013)",
        "section_ref": "part-b-solar",
        "dcp_version": "v2013", "source_chapter_key": "randwick-dcp-2013-part-b",
    },
    # Fairfield — DCP 2013
    {
        "lga": "fairfield", "value_min": 3, "needs_review": False,
        "condition": "9am–3pm mid-winter solstice to at least one living area window on adjoining allotment",
        "source_text": "3 hours minimum direct sunlight between 9am and 3pm at mid-winter solstice to windows of at least one living area of dwelling on adjoining allotment (DCP 2013)",
        "section_ref": "residential-solar",
        "dcp_version": "v2013", "source_chapter_key": "fairfield-dcp-2013-residential",
    },
    # Blacktown — DCP 2015 (4 hours — higher standard)
    {
        "lga": "blacktown", "value_min": 4, "needs_review": False,
        "condition": "9am–3pm 21 June to minimum POS; shadow diagrams required",
        "source_text": "4 hours direct sunlight between 9am and 3pm on 21 June to minimum private open space; shadow diagrams required (DCP 2015)",
        "section_ref": "residential-solar",
        "dcp_version": "v2015", "source_chapter_key": "blacktown-dcp-2015-residential",
    },

    # ══════════════════════════════════════════════════════════════
    # NEEDS REVIEW — standard 3h/9am–3pm/21 June pattern applied
    # based on dominant NSW standard. Marked for PDF verification.
    # ══════════════════════════════════════════════════════════════

    # Waverley — DCP 2022 Part C (PDF not accessible for verification)
    {
        "lga": "waverley", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against DCP Part C)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (DCP 2022 Part C — needs PDF verification)",
        "section_ref": "part-c-solar",
        "dcp_version": "v2022", "source_chapter_key": "waverley-dcp-2022-part-c",
    },
    # Woollahra — DCP 2015 Chapter B3
    {
        "lga": "woollahra", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against DCP Chapter B3)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (DCP 2015 Chapter B3 — needs PDF verification)",
        "section_ref": "b3-solar",
        "dcp_version": "v2015", "source_chapter_key": "woollahra-dcp-2015-chapter-b3",
    },
    # Bayside — DCP 2022
    {
        "lga": "bayside", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against DCP 2022)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (DCP 2022 — needs PDF verification)",
        "section_ref": "residential-solar",
        "dcp_version": "v2022", "source_chapter_key": "bayside-dcp-2022-residential",
    },
    # Parramatta — DCP 2023
    {
        "lga": "parramatta", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against DCP 2023)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (DCP 2023 — needs PDF verification)",
        "section_ref": "residential-solar",
        "dcp_version": "v2023", "source_chapter_key": "parramatta-dcp-2023-residential",
    },
    # Campbelltown — DCP 2015
    {
        "lga": "campbelltown", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against DCP 2015)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (DCP 2015 — needs PDF verification)",
        "section_ref": "residential-solar",
        "dcp_version": "v2015", "source_chapter_key": "campbelltown-dcp-2015-residential",
    },
    # Liverpool — DCP 2008
    {
        "lga": "liverpool", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against DCP 2008)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (DCP 2008 — needs PDF verification)",
        "section_ref": "residential-solar",
        "dcp_version": "v2008", "source_chapter_key": "liverpool-dcp-2008-residential",
    },
    # Northern Beaches — Warringah DCP 2011
    {
        "lga": "northern_beaches", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against Warringah DCP 2011)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (Warringah DCP 2011 — needs PDF verification)",
        "section_ref": "part-b-solar",
        "dcp_version": "v2011", "source_chapter_key": "warringah-dcp-2011-part-b",
    },
    # Burwood — DCP 2013
    {
        "lga": "burwood", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against DCP 2013)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (DCP 2013 — needs PDF verification)",
        "section_ref": "residential-solar",
        "dcp_version": "v2013-amendment-13-nov2025", "source_chapter_key": "burwood-dcp-residential",
    },
    # Canada Bay — DCP
    {
        "lga": "canada_bay", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against DCP)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (DCP — needs PDF verification)",
        "section_ref": "residential-solar",
        "dcp_version": "v-current", "source_chapter_key": "canada-bay-dcp-residential",
    },
    # Cumberland — DCP 2021
    {
        "lga": "cumberland", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against DCP 2021)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (DCP 2021 — needs PDF verification)",
        "section_ref": "residential-solar",
        "dcp_version": "v2021", "source_chapter_key": "cumberland-dcp-2021-residential",
    },
    # Strathfield — DCP 2005
    {
        "lga": "strathfield", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against DCP 2005)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (DCP 2005 — needs PDF verification)",
        "section_ref": "residential-solar",
        "dcp_version": "v2005", "source_chapter_key": "strathfield-dcp-2005-residential",
    },
    # Ryde — DCP 2014
    {
        "lga": "ryde", "value_min": 3, "needs_review": True,
        "condition": "9am–3pm 21 June to living areas and POS (standard NSW pattern — verify against DCP 2014)",
        "source_text": "Assumed 3 hours between 9am and 3pm on 21 June (DCP 2014 — needs PDF verification)",
        "section_ref": "residential-solar",
        "dcp_version": "v2014", "source_chapter_key": "ryde-dcp-2014-residential",
    },
]


def main():
    parser = argparse.ArgumentParser(
        description="Insert solar access hour controls into dcp_setback_controls"
    )
    parser.add_argument("--dry-run", action="store_true",
                        help="Print what would be inserted without writing to DB")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    inserted = 0
    skipped = 0
    review_count = 0

    for row in SOLAR_ROWS:
        lga = row["lga"]
        needs_review = row["needs_review"]

        # Dedup check
        cur.execute("""
            SELECT id FROM dcp_setback_controls
            WHERE lga = %s AND control_type = 'solar_access_hours'
              AND dev_type = 'universal_residential'
              AND is_current = TRUE
        """, (lga,))
        if cur.fetchone():
            print(f"  SKIP dup: {lga}")
            skipped += 1
            continue

        if needs_review:
            review_count += 1

        if args.dry_run:
            flag = " [NEEDS REVIEW]" if needs_review else ""
            print(f"  DRY-RUN: {lga} min={row['value_min']}h cond={row['condition'][:60]}{flag}")
        else:
            cur.execute("""
                INSERT INTO dcp_setback_controls
                  (lga, dev_type, control_type, value_min, value_max, unit,
                   condition, applicability, source_text, section_ref,
                   dcp_version, is_current, extraction_method, source_chapter_key,
                   needs_review, review_reason)
                VALUES (%s, 'universal_residential', 'solar_access_hours',
                        %s, NULL, 'hours',
                        %s, 'universal_residential', %s, %s,
                        %s, TRUE, %s, %s,
                        %s, %s)
            """, (
                lga,
                row["value_min"],
                row["condition"],
                row["source_text"],
                row["section_ref"],
                row["dcp_version"],
                EXTRACTION_METHOD,
                row["source_chapter_key"],
                needs_review,
                "standard_pattern_assumed" if needs_review else None,
            ))
            inserted += 1

    if not args.dry_run:
        conn.commit()

    print(f"\nDone: {inserted} inserted, {skipped} skipped (duplicates)")
    print(f"  Verified: {inserted - review_count}, Needs review: {review_count}")

    # Summary query
    if not args.dry_run:
        cur.execute("""
            SELECT lga, value_min, needs_review,
                   LEFT(condition, 60) as condition_preview
            FROM dcp_setback_controls
            WHERE control_type = 'solar_access_hours' AND is_current = TRUE
            ORDER BY lga
        """)
        rows = cur.fetchall()
        print(f"\n{'LGA':<25} {'Hours':>5} {'Review':>7} Condition")
        print("-" * 90)
        for r in rows:
            flag = "  YES" if r["needs_review"] else "   no"
            print(f"{r['lga']:<25} {r['value_min']:>5} {flag:>7} {r['condition_preview']}")

    conn.close()


if __name__ == "__main__":
    main()
