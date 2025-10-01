#!/usr/bin/env python3
"""
ROLLBACK Phase 2.5 Migration
=============================
Restores foreign keys to pre-migration state using backup

CRITICAL: Uses db_safety_wrapper for all database operations
"""

import sys
import os
import glob
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

def find_latest_backup():
    """Find the latest Phase 2.5 rollback backup"""
    backup_pattern = "backups/phase2b_rollback_data_*.sql"
    backups = glob.glob(backup_pattern)

    if not backups:
        print_error("No Phase 2.5 rollback backup found")
        print_info(f"Looking for: {backup_pattern}")
        return None

    # Sort by modification time (newest first)
    backups.sort(key=os.path.getmtime, reverse=True)
    latest = backups[0]

    print_info(f"Found backup: {latest}")
    mtime = os.path.getmtime(latest)
    print_info(f"Created: {datetime.fromtimestamp(mtime)}")

    return latest

def parse_backup_file(backup_file):
    """Parse backup file to extract foreign key mappings"""
    controls_map = {}  # control_id -> old_provision_id
    permissions_map = {}  # permission_id -> old_provision_id

    try:
        with open(backup_file, 'r', encoding='utf-8') as f:
            current_section = None

            for line in f:
                line = line.strip()

                if not line or not line.startswith('--'):
                    continue

                if 'Development Controls (orphaned)' in line:
                    current_section = 'controls'
                    continue
                elif 'Development Permissions (orphaned)' in line:
                    current_section = 'permissions'
                    continue
                elif line.startswith('-- Total'):
                    current_section = None
                    continue

                # Parse data lines: -- control_id,provision_id
                if current_section and ',' in line:
                    # Remove comment prefix
                    data = line.replace('--', '').strip()
                    parts = data.split(',')
                    if len(parts) == 2:
                        key_id = int(parts[0])
                        provision_id = parts[1]

                        if current_section == 'controls':
                            controls_map[key_id] = provision_id
                        elif current_section == 'permissions':
                            permissions_map[key_id] = provision_id

        print_success(f"Parsed backup: {len(controls_map)} controls, {len(permissions_map)} permissions")
        return controls_map, permissions_map

    except Exception as e:
        print_error(f"Failed to parse backup file: {e}")
        return None, None

def rollback_migration(controls_map, permissions_map):
    """Restore foreign keys to pre-migration state"""
    print_header("ROLLBACK PHASE 2.5 MIGRATION")

    print_warning("This will restore foreign keys to pre-migration state")
    print("  • Revert development_controls.provision_id")
    print("  • Revert development_permissions.source_provision_id")

    response = input("\n[WARNING] Are you sure? Type 'rollback' to confirm: ")
    if response != 'rollback':
        print("Rollback cancelled.")
        sys.exit(0)

    try:
        with get_safe_connection() as safe_conn:
            cursor = safe_conn.cursor()

            # Rollback controls
            if controls_map:
                print("\nReverting development_controls...")
                reverted_controls = 0

                for control_id, old_provision_id in controls_map.items():
                    cursor.execute("""
                        UPDATE development_controls
                        SET provision_id = %s
                        WHERE id = %s;
                    """, (old_provision_id, control_id))
                    reverted_controls += 1

                print_success(f"Reverted {reverted_controls} control foreign keys")

            # Rollback permissions
            if permissions_map:
                print("\nReverting development_permissions...")
                reverted_permissions = 0

                for permission_id, old_provision_id in permissions_map.items():
                    cursor.execute("""
                        UPDATE development_permissions
                        SET source_provision_id = %s
                        WHERE id = %s;
                    """, (old_provision_id, permission_id))
                    reverted_permissions += 1

                print_success(f"Reverted {reverted_permissions} permission foreign keys")

            # Commit changes
            safe_conn.commit()
            print_success("\nRollback complete! Database restored to pre-Phase 2.5 state.")

            return True

    except Exception as e:
        print_error(f"Rollback failed: {e}")
        return False

def verify_rollback():
    """Verify rollback was successful"""
    print_header("VERIFY ROLLBACK")

    try:
        with get_safe_connection() as safe_conn:
            cursor = safe_conn.cursor()

            # Check orphaned controls restored
            cursor.execute("""
                SELECT COUNT(*)
                FROM development_controls dc
                WHERE dc.provision_id IN (
                    SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
                );
            """)
            orphaned_controls = cursor.fetchone()[0]

            # Check orphaned permissions restored
            cursor.execute("""
                SELECT COUNT(*)
                FROM development_permissions dp
                WHERE dp.source_provision_id IS NOT NULL
                  AND dp.source_provision_id IN (
                      SELECT id::text FROM regulatory_provisions WHERE is_canonical = FALSE
                  );
            """)
            orphaned_permissions = cursor.fetchone()[0]

            print(f"Orphaned controls: {orphaned_controls:,}")
            print(f"Orphaned permissions: {orphaned_permissions:,}")

            if orphaned_controls > 0 or orphaned_permissions > 0:
                print_success("Rollback verified - database in pre-migration state")
                return True
            else:
                print_warning("No orphaned records found - rollback may not have worked")
                return False

    except Exception as e:
        print_error(f"Verification failed: {e}")
        return False

def main():
    """Main rollback execution"""
    print_header("PHASE 2.5 ROLLBACK: RESTORE FOREIGN KEYS")

    # Step 1: Find backup
    backup_file = find_latest_backup()
    if not backup_file:
        print_error("Cannot rollback without backup file")
        print_info("If you need to rollback, restore from emergency backup created during migration")
        sys.exit(1)

    # Step 2: Parse backup
    controls_map, permissions_map = parse_backup_file(backup_file)
    if controls_map is None:
        print_error("Failed to parse backup file")
        sys.exit(1)

    if not controls_map and not permissions_map:
        print_warning("No foreign keys to restore in backup")
        print_info("Database may already be in pre-migration state")
        sys.exit(0)

    # Step 3: Rollback
    if not rollback_migration(controls_map, permissions_map):
        print_error("Rollback failed")
        sys.exit(1)

    # Step 4: Verify
    if verify_rollback():
        print_header("ROLLBACK SUCCESSFUL")
        print("\nDatabase restored to pre-Phase 2.5 state")
        print("You can now re-run the migration if needed")
    else:
        print_warning("Rollback completed but verification had issues")
        print("Manually check database state")

    sys.exit(0)

if __name__ == "__main__":
    main()
