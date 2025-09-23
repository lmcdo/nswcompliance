# PRP-F4: Provision Linking Completion

## Objective
Complete provision linking for the remaining 10K provisions (44,210 total - 34,290 linked = 9,920 unlinked).

## Root Cause Analysis
V4-Enhanced linked only 34,290 out of 44,210 provisions to baseline versions
- Document identifier matching issues
- Inconsistent document_id formats
- Special characters and naming variations
- Documents not recognized in version creation

## Technical Implementation

### Phase 1: Unlinked Provision Analysis
```sql
-- Identify unlinked provisions
SELECT
    document_id,
    COUNT(*) as provision_count,
    SUBSTRING(document_id, 1, 50) as doc_sample
FROM regulatory_provisions
WHERE version_id IS NULL
GROUP BY document_id
ORDER BY provision_count DESC
LIMIT 20;
```

### Phase 2: Document ID Normalization
```sql
-- Create document identifier mapping function
CREATE OR REPLACE FUNCTION normalize_document_identifier(doc_id TEXT)
RETURNS TEXT AS $$
BEGIN
    -- Remove common prefixes/suffixes
    -- Handle special characters
    -- Standardize naming patterns
    RETURN REGEXP_REPLACE(
        REGEXP_REPLACE(doc_id, '_.*$', ''),  -- Remove everything after first underscore
        '[^A-Za-z0-9 ]', '', 'g'            -- Remove special characters
    );
END;
$$ LANGUAGE plpgsql;
```

### Phase 3: Fuzzy Matching
```sql
-- Find potential matches using similarity
SELECT
    rp.document_id as provision_doc_id,
    dv.document_identifier as version_doc_id,
    SIMILARITY(normalize_document_identifier(rp.document_id), dv.document_identifier) as similarity_score
FROM regulatory_provisions rp
CROSS JOIN versions.document_versions dv
WHERE rp.version_id IS NULL
AND SIMILARITY(normalize_document_identifier(rp.document_id), dv.document_identifier) > 0.6
ORDER BY similarity_score DESC;
```

### Phase 4: Batch Linking
```sql
-- Link provisions to best matching versions
UPDATE regulatory_provisions
SET version_id = (
    SELECT dv.id
    FROM versions.document_versions dv
    WHERE SIMILARITY(normalize_document_identifier(regulatory_provisions.document_id), dv.document_identifier) > 0.8
    ORDER BY SIMILARITY(normalize_document_identifier(regulatory_provisions.document_id), dv.document_identifier) DESC
    LIMIT 1
)
WHERE version_id IS NULL;
```

## Success Criteria
- >95% provisions linked to versions (42,000+ out of 44,210)
- Document mapping accuracy >90%
- V4 verification passes
- No orphaned provisions

## Verification Commands
```bash
python verify_f4_provision_linking.py
```

## Dependencies
- PostgreSQL database with provisions and versions
- similarity extension for fuzzy matching
- Baseline document versions created