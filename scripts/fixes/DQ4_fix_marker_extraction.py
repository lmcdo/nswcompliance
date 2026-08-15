#!/usr/bin/env python3
"""
DQ-4 Fix: Extract markers from provision text.

Extracts C1, O1, DS1, PC1 markers from the start of provision_text
and populates v2_marker.
"""
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()
import psycopg2

def extract_marker(text):
    """Extract marker from provision text."""
    if not text:
        return None

    # Patterns: C1, C12, O1, DS1, PC1, etc.
    match = re.match(r'^(C\d+|O\d+|DS\d+|PC\d+)\b', text.strip())
    if match:
        return match.group(1)
    return None

def main():
    print("=" * 70)
    print("DQ-4 FIX: Extract markers from provision text")
    print("=" * 70)

    conn = psycopg2.connect('dbname=nsw_planning')
    cur = conn.cursor()

    # Find provisions with marker pattern but no v2_marker
    print("\n1. Finding provisions with extractable markers...")
    cur.execute('''
        SELECT id, provision_text
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
          AND v2_marker IS NULL
          AND (provision_text ~ '^C[0-9]+'
               OR provision_text ~ '^O[0-9]+'
               OR provision_text ~ '^DS[0-9]+'
               OR provision_text ~ '^PC[0-9]+')
    ''')
    provisions = cur.fetchall()
    print(f"   Found {len(provisions)} provisions")

    # Extract and update
    updates = []
    for id, text in provisions:
        marker = extract_marker(text)
        if marker:
            updates.append((marker, id))

    print(f"   Extracted {len(updates)} markers")

    # Show sample
    print("\n2. Sample extractions:")
    for marker, id in updates[:10]:
        print(f"   ID {id}: {marker}")

    # Apply updates
    print(f"\n3. Applying updates...")
    for marker, id in updates:
        cur.execute('''
            UPDATE regulatory_provisions
            SET v2_marker = %s
            WHERE id = %s
        ''', (marker, id))

    print(f"   Updated {len(updates)} rows")

    # Verify
    print("\n4. New marker coverage:")
    cur.execute('''
        SELECT
            COUNT(*) FILTER (WHERE v2_marker IS NOT NULL) as has_marker,
            COUNT(*) as total
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
    ''')
    row = cur.fetchone()
    pct = row[0] / row[1] * 100 if row[1] > 0 else 0
    print(f"   With marker: {row[0]} ({pct:.1f}%)")

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
