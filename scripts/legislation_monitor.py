#!/usr/bin/env python3
"""
Legislation Monitor
===================
Monthly check of NSW planning instruments (SEPPs, LEPs) for version changes.

Auto fallback chain: PCO → AustLII
  NSW Legislation HTML scraping removed from auto chain (Jun 2026) —
  Cloudflare blocks all datacenter IPs (Railway, GitHub Actions).
  Still available via explicit --source nsw_legislation.

Primary source: PCO XML export (legislation.nsw.gov.au/export/week)
  - IP 149.28.176.81 whitelisted (confirmed 2026-05-19 by PCO Website Help)
  - Must run outside Sydney business hours (agreed condition)
  - Returns JSON list of all instruments updated in last 7 days

Fallback source: AustLII consolidated copies (classic.austlii.edu.au)
  - ~7-day lag vs legislation.nsw.gov.au
  - Scrapes "As at DD Month YYYY" date from HTML

Manual source: NSW Legislation individual pages (legislation.nsw.gov.au)
  - Cloudflare-blocked from datacenter IPs as of Jun 2026
  - Only usable via --source nsw_legislation from whitelisted IP

Usage:
    python scripts/legislation_monitor.py               # auto: PCO → AustLII
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
from datetime import date, datetime, timezone
from typing import Optional
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")

import psycopg2
import requests
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env")

# Runbook connector — importable both as a package (pytest, repo root) and as a
# sibling module (when this file is run directly as scripts/legislation_monitor.py).
try:
    from scripts.refresh_runbook import build_refresh_runbook
except ImportError:  # pragma: no cover - direct-run path
    from refresh_runbook import build_refresh_runbook

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

# legislation.nsw.gov.au patterns:
#   "Current version for DD Month YYYY" in the version info bar
#   "Published LW DD.MM.YYYY" in the gazette info
CURRENT_VERSION_PATTERN = re.compile(
    r"Current version for\s+(\d{1,2}\s+\w+\s+\d{4})", re.IGNORECASE
)
PUBLISHED_LW_PATTERN = re.compile(
    r"Published LW\s+(\d{1,2}[\.\s]+\w+[\.\s]+\d{4})", re.IGNORECASE
)


@dataclass
class InstrumentResult:
    instrument_key: str
    instrument_label: str
    changed: bool
    new_version: str | None
    stored_version: str | None
    source: str = ""  # 'pco' or 'austlii'
    error: str | None = None
    stale_notes: tuple = ()


# ── SEPP auto-stale (W3, founder decision 2026-07-29) ───────────────────────
# A version change marks dependent standards rows STALE — not retired. The
# consumers keep serving the last-reviewed values WITH a visible notice; the
# founder clears stale_since/stale_reason during re-verification. The E&C
# Codes SEPP feeds both tables (housing_sepp_standards carries rows citing
# SEPP (E&C) 2008, e.g. secondary-dwelling max_floor_area).
# Each entry: (table, extra WHERE predicate or None). housing_sepp_standards
# carries rows from BOTH instruments (source_document values verified in prod
# 2026-07-29: 'SEPP (Housing) 2021' variants vs '...(Exempt and Complying\n
# Development Codes) 2008'), so each instrument stamps only its OWN rows —
# a Housing amendment must not stale the E&C-derived floor-area standard
# (Sol review of PR #839).
STANDARDS_TABLES_BY_INSTRUMENT = {
    "sepp_exempt_complying_2008": [
        ("cdc_eligibility_standards", None),
        ("housing_sepp_standards",
         "(source_document ILIKE '%exempt%' OR source_document ILIKE '%e&c%')"),
    ],
    "sepp_housing_2021": [
        ("housing_sepp_standards", "source_document ILIKE '%housing%'"),
    ],
}


def mark_dependent_standards_stale(
    conn, instrument_key: str, instrument_label: str,
    old_version: str | None, new_version: str | None,
) -> list[str]:
    """Stamp stale_since/stale_reason on standards rows fed by a changed
    instrument. Only rows not already stale are stamped (the FIRST detected
    change is the one the notice should date from), and only rows the changed
    instrument actually supplies. Returns human-readable lines for the alert;
    empty when the instrument feeds no standards table."""
    notes: list[str] = []
    reason = (
        f"{instrument_label} version changed "
        f"({old_version or 'unknown'} -> {new_version or 'unknown'})"
    )
    cur = conn.cursor()
    for table, predicate in STANDARDS_TABLES_BY_INSTRUMENT.get(instrument_key, []):
        where = "stale_since IS NULL" + (f" AND ({_as_parameterised_sql(predicate)})" if predicate else "")
        cur.execute(
            f"UPDATE {table} SET stale_since = NOW(), stale_reason = %s WHERE {where}",
            (reason,),
        )
        if cur.rowcount:
            notes.append(
                f"  {table}: {cur.rowcount} standards row(s) marked STALE — "
                f"served with a notice until re-checked"
            )
    cur.close()
    return notes


# prior-art-checked: reuse not viable as-is -- this EXTENDS the existing W3 auto-stale code in this same file
# (STANDARDS_TABLES_BY_INSTRUMENT and mark_dependent_standards_stale), reusing its table map, predicates and
# notice wording. dq_probe_live.py's DQ-96 probe only counts the gap; the other flagged files neither stamp
# stale_since nor read instrument_registry.needs_review.
def _as_parameterised_sql(predicate: str) -> str:
    """A STANDARDS_TABLES_BY_INSTRUMENT predicate, ready for a statement that also takes %s parameters.

    psycopg2 formats every % in such a statement, so "ILIKE '%housing%'" read '%h' as a placeholder and
    raised IndexError (checked with cursor.mogrify, 2026-09-14). The first SEPP Housing or E&C Codes change
    detected after #839 would have raised inside check_instrument: the instrument logged as an error rather
    than reported as changed, and its standards rows left with no notice. Doubling each % sends it through
    as a literal."""
    return predicate.replace("%", "%%")


def backfill_stale_for_flagged_instruments(conn) -> list[str]:
    """Stamp the standards rows an ALREADY-flagged amendment should have staled.

    mark_dependent_standards_stale runs only when a check sees a version change happen, so an instrument
    flagged before that path existed (#839, 2026-07-29) was never stamped. On 2026-09-14, 33 SEPP Housing
    standards stored before its 2026-05-15 change, and 2 tied to the E&C Codes SEPP, were served with no
    notice (DQ-96). This runs on every monitor run, so the gap cannot recur for the next instrument.

    Stamps only rows stored BEFORE the detected change (a row stored afterwards may already reflect the
    amended text), only rows with no notice yet (the first notice wins), and dates the notice from the
    change, not from today. Returns lines for the log."""
    notes: list[str] = []
    cur = conn.cursor()
    try:
        for instrument_key, tables in STANDARDS_TABLES_BY_INSTRUMENT.items():
            cur.execute(
                "SELECT instrument_label, current_version, last_changed FROM instrument_registry "
                "WHERE instrument_key = %s AND is_active AND needs_review AND last_changed IS NOT NULL",
                (instrument_key,),
            )
            flagged = cur.fetchone()
            if flagged is None:
                continue
            label, current_version, last_changed = flagged
            reason = (
                f"{label} version changed (detected {last_changed:%Y-%m-%d}; now "
                f"{current_version or 'unknown'}). This standard was stored before that change "
                f"and has not been re-checked."
            )
            for table, predicate in tables:
                where = "stale_since IS NULL AND created_at < %s" + (
                    f" AND ({_as_parameterised_sql(predicate)})" if predicate else "")
                cur.execute(
                    f"UPDATE {table} SET stale_since = %s, stale_reason = %s WHERE {where}",
                    (last_changed, reason, last_changed),
                )
                if cur.rowcount:
                    notes.append(
                        f"  {table}: {cur.rowcount} standards row(s) stored before the {label} change "
                        f"marked STALE — served with a notice until re-checked"
                    )
    finally:
        cur.close()
    return notes


def send_telegram(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        print("[telegram] skipped — no token or chat_id")
        return
    original_len = len(message)
    if original_len > 4000:
        message = message[:3950] + "\n\n… (truncated — full output in Railway logs)"
    print(f"[telegram] sending message ({original_len} chars, truncated={original_len > 4000})")
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=10,
        )
        if resp.ok:
            print(f"[telegram] sent OK ({resp.status_code})")
        else:
            print(f"[telegram] HTTP {resp.status_code}: {resp.text[:200]}")
    except Exception as exc:
        print(f"[telegram] send failed: {exc}")


# ---------------------------------------------------------------------------
# PCO source
# ---------------------------------------------------------------------------

def check_via_pco(instruments: list[dict]) -> dict[str, str | None]:
    """Check instruments via PCO export feed.

    Uses get_changes_since() with a 35-day window so monthly runs never
    miss amendments.  Falls back to get_weekly_changes() if the custom
    query fails.

    Returns dict of {instrument_key: new_version_string_or_None}.
    Raises on access denied or connection error.
    """
    from datetime import datetime, timedelta
    from pco_client import PCOAccessDenied, get_changes_since, get_weekly_changes

    since = (datetime.utcnow() - timedelta(days=35)).strftime("%Y%m%d000000")
    try:
        changes = get_changes_since(since)
        print(f"    PCO: {len(changes)} instruments changed in last 35 days (since {since[:8]})")
    except Exception as exc:
        print(f"    PCO: custom date query failed ({exc}), falling back to weekly")
        changes = get_weekly_changes()
        print(f"    PCO: {len(changes)} instruments changed this week (fallback)")

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
# legislation.nsw.gov.au source (preferred over AustLII — more stable)
# ---------------------------------------------------------------------------


class DownloadTriggeredError(Exception):
    """Raised when legislation.nsw.gov.au serves a download instead of HTML."""
    pass


def check_via_nsw_legislation(
    instruments: list[dict],
) -> tuple[dict[str, str | None], list[str]]:
    """Check instruments via legislation.nsw.gov.au (official NSW source).

    IP 149.28.176.81 whitelisted by PCO (confirmed 2026-05-19).
    Uses plain HTTP requests. Falls back to Playwright if HTTP fails (403).

    Returns (version_map, fetch_errors).
    """
    results: dict[str, str | None] = {}
    fetch_errors: list[str] = []

    for inst in instruments:
        key = inst["instrument_key"]
        url = inst.get("legislation_url")
        if not url:
            print(f"    {key} — no legislation_url mapped, skipping")
            results[key] = None
            continue

        try:
            version = _fetch_nsw_legislation_version_http(url)
            results[key] = version
            print(f"    NSW Legislation: {key} → {version or '(not found)'}")
        except DownloadTriggeredError:
            print(f"    [DOWNLOAD] {key}: page serves download, not HTML")
            results[key] = None
            fetch_errors.append(f"{key}: download triggered (manual check needed)")
            send_telegram(
                f"Legislation Monitor: {key} triggers download\n"
                f"  URL: {url}\n"
                f"  EPI ID may be wrong — check legislation.nsw.gov.au manually\n"
                f"  and update instrument_registry.legislation_url"
            )
        except Exception as exc:
            print(f"    [ERROR] {key}: {exc}")
            results[key] = None
            fetch_errors.append(f"{key}: {exc}")
        # 5s between requests to avoid Cloudflare rate-limiting
        time.sleep(5)

    return results, fetch_errors


def _extract_latest_pit_date(html: str, url: str) -> str | None:
    """Extract the most recent point-in-time version date from the page.

    legislation.nsw.gov.au embeds links like:
      /view/html/inforce/2026-03-13/epi-...
      /view/whole/html/inforce/2026-03-13/epi-...
    in the version timeline and "View whole" links. The most recent date is
    the actual last-amended date, unlike the "Current version for" header
    which advances with time even when the instrument hasn't changed.
    """
    # Extract EPI ID from the URL (e.g. "epi-2008-0572")
    epi_match = re.search(r"(epi-\d{4}-\d+)", url)
    if not epi_match:
        return None

    epi_id = epi_match.group(1)
    # Find all point-in-time links — both fragment and whole-document views:
    #   /view/html/inforce/YYYY-MM-DD/epi-...
    #   /view/whole/html/inforce/YYYY-MM-DD/epi-...
    pit_pattern = re.compile(
        rf"/view/(?:whole/)?html/inforce/(\d{{4}}-\d{{2}}-\d{{2}})/{re.escape(epi_id)}"
    )
    dates = pit_pattern.findall(html)

    # Also check pointInTime URL parameter (e.g. ?pointInTime=2026-04-24)
    pit_param = re.findall(r"pointInTime=(\d{4}-\d{2}-\d{2})", html)
    dates.extend(pit_param)

    if not dates:
        return None

    # Most recent date = last amendment commencement
    latest_iso = sorted(set(dates))[-1]
    # Convert 2026-03-13 → "13 March 2026" to match stored format
    dt = datetime.strptime(latest_iso, "%Y-%m-%d")
    return dt.strftime("%-d %B %Y") if sys.platform != "win32" else dt.strftime("%d %B %Y").lstrip("0")


def _fetch_nsw_legislation_version_http(url: str) -> str | None:
    """Fetch version date from legislation.nsw.gov.au using plain HTTP.

    IP 149.28.176.81 whitelisted by PCO (confirmed 2026-05-19).
    Falls back to Playwright if HTTP returns 403.

    Prefers point-in-time version dates (actual amendment dates) over the
    "Current version for" header which advances with time even when the
    instrument hasn't been amended.
    """
    resp = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)

    if resp.status_code == 403:
        # IP may not be active on this machine — fall back to Playwright
        print(f"    HTTP 403 — falling back to Playwright for {url}")
        return _fetch_nsw_legislation_version_playwright(url)
    if resp.status_code == 404:
        raise RuntimeError(f"HTTP 404 — EPI ID may be wrong: {url}")
    if resp.status_code != 200:
        raise RuntimeError(f"HTTP {resp.status_code}: {url}")

    # Check for download response (not HTML)
    ct = resp.headers.get("Content-Type") or ""
    if "html" not in ct and "text" not in ct:
        raise DownloadTriggeredError(
            f"Page serves download ({ct}) instead of HTML — "
            f"manual check needed: {url}"
        )

    return _extract_version_from_html(resp.text, url)


def _fetch_nsw_legislation_version_playwright(url: str) -> str | None:
    """Playwright fallback for legislation.nsw.gov.au when HTTP fails."""
    browser = _get_playwright_browser()
    ctx = browser.new_context(
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/125.0.0.0 Safari/537.36"
        ),
        accept_downloads=True,
    )
    page = ctx.new_page()
    try:
        resp = page.goto(url, timeout=45000, wait_until="domcontentloaded")
        if resp and resp.status == 404:
            raise RuntimeError(f"HTTP 404 — EPI ID may be wrong: {url}")

        # Wait for Cloudflare challenge to resolve — the challenge page has
        # title "Just a moment..." and its own <h1>. Poll until the real page
        # appears or timeout after ~30s.
        for attempt in range(6):
            html = page.content()
            if "Just a moment" not in html:
                break
            print(f"    Cloudflare challenge detected, waiting... (attempt {attempt + 1}/6)")
            time.sleep(5)
        else:
            raise RuntimeError(
                f"Cloudflare challenge did not resolve after 30s: {url}"
            )

        # Wait for actual legislation content to render
        try:
            page.wait_for_selector(
                ".legislation-title, #content, .legislation-body",
                timeout=10000,
            )
        except Exception:
            pass  # Content may already be in the HTML from goto
        time.sleep(1)
        html = page.content()
    except Exception as exc:
        if "Download is starting" in str(exc):
            raise DownloadTriggeredError(
                f"Page triggers download instead of rendering HTML — "
                f"manual check needed: {url}"
            ) from exc
        raise
    finally:
        ctx.close()

    return _extract_version_from_html(html, url)


def _extract_version_from_html(html: str, url: str) -> str | None:
    """Extract version date from legislation.nsw.gov.au HTML."""
    # Prefer point-in-time version date (actual amendment date, not rolling header)
    pit_date = _extract_latest_pit_date(html, url)
    if pit_date:
        return pit_date

    # Fallback: "Current version for DD Month YYYY" header
    # NOTE: this advances with time even without amendments — may cause false positives
    m = CURRENT_VERSION_PATTERN.search(html)
    if m:
        return m.group(1)

    # Try "Published LW" pattern
    m = PUBLISHED_LW_PATTERN.search(html)
    if m:
        return m.group(1)

    # Try "As at" pattern (some pages use this)
    m = AS_AT_PATTERN.search(html)
    if m:
        return m.group(1)

    # Log a snippet of the HTML for debugging
    snippet = html[:500].replace("\n", " ").strip()
    raise RuntimeError(
        f"No version date pattern found on page — "
        f"legislation.nsw.gov.au may have changed format: {url}\n"
        f"  Tried: PIT links, pointInTime param, 'Current version for', "
        f"'Published LW', 'As at'\n"
        f"  HTML snippet: {snippet[:200]}..."
    )


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
    try:
        page.goto(url, timeout=45000, wait_until="domcontentloaded")

        # Wait for Cloudflare challenge to resolve (same as NSW Legislation)
        for attempt in range(6):
            html = page.content()
            if "Just a moment" not in html:
                break
            print(f"    AustLII Cloudflare challenge, waiting... (attempt {attempt + 1}/6)")
            time.sleep(5)
        else:
            raise RuntimeError(
                f"AustLII Cloudflare challenge did not resolve after 30s: {url}"
            )

        # Try multiple selectors — AustLII may have redesigned.
        # "As at" is the classic format; "Current version" is an alternative.
        for selector in ["text=As at", "text=Current version", "text=In force", "pre", "h1"]:
            try:
                page.wait_for_selector(selector, timeout=10000)
                break
            except Exception:
                continue
        # Give JS a moment to finish rendering
        time.sleep(2)
        html = page.content()
    finally:
        ctx.close()

    m = AS_AT_PATTERN.search(html)
    if m:
        return m.group(1)

    # Try alternative patterns
    m = CURRENT_VERSION_PATTERN.search(html)
    if m:
        return m.group(1)

    # Log snippet for debugging
    snippet = html[:300].replace("\n", " ").strip()
    raise RuntimeError(
        f"Playwright loaded page but no version date pattern found — "
        f"AustLII may have changed format: {url}\n"
        f"  HTML snippet: {snippet[:200]}..."
    )


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

_MONTHS = {m.lower(): i for i, m in enumerate(
    ["January", "February", "March", "April", "May", "June", "July", "August",
     "September", "October", "November", "December"], start=1)}
_VERSION_DATE_RE = re.compile(
    r"\b(\d{1,2})\s+(" + "|".join(_MONTHS) + r")\s+((?:19|20)\d{2})\b", re.I)


def parse_version_date(version: Optional[str]) -> Optional[date]:
    """Turn a version label like '15 May 2026' into a date, or None.

    instrument_registry.version_date is a column that existed and was NEVER
    written by anything (repo-wide grep, 2026-08-16), while current_version
    carried a readable date as text on 25 of 26 active instruments. That is the
    currency date of every LEP and SEPP we monitor, sitting one column away
    from being usable.

    STRICT ON PURPOSE. Only an explicit 'D Month YYYY' phrase parses. A bare
    year, a version number, or anything else returns None and leaves the column
    empty, because a guessed currency date is worse than an absent one — the
    same rule that retired the old version-label parser. wingecarribee_lep_2010
    has no current_version at all (no pco_instrument_id, the known DQ-69 floor)
    and correctly stays NULL.
    """
    if not version:
        return None
    m = _VERSION_DATE_RE.search(version)
    if not m:
        return None
    day, month, year = int(m.group(1)), _MONTHS[m.group(2).lower()], int(m.group(3))
    try:
        return date(year, month, day)
    except ValueError:  # 31 February and friends
        return None


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
        # Source didn't return data for this instrument. Two very different
        # cases hide here, and conflating them is why last_checked sat frozen
        # at 2026-06-08 while the monitor reported "Checked: 26" (2026-08-14):
        #
        #  a) CONFIRMED UNCHANGED — check_via_pco seeds its result with EVERY
        #     instrument_key -> None and fills in only the ones its complete
        #     35-day export lists as amended. Absence is therefore an
        #     affirmative "not amended in the window", and the run HAS
        #     confirmed this instrument. Record that.
        #  b) NOT COVERED — an instrument with no pco_instrument_id can never
        #     appear in that export (pco_to_key is built only from instruments
        #     that have one), so PCO's silence about it says nothing at all.
        #     Writing last_checked here would fabricate a confirmation.
        #     Live case: wingecarribee_lep_2010, the one row that has never
        #     been checked. It must STAY unchecked, not be quietly marked.
        #
        # Only PCO is authoritative-for-absence. The nsw_legislation and
        # austlii paths fetch per instrument, so a None there is a miss, not a
        # confirmation, and must not stamp either.
        confirmed_unchanged = (
            source == "pco" and bool(instrument.get("pco_instrument_id"))
        )
        if confirmed_unchanged and not dry_run:
            cur = conn.cursor()
            cur.execute(
                "UPDATE instrument_registry "
                "SET last_checked = %s, check_failures = 0 "
                "WHERE instrument_key = %s",
                (datetime.now(timezone.utc), key),
            )
            conn.commit()
            cur.close()
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

    stale_notes: list[str] = []
    if changed:
        print(f"  {key} [{source}]")
        print(f"    [CHANGED] {stored_version} → {new_version}")
        if not dry_run:
            cur.execute(
                """
                UPDATE instrument_registry
                SET current_version = %s, version_date = %s, last_checked = %s,
                    last_changed = %s, needs_review = TRUE,
                    check_failures = 0
                WHERE instrument_key = %s
                """,
                (new_version, parse_version_date(new_version), now, now, key),
            )
            # Auto-stale dependent standards (W3): last-reviewed values keep
            # serving WITH a notice; founder clears on re-verification.
            stale_notes = mark_dependent_standards_stale(
                conn, key, label, stored_version, new_version,
            )
            for note in stale_notes:
                print(f"  {note}")
            conn.commit()
    else:
        status = "(first run — baseline set)" if first_run else "[unchanged]"
        print(f"  {key} [{source}] {status}")
        if not dry_run:
            cur.execute(
                """
                UPDATE instrument_registry
                SET current_version = %s, version_date = %s,
                    last_checked = %s, check_failures = 0
                WHERE instrument_key = %s
                """,
                (new_version or stored_version,
                 parse_version_date(new_version or stored_version), now, key),
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
        stale_notes=tuple(stale_notes),
    )


def main():
    parser = argparse.ArgumentParser(description="Monthly SEPP/LEP change monitor")
    parser.add_argument("--key", help="Check specific instrument_key only")
    parser.add_argument("--dry-run", action="store_true", help="No DB writes")
    parser.add_argument(
        "--source", choices=["auto", "pco", "nsw_legislation", "austlii"],
        default="auto",
        help="Force data source (default: auto — try PCO, fall back to "
             "AustLII. nsw_legislation only via explicit flag)",
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
    # Auto chain: PCO → AustLII (nsw_legislation HTML scraping removed from
    # auto chain — Cloudflare blocks all datacenter IPs as of Jun 2026).
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
            # Auto mode — skip nsw_legislation (Cloudflare-blocked), go to AustLII
            print(f"  PCO unavailable ({exc}), falling back to AustLII...")
            source_used = "austlii"

    if source_used == "nsw_legislation":
        # Only reached via explicit --source nsw_legislation (not auto)
        print(f"\n  Source: NSW Legislation (legislation.nsw.gov.au) — authoritative")
        try:
            version_map, source_fetch_errors = check_via_nsw_legislation(instruments)
        except Exception as exc:
            print(f"\n  [ERROR] NSW Legislation failed: {exc}")
            send_telegram(f"Legislation Monitor ERROR\nNSW Legislation failed: {exc}")
            conn.close()
            sys.exit(1)
        # If every instrument failed, report clearly instead of silent zeros
        all_none = all(v is None for v in version_map.values())
        if all_none and source_fetch_errors:
            print(f"\n  All {len(source_fetch_errors)} instruments failed — NSW Legislation fully blocked")
            send_telegram(
                f"Legislation Monitor ERROR (nsw_legislation)\n"
                f"All {len(source_fetch_errors)} instruments failed (Cloudflare?)\n"
                + "\n".join(f"  {e}" for e in source_fetch_errors[:5])
            )
            conn.close()
            sys.exit(1)

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

    # Every run, whatever the source said: an instrument already flagged before the fresh-change path could
    # stamp its standards (DQ-96) gets them stamped here. Independent of this run's fetches, so a fetch
    # failure above does not skip it; a failure here is reported, never allowed to hide the checks above.
    try:
        backfill_notes = backfill_stale_for_flagged_instruments(conn)
        if args.dry_run:
            conn.rollback()
        else:
            conn.commit()
        for note in backfill_notes:
            print(f"  [stale backfill]{' (dry run, rolled back)' if args.dry_run else ''} {note.strip()}")
    except Exception as exc:
        conn.rollback()
        print(f"  [stale backfill] ERROR {exc}")
        send_telegram(f"Legislation Monitor ERROR\nStale-notice backfill failed: {exc}")

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
            entry = (
                f"  {r.instrument_key}\n"
                f"    Was: {r.stored_version or '(unknown)'}\n"
                f"    Now: {r.new_version}"
            )
            if r.stale_notes:
                entry += "\n" + "\n".join(r.stale_notes)
            lines.append(entry)
        msg = (
            f"LEGISLATION CHANGE DETECTED ({source_used})\n"
            f"{len(changed)} instrument(s) updated:\n\n"
            + "\n\n".join(lines)
            + "\n\nVerify on legislation.nsw.gov.au before updating provisions."
            # Scoped, ready-to-run refresh chain per changed instrument (LEP =
            # per-LGA re-ingest+recompute; SEPP = statewide note). Closes the
            # detection -> recompute loop without auto-executing anything.
            + build_refresh_runbook([(r.instrument_key, r.instrument_label) for r in changed])
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
