"""
Create database backup before Step 4
Uses db_safety_wrapper as required by CLAUDE.md
"""
from db_safety_wrapper import get_safe_connection
from pathlib import Path
from datetime import datetime
import json

backup_dir = Path("backups")
backup_dir.mkdir(exist_ok=True)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_file = backup_dir / f"pre_step4_schema_backup_{timestamp}.json"

print("=== CREATING DATABASE BACKUP (Required by CLAUDE.md) ===\n")

# Use safe connection as mandated
conn = get_safe_connection()
cur = conn.cursor()

# Backup schema information
print("1. Backing up schema information...")
cur.execute("""
    SELECT table_name, column_name, data_type, character_maximum_length
    FROM information_schema.columns
    WHERE table_schema = 'public'
    AND table_name = 'regulatory_provisions'
    ORDER BY ordinal_position
""")
schema_info = [
    {
        'table': row[0],
        'column': row[1],
        'type': row[2],
        'max_length': row[3]
    }
    for row in cur.fetchall()
]
print(f"   Backed up {len(schema_info)} column definitions")

# Backup current state statistics
print("\n2. Backing up current state statistics...")
cur.execute("""
    SELECT
        COUNT(*) as total,
        COUNT(*) FILTER (WHERE extraction_method = 'autoschema') as autoschema_count,
        COUNT(*) FILTER (WHERE extraction_method = 'pymupdf') as pymupdf_count,
        AVG(full_text_length) as avg_length,
        MIN(full_text_length) as min_length,
        MAX(full_text_length) as max_length
    FROM regulatory_provisions
""")
stats = cur.fetchone()
state_stats = {
    'total_provisions': stats[0],
    'autoschema_count': stats[1],
    'pymupdf_count': stats[2],
    'avg_length': float(stats[3]) if stats[3] else 0,
    'min_length': stats[4],
    'max_length': stats[5]
}
print(f"   Total provisions: {stats[0]:,}")
print(f"   Average length: {stats[3]:.1f} chars")

# Backup sample provision IDs and their current state
print("\n3. Backing up sample provisions (for verification)...")
cur.execute("""
    SELECT id, ref_number, full_text_length, extraction_method,
           LEFT(provision_text, 200) as text_preview
    FROM regulatory_provisions
    WHERE id IN (18945, 19101, 19195, 6079, 6172, 6169, 6107)
""")
sample_provisions = [
    {
        'id': row[0],
        'ref_number': row[1],
        'full_text_length': row[2],
        'extraction_method': row[3],
        'text_preview': row[4]
    }
    for row in cur.fetchall()
]
print(f"   Backed up {len(sample_provisions)} sample provisions")

conn.close()

# Save backup
backup_data = {
    'backup_timestamp': datetime.now().isoformat(),
    'backup_purpose': 'Pre-Step4 safety backup (SEPP full text import)',
    'schema': schema_info,
    'statistics': state_stats,
    'sample_provisions': sample_provisions
}

with open(backup_file, 'w') as f:
    json.dump(backup_data, f, indent=2)

print(f"\n[OK] Backup created: {backup_file}")
print(f"Backup size: {backup_file.stat().st_size:,} bytes")

# Verify backup
print("\n4. Verifying backup...")
with open(backup_file, 'r') as f:
    verify = json.load(f)
    assert len(verify['schema']) == len(schema_info)
    assert verify['statistics']['total_provisions'] == state_stats['total_provisions']
    print("[OK] Backup verified")

print("\n=== BACKUP COMPLETE ===")
print(f"Database state preserved at: {backup_file}")
print("You can now proceed with Step 4")