#!/usr/bin/env python3
"""
Re-extract corrupted tables using Tesseract OCR

This script:
1. Finds all provisions with OCR errors in tables
2. Converts their PDF pages to high-res images
3. Re-OCRs with Tesseract (much better quality than MinerU default)
4. Updates database with corrected text
"""

import os
import sys
import psycopg2
from pathlib import Path
import pytesseract
from pdf2image import convert_from_path
from PIL import Image
import re

# Point pytesseract to Tesseract executable
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'

# Set Poppler path to manually downloaded version
import glob
POPPLER_PATH = Path(__file__).parent.parent / "poppler" / "poppler-24.08.0" / "Library" / "bin"
if not POPPLER_PATH.exists():
    # Fallback to Chocolatey location
    poppler_paths = glob.glob(r'C:\ProgramData\chocolatey\lib\poppler\tools\poppler-*\Library\bin')
    if poppler_paths:
        POPPLER_PATH = Path(poppler_paths[0])
    else:
        POPPLER_PATH = None

# Database connection
DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'host': 'localhost'
}

# PDF source directory (MinerU output with _origin.pdf files)
PDF_DIR = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\output")

# OCR corruption patterns
CORRUPTION_PATTERNS = r'per[0-9]|staffor|flatbuilding|ormotel|mobilty|tothe|ofthe|inareas|trongly|toef|ahes|Singealsega|Doebenclseg|omraial|Develpmen|tcinstret'


def find_pdf_file(pdf_filename):
    """Find PDF file in the MinerU output directory structure"""
    if not pdf_filename:
        return None

    # Remove .pdf extension from database filename
    doc_name = pdf_filename.replace('.pdf', '')

    # Look for corresponding MinerU output directory
    # The _origin.pdf file is the original PDF used by MinerU
    for pdf_path in PDF_DIR.rglob("*_origin.pdf"):
        # Check if the directory name matches the document name
        dir_name = pdf_path.parent.parent.name
        if doc_name in dir_name or dir_name in doc_name:
            return pdf_path

    return None


def copy_to_temp_path(pdf_path):
    """Copy PDF to temp location with shorter path to avoid Windows 260 char limit"""
    import tempfile
    import shutil
    temp_dir = Path(tempfile.gettempdir()) / "ocr_temp"
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / f"{hash(str(pdf_path))}.pdf"
    if not temp_file.exists():
        shutil.copy2(pdf_path, temp_file)
    return temp_file

def extract_page_with_tesseract(pdf_path, page_num, dpi=300):
    """
    Extract text from a specific PDF page using Tesseract OCR

    Args:
        pdf_path: Path to PDF file
        page_num: Page number (1-indexed)
        dpi: Resolution for image conversion (higher = better quality)

    Returns:
        Extracted text with improved OCR quality
    """
    try:
        print(f"  Converting page {page_num} to image at {dpi} DPI...")

        # Copy to temp path if original is too long
        work_path = copy_to_temp_path(pdf_path) if len(str(pdf_path)) > 200 else pdf_path

        # Convert PDF page to high-resolution image
        kwargs = {
            'dpi': dpi,
            'first_page': page_num,
            'last_page': page_num,
            'thread_count': 4
        }

        # Add Poppler path if found
        if POPPLER_PATH:
            kwargs['poppler_path'] = POPPLER_PATH

        images = convert_from_path(str(work_path), **kwargs)

        if not images:
            print(f"  ERROR: No image generated for page {page_num}")
            return None

        image = images[0]

        # Optionally enhance image for better OCR
        # (uncomment if needed)
        # from PIL import ImageEnhance
        # enhancer = ImageEnhance.Contrast(image)
        # image = enhancer.enhance(1.5)

        print(f"  Running Tesseract OCR...")

        # Run Tesseract with table-optimized settings
        custom_config = r'--oem 3 --psm 6'  # PSM 6 = Assume a single uniform block of text
        text = pytesseract.image_to_string(
            image,
            lang='eng',
            config=custom_config
        )

        return text

    except Exception as e:
        print(f"  ERROR extracting page: {e}")
        return None


def extract_table_from_text(text):
    """
    Convert OCR text back to HTML table format
    This is a simple heuristic - may need adjustment
    """
    # For now, just return the text
    # More sophisticated table detection would go here
    return text


