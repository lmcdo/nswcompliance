#!/usr/bin/env python3
"""
Document Currency Verification Script
======================================
Audits all documents in the compliance engine against their version metadata.
Produces a QA-defensible report of currency status for stakeholder review.

Usage:
    python3 scripts/verify_document_currency.py           # Print audit report
    python3 scripts/verify_document_currency.py --update  # Update last_verified_date for manually confirmed docs
    python3 scripts/verify_document_currency.py --csv     # Export to CSV for stakeholder handoff

Workflow:
1. Run with no flags to see current status
2. Manually check flagged documents against NSW Legislation / council sites
3. Run with --update to record verification date
"""

import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import argparse
import csv
import json
from datetime import date, timedelta
from io import StringIO
from pathlib import Path

import psycopg2
from dotenv import load_dotenv

load_dotenv()

STALENESS_DAYS = 90  # Flag documents not verified within this period

# Official verification URLs for each document type/name
# Used to generate the "check here" column in the report
VERIFICATION_URLS = {
    'SEPP': 'https://legislation.nsw.gov.au/*/current',  # Replace * with SEPP name
    'LEP': 'https://legislation.nsw.gov.au/*/current',
    'DCP_Marrickville': 'https://www.marrickville.nsw.gov.au/Residents/Development-and-planning/Development-control-plan',
    'DCP_Leichhardt': 'https://www.innerwest.nsw.gov.au/Residents/Development-and-planning',
    'DCP_Ashfield': 'https://www.innerwest.nsw.gov.au/Residents/Development-and-planning',
}

# Documents known to be stable (update frequency < annual)
STABLE_DOCUMENTS = {
    'State_Environmental_Planning_Policy_(Housing)_2021',
    'State_Environmental_Planning_Policy_(Biodiversity_and_Conservation)_2021',
    'State_Environmental_Planning_Policy_(Resilience_and_Hazards)_2021',
    'State_Environmental_Planning_Policy_(Industry_and_Employment)_2021',
    'State_Environmental_Planning_Policy_(Primary_Production)_2021',
    'State_Environmental_Planning_Policy_(Planning_Systems)_2021',
    'State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021',
    'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022',
    'State_Environmental_Planning_Policy_(Exempt_and_Complying_Development_Codes)_2008',
}


def get_connection():
    """Connect to the compliance engine database (Supabase)."""
    import os
    db_url = os.environ.get('DATABASE_URL') or os.environ.get('SUPABASE_DB_URL')
    if not db_url:
        print("ERROR: DATABASE_URL not set in .env")
        sys.exit(1)
    return psycopg2.connect(db_url)


def fetch_documents(conn):
    """
    Fetch documents grouped by base document name.
    Many documents are split into sections (e.g. SEPP Housing Section_1 through Section_31).
    We aggregate these into a single entry per unique document for the audit.
    """
    cur = conn.cursor()
    # Use regexp to strip section/page split suffixes from pdf_name
    # Patterns: "_Section_N", "_pages_N-N", "_-_[SPLIT_INTO_N_SECTIONS]", "_chunk_N"
    cur.execute("""
        WITH base_docs AS (
            SELECT
                id,
                pdf_name,
                document_type,
                document_area,
                regulation_year,
                amendment_reference,
                amendment_date,
                source_url,
                last_verified_date,
                version_status,
                extraction_timestamp,
                -- Strip section/split/page-range suffixes to get base document name
                regexp_replace(
                    regexp_replace(
                        regexp_replace(
                            regexp_replace(
                                regexp_replace(
                                    regexp_replace(pdf_name,
                                        ' - Section [0-9]+', '', 'g'),
                                    ' - \\[SPLIT INTO [0-9]+ SECTIONS\\]', '', 'g'),
                                '-[0-9]+-[0-9]+', '', 'g'),
                            '_chunk_[0-9]+', '', 'g'),
                        ' - NSW Legislation', '', 'g'),
                    '\\.pdf$', '', 'g'
                ) AS base_name
            FROM documents
        )
        SELECT
            base_name AS pdf_name,
            document_type,
            MIN(document_area) AS document_area,
            MAX(regulation_year) AS regulation_year,
            MAX(amendment_reference) AS amendment_reference,
            MAX(amendment_date) AS amendment_date,
            MAX(source_url) AS source_url,
            MAX(last_verified_date) AS last_verified_date,
            MAX(version_status) AS version_status,
            COUNT(*) AS section_count,
            array_agg(id) AS section_ids
        FROM base_docs
        GROUP BY base_name, document_type
        ORDER BY document_type, base_name
    """)
    columns = [desc[0] for desc in cur.description]
    rows = [dict(zip(columns, row)) for row in cur.fetchall()]
    cur.close()
    return rows


