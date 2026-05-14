#!/usr/bin/env python3
"""
Manually verify a DCP chapter PDF that can't be auto-downloaded (WAF-blocked).

Downloads are done by the user in a browser. This script:
  1. Hashes the provided PDF file
  2. Compares to the stored hash in dcp_chapter_registry
  3. If unchanged: updates last_verified_at on linked dcp_setback_controls rows
  4. If changed: uploads new PDF to R2, sets needs_extraction=TRUE, sends Telegram alert

Usage:
    python scripts/manual_verify.py --council marrickville --chapter part4-s1-low-density --file ~/Downloads/chapter.pdf
    python scripts/manual_verify.py --council marrickville --chapter part4-s1-low-density --file ~/Downloads/chapter.pdf --dry-run
    python scripts/manual_verify.py --list-blocked   # show all WAF-blocked chapters needing manual check
"""
import argparse
import hashlib
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor

load_dotenv(Path(__file__).parent.parent / ".env")
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        import requests
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
    except Exception:
        pass


def list_blocked(conn):
    """Show chapters that have been WAF-blocked (recent check but no hash update)."""
    cur = conn.cursor(cursor_factory=RealDictCursor)
    cur.execute("""
        SELECT council, chapter_key, chapter_label, council_url,
               content_hash IS NOT NULL as has_hash,
               url_last_checked, url_last_changed, check_failures
        FROM dcp_chapter_registry
        WHERE registration_status = 'confirmed'
          AND council_url IS NOT NULL
          AND is_active = TRUE
          AND COALESCE(is_spatial, FALSE) = FALSE
          AND COALESCE(is_inert, FALSE) = FALSE
          AND check_failures > 0
        ORDER BY council, chapter_key
    """)
    rows = cur.fetchall()
    if not rows:
        print("No blocked/failing chapters found.")
        return

    print(f"\n{'='*70}")
    print(f"Chapters needing manual verification: {len(rows)}")
    print(f"{'='*70}")
    current_council = None
    for r in rows:
        if r["council"] != current_council:
            current_council = r["council"]
            print(f"\n  [{current_council}]")
        hash_status = "has hash" if r["has_hash"] else "NO HASH"
        print(f"    {r['chapter_key']}")
        print(f"      {r['council_url']}")
        print(f"      ({hash_status}, last checked: {r['url_last_checked']})")


def verify(council: str, chapter_key: str, file_path: str, dry_run: bool):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    # 1. Find the chapter in the registry
    cur.execute("""
        SELECT id, council, chapter_key, content_hash, r2_current_path
        FROM dcp_chapter_registry
        WHERE council = %s AND chapter_key = %s
          AND registration_status = 'confirmed'
    """, (council, chapter_key))
    chapter = cur.fetchone()

    if not chapter:
        print(f"ERROR: No confirmed chapter found for council={council}, key={chapter_key}")
        print("Check: python scripts/manual_verify.py --list-blocked")
        conn.close()
        sys.exit(1)

    # 2. Hash the provided file
    pdf_path = Path(file_path).expanduser().resolve()
    if not pdf_path.exists():
        print(f"ERROR: File not found: {pdf_path}")
        conn.close()
        sys.exit(1)

    pdf_data = pdf_path.read_bytes()
    ct = pdf_path.suffix.lower()
    if ct != ".pdf":
        print(f"WARNING: File extension is '{ct}', expected '.pdf'. Proceeding anyway.")

    new_hash = sha256(pdf_data)
    stored_hash = chapter["content_hash"]
    now = datetime.now(timezone.utc)

    print(f"\n  Council     : {council}")
    print(f"  Chapter     : {chapter_key}")
    print(f"  File        : {pdf_path} ({len(pdf_data):,} bytes)")
    print(f"  New hash    : {new_hash[:16]}...")
    print(f"  Stored hash : {(stored_hash or 'NONE')[:16]}{'...' if stored_hash else ''}")

    if new_hash == stored_hash:
        # ── No change — update verification timestamps ──
        print(f"\n  RESULT: No change detected. Updating last_verified_at.")

        if not dry_run:
            # Update registry
            cur.execute("""
                UPDATE dcp_chapter_registry
                SET url_last_checked = %s, check_failures = 0
                WHERE id = %s
            """, (now, chapter["id"]))

            # Update linked control rows
            cur.execute("""
                UPDATE dcp_setback_controls
                SET last_verified_at = %s
                WHERE lga = %s AND source_chapter_key = %s AND is_current = TRUE
            """, (now, council, chapter_key))
            updated = cur.rowcount

            conn.commit()
            print(f"  Updated last_verified_at on {updated} control row(s).")
        else:
            print(f"  DRY-RUN: would update registry and control rows.")

    else:
        # ── Changed — flag for re-extraction ──
        print(f"\n  RESULT: CHANGE DETECTED! Flagging for re-extraction.")

        if not dry_run:
            cur.execute("""
                UPDATE dcp_chapter_registry
                SET content_hash = %s, url_last_checked = %s, url_last_changed = %s,
                    needs_extraction = TRUE, check_failures = 0
                WHERE id = %s
            """, (new_hash, now, now, chapter["id"]))

            # Flag linked controls for review
            cur.execute("""
                UPDATE dcp_setback_controls
                SET needs_review = TRUE
                WHERE lga = %s AND source_chapter_key = %s AND is_current = TRUE
            """, (council, chapter_key))
            flagged = cur.rowcount

            conn.commit()
            print(f"  Flagged {flagged} control row(s) for review.")
            print(f"  Chapter marked needs_extraction=TRUE.")

            send_telegram(
                f"Manual verify: CHANGE detected\n"
                f"  [{council}] {chapter_key}\n"
                f"  Old: {(stored_hash or 'NONE')[:16]}\n"
                f"  New: {new_hash[:16]}\n"
                f"  {flagged} control row(s) flagged for review."
            )
        else:
            print(f"  DRY-RUN: would update hash, flag needs_extraction and needs_review.")

    conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Manually verify a WAF-blocked DCP chapter PDF"
    )
    parser.add_argument("--council", help="Council slug (e.g. marrickville)")
    parser.add_argument("--chapter", help="Chapter key (e.g. part4-s1-low-density)")
    parser.add_argument("--file", help="Path to downloaded PDF file")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--list-blocked", action="store_true",
                        help="List all chapters needing manual verification")
    args = parser.parse_args()

    if args.list_blocked:
        conn = psycopg2.connect(DATABASE_URL)
        list_blocked(conn)
        conn.close()
        return

    if not all([args.council, args.chapter, args.file]):
        parser.error("--council, --chapter, and --file are required (or use --list-blocked)")

    verify(args.council, args.chapter, args.file, args.dry_run)


if __name__ == "__main__":
    main()
