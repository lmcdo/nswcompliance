#!/usr/bin/env python3
"""
Re-parse table structures with better cell boundary detection

This script:
1. Finds tables with mid-sentence cell splits (285 tables)
2. Re-extracts them using multiple table parsers:
   - Camelot (best for bordered tables)
   - img2table (best for borderless tables)
   - Tabula (fallback)
3. Updates database with corrected table HTML
"""

import os
import sys
import psycopg2
from pathlib import Path
import re

# Database connection
DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': os.getenv('DB_PASSWORD', 'postgres'),
    'host': 'localhost'
}

# PDF source directory (MinerU output)
PDF_DIR = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\output")


def get_tables_with_split_sentences():
    """Get list of tables with mid-sentence cell splits"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Find tables where cells end with lowercase and next cell starts with lowercase
    # This indicates mid-sentence split
    query = """
        SELECT
            id,
            document_id,
            pdf_page,
            pdf_source_file,
            ref_number,
            LEFT(provision_text, 200) as preview
        FROM regulatory_provisions
        WHERE provision_text LIKE '%<table%'
            AND provision_text ~ '</td><td>[a-z]'
            AND provision_text ~ '[a-z],</td>'
            AND pdf_source_file IS NOT NULL
            AND pdf_page IS NOT NULL
        ORDER BY document_id, pdf_page;
    """

    cur.execute(query)
    results = cur.fetchall()

    cur.close()
    conn.close()

    return results


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
    temp_dir = Path(tempfile.gettempdir()) / "table_reparse"
    temp_dir.mkdir(exist_ok=True)
    temp_file = temp_dir / f"{hash(str(pdf_path))}.pdf"
    if not temp_file.exists():
        shutil.copy2(pdf_path, temp_file)
    return temp_file


def extract_table_with_camelot(pdf_path, page_num):
    """
    Extract table using Camelot (best for bordered tables)

    Returns:
        HTML table string or None
    """
    try:
        import camelot

        # Copy to temp if path too long
        work_path = copy_to_temp_path(pdf_path) if len(str(pdf_path)) > 200 else pdf_path

        # Extract tables from page
        tables = camelot.read_pdf(
            str(work_path),
            pages=str(page_num),
            flavor='lattice',  # For tables with borders
            strip_text='\n'
        )

        if not tables or len(tables) == 0:
            # Try stream flavor (for borderless tables)
            tables = camelot.read_pdf(
                str(work_path),
                pages=str(page_num),
                flavor='stream',
                strip_text='\n'
            )

        if tables and len(tables) > 0:
            # Get the largest table on the page
            largest_table = max(tables, key=lambda t: t.shape[0] * t.shape[1])

            # Convert to HTML
            html = largest_table.df.to_html(index=False, header=False, border=1)

            # Clean up HTML
            html = html.replace('<table border="1" class="dataframe">', '<table>')
            html = re.sub(r'\s+', ' ', html)  # Normalize whitespace

            return html

        return None

    except Exception as e:
        print(f"  [WARN] Camelot failed: {e}")
        return None


def extract_table_with_img2table(pdf_path, page_num):
    """
    Extract table using img2table (best for borderless tables)

    Returns:
        HTML table string or None
    """
    try:
        from img2table.document import PDF
        from img2table.ocr import TesseractOCR

        # Copy to temp if path too long
        work_path = copy_to_temp_path(pdf_path) if len(str(pdf_path)) > 200 else pdf_path

        # Set up OCR
        ocr = TesseractOCR(
            lang="eng",
            tesseract_cmd=r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        )

        # Extract tables
        doc = PDF(src=str(work_path), pages=[page_num - 1])  # 0-indexed

        extracted_tables = doc.extract_tables(
            ocr=ocr,
            implicit_rows=True,
            borderless_tables=True,
            min_confidence=50
        )

        if extracted_tables and len(extracted_tables) > 0:
            # Get first table on page
            table = extracted_tables[0]
            html = table.html

            # Clean up HTML
            html = re.sub(r'\s+', ' ', html)

            return html

        return None

    except Exception as e:
        print(f"  [WARN] img2table failed: {e}")
        return None


def extract_table_with_tabula(pdf_path, page_num):
    """
    Extract table using Tabula (fallback option)

    Returns:
        HTML table string or None
    """
    try:
        import tabula

        # Copy to temp if path too long
        work_path = copy_to_temp_path(pdf_path) if len(str(pdf_path)) > 200 else pdf_path

        # Extract tables
        dfs = tabula.read_pdf(
            str(work_path),
            pages=page_num,
            multiple_tables=True,
            lattice=True
        )

        if not dfs or len(dfs) == 0:
            # Try stream method
            dfs = tabula.read_pdf(
                str(work_path),
                pages=page_num,
                multiple_tables=True,
                stream=True
            )

        if dfs and len(dfs) > 0:
            # Get largest table
            largest_df = max(dfs, key=lambda df: df.shape[0] * df.shape[1])

            # Convert to HTML
            html = largest_df.to_html(index=False, header=False, border=1)

            # Clean up
            html = html.replace('<table border="1" class="dataframe">', '<table>')
            html = re.sub(r'\s+', ' ', html)

            return html

        return None

    except Exception as e:
        print(f"  [WARN] Tabula failed: {e}")
        return None


def reparse_table(pdf_path, page_num):
    """
    Try multiple parsers in order of quality

    Returns:
        HTML table string or None
    """
    print(f"  Trying Camelot (bordered tables)...")
    result = extract_table_with_camelot(pdf_path, page_num)
    if result:
        print(f"  [OK] Camelot succeeded")
        return result, "camelot"

    print(f"  Trying img2table (borderless tables)...")
    result = extract_table_with_img2table(pdf_path, page_num)
    if result:
        print(f"  [OK] img2table succeeded")
        return result, "img2table"

    print(f"  Trying Tabula (fallback)...")
    result = extract_table_with_tabula(pdf_path, page_num)
    if result:
        print(f"  [OK] Tabula succeeded")
        return result, "tabula"

    return None, None


def update_provision_table(provision_id, new_html, parser_used):
    """Update a provision with corrected table HTML"""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()

    # Add marker to indicate this was re-parsed
    marked_html = f"<!-- Re-parsed table structure using {parser_used} -->\n{new_html}"

    update_query = """
        UPDATE regulatory_provisions
        SET provision_text = %s
        WHERE id = %s;
    """

    cur.execute(update_query, (marked_html, provision_id))
    conn.commit()

    cur.close()
    conn.close()


def check_dependencies():
    """Check if required libraries are installed"""
    missing = []

    try:
        import camelot
        print("[OK] camelot-py found")
    except ImportError:
        missing.append("camelot-py[cv]")

    try:
        from img2table.document import PDF
        print("[OK] img2table found")
    except ImportError:
        missing.append("img2table")

    try:
        import tabula
        print("[OK] tabula-py found")
    except ImportError:
        missing.append("tabula-py")

    try:
        import pytesseract
        # Set explicit path
        pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
        pytesseract.get_tesseract_version()
        print("[OK] pytesseract and Tesseract OCR found")
    except Exception as e:
        print(f"[WARN] Tesseract check failed: {e}")
        print("[INFO] Continuing anyway (only img2table needs Tesseract)")

    if missing:
        print("[ERROR] Missing dependencies:")
        for lib in missing:
            print(f"  - {lib}")
        print()
        print("Install with:")
        print(f"  pip install {' '.join(missing)}")
        return False

    return True


def main():
    print("=" * 70)
    print("Table Structure Re-parsing Tool")
    print("=" * 70)
    print()

    # Check dependencies
    if not check_dependencies():
        sys.exit(1)

    # Get tables with split sentences
    print("Fetching tables with mid-sentence cell splits...")
    split_tables = get_tables_with_split_sentences()

    print(f"Found {len(split_tables)} tables with cell boundary issues")
    print()

    # Group by PDF to minimize file operations
    tables_by_pdf = {}
    for row in split_tables:
        prov_id, doc_id, page_num, pdf_file, ref_num, preview = row

        if pdf_file not in tables_by_pdf:
            tables_by_pdf[pdf_file] = []

        tables_by_pdf[pdf_file].append({
            'id': prov_id,
            'page': page_num,
            'ref': ref_num,
            'preview': preview
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
        print(f"Tables to re-parse: {len(tables)}")

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

            print(f"Provision {prov_id} (page {page_num})...")

            # Re-parse table with multiple parsers
            new_html, parser_used = reparse_table(pdf_path, page_num)

            if not new_html:
                print(f"  [FAIL] All parsers failed")
                total_failed += 1
                continue

            # Update database
            try:
                update_provision_table(prov_id, new_html, parser_used)
                print(f"  [OK] Updated in database (used {parser_used})")
                total_fixed += 1
            except Exception as e:
                print(f"  [ERROR] Database update failed: {e}")
                total_failed += 1

    # Summary
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tables processed: {len(split_tables)}")
    print(f"Successfully re-parsed: {total_fixed}")
    print(f"Failed: {total_failed}")
    print()

    if total_fixed > 0:
        print("[OK] Re-parsing complete!")
        print()
        print("Next step: Verify improvements in database:")
        print('  psql -U postgres -h localhost -d nsw_planning -c "')
        print('    SELECT COUNT(*) FROM regulatory_provisions')
        print("    WHERE provision_text LIKE '%Re-parsed table structure%';")
        print('  "')


if __name__ == "__main__":
    main()
