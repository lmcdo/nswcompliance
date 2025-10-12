#!/usr/bin/env python3
"""
Fix Orphaned Document IDs - Critical Priority
==============================================
Fixes 2,486 provisions with document_ids that don't match documents table format.

Problem:
- Provisions use: "Inner West Ashfield DCP 2016 - Chapter E1..."
- Documents use: "Inner_West_Ashfield_DCP_2016___Chapter_E1..."

Solution:
1. Find all orphaned provisions
2. Normalize document_id format (spaces → underscores, " - " → "___")
3. Match against documents table
4. Update provisions with correct document_id
5. Verify all provisions now have valid document references

Safety:
- Dry run mode first
- Transaction rollback on errors
- Detailed logging of changes
- Backup recommendation
"""

import sys
from pathlib import Path
import re

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_safety_wrapper import get_safe_connection
from datetime import datetime


class DocumentIDFixer:
    def __init__(self, dry_run=True):
        self.conn = get_safe_connection()
        self.cursor = self.conn.cursor()
        self.dry_run = dry_run
        self.fixed_count = 0
        self.no_match_count = 0
        self.error_count = 0
        self.changes = []

    def normalize_document_id(self, doc_id: str) -> str:
        """
        Convert provision document_id format to documents table format.

        Examples:
        "Inner West Ashfield DCP 2016 - Chapter E1- Heritage..."
        → "Inner_West_Ashfield_DCP_2016___Chapter_E1__Heritage..."

        "State Environmental Planning Policy (Transport and Infrastructure) 2021 - NSW Legislation"
        → "State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021___NSW_Legislation"
        """
        # Step 1: Replace " - " with "___" (triple underscore separator)
        normalized = doc_id.replace(' - ', '___')

        # Step 2: Replace remaining spaces with "_"
        normalized = normalized.replace(' ', '_')

        # Step 3: Handle edge cases
        # Multiple underscores in a row (from "  - " or similar)
        normalized = re.sub(r'_{4,}', '___', normalized)

        return normalized

    def find_orphaned_provisions(self):
        """Find all provisions with document_ids that don't exist in documents table"""
        print("\n" + "="*80)
        print("FINDING ORPHANED PROVISIONS")
        print("="*80)

        self.cursor.execute("""
            SELECT
                rp.id,
                rp.document_id,
                rp.ref_number,
                LEFT(rp.provision_text, 100) as text_preview
            FROM regulatory_provisions rp
            LEFT JOIN documents d ON rp.document_id = d.id
            WHERE d.id IS NULL
            ORDER BY rp.document_id, rp.id;
        """)

        orphaned = self.cursor.fetchall()

        print(f"Found {len(orphaned)} orphaned provisions")

        if len(orphaned) > 0:
            # Show sample
            print("\nSample orphaned provisions:")
            for i, (prov_id, doc_id, ref_num, text) in enumerate(orphaned[:5]):
                print(f"  {prov_id}: {doc_id[:60]}...")
                print(f"     Ref: {ref_num}")
                print(f"     Text: {text}...")
                print()

        return orphaned

    def find_matching_document(self, provision_doc_id: str):
        """
        Try to find matching document using normalized ID.
        Returns (document_id, pdf_name) or (None, None) if not found.
        """
        normalized = self.normalize_document_id(provision_doc_id)

        # Try exact match first
        self.cursor.execute("""
            SELECT id, pdf_name
            FROM documents
            WHERE id = %s;
        """, (normalized,))

        result = self.cursor.fetchone()
        if result:
            return result

        # Try fuzzy match (normalized version might have slight differences)
        # Remove trailing/leading underscores and try again
        normalized_clean = normalized.strip('_')
        self.cursor.execute("""
            SELECT id, pdf_name
            FROM documents
            WHERE id = %s OR id LIKE %s OR id LIKE %s;
        """, (normalized_clean, f"{normalized_clean}%", f"%{normalized_clean}"))

        result = self.cursor.fetchone()
        if result:
            return result

        return None, None

    def fix_provision(self, provision_id: int, old_doc_id: str, new_doc_id: str, pdf_name: str):
        """Update a single provision's document_id"""

        change_record = {
            'provision_id': provision_id,
            'old_doc_id': old_doc_id,
            'new_doc_id': new_doc_id,
            'pdf_name': pdf_name
        }

        if not self.dry_run:
            try:
                self.cursor.execute("""
                    UPDATE regulatory_provisions
                    SET document_id = %s
                    WHERE id = %s;
                """, (new_doc_id, provision_id))

                self.fixed_count += 1
                self.changes.append(change_record)

            except Exception as e:
                print(f"  [ERROR] Failed to update provision {provision_id}: {e}")
                self.error_count += 1
                self.conn.rollback()
                raise
        else:
            self.fixed_count += 1
            self.changes.append(change_record)

    def process_orphaned_provisions(self, orphaned_list):
        """Process all orphaned provisions and fix their document_ids"""
        print("\n" + "="*80)
        print(f"{'DRY RUN - ' if self.dry_run else ''}PROCESSING ORPHANED PROVISIONS")
        print("="*80)

        # Group by document_id to show progress better
        by_doc = {}
        for prov_id, doc_id, ref_num, text in orphaned_list:
            if doc_id not in by_doc:
                by_doc[doc_id] = []
            by_doc[doc_id].append((prov_id, ref_num, text))

        print(f"Found {len(by_doc)} unique orphaned document IDs")
        print()

        for doc_id, provisions in by_doc.items():
            print(f"\nProcessing: {doc_id}")
            print(f"  Provisions: {len(provisions)}")

            # Find matching document
            new_doc_id, pdf_name = self.find_matching_document(doc_id)

            if new_doc_id:
                print(f"  [OK] Found match: {new_doc_id}")
                print(f"    PDF: {pdf_name}")

                # Fix all provisions for this document
                for prov_id, ref_num, text in provisions:
                    self.fix_provision(prov_id, doc_id, new_doc_id, pdf_name)

                print(f"  [OK] Fixed {len(provisions)} provisions")
            else:
                print(f"  [SKIP] No match found - provisions will remain orphaned")
                self.no_match_count += len(provisions)

    def verify_fixes(self):
        """Verify that all provisions now have valid document references"""
        print("\n" + "="*80)
        print("VERIFICATION")
        print("="*80)

        # Count orphaned provisions after fix
        self.cursor.execute("""
            SELECT COUNT(*)
            FROM regulatory_provisions rp
            LEFT JOIN documents d ON rp.document_id = d.id
            WHERE d.id IS NULL;
        """)

        remaining_orphaned = self.cursor.fetchone()[0]

        print(f"Provisions fixed: {self.fixed_count:,}")
        print(f"No match found: {self.no_match_count:,}")
        print(f"Errors: {self.error_count:,}")
        print(f"Remaining orphaned: {remaining_orphaned:,}")

        if remaining_orphaned > 0:
            print(f"\n[WARNING] {remaining_orphaned} provisions still orphaned")
            print("These may need manual intervention or documents don't exist in DB")
        else:
            print("\n[SUCCESS] All provisions now have valid document references!")

        return remaining_orphaned == 0

    def generate_report(self):
        """Generate detailed report of changes"""
        print("\n" + "="*80)
        print("CHANGE REPORT")
        print("="*80)

        if not self.changes:
            print("No changes made")
            return

        print(f"\nTotal changes: {len(self.changes)}")
        print("\nSample changes:")

        for i, change in enumerate(self.changes[:10]):
            print(f"\n{i+1}. Provision {change['provision_id']}")
            print(f"   Old: {change['old_doc_id'][:70]}...")
            print(f"   New: {change['new_doc_id'][:70]}...")
            print(f"   PDF: {change['pdf_name']}")

        if len(self.changes) > 10:
            print(f"\n... and {len(self.changes) - 10} more")

        # Save full report
        if not self.dry_run:
            report_file = f"migration_markers/fix_orphaned_ids_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            Path("migration_markers").mkdir(exist_ok=True)

            with open(report_file, 'w') as f:
                f.write("Document ID Fix Report\n")
                f.write("="*80 + "\n\n")
                f.write(f"Date: {datetime.now().isoformat()}\n")
                f.write(f"Total changes: {len(self.changes)}\n\n")

                for change in self.changes:
                    f.write(f"Provision {change['provision_id']}:\n")
                    f.write(f"  Old: {change['old_doc_id']}\n")
                    f.write(f"  New: {change['new_doc_id']}\n")
                    f.write(f"  PDF: {change['pdf_name']}\n\n")

            print(f"\n[OK] Full report saved to: {report_file}")

    def run(self):
        """Main execution flow"""
        print("="*80)
        print("FIX ORPHANED DOCUMENT IDS - CRITICAL PRIORITY")
        print("="*80)
        print(f"Mode: {'DRY RUN' if self.dry_run else 'LIVE UPDATE'}")
        print(f"Started: {datetime.now().isoformat()}\n")

        # Step 1: Find orphaned provisions
        orphaned = self.find_orphaned_provisions()

        if not orphaned:
            print("\n[SUCCESS] No orphaned provisions found!")
            return True

        # Step 2: Process and fix
        self.process_orphaned_provisions(orphaned)

        # Step 3: Commit or rollback
        if not self.dry_run:
            if self.error_count > 0:
                print("\n[WARNING] Errors occurred - rolling back all changes")
                self.conn.rollback()
                return False
            else:
                print(f"\n[OK] Committing {self.fixed_count} changes...")
                self.conn.commit()

        # Step 4: Verify
        success = self.verify_fixes()

        # Step 5: Report
        self.generate_report()

        print("\n" + "="*80)
        if self.dry_run:
            print("DRY RUN COMPLETE")
            print("="*80)
            print("\nNo changes were made to the database.")
            print("Run with --live flag to apply changes.")
        else:
            print("MIGRATION COMPLETE")
            print("="*80)
            print(f"Fixed: {self.fixed_count:,} provisions")
            print(f"No match: {self.no_match_count:,} provisions")
            print(f"Errors: {self.error_count:,} provisions")

        return success

    def close(self):
        """Close database connection"""
        if self.cursor:
            self.cursor.close()
        if self.conn:
            self.conn.close()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Fix orphaned document IDs')
    parser.add_argument('--live', action='store_true',
                       help='Apply changes (default is dry run)')
    parser.add_argument('--no-backup-check', action='store_true',
                       help='Skip backup verification (NOT recommended)')

    args = parser.parse_args()

    # Safety check
    if args.live and not args.no_backup_check:
        print("\n" + "="*80)
        print("WARNING: SAFETY CHECK")
        print("="*80)
        print("\nThis migration will modify 2,000+ provisions.")
        print("Have you created a database backup?")
        print("\nRecommended backup command:")
        print("  python create_backup.py")
        print("\nOr use PostgreSQL dump:")
        print('  pg_dump -U postgres nsw_planning > backup_before_id_fix.sql')

        response = input("\nContinue? (yes/no): ")
        if response.lower() != 'yes':
            print("\nMigration cancelled. Create a backup first!")
            return False

    # Run migration
    dry_run = not args.live
    fixer = DocumentIDFixer(dry_run=dry_run)

    try:
        success = fixer.run()
        return success
    finally:
        fixer.close()


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
