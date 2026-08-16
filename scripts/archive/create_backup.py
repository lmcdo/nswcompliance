#!/usr/bin/env python3
"""
Create database backup before migration
Backs up the regulatory_provisions table structure and metadata
"""

import psycopg2
import os
import json
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

def create_backup():
    """Create backup of current database state"""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = Path("backups")
    backup_dir.mkdir(exist_ok=True)

    backup_file = backup_dir / f"pre_version_migration_{timestamp}.json"

    print(f"Creating backup: {backup_file}")

    conn = psycopg2.connect(os.environ['DATABASE_URL'], connect_timeout=30)
    cur = conn.cursor()

    backup_data = {
        "timestamp": timestamp,
        "migration": "provision_versioning",
        "database_state": {}
    }

    try:
        # Get table count
        print("1. Backing up table counts...")
        cur.execute("SELECT COUNT(*) FROM regulatory_provisions")
        provision_count = cur.fetchone()[0]
        backup_data["database_state"]["provision_count"] = provision_count
        print(f"   - regulatory_provisions: {provision_count} rows")

        # Get column names
        print("2. Backing up schema...")
        cur.execute("""
            SELECT column_name, data_type
            FROM information_schema.columns
            WHERE table_name = 'regulatory_provisions'
            ORDER BY ordinal_position
        """)
        columns = cur.fetchall()
        backup_data["database_state"]["regulatory_provisions_columns"] = [
            {"name": col[0], "type": col[1]} for col in columns
        ]
        print(f"   - {len(columns)} columns in regulatory_provisions")

        # Get sample of provision IDs (for validation later)
        print("3. Backing up sample provision IDs...")
        cur.execute("""
            SELECT id, ref_number, provision_text, last_updated
            FROM regulatory_provisions
            ORDER BY id
            LIMIT 100
        """)
        samples = cur.fetchall()
        backup_data["sample_provisions"] = [
            {
                "id": row[0],
                "ref_number": row[1],
                "provision_text": row[2][:100] if row[2] else None,  # First 100 chars
                "last_updated": row[3].isoformat() if row[3] else None
            }
            for row in samples
        ]
        print(f"   - {len(samples)} sample provisions")

        # Get index information
        print("4. Backing up indexes...")
        cur.execute("""
            SELECT indexname, indexdef
            FROM pg_indexes
            WHERE tablename = 'regulatory_provisions'
            ORDER BY indexname
        """)
        indexes = cur.fetchall()
        backup_data["database_state"]["indexes"] = [
            {"name": idx[0], "definition": idx[1]} for idx in indexes
        ]
        print(f"   - {len(indexes)} indexes")

        # Write backup file
        print("5. Writing backup file...")
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, indent=2, default=str)

        print(f"\n[OK] Backup created: {backup_file}")
        print(f"     Size: {backup_file.stat().st_size / 1024:.2f} KB")

        cur.close()
        conn.close()

        return str(backup_file)

    except Exception as e:
        print(f"[FAIL] Backup failed: {e}")
        cur.close()
        conn.close()
        raise

if __name__ == "__main__":
    create_backup()
