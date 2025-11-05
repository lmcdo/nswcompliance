#!/usr/bin/env python3
"""
Generate PDF page images for Part G requirements (the 120 missing URLs)
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import psycopg2
from pathlib import Path
import fitz  # PyMuPDF
from collections import defaultdict

OUTPUT_BASE = Path('frontend-nextjs/public/pdf-pages')

# Map page ranges to PDF files
PART_G_PDFS = [
    {
        'range': (1, 50),
        'pdf': 'docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023-1-50.pdf',
        'offset': 0  # PDF page 1 = document page 1
    },
    {
        'range': (51, 100),
        'pdf': 'docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023-51-100.pdf',
        'offset': 50  # PDF page 1 = document page 51
    },
    {
        'range': (101, 149),
        'pdf': 'docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023-101-149.pdf',
        'offset': 100  # PDF page 1 = document page 101
    },
]

def get_pdf_for_page(page_num):
    """Return (pdf_path, pdf_page_index) for a document page number"""
    for pdf_info in PART_G_PDFS:
        start, end = pdf_info['range']
        if start <= page_num <= end:
            # Calculate PDF page index (0-based)
            pdf_page_idx = page_num - pdf_info['offset'] - 1
            return (pdf_info['pdf'], pdf_page_idx)
    return (None, None)

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
    print('GENERATE PART G PDF IMAGE URLS')
    print('='*100)

    # Get requirements missing URLs (should be the 120 Part G ones)
    cur.execute("""
        SELECT
            id,
            pdf_page,
            part_name
        FROM dcp_general_requirements
        WHERE lga = 'Inner West'
        AND former_council = 'Leichhardt'
        AND pdf_page IS NOT NULL
        AND pdf_page_image_url IS NULL
        ORDER BY pdf_page
    """)

    requirements = cur.fetchall()
    print(f'\nFound {len(requirements)} requirements missing image URLs')
    print()

    if len(requirements) == 0:
        print('✅ All requirements already have URLs!')
        conn.close()
        return

    # Group by page
    by_page = defaultdict(list)
    for req_id, page_num, part_name in requirements:
        by_page[page_num].append(req_id)

    # Create output directory for part-g
    output_dir = OUTPUT_BASE / 'leichhardt-part-g'
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f'Output directory: {output_dir}')
    print()

    # Process each page
    total_generated = 0
    total_reused = 0
    total_failed = 0

    for page_num in sorted(by_page.keys()):
        req_ids = by_page[page_num]

        # Get PDF and page index for this page
        pdf_path, pdf_page_idx = get_pdf_for_page(page_num)

        if not pdf_path:
            print(f'❌ Page {page_num}: No PDF mapping found')
            total_failed += len(req_ids)
            continue

        pdf_file = Path(pdf_path)
        if not pdf_file.exists():
            print(f'❌ Page {page_num}: PDF not found: {pdf_file}')
            total_failed += len(req_ids)
            continue

        # Check if image already exists
        image_filename = f'page_{page_num}.png'
        image_path = output_dir / image_filename

        if not image_path.exists():
            # Generate image
            try:
                doc = fitz.open(str(pdf_file))

                if pdf_page_idx < 0 or pdf_page_idx >= len(doc):
                    print(f'❌ Page {page_num}: Invalid PDF index {pdf_page_idx} (PDF has {len(doc)} pages)')
                    doc.close()
                    total_failed += len(req_ids)
                    continue

                page = doc[pdf_page_idx]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale
                pix.save(str(image_path))
                doc.close()

                print(f'✅ Generated page {page_num}.png ({len(req_ids)} requirements)')
                total_generated += 1

            except Exception as e:
                print(f'❌ Page {page_num}: Error generating image: {e}')
                total_failed += len(req_ids)
                continue
        else:
            print(f'♻️  Reusing existing page {page_num}.png ({len(req_ids)} requirements)')
            total_reused += 1

        # Update all requirements for this page
        image_url = f'/pdf-pages/leichhardt-part-g/{image_filename}'
        cur.execute("""
            UPDATE dcp_general_requirements
            SET pdf_page_image_url = %s
            WHERE id = ANY(%s)
        """, (image_url, req_ids))

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

    print(f'Total requirements: {total}')
    print(f'Have pdf_page: {has_page} ({has_page/total*100:.1f}%)')
    print(f'Have pdf_page_image_url: {has_url} ({has_url/total*100:.1f}%)')
    print(f'Still missing: {missing} ({missing/total*100:.1f}%)')
    print()

    print(f'Summary:')
    print(f'  Generated: {total_generated} images')
    print(f'  Reused: {total_reused} images')
    print(f'  Failed: {total_failed} requirements')
    print()

    if missing == 0:
        print('✅ SUCCESS: All requirements with page numbers now have image URLs!')
    else:
        print(f'⚠️  WARNING: {missing} requirements still missing image URLs')

    print('='*100)

    conn.close()

if __name__ == '__main__':
    main()
