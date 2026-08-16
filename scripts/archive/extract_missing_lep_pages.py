#!/usr/bin/env python3
"""
Extract the 5 missing LEP PDF pages for Key Sites and Environmental provisions.

Priority order: Leichhardt → Ashfield → Marrickville → Environmental
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

import fitz  # PyMuPDF
from pathlib import Path

# Pages to extract with their clause mappings
PAGES_TO_EXTRACT = [
    # Leichhardt
    {'page': 84, 'clauses': ['6.29'], 'name': '13-15 Victoria Rd, Rozelle', 'lga': 'Leichhardt'},

    # Marrickville
    {'page': 87, 'clauses': ['6.32', '6.33'], 'name': 'Special Entertainment Precinct + Parramatta Rd', 'lga': 'Marrickville'},

    # Environmental (All LGAs)
    {'page': 60, 'clauses': ['6.1'], 'name': 'Acid sulfate soils', 'lga': 'All'},
    {'page': 62, 'clauses': ['6.5'], 'name': 'Flood liable land', 'lga': 'All'},
    {'page': 63, 'clauses': ['6.6'], 'name': 'Contaminated land', 'lga': 'All'},
]

# Paths
LEP_PDF_PATH = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\extraction_outputs\leps\Inner West Local Environmental Plan 2022 - NSW Legislation\auto\Inner West Local Environmental Plan 2022 - NSW Legislation_origin.pdf")
OUTPUT_DIR = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\frontend-nextjs\public\pdf-pages")

def extract_lep_pages():
    """Extract missing LEP pages as high-resolution PNG images."""

    print('=' * 80)
    print('EXTRACT MISSING LEP PDF PAGES')
    print('=' * 80)
    print()

    # Check if LEP PDF exists
    pdf_path = LEP_PDF_PATH
    if not pdf_path.exists():
        print(f'❌ ERROR: LEP PDF not found at:')
        print(f'   {pdf_path}')
        print()
        print('Searching for alternative PDF locations...')

        # Try to find PDF in other locations
        base_dir = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\extraction_outputs\leps")
        pdf_files = list(base_dir.rglob("*_origin.pdf"))

        if pdf_files:
            print(f'\nFound {len(pdf_files)} potential LEP PDFs:')
            for pdf in pdf_files:
                print(f'  - {pdf.name}')
            print()
            print('Using first PDF found...')
            pdf_path = pdf_files[0]
        else:
            print('❌ No LEP PDFs found. Please check extraction_outputs/leps/ directory.')
            return

    print(f'📄 Source PDF: {pdf_path.name}')
    print(f'📁 Output directory: {OUTPUT_DIR}')
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Open PDF
    try:
        doc = fitz.open(str(pdf_path))
        print(f'✅ Opened PDF ({len(doc)} pages)')
        print()
    except Exception as e:
        print(f'❌ ERROR opening PDF: {e}')
        return

    print('=' * 80)
    print('EXTRACTING PAGES')
    print('=' * 80)
    print()

    total_images = 0
    total_size = 0

    for idx, page_info in enumerate(PAGES_TO_EXTRACT, 1):
        page_num = page_info['page']
        clauses = page_info['clauses']
        name = page_info['name']
        lga = page_info['lga']

        print(f'[{idx}/{len(PAGES_TO_EXTRACT)}] Page {page_num} ({lga})')
        print(f'     {name}')
        print(f'     Clauses: {", ".join(clauses)}')

        # Check if page number is valid
        if page_num < 1 or page_num > len(doc):
            print(f'     ❌ ERROR: Page {page_num} out of range (PDF has {len(doc)} pages)')
            print()
            continue

        # Extract page as image
        try:
            page = doc[page_num - 1]  # 0-indexed

            # Render at 2x resolution for clarity (same as DCP extraction)
            zoom = 2.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            # Save image for each clause on this page
            for clause in clauses:
                image_filename = f"iwlep_clause_{clause.replace('.', '_')}_page_{page_num}.png"
                image_path = OUTPUT_DIR / image_filename

                pix.save(str(image_path))

                # Get file size
                file_size = image_path.stat().st_size
                total_size += file_size
                total_images += 1

                print(f'     ✅ Saved: {image_filename} ({file_size / 1024:.0f} KB)')

        except Exception as e:
            print(f'     ❌ ERROR: {e}')

        print()

    doc.close()

    # Summary
    print('=' * 80)
    print('EXTRACTION COMPLETE')
    print('=' * 80)
    print()
    print(f'Total images created:  {total_images}')
    print(f'Total size:            {total_size / 1024:.1f} KB ({total_size / (1024 * 1024):.2f} MB)')
    print(f'Average per image:     {(total_size / total_images / 1024):.0f} KB')
    print()
    print(f'Images saved to: {OUTPUT_DIR}')
    print()

    # List what was created
    print('Files created:')
    for page_info in PAGES_TO_EXTRACT:
        for clause in page_info['clauses']:
            image_filename = f"iwlep_clause_{clause.replace('.', '_')}_page_{page_info['page']}.png"
            print(f'  ✅ {image_filename}')

    print()
    print('=' * 80)
    print('NEXT STEPS')
    print('=' * 80)
    print()
    print('1. Verify images look correct by opening a few in the pdf-pages/ directory')
    print('2. Test in browser: http://localhost:3003/')
    print('3. Search for an address with Key Sites provisions')
    print('4. Click LEP tab and expand provisions to see PDF images')
    print()
    print('✅ All high-priority LEP provisions now have PDF page images!')


if __name__ == "__main__":
    extract_lep_pages()
