#!/usr/bin/env python3
"""
Scrape LEP land use tables from legislation.nsw.gov.au for all zones in an LEP.

Usage:
    python scripts/scrape_lep_land_use.py --epi epi-2021-0498 --lga Bayside --dry-run
    python scripts/scrape_lep_land_use.py --epi epi-2021-0498 --lga Bayside
"""
import re
import sys
import os
import argparse
from datetime import datetime, timezone
import requests
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

import psycopg2

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'
}


def fetch_lep_html(epi_id: str, local_file: str = None) -> str:
    """Fetch full LEP HTML from legislation.nsw.gov.au or read from local file."""
    if local_file:
        print(f"Reading local file: {local_file}")
        with open(local_file, 'r', encoding='utf-8') as f:
            text = f.read()
        print(f"  {len(text):,} chars")
        return text

    # prior-art-checked: reuses scripts/legislation_monitor.py's own
    # _get_playwright_browser() rather than starting a second browser. Its
    # _fetch_nsw_legislation_version_playwright cannot be reused directly --
    # it returns a VERSION STRING extracted from the page, and this needs the
    # whole HTML to parse land use tables out of. Browser lifecycle stays in
    # one place; only the "what do I want off the page" part differs.
    url = f"https://legislation.nsw.gov.au/view/whole/html/inforce/current/{epi_id}"

    # WHY NOT curl. legislation.nsw.gov.au sits behind a Cloudflare browser
    # challenge -- "Just a moment..." -- and curl, requests and every
    # datacenter IP receive it. Documented in the monitor above: "NSW
    # Legislation HTML scraping removed from auto chain (Jun 2026) - Cloudflare
    # blocks all datacenter IPs (Railway, GitHub Actions)". This script never
    # moved, and nothing told anyone.
    #
    # IT FAILED SILENTLY, WHICH IS WHY IT SAT BROKEN. The challenge page is a
    # valid 200, so curl succeeded, the parser found no tables, and the run
    # printed "TOTAL: 0 zones, 0 use entries" -- indistinguishable from an LEP
    # that genuinely has none. Measured 2026-09-24 against Bayside
    # (epi-2021-0498), which already HAS 20 zones loaded: identical 5,697-char
    # response, identical 0 zones. Every council would have read the same.
    #
    # A real browser clears it, and does NOT need the whitelisted Fly IP:
    # measured the same day from a laptop, epi-2010-0076 returned 1,477,488
    # chars containing the Land Use Table, challenge cleared on the first poll.
    from legislation_monitor import _get_playwright_browser

    print(f"Fetching {url} via Playwright ...")
    ctx = _get_playwright_browser().new_context(user_agent=(
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"))
    try:
        page = ctx.new_page()
        resp = page.goto(url, timeout=60000, wait_until="domcontentloaded")
        if resp is not None and resp.status == 404:
            raise RuntimeError(f"HTTP 404 - EPI id may be wrong: {epi_id}")
        # Polled rather than slept: it cleared on the first poll when measured,
        # and a fixed sleep is either wasted time or too short on a slow day.
        for _ in range(8):
            text = page.content()
            if "Just a moment" not in text:
                break
            page.wait_for_timeout(5000)
        else:
            raise RuntimeError(
                "Cloudflare challenge did not clear after ~40s. This is NOT an "
                "LEP with no zones -- do not read a 0-zone result as one.")
    finally:
        ctx.close()

    print(f"  {len(text):,} chars")
    # The whole point: a challenge page parses to zero zones without erroring,
    # which is the failure that kept this quiet. Refuse rather than return it.
    if len(text) < 50_000:
        raise RuntimeError(
            f"only {len(text):,} chars returned for {epi_id} - far too small for "
            f"a whole LEP, so this is a challenge or error page, not the land "
            f"use tables. Refusing instead of reporting 0 zones.")
    return text


def parse_land_use_tables(html: str) -> dict:
    """
    Parse all zone land use tables from an LEP HTML page.
    Returns {zone_code: {name, permitted_without, permitted_with, prohibited}}.
    """
    soup = BeautifulSoup(html, 'html.parser')
    zones = {}

    # Normalize text: replace non-breaking spaces with regular spaces
    text = soup.get_text(separator='\n')
    text = text.replace('\xa0', ' ')

    # Some LEPs split zone code and name across lines — rejoin them
    text = re.sub(r'(Zone\s+[A-Z][A-Z]?\d?[A-Z]?)\s*\n\s*(?=[A-Z])', r'\1   ', text)

    zone_pattern = re.compile(r'^Zone\s+([A-Z][A-Z]?\d[A-Z]?)\s{2,}(.+)$', re.MULTILINE)
    zone_splits = list(zone_pattern.finditer(text))

    for i, match in enumerate(zone_splits):
        zone_code = match.group(1)
        zone_name = match.group(2).strip()

        start = match.end()
        end = zone_splits[i + 1].start() if i + 1 < len(zone_splits) else len(text)
        section = text[start:end]

        # Extract the three categories
        # End markers: next zone heading, or sections that follow the Land Use Table
        end_marker = r'(?=Permitted with consent|$)'
        end_marker_prohibited = r'(?=Zone\s+[A-Z]|Part\s+\d|Schedule\s+\d|Division\s+\d|Exempt and complying|Principal development standards|$)'
        without_consent = extract_uses(section, r'Permitted without consent[\s:]*\n(.*?)' + end_marker)
        with_consent = extract_uses(section, r'Permitted with consent[\s:]*\n(.*?)(?=Prohibited|$)')
        prohibited = extract_uses(section, r'Prohibited[\s:]*\n(.*?)' + end_marker_prohibited)

        if without_consent or with_consent or prohibited:
            zones[zone_code] = {
                'name': zone_name,
                'permitted_without': without_consent,
                'permitted_with': with_consent,
                'prohibited': prohibited,
            }

    return zones


def extract_uses(section: str, pattern: str) -> list:
    """Extract development type names from a section using regex."""
    m = re.search(pattern, section, re.DOTALL | re.IGNORECASE)
    if not m:
        return []

    block = m.group(1)
    # The text may have uses on one line separated by ; or on separate lines
    # First flatten to one string, then split by ; and \n
    uses = []
    for part in re.split(r'[;\n]', block):
        part = part.strip()
        # Skip empty, Nil, numbered prefixes, objectives text
        if not part or part == 'Nil' or part.startswith('(') or part.startswith('Objective'):
            continue
        # Stop at next section marker
        if re.match(r'^\d+\s+(Objectives|Permitted|Prohibited)', part):
            break
        # Skip fragments like "including any development that is..."
        if part.startswith('including any development'):
            continue
        # Skip PDF header/footer noise (page numbers, legislation metadata)
        if re.match(r'^Page\s+\d+\s+of\s+\d+', part):
            continue
        if 'Local Environmental Plan' in part:
            continue
        if re.match(r'^Current version for', part):
            continue
        if re.match(r'^(accessed|Published)', part, re.IGNORECASE):
            continue
        # Clean up
        part = part.strip(',').strip()
        if part and len(part) > 2 and not part[0].isdigit():
            uses.append(part)

    return uses


def slugify_dev_type(name: str) -> str:
    """Convert 'Dwelling houses' to 'dwelling_houses'."""
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--epi', required=True, help='EPI ID (e.g. epi-2021-0498)')
    parser.add_argument('--lga', required=True, help='LGA name (e.g. Bayside)')
    parser.add_argument('--file', help='Local HTML file path (skips HTTP fetch)')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    html = fetch_lep_html(args.epi, args.file)
    zones = parse_land_use_tables(html)

    total_rows = 0
    for zone_code, data in sorted(zones.items()):
        n_without = len(data['permitted_without'])
        n_with = len(data['permitted_with'])
        n_prohibited = len(data['prohibited'])
        total = n_without + n_with + n_prohibited
        total_rows += total
        print(f"\n  {zone_code} - {data['name']}")
        print(f"    Without consent: {n_without}  With consent: {n_with}  Prohibited: {n_prohibited}")
        if n_without:
            print(f"    Without: {', '.join(data['permitted_without'][:5])}{'...' if n_without > 5 else ''}")
        if n_with:
            print(f"    With:    {', '.join(data['permitted_with'][:5])}{'...' if n_with > 5 else ''}")

    print(f"\n  TOTAL: {len(zones)} zones, {total_rows} use entries")

    if args.dry_run:
        print("\n  [DRY RUN] No database changes.")
        return

    # Insert into lep_land_use_table
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    # Clear existing data for this LGA
    cur.execute("DELETE FROM lep_land_use_table WHERE lga = %s", (args.lga,))
    deleted = cur.rowcount
    print(f"\n  Deleted {deleted} existing rows for {args.lga}")

    inserted = 0
    upsert_sql = """
        INSERT INTO lep_land_use_table (zone, zone_name, lga, development_type, permissibility)
        VALUES (%s, %s, %s, %s, %s)
        ON CONFLICT (zone, lga, development_type) DO UPDATE SET
            permissibility = EXCLUDED.permissibility,
            zone_name = EXCLUDED.zone_name
    """
    for zone_code, data in zones.items():
        zone_name = data['name']
        for dev_type in data['permitted_without']:
            slug = slugify_dev_type(dev_type)
            if slug:
                cur.execute(upsert_sql, (zone_code, zone_name, args.lga, slug, 'exempt'))
                inserted += 1
        for dev_type in data['permitted_with']:
            slug = slugify_dev_type(dev_type)
            if slug:
                cur.execute(upsert_sql, (zone_code, zone_name, args.lga, slug, 'permitted'))
                inserted += 1
        for dev_type in data['prohibited']:
            slug = slugify_dev_type(dev_type)
            if slug:
                cur.execute(upsert_sql, (zone_code, zone_name, args.lga, slug, 'prohibited'))
                inserted += 1

    # Update zone coverage with provenance
    now = datetime.now(timezone.utc)
    source_url = f"https://legislation.nsw.gov.au/view/whole/html/inforce/current/{args.epi}"
    for zone_code in zones:
        cur.execute("""
            INSERT INTO lep_zone_coverage (zone, lga, is_complete, scraped_at, source_url)
            VALUES (%s, %s, true, %s, %s)
            ON CONFLICT (zone, lga) DO UPDATE SET
                is_complete = true, scraped_at = EXCLUDED.scraped_at, source_url = EXCLUDED.source_url
        """, (zone_code, args.lga, now, source_url))

    conn.commit()
    print(f"  Inserted {inserted} rows, updated {len(zones)} zone coverage entries")
    conn.close()


if __name__ == '__main__':
    main()
