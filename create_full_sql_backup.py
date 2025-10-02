"""
Create full SQL database backup
Uses db_safety_wrapper as required by CLAUDE.md
"""
from db_safety_wrapper import get_safe_connection
from pathlib import Path
from datetime import datetime
import subprocess
import json

backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
sql_backup_file = backup_dir / f"nsw_planning_full_backup_{timestamp}.sql"
metadata_file = backup_dir / f"nsw_planning_backup_metadata_{timestamp}.json"

print("\n" + "="*80)
print("FULL DATABASE BACKUP (SQL + Metadata)")
print("="*80 + "\n")

# Get database statistics before backup
print("1. Collecting database statistics...")
conn = get_safe_connection()
cur = conn.cursor()

# Get table counts
cur.execute("""
    SELECT
        (SELECT COUNT(*) FROM regulatory_provisions) as provisions,
        (SELECT COUNT(*) FROM documents) as documents,
        (SELECT COUNT(*) FROM development_permissions) as permissions,
        (SELECT COUNT(*) FROM sepp_lep_overrides) as overrides
""")
row = cur.fetchone()
stats = {
    'regulatory_provisions': row[0],
    'documents': row[1] if row[1] else 0,
    'development_permissions': row[2] if row[2] else 0,
    'sepp_lep_overrides': row[3] if row[3] else 0
}
print(f"   Provisions: {stats['regulatory_provisions']:,}")
print(f"   Documents: {stats['documents']:,}")
print(f"   Permissions: {stats['development_permissions']:,}")
print(f"   Overrides: {stats['sepp_lep_overrides']:,}")

# Get extraction method breakdown
cur.execute("""
    SELECT
        extraction_method,
        COUNT(*) as count,
        AVG(LENGTH(provision_text))::int as avg_len
    FROM regulatory_provisions
    GROUP BY extraction_method
    ORDER BY count DESC
""")
extraction_stats = []
for row in cur.fetchall():
    extraction_stats.append({
        'method': row[0] or 'NULL',
        'count': row[1],
        'avg_length': row[2]
    })
    print(f"   {row[0] or 'NULL':15} {row[1]:>8,} provisions (avg {row[2]:>5,} chars)")

conn.close()

# Create SQL backup using pg_dump
print(f"\n2. Creating SQL backup...")
print(f"   Backup file: {sql_backup_file}")

try:
    # Try to find pg_dump
    pg_dump_cmd = "pg_dump"

    # Run pg_dump
    cmd = [
        pg_dump_cmd,
        "-h", "127.0.0.1",
        "-p", "5432",
        "-U", "postgres",
        "-d", "nsw_planning",
        "-f", str(sql_backup_file),
        "--verbose"
    ]

    print(f"   Running: {' '.join(cmd[:8])}...")
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300  # 5 minutes max
    )

    if result.returncode == 0:
        backup_size = sql_backup_file.stat().st_size
        print(f"   [OK] SQL backup created: {backup_size:,} bytes ({backup_size/1024/1024:.1f} MB)")
    else:
        print(f"   [WARN] pg_dump returned code {result.returncode}")
        if result.stderr:
            print(f"   Error: {result.stderr[:200]}")

except FileNotFoundError:
    print(f"   [WARN] pg_dump not found in PATH")
    print(f"   [INFO] JSON metadata backup will still be created")
    sql_backup_file = None
except subprocess.TimeoutExpired:
    print(f"   [ERROR] pg_dump timed out after 5 minutes")
    sql_backup_file = None
except Exception as e:
    print(f"   [ERROR] Failed to create SQL backup: {e}")
    sql_backup_file = None

# Create metadata backup
print(f"\n3. Creating metadata backup...")
metadata = {
    'backup_timestamp': datetime.now().isoformat(),
    'backup_type': 'full_database',
    'sql_backup_file': str(sql_backup_file) if sql_backup_file else None,
    'sql_backup_size_bytes': sql_backup_file.stat().st_size if sql_backup_file and sql_backup_file.exists() else 0,
    'database': 'nsw_planning',
    'statistics': stats,
    'extraction_methods': extraction_stats,
    'purpose': 'Complete database backup before SEPP extraction operations'
}

with open(metadata_file, 'w') as f:
    json.dump(metadata, f, indent=2)

print(f"   [OK] Metadata saved: {metadata_file}")

# Summary
print(f"\n{'='*80}")
print("BACKUP COMPLETE")
print(f"{'='*80}")
if sql_backup_file and sql_backup_file.exists():
    print(f"SQL Backup:    {sql_backup_file}")
    print(f"Size:          {sql_backup_file.stat().st_size/1024/1024:.1f} MB")
print(f"Metadata:      {metadata_file}")
print(f"Total rows:    {stats['regulatory_provisions']:,} provisions")
print(f"\nBackup Status: {'✅ COMPLETE' if sql_backup_file else '⚠️ METADATA ONLY (pg_dump unavailable)'}")
print(f"{'='*80}\n")