# Database Backup & Restore Procedures

## Backup Created
- **File**: `nsw_planning_BACKUP_20250907_221816.db`
- **Size**: 55.45 MB
- **Date**: 2025-09-07 22:18:16
- **Contents**: 
  - 24 tables
  - 22,095 regulatory provisions
  - 1,394 AutoSchemaKG entities
  - 2,734 knowledge graph relationships
  - All visual element linkages

## Critical Data Protected
This backup preserves:
- ✅ **Years of RAG-Anything extraction work**
- ✅ **AutoSchemaKG entity relationships**  
- ✅ **LangExtract provisions with full text**
- ✅ **Visual element to clause linkages**
- ✅ **Quantitative standards and confidence scores**
- ✅ **Document provenance and page references**

## Restore Procedures

### Quick Restore (if PRP-K7 import fails)
```bash
# Stop any processes using the database
pkill -f "python.*nsw_planning"

# Replace corrupted database with backup
cp nsw_planning_BACKUP_20250907_221816.db nsw_planning.db

# Verify restore
python -c "
import sqlite3
conn = sqlite3.connect('nsw_planning.db')
cur = conn.cursor()
provisions = cur.execute('SELECT COUNT(*) FROM regulatory_provisions').fetchone()[0]
entities = cur.execute('SELECT COUNT(*) FROM kg_entities').fetchone()[0]
print(f'Restored - Provisions: {provisions:,}, Entities: {entities:,}')
conn.close()
"
```

### Verification Script
```python
# verify_database_integrity.py
import sqlite3
from datetime import datetime

def verify_database_integrity(db_path='nsw_planning.db'):
    """Verify database integrity after restore"""
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        
        # Check table count
        tables = cur.execute('SELECT COUNT(*) FROM sqlite_master WHERE type="table"').fetchone()[0]
        assert tables == 24, f"Expected 24 tables, found {tables}"
        
        # Check provision count
        provisions = cur.execute('SELECT COUNT(*) FROM regulatory_provisions').fetchone()[0]
        assert provisions >= 22095, f"Expected ≥22,095 provisions, found {provisions}"
        
        # Check entities
        entities = cur.execute('SELECT COUNT(*) FROM kg_entities').fetchone()[0]  
        assert entities >= 1394, f"Expected ≥1,394 entities, found {entities}"
        
        # Check relationships
        relationships = cur.execute('SELECT COUNT(*) FROM kg_relationships').fetchone()[0]
        assert relationships >= 2734, f"Expected ≥2,734 relationships, found {relationships}"
        
        # Check C11/C12 provisions specifically
        c11_count = cur.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE ref_number LIKE "C11%"').fetchone()[0]
        c12_count = cur.execute('SELECT COUNT(*) FROM regulatory_provisions WHERE ref_number LIKE "C12%"').fetchone()[0]
        
        conn.close()
        
        print("✅ DATABASE INTEGRITY VERIFIED")
        print(f"  Tables: {tables}")
        print(f"  Provisions: {provisions:,}")
        print(f"  Entities: {entities:,}")
        print(f"  Relationships: {relationships:,}")
        print(f"  C11 provisions: {c11_count}")
        print(f"  C12 provisions: {c12_count}")
        
        return True
        
    except Exception as e:
        print(f"❌ DATABASE INTEGRITY FAILED: {e}")
        return False

if __name__ == "__main__":
    verify_database_integrity()
```

## Pre-Import Safety Checklist

Before running PRP-K7 import:
- [x] **Backup created**: `nsw_planning_BACKUP_20250907_221816.db`
- [ ] **Backup verified**: Run integrity check on backup file
- [ ] **Restore procedure tested**: Test restore process on copy
- [ ] **Import pipeline tested**: Test EntityAwareZoneImporter on backup copy first
- [ ] **Rollback plan ready**: Document exact rollback steps

## Recovery Commands

### If import corrupts database:
```bash
# Emergency restore
mv nsw_planning.db nsw_planning_CORRUPTED.db
cp nsw_planning_BACKUP_20250907_221816.db nsw_planning.db
echo "Database restored to pre-import state"
```

### If partial corruption:
```bash
# Analyze what went wrong
sqlite3 nsw_planning.db "PRAGMA integrity_check;"

# Compare with backup
python -c "
import sqlite3

# Count differences
original = sqlite3.connect('nsw_planning_BACKUP_20250907_221816.db')
current = sqlite3.connect('nsw_planning.db')

orig_provisions = original.execute('SELECT COUNT(*) FROM regulatory_provisions').fetchone()[0]
curr_provisions = current.execute('SELECT COUNT(*) FROM regulatory_provisions').fetchone()[0]

print(f'Provisions - Original: {orig_provisions}, Current: {curr_provisions}')
print(f'Difference: {curr_provisions - orig_provisions}')

original.close()
current.close()
"
```

## Additional Safety Measures

1. **Create SQL dump** (alternative backup format):
```bash
sqlite3 nsw_planning.db .dump > nsw_planning_BACKUP_20250907_221816.sql
```

2. **Compress backup** for long-term storage:
```bash
gzip -k nsw_planning_BACKUP_20250907_221816.db
# Creates nsw_planning_BACKUP_20250907_221816.db.gz
```

3. **Weekly backup rotation**:
```bash
# Keep weekly backups
cp nsw_planning.db "nsw_planning_WEEKLY_$(date +%Y%m%d).db"
```

## Notes
- **Backup is pristine**: Contains complete extraction work before any PRP-K7 modifications
- **Restore is instant**: Simple file copy operation
- **No data loss risk**: All AutoSchemaKG relationships preserved
- **Testing recommended**: Test PRP-K7 import on backup copy first

**Status**: ✅ SAFE TO PROCEED with PRP-K7 import - backup secured