#!/usr/bin/env python3
"""
Import MinerU JSON with Page Numbers - SAFE VERSION
Uses db_safety_wrapper.py for all database operations

CRITICAL SAFETY FEATURES:
- Automatic backup before any writes
- Transaction rollback on errors
- Timeout protection (30 seconds)
- Query safety validation
- Health checks before/after

Usage:
    python import_mineru_json_with_pages.py --source extraction_outputs/leps
    python import_mineru_json_with_pages.py --source extraction_outputs/sepps --document-type SEPP
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from db_safety_wrapper import get_safe_connection, DatabaseSafetyError

class MinerUImporter:
    """Safe importer for MinerU JSON output with page numbers"""

    def __init__(self, source_dir: Path, document_type: str = 'LEP', dry_run: bool = False):
        self.source_dir = source_dir
        self.document_type = document_type.upper()
        self.dry_run = dry_run
        self.stats = {
            'files_processed': 0,
            'provisions_found': 0,
            'provisions_inserted': 0,
            'provisions_updated': 0,
            'provisions_skipped': 0,
            'errors': []
        }

    def find_mineru_json_files(self) -> List[Path]:
        """Find all MinerU JSON output files"""
        json_files = []

        # MinerU creates output in subdirectories: source_dir/pdf_name/auto/pdf_name.json
        for pdf_dir in self.source_dir.iterdir():
            if not pdf_dir.is_dir():
                continue

            # Check for auto/ subdirectory
            auto_dir = pdf_dir / 'auto'
            if auto_dir.exists():
                # Find JSON file
                for json_file in auto_dir.glob('*.json'):
                    if 'content_list' not in json_file.name:  # Skip metadata files
                        json_files.append(json_file)
                        break

        return json_files

    def normalize_document_id(self, pdf_name: str) -> str:
        """Convert PDF filename to document_id format"""
        # Remove .pdf extension
        doc_id = pdf_name.replace('.pdf', '')

        # Replace spaces with underscores
        doc_id = doc_id.replace(' ', '_')

        # Replace special characters
        doc_id = doc_id.replace('-', '_')
        doc_id = doc_id.replace('(', '_')
        doc_id = doc_id.replace(')', '_')
        doc_id = doc_id.replace('__', '_')

        # Add triple underscore for separators (matches existing pattern)
        doc_id = doc_id.replace(' - ', '___')

        return doc_id

    def extract_provisions_from_json(self, json_path: Path) -> List[Dict[str, Any]]:
        """
        Extract provisions with page numbers from MinerU JSON

        MinerU JSON structure (simplified):
        {
            "pdf_info": { ... },
            "layout_dets": [
                {
                    "layout_no": 0,
                    "layout_bbox": [...],
                    "page_no": 1,
                    "text": "Provision text here..."
                },
                ...
            ]
        }
        """
        try:
            with json_path.open('r', encoding='utf-8') as f:
                data = json.load(f)

            provisions = []

            # Extract from layout_dets (MinerU's structured output)
            if 'layout_dets' in data:
                for item in data['layout_dets']:
                    text = item.get('text', '').strip()
                    page_no = item.get('page_no')

                    # Skip empty or very short text
                    if not text or len(text) < 50:
                        continue

                    # Skip headers/footers (heuristic: very short lines at top/bottom)
                    if len(text) < 100 and page_no:
                        continue

                    provisions.append({
                        'text': text,
                        'page_no': page_no,
                        'layout_no': item.get('layout_no'),
                        'bbox': item.get('layout_bbox')
                    })

            return provisions

        except Exception as e:
            print(f"Error parsing JSON {json_path}: {e}")
            self.stats['errors'].append(f"Parse error in {json_path.name}: {e}")
            return []

    def get_or_create_document(self, conn, document_id: str, pdf_name: str) -> bool:
        """Ensure document exists in documents table"""
        try:
            cursor = conn.cursor()

            # Check if document exists
            cursor.execute("""
                SELECT id FROM documents WHERE id = %s
            """, (document_id,))

            if cursor.fetchone():
                cursor.close()
                return True

            # Create document if doesn't exist
            cursor.execute("""
                INSERT INTO documents (id, document_type, pdf_name, created_at)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO NOTHING
            """, (document_id, self.document_type, pdf_name, datetime.now()))

            cursor.close()
            return True

        except Exception as e:
            print(f"Error creating document {document_id}: {e}")
            return False

    def import_provisions(self, conn, document_id: str, pdf_name: str, provisions: List[Dict]) -> int:
        """
        Import provisions to database with page numbers

        Strategy:
        - INSERT new provisions with pdf_page, pdf_source_file
        - UPDATE existing provisions if they match by text similarity
        - Use ON CONFLICT to handle duplicates
        """
        cursor = conn.cursor()
        imported = 0
        updated = 0

        for i, prov in enumerate(provisions):
            try:
                # Generate ref_number (simple: layout_no or sequential)
                ref_number = f"provision_{prov.get('layout_no', i)}"

                # Execute INSERT with ON CONFLICT
                cursor.execute("""
                    INSERT INTO regulatory_provisions (
                        document_id,
                        ref_number,
                        provision_text,
                        pdf_page,
                        pdf_source_file,
                        pdf_extra,
                        created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (document_id, ref_number) DO UPDATE SET
                        provision_text = EXCLUDED.provision_text,
                        pdf_page = EXCLUDED.pdf_page,
                        pdf_source_file = EXCLUDED.pdf_source_file,
                        pdf_extra = EXCLUDED.pdf_extra,
                        updated_at = NOW()
                    RETURNING id
                """, (
                    document_id,
                    ref_number,
                    prov['text'],
                    prov['page_no'],
                    pdf_name,
                    json.dumps({
                        'extraction_method': 'mineru',
                        'extracted_at': datetime.now().isoformat(),
                        'layout_no': prov.get('layout_no'),
                        'bbox': prov.get('bbox')
                    }),
                    datetime.now()
                ))

                result = cursor.fetchone()
                if result:
                    imported += 1

                if (i + 1) % 100 == 0:
                    print(f"  Imported {i + 1}/{len(provisions)} provisions")

            except Exception as e:
                print(f"Error importing provision {i}: {e}")
                self.stats['errors'].append(f"Import error in {document_id}: {e}")
                continue

        cursor.close()

        self.stats['provisions_inserted'] += imported
        return imported

    def verify_import(self, conn, document_id: str) -> Dict[str, Any]:
        """Verify imported provisions"""
        cursor = conn.cursor()

        cursor.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) as with_pages,
                MIN(pdf_page) as min_page,
                MAX(pdf_page) as max_page
            FROM regulatory_provisions
            WHERE document_id = %s
        """, (document_id,))

        result = cursor.fetchone()
        cursor.close()

        return {
            'total': result[0],
            'with_pages': result[1],
            'min_page': result[2],
            'max_page': result[3],
            'coverage_pct': 100.0 * result[1] / result[0] if result[0] > 0 else 0
        }

    def process_file(self, conn, json_path: Path):
        """Process a single MinerU JSON file"""
        print(f"\n{'='*60}")
        print(f"Processing: {json_path.parent.parent.name}")
        print(f"{'='*60}")

        # Extract PDF name from directory structure
        pdf_dir_name = json_path.parent.parent.name
        pdf_name = pdf_dir_name if '.pdf' in pdf_dir_name else f"{pdf_dir_name}.pdf"

        # Normalize to document_id
        document_id = self.normalize_document_id(pdf_name)
        print(f"Document ID: {document_id}")

        # Extract provisions from JSON
        print("Extracting provisions from JSON...")
        provisions = self.extract_provisions_from_json(json_path)
        print(f"Found {len(provisions)} provisions with page numbers")

        if not provisions:
            print("⚠️ No provisions found, skipping")
            self.stats['provisions_skipped'] += 1
            return

        self.stats['provisions_found'] += len(provisions)

        # Dry run mode
        if self.dry_run:
            print(f"[DRY RUN] Would import {len(provisions)} provisions")
            return

        # Ensure document exists
        if not self.get_or_create_document(conn, document_id, pdf_name):
            print("❌ Failed to create document, skipping")
            return

        # Import provisions
        print("Importing provisions to database...")
        imported = self.import_provisions(conn, document_id, pdf_name, provisions)
        print(f"✅ Imported {imported} provisions")

        # Verify
        verification = self.verify_import(conn, document_id)
        print(f"\nVerification:")
        print(f"  Total provisions: {verification['total']}")
        print(f"  With page numbers: {verification['with_pages']}")
        print(f"  Page range: {verification['min_page']}-{verification['max_page']}")
        print(f"  Coverage: {verification['coverage_pct']:.1f}%")

        self.stats['files_processed'] += 1

    def run(self):
        """Main import process"""
        print("="*60)
        print(f"MINERU JSON IMPORT - {self.document_type}")
        print("="*60)
        print(f"Source: {self.source_dir}")
        print(f"Document Type: {self.document_type}")
        print(f"Dry Run: {self.dry_run}")
        print("="*60)

        # Find JSON files
        json_files = self.find_mineru_json_files()
        print(f"\nFound {len(json_files)} JSON files to process")

        if not json_files:
            print("⚠️ No MinerU JSON files found!")
            print("\nExpected directory structure:")
            print("  source_dir/")
            print("    pdf_name/")
            print("      auto/")
            print("        pdf_name.json  ← MinerU output")
            return False

        # Connect with safety wrapper
        try:
            print("\nConnecting to database (with safety checks)...")
            conn = get_safe_connection()
            print("✅ Database connection established (safety protocols active)")

            # Process each file
            for json_file in json_files:
                try:
                    self.process_file(conn, json_file)

                    # Commit after each file
                    if not self.dry_run:
                        conn.commit()

                except Exception as e:
                    print(f"❌ Error processing {json_file.name}: {e}")
                    self.stats['errors'].append(f"File error {json_file.name}: {e}")
                    conn.rollback()
                    continue

            # Final commit
            if not self.dry_run:
                conn.commit()

            conn.close()

        except DatabaseSafetyError as e:
            print(f"\n🚨 DATABASE SAFETY ERROR: {e}")
            print("Import aborted for safety reasons")
            return False

        except Exception as e:
            print(f"\n❌ CRITICAL ERROR: {e}")
            return False

        # Print final stats
        self.print_stats()
        return True

    def print_stats(self):
        """Print import statistics"""
        print("\n" + "="*60)
        print("IMPORT COMPLETE")
        print("="*60)
        print(f"Files processed: {self.stats['files_processed']}")
        print(f"Provisions found: {self.stats['provisions_found']}")
        print(f"Provisions inserted: {self.stats['provisions_inserted']}")
        print(f"Provisions updated: {self.stats['provisions_updated']}")
        print(f"Provisions skipped: {self.stats['provisions_skipped']}")

        if self.stats['errors']:
            print(f"\n⚠️ Errors: {len(self.stats['errors'])}")
            for error in self.stats['errors'][:10]:  # Show first 10
                print(f"  - {error}")

        print("="*60)

def main():
    parser = argparse.ArgumentParser(description='Import MinerU JSON with page numbers')
    parser.add_argument('--source', type=str, required=True,
                       help='Source directory containing MinerU output')
    parser.add_argument('--document-type', type=str, default='LEP',
                       choices=['LEP', 'SEPP', 'DCP'],
                       help='Document type to import')
    parser.add_argument('--dry-run', action='store_true',
                       help='Dry run mode (no database writes)')

    args = parser.parse_args()

    source_dir = Path(args.source)
    if not source_dir.exists():
        print(f"❌ Source directory not found: {source_dir}")
        return 1

    importer = MinerUImporter(source_dir, args.document_type, args.dry_run)
    success = importer.run()

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
