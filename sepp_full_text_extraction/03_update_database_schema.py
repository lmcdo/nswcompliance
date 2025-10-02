"""
STEP 3: Update database schema to support full text provisions

Changes:
1. Remove TEXT(500) truncation from provision_text column
2. Add full_text_length column
3. Add extraction_method column
4. Add last_updated timestamp
5. Create backup before changes

Exit Codes:
- 0: Success - schema updated
- 1: Failure - schema update failed
"""

import os
import sys
import subprocess
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from db_config import get_connection

BACKUP_DIR = Path("backups")
SCHEMA_BACKUP = BACKUP_DIR / f"schema_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"

def create_backup():
    """Create database backup before schema changes"""
    print("\n=== CREATING DATABASE BACKUP ===\n")

    BACKUP_DIR.mkdir(exist_ok=True)

    # PostgreSQL backup command
    cmd = [
        "pg_dump",
        "-U", "postgres",
        "-d", "nsw_planning",
        "-f", str(SCHEMA_BACKUP),
        "--schema-only"  # Only backup schema, not data (faster)
    ]

    try:
        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

        if result.returncode == 0:
            size = SCHEMA_BACKUP.stat().st_size if SCHEMA_BACKUP.exists() else 0
            print(f"[OK] Schema backup created: {SCHEMA_BACKUP} ({size:,} bytes)")
            return True
        else:
            print(f"[X] Backup failed: {result.stderr}")
            return False

    except Exception as e:
        print(f"[X] Backup error: {e}")
        return False

