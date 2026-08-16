#!/usr/bin/env python3
"""
Backfill heritage metadata for Ashfield DCP 2016.

Three operations in sequence:
  1. Set v2_marker = 'heritage' on all heritage chapter provisions
     (prerequisite for tag_heritage_deterministic.py)
  2. Set v2_heritage_hca from section_header prefix on chapter-d-precinct-guidelines
     (enables HCA-specific filtering: Summer Hill site sees only Summer Hill provisions)
  3. Set v2_heritage_hca = 'haberfield' on chapter-e2-haberfield
     (entire chapter is Haberfield-specific)

After this script, run:
    python scripts/fixes/tag_heritage_deterministic.py

Usage:
    python scripts/backfill_ashfield_heritage.py --dry-run   # preview counts only
    python scripts/backfill_ashfield_heritage.py             # apply
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend-nextjs/.env.local'))

import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


# Section header prefix → HCA slug for chapter-d-precinct-guidelines
# Keys must match the start of section_header (case-insensitive prefix match)
HCA_PREFIX_MAP = {
    'Ashfield Town':   'ashfield_town_centre',
    'Hurlstone Park':  'hurlstone_park',
    'Haberfield':      'haberfield',
    'Ashfield South':  'ashfield_south',
    'Croydon South':   'croydon_south',
    'Canterbury Road': 'canterbury_road',
    'Ashfield East':   'ashfield_east',
    'Summer Hill':     'summer_hill',
}

# Heritage chapter keys — these get v2_marker = 'heritage'
HERITAGE_CHAPTER_KEYS = [
    'chapter-e1-heritage',
    'chapter-e2-haberfield',
]

# Chapter-key → fixed HCA (entire chapter is for one HCA)
CHAPTER_HCA_MAP = {
    'chapter-e2-haberfield': 'haberfield',
}


def get_db_url():
    url = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
    if not url:
        host = os.getenv('DATABASE_HOST') or os.getenv('DB_HOST')
        port = os.getenv('DATABASE_PORT') or os.getenv('DB_PORT') or '5432'
        name = os.getenv('DATABASE_NAME') or os.getenv('DB_NAME') or 'postgres'
        user = os.getenv('DATABASE_USER') or os.getenv('DB_USER')
        password = os.getenv('DATABASE_PASSWORD') or os.getenv('DB_PASSWORD')
        url = f"postgresql://{user}:{password}@{host}:{port}/{name}"
    return url


def classify_hca(section_header: str) -> str | None:
    if not section_header:
        return None
    for prefix, hca in HCA_PREFIX_MAP.items():
        if section_header.startswith(prefix):
            return hca
    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--dry-run', action='store_true', help='Preview without applying')
    args = parser.parse_args()

    mode = 'DRY RUN' if args.dry_run else 'APPLY'
    print(f"\nAshfield Heritage Backfill — {mode}")
    print("=" * 60)

    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor()

    # ─────────────────────────────────────────────────────────────
    # Step 1: v2_marker = 'heritage' on all heritage chapter rows
    # ─────────────────────────────────────────────────────────────
    print("\nStep 1: Set v2_marker = 'heritage' on heritage chapters")

    cur.execute("""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE source_council = 'ashfield'
          AND is_current = true
          AND source_chapter_key = ANY(%s)
          AND (v2_marker IS NULL OR v2_marker != 'heritage')
    """, (HERITAGE_CHAPTER_KEYS,))
    to_mark = cur.fetchone()[0]
    print(f"  Provisions to update: {to_mark}")

    if not args.dry_run and to_mark > 0:
        cur.execute("""
            UPDATE regulatory_provisions
            SET v2_marker = 'heritage'
            WHERE source_council = 'ashfield'
              AND is_current = true
              AND source_chapter_key = ANY(%s)
        """, (HERITAGE_CHAPTER_KEYS,))
        print(f"  Updated {cur.rowcount} rows")
        conn.commit()

    # ─────────────────────────────────────────────────────────────
    # Step 2: v2_heritage_hca from section_header prefix matching
    #         (chapter-d-precinct-guidelines)
    # ─────────────────────────────────────────────────────────────
    print("\nStep 2: Map v2_heritage_hca from section headers (precinct guidelines)")

    cur.execute("""
        SELECT id, section_header FROM regulatory_provisions
        WHERE source_council = 'ashfield'
          AND is_current = true
          AND source_chapter_key = 'chapter-d-precinct-guidelines'
          AND section_header IS NOT NULL
    """)
    rows = cur.fetchall()

    hca_updates = []
    unmatched = []
    hca_counts: dict[str, int] = {}

    for row_id, header in rows:
        hca = classify_hca(header)
        if hca:
            hca_updates.append((hca, row_id))
            hca_counts[hca] = hca_counts.get(hca, 0) + 1
        else:
            unmatched.append(header[:80])

    print(f"  Matched: {len(hca_updates)}")
    for hca, count in sorted(hca_counts.items(), key=lambda x: -x[1]):
        print(f"    {hca}: {count}")
    if unmatched:
        print(f"  Unmatched ({len(unmatched)}):")
        for h in unmatched[:10]:
            print(f"    {h!r}")

    if not args.dry_run and hca_updates:
        for hca, row_id in hca_updates:
            cur.execute("""
                UPDATE regulatory_provisions SET v2_heritage_hca = %s WHERE id = %s
            """, (hca, row_id))
        conn.commit()
        print(f"  Applied {len(hca_updates)} updates")

    # ─────────────────────────────────────────────────────────────
    # Step 3: v2_heritage_hca = fixed value for whole-chapter HCAs
    # ─────────────────────────────────────────────────────────────
    print("\nStep 3: Set v2_heritage_hca for chapter-level HCA chapters")

    for chapter_key, hca in CHAPTER_HCA_MAP.items():
        cur.execute("""
            SELECT COUNT(*) FROM regulatory_provisions
            WHERE source_council = 'ashfield'
              AND is_current = true
              AND source_chapter_key = %s
              AND (v2_heritage_hca IS NULL OR v2_heritage_hca != %s)
        """, (chapter_key, hca))
        count = cur.fetchone()[0]
        print(f"  {chapter_key} → {hca}: {count} provisions")

        if not args.dry_run and count > 0:
            cur.execute("""
                UPDATE regulatory_provisions
                SET v2_heritage_hca = %s
                WHERE source_council = 'ashfield'
                  AND is_current = true
                  AND source_chapter_key = %s
            """, (hca, chapter_key))
            conn.commit()

    # ─────────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN complete — no changes made.")
        print("Run without --dry-run to apply.")
    else:
        print("Done. Next step:")
        print("  python scripts/fixes/tag_heritage_deterministic.py")
        print()
        print("Verify:")
        print("  SELECT v2_heritage_hca, COUNT(*) FROM regulatory_provisions")
        print("  WHERE source_council = 'ashfield' AND is_current = true")
        print("  GROUP BY v2_heritage_hca ORDER BY count DESC;")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
