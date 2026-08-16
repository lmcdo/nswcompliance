"""
Extract DCP Table of Contents from content_list.json files
Maps TOC structure to database for /browse route

Supports both text format (Marrickville) and HTML table format (Ashfield/Leichhardt)
"""

import json
import re
import os
from pathlib import Path
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv
from html.parser import HTMLParser

# Load environment variables
load_dotenv()

class TOCTableParser(HTMLParser):
    """Parse HTML table to extract TOC entries"""
    def __init__(self):
        super().__init__()
        self.in_table = False
        self.in_row = False
        self.in_cell = False
        self.current_row = []
        self.rows = []
        self.current_data = ''

    def handle_starttag(self, tag, attrs):
        if tag == 'table':
            self.in_table = True
        elif tag == 'tr' and self.in_table:
            self.in_row = True
            self.current_row = []
        elif tag == 'td' and self.in_row:
            self.in_cell = True
            self.current_data = ''

    def handle_endtag(self, tag):
        if tag == 'table':
            self.in_table = False
        elif tag == 'tr' and self.in_row:
            self.in_row = False
            if self.current_row:
                self.rows.append(self.current_row)
        elif tag == 'td' and self.in_cell:
            self.in_cell = False
            self.current_row.append(self.current_data.strip())

    def handle_data(self, data):
        if self.in_cell:
            self.current_data += data

def extract_toc_from_content_list(json_path):
    """Extract TOC structure from content_list.json (text or table format)"""
    try:
        with open(json_path, 'r', encoding='utf-8') as f:
            content = json.load(f)
    except Exception as e:
        print(f"  X Error reading {json_path}: {e}")
        return None

    # Try text format first (Marrickville style - single block)
    for item in content:
        if item.get('type') == 'text':
            text = item.get('text', '')
            # Check if this looks like a TOC (has multiple lines with dots/page numbers)
            if '......' in text or (text.count('\n') > 3 and text.count('.') > 10):
                toc = parse_toc_text(text)
                if toc:
                    return toc

    # Try split-entry text format (Leichhardt Part F style - separate text entries)
    toc = extract_split_entry_toc(content)
    if toc:
        return toc

    # Try table format (Ashfield/Leichhardt style)
    for item in content:
        if item.get('type') == 'table':
            table_html = item.get('table_body', '')
            # Check if this is a TOC table (has Section/Page headers)
            if ('Section' in table_html or 'section' in table_html) and \
               ('Page' in table_html or 'page' in table_html):
                toc = parse_table_toc(table_html)
                if toc:
                    return toc

    # Try headerless TOC format (4.1, 5.0, 6.0 style - consecutive entries without header)
    toc = extract_headerless_toc(content)
    if toc:
        return toc

    return None

def extract_split_entry_toc(content):
    """Extract TOC from separate text entries (Leichhardt Part F/D/E style)

    Handles cases where each TOC line is a separate text item:
    - "CONTENTS" (header)
    - "SECTION 1 – FOOD .... 3" (entry)
    - "F1.1 FOOD PRODUCTION...... 4" (entry)
    - "F1.1.3 Community gardens.. 6" (entry)
    """
    # Look for TOC header followed by TOC-like entries
    for i, item in enumerate(content):
        if item.get('type') != 'text':
            continue

        text = item.get('text', '').strip()

        # Check if this is a TOC header
        if text.upper() in ['CONTENTS', 'TABLE OF CONTENTS', 'LIST OF CONTENTS']:
            # Collect following entries that look like TOC entries
            toc_lines = []
            page_idx = item.get('page_idx', 0)

            # Look ahead at next 30 items (generous limit)
            for j in range(i + 1, min(i + 31, len(content))):
                next_item = content[j]

                # Stop if we've moved to a different page (TOC usually on same page or next)
                if next_item.get('page_idx', 0) > page_idx + 1:
                    break

                if next_item.get('type') != 'text':
                    continue

                next_text = next_item.get('text', '').strip()

                # Skip empty lines
                if not next_text:
                    continue

                # Stop at common section starters (end of TOC)
                # BUT: Include them if they have TOC formatting (dots + page number)
                if next_text.upper().startswith(('LIST OF ', 'SECTION ', 'PART ', 'OBJECTIVES', 'INTRODUCTION')):
                    # Include if it has dots and page number (it's a TOC entry, not content start)
                    if '..' in next_text and re.search(r'\d+\s*$', next_text):
                        toc_lines.append(next_text)
                        continue  # Keep looking for more TOC entries
                    # Stop at "LIST OF TABLES/FIGURES" (not a TOC entry)
                    elif next_text.upper().startswith('LIST OF '):
                        break
                    # If no dots/page number, it's the start of content - stop collecting
                    else:
                        break

                # Check if this looks like a TOC entry (has dots and ends with number)
                if '..' in next_text and re.search(r'\d+\s*$', next_text):
                    toc_lines.append(next_text)
                elif re.match(r'^[A-Z]?\d+\.[\d.]*\s+', next_text):
                    # Also accept entries like "F1.1 Title" even without dots (might have page number)
                    toc_lines.append(next_text)

            # If we found TOC-like entries, parse them
            if len(toc_lines) >= 2:  # Need at least 2 entries to be a TOC
                combined_text = '\n'.join(toc_lines)
                toc = parse_toc_text(combined_text)
                if toc:
                    return toc

    return None

