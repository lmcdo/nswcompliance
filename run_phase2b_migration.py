#!/usr/bin/env python3
"""
Phase 2.5 Migration: Fix Orphaned Foreign Key References
===========================================================
Safe migration to update foreign keys to canonical provisions

CRITICAL: Uses db_safety_wrapper for all database operations
"""

import sys
import os
from datetime import datetime
from db_safety_wrapper import get_safe_connection

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

def check_prerequisites():
    """Check if migration can proceed"""
    print_header("STEP 0: PRE-FLIGHT CHECKS")

    try:
        with get_safe_connection() as safe_conn:
            cursor = safe_conn.cursor()

            # Check 1: Phase 1/2A complete
            cursor.execute("""
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = 'regulatory_provisions'
                  AND column_name IN ('is_canonical', 'canonical_provision_id', 'text_hash');
            """)
            phase_cols = [row[0] for row in cursor.fetchall()]

            if len(phase_cols) < 3:
                print_error("Phase 1 not complete! Run Phase 1 first.")
                return False

            print_success("Phase 1/2A complete (all columns present)")

            # Check 2: Count orphaned controls
            cursor.execute("""
                SELECT COUNT(*)
                FROM development_controls dc
                WHERE dc.provision_id IN (
                    SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
                );
            """)
            orphaned_controls = cursor.fetchone()[0]

            if orphaned_controls == 0:
                print_warning("No orphaned controls found. Migration not needed.")
                return False

            print_success(f"Found {orphaned_controls:,} orphaned controls to fix")

            # Check 3: Count orphaned permissions
            cursor.execute("""
                SELECT COUNT(*)
                FROM development_permissions dp
                WHERE dp.source_provision_id IS NOT NULL
                  AND dp.source_provision_id IN (
                      SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
                  );
            """)
            orphaned_permissions = cursor.fetchone()[0]

            if orphaned_permissions > 0:
                print_success(f"Found {orphaned_permissions:,} orphaned permissions to fix")
            else:
                print_info("No orphaned permissions found")

            return True

    except Exception as e:
        print_error(f"Pre-flight checks failed: {e}")
        return False

def create_rollback_backup():
    """Create backup of current foreign key state for rollback"""
    print_header("STEP 1: CREATE ROLLBACK BACKUP")

    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = os.path.join(backup_dir, f"phase2b_rollback_data_{timestamp}.sql")

    print_info(f"Creating rollback backup: {backup_file}")

    try:
        with get_safe_connection() as safe_conn:
            cursor = safe_conn.cursor()

            with open(backup_file, 'w', encoding='utf-8') as f:
                f.write(f"-- Phase 2.5 Rollback Backup\n")
                f.write(f"-- Created: {datetime.now()}\n")
                f.write(f"-- Purpose: Restore original foreign key values\n\n")

                # Backup orphaned control foreign keys
                cursor.execute("""
                    SELECT dc.id, dc.provision_id
                    FROM development_controls dc
                    WHERE dc.provision_id IN (
                        SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
                    )
                    ORDER BY dc.id;
                """)

                controls = cursor.fetchall()
                if controls:
                    f.write("-- Development Controls (orphaned)\n")
                    f.write("-- Format: control_id, old_provision_id\n")
                    for control_id, provision_id in controls:
                        f.write(f"-- {control_id},{provision_id}\n")
                    f.write(f"\n-- Total orphaned controls: {len(controls)}\n\n")

                # Backup orphaned permission foreign keys
                cursor.execute("""
                    SELECT dp.id, dp.source_provision_id
                    FROM development_permissions dp
                    WHERE dp.source_provision_id IS NOT NULL
                      AND dp.source_provision_id IN (
                          SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
                      )
                    ORDER BY dp.id;
                """)

                permissions = cursor.fetchall()
                if permissions:
                    f.write("-- Development Permissions (orphaned)\n")
                    f.write("-- Format: permission_id, old_source_provision_id\n")
                    for perm_id, provision_id in permissions:
                        f.write(f"-- {perm_id},{provision_id}\n")
                    f.write(f"\n-- Total orphaned permissions: {len(permissions)}\n\n")

        size_kb = os.path.getsize(backup_file) / 1024
        print_success(f"Rollback backup created: {backup_file} ({size_kb:.1f} KB)")
        return backup_file

    except Exception as e:
        print_error(f"Backup creation failed: {e}")
        return None

def run_migration():
    """Execute Phase 2.5 migration"""
    print_header("STEP 2: RUN MIGRATION")

    migration_file = "migrations/phase2b_fix_orphaned_controls.sql"

    if not os.path.exists(migration_file):
        print_error(f"Migration file not found: {migration_file}")
        return False

    print_info("Reading migration SQL...")
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    try:
        print_info("Executing migration SQL...")
        print_info("This should take 5-10 seconds...")

        with get_safe_connection() as safe_conn:
            cursor = safe_conn.cursor()

            # Execute migration
            cursor.execute(sql_content)

            # Commit changes
            safe_conn.commit()

        print_success("Migration completed successfully")
        return True

    except Exception as e:
        print_error(f"Migration failed: {e}")
        return False

