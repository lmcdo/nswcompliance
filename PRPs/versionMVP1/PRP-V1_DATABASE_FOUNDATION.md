# PRP-V1: Database Version Foundation

## Objective
Create the foundational database schema for document version tracking with minimal complexity while allowing future expansion.

## Prerequisites
- PostgreSQL 14+ running
- Database connection configured in `db_config.py`
- Backup of current database completed

## Implementation Steps

### Step 1: Create Version Schema
```sql
-- Create version tracking schema
CREATE SCHEMA IF NOT EXISTS versions;

-- Main version registry table
CREATE TABLE versions.document_versions (
    id SERIAL PRIMARY KEY,
    document_type VARCHAR(20) NOT NULL CHECK (document_type IN ('SEPP', 'LEP', 'DCP')),
    document_identifier VARCHAR(255) NOT NULL,
    version_number VARCHAR(20) NOT NULL,
    version_status VARCHAR(20) NOT NULL CHECK (version_status IN ('CURRENT', 'PREVIOUS', 'ARCHIVED')),
    effective_date DATE NOT NULL,
    superseded_date DATE,
    document_url TEXT,
    change_summary TEXT,
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system',
    UNIQUE(document_type, document_identifier, version_status)
);

-- Index for performance
CREATE INDEX idx_version_lookup ON versions.document_versions(document_type, document_identifier, version_status);
CREATE INDEX idx_version_dates ON versions.document_versions(effective_date, superseded_date);
CREATE INDEX idx_version_current ON versions.document_versions(version_status) WHERE version_status = 'CURRENT';
```

### Step 2: Modify Existing Tables
```sql
-- Add version tracking to regulatory_provisions
ALTER TABLE regulatory_provisions
    ADD COLUMN IF NOT EXISTS version_id INTEGER REFERENCES versions.document_versions(id),
    ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT true,
    ADD COLUMN IF NOT EXISTS version_effective_date DATE;

-- Add version tracking to other core tables
ALTER TABLE development_controls
    ADD COLUMN IF NOT EXISTS version_id INTEGER REFERENCES versions.document_versions(id),
    ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT true;

ALTER TABLE quantitative_standards
    ADD COLUMN IF NOT EXISTS version_id INTEGER REFERENCES versions.document_versions(id),
    ADD COLUMN IF NOT EXISTS is_current BOOLEAN DEFAULT true;

-- Create indexes for version queries
CREATE INDEX idx_provisions_version ON regulatory_provisions(version_id, is_current);
CREATE INDEX idx_controls_version ON development_controls(version_id, is_current);
CREATE INDEX idx_standards_version ON quantitative_standards(version_id, is_current);
```

### Step 3: Create Version Audit Table
```sql
-- Audit trail for version changes
CREATE TABLE versions.version_audit_log (
    id SERIAL PRIMARY KEY,
    version_id INTEGER REFERENCES versions.document_versions(id),
    action VARCHAR(50) NOT NULL,
    action_details JSONB,
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    performed_by VARCHAR(100)
);

-- Function to auto-log version changes
CREATE OR REPLACE FUNCTION versions.log_version_change()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'INSERT' THEN
        INSERT INTO versions.version_audit_log(version_id, action, action_details, performed_by)
        VALUES (NEW.id, 'CREATE', row_to_json(NEW), COALESCE(NEW.created_by, 'system'));
    ELSIF TG_OP = 'UPDATE' THEN
        INSERT INTO versions.version_audit_log(version_id, action, action_details, performed_by)
        VALUES (NEW.id, 'UPDATE', jsonb_build_object('old', row_to_json(OLD), 'new', row_to_json(NEW)), 'system');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Attach trigger
CREATE TRIGGER version_audit_trigger
AFTER INSERT OR UPDATE ON versions.document_versions
FOR EACH ROW EXECUTE FUNCTION versions.log_version_change();
```

### Step 4: Create Helper Functions
```sql
-- Get current version for a document
CREATE OR REPLACE FUNCTION versions.get_current_version(
    p_doc_type VARCHAR,
    p_doc_identifier VARCHAR
) RETURNS INTEGER AS $$
DECLARE
    v_version_id INTEGER;
BEGIN
    SELECT id INTO v_version_id
    FROM versions.document_versions
    WHERE document_type = p_doc_type
      AND document_identifier = p_doc_identifier
      AND version_status = 'CURRENT'
    LIMIT 1;

    RETURN v_version_id;
END;
$$ LANGUAGE plpgsql;

-- Get version at specific date
CREATE OR REPLACE FUNCTION versions.get_version_at_date(
    p_doc_type VARCHAR,
    p_doc_identifier VARCHAR,
    p_date DATE
) RETURNS INTEGER AS $$
DECLARE
    v_version_id INTEGER;
BEGIN
    SELECT id INTO v_version_id
    FROM versions.document_versions
    WHERE document_type = p_doc_type
      AND document_identifier = p_doc_identifier
      AND effective_date <= p_date
      AND (superseded_date IS NULL OR superseded_date > p_date)
    ORDER BY effective_date DESC
    LIMIT 1;

    RETURN v_version_id;
END;
$$ LANGUAGE plpgsql;
```

## Verification Checklist

### Database Objects Created
- [ ] Schema `versions` created
- [ ] Table `versions.document_versions` created
- [ ] Table `versions.version_audit_log` created
- [ ] Version columns added to `regulatory_provisions`
- [ ] Version columns added to `development_controls`
- [ ] Version columns added to `quantitative_standards`
- [ ] All indexes created
- [ ] Helper functions created
- [ ] Audit trigger functioning

### Data Integrity
- [ ] No existing data lost
- [ ] Foreign key constraints valid
- [ ] Check constraints enforced
- [ ] Unique constraints working
- [ ] Indexes improving query performance

### Performance Metrics
- [ ] Version lookup query <100ms
- [ ] Current version query <50ms
- [ ] Date-based version query <200ms
- [ ] Audit log inserts <10ms

## Rollback Procedure

If issues occur, run:
```sql
-- Rollback version changes
ALTER TABLE regulatory_provisions
    DROP COLUMN IF EXISTS version_id,
    DROP COLUMN IF EXISTS is_current,
    DROP COLUMN IF EXISTS version_effective_date;

ALTER TABLE development_controls
    DROP COLUMN IF EXISTS version_id,
    DROP COLUMN IF EXISTS is_current;

ALTER TABLE quantitative_standards
    DROP COLUMN IF EXISTS version_id,
    DROP COLUMN IF EXISTS is_current;

DROP SCHEMA versions CASCADE;
```

## Success Criteria

1. ✅ All database objects created without errors
2. ✅ Existing data remains accessible
3. ✅ Version queries return in <200ms
4. ✅ Audit trail captures all changes
5. ✅ No impact on existing API functionality

## Next Steps

After successful completion:
1. Run `verify_v1_database.py` to validate schema
2. Proceed to PRP-V2_VERSION_SERVICE.md
3. Document any deviations in `execution_log.json`