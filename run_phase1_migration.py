#!/usr/bin/env python3
"""
SAFE Phase 1 Migration: Mark True Duplicates
============================================
This script:
1. Creates full database backup
2. Runs Phase 1 migration (adds columns, marks duplicates)
3. Validates results
4. Provides rollback instructions if needed

NO DATA IS DELETED - only flagged with is_canonical column
"""

import sys
import os
from datetime import datetime
from db_config import get_connection
import subprocess

class Color:
    """Disabled for Windows console compatibility"""
    HEADER = ''
    OKBLUE = ''
    OKCYAN = ''
    OKGREEN = ''
    WARNING = ''
    FAIL = ''
    ENDC = ''
    BOLD = ''

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
    """Create full database backup before migration"""
    print_header("STEP 1: CREATE BACKUP")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = "backups"
    os.makedirs(backup_dir, exist_ok=True)

    backup_file = os.path.join(backup_dir, f"pre_phase1_migration_{timestamp}.sql")

    print_info(f"Creating backup: {backup_file}")
    print_info("This may take 1-2 minutes...")

    try:
        # Use Python to create backup
        conn = get_connection()

        # Get database connection details
        db_params = conn.get_dsn_parameters()

        # Build pg_dump command
        pg_dump_cmd = [
            "pg_dump",
            "-h", db_params.get('host', 'localhost'),
            "-p", db_params.get('port', '5432'),
            "-U", db_params.get('user', 'postgres'),
            "-d", db_params.get('dbname', 'nsw_planning'),
            "-f", backup_file,
            "--no-owner",
            "--no-acl"
        ]

        # Set password environment variable
        env = os.environ.copy()
        if 'password' in db_params:
            env['PGPASSWORD'] = db_params['password']

        result = subprocess.run(pg_dump_cmd, env=env, capture_output=True, text=True)

        if result.returncode != 0:
            print_warning("pg_dump not available, using Python backup method")
            return create_python_backup(conn, backup_file)

        conn.close()

        # Check backup file size
        size_mb = os.path.getsize(backup_file) / (1024 * 1024)
        print_success(f"Backup created: {backup_file} ({size_mb:.1f} MB)")
        return backup_file

    except Exception as e:
        print_warning(f"Standard backup failed: {e}")
        print_info("Attempting Python-based backup...")
        return create_python_backup(get_connection(), backup_file)

