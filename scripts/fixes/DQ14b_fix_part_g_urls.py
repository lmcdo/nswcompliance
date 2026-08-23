#!/usr/bin/env python3
"""
DQ-14b: Fix Part G provisions that were incorrectly mapped.

Part G provisions have:
- pdf_page = 124 (incorrect - this is an offset)
- page_number = 24 (correct - actual page in PDF)

They were mapped to leichhardt-part-c1 but should be leichhardt-part-g.
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import os
import psycopg2
from pathlib import Path

LOCAL_DB = f"postgresql://{os.environ.get('DB_USER', 'postgres')}:{os.environ['DB_PASSWORD']}@{os.environ.get('DB_HOST', '127.0.0.1')}:{os.environ.get('DB_PORT', '5432')}/{os.environ.get('DB_NAME', 'nsw_planning')}"
OUTPUT_DIR = Path('frontend-nextjs/public/pdf-pages')

def main():
    conn = psycopg2.connect(LOCAL_DB)
    cur = conn.cursor()

    print("=" * 70)
    print("DQ-14b: FIXING PART G PDF URLs")
    print("=" * 70)

    # Check Part G folder
    part_g_folder = OUTPUT_DIR / 'leichhardt-part-g'
    if part_g_folder.exists():
        existing = list(part_g_folder.glob('page_*.png'))
        print(f"\nPart G folder has {len(existing)} PNG files")
        if existing:
            pages = sorted([int(f.stem.replace('page_', '')) for f in existing])
            print(f"  Page range: {min(pages)} - {max(pages)}")
    else:
        print("\nWARNING: Part G folder doesn't exist!")
        return

    # Find Part G provisions without valid URLs
    cur.execute('''
        SELECT id, document_id, page_number
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%Part%G%'
          AND v2_is_actionable = true
          AND page_number IS NOT NULL
    ''')
    part_g_provisions = cur.fetchall()
    print(f"\nFound {len(part_g_provisions)} Part G provisions with page numbers")

    # Update URLs using page_number (not pdf_page)
    updated = 0
    invalid = 0

    for prov_id, doc_id, page_num_str in part_g_provisions:
        try:
            page_num = int(page_num_str)
        except (ValueError, TypeError):
            invalid += 1
            continue

        # Check if PNG exists
        png_path = part_g_folder / f"page_{page_num}.png"
        if png_path.exists():
            url = f"/pdf-pages/leichhardt-part-g/page_{page_num}.png"
            cur.execute('''
                UPDATE regulatory_provisions
                SET pdf_page_image_url = %s
                WHERE id = %s
            ''', (url, prov_id))
            updated += 1

            if updated <= 5:
                print(f"  [OK] ID {prov_id}: page {page_num} -> {url}")
        else:
            invalid += 1
            if invalid <= 5:
                print(f"  [SKIP] ID {prov_id}: page {page_num} not found")

    print(f"\nUpdated: {updated}")
    print(f"Skipped (no PNG): {invalid}")

    # Verify
    cur.execute('''
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE pdf_page_image_url IS NOT NULL) as has_url
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%Part%G%'
          AND v2_is_actionable = true
    ''')
    total, has_url = cur.fetchone()
    pct = 100 * has_url / total if total > 0 else 0
    print(f"\nPart G: {has_url}/{total} have PDF URLs ({pct:.0f}%)")

    # Overall Leichhardt status
    cur.execute('''
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE pdf_page_image_url IS NOT NULL) as has_url
        FROM regulatory_provisions
        WHERE document_id ILIKE '%Leichhardt%'
          AND document_id NOT ILIKE '%Local_Environmental_Plan%'
          AND v2_is_actionable = true
    ''')
    total, has_url = cur.fetchone()
    pct = 100 * has_url / total if total > 0 else 0
    print(f"Leichhardt total: {has_url}/{total} have PDF URLs ({pct:.0f}%)")

    # Commit
    response = input("\nCommit changes? (y/n): ")
    if response.lower() == 'y':
        conn.commit()
        print("Changes committed!")
    else:
        conn.rollback()
        print("Changes rolled back.")

    conn.close()


if __name__ == "__main__":
    main()
