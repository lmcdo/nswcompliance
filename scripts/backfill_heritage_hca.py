#!/usr/bin/env python3
"""
Backfill v2_heritage_hca and v2_marker = 'heritage' for Inner West councils.

Each council uses a different structural pattern:

  ASHFIELD   — HCA in section_header prefix ("Summer Hill —", "Haberfield —")
               Already done via backfill_ashfield_heritage.py (2026-03-19)

  MARRICKVILLE — HCA encoded directly in chapter_key
                 part9-p06-petersham-south → petersham_south
                 part8-heritage = general heritage (no specific HCA)

  LEICHHARDT — HCA in section_header as "X Distinctive Neighbourhood"
               part-c-s2-urban-character is the container chapter

Usage:
    python scripts/backfill_heritage_hca.py --council marrickville --dry-run
    python scripts/backfill_heritage_hca.py --council leichhardt --dry-run
    python scripts/backfill_heritage_hca.py --council marrickville
    python scripts/backfill_heritage_hca.py --council leichhardt
    python scripts/backfill_heritage_hca.py --all   # run all pending councils

After running, execute:
    python scripts/fixes/tag_heritage_deterministic.py
"""

import os
import sys
import re
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'frontend-nextjs/.env.local'))
import psycopg2

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')


# ─── MARRICKVILLE CONFIG ────────────────────────────────────────────────────
# part9-p* chapter keys encode the locality — extract directly
# part8-heritage = general heritage (applies to all heritage sites in Mville)
MARRICKVILLE_HERITAGE_CHAPTERS = {
    'general': ['part8-heritage'],
    'precinct_pattern': r'^part9-p\d+-(.+)$',   # capture group 1 = hca slug
}

# ─── LEICHHARDT CONFIG ──────────────────────────────────────────────────────
# Distinctive Neighbourhoods chapter: HCA in section header
LEICHHARDT_HERITAGE_CHAPTERS = {
    'general': [],   # no single general heritage chapter
    'section_header_chapters': ['part-c-s2-urban-character'],
    # Regex to extract HCA name from section header
    # e.g. "Balmain Distinctive Neighbourhood" → "balmain"
    # e.g. "Iron Cove Parklands Distinctive Neighbourhood" → "iron_cove_parklands"
    'header_pattern': r'^(.+?)\s+Distinctive\s+Neighbourhood',
    # Also handle suburb profile headers that aren't explicit DN
    'suburb_profile_pattern': r'^(.+?)\s+Suburb\s+Profile',
}


def get_db_url():
    url = os.getenv('SUPABASE_DB_URL') or os.getenv('DATABASE_URL')
    if not url:
        host = os.getenv('DATABASE_HOST') or os.getenv('DB_HOST')
        port = os.getenv('DATABASE_PORT') or os.getenv('DB_PORT') or '5432'
        name = os.getenv('DATABASE_NAME') or os.getenv('DB_NAME') or 'postgres'
        user = os.getenv('DATABASE_USER') or os.getenv('DB_USER')
        pw = os.getenv('DATABASE_PASSWORD') or os.getenv('DB_PASSWORD')
        url = f"postgresql://{user}:{pw}@{host}:{port}/{name}"
    return url


def to_slug(name: str) -> str:
    """Convert locality name to underscore slug."""
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def run_marrickville(cur, dry_run: bool):
    print("\n=== MARRICKVILLE ===")
    config = MARRICKVILLE_HERITAGE_CHAPTERS
    pattern = re.compile(config['precinct_pattern'])

    # Step 1: Set v2_marker = 'heritage' on part8-heritage and all part9-p* chapters
    cur.execute("""
        SELECT DISTINCT source_chapter_key FROM regulatory_provisions
        WHERE source_council = 'marrickville' AND is_current = true
          AND (source_chapter_key = 'part8-heritage'
               OR source_chapter_key ~ '^part9-p')
    """)
    heritage_chapters = [r[0] for r in cur.fetchall()]
    print(f"\nStep 1: Heritage chapters found: {len(heritage_chapters)}")

    cur.execute("""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE source_council = 'marrickville' AND is_current = true
          AND source_chapter_key = ANY(%s)
          AND (v2_marker IS NULL OR v2_marker != 'heritage')
    """, (heritage_chapters,))
    to_mark = cur.fetchone()[0]
    print(f"  Rows to set v2_marker='heritage': {to_mark}")

    if not dry_run and to_mark > 0:
        cur.execute("""
            UPDATE regulatory_provisions
            SET v2_marker = 'heritage'
            WHERE source_council = 'marrickville'
              AND is_current = true
              AND source_chapter_key = ANY(%s)
        """, (heritage_chapters,))
        print(f"  Updated {cur.rowcount} rows")

    # Step 2: Set v2_heritage_hca from chapter key for part9-p* chapters
    print("\nStep 2: Map v2_heritage_hca from part9-p* chapter keys")
    hca_by_chapter: dict[str, str] = {}
    for ch in heritage_chapters:
        m = pattern.match(ch)
        if m:
            hca_by_chapter[ch] = to_slug(m.group(1).replace('-', ' '))

    print(f"  Chapters with HCA: {len(hca_by_chapter)}")
    for ch, hca in sorted(hca_by_chapter.items()):
        cur.execute("""
            SELECT COUNT(*) FROM regulatory_provisions
            WHERE source_council = 'marrickville' AND is_current = true
              AND source_chapter_key = %s
        """, (ch,))
        count = cur.fetchone()[0]
        print(f"    {ch} → {hca} ({count} rows)")

    if not dry_run:
        for ch, hca in hca_by_chapter.items():
            cur.execute("""
                UPDATE regulatory_provisions
                SET v2_heritage_hca = %s
                WHERE source_council = 'marrickville'
                  AND is_current = true
                  AND source_chapter_key = %s
            """, (hca, ch))
        print(f"  Applied HCA updates for {len(hca_by_chapter)} chapters")


