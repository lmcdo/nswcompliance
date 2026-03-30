#!/usr/bin/env python3
"""
Post-review utility: mark an instrument as reviewed and update currency.

Run this AFTER you have:
  1. Reviewed the amendment on legislation.nsw.gov.au
  2. Manually updated any affected provisions in regulatory_provisions
     or housing_sepp_standards as needed

This script:
  - Clears needs_review=FALSE on instrument_registry
  - Updates instrument_currency.verified_at and version_label
  - Sends Telegram confirmation

Usage:
    python scripts/update_instrument_provisions.py --key sepp_housing_2021
    python scripts/update_instrument_provisions.py --key sepp_housing_2021 --version "Version 15 (commenced 15 Mar 2026)"
    python scripts/update_instrument_provisions.py --key sepp_housing_2021 --dry-run
"""

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")


def send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return
    try:
        requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
    except Exception:
        pass


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--key", required=True, help="instrument_key to mark reviewed")
    parser.add_argument("--version", help="Version label to record (e.g. 'Version 15')")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False
    cur = conn.cursor()

    # Verify instrument exists
    cur.execute(
        "SELECT instrument_key, instrument_label, instrument_type, legislation_url, current_version, needs_review FROM instrument_registry WHERE instrument_key = %s",
        (args.key,),
    )
    row = cur.fetchone()
    if not row:
        print(f"ERROR: instrument_key '{args.key}' not found in instrument_registry")
        sys.exit(1)

    key, label, inst_type, url, current_version, needs_review = row
    version_label = args.version or current_version or "(version not recorded)"
    now = datetime.now(timezone.utc)

    print(f"Instrument : {key}")
    print(f"Label      : {label}")
    print(f"Version    : {version_label}")
    print(f"needs_review currently: {needs_review}")

    if args.dry_run:
        print("\nDRY RUN — no changes written.")
        return

    # Clear needs_review, set version
    cur.execute(
        """
        UPDATE instrument_registry
        SET needs_review = FALSE,
            current_version = %s,
            last_checked = %s
        WHERE instrument_key = %s
        """,
        (version_label, now, key),
    )

    # Update currency
    cur.execute(
        """
        INSERT INTO instrument_currency
            (council, instrument_key, instrument_label, instrument_type,
             verified_at, version_label, source_url)
        VALUES (NULL, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (council, instrument_key) DO UPDATE
            SET verified_at    = EXCLUDED.verified_at,
                version_label  = EXCLUDED.version_label,
                updated_at     = NOW()
        """,
        (key, label, inst_type, now, version_label, url),
    )

    conn.commit()
    cur.close()
    conn.close()

    msg = (
        f"Instrument provisions updated — {key}\n"
        f"Version: {version_label}\n"
        f"Reviewed and committed by: {os.environ.get('USER', 'unknown')}\n"
        f"Provisions now live."
    )
    print(f"\n{msg}")
    send_telegram(msg)


if __name__ == "__main__":
    main()
