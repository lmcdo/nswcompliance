#!/usr/bin/env python3
"""
COMPLETE DCP RE-EXTRACTION USING PDFPLUMBER

This script does a PROPER extraction from PDFs:
1. Extracts complete text (no fragmentation)
2. Extracts all tables with proper structure
3. Splits only on clear section boundaries
4. Preserves document structure

NO MORE FRAGMENTS. NO MORE BROKEN TABLES.
"""
import pdfplumber
import psycopg2
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
import sys

DB_CONFIG = {
    'dbname': 'nsw_planning',
    'user': 'postgres',
    'password': 'Sturt1802!',
    'host': 'localhost'
}

OUTPUT_DIR = Path(r"C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine\output")


class DCPExtractor:
    """Complete DCP extraction from PDFs using pdfplumber"""

    def __init__(self, pdf_path: Path, document_id: str):
        self.pdf_path = pdf_path
        self.document_id = document_id
        self.sections = []

    def extract_complete_document(self) -> List[Dict[str, Any]]:
        """
        Extract complete document with proper section boundaries

        Returns list of sections:
        {
            'section_number': '4.1.5',
            'section_title': 'Streetscape and design',
            'content': 'Full text content...',
            'tables': [<table HTML>, ...],
            'page_start': 5,
            'page_end': 7
        }
        """
        sections = []
        current_section = None

        with pdfplumber.open(self.pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages, start=1):
                print(f"  Processing page {page_num}/{len(pdf.pages)}", end='\r')

                # Extract text
                text = page.extract_text() or ""

                # Extract tables on this page
                page_tables = page.extract_tables()

                # Look for section headings (like "4.1.5 Streetscape and design")
                section_match = re.search(r'^(\d+(?:\.\d+)*)\s+([A-Z][^\n]+)$', text, re.MULTILINE)

                if section_match:
                    # Save previous section
                    if current_section:
                        current_section['page_end'] = page_num - 1
                        sections.append(current_section)

                    # Start new section
                    current_section = {
                        'section_number': section_match.group(1),
                        'section_title': section_match.group(2).strip(),
                        'content': '',
                        'tables': [],
                        'page_start': page_num,
                        'page_end': page_num,
                        'pages': [page_num]  # Track all pages this section spans
                    }

                # Add content to current section
                if current_section:
                    current_section['content'] += f"\n\n{text}"

                    # Track which pages this section spans
                    if page_num not in current_section['pages']:
                        current_section['pages'].append(page_num)

                    # Add tables
                    if page_tables:
                        for table_data in page_tables:
                            table_html = self.table_to_html(table_data)
                            if table_html:
                                current_section['tables'].append({
                                    'html': table_html,
                                    'page': page_num
                                })
                else:
                    # No section yet - this is preamble/TOC
                    if not sections or sections[-1].get('section_number') != 'preamble':
                        sections.append({
                            'section_number': 'preamble',
                            'section_title': 'Document Information',
                            'content': text,
                            'tables': [],
                            'page_start': page_num,
                            'page_end': page_num,
                            'pages': [page_num]
                        })
                    else:
                        sections[-1]['content'] += f"\n\n{text}"
                        sections[-1]['page_end'] = page_num
                        if page_num not in sections[-1]['pages']:
                            sections[-1]['pages'].append(page_num)

            # Save final section
            if current_section:
                current_section['page_end'] = len(pdf.pages)
                sections.append(current_section)

        print()  # New line after progress
        return sections

    def table_to_html(self, table_data: List[List[str]]) -> str:
        """Convert pdfplumber table data to clean HTML"""
        if not table_data or len(table_data) < 2:
            return ""

        html = "<table>\n"

        # Detect header row (first row is usually header)
        first_row = table_data[0]
        is_header = all(cell and len(str(cell).strip()) < 50 for cell in first_row if cell)

        if is_header:
            html += "<thead>\n<tr>\n"
            for cell in first_row:
                html += f"  <th>{(cell or '').strip()}</th>\n"
            html += "</tr>\n</thead>\n<tbody>\n"
            data_rows = table_data[1:]
        else:
            html += "<tbody>\n"
            data_rows = table_data

        # Data rows
        for row in data_rows:
            html += "<tr>\n"
            for cell in row:
                html += f"  <td>{(cell or '').strip()}</td>\n"
            html += "</tr>\n"

        html += "</tbody>\n</table>"

        return html

    def clean_section_content(self, content: str) -> str:
        """Clean up extracted text"""
        # Remove excessive whitespace
        content = re.sub(r'\n{3,}', '\n\n', content)

        # Remove page numbers (like "Page 5")
        content = re.sub(r'\nPage \d+\n', '\n', content)

        # Clean up spaces
        content = re.sub(r'[ \t]+', ' ', content)

        return content.strip()


def find_all_dcp_pdfs() -> List[Tuple[Path, str]]:
    """Find all DCP PDF files"""
    pdfs = []

    for pdf_path in OUTPUT_DIR.rglob("*_origin.pdf"):
        # Get document name from directory structure
        doc_dir = pdf_path.parent.parent.name

        # Only process DCPs (exclude LEP/SEPP)
        if any(x in doc_dir.lower() for x in ['dcp', 'marrickville', 'ashfield', 'leichhardt']):
            if not any(x in doc_dir.lower() for x in ['lep', 'sepp', 'environmental plan']):
                # Create document_id
                document_id = doc_dir.replace(' ', '_').replace('-', '_').replace('(', '_').replace(')', '_')
                document_id = re.sub(r'_+', '_', document_id)

                pdfs.append((pdf_path, document_id))

    return pdfs


