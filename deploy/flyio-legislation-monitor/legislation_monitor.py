#!/usr/bin/env python3
"""
Legislation Monitor
===================
Weekly check of NSW planning instruments (SEPPs, LEPs) for version changes.

Primary source: PCO XML export (legislation.nsw.gov.au/export/week)
  - Requires IP whitelisting (contact belinda.brown@pco.nsw.gov.au)
  - Must run outside Sydney business hours
  - Returns JSON list of all instruments updated in last 7 days

Fallback source: AustLII consolidated copies (classic.austlii.edu.au)
  - ~7-day lag vs legislation.nsw.gov.au
  - Scrapes "As at DD Month YYYY" date from HTML
  - Used when PCO endpoint is inaccessible (403, timeout, etc.)

Usage:
    python scripts/legislation_monitor.py               # all active instruments
    python scripts/legislation_monitor.py --key sepp_housing_2021
    python scripts/legislation_monitor.py --dry-run
    python scripts/legislation_monitor.py --source pco   # force PCO only
    python scripts/legislation_monitor.py --source austlii  # force AustLII only

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

# "As at DD Month YYYY" in the <PRE> block at the top of each AustLII page
AS_AT_PATTERN = re.compile(r"As at\s+(\d{1,2}\s+\w+\s+\d{4})", re.IGNORECASE)


@dataclass
class InstrumentResult:
    instrument_key: str
    instrument_label: str
    changed: bool
    new_version: str | None
    stored_version: str | None
    source: str = ""  # 'pco' or 'austlii'
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


# ---------------------------------------------------------------------------
# PCO source
# ---------------------------------------------------------------------------

def check_via_pco(instruments: list[dict]) -> dict[str, str | None]:
    """Check instruments via PCO weekly export feed.

    Returns dict of {instrument_key: new_version_string_or_None}.
    Raises on access denied or connection error.
    """
    from pco_client import PCOAccessDenied, get_weekly_changes

    changes = get_weekly_changes()
    print(f"    PCO: {len(changes)} instruments changed this week")

    # Build lookup: pco_instrument_id → instrument_key
    pco_to_key = {}
    for inst in instruments:
        pco_id = inst.get("pco_instrument_id")
        if pco_id:
            pco_to_key[pco_id] = inst["instrument_key"]

    results: dict[str, str | None] = {inst["instrument_key"]: None for inst in instruments}

    for change in changes:
        if change.instrument_id in pco_to_key:
            key = pco_to_key[change.instrument_id]
            # Use point_in_time as version string (matches AustLII "As at" concept)
            version = change.point_in_time or change.last_updated or "updated"
            results[key] = version
            print(f"    PCO match: {key} → {version}")

    return results


# ---------------------------------------------------------------------------
# AustLII fallback source
# ---------------------------------------------------------------------------

_PLAYWRIGHT_BROWSER = None


def _get_playwright_browser():
    """Lazy-init a shared Playwright browser for the process."""
    global _PLAYWRIGHT_BROWSER
    if _PLAYWRIGHT_BROWSER is None:
        from playwright.sync_api import sync_playwright
        pw = sync_playwright().start()
        _PLAYWRIGHT_BROWSER = pw.chromium.launch(
            headless=True,
            args=["--disable-blink-features=AutomationControlled"],
        )
    return _PLAYWRIGHT_BROWSER


def fetch_as_at_playwright(url: str) -> str | None:
    """Fetch an AustLII page via Playwright to solve Cloudflare challenges."""
    browser = _get_playwright_browser()
    ctx = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
    )
    page = ctx.new_page()
    page.goto(url, timeout=45000)
    page.wait_for_selector("pre", timeout=45000)
    html = page.content()
    ctx.close()

    m = AS_AT_PATTERN.search(html)
    return m.group(1) if m else None


def fetch_as_at(url: str) -> str | None:
    """Fetch an AustLII page and return the "As at" date string.

    Tries plain HTTP first. On 403 (Cloudflare challenge), falls back
    to Playwright with a headless browser.
    """
    resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    if resp.status_code == 429:
        time.sleep(10)
        resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    if resp.status_code == 403:
        print(f"    HTTP 403 — using Playwright to solve Cloudflare challenge...")
        return fetch_as_at_playwright(url)
    if resp.status_code != 200:
        raise RuntimeError(f"AustLII HTTP {resp.status_code}: {url}")
    m = AS_AT_PATTERN.search(resp.text)
    return m.group(1) if m else None


def check_via_austlii(instruments: list[dict]) -> tuple[dict[str, str | None], list[str]]:
    """Check instruments via AustLII consolidated copies.

    Returns (version_map, fetch_errors) where fetch_errors is a list of
    error strings for instruments that could not be checked at all.
    """
    results: dict[str, str | None] = {}
    fetch_errors: list[str] = []

    for inst in instruments:
        key = inst["instrument_key"]
        austlii_url = inst.get("austlii_url")
        if not austlii_url:
            print(f"    {key} — no AustLII URL mapped, skipping")
            results[key] = None
            continue

        try:
            as_at = fetch_as_at(austlii_url)
            results[key] = as_at
            print(f"    AustLII: {key} → {as_at or '(not found)'}")
        except Exception as exc:
            print(f"    [ERROR] {key}: {exc}")
            results[key] = None
            fetch_errors.append(f"{key}: {exc}")
        time.sleep(2)

    return results, fetch_errors


# ---------------------------------------------------------------------------
# Core check logic
# ---------------------------------------------------------------------------

def check_instrument(
    instrument: dict, new_version: str | None, source: str,
    dry_run: bool, conn,
) -> InstrumentResult:
    """Compare detected version against stored version and update DB."""
    key = instrument["instrument_key"]
    label = instrument["instrument_label"]
    stored_version = instrument["current_version"]
    legislation_url = instrument["legislation_url"]

    if new_version is None:
        # Source didn't return data for this instrument — not an error,
        # just means no change detected (or instrument not in source's scope)
        return InstrumentResult(
            instrument_key=key, instrument_label=label,
            changed=False, new_version=None,
            stored_version=stored_version, source=source,
        )

    changed = bool(
        new_version and stored_version and new_version != stored_version
    )
    first_run = new_version and not stored_version

    now = datetime.now(timezone.utc)
    cur = conn.cursor()

    if changed:
        print(f"  {key} [{source}]")
        print(f"    [CHANGED] {stored_version} → {new_version}")
        if not dry_run:
            cur.execute(
                """
                UPDATE instrument_registry
                SET current_version = %s, last_checked = %s,
                    last_changed = %s, needs_review = TRUE,
                    check_failures = 0
                WHERE instrument_key = %s
                """,
                (new_version, now, now, key),
            )
            conn.commit()
    else:
        status = "(first run — baseline set)" if first_run else "[unchanged]"
        print(f"  {key} [{source}] {status}")
        if not dry_run:
            cur.execute(
                """
                UPDATE instrument_registry
                SET current_version = %s, last_checked = %s, check_failures = 0
                WHERE instrument_key = %s
                """,
                (new_version or stored_version, now, key),
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
                    now, new_version or stored_version, legislation_url,
                ),
            )
            conn.commit()
    cur.close()

    return InstrumentResult(
        instrument_key=key, instrument_label=label,
        changed=changed, new_version=new_version,
        stored_version=stored_version, source=source,
    )


def main():
    parser = argparse.ArgumentParser(description="Weekly SEPP/LEP change monitor")
    parser.add_argument("--key", help="Check specific instrument_key only")
    parser.add_argument("--dry-run", action="store_true", help="No DB writes")
    parser.add_argument(
        "--source", choices=["auto", "pco", "austlii"], default="auto",
        help="Force data source (default: auto — try PCO, fall back to AustLII)",
    )
    args = parser.parse_args()

    conn = psycopg2.connect(DATABASE_URL)
    conn.autocommit = False

    cur = conn.cursor()
    query = """
        SELECT instrument_key, instrument_label, instrument_type,
               legislation_url, current_version,
               pco_instrument_id, austlii_url
        FROM instrument_registry
        WHERE is_active = TRUE
    """
    params: list = []
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

    # Determine source and fetch version data
    source_used = args.source
    version_map: dict[str, str | None] = {}
    source_fetch_errors: list[str] = []

    if source_used in ("auto", "pco"):
        try:
            print("\n  Trying PCO weekly export...")
            version_map = check_via_pco(instruments)
            source_used = "pco"
            print(f"  Source: PCO (legislation.nsw.gov.au)")
        except Exception as exc:
            if source_used == "pco":
                # User forced PCO — don't fall back
                print(f"\n  [ERROR] PCO failed: {exc}")
                send_telegram(f"Legislation Monitor ERROR\nPCO access failed: {exc}")
                conn.close()
                sys.exit(1)
            # Auto mode — fall back to AustLII
            print(f"  PCO unavailable ({exc}), falling back to AustLII...")
            source_used = "austlii"

    if source_used == "austlii":
        print(f"\n  Source: AustLII (classic.austlii.edu.au) — ~7-day lag")
        version_map, source_fetch_errors = check_via_austlii(instruments)

    # Process results
    print(f"\n{'='*60}")
    results = []
    for instrument in instruments:
        key = instrument["instrument_key"]
        new_version = version_map.get(key)
        try:
            result = check_instrument(
                instrument, new_version, source_used, args.dry_run, conn,
            )
            results.append(result)
        except Exception as exc:
            print(f"  {key} [ERROR] {exc}")
            cur = conn.cursor()
            cur.execute(
                "UPDATE instrument_registry SET check_failures = check_failures + 1, "
                "last_checked = %s WHERE instrument_key = %s",
                (datetime.now(timezone.utc), key),
            )
            if not args.dry_run:
                conn.commit()
            cur.close()
            results.append(InstrumentResult(
                instrument_key=key, instrument_label=instrument["instrument_label"],
                changed=False, new_version=None,
                stored_version=instrument["current_version"],
                source=source_used, error=str(exc),
            ))

    conn.close()

    changed = [r for r in results if r.changed]
    errors = [r for r in results if r.error]
    checked = [r for r in results if not r.error]

    # Count instruments with AustLII URLs that failed at the fetch level
    total_fetch_errors = len(source_fetch_errors)

    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    print(f"  Source       : {source_used}")
    print(f"  Checked      : {len(checked)}")
    print(f"  Changed      : {len(changed)}")
    print(f"  DB errors    : {len(errors)}")
    print(f"  Fetch errors : {total_fetch_errors}")

    if source_fetch_errors:
        for err in source_fetch_errors:
            print(f"  FETCH ERROR: {err}")

    if errors:
        for r in errors:
            print(f"  ERROR [{r.instrument_key}]: {r.error}")

    all_errors = errors or source_fetch_errors
    if all_errors:
        error_lines = [f"  {r.instrument_key}: {r.error}" for r in errors]
        error_lines += [f"  {e}" for e in source_fetch_errors]
        send_telegram(
            f"Legislation Monitor ERROR ({source_used})\n"
            + "\n".join(error_lines)
        )

    if changed:
        lines = []
        for r in changed:
            lines.append(
                f"  {r.instrument_key}\n"
                f"    Was: {r.stored_version or '(unknown)'}\n"
                f"    Now: {r.new_version}"
            )
        msg = (
            f"LEGISLATION CHANGE DETECTED ({source_used})\n"
            f"{len(changed)} instrument(s) updated:\n\n"
            + "\n\n".join(lines)
            + "\n\nVerify on legislation.nsw.gov.au before updating provisions."
            + "\nThen run: python scripts/update_instrument_provisions.py --key <key>"
        )
        print(f"\n{msg}")
        send_telegram(msg)
        sys.exit(2)

    if all_errors and not changed:
        # Don't report success when instruments couldn't be checked
        print(f"\n  ERROR: {total_fetch_errors} instrument(s) could not be verified.")
        sys.exit(1)

    send_telegram(
        f"Legislation Monitor: no changes ({len(checked)} instruments checked via {source_used})"
    )
    print(f"\n  No changes. All instruments current.")
    sys.exit(0)


if __name__ == "__main__":
    main()
