#!/usr/bin/env python3
"""
Populate missing pdf_page_image_url for Leichhardt dcp_general_requirements
Generates PNG images for pages and updates the database
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')
import psycopg2
from pathlib import Path
import fitz  # PyMuPDF
from collections import defaultdict

OUTPUT_BASE = Path('frontend-nextjs/public/pdf-pages')

# Map part letters to full paths
PART_MAPPING = {
    'Part A': {
        'slug': 'leichhardt-part-a',
        'pdf': 'docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 3 - Part A  Introduction - with IWLEP 2022 amendments.pdf'
    },
    'Part B': {
        'slug': 'leichhardt-part-b',
        'pdf': 'docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 4 - Part B Connections - with IWLEP 2022 amendments.pdf'
    },
    'Part C': {
        'slug': 'leichhardt-part-c1',
        'pdf': 'docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 5 -  Part C Place Section 1 - with IWLEP 2022 amendments March 23.pdf'
    },
    'Part C.1': {
        'slug': 'leichhardt-part-c1',
        'pdf': 'docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 5 -  Part C Place Section 1 - with IWLEP 2022 amendments March 23.pdf'
    },
    'Part D': {
        'slug': 'leichhardt-part-d',
        'pdf': 'docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 9 - Part D Energy - with IWLEP 2022 amendments.pdf'
    },
    'Part E': {
        'slug': 'leichhardt-part-e',
        'pdf': 'docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 10 - Part E Water - with IWLEP 2022 amendments.pdf'
    },
    'Part F': {
        'slug': 'leichhardt-part-f',
        'pdf': 'docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 11 - Part F Food - with IWLEP 2022 amendments.pdf'
    },
}

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
    print('POPULATE MISSING LEICHHARDT PDF IMAGE URLS')
    print('='*100)

    # Get requirements missing image URLs
    cur.execute("""
        SELECT
            dgr.id,
            dgr.pdf_page,
            dgr.part_number,
            dgr.part_name,
            dgr.primary_source_provision_id,
            rp.pdf_source_file
        FROM dcp_general_requirements dgr
        LEFT JOIN regulatory_provisions rp ON rp.id = dgr.primary_source_provision_id
        WHERE dgr.lga = 'Inner West'
        AND dgr.former_council = 'Leichhardt'
        AND dgr.pdf_page IS NOT NULL
        AND dgr.pdf_page_image_url IS NULL
        ORDER BY dgr.part_number, dgr.pdf_page
    """)

    requirements = cur.fetchall()
    print(f'\nFound {len(requirements)} requirements missing image URLs')
    print()

    # Group by part and page
    by_part_page = defaultdict(lambda: defaultdict(list))
    part_pdf_map = {}

    for req_id, page_num, part_num, part_name, source_id, pdf_file in requirements:
        # Determine part slug and get PDF path from PART_MAPPING
        part_slug = None
        pdf_path = None

        if part_num:
            for key in PART_MAPPING:
                if part_num.startswith(key):
                    part_slug = PART_MAPPING[key]['slug']
                    pdf_path = PART_MAPPING[key]['pdf']
                    break

        if not part_slug:
            # Fallback based on part name
            if 'Introduction' in (part_name or ''):
                part_slug = 'leichhardt-part-a'
                pdf_path = PART_MAPPING['Part A']['pdf']
            elif 'Connection' in (part_name or '') or 'Heritage' in (part_name or ''):
                part_slug = 'leichhardt-part-b'
                pdf_path = PART_MAPPING['Part B']['pdf']
            elif 'Place' in (part_name or ''):
                part_slug = 'leichhardt-part-c1'
                pdf_path = PART_MAPPING['Part C']['pdf']
            elif 'Energy' in (part_name or ''):
                part_slug = 'leichhardt-part-d'
                pdf_path = PART_MAPPING['Part D']['pdf']
            elif 'Water' in (part_name or ''):
                part_slug = 'leichhardt-part-e'
                pdf_path = PART_MAPPING['Part E']['pdf']
            elif 'Food' in (part_name or ''):
                part_slug = 'leichhardt-part-f'
                pdf_path = PART_MAPPING['Part F']['pdf']
            else:
                print(f'  ⚠️  Cannot determine part for requirement {req_id} (part: {part_num}, name: {part_name})')
                continue

        by_part_page[part_slug][page_num].append(req_id)
        if pdf_path:
            part_pdf_map[part_slug] = pdf_path

    # Process each part
    total_generated = 0

    for part_slug in sorted(by_part_page.keys()):
        print(f'\n{part_slug}:')

        # Create output directory
        output_dir = OUTPUT_BASE / part_slug
        output_dir.mkdir(parents=True, exist_ok=True)

        pages = by_part_page[part_slug]

        print(f'  Pages to generate: {len(pages)}')

        # Get PDF path from mapping
        pdf_path = Path(part_pdf_map.get(part_slug, ''))

        if not pdf_path.exists():
            print(f'  ❌ PDF not found: {pdf_path}')
            continue

        print(f'  PDF: {pdf_path.name}')

        try:
            doc = fitz.open(str(pdf_path))

            generated = 0
            for page_num in sorted(pages.keys()):
                req_ids = pages[page_num]

                # Check if image already exists
                image_filename = f'page_{page_num}.png'
                image_path = output_dir / image_filename

                if not image_path.exists():
                    # Generate image
                    page_idx = page_num - 1

                    if page_idx < 0 or page_idx >= len(doc):
                        print(f'    ❌ Invalid page {page_num} (PDF has {len(doc)} pages)')
                        continue

                    page = doc[page_idx]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x scale
                    pix.save(str(image_path))
                    print(f'    ✅ Generated page {page_num}.png')
                else:
                    print(f'    ♻️  Reusing existing page {page_num}.png')

                # Update all requirements for this page
                image_url = f'/pdf-pages/{part_slug}/{image_filename}'
                cur.execute("""
                    UPDATE dcp_general_requirements
                    SET pdf_page_image_url = %s
                    WHERE id = ANY(%s)
                """, (image_url, req_ids))

                generated += len(req_ids)

            doc.close()
            conn.commit()

            print(f'  ✅ Updated {generated} requirements')
            total_generated += generated

        except Exception as e:
            print(f'  ❌ Error: {e}')
            conn.rollback()
            continue

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

    if missing == 0:
        print('✅ SUCCESS: All requirements with page numbers now have image URLs!')
    else:
        print(f'⚠️  WARNING: {missing} requirements still missing image URLs')

    print('='*100)

    conn.close()

if __name__ == '__main__':
    main()