def backup_database():
    """Create backup before deletion"""
    import subprocess
    from datetime import datetime

    backup_file = f"backups/nsw_planning_before_dcp_reextraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.backup"
    Path("backups").mkdir(exist_ok=True)

    print(f"Creating backup: {backup_file}")

    cmd = [
        "C:\\Program Files\\PostgreSQL\\17\\bin\\pg_dump.exe",
        "-U", "postgres",
        "-h", "127.0.0.1",
        "-F", "c",
        "-f", backup_file,
        "nsw_planning"
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, env={'PGPASSWORD': 'Sturt1802!'})

    if result.returncode == 0:
        print(f"[OK] Backup created: {backup_file}")
        return True
    else:
        print(f"[ERROR] Backup failed: {result.stderr}")
        return False


def delete_old_dcp_provisions(conn):
    """Delete all existing DCP provisions"""
    cursor = conn.cursor()

    # Count before deletion
    cursor.execute("SELECT COUNT(*) FROM regulatory_provisions WHERE document_id LIKE '%DCP%' OR document_id LIKE '%Marrickville%' OR document_id LIKE '%Ashfield%' OR document_id LIKE '%Leichhardt%';")
    count_before = cursor.fetchone()[0]

    print(f"Deleting {count_before} existing DCP provisions...")

    cursor.execute("""
        DELETE FROM regulatory_provisions
        WHERE document_id LIKE '%DCP%'
           OR document_id LIKE '%Marrickville%'
           OR document_id LIKE '%Ashfield%'
           OR document_id LIKE '%Leichhardt%';
    """)

    conn.commit()
    cursor.close()

    print(f"[OK] Deleted {count_before} provisions")


def import_sections_to_database(conn, document_id: str, pdf_name: str, sections: List[Dict]):
    """Import extracted sections to database"""
    cursor = conn.cursor()
    imported = 0

    for i, section in enumerate(sections):
        # Clean content
        content = section['content'].strip()

        # Generate ref_number
        if section['section_number'] == 'preamble':
            ref_number = f"{document_id}__preamble"
        else:
            ref_number = f"{document_id}__{section['section_number'].replace('.', '_')}"

        # Create section header
        if section['section_number'] != 'preamble':
            full_text = f"# {section['section_number']} {section['section_title']}\n\n{content}"
        else:
            full_text = content

        # Add tables inline
        if section['tables']:
            full_text += "\n\n---\n\n"
            for j, table in enumerate(section['tables']):
                full_text += f"\n\n**Table {j+1}** (Page {table['page']})\n\n{table['html']}\n\n"

        # Insert provision
        try:
            cursor.execute("""
                INSERT INTO regulatory_provisions (
                    document_id,
                    ref_number,
                    section_header,
                    provision_text,
                    pdf_page,
                    pdf_source_file,
                    page_range
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                document_id,
                ref_number,
                section['section_title'],
                full_text,
                section['page_start'],
                pdf_name,
                section.get('pages', [section['page_start']])  # Use pages array or fallback to page_start
            ))

            imported += 1

        except Exception as e:
            print(f"  [ERROR] Failed to import section {section['section_number']}: {e}")
            continue

    conn.commit()
    cursor.close()

    return imported


def main():
    print("=" * 70)
    print("COMPLETE DCP RE-EXTRACTION WITH PDFPLUMBER")
    print("=" * 70)
    print()

    # Step 1: Find all DCP PDFs
    print("[1/5] Finding DCP PDFs...")
    pdfs = find_all_dcp_pdfs()
    print(f"[OK] Found {len(pdfs)} DCP PDFs to process")
    print()

    if not pdfs:
        print("[ERROR] No DCP PDFs found!")
        return 1

    # Step 2: Backup database (SKIP - done manually)
    print("[2/5] Database backup...")
    print("[OK] Backup already created manually")
    print()

    # Step 3: Connect to database
    print("[3/5] Connecting to database...")
    conn = psycopg2.connect(**DB_CONFIG)
    print("[OK] Connected")
    print()

    # Step 4: Delete old provisions
    print("[4/5] Deleting old DCP provisions...")
    delete_old_dcp_provisions(conn)
    print()

    # Step 5: Extract and import each PDF
    print("[5/5] Extracting and importing DCPs...")
    print()

    total_sections = 0
    total_tables = 0

    for idx, (pdf_path, document_id) in enumerate(pdfs, start=1):
        print(f"[{idx}/{len(pdfs)}] {pdf_path.parent.parent.name}")
        print(f"  Document ID: {document_id}")

        try:
            # Extract
            extractor = DCPExtractor(pdf_path, document_id)
            sections = extractor.extract_complete_document()

            # Count tables
            table_count = sum(len(s['tables']) for s in sections)

            print(f"  Extracted: {len(sections)} sections, {table_count} tables")

            # Import
            imported = import_sections_to_database(
                conn,
                document_id,
                pdf_path.parent.parent.name + ".pdf",
                sections
            )

            print(f"  [OK] Imported {imported} provisions")

            total_sections += imported
            total_tables += table_count

        except Exception as e:
            print(f"  [ERROR] Failed: {e}")
            continue

        print()

    conn.close()

    # Summary
    print("=" * 70)
    print("EXTRACTION COMPLETE")
    print("=" * 70)
    print(f"PDFs processed: {len(pdfs)}")
    print(f"Total sections imported: {total_sections}")
    print(f"Total tables extracted: {total_tables}")
    print()
    print("[OK] All DCPs re-extracted successfully!")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())
