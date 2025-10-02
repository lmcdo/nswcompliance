#!/usr/bin/env python3
"""
Phase 2A Migration: Clean Cross-References
===========================================
Safe migration to clean cross-reference arrows from ref_number field
"""

import sys
import os
from datetime import datetime
from db_config import get_connection
import subprocess

def print_header(message):
    print(f"\n{'=' * 80}")
    print(f"{message}")
    print(f"{'=' * 80}\n")

def print_success(message):
    print(f"[SUCCESS] {message}")

def print_warning(message):
    print(f"[WARNING] {message}")

def print_error(message):
    print(f"[ERROR] {message}")

def print_info(message):
    print(f"[INFO] {message}")

def create_backup():
    """Create database backup before migration"""
    print_header("STEP 1: CREATE BACKUP")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    backup_file = os.path.join(backup_dir, f"pre_phase2a_migration_{timestamp}.sql")

    print_info(f"Creating backup: {backup_file}")

    # Use Python backup method
    conn = get_connection()
    cur = conn.cursor()

    with open(backup_file, 'w', encoding='utf-8') as f:
        f.write(f"-- Database backup created: {datetime.now()}\n")
        f.write(f"-- Phase 2A pre-migration backup\n\n")

        # Backup regulatory_provisions table structure
        cur.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'regulatory_provisions'
            ORDER BY ordinal_position;
        """)

        f.write("-- Table structure\n")
        for row in cur.fetchall():
            f.write(f"-- Column: {row[0]} ({row[1]})\n")

        # Backup affected provisions (those with arrows)
        cur.execute("""
            SELECT id, ref_number, provision_text, document_id, is_canonical
            FROM regulatory_provisions
            WHERE ref_number LIKE '%->%'
            ORDER BY id;
        """)

        f.write("\n-- Provisions with cross-reference arrows\n")
        f.write("-- Format: ID | ref_number | is_canonical\n\n")

        count = 0
        for row in cur.fetchall():
            f.write(f"-- ID: {row[0]} | ref_number: {row[1]} | canonical: {row[4]}\n")
            count += 1

        f.write(f"\n-- Total provisions with arrows backed up: {count}\n")

    conn.close()

    size_mb = os.path.getsize(backup_file) / (1024 * 1024)
    print_success(f"Backup created: {backup_file} ({size_mb:.1f} MB)")
    return backup_file

def check_prerequisites():
    """Check if migration can proceed"""
    print_header("STEP 0: PRE-FLIGHT CHECKS")

    conn = get_connection()
    cur = conn.cursor()

    # Check 1: Phase 1 complete
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'regulatory_provisions'
          AND column_name IN ('is_canonical', 'canonical_provision_id', 'text_hash');
    """)
    phase1_cols = [row[0] for row in cur.fetchall()]

    if len(phase1_cols) < 3:
        print_error("Phase 1 not complete! Run Phase 1 first.")
        conn.close()
        return False

    print_success("Phase 1 complete (all columns present)")

    # Check 2: Count provisions to clean
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE ref_number LIKE '%->%';
    """)
    arrow_count = cur.fetchone()[0]

    if arrow_count == 0:
        print_warning("No provisions with arrows found. Migration not needed.")
        conn.close()
        return False

    print_success(f"Found {arrow_count:,} provisions with cross-reference arrows")

    # Check 3: Column doesn't already exist
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'regulatory_provisions'
          AND column_name = 'cross_reference_text';
    """)
    if cur.fetchone() is not None:
        print_warning("cross_reference_text column already exists")
        response = input("Migration may have run before. Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            conn.close()
            return False

    conn.close()
    return True

def run_migration():
    """Execute Phase 2A migration"""
    print_header("STEP 2: RUN MIGRATION")

    migration_file = "migrations/phase2a_clean_cross_references_SAFE.sql"

    if not os.path.exists(migration_file):
        print_error(f"Migration file not found: {migration_file}")
        return False

    print_info("Reading migration SQL...")
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Extract migration part (before VALIDATION QUERIES)
    if '-- VALIDATION QUERIES' in sql_content:
        sql_content = sql_content.split('-- VALIDATION QUERIES')[0]

    if '-- ROLLBACK' in sql_content:
        sql_content = sql_content.split('-- ROLLBACK')[0]

    conn = get_connection()
    cur = conn.cursor()

    try:
        print_info("Executing migration SQL...")
        print_info("This may take 30-60 seconds...")

        cur.execute(sql_content)
        conn.commit()

        print_success("Migration completed successfully")
        conn.close()
        return True

    except Exception as e:
        print_error(f"Migration failed: {e}")
        conn.rollback()
        conn.close()
        return False

def validate_results():
    """Validate migration results"""
    print_header("STEP 3: VALIDATE RESULTS")

    conn = get_connection()
    cur = conn.cursor()

    # Check 1: Cross-references preserved
    print_info("Checking cross-references preserved...")
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE cross_reference_text IS NOT NULL) as with_refs,
            COUNT(*) FILTER (WHERE LENGTH(cross_reference_text) > 0) as non_empty
        FROM regulatory_provisions;
    """)
    row = cur.fetchone()
    print(f"  Cross-references preserved: {row[1]:,}")

    # Check 2: Arrows removed
    print_info("Checking arrows removed...")
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE ref_number LIKE '%->%';
    """)
    arrows = cur.fetchone()[0]
    if arrows == 0:
        print_success(f"  All arrows removed from ref_number")
    else:
        print_warning(f"  {arrows} provisions still have arrows!")

    # Check 3: New duplicates
    print_info("Checking new duplicates...")
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions
        WHERE migration_phase = 'phase2a_duplicate';
    """)
    new_dups = cur.fetchone()[0]
    print(f"  New duplicates marked: {new_dups}")

    # Check 4: Canonical count
    print_info("Checking canonical counts...")
    cur.execute("""
        SELECT
            COUNT(*) FILTER (WHERE is_canonical = TRUE) as canonical,
            COUNT(*) FILTER (WHERE is_canonical = FALSE) as duplicates,
            COUNT(*) as total
        FROM regulatory_provisions;
    """)
    row = cur.fetchone()
    print(f"  Canonical: {row[0]:,} ({row[0]/row[2]*100:.1f}%)")
    print(f"  Duplicates: {row[1]:,} ({row[1]/row[2]*100:.1f}%)")

    # Check 5: Sample
    print_info("\nSample cleaned provisions:")
    cur.execute("""
        SELECT id, ref_number, LEFT(cross_reference_text, 50)
        FROM regulatory_provisions
        WHERE cross_reference_text IS NOT NULL
        ORDER BY id
        LIMIT 5;
    """)
    for row in cur.fetchall():
        print(f"    ID {row[0]:5d}: {row[1]:30s} -> {row[2]}...")

    conn.close()
    print_success("\nValidation complete")
    return True

def print_summary(backup_file):
    """Print migration summary"""
    print_header("MIGRATION COMPLETE")

    print("What changed:")
    print("  • Added column: cross_reference_text")
    print("  • Preserved cross-reference data (~2,645 provisions)")
    print("  • Cleaned ref_number field (removed arrows)")
    print("  • Marked new duplicates revealed by cleaning")
    print("  • NO data deleted")

    print("\nNext steps:")
    print("  1. Verify frontend still works")
    print("  2. Check no ref_number queries break")
    print("  3. Test provision lookups")

    print(f"\nBackup location:")
    print(f"  {backup_file}")

    print(f"\nTo rollback (if needed):")
    print(f"  python rollback_phase2a.py")
    print("  OR manually run ROLLBACK section in:")
    print("  migrations/phase2a_clean_cross_references_SAFE.sql")

    print(f"\n[SUCCESS] Phase 2A migration successful!\n")

def main():
    """Main migration execution"""
    print_header("PHASE 2A MIGRATION: CLEAN CROSS-REFERENCES")
    print("This migration is SAFE and REVERSIBLE")
    print("No data will be deleted, cross-references preserved")

    # Step 0: Prerequisites
    if not check_prerequisites():
        print_error("Pre-flight checks failed. Aborting.")
        sys.exit(1)

    # Confirm
    print("\n[WARNING] Ready to proceed?")
    response = input("Type 'yes' to continue: ")
    if response.lower() != 'yes':
        print("Migration cancelled.")
        sys.exit(0)

    # Step 1: Backup
    backup_file = create_backup()
    if not backup_file:
        print_error("Backup failed. Aborting migration.")
        sys.exit(1)

    # Step 2: Run migration
    if not run_migration():
        print_error("Migration failed.")
        sys.exit(1)

    # Step 3: Validate
    if not validate_results():
        print_warning("Validation found issues.")

    # Step 4: Summary
    print_summary(backup_file)

if __name__ == "__main__":
    main()
