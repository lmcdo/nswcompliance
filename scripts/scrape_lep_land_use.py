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

    # Use curl subprocess — requests gets 403 but curl with browser UA works
    import subprocess, tempfile
    url = f"https://legislation.nsw.gov.au/view/whole/html/inforce/current/{epi_id}"
    print(f"Fetching {url} via curl ...")
    tmp = tempfile.NamedTemporaryFile(suffix='.html', delete=False, mode='w')
    tmp.close()
    result = subprocess.run(
        ['curl', '-sL', '-o', tmp.name, '-H',
         'User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36', url],
        capture_output=True, timeout=60
    )
    if result.returncode != 0:
        raise RuntimeError(f"curl failed: {result.stderr}")
    with open(tmp.name, 'r', encoding='utf-8', errors='replace') as f:
        text = f.read()
    os.unlink(tmp.name)
    print(f"  {len(text):,} chars")
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

    # Update zone coverage
    for zone_code in zones:
        cur.execute("""
            INSERT INTO lep_zone_coverage (zone, lga, is_complete)
            VALUES (%s, %s, true)
            ON CONFLICT (zone, lga) DO UPDATE SET is_complete = true
        """, (zone_code, args.lga))

    conn.commit()
    print(f"  Inserted {inserted} rows, updated {len(zones)} zone coverage entries")
    conn.close()


if __name__ == '__main__':
    main()
