#!/usr/bin/env python3
"""
Generate PDF page images for Part E requirements (the 39 newly fixed ones)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import psycopg2
from pathlib import Path
import fitz  # PyMuPDF
from collections import defaultdict

OUTPUT_BASE = Path('frontend-nextjs/public/pdf-pages')
PART_E_PDF = Path('docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 10 - Part E Water - with IWLEP 2022 amendments.pdf')

def main():
    conn = psycopg2.connect(
        dbname='nsw_planning',
        user='postgres',
        password='postgres',
        host='localhost',
        port='5432'
    )
    cur = conn.cursor()

    print('='*100)
    print('GENERATE PART E PDF IMAGE URLS')
    print('='*100)

    # Get Part E requirements missing URLs
    cur.execute("""
        SELECT
            dgr.id,
            dgr.pdf_page
        FROM dcp_general_requirements dgr
        JOIN regulatory_provisions rp ON rp.id = dgr.primary_source_provision_id
        WHERE dgr.lga = 'Inner West'
        AND dgr.former_council = 'Leichhardt'
        AND dgr.pdf_page IS NOT NULL
        AND dgr.pdf_page_image_url IS NULL
        AND rp.document_id LIKE '%Part E%Water%'
        ORDER BY dgr.pdf_page
    """)

    requirements = cur.fetchall()
    print(f'\nFound {len(requirements)} Part E requirements missing image URLs')

    if len(requirements) == 0:
        print('All Part E requirements already have URLs!')
        conn.close()
        return

    # Group by page
    by_page = defaultdict(list)
    for req_id, page_num in requirements:
        by_page[page_num].append(req_id)

    print(f'Pages needed: {sorted(by_page.keys())}')
    print()

    # Create output directory for part-e
    output_dir = OUTPUT_BASE / 'leichhardt-part-e'
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f'Output directory: {output_dir}')
    print()

    if not PART_E_PDF.exists():
        print(f'ERROR: PDF not found: {PART_E_PDF}')
        conn.close()
        return

    # Open PDF
    doc = fitz.open(str(PART_E_PDF))
    print(f'PDF: {PART_E_PDF.name} ({len(doc)} pages)')
    print()

    # Process each page
    total_generated = 0
    total_reused = 0
    total_updated = 0

    for page_num in sorted(by_page.keys()):
        req_ids = by_page[page_num]

        # Check if image already exists
        image_filename = f'page_{page_num}.png'
        image_path = output_dir / image_filename

        if not image_path.exists():
            # Generate image
            page_idx = page_num - 1

            if page_idx < 0 or page_idx >= len(doc):
                print(f'ERROR: Page {page_num} invalid (PDF has {len(doc)} pages)')
                continue

            page = doc[page_idx]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale
            pix.save(str(image_path))
            print(f'Generated page {page_num}.png ({len(req_ids)} requirements)')
            total_generated += 1
        else:
            print(f'Reusing page {page_num}.png ({len(req_ids)} requirements)')
            total_reused += 1

        # Update all requirements for this page
        image_url = f'/pdf-pages/leichhardt-part-e/{image_filename}'
        cur.execute("""
            UPDATE dcp_general_requirements
            SET pdf_page_image_url = %s
            WHERE id = ANY(%s)
        """, (image_url, req_ids))

        total_updated += len(req_ids)

    doc.close()
    conn.commit()

    # Verification
    print('\n' + '='*100)
    print('VERIFICATION')
    print('='*100)

    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(pdf_page) as has_page,
            COUNT(pdf_page_image_url) as has_url,
            COUNT(CASE WHEN pdf_page IS NOT NULL AND pdf_page_image_url IS NULL THEN 1 END) as missing
        FROM dcp_general_requirements
        WHERE lga = 'Inner West'
        AND former_council = 'Leichhardt'
    """)

    total, has_page, has_url, missing = cur.fetchone()

    print(f'Leichhardt requirements:')
    print(f'  Total: {total}')
    print(f'  Have pdf_page: {has_page} ({has_page/total*100:.1f}%)')
    print(f'  Have pdf_page_image_url: {has_url} ({has_url/total*100:.1f}%)')
    print(f'  Missing URLs: {missing} ({missing/total*100:.1f}%)')
    print()

    print(f'Summary:')
    print(f'  Generated: {total_generated} images')
    print(f'  Reused: {total_reused} images')
    print(f'  Updated: {total_updated} requirements')
    print()

    if missing == 0:
        print('SUCCESS: All requirements with page numbers now have image URLs!')
    else:
        print(f'WARNING: {missing} requirements still missing image URLs')

    print('='*100)

    conn.close()

if __name__ == '__main__':
    main()
