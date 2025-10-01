#!/usr/bin/env python3
"""
Automated Phase 2.5 Migration Runner (No confirmation prompts)
"""
import sys
from run_phase2b_migration import (
    check_prerequisites,
    create_rollback_backup,
    run_migration,
    validate_results,
    print_summary,
    print_header
)

def main():
    print_header("PHASE 2.5 MIGRATION: FIX ORPHANED FOREIGN KEYS (AUTO)")
    print("This migration is SAFE and REVERSIBLE")
    print("Running automatically without confirmation prompts\n")

    # Prerequisites
    if not check_prerequisites():
        print("[ERROR] Prerequisites failed")
        sys.exit(1)

    # Backup
    backup_file = create_rollback_backup()
    if not backup_file:
        print("[ERROR] Backup failed")
        sys.exit(1)

    # Migration
    if not run_migration():
        print("[ERROR] Migration failed")
        sys.exit(1)

    # Validation
    success = validate_results()

    # Summary
    print_summary(backup_file, success)

    sys.exit(0 if success else 2)

if __name__ == "__main__":
    main()
