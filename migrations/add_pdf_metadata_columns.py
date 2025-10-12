#!/usr/bin/env python3
"""
Add PDF Metadata Columns to regulatory_provisions
==================================================
Hybrid approach: Critical fields as typed columns + flexible JSONB for extras

Purpose: Enable council stakeholder verification and legal defensibility
- pdf_page: Integer page number for "View PDF" links
- pdf_section: Section/clause number (e.g., "4.1.6.2", "C8")
- pdf_source_file: Original PDF filename for audit trail
- pdf_extra: JSONB for additional metadata (hierarchy, extraction method, etc.)
"""

import sys
from pathlib import Path

# Add parent directory to path to import db_safety_wrapper
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_safety_wrapper import get_safe_connection
from datetime import datetime

def add_pdf_metadata_columns():
    """Add PDF metadata columns to regulatory_provisions table"""

    print("="*80)
    print("PDF METADATA MIGRATION - PHASE 1: ADD COLUMNS")
    print("="*80)
    print(f"Started: {datetime.now().isoformat()}\n")

    conn = get_safe_connection()
    cursor = conn.cursor()

    try:
        # Step 1: Add columns
        print("Step 1: Adding pdf_page column (INTEGER)...")
        cursor.execute("""
            ALTER TABLE regulatory_provisions
            ADD COLUMN IF NOT EXISTS pdf_page INTEGER;
        """)
        print("[OK] pdf_page column added\n")

        print("Step 2: Adding pdf_section column (TEXT)...")
        cursor.execute("""
            ALTER TABLE regulatory_provisions
            ADD COLUMN IF NOT EXISTS pdf_section TEXT;
        """)
        print("[OK] pdf_section column added\n")

        print("Step 3: Adding pdf_source_file column (TEXT)...")
        cursor.execute("""
            ALTER TABLE regulatory_provisions
            ADD COLUMN IF NOT EXISTS pdf_source_file TEXT;
        """)
        print("[OK] pdf_source_file column added\n")

        print("Step 4: Adding pdf_extra column (JSONB)...")
        cursor.execute("""
            ALTER TABLE regulatory_provisions
            ADD COLUMN IF NOT EXISTS pdf_extra JSONB DEFAULT '{}';
        """)
        print("[OK] pdf_extra column added\n")

        # Step 2: Add check constraint
        print("Step 5: Adding check constraint for pdf_page...")
        cursor.execute("""
            ALTER TABLE regulatory_provisions
            DROP CONSTRAINT IF EXISTS check_pdf_page_positive;
        """)
        cursor.execute("""
            ALTER TABLE regulatory_provisions
            DROP CONSTRAINT IF EXISTS check_pdf_page_nonnegative;
        """)
        cursor.execute("""
            ALTER TABLE regulatory_provisions
            ADD CONSTRAINT check_pdf_page_nonnegative
            CHECK (pdf_page IS NULL OR pdf_page >= 0);
        """)
        print("[OK] Check constraint added\n")

        # Step 3: Add column comments for documentation
        print("Step 6: Adding column comments for documentation...")
        cursor.execute("""
            COMMENT ON COLUMN regulatory_provisions.pdf_page IS
            'Page number in original PDF (0-indexed from extraction, display as +1)';
        """)
        cursor.execute("""
            COMMENT ON COLUMN regulatory_provisions.pdf_section IS
            'Section/clause number from PDF (e.g., "4.1.6.2", "C8", "Schedule 1")';
        """)
        cursor.execute("""
            COMMENT ON COLUMN regulatory_provisions.pdf_source_file IS
            'Original PDF filename for audit trail and verification';
        """)
        cursor.execute("""
            COMMENT ON COLUMN regulatory_provisions.pdf_extra IS
            'Additional PDF metadata: text_level, hierarchy, extraction_method, etc.';
        """)
        print("[OK] Column comments added\n")

        # Commit the changes
        conn.commit()

        # Step 4: Verify columns exist
        print("Step 7: Verifying columns...")
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'regulatory_provisions'
            AND column_name IN ('pdf_page', 'pdf_section', 'pdf_source_file', 'pdf_extra')
            ORDER BY column_name;
        """)

        columns = cursor.fetchall()
        print("Columns verified:")
        for col_name, col_type, nullable in columns:
            print(f"  - {col_name} ({col_type}) nullable={nullable}")

        if len(columns) == 4:
            print("\n[SUCCESS] All 4 columns added successfully!\n")
        else:
            print(f"\n[WARNING] Expected 4 columns, found {len(columns)}\n")

        # Step 5: Check current data
        print("Step 8: Checking current data coverage...")
        cursor.execute("""
            SELECT
                COUNT(*) as total_provisions,
                COUNT(page_number) as has_page_number,
                COUNT(ref_number) as has_ref_number,
                COUNT(section_header) as has_section_header,
                COUNT(document_id) as has_document_id
            FROM regulatory_provisions;
        """)

        total, has_page, has_ref, has_section, has_doc = cursor.fetchone()
        print(f"  Total provisions: {total:,}")
        print(f"  Has page_number: {has_page:,} ({has_page/total*100:.1f}%)")
        print(f"  Has ref_number: {has_ref:,} ({has_ref/total*100:.1f}%)")
        print(f"  Has section_header: {has_section:,} ({has_section/total*100:.1f}%)")
        print(f"  Has document_id: {has_doc:,} ({has_doc/total*100:.1f}%)")

        print("\n" + "="*80)
        print("MIGRATION PHASE 1 COMPLETED SUCCESSFULLY")
        print("="*80)
        print("\nNext steps:")
        print("  1. Run backfill script to populate pdf_* columns from JSON files")
        print("  2. Add indexes after data is loaded (better performance)")
        print("  3. Update frontend to display PDF metadata")
        print("\nCompleted: " + datetime.now().isoformat())

    except Exception as e:
        conn.rollback()
        print(f"\n[ERROR] Migration failed: {e}")
        raise

    finally:
        cursor.close()
        conn.close()


if __name__ == "__main__":
    add_pdf_metadata_columns()
