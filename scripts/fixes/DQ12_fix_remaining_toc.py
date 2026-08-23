#!/usr/bin/env python3
"""
DQ-12: Fix remaining TOC (Table of Contents) provisions that are still marked actionable.

These are provisions that contain TOC content like:
- "Part 2 Generic Provisions..... 2.14 Unique Environmental Features 1 2.14.1 Objectives.... 1"
- Section numbers with page numbers and ellipses

These should be marked as v2_is_actionable = false.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import psycopg2
from dotenv import load_dotenv

load_dotenv()

# Use LOCAL database for frontend fixes
LOCAL_DB = f"postgresql://{os.environ.get('DB_USER', 'postgres')}:{os.environ['DB_PASSWORD']}@{os.environ.get('DB_HOST', '127.0.0.1')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'nsw_planning')}"

def find_toc_provisions(conn):
    """Find all TOC provisions that are still marked actionable."""
    cur = conn.cursor()

    # Multiple patterns to catch TOC entries
    cur.execute('''
        SELECT id, document_id, LEFT(provision_text, 200)
        FROM regulatory_provisions
        WHERE v2_is_actionable = true
          AND (
            -- Pattern 1: "Part X Generic Provisions....." followed by section list
            provision_text ~ 'Part\\s+\\d+\\s+(Generic\\s+)?Provisions\\.{3,}'
            -- Pattern 2: Section with page numbers like "2.14.1 Objectives.... 1"
            OR provision_text ~ '\\d+\\.\\d+(\\.\\d+)?\\s+[A-Za-z]+\\.{3,}\\s*\\d+\\s*(\\n|$)'
            -- Pattern 3: Multiple ellipses with numbers (TOC pattern)
            OR (
                provision_text ~ '\\.{3,}\\s*\\d+\\s*\\n'
                AND provision_text ~ '\\.{3,}\\s*\\d+\\s*\\n.*\\.{3,}\\s*\\d+'
            )
            -- Pattern 4: Section headers with page numbers
            OR provision_text ~ '^\\d+\\.\\d+\\s+[A-Z][a-z]+.*\\.{2,}\\s*\\d+\\s*(\\n|$)'
            -- Pattern 5: "Part 9 Strategic Context..." with section listings
            OR provision_text ~ 'Part\\s*\\$?\\\\?textcircled.*Strategic\\s+Context'
          )
        ORDER BY id
    ''')

    return cur.fetchall()

def fix_toc_provisions(conn, provision_ids):
    """Mark TOC provisions as non-actionable."""
    cur = conn.cursor()

    cur.execute('''
        UPDATE regulatory_provisions
        SET v2_is_actionable = false
        WHERE id = ANY(%s)
        RETURNING id
    ''', (provision_ids,))

    updated = cur.fetchall()
    conn.commit()

    return len(updated)

def main():
    print("DQ-12: Fixing remaining TOC provisions\n")
    print("=" * 60)

    conn = psycopg2.connect(LOCAL_DB)

    # Find TOC provisions
    toc_provisions = find_toc_provisions(conn)
    print(f"\nFound {len(toc_provisions)} TOC provisions still marked actionable:\n")

    for prov in toc_provisions:
        print(f"  ID {prov[0]}: {prov[1][:50]}...")
        print(f"    Text: {prov[2][:100]}...")
        print()

    if not toc_provisions:
        print("No TOC provisions to fix!")
        conn.close()
        return

    # Confirm before fixing
    provision_ids = [p[0] for p in toc_provisions]

    print(f"\nWill mark {len(provision_ids)} provisions as non-actionable.")

    # Fix them
    updated = fix_toc_provisions(conn, provision_ids)
    print(f"\n✅ Fixed {updated} TOC provisions")

    # Verify
    remaining = find_toc_provisions(conn)
    print(f"Remaining TOC provisions: {len(remaining)}")

    conn.close()

    print("\n" + "=" * 60)
    print("IMPORTANT: Run sync_v2_to_supabase.py to update production!")

if __name__ == '__main__':
    main()
