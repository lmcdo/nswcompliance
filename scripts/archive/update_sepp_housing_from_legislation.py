#!/usr/bin/env python3
"""
SEPP Housing 2021 — Targeted Currency Update
=============================================
Fetches the current consolidated SEPP Housing from NSW Legislation,
extracts text for clauses changed by EPIs 512/597/647/684,
and updates those provisions directly in the database.

No diffing against old text. Authoritative source overwrites DB.

Usage:
    python3 scripts/update_sepp_housing_from_legislation.py --dry-run   # Show what would change
    python3 scripts/update_sepp_housing_from_legislation.py --update    # Apply updates
"""

import sys, re, os, argparse, hashlib
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import psycopg2
from dotenv import load_dotenv
from urllib.request import urlopen, Request
from html.parser import HTMLParser

load_dotenv()

NSW_LEGISLATION_URL = 'https://legislation.nsw.gov.au/view/whole/html/inforce/current/epi-2021-0714'

# Clauses changed by EPIs 512/597/647/684
# These are the ONLY provisions we touch
AFFECTED_CLAUSES = {
    '15C': 'Group homes — development to which division applies',
    '42': 'Complying development — group homes division applicability',
    '61': 'Development in prescribed zones — group homes',
    '64': 'Complying development — group homes standards',
    '74': 'Non-discretionary development standards (parking rates)',
    '87': 'Additional floor space ratios — seniors housing',
    '90': 'Subdivision',
}

AFFECTED_DEFINITIONS = [
    'low and mid rise housing area',
    'low and mid rise housing inner area',
    'low and mid rise housing outer area',
]


class TextExtractor(HTMLParser):
    """Extract text from HTML preserving block boundaries as newlines."""
    BLOCK_TAGS = {'div', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li',
                  'tr', 'dt', 'dd', 'section', 'article', 'blockquote', 'pre', 'br'}

    def __init__(self):
        super().__init__()
        self.text = []
        self.in_body = False
        self.skip_tags = {'script', 'style', 'nav', 'header', 'footer', 'noscript'}
        self.skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag == 'body':
            self.in_body = True
        if tag in self.skip_tags:
            self.skip_depth += 1
        if self.in_body and self.skip_depth == 0 and tag in self.BLOCK_TAGS:
            self.text.append('\n')

    def handle_endtag(self, tag):
        if tag in self.skip_tags and self.skip_depth > 0:
            self.skip_depth -= 1
        if self.in_body and self.skip_depth == 0 and tag in self.BLOCK_TAGS:
            self.text.append('\n')

    def handle_data(self, data):
        if self.in_body and self.skip_depth == 0:
            self.text.append(data)

    def get_text(self):
        text = ''.join(self.text)
        return re.sub(r'\n{3,}', '\n\n', text)


def fetch_current_text():
    """Fetch and extract plain text from current consolidated SEPP Housing."""
    print("Fetching current SEPP Housing from NSW Legislation...")
    req = Request(NSW_LEGISLATION_URL, headers={
        'User-Agent': 'Mozilla/5.0 (compliance-engine research tool)',
        'Accept': 'text/html',
    })
    response = urlopen(req, timeout=30)
    html = response.read().decode('utf-8')
    parser = TextExtractor()
    parser.feed(html)
    text = parser.get_text()
    print(f"  Fetched {len(text)} chars of clean text")
    return text


def extract_clause(text: str, clause_num: str) -> str:
    """Extract a clause block: starts at 'N  Title', ends at next clause heading."""
    escaped = re.escape(clause_num)
    pattern = rf'^\s*{escaped}\s+[A-Z].*?(?=^\s*\d+[A-Z]?\s+[A-Z]|\Z)'
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL)
    return match.group(0).strip() if match else ''


def extract_definition(text: str, term: str) -> str:
    """Extract a definition block: 'term means...' until next definition."""
    escaped = re.escape(term)
    pattern = rf'^\s*{escaped}\s+means.*?(?=^\s*[a-z].*\s+means|\Z)'
    match = re.search(pattern, text, re.MULTILINE | re.DOTALL | re.IGNORECASE)
    return match.group(0).strip()[:3000] if match else ''


def find_provisions_in_db(conn, clause_nums: list) -> dict:
    """
    Find provisions in regulatory_provisions matching these clause numbers.
    Returns {ref_number: [{id, provision_text, ...}]}
    """
    cur = conn.cursor()
    placeholders = ','.join(['%s'] * len(clause_nums))
    cur.execute(
        "SELECT id, ref_number, provision_text, document_id, section_header "
        "FROM regulatory_provisions "
        "WHERE document_id LIKE '%%Housing%%2021%%' "
        f"AND ref_number IN ({placeholders}) "
        "ORDER BY ref_number",
        clause_nums
    )
    results = {}
    for row in cur.fetchall():
        ref = row[1]
        results.setdefault(ref, []).append({
            'id': row[0],
            'ref_number': row[1],
            'provision_text': row[2],
            'document_id': row[3],
            'section_header': row[4],
        })
    cur.close()
    return results


def find_definition_provisions(conn, terms: list) -> dict:
    """
    Find provisions that ARE the definitions (not just references to them).
    Only match rows where provision_text starts with the definition term + 'means'.
    """
    cur = conn.cursor()
    results = {}
    for term in terms:
        cur.execute(
            "SELECT id, ref_number, provision_text, document_id, section_header "
            "FROM regulatory_provisions "
            "WHERE document_id LIKE '%%Housing%%2021%%' "
            "AND provision_text LIKE %s",
            (f'{term} means%',)
        )
        for row in cur.fetchall():
            results.setdefault(term, []).append({
                'id': row[0],
                'ref_number': row[1],
                'provision_text': row[2][:200] if row[2] else None,
                'document_id': row[3],
                'section_header': row[4],
            })
    cur.close()
    return results