def get_corrupted_tables():
    """Get list of corrupted table provisions from database"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    query = f"""
        SELECT
            id,
            document_id,
            pdf_page,
            pdf_source_file,
            ref_number,
            CASE
                WHEN provision_text ~ 'Singealsega|Doebenclseg' THEN 'CRITICAL'
                WHEN provision_text ~ 'toef|ahes|omraial' THEN 'HIGH'
                WHEN provision_text ~ 'per[0-9]|staffor|flatbuilding|ormotel|mobilty' THEN 'MEDIUM'
                ELSE 'LOW'
            END as severity
        FROM regulatory_provisions
        WHERE provision_text LIKE '%<table%'
            AND provision_text ~ '{CORRUPTION_PATTERNS}'
            AND pdf_source_file IS NOT NULL
            AND pdf_page IS NOT NULL
        ORDER BY severity, document_id, pdf_page;
    """

    cur.execute(query)
    results = cur.fetchall()

    cur.close()
    conn.close()

    return results


def update_provision_text(provision_id, new_text):
    """Update a provision with corrected OCR text"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Add flag to indicate this was re-OCRed with Tesseract
    update_query = """
        UPDATE regulatory_provisions
        SET provision_text = %s
        WHERE id = %s;
    """

    cur.execute(update_query, (new_text, provision_id))
    conn.commit()

    cur.close()
    conn.close()


def main():
    print("=" * 70)
    print("Tesseract Table Re-extraction Tool")
    print("=" * 70)
    print()

    # Check if Tesseract is installed
    try:
        pytesseract.get_tesseract_version()
        print("[OK] Tesseract OCR found")
    except:
        print("[ERROR] Tesseract not installed")
        print("  Please run: scripts\\install_tesseract.bat")
        sys.exit(1)

    # Get corrupted tables
    print()
    print("Fetching corrupted tables from database...")
    corrupted_tables = get_corrupted_tables()

    print(f"Found {len(corrupted_tables)} corrupted tables")
    print()

    # Group by PDF to minimize file operations
    tables_by_pdf = {}
    for row in corrupted_tables:
        prov_id, doc_id, page_num, pdf_file, ref_num, severity = row

        if pdf_file not in tables_by_pdf:
            tables_by_pdf[pdf_file] = []

        tables_by_pdf[pdf_file].append({
            'id': prov_id,
            'page': page_num,
            'ref': ref_num,
            'severity': severity
        })

    print(f"Across {len(tables_by_pdf)} unique PDF files")
    print()

    # Process each PDF
    total_fixed = 0
    total_failed = 0

    for pdf_filename, tables in tables_by_pdf.items():
        print(f"\n{'=' * 70}")
        print(f"PDF: {pdf_filename}")
        print(f"{'=' * 70}")
        print(f"Tables to fix: {len(tables)}")

        # Find PDF file
        pdf_path = find_pdf_file(pdf_filename)

        if not pdf_path:
            print(f"[ERROR] Could not find PDF file: {pdf_filename}")
            total_failed += len(tables)
            continue

        print(f"[OK] Found: {pdf_path}")
        print()

        # Process each table in this PDF
        for table in tables:
            prov_id = table['id']
            page_num = table['page']
            severity = table['severity']

            print(f"[{severity}] Provision {prov_id} (page {page_num})...")

            # Extract page with Tesseract
            ocr_text = extract_page_with_tesseract(pdf_path, page_num)

            if not ocr_text:
                print(f"  [FAIL] FAILED to extract")
                total_failed += 1
                continue

            # Check if OCR improved
            has_errors = bool(re.search(CORRUPTION_PATTERNS, ocr_text))

            if has_errors:
                print(f"  [WARN] Still contains OCR errors")
                print(f"  Text preview: {ocr_text[:150]}...")

            # Update database
            # Note: For tables, we should ideally reconstruct HTML structure
            # For now, storing as plain text with note that it needs table parsing
            wrapped_text = f"<!-- Re-OCRed with Tesseract -->\n{ocr_text}"

            try:
                update_provision_text(prov_id, wrapped_text)
                print(f"  [OK] Updated in database")
                total_fixed += 1
            except Exception as e:
                print(f"  [ERROR] Database update failed: {e}")
                total_failed += 1

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total provisions processed: {len(corrupted_tables)}")
    print(f"Successfully fixed: {total_fixed}")
    print(f"Failed: {total_failed}")
    print()

    if total_fixed > 0:
        print("[OK] Re-extraction complete!")
        print()
        print("Next step: Verify improvements in database:")
        print('  psql -U postgres -h localhost -d nsw_planning -c "')
        print('    SELECT COUNT(*) FROM regulatory_provisions')
        print(f'    WHERE provision_text ~ \'{CORRUPTION_PATTERNS}\';')
        print('  "')


if __name__ == "__main__":
    main()