def classify_currency(doc: dict) -> dict:
    """
    Classify a document's currency status based on available metadata.
    Returns enriched doc dict with flags and recommendations.
    """
    today = date.today()
    verified = doc['last_verified_date']
    status = doc['version_status'] or 'unverified'
    doc_type = doc['document_type'] or 'unknown'
    doc_name = doc['pdf_name'] or ''

    flags = []
    recommendation = ''
    is_stable = any(s in doc_name for s in STABLE_DOCUMENTS)
    days_since_verified = (today - verified).days if verified else None

    # Flag: never verified
    if status == 'unverified':
        flags.append('UNVERIFIED')

    # Flag: stale verification
    if verified and days_since_verified > STALENESS_DAYS:
        flags.append(f'STALE ({days_since_verified}d)')

    # Flag: missing amendment metadata
    if not doc['amendment_reference'] and not doc['amendment_date']:
        flags.append('NO_AMENDMENT_DATA')

    # Flag: missing source URL
    if not doc['source_url']:
        flags.append('NO_SOURCE_URL')

    # Recommendation
    if status == 'unverified' and not is_stable:
        recommendation = 'VERIFY AGAINST OFFICIAL SOURCE'
    elif status == 'unverified' and is_stable:
        recommendation = 'Low priority — consolidated SEPP (verify quarterly)'
    elif flags:
        recommendation = 'Re-verify: ' + ', '.join(flags)
    else:
        recommendation = 'Current'

    # Verification URL
    if doc_type == 'SEPP' or doc_type == 'LEP':
        check_url = f"https://legislation.nsw.gov.au/view/current/{doc_name.replace(' ', '_').replace('__NSW_Legislation', '')}"
    elif 'Marrickville' in doc_name:
        check_url = VERIFICATION_URLS['DCP_Marrickville']
    elif 'Leichhardt' in doc_name:
        check_url = VERIFICATION_URLS['DCP_Leichhardt']
    elif 'Ashfield' in doc_name:
        check_url = VERIFICATION_URLS['DCP_Ashfield']
    else:
        check_url = ''

    return {
        **doc,
        'flags': flags,
        'recommendation': recommendation,
        'check_url': check_url,
        'is_stable': is_stable,
        'days_since_verified': days_since_verified,
    }


def print_report(documents: list):
    """Print a structured currency audit report."""
    today = date.today()

    # Group by document type
    by_type = {}
    for doc in documents:
        dt = doc['document_type'] or 'unknown'
        by_type.setdefault(dt, []).append(doc)

    # Summary counts
    total = len(documents)
    unverified = sum(1 for d in documents if d['version_status'] == 'unverified')
    stale = sum(1 for d in documents if 'STALE' in ' '.join(d['flags']))
    current = sum(1 for d in documents if d['version_status'] == 'current')
    flagged = sum(1 for d in documents if d['flags'])

    print("=" * 80)
    print(f"  DOCUMENT CURRENCY AUDIT — {today.isoformat()}")
    print("=" * 80)
    print()
    print(f"  Total documents: {total}")
    print(f"  Current (verified): {current}")
    print(f"  Unverified: {unverified}")
    print(f"  Stale (>{STALENESS_DAYS}d): {stale}")
    print(f"  Documents with flags: {flagged}")
    print()

    # Priority sections
    for doc_type in ['SEPP', 'LEP', 'DCP']:
        docs = by_type.get(doc_type, [])
        if not docs:
            continue

        print(f"  {'—' * 76}")
        print(f"  {doc_type} ({len(docs)} documents)")
        print(f"  {'—' * 76}")

        # Prioritise: flagged first, then stable
        flagged_docs = [d for d in docs if d['flags']]
        clean_docs = [d for d in docs if not d['flags']]

        for doc in flagged_docs + clean_docs:
            flags_str = ' '.join(f'[{f}]' for f in doc['flags']) if doc['flags'] else '[OK]'
            year = doc.get('regulation_year') or '??'
            amendment = doc.get('amendment_reference') or 'none'
            verified_str = doc['last_verified_date'].isoformat() if doc['last_verified_date'] else 'never'
            sections = doc.get('section_count', 1)
            section_label = f" ({sections} sections)" if sections > 1 else ""
            print(f"    {flags_str:30s} {year} amdt:{amendment:10s} verified:{verified_str}")
            print(f"      {doc['pdf_name'][:70]}{section_label}")
            if doc['recommendation'] != 'Current':
                print(f"      -> {doc['recommendation']}")
            if doc.get('check_url'):
                print(f"      URL: {doc['check_url']}")
            print()

    # Action items
    action_items = [d for d in documents if d['flags'] and not d['is_stable']]
    if action_items:
        print(f"  {'=' * 76}")
        print(f"  ACTION ITEMS — {len(action_items)} documents need manual verification")
        print(f"  {'=' * 76}")
        for i, doc in enumerate(action_items, 1):
            print(f"  {i}. [{doc['document_type']}] {doc['pdf_name'][:60]}")
            if doc.get('check_url'):
                print(f"     Check: {doc['check_url']}")
        print()


