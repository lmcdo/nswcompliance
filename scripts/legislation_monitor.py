#!/usr/bin/env python3
"""
Legislation Monitor
===================
Weekly check of legislation.nsw.gov.au for SEPP and LEP version changes.
Reads from instrument_registry, updates instrument_currency.

Run alongside r2_monitor.py on the Monday 02:00 UTC schedule.

Usage:
    python scripts/legislation_monitor.py               # all active instruments
    python scripts/legislation_monitor.py --key sepp_housing_2021
    python scripts/legislation_monitor.py --dry-run

Exit codes:
    0 = no changes
    1 = error
    2 = changes detected (one or more instruments flagged for review)
"""

import argparse
import hashlib
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("SUPABASE_DB_URL")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; PlotDetect/1.0; "
        "+https://plotdetect.com.au; compliance-data-fetch)"
    ),
    "Accept": "text/html,*/*",
}

# CSS selectors tried in order to find the version string on legislation pages
VERSION_SELECTORS = [
    "span.legislation-version",
    "div.version-details",
    "p.version",
    ".doc-version",
    "h1 + div",  # fallback — grab text near the title
]

# Regex patterns tried in order against page text to extract version info
VERSION_PATTERNS = [
    r"Version\s+(\d+[\w.]*)\s*[-–—]\s*([^\n<]+)",       # "Version 15 - commenced 1 Jan 2026"
    r"Version\s+(\d+[\w.]*)\s*\(([^)]+)\)",               # "Version 15 (commenced 1 Jan 2026)"
    r"(Version\s+\d+[\w.]*)",                              # bare "Version 15"
    r"commenced\s+(\d{1,2}\s+\w+\s+\d{4})",               # "commenced 15 March 2026"
]


@dataclass
class InstrumentResult:
    instrument_key: str
    instrument_label: str
    changed: bool
    new_hash: str
    new_version: str | None
    stored_version: str | None
    error: str | None = None


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


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def fetch_legislation_page(url: str) -> tuple[str, str]:
    """
    Fetch a legislation.nsw.gov.au page.
    Returns (html_content, content_hash).
    Raises RuntimeError on non-200.
    """
    resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    if resp.status_code == 429:
        time.sleep(10)
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {url}")
    return resp.text, sha256(resp.content)


def extract_version(html: str) -> str | None:
    """
    Try to extract a version string from legislation page HTML.
    Returns the version string, or None if not parseable.
    """
    soup = BeautifulSoup(html, "lxml")

    # Try CSS selectors first
    for selector in VERSION_SELECTORS:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(" ", strip=True)
            if text:
                return text[:200]  # cap length

    # Fall back to regex on full page text
    text = soup.get_text(" ", strip=True)
    for pattern in VERSION_PATTERNS:
        m = re.search(pattern, text, re.IGNORECASE)
        if m:
            return m.group(0)[:200]

    return None


