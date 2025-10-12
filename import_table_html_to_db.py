#!/usr/bin/env python3
"""
Import Table HTML from JSON Extraction Files to Database
=========================================================
Finds table elements in JSON files and updates corresponding provisions
in the database with parsed, human-readable table content.
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from db_safety_wrapper import get_safe_connection

class TableHTMLImporter:
    def __init__(self):
        self.conn = get_safe_connection()
        self.cursor = self.conn.cursor()
        self.tables_found = 0
        self.tables_imported = 0
        self.provisions_updated = 0
        self.updated_provisions = set()  # Track which provisions we've already updated

    def find_all_json_files(self) -> List[Path]:
        """Find all JSON files in output directory"""
        output_dir = Path("output")
        if not output_dir.exists():
            print(f"ERROR: Output directory not found at {output_dir}")
            return []

        json_files = list(output_dir.rglob("*_content_list.json"))
        print(f"Found {len(json_files)} content_list.json files")
        return json_files

    def extract_document_id_from_path(self, json_path: Path) -> str:
        """Extract document ID from JSON file path"""
        # Get the parent directory name as document ID
        doc_id = json_path.parent.parent.name

        # Clean up common patterns
        doc_id = doc_id.replace(" - ", " ")
        doc_id = re.sub(r'\s+', ' ', doc_id).strip()

        return doc_id

    def parse_html_table_to_text(self, table_html: str) -> str:
        """Parse HTML table into human-readable text"""
        soup = BeautifulSoup(table_html, 'html.parser')
        table = soup.find('table')

        if not table:
            return table_html

        rows = []
        for tr in table.find_all('tr'):
            cells = []
            for cell in tr.find_all(['td', 'th']):
                text = cell.get_text(strip=True)
                cells.append(text)

            if cells:
                rows.append(' | '.join(cells))

        return '\n'.join(rows)

    def parse_setback_table(self, table_html: str) -> str:
        """Parse table into markdown table format for ReactMarkdown rendering"""
        soup = BeautifulSoup(table_html, 'html.parser')
        table = soup.find('table')

        if not table:
            return table_html

        rows = table.find_all('tr')
        if not rows:
            return table_html

        # Extract header row for context
        header_row = rows[0] if rows else None
        table_title = ""
        if header_row:
            header_cells = header_row.find_all(['td', 'th'])
            header_text = ' '.join([cell.get_text(strip=True) for cell in header_cells])
            table_title = header_text

        # Build markdown table with rowspan handling
        # Markdown doesn't support rowspan, so we repeat values
        markdown_rows = []
        rowspan_tracker = {}  # {col_index: (value, remaining_rows)}

        for row_idx, row in enumerate(rows):
            cells = row.find_all(['td', 'th'])

            # Build current row data accounting for rowspans
            current_row = []
            cell_idx = 0
            col_position = 0

            while cell_idx < len(cells) or col_position in rowspan_tracker:
                # Check if this column position has a rowspan from previous row
                if col_position in rowspan_tracker:
                    value, remaining = rowspan_tracker[col_position]
                    current_row.append(value)

                    if remaining > 1:
                        rowspan_tracker[col_position] = (value, remaining - 1)
                    else:
                        del rowspan_tracker[col_position]

                    col_position += 1
                elif cell_idx < len(cells):
                    cell = cells[cell_idx]
                    cell_text = cell.get_text(strip=True)

                    # Handle colspan and rowspan
                    colspan = int(cell.get('colspan', 1))
                    rowspan = int(cell.get('rowspan', 1))

                    # Add cell value once, then empty cells for remaining colspan
                    current_row.append(cell_text)

                    # Track rowspan for THIS column only
                    if rowspan > 1:
                        rowspan_tracker[col_position] = (cell_text, rowspan - 1)

                    col_position += 1

                    # For colspan > 1, add empty cells for remaining columns
                    for _ in range(colspan - 1):
                        current_row.append('')
                        col_position += 1

                    cell_idx += 1
                else:
                    break

            markdown_rows.append(current_row)

        if not markdown_rows:
            return self.parse_html_table_to_text(table_html)

        # Build markdown table output
        output_lines = []

        # Add table title if available
        if table_title and 'setback' in table_title.lower():
            output_lines.append(f"**{table_title}**\n")

        # Get number of columns from first row
        num_cols = len(markdown_rows[0]) if markdown_rows else 0

        if num_cols == 0:
            return self.parse_html_table_to_text(table_html)

        # Check if any column is always empty (except header)
        empty_cols = []
        for col_idx in range(num_cols):
            is_empty = True
            for row_idx in range(1, len(markdown_rows)):  # Skip header
                if col_idx < len(markdown_rows[row_idx]) and markdown_rows[row_idx][col_idx].strip():
                    is_empty = False
                    break
            if is_empty:
                empty_cols.append(col_idx)

        # Remove empty columns
        if empty_cols:
            for row_idx in range(len(markdown_rows)):
                markdown_rows[row_idx] = [cell for col_idx, cell in enumerate(markdown_rows[row_idx]) if col_idx not in empty_cols]
            num_cols = len(markdown_rows[0])

        # Build markdown table header (first row)
        output_lines.append('| ' + ' | '.join(markdown_rows[0]) + ' |')
        output_lines.append('| ' + ' | '.join(['---'] * num_cols) + ' |')

        # Build data rows
        for row in markdown_rows[1:]:
            # Pad row if needed to match column count
            while len(row) < num_cols:
                row.append('')
            output_lines.append('| ' + ' | '.join(row[:num_cols]) + ' |')

        return '\n'.join(output_lines)

    def find_matching_provision(self, document_id: str, table_context: str, page_num: int) -> Optional[int]:
        """Find provision that matches this table content"""

        # Convert document_id to wildcard pattern
        doc_pattern = document_id.replace(' ', '%').replace('-', '%').replace('_', '%')

        # Get all table provisions from this document
        self.cursor.execute("""
            SELECT id, ref_number, provision_text
            FROM regulatory_provisions
            WHERE document_id ILIKE %s
            AND (ref_number ILIKE '%%table%%' OR provision_text ILIKE '%%Table showing%%')
            ORDER BY id
        """, (f"%{doc_pattern}%",))

        provisions = self.cursor.fetchall()

        if not provisions:
            return None

        # Smart matching: Find best match based on table content
        table_lower = table_context.lower()
        best_match = None
        best_score = 0

        for prov_id, ref_num, prov_text in provisions:
            score = 0
            ref_lower = (ref_num or '').lower()
            text_lower = (prov_text or '').lower()

            # Check for keyword matches
            keywords = {
                'side': ['side', 'lateral'],
                'front': ['front', 'street'],
                'rear': ['rear', 'back'],
                'setback': ['setback', 'building line'],
                'coverage': ['coverage', 'site coverage'],
                'lot': ['lot', 'allotment'],
            }

            for category, terms in keywords.items():
                table_has = any(term in table_lower for term in terms)
                prov_has = any(term in text_lower or term in ref_lower for term in terms)

                if table_has and prov_has:
                    score += 2

            # If we found a strong match, use it
            if score > best_score:
                best_score = score
                best_match = prov_id

        # Return best match, or first provision if no good match
        if best_match:
            return best_match
        elif provisions:
            return provisions[0][0]

        return None

    def process_json_file(self, json_path: Path) -> int:
        """Process a single JSON file and import tables"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                return 0

            # Extract document ID
            document_id = self.extract_document_id_from_path(json_path)

            # Find all tables in this file
            tables = [item for item in data if item.get('type') == 'table']

            if not tables:
                return 0

            print(f"\nProcessing: {document_id}")
            print(f"  Found {len(tables)} tables")

            imported_count = 0

            for table in tables:
                self.tables_found += 1

                table_html = table.get('table_body', '')
                page_idx = table.get('page_idx', 0)

                if not table_html:
                    continue

                # Parse table to readable text
                parsed_table = self.parse_setback_table(table_html)

                # Find matching provision
                provision_id = self.find_matching_provision(document_id, parsed_table, page_idx)

                if provision_id:
                    # Skip if we've already updated this provision
                    if provision_id in self.updated_provisions:
                        print(f"  [SKIP] Provision {provision_id} already updated, skipping duplicate")
                        continue

                    # Update provision with parsed table content
                    self.cursor.execute("""
                        UPDATE regulatory_provisions
                        SET provision_text = %s
                        WHERE id = %s
                    """, (parsed_table, provision_id))

                    self.updated_provisions.add(provision_id)
                    self.provisions_updated += 1
                    imported_count += 1

                    print(f"  [OK] Updated provision {provision_id} with table content")
                else:
                    print(f"  [WARN] No matching provision found for table on page {page_idx}")

            self.conn.commit()
            return imported_count

        except Exception as e:
            print(f"ERROR processing {json_path}: {e}")
            return 0

    def run_import(self):
        """Main import process"""
        print("="*70)
        print("TABLE HTML -> DATABASE IMPORT")
        print("="*70)
        print("Finding tables in JSON files and updating database provisions\n")

        # Find all JSON files
        json_files = self.find_all_json_files()

        if not json_files:
            print("ERROR: No JSON files found")
            return

        # Process each file
        for json_file in json_files:
            self.process_json_file(json_file)

        # Summary
        print("\n" + "="*70)
        print("IMPORT SUMMARY")
        print("="*70)
        print(f"JSON files processed: {len(json_files)}")
        print(f"Tables found: {self.tables_found}")
        print(f"Provisions updated: {self.provisions_updated}")
        print(f"\n[OK] Table content now available in database!")
        print("="*70)

    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    """Main execution"""
    importer = TableHTMLImporter()

    try:
        importer.run_import()
    finally:
        importer.close()


if __name__ == "__main__":
    main()
