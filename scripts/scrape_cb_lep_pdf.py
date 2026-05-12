#!/usr/bin/env python3
"""
Parse Canterbury-Bankstown LEP 2023 land use tables from PDF.
The CB LEP isn't available as server-rendered HTML on legislation.nsw.gov.au,
so we parse the PDF directly with PyMuPDF.

Usage:
    python scripts/scrape_cb_lep_pdf.py --dry-run
    python scripts/scrape_cb_lep_pdf.py
"""
import re
import os
import sys
import argparse
from datetime import datetime, timezone
import fitz  # PyMuPDF

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

PDF_PATH = os.path.join(
    os.path.expanduser('~'), 'Downloads',
    'canterbury bankstown epi-2023-0336.pdf'
)
LGA = 'Canterbury-Bankstown'


def extract_text(pdf_path: str) -> str:
    doc = fitz.open(pdf_path)
    text = ''
    for page in doc:
        page_text = page.get_text()
        # Strip PDF header/footer noise
        page_text = re.sub(r'Canterbury-Bankstown Local Environmental Plan 2023 \[NSW\]', '', page_text)
        page_text = re.sub(r'Current version for .+?\)', '', page_text)
        page_text = re.sub(r'Page \d+ of \d+', '', page_text)
        text += page_text + '\n'
    return text


def parse_zones(text: str) -> dict:
    zones = {}
    # PDF zone headings: "Zone R2\nLow Density Residential" or "Zone R2 Low Density Residential"
    # Rejoin split headings
    text = re.sub(r'(Zone\s+[A-Z][A-Z]?\d[A-Z]?)\s*\n\s*(?=[A-Z])', r'\1  ', text)

    zone_pattern = re.compile(r'^Zone\s+([A-Z][A-Z]?\d[A-Z]?)\s+([A-Z][A-Za-z][^\n]+)$', re.MULTILINE)
    matches = list(zone_pattern.finditer(text))

    for i, match in enumerate(matches):
        zone_code = match.group(1)
        zone_name = match.group(2).strip()
        # Truncate at TOC dots
        zone_name = re.split(r'\.{3,}', zone_name)[0].strip()

        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        section = text[start:end]

        # Only process actual land use table entries (have consent categories)
        if not re.search(r'Permitted (without|with) consent', section, re.IGNORECASE):
            continue

        without = extract_uses(section, r'Permitted without consent[\s:]*\n(.*?)(?=Permitted with consent|$)')
        with_c = extract_uses(section, r'Permitted with consent[\s:]*\n(.*?)(?=Prohibited|$)')
        prohibited = extract_uses(section, r'Prohibited[\s:]*\n(.*?)(?=Zone\s+[A-Z]|$)')

        if (without or with_c or prohibited) and zone_code not in zones:
            zones[zone_code] = {
                'name': zone_name,
                'permitted_without': without,
                'permitted_with': with_c,
                'prohibited': prohibited,
            }

    return zones


def extract_uses(section: str, pattern: str) -> list:
    m = re.search(pattern, section, re.DOTALL | re.IGNORECASE)
    if not m:
        return []
    block = m.group(1)
    uses = []
    for part in re.split(r'[;\n]', block):
        part = part.strip()
        if not part or part == 'Nil' or part.startswith('(') or part.startswith('Objective'):
            continue
        if re.match(r'^\d+\s+(Objectives|Permitted|Prohibited)', part):
            break
        if part.startswith('including any development'):
            continue
        part = part.strip(',').strip()
        if part and len(part) > 2 and not part[0].isdigit():
            uses.append(part)
    return uses


def slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf', default=PDF_PATH)
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args()

    print(f"Reading PDF: {args.pdf}")
    text = extract_text(args.pdf)
    print(f"  {len(text):,} chars extracted")

    zones = parse_zones(text)

    total_rows = 0
    for zone_code, data in sorted(zones.items()):
        n_without = len(data['permitted_without'])
        n_with = len(data['permitted_with'])
        n_prohibited = len(data['prohibited'])
        total = n_without + n_with + n_prohibited
        total_rows += total
        print(f"\n  {zone_code} - {data['name']}")
        print(f"    Without consent: {n_without}  With consent: {n_with}  Prohibited: {n_prohibited}")

    print(f"\n  TOTAL: {len(zones)} zones, {total_rows} use entries")

    if args.dry_run:
        print("\n  [DRY RUN] No database changes.")
        return

    import psycopg2
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    cur = conn.cursor()

    cur.execute("DELETE FROM lep_land_use_table WHERE lga = %s", (LGA,))
    print(f"\n  Deleted {cur.rowcount} existing rows for {LGA}")

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
            slug = slugify(dev_type)
            if slug:
                cur.execute(upsert_sql, (zone_code, zone_name, LGA, slug, 'exempt'))
                inserted += 1
        for dev_type in data['permitted_with']:
            slug = slugify(dev_type)
            if slug:
                cur.execute(upsert_sql, (zone_code, zone_name, LGA, slug, 'permitted'))
                inserted += 1
        for dev_type in data['prohibited']:
            slug = slugify(dev_type)
            if slug:
                cur.execute(upsert_sql, (zone_code, zone_name, LGA, slug, 'prohibited'))
                inserted += 1

    now = datetime.now(timezone.utc)
    source_url = "https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2023-0252"
    for zone_code in zones:
        cur.execute("""
            INSERT INTO lep_zone_coverage (zone, lga, is_complete, scraped_at, source_url)
            VALUES (%s, %s, true, %s, %s)
            ON CONFLICT (zone, lga) DO UPDATE SET
                is_complete = true, scraped_at = EXCLUDED.scraped_at, source_url = EXCLUDED.source_url
        """, (zone_code, LGA, now, source_url))

    conn.commit()
    print(f"  Inserted {inserted} rows, updated {len(zones)} zone coverage entries")
    conn.close()


if __name__ == '__main__':
    main()