def check_instrument(instrument: dict, dry_run: bool, conn) -> InstrumentResult:
    key = instrument["instrument_key"]
    label = instrument["instrument_label"]
    url = instrument["legislation_url"]
    stored_hash = instrument["content_hash"]
    stored_version = instrument["current_version"]

    print(f"\n  {key}")

    try:
        html, new_hash = fetch_legislation_page(url)
        new_version = extract_version(html)

        print(f"    Stored version : {stored_version or '(none)'}")
        print(f"    Fetched version: {new_version or '(not parseable)'}")
        print(f"    Hash match     : {new_hash == stored_hash}")

        changed = (new_hash != stored_hash) or (
            new_version and stored_version and new_version != stored_version
        )

        now = datetime.now(timezone.utc)
        cur = conn.cursor()

        if changed:
            print(f"    [CHANGED]")
            if not dry_run:
                cur.execute(
                    """
                    UPDATE instrument_registry
                    SET content_hash = %s, current_version = %s,
                        last_checked = %s, last_changed = %s,
                        needs_review = TRUE, check_failures = 0
                    WHERE instrument_key = %s
                    """,
                    (new_hash, new_version, now, now, key),
                )
                conn.commit()
        else:
            print(f"    [unchanged]")
            if not dry_run:
                cur.execute(
                    """
                    UPDATE instrument_registry
                    SET content_hash = %s, current_version = %s,
                        last_checked = %s, check_failures = 0
                    WHERE instrument_key = %s
                    """,
                    (new_hash, new_version, now, key),
                )
                # Update currency table — confirmed current
                cur.execute(
                    """
                    INSERT INTO instrument_currency
                        (council, instrument_key, instrument_label, instrument_type,
                         verified_at, version_label, source_url)
                    VALUES (NULL, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (council, instrument_key) DO UPDATE
                        SET verified_at = EXCLUDED.verified_at,
                            version_label = EXCLUDED.version_label,
                            updated_at = NOW()
                    """,
                    (
                        key, label, instrument["instrument_type"],
                        now, new_version, url,
                    ),
                )
                conn.commit()
        cur.close()

        return InstrumentResult(
            instrument_key=key, instrument_label=label,
            changed=changed, new_hash=new_hash,
            new_version=new_version, stored_version=stored_version,
        )

    except Exception as exc:
        print(f"    [ERROR] {exc}")
        cur = conn.cursor()
        cur.execute(
            "UPDATE instrument_registry SET check_failures = check_failures + 1, last_checked = %s WHERE instrument_key = %s",
            (datetime.now(timezone.utc), key),
        )
        if not dry_run:
            conn.commit()
        cur.close()
        return InstrumentResult(
            instrument_key=key, instrument_label=label,
            changed=False, new_hash="", new_version=None,
            stored_version=stored_version, error=str(exc),
        )


def main():
    parser = argparse.ArgumentParser(description="Weekly legislation.nsw.gov.au monitor")
    parser.add_argument("--key", help="Check specific instrument_key only")
    parser.add_argument("--dry-run", action="store_true", help="No DB writes")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    cur = conn.cursor()
    query = """
        SELECT instrument_key, instrument_label, instrument_type,
               legislation_url, current_version, content_hash
        FROM instrument_registry
        WHERE is_active = TRUE
    """
    params = []
    if args.key:
        query += " AND instrument_key = %s"
        params.append(args.key)
    query += " ORDER BY instrument_type, instrument_key"
    cur.execute(query, params)
    cols = [d[0] for d in cur.description]
    instruments = [dict(zip(cols, row)) for row in cur.fetchall()]
    cur.close()

    print("=" * 60)
    print(f"Legislation Monitor — {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    if args.dry_run:
        print("DRY RUN")
    print(f"Checking {len(instruments)} instruments...")
    print("=" * 60)

    results = []
    for instrument in instruments:
        result = check_instrument(instrument, args.dry_run, conn)
        results.append(result)
        time.sleep(2)  # polite delay between legislation.nsw.gov.au requests

    conn.close()

    changed = [r for r in results if r.changed]
    errors = [r for r in results if r.error]

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Checked  : {len(results)}")
    print(f"  Changed  : {len(changed)}")
    print(f"  Errors   : {len(errors)}")

    if errors:
        for r in errors:
            print(f"  ERROR [{r.instrument_key}]: {r.error}")
        send_telegram(
            f"Legislation Monitor ERROR\n"
            + "\n".join(f"  {r.instrument_key}: {r.error}" for r in errors)
        )

    if changed:
        lines = []
        for r in changed:
            lines.append(
                f"  {r.instrument_key}\n"
                f"    Was: {r.stored_version or '(unknown)'}\n"
                f"    Now: {r.new_version or '(not parseable — hash changed)'}"
            )
        msg = (
            f"LEGISLATION CHANGE DETECTED\n"
            f"{len(changed)} instrument(s) changed:\n\n"
            + "\n\n".join(lines)
            + "\n\nReview amendments on legislation.nsw.gov.au before updating provisions."
            + "\nThen run: python scripts/update_instrument_provisions.py --key <key>"
        )
        print(f"\n{msg}")
        send_telegram(msg)
        sys.exit(2)

    if errors and not changed:
        sys.exit(1)

    send_telegram(f"Legislation Monitor: no changes ({len(results)} instruments checked)")
    print("\n  No changes. All instruments current.")
    sys.exit(0)


if __name__ == "__main__":
    main()
