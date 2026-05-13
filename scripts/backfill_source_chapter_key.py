#!/usr/bin/env python3
"""
Backfill source_chapter_key on existing dcp_setback_controls rows.

Maps each row to the dcp_chapter_registry chapter it was extracted from,
using (lga, section_ref) patterns. This enables the change-tracking chain:
chapter PDF changes → flag affected control rows for review.

Usage:
    python scripts/backfill_source_chapter_key.py --dry-run   # preview only
    python scripts/backfill_source_chapter_key.py             # apply
"""
import os, sys, argparse
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

# Explicit mapping: (lga) → list of (section_ref_prefix, chapter_key)
# Checked in order — first match wins. More specific prefixes first.
LGA_CHAPTER_MAP: dict[str, list[tuple[str, str]]] = {
    # Inner West — per-chapter PDFs in dcp_chapter_registry
    "ashfield": [
        ("chapter-f-dev-category", "chapter-f-dev-category"),
        ("chapter-a-miscellaneous", "chapter-a-miscellaneous"),
        ("chapter-d-precinct", "chapter-d-precinct-guidelines"),
    ],
    "marrickville": [
        ("part4-s1-low-density", "part4-s1-low-density"),
        ("part2-generic", "part2-generic-provisions"),
        # OCR-extracted rows use varying section_ref formats
        ("Marrickville_DCP", "part4-s1-low-density"),
        ("s4.1", "part4-s1-low-density"),
        ("C10", "part4-s1-low-density"),
        ("C11", "part4-s1-low-density"),
    ],
    "leichhardt": [
        ("part-c-s3-residential", "part-c-s3-residential"),
        ("part-c-c4", "part-c-s3-residential"),
        ("C3.", "part-c-s3-residential"),
    ],
    # Woollahra — per-chapter PDFs
    "woollahra": [
        ("chapter-b3-general-development", "chapter-b3-general-development"),
        ("B3.", "chapter-b3-general-development"),
    ],
    # Waverley — single PDF, chapter_key is 'waverley-dcp-2022'
    "waverley": [
        ("waverley-dcp-2022", "waverley-dcp-2022"),
        ("C1", "waverley-dcp-2022"),
        ("B", "waverley-dcp-2022"),
    ],
    # Ku-ring-gai — per-chapter PDFs
    "ku_ring_gai": [
        ("Ku-ring-gai_DCP_2024__section_a_part_4_1", "section-a-part-4-1-secondary-dwellings"),
        ("Ku-ring-gai_DCP_2024__section_a_part_4", "section-a-part-4-dwelling-houses"),
        ("section-a-part-4-1", "section-a-part-4-1-secondary-dwellings"),
        ("section-a-part-4-dwelling", "section-a-part-4-dwelling-houses"),
        ("section-a-part-5", "section-a-part-5-dual-occupancy"),
        ("4A", "section-a-part-4-dwelling-houses"),
        ("4.1", "section-a-part-4-1-secondary-dwellings"),
        ("4_1", "section-a-part-4-1-secondary-dwellings"),
    ],
    # Tier 2 councils — not yet in dcp_chapter_registry, but set chapter_key
    # so it's ready when they are registered.
    "canterbury_bankstown": [
        ("ch5-1", "chapter-5-1-bankstown-residential"),
        ("ch5-2", "chapter-5-2-canterbury-residential"),
    ],
    "blacktown": [
        ("s3.2", "part-3-residential"),
        ("s3.4", "part-3-residential"),
        ("s4.3", "part-4-secondary-dwellings"),
    ],
    "campbelltown": [
        ("s3.6.1", "part-3-residential"),
        ("s3.6.2", "part-3-residential"),
    ],
    "cumberland": [
        ("cumberland-part-b", "part-b-residential"),
        ("s3.6", "part-b-residential"),
    ],
    "hornsby": [
        ("s3", "part-3-residential"),
    ],
    "liverpool": [
        ("s2.1", "part-2-residential"),
        ("part8", "part-8-residential"),
        ("Part8", "part-8-residential"),
    ],
    "northern_beaches": [
        ("B3", "part-b-development-controls"),
        ("B8", "part-b-development-controls"),
    ],
    "penrith": [
        ("penrith-part-d2", "part-d2-residential"),
        ("s4.5", "part-d2-residential"),
        ("s4.6", "part-d2-residential"),
        ("penrith-dcp", "part-d2-residential"),
    ],
    # New LGAs added May 2026 — PDF-based extraction
    "burwood": [
        ("burwood-part4-residential", "part-4-residential"),
    ],
    "camden": [
        ("camden-part4-residential", "part-4-residential"),
    ],
    "canada_bay": [
        ("canada-bay-part-e-single", "part-e-single-dwellings"),
    ],
    "fairfield": [
        ("fairfield-ch5-dwelling", "chapter-5-dwelling-houses"),
    ],
    "ryde": [
        ("ryde-part3.3-dwelling", "part-3-3-dwelling-houses"),
    ],
    "strathfield": [
        ("strathfield-part-a-dwelling", "part-a-dwelling-houses"),
    ],
    "the_hills": [
        ("hills-shire-part-b-section2", "part-b-section-2-residential"),
    ],
}