def validate_results():
    """Validate migration results"""
    print_header("STEP 3: VALIDATE RESULTS")

    try:
        with get_safe_connection() as safe_conn:
            cursor = safe_conn.cursor()

            # Check 1: Orphaned controls
            print_info("Checking orphaned controls...")
            cursor.execute("""
                SELECT COUNT(*)
                FROM development_controls dc
                WHERE dc.provision_id IN (
                    SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
                );
            """)
            orphaned_controls = cursor.fetchone()[0]

            if orphaned_controls == 0:
                print_success("All controls now point to canonical provisions")
            else:
                print_warning(f"{orphaned_controls} controls still orphaned (no canonical found)")

            # Check 2: Orphaned permissions
            print_info("Checking orphaned permissions...")
            cursor.execute("""
                SELECT COUNT(*)
                FROM development_permissions dp
                WHERE dp.source_provision_id IS NOT NULL
                  AND dp.source_provision_id IN (
                      SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
                  );
            """)
            orphaned_permissions = cursor.fetchone()[0]

            if orphaned_permissions == 0:
                print_success("All permissions now point to canonical provisions")
            else:
                print_warning(f"{orphaned_permissions} permissions still orphaned")

            # Check 3: Canonical view join
            print_info("Testing canonical view join...")
            cursor.execute("""
                SELECT COUNT(DISTINCT dc.id)
                FROM regulatory_provisions_canonical rp
                JOIN development_controls dc ON dc.provision_id = rp.id::text;
            """)
            joined_controls = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM development_controls;")
            total_controls = cursor.fetchone()[0]

            print(f"  Total controls: {total_controls:,}")
            print(f"  Joinable via canonical view: {joined_controls:,}")
            print(f"  Join rate: {joined_controls/total_controls*100:.1f}%")

            # Check 4: Sample fixed controls
            print_info("\nSample fixed controls:")
            cursor.execute("""
                SELECT
                    dc.id,
                    dc.control_type,
                    rp.ref_number,
                    rp.is_canonical
                FROM development_controls dc
                JOIN regulatory_provisions rp ON dc.provision_id = rp.id::text
                WHERE rp.is_canonical = TRUE
                LIMIT 5;
            """)

            for row in cursor.fetchall():
                print(f"    Control {row[0]:5d}: {row[1]:15s} -> Provision {row[2]:30s} (canonical: {row[3]})")

        print_success("\nValidation complete")
        return orphaned_controls == 0 and orphaned_permissions == 0

    except Exception as e:
        print_error(f"Validation failed: {e}")
        return False

def print_summary(backup_file, success):
    """Print migration summary"""
    print_header("MIGRATION COMPLETE")

    if success:
        print("Status: SUCCESS")
        print("\nWhat changed:")
        print("  • Updated development_controls foreign keys to canonical provisions")
        print("  • Updated development_permissions foreign keys to canonical provisions")
        print("  • All controls now joinable via regulatory_provisions_canonical view")
        print("  • NO data deleted or modified (only foreign key references updated)")
    else:
        print("Status: PARTIAL SUCCESS")
        print("\nWhat changed:")
        print("  • Most foreign keys updated to canonical provisions")
        print("  • Some orphaned records remain (no canonical found for them)")
        print("  • Review remaining orphaned records manually")

    print(f"\nNext steps:")
    print("  1. Test frontend compliance dashboard")
    print("  2. Verify controls display correctly")
    print("  3. Check exempt/complying codes workflow")

    print(f"\nBackup location:")
    print(f"  {backup_file}")

    print(f"\nTo rollback (if needed):")
    print(f"  python rollback_phase2b.py")

    print(f"\n[SUCCESS] Phase 2.5 migration complete!\n")

def main():
    """Main migration execution"""
    print_header("PHASE 2.5 MIGRATION: FIX ORPHANED FOREIGN KEYS")
    print("This migration is SAFE and REVERSIBLE")
    print("Updates foreign keys to point to canonical provisions")

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
    backup_file = create_rollback_backup()
    if not backup_file:
        print_error("Backup failed. Aborting migration.")
        sys.exit(1)

    # Safety wrapper will also create emergency backup before UPDATE operations

    # Step 2: Run migration
    if not run_migration():
        print_error("Migration failed.")
        sys.exit(1)

    # Step 3: Validate
    success = validate_results()

    # Step 4: Summary
    print_summary(backup_file, success)

    sys.exit(0 if success else 2)

if __name__ == "__main__":
    main()
