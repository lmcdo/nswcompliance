# PRP-F1: Foreign Key Constraint Resolution

## Objective
Fix V5 foreign key constraint errors in provision_changes table that prevent change tracking functionality.

## Root Cause Analysis
Error: `insert or update on table "provision_changes" violates foreign key constraint "provision_changes_document_version_id_fkey"`
- provision_changes table references document_versions.id
- Some test data being inserted references non-existent version IDs
- Need to ensure all referenced version IDs exist before insertion

## Technical Implementation

### Phase 1: Constraint Analysis
```sql
-- Check existing foreign key constraints
SELECT
    tc.constraint_name,
    tc.table_name,
    kcu.column_name,
    ccu.table_name AS referenced_table,
    ccu.column_name AS referenced_column
FROM information_schema.table_constraints tc
JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name
JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name
WHERE tc.constraint_type = 'FOREIGN KEY'
AND tc.table_name = 'provision_changes';
```

### Phase 2: Data Validation
```sql
-- Check for orphaned references
SELECT DISTINCT pc.document_version_id
FROM versions.provision_changes pc
LEFT JOIN versions.document_versions dv ON pc.document_version_id = dv.id
WHERE dv.id IS NULL;
```

### Phase 3: Constraint Repair
```sql
-- Remove invalid records
DELETE FROM versions.provision_changes
WHERE document_version_id NOT IN (
    SELECT id FROM versions.document_versions
);

-- Add validation function
CREATE OR REPLACE FUNCTION validate_version_reference(version_id INTEGER)
RETURNS BOOLEAN AS $$
BEGIN
    RETURN EXISTS (SELECT 1 FROM versions.document_versions WHERE id = version_id);
END;
$$ LANGUAGE plpgsql;
```

## Success Criteria
- All foreign key constraints validated
- No orphaned provision_changes records
- Change tracking inserts succeed
- V5 verification passes

## Verification Commands
```bash
python verify_f1_foreign_key_fix.py
```

## Dependencies
- PostgreSQL database running
- versions.document_versions table populated
- versions.provision_changes table exists