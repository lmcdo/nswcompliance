#!/usr/bin/env python3
"""
Legislation Monitor
===================
Weekly check of AustLII consolidated copies of NSW SEPPs and LEPs for
"As at" date changes. AustLII receives PCO data weekly and publishes
within 2 working days — provides ~7-day lag detection without Cloudflare.

When PCO API access is granted, swap austlii_url → legislation_url
and update the fetch + parse logic to use the XML export endpoint.

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

# AustLII consolidated regulation URLs for monitored instruments
# classic.austlii.edu.au — clean 200, no Cloudflare
AUSTLII_URLS: dict[str, str] = {
    "sepp_housing_2021":         "https://classic.austlii.edu.au/au/legis/nsw/consol_reg/sepp2021448/",
    "sepp_exempt_complying_2008": "https://classic.austlii.edu.au/au/legis/nsw/consol_reg/seppacdc2008721/",
}

# "As at DD Month YYYY" in the <PRE> block at the top of each AustLII page
AS_AT_PATTERN = re.compile(r"As at\s+(\d{1,2}\s+\w+\s+\d{4})", re.IGNORECASE)


@dataclass
class InstrumentResult:
    instrument_key: str
    instrument_label: str
    changed: bool
    new_as_at: str | None
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


def fetch_as_at(url: str) -> str | None:
    """
    Fetch an AustLII consolidated regulation page and return the "As at" date string.
    Returns None if not found.
    Raises RuntimeError on non-200.
    """
    resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    if resp.status_code == 429:
        time.sleep(10)
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {url}")
    m = AS_AT_PATTERN.search(resp.text)
    return m.group(1) if m else None


def check_instrument(instrument: dict, dry_run: bool, conn) -> InstrumentResult:
    key = instrument["instrument_key"]
    label = instrument["instrument_label"]
    stored_version = instrument["current_version"]
    legislation_url = instrument["legislation_url"]

    austlii_url = AUSTLII_URLS.get(key)
    if not austlii_url:
        # No AustLII URL mapped — skip with a note (e.g. LEPs, which are council-specific)
        print(f"\n  {key} — no AustLII URL mapped, skipping")
        return InstrumentResult(
            instrument_key=key, instrument_label=label,
            changed=False, new_as_at=None,
            stored_version=stored_version,
            error="no AustLII URL mapped",
        )

    print(f"\n  {key}")
    print(f"    AustLII: {austlii_url}")

    try:
        new_as_at = fetch_as_at(austlii_url)

        print(f"    Stored version : {stored_version or '(none)'}")
        print(f"    AustLII As at  : {new_as_at or '(not found)'}")

        changed = bool(
            new_as_at
            and stored_version
            and new_as_at != stored_version
        )
        # Also flag as changed if we now have a date and stored nothing before
        first_run = new_as_at and not stored_version

        now = datetime.now(timezone.utc)
        cur = conn.cursor()

        if changed:
            print(f"    [CHANGED] {stored_version} → {new_as_at}")
            if not dry_run:
                cur.execute(
                    """
                    UPDATE instrument_registry
                    SET current_version = %s, last_checked = %s,
                        last_changed = %s, needs_review = TRUE,
                        check_failures = 0
                    WHERE instrument_key = %s
                    """,
                    (new_as_at, now, now, key),
                )
                conn.commit()
        else:
            status = "(first run — baseline set)" if first_run else "[unchanged]"
            print(f"    {status}")
            if not dry_run:
                cur.execute(
                    """
                    UPDATE instrument_registry
                    SET current_version = %s, last_checked = %s, check_failures = 0
                    WHERE instrument_key = %s
                    """,
                    (new_as_at or stored_version, now, key),
                )
                # Update currency — confirmed current as of this check
                cur.execute(
                    """
                    INSERT INTO instrument_currency
                        (council, instrument_key, instrument_label, instrument_type,
                         verified_at, version_label, source_url)
                    VALUES (NULL, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (council, instrument_key) DO UPDATE
                        SET verified_at   = EXCLUDED.verified_at,
                            version_label = EXCLUDED.version_label,
                            updated_at    = NOW()
                    """,
                    (
                        key, label, instrument["instrument_type"],
                        now, new_as_at or stored_version, legislation_url,
                    ),
                )
                conn.commit()
        cur.close()

        return InstrumentResult(
            instrument_key=key, instrument_label=label,
            changed=changed, new_as_at=new_as_at,
            stored_version=stored_version,
        )

    except Exception as exc:
        print(f"    [ERROR] {exc}")
        cur = conn.cursor()
        cur.execute(
            "UPDATE instrument_registry SET check_failures = check_failures + 1, "
            "last_checked = %s WHERE instrument_key = %s",
            (datetime.now(timezone.utc), key),
        )
        if not dry_run:
            conn.commit()
        cur.close()
        return InstrumentResult(
            instrument_key=key, instrument_label=label,
            changed=False, new_as_at=None,
            stored_version=stored_version, error=str(exc),
        )


def main():
    parser = argparse.ArgumentParser(description="Weekly SEPP/LEP change monitor via AustLII")
    parser.add_argument("--key", help="Check specific instrument_key only")
    parser.add_argument("--dry-run", action="store_true", help="No DB writes")
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    cur = conn.cursor()
    query = """
        SELECT instrument_key, instrument_label, instrument_type,
               legislation_url, current_version
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
    print("Source: AustLII consolidated copies (classic.austlii.edu.au)")
    print("Note: ~7-day lag vs legislation.nsw.gov.au")
    if args.dry_run:
        print("DRY RUN")
    print(f"Checking {len(instruments)} instruments...")
    print("=" * 60)

    results = []
    for instrument in instruments:
        result = check_instrument(instrument, args.dry_run, conn)
        results.append(result)
        time.sleep(2)

    conn.close()

    real_results = [r for r in results if not r.error or r.error != "no AustLII URL mapped"]
    changed = [r for r in results if r.changed]
    errors = [r for r in results if r.error and r.error != "no AustLII URL mapped"]

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Checked  : {len(real_results)}")
    print(f"  Changed  : {len(changed)}")
    print(f"  Errors   : {len(errors)}")

    if errors:
        for r in errors:
            print(f"  ERROR [{r.instrument_key}]: {r.error}")
        send_telegram(
            "Legislation Monitor ERROR\n"
            + "\n".join(f"  {r.instrument_key}: {r.error}" for r in errors)
        )

    if changed:
        lines = []
        for r in changed:
            lines.append(
                f"  {r.instrument_key}\n"
                f"    Was: {r.stored_version or '(unknown)'}\n"
                f"    Now: {r.new_as_at}"
            )
        msg = (
            f"LEGISLATION CHANGE DETECTED\n"
            f"{len(changed)} instrument(s) updated on AustLII:\n\n"
            + "\n\n".join(lines)
            + "\n\nVerify on legislation.nsw.gov.au before updating provisions."
            + "\nThen run: python scripts/update_instrument_provisions.py --key <key>"
        )
        print(f"\n{msg}")
        send_telegram(msg)
        sys.exit(2)

    if errors and not changed:
        sys.exit(1)

    send_telegram(
        f"Legislation Monitor: no changes ({len(real_results)} instruments checked via AustLII)"
    )
    print("\n  No changes. All instruments current on AustLII.")
    sys.exit(0)


if __name__ == "__main__":
    main()
