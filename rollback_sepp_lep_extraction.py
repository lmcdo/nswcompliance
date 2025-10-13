#!/usr/bin/env python3
"""
EMERGENCY ROLLBACK - Restore database to pre-extraction state
"""
import subprocess
import sys
from pathlib import Path
from glob import glob

BACKUP_PATTERN = "backups/nsw_planning_before_sepp_lep_extraction_*.backup"
PSQL_PATH = r"C:\Program Files\PostgreSQL\17\bin\psql.exe"
PG_RESTORE_PATH = r"C:\Program Files\PostgreSQL\17\bin\pg_restore.exe"

def find_latest_backup():
    """Find the most recent backup file"""
    backups = glob(BACKUP_PATTERN)
    if not backups:
        print(f"[ERROR] No backup found matching: {BACKUP_PATTERN}")
        return None

    # Sort by filename (timestamp) to get latest
    latest = sorted(backups)[-1]
    return latest

def main():
    print("="*60)
    print("EMERGENCY ROLLBACK INITIATED")
    print("="*60)
    print("\nThis will restore database to state before SEPP/LEP extraction")

    # Find backup
    backup_file = find_latest_backup()
    if not backup_file:
        return 1

    print(f"\nBackup file: {backup_file}")
    confirm = input("\nAre you sure? (type 'yes' to confirm): ")

    if confirm.lower() != 'yes':
        print("\nRollback cancelled")
        return 0

    print("\n1. Creating backup of current state (just in case)...")
    from datetime import datetime
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    emergency_backup = f"backups/emergency_before_rollback_{timestamp}.backup"

    result = subprocess.run([
        r"C:\Program Files\PostgreSQL\17\bin\pg_dump.exe",
        "-U", "postgres",
        "-h", "localhost",
        "--format=custom",
        f"--file={emergency_backup}",
        "nsw_planning"
    ])

    if result.returncode != 0:
        print("[ERROR] Failed to create emergency backup!")
        return 1

    print(f"   [OK] Emergency backup created: {emergency_backup}")

    print("\n2. Restoring from backup...")
    print("   Note: This may take 1-2 minutes...")

    # Use pg_restore with --clean to drop existing objects first
    result = subprocess.run([
        PG_RESTORE_PATH,
        "-U", "postgres",
        "-h", "localhost",
        "-d", "nsw_planning",
        "--clean",
        "--if-exists",
        backup_file
    ], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"[ERROR] Restore failed: {result.stderr}")
        return 1

    print("   [OK] Restore completed")

    print("\n3. Verifying restoration...")
    result = subprocess.run([
        PSQL_PATH,
        "-U", "postgres",
        "-h", "localhost",
        "-d", "nsw_planning",
        "-c", "SELECT COUNT(*) as provisions, COUNT(*) FILTER (WHERE pdf_page IS NOT NULL) as with_page FROM regulatory_provisions;"
    ])

    if result.returncode != 0:
        print("[ERROR] Verification failed!")
        return 1

    print("\n" + "="*60)
    print("[SUCCESS] ROLLBACK COMPLETE")
    print("="*60)
    print("\nDatabase restored to pre-extraction state")
    print(f"Emergency backup of rolled-back state: {emergency_backup}")

    return 0

if __name__ == "__main__":
    sys.exit(main())
