# PRP-V4-Enhanced: Data Migration with Baseline Versioning

## Objective
Bootstrap existing 22,105 provisions with baseline document versions using Snapshot Baseline strategy for legislative compliance.

## Prerequisites
- PRP-V1 completed (database schema exists)
- PRP-V2 completed (version services available)
- Current provisions loaded in database (22,105 records)
- Downloaded consolidated documents from official sources

## Implementation Strategy

### Snapshot Baseline Approach
- Treat current downloaded documents as "v1.0-baseline"
- All existing provisions link to baseline versions
- Track all future changes from this point forward
- Clear metadata about baseline coverage limitations

## Technical Specification

### Phase 1: Document Discovery
```sql
-- Identify unique documents from existing provisions
SELECT
    DISTINCT
    CASE
        WHEN document_id LIKE '%LEP%' THEN 'LEP'
        WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
        WHEN document_id LIKE '%DCP%' THEN 'DCP'
        ELSE 'UNKNOWN'
    END as document_type,
    regexp_replace(document_id, '_.*', '') as document_identifier,
    COUNT(*) as provision_count,
    MIN(created_at) as earliest_provision,
    MAX(created_at) as latest_provision
FROM regulatory_provisions
WHERE document_id IS NOT NULL
GROUP BY document_type, document_identifier
ORDER BY document_type, provision_count DESC;
```

### Phase 2: Baseline Version Creation
```sql
-- Create baseline document versions
INSERT INTO versions.document_versions (
    document_type,
    document_identifier,
    version_number,
    version_status,
    effective_date,
    document_url,
    change_summary,
    metadata,
    created_by
)
SELECT
    doc_analysis.document_type,
    doc_analysis.document_identifier,
    'v1.0-baseline' as version_number,
    'CURRENT' as version_status,
    '2024-09-20' as effective_date, -- Baseline date
    CASE
        WHEN doc_analysis.document_type = 'LEP'
        THEN 'https://legislation.nsw.gov.au/view/html/inforce/current/'
        WHEN doc_analysis.document_type = 'SEPP'
        THEN 'https://legislation.nsw.gov.au/view/html/inforce/current/'
        ELSE NULL
    END as document_url,
    'Baseline version from consolidated download Sept 2024' as change_summary,
    jsonb_build_object(
        'baseline', true,
        'consolidation_date', '2024-09-20',
        'source', 'legislation.nsw.gov.au + council sites',
        'provision_count', doc_analysis.provision_count,
        'coverage_note', 'Tracks changes from 2024-09-20 forward only',
        'historical_coverage', 'none'
    ) as metadata,
    'baseline_migration_script' as created_by
FROM (
    -- Document analysis subquery
    SELECT
        CASE
            WHEN document_id LIKE '%LEP%' THEN 'LEP'
            WHEN document_id LIKE '%SEPP%' THEN 'SEPP'
            WHEN document_id LIKE '%DCP%' THEN 'DCP'
            ELSE 'UNKNOWN'
        END as document_type,
        regexp_replace(document_id, '_.*', '') as document_identifier,
        COUNT(*) as provision_count
    FROM regulatory_provisions
    WHERE document_id IS NOT NULL
    GROUP BY document_type, document_identifier
) doc_analysis
WHERE doc_analysis.document_type != 'UNKNOWN';
```

### Phase 3: Provision Version Linkage
```sql
-- Link provisions to their baseline document versions
UPDATE regulatory_provisions
SET
    version_id = dv.id,
    version_effective_date = dv.effective_date,
    is_current = true
FROM versions.document_versions dv
WHERE regulatory_provisions.document_id LIKE dv.document_identifier || '%'
  AND dv.version_number = 'v1.0-baseline'
  AND dv.version_status = 'CURRENT';
```