def extract_headerless_toc(content):
    """Extract TOC from consecutive entries without header (e.g., Section 4.1, 5.0, 6.0)

    Handles documents where TOC entries appear early in document but have no header:
    - "4.1.1 Site Planning ......... 1"
    - "4.1.2 Building Design ........ 3"
    - "4.1.3 Landscaping ............ 5"

    Pattern: Consecutive text items with section numbers, dots, and page numbers
    """
    # Only check first 5 pages (TOC usually at start)
    max_page_idx = 5

    # Look for clusters of consecutive TOC-like entries
    for i, item in enumerate(content):
        if item.get('type') != 'text':
            continue

        # Skip if we're past page 5
        if item.get('page_idx', 0) > max_page_idx:
            break

        text = item.get('text', '').strip()

        # Check if this looks like first TOC entry (section number, dots, page number)
        # Match patterns like "4.1.1 Title .... 3" or "2.1 Objectives ...... 1"
        if re.match(r'^\d+\.[\d.]*\s+.+[\s.]+\d+\s*$', text) or \
           (re.match(r'^\d+\.[\d.]*\s+', text) and '..' in text):

            # Collect consecutive TOC-like entries
            toc_lines = [text]
            page_idx = item.get('page_idx', 0)

            # Look ahead for more TOC entries
            for j in range(i + 1, min(i + 51, len(content))):
                next_item = content[j]

                # Stop if we've moved too far (more than 2 pages)
                if next_item.get('page_idx', 0) > page_idx + 2:
                    break

                if next_item.get('type') != 'text':
                    continue

                next_text = next_item.get('text', '').strip()

                if not next_text:
                    continue

                # Check if this is also a TOC entry
                if re.match(r'^\d+\.[\d.]*\s+.+[\s.]+\d+\s*$', next_text) or \
                   (re.match(r'^\d+\.[\d.]*\s+', next_text) and '..' in next_text):
                    toc_lines.append(next_text)
                elif len(toc_lines) >= 3:
                    # We've found at least 3 TOC entries and now hit non-TOC text - stop
                    break
                elif not next_text.startswith(('Figure', 'Table', 'Image', 'Note:')):
                    # If it's not a TOC entry and not skippable, might not be TOC - continue cautiously
                    continue

            # If we found enough consecutive entries (at least 3), parse as TOC
            if len(toc_lines) >= 3:
                combined_text = '\n'.join(toc_lines)
                toc = parse_toc_text(combined_text)
                if toc and len(toc) >= 3:
                    return toc

    return None

