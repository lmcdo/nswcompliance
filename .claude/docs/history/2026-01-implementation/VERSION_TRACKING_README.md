# Provision Versioning & Change Tracking

## Overview

This implementation adds provision-level versioning on top of existing document versioning, enabling:

- **Historical Queries**: Retrieve provisions as they existed on any date
- **Change Detection**: Automatic detection of text changes via SHA-256 hashing
- **Change Tracking**: Complete audit trail of all provision modifications
- **Version Comparison**: Before/after text comparison for amendments

## Architecture

### Three-Tier Tracking System

1. **regulatory_provisions** (Current Snapshot)
   - `current_version_id` → points to latest provision_versions.id
   - `is_current = TRUE` → marks active provisions
   - `version_count` → total versions for this provision

2. **provision_versions** (Historical Snapshots)
   - Full provision copies when text changes
   - `effective_from` → when this version became active
   - `effective_to` → when superseded (NULL = current)
   - `text_hash` → SHA-256 for change detection

3. **provision_change_log** (Audit Trail)
   - Lightweight change records
   - Links to before/after versions
   - Amendment references

### Fast Query Paths

- **Current provisions**: `WHERE is_current = TRUE` (no JOIN, <50ms)
- **Historical provisions**: `JOIN provision_versions ON date range` (<500ms)

## Installation

### Step 1: Database Schema

Run the migration to create version tracking tables:

```bash
# Connect to database
psql $DATABASE_URL -f scripts/migrations/create_version_schema.sql
```

This creates:
- `provision_versions` table
- `provision_change_log` table
- Version tracking columns in `regulatory_provisions`
- All necessary indexes

### Step 2: Backfill Existing Data

Create version 1 baseline for all existing provisions:

```bash
# Dry run (no changes)
python scripts/backfill_provision_versions.py --dry-run

# Actual backfill
python scripts/backfill_provision_versions.py

# With custom batch size
python scripts/backfill_provision_versions.py --batch-size 2000
```

**Expected output:**
```
Provisions: 47,818
Version 1 records: 47,818
With current_version_id: 47,818
✓ All validation checks passed
```

### Step 3: Performance Optimization (Optional)

Add materialized views and additional indexes:

```bash
psql $DATABASE_URL -f scripts/migrations/optimize_version_performance.sql
```

## Usage

### Extraction Pipeline (Automatic)

The extraction pipeline automatically creates new versions when provisions change:

```bash
# Example: Re-extract SEPP Housing 2021 (will detect changes)
cd sepp_full_text_extraction
python 04_import_full_provisions_FIXED.py
```

**Output:**
```
Updated: 241 provisions
Inserted: 0 provisions
Versions Created: 15 (changes detected)
```

### API Queries

#### 1. Current Provisions (Default)

```bash
curl "http://localhost:3003/api/provisions/for-property?zone=R2"
```

Returns current provisions with standard filtering.

#### 2. Historical Provisions

```bash
curl "http://localhost:3003/api/provisions/for-property?zone=R2&version_date=2024-05-15"
```

Returns provisions as they existed on May 15, 2024.

#### 3. Provisions with Version Metadata

```bash
curl "http://localhost:3003/api/provisions/for-property?zone=R2&include_version_metadata=true"
```

Returns provisions with version fields:
- `version_number`: Current version (1, 2, 3, etc.)
- `version_count`: Total versions for this provision
- `effective_from`: When current version became active
- `first_seen_date`: When provision was first extracted
- `last_modified_date`: Last change timestamp

#### 4. Query Changes

```bash
# Changes by document
curl "http://localhost:3003/api/provisions/changes?document_id=Marrickville_DCP_2011__Part_2&since=2024-01-01"

# Changes by provision
curl "http://localhost:3003/api/provisions/changes?provision_id=12345&since=2024-01-01"

# Filter by change type
curl "http://localhost:3003/api/provisions/changes?document_id=Marrickville_DCP_2011__Part_2&change_type=modified"
```

**Response structure:**
```json
{
  "success": true,
  "data": {
    "summary": {
      "modified": 15,
      "created": 0,
      "deleted": 0,
      "total": 15
    },
    "changes": {
      "modified": [
        {
          "provision_id": 12345,
          "ref_number": "2.1.4",
          "change_type": "text_modified",
          "changed_at": "2024-06-15T10:30:00Z",
          "text_before": "Old provision text...",
          "text_after": "New provision text...",
          "version_from": 1,
          "version_to": 2,
          "amendment_reference": "Amendment 3 - June 2024"
        }
      ]
    }
  }
}
```

## Testing

### Unit Tests (Database)

```bash
python tests/test_version_tracking.py
```

Tests:
- ✓ Version schema exists
- ✓ Provisions have version baseline
- ✓ Version metadata fields populated
- ✓ Historical queries work
- ✓ Version counts accurate
- ✓ Change log integrity
- ✓ Text hash consistency