# Sentinel chapter keys for explanation rows that reference external instruments
# (ADG, LEP) rather than DCP chapters. These are not monitorable via the DCP
# chapter registry but should not be flagged as blind spots by the watchdog.
EXTERNAL_INSTRUMENT_MAP: dict[str, str] = {
    "ADG": "_external_adg",
    "LEP": "_external_lep",
    "various": "_external_various",
}


def match_chapter_key(lga: str, section_ref: str | None) -> str | None:
    """Find the chapter_key for a given (lga, section_ref)."""
    if not section_ref:
        return None
    # Check external instrument sentinels first (ADG, LEP, various)
    if section_ref in EXTERNAL_INSTRUMENT_MAP:
        return EXTERNAL_INSTRUMENT_MAP[section_ref]
    prefixes = LGA_CHAPTER_MAP.get(lga, [])
    for prefix, chapter_key in prefixes:
        if section_ref.startswith(prefix):
            return chapter_key
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # Get all rows missing source_chapter_key
    cur.execute("""
        SELECT id, lga, dev_type, control_type, section_ref, source_chapter_key
        FROM dcp_setback_controls
        WHERE is_current = TRUE
          AND source_chapter_key IS NULL
        ORDER BY lga, dev_type, control_type
    """)
    rows = cur.fetchall()
    print(f"Rows missing source_chapter_key: {len(rows)}")

    matched = 0
    unmatched = []

    for row in rows:
        chapter_key = match_chapter_key(row["lga"], row["section_ref"])
        if chapter_key:
            matched += 1
            if args.dry_run:
                print(f"  MATCH: [{row['lga']}] {row['section_ref']} → {chapter_key}")
            else:
                cur.execute(
                    "UPDATE dcp_setback_controls SET source_chapter_key = %s WHERE id = %s",
                    (chapter_key, row["id"]),
                )
        else:
            unmatched.append(row)

    if not args.dry_run and matched > 0:
        conn.commit()

    print(f"\nMatched: {matched}")
    print(f"Unmatched: {len(unmatched)}")

    if unmatched:
        print("\nUnmatched rows (need manual mapping or have no section_ref):")
        for row in unmatched:
            print(f"  id={row['id']} lga={row['lga']} dev_type={row['dev_type']} "
                  f"control_type={row['control_type']} section_ref={row['section_ref']}")

    # Verify: show chapter_key coverage after backfill
    if not args.dry_run:
        cur.execute("""
            SELECT lga,
                   count(*) as total,
                   count(source_chapter_key) as has_chapter_key,
                   count(*) - count(source_chapter_key) as missing
            FROM dcp_setback_controls
            WHERE is_current = TRUE
            GROUP BY lga
            ORDER BY lga
        """)
        print("\nPost-backfill coverage:")
        for r in cur.fetchall():
            status = "OK" if r["missing"] == 0 else f"GAPS: {r['missing']}"
            print(f"  {r['lga']:25} {r['total']:3} rows, {r['has_chapter_key']:3} mapped  [{status}]")

    cur.close()
    conn.close()


if __name__ == "__main__":
    main()