def update_provisions(conn, updates: list):
    """Update provision_text for specific provision IDs."""
    cur = conn.cursor()
    for update in updates:
        cur.execute("""
            UPDATE regulatory_provisions
            SET provision_text = %s,
                last_updated = NOW()
            WHERE id = %s
        """, (update['new_text'], update['id']))
    conn.commit()
    print(f"  Updated {cur.rowcount} provisions")
    cur.close()


def update_document_sections(conn, current_text: str):
    """
    Replace full_text in documents table for SEPP Housing sections
    with clean HTML-extracted text. This is the authoritative update.
    """
    cur = conn.cursor()

    # Update the main unsplit document
    cur.execute("""
        UPDATE documents
        SET full_text = %s,
            version_status = 'current',
            amendment_reference = 'EPIs 512/597/647/684 (Dec 2025)',
            last_verified_date = CURRENT_DATE
        WHERE id = 'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation'
    """, (current_text,))
    print(f"  Updated main document full_text ({cur.rowcount} row)")

    # Mark all section splits as current too
    cur.execute("""
        UPDATE documents
        SET version_status = 'current',
            amendment_reference = 'EPIs 512/597/647/684 (Dec 2025)',
            last_verified_date = CURRENT_DATE
        WHERE pdf_name LIKE '%Housing%2021%'
          AND id != 'State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation'
    """)
    print(f"  Marked {cur.rowcount} section splits as current")

    conn.commit()
    cur.close()


def main():
    parser = argparse.ArgumentParser(description='Update SEPP Housing provisions from NSW Legislation')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without changing DB')
    parser.add_argument('--update', action='store_true', help='Apply updates to DB')
    args = parser.parse_args()

    if not args.dry_run and not args.update:
        print("Specify --dry-run or --update")
        return

    # Step 1: Fetch authoritative current text
    current_text = fetch_current_text()

    # Step 2: Extract affected clause texts from current version
    print("\nExtracting affected clauses from current version...")
    clause_texts = {}
    for clause_num, description in AFFECTED_CLAUSES.items():
        extracted = extract_clause(current_text, clause_num)
        if extracted:
            clause_texts[clause_num] = extracted
            print(f"  §{clause_num}: {len(extracted)} chars ({description})")
        else:
            print(f"  §{clause_num}: NOT EXTRACTED — needs manual check")

    definition_texts = {}
    for term in AFFECTED_DEFINITIONS:
        extracted = extract_definition(current_text, term)
        if extracted:
            definition_texts[term] = extracted
            print(f"  DEF '{term}': {len(extracted)} chars")
        else:
            print(f"  DEF '{term}': NOT EXTRACTED")

    # Step 3: Find matching provisions in DB
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL')
    conn = psycopg2.connect(db_url)

    print("\nLooking up provisions in database...")
    db_clauses = find_provisions_in_db(conn, list(clause_texts.keys()))
    db_definitions = find_definition_provisions(conn, list(definition_texts.keys()))

    # Report what was found
    print(f"\n  Clause provisions in DB: {sum(len(v) for v in db_clauses.values())} rows across {len(db_clauses)} clauses")
    print(f"  Definition provisions in DB: {sum(len(v) for v in db_definitions.values())} rows across {len(db_definitions)} terms")

    # Show what's NOT in DB
    missing_clauses = set(clause_texts.keys()) - set(db_clauses.keys())
    if missing_clauses:
        print(f"\n  Clauses not in regulatory_provisions: {missing_clauses}")
        print("  These may not have been extracted as individual provisions.")

    missing_defs = set(definition_texts.keys()) - set(db_definitions.keys())
    if missing_defs:
        print(f"  Definitions not in regulatory_provisions: {missing_defs}")

    # Step 4: Apply updates
    updates = []

    for clause_num, provisions in db_clauses.items():
        new_text = clause_texts.get(clause_num)
        if not new_text:
            continue
        for prov in provisions:
            updates.append({
                'id': prov['id'],
                'ref_number': clause_num,
                'new_text': new_text,
                'old_text': prov['provision_text'][:100] if prov['provision_text'] else '(none)',
            })

    for term, provisions in db_definitions.items():
        new_text = definition_texts.get(term)
        if not new_text:
            continue
        for prov in provisions:
            updates.append({
                'id': prov['id'],
                'ref_number': prov['ref_number'],
                'new_text': new_text,
                'old_text': prov['provision_text'][:100] if prov['provision_text'] else '(none)',
            })

    print(f"\n{'=' * 70}")
    if args.dry_run:
        print(f"  DRY RUN: {len(updates)} provisions would be updated")
        print(f"{'=' * 70}")
        for u in updates:
            print(f"\n  [{u['ref_number']}] ID: {u['id']}")
            if u['old_text'] == u['new_text']:
                print(f"    ✓ Text identical (no change) — {len(u['old_text'])} chars")
            else:
                print(f"    ✗ Text differs — {len(u['old_text'])} → {len(u['new_text'])} chars")
                print(f"      Old: {u['old_text'][:250]}")
                print(f"      New: {u['new_text'][:250]}")

        # Also show what the document-level update would do
        print(f"\n  Document table: main full_text would be replaced with {len(current_text)} chars")
        print(f"  All SEPP Housing sections marked version_status='current'")

    elif args.update:
        print(f"  UPDATING: {len(updates)} provisions")
        print(f"{'=' * 70}")

        if updates:
            update_provisions(conn, updates)

        # Update document sections with clean text
        update_document_sections(conn, current_text)

        print(f"\n  Done. SEPP Housing provisions updated to Dec 2025 version.")
        print(f"  Source: {NSW_LEGISLATION_URL}")

    conn.close()


if __name__ == '__main__':
    main()