### Integration Tests (API)

```bash
# Start Next.js dev server first
cd frontend-nextjs
npm run dev

# Run API tests
python tests/test_versioning_api.py
```

Tests:
- ✓ Current provisions query
- ✓ Historical provisions query
- ✓ Version metadata inclusion
- ✓ Changes by document
- ✓ Changes by provision
- ✓ Changes with date filter

## Maintenance

### Daily (Automated)

```bash
# Update statistics
psql $DATABASE_URL -c "VACUUM ANALYZE provision_versions, provision_change_log;"

# Refresh materialized view (if using)
psql $DATABASE_URL -c "SELECT refresh_current_provisions_view();"
```

### After Batch Updates

```bash
# Update statistics immediately
psql $DATABASE_URL -c "ANALYZE provision_versions;"

# Refresh materialized view
psql $DATABASE_URL -c "SELECT refresh_current_provisions_view();"
```

## How It Works

### Change Detection Algorithm

```python
# 1. Calculate hash of new text
new_hash = sha256(new_text)

# 2. Compare with stored hash
if new_hash != old_hash:
    # 3. Close current version
    UPDATE provision_versions SET effective_to = NOW()
    WHERE provision_id = X AND effective_to IS NULL

    # 4. Create new version
    INSERT INTO provision_versions (...)
    VALUES (provision_id, version_number=2, ...)

    # 5. Update provision
    UPDATE regulatory_provisions
    SET current_version_id = new_version_id,
        version_count = 2
    WHERE id = X

    # 6. Log change
    INSERT INTO provision_change_log (...)
```

### Historical Query Logic

```sql
-- Query provisions as of specific date
SELECT rp.*, pv.provision_text
FROM regulatory_provisions rp
INNER JOIN provision_versions pv ON (
    pv.provision_id = rp.id
    AND pv.effective_from <= '2024-05-15'
    AND (pv.effective_to IS NULL OR pv.effective_to > '2024-05-15')
)
WHERE rp.v2_dcp_layer = 'generic'
```

## Performance

### Benchmarks (47,818 provisions)

| Query Type | Response Time | Notes |
|------------|---------------|-------|
| Current provisions | < 50ms | No JOIN required |
| Historical provisions | < 500ms | With JOIN on date range |
| Changes query | < 100ms | 100 results |
| Materialized view | < 20ms | Precomputed JOIN |

### Optimization Tips

1. **Use materialized view** for current provisions with version metadata (2-3x faster)
2. **Filter by is_current = TRUE** when querying current provisions only
3. **Add date indexes** if querying specific date ranges frequently
4. **Batch updates** and refresh statistics after large changes

## Troubleshooting

### Issue: Slow historical queries

**Solution:** Check index usage:
```sql
EXPLAIN ANALYZE
SELECT * FROM regulatory_provisions rp
INNER JOIN provision_versions pv ON (...)
WHERE ...
```

Verify `idx_pv_date_range` is being used.

### Issue: Version counts don't match

**Solution:** Run validation query:
```sql
SELECT
    rp.id,
    rp.version_count,
    COUNT(pv.id) as actual_versions
FROM regulatory_provisions rp
LEFT JOIN provision_versions pv ON pv.provision_id = rp.id
GROUP BY rp.id, rp.version_count
HAVING rp.version_count != COUNT(pv.id);
```

### Issue: Text hashes incorrect

**Solution:** Recalculate hashes:
```python
from version_tracking import calculate_text_hash
# ... update hashes in database
```

## Legal Compliance

This implementation supports:

1. **Point-in-Time Certification**: Certifiers can retrieve provisions as of DA lodgement date
2. **Audit Trail**: Complete history of all changes with timestamps
3. **Amendment Tracking**: Links changes to specific DCP amendments
4. **Change Comparison**: Before/after text for compliance verification

Per LEGAL_RATIONALE.md Section 7.4, this addresses the legal compliance risk when councils amend DCPs mid-assessment.

## Future Enhancements

Potential improvements (not yet implemented):

1. **Provision Comparison UI**: Visual diff tool showing before/after
2. **Change Notifications**: Alert system for provisions affecting in-progress DAs
3. **Version Comments**: User-added notes on specific versions
4. **Automatic Change Detection**: Email alerts when amendments published
5. **Rollback Capability**: Restore previous versions if needed
6. **Bulk Change Reports**: Summary of all changes in amendment

## Support

For issues or questions:

1. Check LEGAL_RATIONALE.md Section 7.4 for requirements
2. Run test suite: `python tests/test_version_tracking.py`
3. Review database schema: `scripts/migrations/create_version_schema.sql`
4. Check change log: `SELECT * FROM provision_change_log ORDER BY changed_at DESC LIMIT 10;`