def run_leichhardt(cur, dry_run: bool):
    print("\n=== LEICHHARDT ===")
    config = LEICHHARDT_HERITAGE_CHAPTERS
    dn_pattern = re.compile(config['header_pattern'], re.IGNORECASE)
    sp_pattern = re.compile(config['suburb_profile_pattern'], re.IGNORECASE)

    # Step 1: Set v2_marker = 'heritage' on part-c-s2-urban-character
    target_chapters = config['section_header_chapters']
    cur.execute("""
        SELECT COUNT(*) FROM regulatory_provisions
        WHERE source_council = 'leichhardt' AND is_current = true
          AND source_chapter_key = ANY(%s)
          AND (v2_marker IS NULL OR v2_marker != 'heritage')
    """, (target_chapters,))
    to_mark = cur.fetchone()[0]
    print(f"\nStep 1: Set v2_marker='heritage' on {target_chapters}: {to_mark} rows")

    if not dry_run and to_mark > 0:
        cur.execute("""
            UPDATE regulatory_provisions
            SET v2_marker = 'heritage'
            WHERE source_council = 'leichhardt'
              AND is_current = true
              AND source_chapter_key = ANY(%s)
        """, (target_chapters,))
        print(f"  Updated {cur.rowcount} rows")

    # Step 2: Extract HCA from section headers matching DN pattern
    print("\nStep 2: Map v2_heritage_hca from Distinctive Neighbourhood section headers")
    cur.execute("""
        SELECT id, section_header FROM regulatory_provisions
        WHERE source_council = 'leichhardt' AND is_current = true
          AND source_chapter_key = ANY(%s)
          AND section_header IS NOT NULL
    """, (target_chapters,))
    rows = cur.fetchall()

    hca_updates = []
    hca_counts: dict[str, int] = {}
    unmatched = []

    for row_id, header in rows:
        hca = None
        m = dn_pattern.match(header)
        if m:
            hca = to_slug(m.group(1))
        else:
            m = sp_pattern.match(header)
            if m:
                hca = to_slug(m.group(1))

        if hca:
            hca_updates.append((hca, row_id))
            hca_counts[hca] = hca_counts.get(hca, 0) + 1
        else:
            unmatched.append(header[:70])

    print(f"  Matched: {len(hca_updates)}")
    for hca, count in sorted(hca_counts.items(), key=lambda x: -x[1]):
        print(f"    {hca}: {count}")
    if unmatched:
        print(f"  Unmatched ({len(unmatched)}) — general controls, not HCA-specific:")
        for h in unmatched[:8]:
            print(f"    {h!r}")

    if not dry_run and hca_updates:
        for hca, row_id in hca_updates:
            cur.execute("""
                UPDATE regulatory_provisions SET v2_heritage_hca = %s WHERE id = %s
            """, (hca, row_id))
        print(f"  Applied {len(hca_updates)} HCA updates")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--council', choices=['marrickville', 'leichhardt'], help='Single council to run')
    parser.add_argument('--all', action='store_true', help='Run all pending councils')
    parser.add_argument('--dry-run', action='store_true', help='Preview without applying')
    args = parser.parse_args()

    if not args.council and not args.all:
        parser.error('Specify --council <name> or --all')

    mode = 'DRY RUN' if args.dry_run else 'APPLY'
    print(f"\nHeritage HCA Backfill — {mode}")
    print("=" * 60)

    conn = psycopg2.connect(get_db_url())
    cur = conn.cursor()

    councils = []
    if args.all:
        councils = ['marrickville', 'leichhardt']
    elif args.council:
        councils = [args.council]

    for council in councils:
        if council == 'marrickville':
            run_marrickville(cur, args.dry_run)
        elif council == 'leichhardt':
            run_leichhardt(cur, args.dry_run)

        if not args.dry_run:
            conn.commit()
            print(f"\n  Committed {council}")

    print("\n" + "=" * 60)
    if args.dry_run:
        print("DRY RUN — no changes made. Run without --dry-run to apply.")
    else:
        print("Done. Next: python scripts/fixes/tag_heritage_deterministic.py")

    cur.close()
    conn.close()


if __name__ == '__main__':
    main()