def parse_toc_text(toc_text):
    """Parse TOC text into structured sections

    Handles multiple formats:
    - Digit-based: "2.10.1 Objectives...... 4" (Marrickville)
    - Letter-based: "A1.1 NAME OF THIS PLAN... ..3" (Leichhardt Part A)
    - Mixed: "G13.1 Relationship to other plans... .... 151" (Leichhardt Part G)
    """
    lines = toc_text.strip().split('\n')
    sections = []

    for line in lines:
        # Skip empty lines
        if not line.strip():
            continue

        # Match patterns like:
        # - "2.10.1 Objectives...... 4" (Marrickville - continuous dots)
        # - "A1.1 NAME OF THIS PLAN... ..3" (Leichhardt - multiple dot sequences)
        # - "G13.1 Relationship... .... 151" (Leichhardt Part G - dots with spaces)
        # - "4.1 Land use .. ...154" (numeric - dots and spaces mixed)
        # - "SECTION 1 – FOOD .... 3" (Leichhardt Part F - word + number)
        # Use [\s.]+ to match any combination of spaces and dots
        # Match either "SECTION 1" or "F1.1" style section numbers
        match = re.match(r'^([A-Z]+\s+\d+|[A-Z]?\d+\.[\d.]*)\s+(.+?)\s+([\s.]+)\s*(\d+)?', line)

        if match:
            section_num, title, _dots, page = match.groups()  # 4 groups now (added dots pattern)
            sections.append({
                'section_number': section_num.rstrip('.'),  # Remove trailing dots
                'title': title.strip(),
                'page': int(page) if page else None
            })

    return sections if sections else None

def parse_table_toc(table_html):
    """Parse HTML table TOC into structured sections

    Handles multiple formats:
    - 3-column: [section_num, title, page]
    - 2-column: [title, page] (Ashfield style)
    - Malformed: [empty, "title + page"] (extract page from merged text)
    """
    parser = TOCTableParser()
    parser.feed(table_html)

    sections = []
    section_counter = 1  # For auto-numbering 2-column tables

    # Parse rows (skip header row)
    for row in parser.rows[1:]:  # Skip first row (headers)
        if len(row) < 2:
            continue  # Need at least 2 columns

        # Detect format based on column count
        if len(row) >= 3:
            # 3-column format: [section_num, title, page]
            section_num = row[0].strip()
            title = row[1].strip()
            page_str = row[2].strip()
        else:
            # 2-column format: [title, page] or [empty, title+page]
            col1 = row[0].strip()
            col2 = row[1].strip()

            # Check if col2 contains "title + page" (e.g., "Awnings to Buildings Over Public Land 6")
            # Look for a number at the end
            match = re.match(r'^(.+?)\s+(\d+)$', col2)

            if not col1 and match:
                # Malformed: title and page in col2
                title = match.group(1).strip()
                page_str = match.group(2)
                section_num = str(section_counter)
            elif col1 and col2:
                # Standard 2-column: [title, page]
                title = col1
                page_str = col2
                section_num = str(section_counter)
            else:
                # Skip invalid rows
                continue

        # Skip if no title
        if not title:
            continue

        # Skip header-like rows
        if section_num.lower() in ['ref', 'ref.', 'section', 'no', 'no.']:
            continue
        if title.lower() in ['section', 'page', 'ref', 'ref.']:
            continue

        # Parse page number
        page = None
        if page_str and page_str.isdigit():
            page = int(page_str)

        # Handle different section numbering formats
        # Format 1: "1", "2", "3" -> keep as is (auto-numbered or explicit)
        # Format 2: "1.1", "1.2" -> keep as is (hierarchical)
        if section_num.isdigit() and len(section_num) <= 2:
            # Single digit - this is a main section
            section_number = section_num
        elif '.' in section_num:
            # Already has dot notation
            section_number = section_num
        else:
            # Letter or other format - keep as is
            section_number = section_num

        sections.append({
            'section_number': section_number,
            'title': title,
            'page': page
        })

        section_counter += 1

    return sections if sections else None

def calculate_page_ranges(sections):
    """Calculate page_end for each section based on next section's start"""
    if not sections:
        return []

    # For sections without page numbers, assign sequential pages starting from 1
    # This handles headerless TOCs where page numbers couldn't be extracted
    has_any_pages = any(s.get('page') is not None for s in sections)
    if not has_any_pages:
        # All sections lack page numbers - assign sequential pages
        for i, section in enumerate(sections, start=1):
            section['page'] = i
            section['page_end'] = None

    # Initialize page_end for all sections
    for section in sections:
        if 'page_end' not in section:
            section['page_end'] = None

    # Filter out sections without page numbers
    valid_sections = [s for s in sections if s['page'] is not None]

    if not valid_sections:
        return []

    # Sort by page number
    sorted_sections = sorted(valid_sections, key=lambda x: x['page'])

    for i, section in enumerate(sorted_sections):
        if i < len(sorted_sections) - 1:
            # End page is before next section starts
            section['page_end'] = sorted_sections[i + 1]['page'] - 1
        else:
            # Last section goes to end of document (NULL means no upper bound)
            section['page_end'] = None

    return sorted_sections