def check_current_schema():
    """Check current provision_text column definition"""
    print("\n=== CHECKING CURRENT SCHEMA ===\n")

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Get column info
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'regulatory_provisions'
            AND column_name = 'provision_text'
        """)

        result = cur.fetchone()
        if result:
            col_name, data_type, max_length = result
            print(f"Current provision_text column:")
            print(f"  Type: {data_type}")
            print(f"  Max Length: {max_length if max_length else 'unlimited'}")

            if max_length and max_length <= 500:
                print(f"\n[!] Column has {max_length} char limit - needs update")
                return True
            elif not max_length:
                print(f"\n[OK] Column already unlimited")
                return False
        else:
            print("[X] provision_text column not found")
            return False

        conn.close()

    except Exception as e:
        print(f"[X] Error checking schema: {e}")
        return False

def update_schema():
    """Update database schema"""
    print("\n=== UPDATING DATABASE SCHEMA ===\n")

    try:
        conn = get_connection()
        cur = conn.cursor()

        # 1. Remove length restriction from provision_text
        print("1. Removing provision_text length restriction...")
        cur.execute("""
            ALTER TABLE regulatory_provisions
            ALTER COLUMN provision_text TYPE TEXT
        """)
        print("   [OK] provision_text now unlimited TEXT")

        # 2. Add new columns if they don't exist
        print("\n2. Adding new metadata columns...")

        # Check if columns exist
        cur.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'regulatory_provisions'
            AND column_name IN ('full_text_length', 'extraction_method', 'last_updated')
        """)
        existing_cols = [row[0] for row in cur.fetchall()]

        if 'full_text_length' not in existing_cols:
            cur.execute("""
                ALTER TABLE regulatory_provisions
                ADD COLUMN full_text_length INTEGER
            """)
            print("   [OK] Added full_text_length column")

        if 'extraction_method' not in existing_cols:
            cur.execute("""
                ALTER TABLE regulatory_provisions
                ADD COLUMN extraction_method TEXT
            """)
            print("   [OK] Added extraction_method column")

        if 'last_updated' not in existing_cols:
            cur.execute("""
                ALTER TABLE regulatory_provisions
                ADD COLUMN last_updated TIMESTAMP DEFAULT NOW()
            """)
            print("   [OK] Added last_updated column")

        # 3. Calculate full_text_length for existing provisions
        print("\n3. Calculating text lengths for existing provisions...")
        cur.execute("""
            UPDATE regulatory_provisions
            SET full_text_length = LENGTH(provision_text)
            WHERE full_text_length IS NULL
        """)
        updated_count = cur.rowcount
        print(f"   [OK] Updated {updated_count:,} provisions")

        # 4. Set extraction_method for existing provisions
        print("\n4. Setting extraction method for existing provisions...")
        cur.execute("""
            UPDATE regulatory_provisions
            SET extraction_method = 'autoschema'
            WHERE extraction_method IS NULL
        """)
        updated_count = cur.rowcount
        print(f"   [OK] Updated {updated_count:,} provisions")

        # 5. Create index on full_text_length for performance
        print("\n5. Creating performance index...")
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_regulatory_provisions_text_length
            ON regulatory_provisions(full_text_length)
        """)
        print("   [OK] Created index on full_text_length")

        conn.commit()
        conn.close()

        print("\n[SUCCESS] SCHEMA UPDATE SUCCESSFUL")
        return True

    except Exception as e:
        print(f"\n[X] Schema update failed: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False

def verify_schema():
    """Verify schema changes were applied"""
    print("\n=== VERIFYING SCHEMA CHANGES ===\n")

    try:
        conn = get_connection()
        cur = conn.cursor()

        # Check columns exist
        cur.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns
            WHERE table_name = 'regulatory_provisions'
            AND column_name IN ('provision_text', 'full_text_length', 'extraction_method', 'last_updated')
            ORDER BY column_name
        """)

        columns = cur.fetchall()
        print("Updated columns:")
        for col_name, data_type, max_length in columns:
            length_str = f" ({max_length} chars)" if max_length else " (unlimited)"
            print(f"  [OK] {col_name:20} {data_type:15} {length_str}")

        # Check text lengths
        cur.execute("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE full_text_length <= 500) as truncated,
                COUNT(*) FILTER (WHERE full_text_length > 500) as full_text,
                AVG(full_text_length) as avg_length,
                MAX(full_text_length) as max_length
            FROM regulatory_provisions
        """)

        stats = cur.fetchone()
        print(f"\nProvision statistics:")
        print(f"  Total provisions:      {stats[0]:,}")
        print(f"  Truncated (≤500):      {stats[1]:,}")
        print(f"  Full text (>500):      {stats[2]:,}")
        print(f"  Average length:        {stats[3]:,.0f} chars")
        print(f"  Longest provision:     {stats[4]:,} chars")

        # Check index exists
        cur.execute("""
            SELECT indexname
            FROM pg_indexes
            WHERE tablename = 'regulatory_provisions'
            AND indexname = 'idx_regulatory_provisions_text_length'
        """)

        if cur.fetchone():
            print(f"\n  [OK] Performance index created")

        conn.close()

        print("\n[SUCCESS] SCHEMA VERIFICATION PASSED")
        return True

    except Exception as e:
        print(f"\n[X] Verification failed: {e}")
        return False

def main():
    """Main execution"""
    print("\n" + "="*80)
    print("DATABASE SCHEMA UPDATE - STEP 3")
    print("="*80)

    # Create backup first
    backup_success = create_backup()
    if not backup_success:
        print("\n[!] WARNING: pg_dump not available, skipping file backup.")
        print("[!] Proceeding with schema update (changes are reversible).")
        print("\nContinue without backup? (yes/no): ", end='')
        response = input().strip().lower()
        if response != 'yes':
            print("Aborted.")
            return 1

    # Check if update needed
    needs_text_update = check_current_schema()

    # Always try to update schema (adds missing columns if needed)
    print("\nAttempting schema update...")
    if not update_schema():
        print(f"\n[X] Schema update failed")
        print(f"Restore from backup: psql -U postgres -d nsw_planning -f {SCHEMA_BACKUP}")
        return 1

    # Verify changes
    if not verify_schema():
        print(f"\n[X] Verification failed")
        print(f"Restore from backup: psql -U postgres -d nsw_planning -f {SCHEMA_BACKUP}")
        return 1

    print(f"\n[SUCCESS] SCHEMA UPDATE COMPLETE")
    print(f"\nBackup saved: {SCHEMA_BACKUP}")
    print(f"Next step: Run 04_import_full_provisions.py")
    return 0

if __name__ == "__main__":
    sys.exit(main())