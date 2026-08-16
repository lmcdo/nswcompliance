#!/usr/bin/env python3
"""
Migration 010 — Fix dcp_chapter_registry
=========================================
1. Back up affected rows to scripts/backups/migration_010_backup_<timestamp>.json
2. Retire leichhardt/part-g-s13-pyrmont-bridge-rd (renamed on hub page)
3. Insert leichhardt/part-g-s13-site-specific (new name for same chapter)
4. Retire two SEPP entries stored in dcp_chapter_registry
   (epi-2021-0624, epi-2021-0620 — already tracked in instrument_registry)

Usage:
    python scripts/run_migration_010_fix_registry.py --dry-run
    python scripts/run_migration_010_fix_registry.py
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL / SUPABASE_DB_URL not set in .env")
    sys.exit(1)


def backup_affected_rows(conn) -> dict:
    cur = conn.cursor()

    # Rows being retired
    cur.execute("""
        SELECT id, council, chapter_key, chapter_label, council_url,
               council_page_url, is_active, content_hash
        FROM dcp_chapter_registry
        WHERE
            (council = 'leichhardt' AND chapter_key = 'part-g-s13-pyrmont-bridge-rd')
            OR council_url LIKE '%epi-2021-0624%'
            OR council_url LIKE '%epi-2021-0620%'
    """)
    cols = [d[0] for d in cur.description]
    rows = [dict(zip(cols, row)) for row in cur.fetchall()]

    cur.close()
    return {"timestamp": datetime.now(timezone.utc).isoformat(), "rows": rows}


def run(dry_run: bool, conn):
    now = datetime.now(timezone.utc)

    # ── 1. Backup ─────────────────────────────────────────────────────────────
    backup = backup_affected_rows(conn)
    backup_path = (
        Path(__file__).parent
        / "backups"
        / f"migration_010_backup_{now.strftime('%Y%m%d_%H%M%S')}.json"
    )
    backup_path.parent.mkdir(exist_ok=True)
    backup_path.write_text(json.dumps(backup, indent=2, default=str))
    print(f"Backup written: {backup_path}")
    print(f"  {len(backup['rows'])} row(s) backed up")
    for r in backup["rows"]:
        print(f"    [{r['council']}/{r['chapter_key']}] active={r['is_active']}")

    if not backup["rows"]:
        print("\nNo matching rows found — nothing to do.")
        return

    cur = conn.cursor()

    # ── 2. Retire old leichhardt chapter key ──────────────────────────────────
    print("\n[1/3] Retiring leichhardt/part-g-s13-pyrmont-bridge-rd...")
    cur.execute("""
        UPDATE dcp_chapter_registry
        SET is_active = FALSE
        WHERE council = 'leichhardt'
          AND chapter_key = 'part-g-s13-pyrmont-bridge-rd'
    """)
    print(f"      {cur.rowcount} row(s) updated")

    # ── 3. Insert renamed chapter ─────────────────────────────────────────────
    print("\n[2/3] Inserting leichhardt/part-g-s13-site-specific...")

    # Check it doesn't already exist
    cur.execute("""
        SELECT id FROM dcp_chapter_registry
        WHERE council = 'leichhardt' AND chapter_key = 'part-g-s13-site-specific'
    """)
    if cur.fetchone():
        print("      Already exists — skipping insert")
    else:
        # Copy sort_order from the retired row + 1 so it slots in same position
        cur.execute("""
            SELECT sort_order, council_page_url, hub_expected_count
            FROM dcp_chapter_registry
            WHERE council = 'leichhardt' AND chapter_key = 'part-g-s13-pyrmont-bridge-rd'
        """)
        row = cur.fetchone()
        sort_order = (row[0] or 0) if row else 0
        hub_url = (row[1] if row else
                   "https://www.innerwest.nsw.gov.au/develop/plans-policies-and-controls/"
                   "development-controls-lep-and-dcp/development-control-plans-dcp/leichhardt-dcp")
        hub_expected = row[2] if row else 16

        cur.execute("""
            INSERT INTO dcp_chapter_registry
                (council, chapter_key, chapter_label, dcp_name,
                 council_page_url, hub_expected_count,
                 sort_order, is_active)
            VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
        """, (
            "leichhardt",
            "part-g-s13-site-specific",
            "Part G \u2013 Site Specific Controls - Section 13",
            "Leichhardt DCP 2013",
            hub_url,
            hub_expected,
            sort_order,
        ))
        print(f"      {cur.rowcount} row(s) inserted")

    # ── 4. Retire SEPP entries from DCP registry ──────────────────────────────
    print("\n[3/3] Retiring SEPP entries from dcp_chapter_registry...")
    cur.execute("""
        UPDATE dcp_chapter_registry
        SET is_active = FALSE
        WHERE council_url LIKE '%epi-2021-0624%'
           OR council_url LIKE '%epi-2021-0620%'
    """)
    print(f"      {cur.rowcount} row(s) updated")

    # ── Commit ────────────────────────────────────────────────────────────────
    if dry_run:
        conn.rollback()
        print("\nDRY RUN — rolled back, no changes written")
    else:
        conn.commit()
        print("\nCommitted.")

    cur.close()


def main():
    parser = argparse.ArgumentParser(description="Migration 010: fix dcp_chapter_registry")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.dry_run:
        print("DRY RUN — no changes will be written\n")

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    try:
        run(args.dry_run, conn)
    finally:
        conn.close()


if __name__ == "__main__":
    main()