def extract_all_tocs(base_dir='output'):
    """Extract TOCs from all DCP content_list.json files (Marrickville, Ashfield, Leichhardt)"""
    output_dir = Path(base_dir)
    toc_data = {}

    # Find all content_list.json files for ALL Inner West DCPs
    patterns = [
        '**/Marrickville*DCP*/auto/*content_list.json',
        '**/Ashfield*DCP*/auto/*content_list.json',
        '**/Leichhardt*DCP*/auto/*content_list.json',
        '**/Inner*West*DCP*/auto/*content_list.json'
    ]

    json_files = []
    for pattern in patterns:
        json_files.extend(list(output_dir.glob(pattern)))

    # Remove duplicates (some files might match multiple patterns)
    json_files = list(set(json_files))

    print(f"Found {len(json_files)} DCP sections to process\n")

    for json_file in json_files:
        folder_name = json_file.parent.parent.name

        # Convert folder name to document_id format to match provisions table
        # "Marrickville DCP 2011 - 2 10 Parking" → "Marrickville_DCP_2011__2_10_Parking"
        # "Chapter E1- Heritage" → "Chapter_E1_Heritage" (dash+space becomes single underscore)
        # Process order matters to match provisions import logic:
        doc_id = (folder_name
                  .replace(',', '')  # Remove commas
                  .replace(' - ', '__')  # Main delimiter (space-dash-space)
                  .replace('- ', '_')  # Dash-space becomes underscore (e.g., "E1- " → "E1_")
                  .replace(' -', '_')  # Space-dash becomes underscore
                  .replace('-', '_')  # Any remaining dashes
                  .replace(' ', '_'))  # All remaining spaces

        print(f"Processing: {folder_name[:60]}...")

        toc = extract_toc_from_content_list(json_file)

        if toc:
            # Calculate page ranges
            toc_with_ranges = calculate_page_ranges(toc)

            if toc_with_ranges:
                toc_data[doc_id] = {
                    'document_id': doc_id,
                    'folder_name': folder_name,
                    'sections': toc_with_ranges
                }
                print(f"  OK Extracted TOC: {len(toc_with_ranges)} sections")
            else:
                print(f"  X No valid sections with page numbers")
        else:
            print(f"  X No TOC found")

    return toc_data

def create_toc_table(cur):
    """Create dcp_table_of_contents table"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS dcp_table_of_contents (
            id SERIAL PRIMARY KEY,
            document_id TEXT NOT NULL,
            section_number TEXT NOT NULL,
            section_title TEXT NOT NULL,
            page_start INTEGER NOT NULL,
            page_end INTEGER,
            part_number INTEGER,
            depth INTEGER NOT NULL,
            parent_section TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );

        -- Drop existing indexes if they exist
        DROP INDEX IF EXISTS idx_dcp_toc_document;
        DROP INDEX IF EXISTS idx_dcp_toc_pages;
        DROP INDEX IF EXISTS idx_dcp_toc_section;

        -- Create indexes
        CREATE INDEX idx_dcp_toc_document
            ON dcp_table_of_contents(document_id);
        CREATE INDEX idx_dcp_toc_pages
            ON dcp_table_of_contents(document_id, page_start, page_end);
        CREATE INDEX idx_dcp_toc_section
            ON dcp_table_of_contents(section_number);
    """)
    print("OK Created dcp_table_of_contents table with indexes")

