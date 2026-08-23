#!/usr/bin/env python3
"""
DQ-14: Populate missing pdf_page_image_url for Leichhardt provisions.

Many Leichhardt provisions have pdf_page or page_number but no pdf_page_image_url.
This script derives the URL from the page number and document_id.

Folder mapping:
- Part C Section 1 -> leichhardt-part-c1
- Part C Section 2 -> leichhardt-part-c2
- Part D (Energy) -> leichhardt-part-d
- Part E (Water) -> leichhardt-part-e
- Part F (Food) -> leichhardt-part-f
- Part G (Site-Specific) -> leichhardt-part-g
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import psycopg2
import re

LOCAL_DB = f"postgresql://{os.environ.get('DB_USER', 'postgres')}:{os.environ['DB_PASSWORD']}@{os.environ.get('DB_HOST', '127.0.0.1')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'nsw_planning')}"

# Document_id pattern to folder mapping
FOLDER_MAP = [
    (r'Section[_ ]1', 'leichhardt-part-c1'),
    (r'Section[_ ]2', 'leichhardt-part-c2'),
    (r'Section[_ ]3', 'leichhardt-part-c1'),  # Section 3 also uses c1 folder
    (r'Section[_ ]4', 'leichhardt-part-c1'),  # Section 4 also uses c1 folder
    (r'Part[_ ]A', 'leichhardt-part-a'),
    (r'Part[_ ]B', 'leichhardt-part-b'),
    (r'Part[_ ]D', 'leichhardt-part-d'),
    (r'Part[_ ]E', 'leichhardt-part-e'),
    (r'Part[_ ]F', 'leichhardt-part-f'),
    (r'Part[_ ]G', 'leichhardt-part-g'),
]


def get_folder_from_docid(document_id):
    """Derive PDF folder name from document_id."""
    if not document_id:
        return None

    for pattern, folder in FOLDER_MAP:
        if re.search(pattern, document_id, re.IGNORECASE):
            return folder

    return None


def main():
    conn = psycopg2.connect(LOCAL_DB)
    cur = conn.cursor()

    print("=" * 70)
    print("DQ-14: POPULATING LEICHHARDT PDF IMAGE URLs")
    print("=" * 70)

    # Find provisions with page info but no image URL
    cur.execute('''
        SELECT id, document_id, pdf_page, page_number
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND document_id NOT ILIKE '%Local_Environmental_Plan%'
          AND v2_is_actionable = true
          AND (pdf_page_image_url IS NULL OR pdf_page_image_url = '')
          AND (pdf_page IS NOT NULL OR page_number IS NOT NULL)
    ''')
    provisions = cur.fetchall()
    print(f"\nFound {len(provisions)} provisions with page info but no image URL")

    updated = 0
    failed = 0
    folder_stats = {}

    for prov_id, doc_id, pdf_page, page_number in provisions:
        # Get page number (prefer pdf_page, fall back to page_number)
        page = pdf_page or page_number
        if not page:
            failed += 1
            continue

        # Get folder from document_id
        folder = get_folder_from_docid(doc_id)
        if not folder:
            failed += 1
            if failed <= 5:
                print(f"  [FAIL] ID {prov_id}: Can't determine folder from {doc_id[:50]}...")
            continue

        # Construct URL
        image_url = f"/pdf-pages/{folder}/page_{page}.png"

        # Update
        cur.execute('''
            UPDATE regulatory_provisions
            SET pdf_page_image_url = %s
            WHERE id = %s
        ''', (image_url, prov_id))

        updated += 1
        folder_stats[folder] = folder_stats.get(folder, 0) + 1

        if updated <= 5:
            print(f"  [OK] ID {prov_id}: page {page} -> {image_url}")

    print(f"\n" + "-" * 70)
    print(f"Updated: {updated}")
    print(f"Failed: {failed}")

    if folder_stats:
        print(f"\nBy folder:")
        for folder, count in sorted(folder_stats.items(), key=lambda x: -x[1]):
            print(f"  {folder}: {count}")

    # Verify final state
    print("\n" + "=" * 70)
    print("VERIFICATION")
    print("=" * 70)

    cur.execute('''
        SELECT
            COUNT(*) FILTER (WHERE pdf_page_image_url IS NOT NULL AND pdf_page_image_url != '') as has_url,
            COUNT(*) as total
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND document_id NOT ILIKE '%Local_Environmental_Plan%'
          AND v2_is_actionable = true
    ''')
    has_url, total = cur.fetchone()
    pct = 100 * has_url / total if total > 0 else 0
    status = "PASS" if pct > 90 else ("WARN" if pct > 70 else "FAIL")
    print(f"\n[{status}] Leichhardt with PDF URLs: {has_url}/{total} ({pct:.0f}%)")

    # Commit
    print("\n" + "-" * 70)
    response = input("Commit changes? (y/n): ")
    if response.lower() == 'y':
        conn.commit()
        print("Changes committed!")
        print("\nIMPORTANT: Run sync_v2_to_supabase.py to update production!")
    else:
        conn.rollback()
        print("Changes rolled back.")

    conn.close()


if __name__ == "__main__":
    main()
