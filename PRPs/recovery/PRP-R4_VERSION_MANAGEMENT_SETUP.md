# PRP-R4: Version Management Schema Setup

## Objective
Create version management infrastructure for regulatory provisions

## Prerequisites
- PRP-R3 completed (data migrated)
- PostgreSQL database with core data
- Version management requirements defined

## Implementation Steps

### Step 1: Create Versions Schema
```sql
CREATE SCHEMA IF NOT EXISTS versions;
```

### Step 2: Create Document Versions Table
```sql
CREATE TABLE versions.document_versions (
    id SERIAL PRIMARY KEY,
    document_type VARCHAR(50),
    document_identifier VARCHAR(500),
    version_number VARCHAR(50),
    version_status VARCHAR(20),
    effective_date DATE,
    document_url TEXT,
    notes TEXT,
    metadata JSONB,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Step 3: Populate Document Versions
- Create baseline versions for all documents
- Link regulatory_provisions to versions
- Set version_id for all provisions

### Step 4: Create Change Tracking
```sql
CREATE TABLE versions.provision_changes (
    id SERIAL PRIMARY KEY,
    provision_id INTEGER,
    document_version_id INTEGER,
    change_type VARCHAR(50),
    previous_value TEXT,
    new_value TEXT,
    change_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Verification
- versions schema exists
- document_versions table populated
- All provisions linked to versions
- Change tracking ready

## Completion Gate
- Version management operational
- All PRPs can run against versioned data
- Marker file: `recovery_checkpoints/R4_complete.marker`