def export_csv(documents: list, output_path: str = None):
    """Export audit to CSV for stakeholder handoff."""
    if not output_path:
        output_path = f"document_currency_audit_{date.today().isoformat()}.csv"

    fields = [
        'pdf_name', 'document_type', 'regulation_year', 'amendment_reference',
        'amendment_date', 'last_verified_date', 'version_status',
        'flags', 'recommendation', 'check_url'
    ]

    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        for doc in documents:
            row = {
                **doc,
                'flags': ' | '.join(doc['flags']) if doc['flags'] else '',
                'amendment_date': doc['amendment_date'].isoformat() if doc['amendment_date'] else '',
                'last_verified_date': doc['last_verified_date'].isoformat() if doc['last_verified_date'] else '',
            }
            writer.writerow(row)

    print(f"Exported to: {output_path}")
    return output_path


def update_verified(conn, document_ids: list = None):
    """
    Mark documents as verified (set last_verified_date to today, version_status to 'current').
    If no IDs provided, prompts for confirmation to update ALL documents.
    document_ids can be individual IDs or lists (from grouped query section_ids).
    """
    today = date.today()
    cur = conn.cursor()

    if document_ids:
        # Flatten in case some are lists (from section_ids arrays)
        flat_ids = []
        for id_val in document_ids:
            if isinstance(id_val, list):
                flat_ids.extend(id_val)
            else:
                flat_ids.append(id_val)
        placeholders = ','.join(['%s'] * len(flat_ids))
        cur.execute(
            f"UPDATE documents SET last_verified_date = %s, version_status = 'current' "
            f"WHERE id IN ({placeholders})",
            [today] + flat_ids
        )
    else:
        response = input("\nUpdate ALL documents? This sets version_status='current' and last_verified_date=today. (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            return
        cur.execute(
            "UPDATE documents SET last_verified_date = %s, version_status = 'current'",
            [today]
        )

    conn.commit()
    print(f"Updated {cur.rowcount} documents. last_verified_date={today}, version_status='current'")
    cur.close()


def main():
    parser = argparse.ArgumentParser(description='Document currency verification audit')
    parser.add_argument('--update', action='store_true', help='Mark all documents as verified (after manual check)')
    parser.add_argument('--update-ids', nargs='+', help='Mark specific document IDs as verified')
    parser.add_argument('--csv', action='store_true', help='Export audit to CSV')
    parser.add_argument('--csv-path', type=str, default=None, help='Custom CSV output path')
    args = parser.parse_args()

    print("Connecting to database...")
    conn = get_connection()

    try:
        raw_docs = fetch_documents(conn)
        print(f"Fetched {len(raw_docs)} documents.")

        documents = [classify_currency(doc) for doc in raw_docs]

        if args.update:
            update_verified(conn)
        elif args.update_ids:
            update_verified(conn, args.update_ids)

        if args.csv:
            export_csv(documents, args.csv_path)
        else:
            print_report(documents)

    finally:
        conn.close()


if __name__ == '__main__':
    main()