def insert_into_database(toc_data):
    """Insert TOC structure into database"""

    # Database connection
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        database=os.getenv('DB_NAME', 'nsw_planning'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )

    cur = conn.cursor()

    try:
        # Create table
        create_toc_table(cur)

        # Clear existing data
        cur.execute("TRUNCATE TABLE dcp_table_of_contents;")
        print("OK Cleared existing TOC data")

        # Prepare data for bulk insert
        rows = []

        for doc_id, data in toc_data.items():
            for section in data['sections']:
                # Skip sections without page numbers (can't link to provisions)
                if section['page'] is None:
                    continue

                # Determine depth (2.10 = depth 2, 2.10.1 = depth 3)
                depth = section['section_number'].count('.') + 1

                # Extract part number (first number before dot)
                try:
                    part = int(section['section_number'].split('.')[0])
                except:
                    part = None

                # Parent section (2.10.1 → parent is 2.10)
                parts = section['section_number'].split('.')
                parent = '.'.join(parts[:-1]) if len(parts) > 1 else None

                rows.append((
                    doc_id,
                    section['section_number'],
                    section['title'],
                    section['page'],
                    section['page_end'],
                    part,
                    depth,
                    parent
                ))

        # Bulk insert
        execute_values(
            cur,
            """
            INSERT INTO dcp_table_of_contents
                (document_id, section_number, section_title,
                 page_start, page_end, part_number, depth, parent_section)
            VALUES %s
            """,
            rows
        )

        conn.commit()
        print(f"OK Inserted {len(rows)} TOC entries for {len(toc_data)} documents")

        # Show summary statistics
        cur.execute("""
            SELECT
                COUNT(DISTINCT document_id) as documents,
                COUNT(*) as total_sections,
                COUNT(CASE WHEN depth = 2 THEN 1 END) as main_sections,
                COUNT(CASE WHEN depth = 3 THEN 1 END) as subsections,
                COUNT(CASE WHEN depth > 3 THEN 1 END) as sub_subsections
            FROM dcp_table_of_contents
        """)

        stats = cur.fetchone()
        print(f"\n=== TOC Statistics ===")
        print(f"Documents: {stats[0]}")
        print(f"Total sections: {stats[1]}")
        print(f"Main sections (e.g., 2.10): {stats[2]}")
        print(f"Subsections (e.g., 2.10.1): {stats[3]}")
        print(f"Sub-subsections (e.g., 2.10.1.1): {stats[4]}")

    except Exception as e:
        conn.rollback()
        print(f"X Error inserting data: {e}")
        raise
    finally:
        cur.close()
        conn.close()

def verify_toc_data():
    """Verify TOC data matches provisions"""
    conn = psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', '5432')),
        database=os.getenv('DB_NAME', 'nsw_planning'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD')
    )

    cur = conn.cursor()

    # Test query: Get provision counts for section 2.10 Parking
    cur.execute("""
        SELECT
            t.section_number,
            t.section_title,
            t.page_start,
            t.page_end,
            COUNT(p.id) as provision_count
        FROM dcp_table_of_contents t
        LEFT JOIN regulatory_provisions p
            ON p.document_id = t.document_id
            AND p.pdf_page >= t.page_start
            AND (p.pdf_page <= t.page_end OR t.page_end IS NULL)
        WHERE t.document_id = 'Marrickville_DCP_2011__2_10_Parking'
        GROUP BY t.section_number, t.section_title, t.page_start, t.page_end
        ORDER BY t.page_start
        LIMIT 10
    """)

    print(f"\n=== Sample: 2.10 Parking Subsections ===")
    for row in cur.fetchall():
        section_num, title, page_start, page_end, count = row
        page_range = f"{page_start}-{page_end}" if page_end else f"{page_start}+"
        print(f"{section_num} {title[:40]:40} | Pages {page_range:8} | {count:3} provisions")

    cur.close()
    conn.close()

def main():
    print("="*70)
    print("DCP Table of Contents Extraction")
    print("="*70)
    print()

    # Step 1: Extract TOC from JSON files
    print("Step 1: Extracting TOC from content_list.json files...")
    print("-"*70)
    toc_data = extract_all_tocs()

    if not toc_data:
        print("\nX No TOC data extracted. Exiting.")
        return

    print(f"\nOK Successfully extracted TOC for {len(toc_data)} documents")

    # Step 2: Insert into database
    print("\n" + "="*70)
    print("Step 2: Inserting TOC data into database...")
    print("-"*70)
    insert_into_database(toc_data)

    # Step 3: Verify
    print("\n" + "="*70)
    print("Step 3: Verifying TOC data...")
    print("-"*70)
    verify_toc_data()

    print("\n" + "="*70)
    print("OK TOC Extraction Complete!")
    print("="*70)

if __name__ == '__main__':
    main()
