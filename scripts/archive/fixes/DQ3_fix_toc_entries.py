#!/usr/bin/env python3
"""
DQ-3 Fix: Mark TOC/header entries as non-actionable.

Identifies provisions that are table of contents or pure headers
and marks them as v2_is_actionable = false.
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

def main():
    print("=" * 70)
    print("DQ-3 FIX: Mark TOC/header entries as non-actionable")
    print("=" * 70)

    conn = psycopg2.connect('dbname=nsw_planning')
    cur = conn.cursor()

    # Find TOC-style entries (contain "1.1 Name of Plan" or similar TOC patterns)
    print("\n1. Finding TOC entries...")
    cur.execute('''
        SELECT id, substring(provision_text, 1, 100)
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
          AND (provision_text LIKE '%1.1 Name of Plan%'
               OR provision_text LIKE '%1.1AA Commencement%'
               OR provision_text LIKE '%Table of Contents%'
               OR (provision_text LIKE 'Part 1 Preliminary%'
                   AND provision_text LIKE '%Aims of Plan%'))
    ''')
    toc_entries = cur.fetchall()
    print(f"   Found {len(toc_entries)} TOC entries")

    for id, text in toc_entries[:5]:
        print(f"   ID {id}: {text[:60]}...")

    # Find pure section headers (very short with just "Part X Name")
    print("\n2. Finding pure section headers...")
    cur.execute('''
        SELECT id, provision_text
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
          AND provision_text ~ '^Part [0-9]+ [A-Z][a-z]+$'
          AND length(provision_text) < 30
    ''')
    headers = cur.fetchall()
    print(f"   Found {len(headers)} pure headers")

    # Combine IDs to update
    ids_to_fix = [row[0] for row in toc_entries] + [row[0] for row in headers]

    if not ids_to_fix:
        print("\nNo entries to fix!")
        conn.close()
        return

    print(f"\n3. Total entries to mark as non-actionable: {len(ids_to_fix)}")

    # Update
    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_is_actionable = false
        WHERE id = ANY(%s)
    ''', (ids_to_fix,))

    updated = cur.rowcount
    print(f"   Updated: {updated} rows")

    # Verify
    print("\n4. Verification:")
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE v2_is_actionable = true")
    remaining = cur.fetchone()[0]
    print(f"   Remaining actionable: {remaining}")

    # Commit
    confirm = input("\nCommit changes? (y/n): ")
    if confirm.lower() == 'y':
        conn.commit()
        print("Changes committed!")
    else:
        conn.rollback()
        print("Changes rolled back.")

    conn.close()

if __name__ == "__main__":
    main()
