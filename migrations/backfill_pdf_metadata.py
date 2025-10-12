#!/usr/bin/env python3
"""
Backfill PDF Metadata from JSON Extraction Files
================================================
Populates pdf_page, pdf_section, pdf_source_file, pdf_extra columns
from the output/**/*_content_list.json files.

Strategy:
1. Find all *_content_list.json files in output/
2. For each document, extract:
   - page_idx → pdf_page
   - Extract section numbers from text_level==1 elements
   - Document name → pdf_source_file
   - text_level, img_path, etc → pdf_extra JSONB
3. Match provisions by document_id and text content
4. Update in batches for performance
"""

import sys
from pathlib import Path
import json
import re

# Add parent directory to path to import db_safety_wrapper
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_safety_wrapper import get_safe_connection
from datetime import datetime


class PDFMetadataBackfiller:
    def __init__(self):
        self.conn = get_safe_connection()
        self.cursor = self.conn.cursor()
        self.updated_count = 0
        self.skipped_count = 0
        self.error_count = 0

    def find_all_json_files(self):
        """Find all content_list.json files"""
        output_dir = Path("output")
        if not output_dir.exists():
            print(f"ERROR: Output directory not found at {output_dir}")
            return []

        json_files = list(output_dir.rglob("*_content_list.json"))
        print(f"Found {len(json_files)} JSON files")
        return json_files

    def extract_document_name(self, json_path: Path) -> str:
        """Extract clean document name from path"""
        # Example: "output/Marrickville DCP 2011 - 4.1 Low Density/auto/..."
        # → "Marrickville DCP 2011 - 4.1 Low Density Residential Development"
        doc_dir = json_path.parent.parent.name
        doc_dir = doc_dir.replace(" - ", " ").strip()
        doc_dir = re.sub(r'\s+', ' ', doc_dir)
        return doc_dir

    def extract_section_number(self, text: str) -> str:
        """Extract section number from text (e.g., '4.1.6.2', 'C8', 'Schedule 1')"""
        # Pattern 1: Numbered sections like "4.1.6.2"
        match = re.match(r'^(\d+(?:\.\d+)+[A-Z]?)\s', text)
        if match:
            return match.group(1)

        # Pattern 2: Control codes like "C8", "D12"
        match = re.match(r'^([A-Z]\d+[A-Z]?)\s*$', text.strip())
        if match:
            return match.group(1)

        # Pattern 3: Schedule references
        match = re.match(r'^(Schedule\s+\d+[A-Z]?)', text, re.IGNORECASE)
        if match:
            return match.group(1)

        return None

    def build_pdf_extra(self, item: dict) -> dict:
        """Build pdf_extra JSONB from JSON item"""
        extra = {}

        # Add text_level if present
        if 'text_level' in item:
            extra['text_level'] = item['text_level']

        # Add image path if present
        if 'img_path' in item and item['img_path']:
            extra['img_path'] = item['img_path']

        # Add table metadata
        if item.get('type') == 'table':
            if item.get('table_caption'):
                extra['table_caption'] = item['table_caption']
            if item.get('table_footnote'):
                extra['table_footnote'] = item['table_footnote']

        # Add image metadata
        if item.get('type') == 'image':
            if item.get('image_caption'):
                extra['image_caption'] = item['image_caption']
            if item.get('image_footnote'):
                extra['image_footnote'] = item['image_footnote']

        # Add extraction method
        extra['extraction_method'] = 'MinerU'
        extra['extracted_at'] = datetime.now().isoformat()

        return extra

    def process_json_file(self, json_path: Path):
        """Process a single JSON file and backfill metadata"""
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            if not isinstance(data, list):
                return

            doc_name = self.extract_document_name(json_path)
            pdf_filename = f"{doc_name}.pdf"

            print(f"\nProcessing: {doc_name}")
            print(f"  Items in JSON: {len(data)}")

            # Build a map of provisions from database
            # Query by document_id pattern
            doc_pattern = doc_name.replace(' ', '%').replace('-', '%').replace('_', '%')
            self.cursor.execute("""
                SELECT id, provision_text, ref_number, page_number
                FROM regulatory_provisions
                WHERE document_id ILIKE %s
            """, (f"%{doc_pattern}%",))

            provisions = self.cursor.fetchall()
            print(f"  Provisions in DB: {len(provisions)}")

            if not provisions:
                print(f"  [SKIP] No provisions found for this document")
                self.skipped_count += len(data)
                return

            # Process each JSON item
            updates = 0
            for item in data:
                item_type = item.get('type')
                page_idx = item.get('page_idx')
                text = item.get('text', '')

                if not page_idx and page_idx != 0:
                    continue

                # Extract section number if this is a heading
                section_number = None
                if item_type == 'text' and item.get('text_level') == 1:
                    section_number = self.extract_section_number(text)

                # Build pdf_extra
                pdf_extra = self.build_pdf_extra(item)

                # For tables, match by ref_number containing "table"
                if item_type == 'table':
                    for prov_id, prov_text, ref_num, page_num in provisions:
                        if ref_num and 'table' in ref_num.lower():
                            # Check if provision text matches table content
                            table_html = item.get('table_body', '')
                            if table_html[:100] in prov_text or prov_text[:100] in table_html:
                                self.update_provision(prov_id, page_idx, section_number, pdf_filename, pdf_extra)
                                updates += 1
                                break

                # For text, match by content similarity
                elif item_type == 'text' and text:
                    text_preview = text[:200]
                    for prov_id, prov_text, ref_num, page_num in provisions:
                        if text_preview in prov_text or prov_text[:200] in text:
                            self.update_provision(prov_id, page_idx, section_number, pdf_filename, pdf_extra)
                            updates += 1
                            break

            self.conn.commit()
            print(f"  [OK] Updated {updates} provisions")

        except Exception as e:
            print(f"  [ERROR] Failed to process {json_path}: {e}")
            self.error_count += 1
            self.conn.rollback()

    def update_provision(self, provision_id: int, page_idx: int, section_number: str, pdf_filename: str, pdf_extra: dict):
        """Update a single provision with PDF metadata"""
        try:
            self.cursor.execute("""
                UPDATE regulatory_provisions
                SET
                    pdf_page = %s,
                    pdf_section = COALESCE(pdf_section, %s),
                    pdf_source_file = COALESCE(pdf_source_file, %s),
                    pdf_extra = COALESCE(pdf_extra, '{}'::jsonb) || %s::jsonb
                WHERE id = %s
                AND pdf_page IS NULL  -- Only update if not already set
            """, (page_idx, section_number, pdf_filename, json.dumps(pdf_extra), provision_id))

            if self.cursor.rowcount > 0:
                self.updated_count += 1

        except Exception as e:
            print(f"    [ERROR] Failed to update provision {provision_id}: {e}")
            self.error_count += 1

    def add_indexes(self):
        """Add indexes after data is loaded"""
        print("\n" + "="*80)
        print("ADDING INDEXES")
        print("="*80)

        try:
            print("Creating index on pdf_page...")
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_provisions_pdf_page
                ON regulatory_provisions(pdf_page)
                WHERE pdf_page IS NOT NULL;
            """)

            print("Creating index on pdf_section...")
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_provisions_pdf_section
                ON regulatory_provisions(pdf_section)
                WHERE pdf_section IS NOT NULL;
            """)

            print("Creating GIN index on pdf_extra...")
            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_provisions_pdf_extra
                ON regulatory_provisions USING GIN(pdf_extra);
            """)

            self.conn.commit()
            print("[OK] All indexes created\n")

        except Exception as e:
            print(f"[ERROR] Failed to create indexes: {e}")
            self.conn.rollback()

    def verify_backfill(self):
        """Verify the backfill results"""
        print("="*80)
        print("VERIFICATION")
        print("="*80)

        self.cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(pdf_page) as has_page,
                COUNT(pdf_section) as has_section,
                COUNT(pdf_source_file) as has_file,
                COUNT(pdf_extra) FILTER (WHERE pdf_extra != '{}'::jsonb) as has_extra
            FROM regulatory_provisions;
        """)

        total, has_page, has_section, has_file, has_extra = self.cursor.fetchone()

        print(f"Total provisions: {total:,}")
        print(f"Has pdf_page: {has_page:,} ({has_page/total*100:.1f}%)")
        print(f"Has pdf_section: {has_section:,} ({has_section/total*100:.1f}%)")
        print(f"Has pdf_source_file: {has_file:,} ({has_file/total*100:.1f}%)")
        print(f"Has pdf_extra: {has_extra:,} ({has_extra/total*100:.1f}%)")

        # Sample data
        print("\nSample provisions with metadata:")
        self.cursor.execute("""
            SELECT id, ref_number, pdf_page, pdf_section, pdf_source_file
            FROM regulatory_provisions
            WHERE pdf_page IS NOT NULL
            LIMIT 5;
        """)

        for prov_id, ref_num, page, section, file in self.cursor.fetchall():
            print(f"  ID {prov_id}: {ref_num} | Page {page} | Section {section} | {file}")

    def run(self):
        """Main backfill process"""
        print("="*80)
        print("PDF METADATA BACKFILL - PHASE 2")
        print("="*80)
        print(f"Started: {datetime.now().isoformat()}\n")

        # Find all JSON files
        json_files = self.find_all_json_files()
        if not json_files:
            print("ERROR: No JSON files found")
            return

        # Process each file
        for json_file in json_files:
            self.process_json_file(json_file)

        # Add indexes
        self.add_indexes()

        # Verify results
        self.verify_backfill()

        print("\n" + "="*80)
        print("BACKFILL COMPLETED")
        print("="*80)
        print(f"Provisions updated: {self.updated_count:,}")
        print(f"Provisions skipped: {self.skipped_count:,}")
        print(f"Errors: {self.error_count}")
        print(f"Completed: {datetime.now().isoformat()}")

    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


if __name__ == "__main__":
    backfiller = PDFMetadataBackfiller()
    try:
        backfiller.run()
    finally:
        backfiller.close()
