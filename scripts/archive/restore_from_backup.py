#!/usr/bin/env python3
"""
Restore regulatory_provisions from backup file
"""

import json
import psycopg2
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from psycopg2.extras import execute_batch

load_dotenv()

def restore_from_backup(backup_file: str, batch_size: int = 1000):
    """Restore provisions from JSON backup"""

    print("=" * 70)
    print("RESTORE REGULATORY_PROVISIONS FROM BACKUP")
    print("=" * 70)

    backup_path = Path(backup_file)
    if not backup_path.exists():
        print(f"[FAIL] Backup file not found: {backup_file}")
        sys.exit(1)

    print(f"\nLoading backup: {backup_path.name}")
    print(f"File size: {backup_path.stat().st_size / (1024*1024):.2f} MB")

    # Load backup
    with open(backup_path, 'r', encoding='utf-8') as f:
        backup = json.load(f)

    # Handle both formats: list or dict with metadata
    if isinstance(backup, list):
        data = backup
        print(f"Backup format: List (simple)")
        print(f"Row count in backup: {len(data)}")
    else:
        print(f"Backup timestamp: {backup.get('timestamp', 'unknown')}")
        print(f"Backup purpose: {backup.get('purpose', 'unknown')}")
        print(f"Row count in backup: {backup.get('row_count', len(backup.get('data', [])))}")
        data = backup.get('data', [])

    if not data:
        print("[FAIL] No data found in backup")
        sys.exit(1)

    print(f"\n[OK] Loaded {len(data)} provisions from backup")

    # Connect to database
    conn = psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=30)
    conn.autocommit = False
    cur = conn.cursor()

    # Set long timeout
    cur.execute("SET statement_timeout = '600s'")

    try:
        # Check current state
        cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
        current_count = cur.fetchone()[0]
        print(f"\nCurrent table count: {current_count}")

        if current_count > 0:
            response = input(f"\n[WARN] Table already has {current_count} rows. Truncate? (yes/no): ")
            if response.lower() != 'yes':
                print("Restore cancelled")
                sys.exit(0)

            print("Truncating regulatory_provisions...")
            cur.execute("TRUNCATE TABLE regulatory_provisions CASCADE")
            conn.commit()
            print("[OK] Table truncated")

        # Get column names from first record
        columns = list(data[0].keys())
        print(f"\nColumns to restore: {len(columns)}")

        # Build insert query
        column_list = ', '.join(columns)
        placeholders = ', '.join([f'%({col})s' for col in columns])
        insert_query = f"""
            INSERT INTO regulatory_provisions ({column_list})
            VALUES ({placeholders})
        """

        # Convert dict types to JSON strings (but keep arrays as lists for psycopg2)
        print("\nPreparing data...")
        for record in data:
            for key, value in record.items():
                if isinstance(value, dict):
                    record[key] = json.dumps(value)

        # Insert in batches
        print(f"\nInserting {len(data)} provisions in batches of {batch_size}...")
        total = len(data)
        inserted = 0

        for i in range(0, total, batch_size):
            batch = data[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (total + batch_size - 1) // batch_size

            print(f"  Batch {batch_num}/{total_batches} ({len(batch)} records)...", end='')

            execute_batch(cur, insert_query, batch, page_size=batch_size)
            conn.commit()
            inserted += len(batch)

            print(f" [OK] ({inserted}/{total})")

        print(f"\n[OK] Inserted {inserted} provisions")

        # Verify
        print("\nVerifying restore...")
        cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
        final_count = cur.fetchone()[0]
        print(f"  Final count: {final_count}")

        if final_count == len(data):
            print("[OK] Restore successful!")
        else:
            print(f"[WARN] Expected {len(data)}, got {final_count}")

        # Show sample
        cur.execute("""
            SELECT id, document_id, ref_number, LEFT(provision_text, 50)
            FROM regulatory_provisions
            ORDER BY id
            LIMIT 5
        """)
        samples = cur.fetchall()
        print("\nSample restored provisions:")
        for sample in samples:
            print(f"  ID={sample[0]}, doc={sample[1]}, ref={sample[2]}, text={sample[3]}...")

        print("\n" + "=" * 70)
        print("[OK] RESTORE COMPLETED")
        print("=" * 70)

    except Exception as e:
        print(f"\n[FAIL] Restore failed: {e}")
        conn.rollback()
        raise
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Restore regulatory_provisions from backup')
    parser.add_argument('backup_file', nargs='?',
                       default='backups/regulatory_provisions_before_v2_20251122_231205.json',
                       help='Path to backup JSON file')
    parser.add_argument('--batch-size', type=int, default=1000,
                       help='Batch size for inserts')

    args = parser.parse_args()
    restore_from_backup(args.backup_file, args.batch_size)