### Phase 4: Provision Change Tracking Setup
```sql
-- Create provision changes table for future tracking
CREATE TABLE IF NOT EXISTS versions.provision_changes (
    id SERIAL PRIMARY KEY,
    document_version_id INTEGER REFERENCES versions.document_versions(id),
    provision_id INTEGER REFERENCES regulatory_provisions(id),
    change_type VARCHAR(20) CHECK (change_type IN ('NEW', 'MODIFIED', 'DELETED', 'UNCHANGED')),
    old_content TEXT,
    new_content TEXT,
    change_summary TEXT,
    change_metadata JSONB DEFAULT '{}',
    effective_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100) DEFAULT 'system'
);

-- Create indexes for performance
CREATE INDEX IF NOT EXISTS idx_provision_changes_provision
ON versions.provision_changes(provision_id);

CREATE INDEX IF NOT EXISTS idx_provision_changes_document_version
ON versions.provision_changes(document_version_id);

CREATE INDEX IF NOT EXISTS idx_provision_changes_type_date
ON versions.provision_changes(change_type, effective_date);

-- Record baseline provisions as initial state
INSERT INTO versions.provision_changes (
    document_version_id,
    provision_id,
    change_type,
    new_content,
    change_summary,
    effective_date,
    created_by
)
SELECT
    rp.version_id,
    rp.id,
    'NEW' as change_type,
    rp.provision_text,
    'Baseline provision from consolidated download' as change_summary,
    '2024-09-20' as effective_date,
    'baseline_migration_script' as created_by
FROM regulatory_provisions rp
WHERE rp.version_id IS NOT NULL;
```

## Implementation Steps

### Step 1: Pre-Migration Analysis (30 minutes)
```python
def analyze_current_provisions():
    """Analyze existing provisions for migration planning"""
    # Count provisions by document type
    # Identify document naming patterns
    # Check for data quality issues
    # Generate migration plan
```

### Step 2: Document Version Bootstrap (45 minutes)
```python
def create_baseline_versions():
    """Create baseline document versions"""
    # Discover unique documents
    # Create version records with metadata
    # Validate version creation
    # Log creation results
```

### Step 3: Provision Linkage (45 minutes)
```python
def link_provisions_to_versions():
    """Link existing provisions to baseline versions"""
    # Update provision version_id references
    # Set baseline effective dates
    # Mark all as current
    # Verify linkage integrity
```

### Step 4: Change Tracking Setup (30 minutes)
```python
def setup_change_tracking():
    """Initialize provision change tracking"""
    # Create change tracking tables
    # Record baseline state
    # Set up indexes
    # Validate tracking ready
```

## Verification Checklist

### Data Migration Verification
- [ ] All unique documents identified correctly
- [ ] Baseline versions created for each document
- [ ] All 22,105 provisions linked to versions
- [ ] No orphaned provisions (version_id = NULL)
- [ ] Version metadata includes baseline flags

### Document Coverage Verification
- [ ] LEP documents properly identified
- [ ] SEPP documents properly identified
- [ ] DCP documents properly identified
- [ ] Unknown document types < 5%
- [ ] Provision counts match expected totals

### Change Tracking Verification
- [ ] provision_changes table created
- [ ] Baseline provisions recorded as 'NEW'
- [ ] Indexes created for performance
- [ ] Change tracking ready for future amendments

### Legislative Compliance Verification
- [ ] Baseline date consistently set (2024-09-20)
- [ ] Metadata includes coverage limitations
- [ ] Document URLs point to official sources
- [ ] Audit trail captures migration process

## Deliverables

1. **Document version records** - Baseline versions for all documents
2. **Provision version linkage** - All provisions linked to document versions
3. **Change tracking infrastructure** - Ready for future amendment tracking
4. **Migration report** - Complete audit of migration process
5. **Verification results** - Proof of successful migration

## Rollback Plan
```sql
-- Emergency rollback if migration fails
BEGIN;

-- Remove version linkages
UPDATE regulatory_provisions
SET version_id = NULL,
    version_effective_date = NULL,
    is_current = true;

-- Remove baseline versions
DELETE FROM versions.provision_changes
WHERE created_by = 'baseline_migration_script';

DELETE FROM versions.document_versions
WHERE created_by = 'baseline_migration_script';

-- Drop change tracking table if needed
DROP TABLE IF EXISTS versions.provision_changes;

COMMIT;
```

## Success Criteria
✅ 100% of provisions linked to document versions
✅ Zero orphaned provisions remain
✅ Baseline metadata accurately reflects coverage
✅ Change tracking infrastructure operational
✅ Migration audit trail complete
✅ Performance benchmarks met (<2s queries)

## Next PRP Dependencies
This PRP must complete successfully before:
- PRP-V5-Enhanced (change tracking functionality)
- PRP-V6-Enhanced (API integration)
- All subsequent version-aware features

## Estimated Time
**3 hours total**
- Analysis: 30 minutes
- Bootstrap: 45 minutes
- Linkage: 45 minutes
- Setup: 30 minutes
- Verification: 30 minutes