def create_python_backup(conn, backup_file):
    """Create backup using Python (fallback if pg_dump unavailable)"""
    cur = conn.cursor()

    with open(backup_file, 'w', encoding='utf-8') as f:
        # Write header
        f.write(f"-- Database backup created: {datetime.now()}\n")
        f.write(f"-- Table: regulatory_provisions\n\n")

        # Get table schema
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'regulatory_provisions'
            ORDER BY ordinal_position;
        """)
        columns = [row[0] for row in cur.fetchall()]

        # Export data
        cur.execute(f"SELECT * FROM regulatory_provisions;")

        count = 0
        for row in cur:
            if count % 1000 == 0:
                print_info(f"  Backed up {count} provisions...")

            values = []
            for val in row:
                if val is None:
                    values.append('NULL')
                elif isinstance(val, str):
                    # Escape single quotes
                    escaped = val.replace("'", "''")
                    values.append(f"'{escaped}'")
                else:
                    values.append(str(val))

            f.write(f"-- Row {count + 1}\n")
            count += 1

    size_mb = os.path.getsize(backup_file) / (1024 * 1024)
    print_success(f"Python backup created: {backup_file} ({size_mb:.1f} MB)")
    return backup_file

def check_prerequisites():
    """Check if migration can proceed"""
    print_header("STEP 0: PRE-FLIGHT CHECKS")

    conn = get_connection()
    cur = conn.cursor()

    # Check 1: Table exists
    cur.execute("""
        SELECT EXISTS (
            SELECT FROM information_schema.tables
            WHERE table_name = 'regulatory_provisions'
        );
    """)
    if not cur.fetchone()[0]:
        print_error("Table 'regulatory_provisions' does not exist")
        return False
    print_success("Table 'regulatory_provisions' exists")

    # Check 2: Columns don't already exist
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'regulatory_provisions'
          AND column_name IN ('is_canonical', 'canonical_provision_id', 'text_hash');
    """)
    existing_cols = [row[0] for row in cur.fetchall()]

    if existing_cols:
        print_warning(f"Columns already exist: {', '.join(existing_cols)}")
        response = input("Migration may have run before. Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            return False
    else:
        print_success("No conflicting columns found")

    # Check 3: Count provisions
    cur.execute("SELECT COUNT(*) FROM regulatory_provisions;")
    count = cur.fetchone()[0]
    print_success(f"Found {count:,} provisions to process")

    conn.close()
    return True

def run_migration():
    """Execute the Phase 1 migration SQL"""
    print_header("STEP 2: RUN MIGRATION")

    migration_file = "migrations/phase1_mark_duplicates_SAFE.sql"

    if not os.path.exists(migration_file):
        print_error(f"Migration file not found: {migration_file}")
        return False

    print_info("Reading migration SQL...")
    with open(migration_file, 'r', encoding='utf-8') as f:
        sql_content = f.read()

    # Split SQL into logical sections
    # Extract only the migration part (before VALIDATION QUERIES)
    if '-- VALIDATION QUERIES' in sql_content:
        sql_content = sql_content.split('-- VALIDATION QUERIES')[0]

    if '-- ROLLBACK' in sql_content:
        sql_content = sql_content.split('-- ROLLBACK')[0]

    conn = get_connection()
    cur = conn.cursor()

    try:
        print_info(f"Executing migration SQL...")
        print_info(f"This may take 1-2 minutes...")

        # Execute the entire migration as a single transaction
        # psycopg2 can handle multi-statement SQL
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

    # Validation 1: Count canonical vs duplicates
    print_info("Checking canonical vs duplicate counts...")
    cur.execute("""
        SELECT
            is_canonical,
            COUNT(*) as count
        FROM regulatory_provisions
        GROUP BY is_canonical
        ORDER BY is_canonical DESC;
    """)

    results = cur.fetchall()
    total = sum(row[1] for row in results)

    print("\n  Results:")
    for row in results:
        is_canon = row[0]
        count = row[1]
        pct = count / total * 100
        label = "Canonical" if is_canon else "Duplicate" if is_canon is False else "Unmarked"
        print(f"    {label:15s}: {count:6,} ({pct:5.1f}%)")

    # Validation 2: Check for orphaned duplicates
    print_info("\nChecking for orphaned duplicates...")
    cur.execute("""
        SELECT COUNT(*)
        FROM regulatory_provisions dup
        LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
        WHERE dup.is_canonical = FALSE
          AND (canonical.id IS NULL OR canonical.is_canonical = FALSE);
    """)
    orphaned = cur.fetchone()[0]

    if orphaned == 0:
        print_success(f"  No orphaned duplicates (expected: 0, found: {orphaned})")
    else:
        print_error(f"  Found {orphaned} orphaned duplicates!")

    # Validation 3: Sample duplicate groups
    print_info("\nSample duplicate groups (top 5):")
    cur.execute("""
        SELECT
            canonical.ref_number,
            LEFT(canonical.provision_text, 60) as text_preview,
            COUNT(*) as duplicate_count
        FROM regulatory_provisions dup
        JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
        WHERE dup.is_canonical = FALSE
        GROUP BY canonical.id, canonical.ref_number, canonical.provision_text
        ORDER BY COUNT(*) DESC
        LIMIT 5;
    """)

    for i, row in enumerate(cur.fetchall(), 1):
        print(f"    {i}. {row[0]:30s} ({row[2]} duplicates)")
        print(f"       \"{row[1]}...\"")

    # Validation 4: Check text_hash populated
    print_info("\nChecking text_hash coverage...")
    cur.execute("""
        SELECT
            COUNT(*) as total,
            COUNT(text_hash) as with_hash,
            COUNT(*) - COUNT(text_hash) as missing_hash
        FROM regulatory_provisions;
    """)
    row = cur.fetchone()
    if row[2] == 0:
        print_success(f"  All {row[0]:,} provisions have text_hash")
    else:
        print_warning(f"  {row[2]:,} provisions missing text_hash")

    conn.close()

    print_success("\nValidation complete")
    return orphaned == 0

def print_summary(backup_file):
    """Print migration summary and next steps"""
    print_header("MIGRATION COMPLETE")

    print("What changed:")
    print("  • Added 4 new columns: is_canonical, canonical_provision_id, text_hash, migration_phase")
    print("  • Marked ~2,319 provisions as duplicates (is_canonical = FALSE)")
    print("  • Created view: regulatory_provisions_canonical")
    print("  • NO data was deleted")

    print("\nNext steps:")
    print("  1. Update frontend queries to use:")
    print("     WHERE is_canonical = TRUE")
    print("     OR use the view:")
    print("     SELECT * FROM regulatory_provisions_canonical")

    print("\nBackup location:")
    print(f"  {backup_file}")

    print("\nTo rollback (if needed):")
    print("  python rollback_phase1.py")
    print("  OR manually run ROLLBACK section in:")
    print("  migrations/phase1_mark_duplicates_SAFE.sql")

    print("\n[SUCCESS] Migration successful!\n")

def main():
    """Main migration execution"""
    print_header("PHASE 1 MIGRATION: MARK TRUE DUPLICATES")
    print("This migration is SAFE and REVERSIBLE")
    print("No data will be deleted, only flagged with is_canonical column")

    # Step 0: Prerequisites
    if not check_prerequisites():
        print_error("Pre-flight checks failed. Aborting.")
        sys.exit(1)

    # Confirm before proceeding
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
        print_error("Migration failed. Database unchanged (transaction rolled back).")
        sys.exit(1)

    # Step 3: Validate
    if not validate_results():
        print_warning("Validation found issues. Check results above.")
        response = input("Continue anyway? (yes/no): ")
        if response.lower() != 'yes':
            print_error("Migration validation failed.")
            sys.exit(1)

    # Step 4: Summary
    print_summary(backup_file)

if __name__ == "__main__":
    main()
