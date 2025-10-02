# Phase 1 Migration Verification Guide

## Quick Start

### Full Verification Workflow

```bash
# Step 1: Pre-migration verification
python verify_phase1_migration.py pre

# Step 2: Run migration
python run_phase1_migration.py

# Step 3: Post-migration verification
python verify_phase1_migration.py post
```

Expected outcome: **All tests PASS** in both pre and post verification.

---

## Verification Script Features

### Objective Testing Categories

The verification script runs **60+ granular tests** across 9 categories:

#### 1. Database State Checks (Pre-Migration)
- ✓ Table exists
- ✓ Migration columns don't exist yet
- ✓ View doesn't exist yet
- ✓ Baseline data count recorded
- ✓ Critical fields not NULL

#### 2. Data Quality Checks (Pre-Migration)
- ✓ Duplicate patterns identified
- ✓ Provision text coverage >99%
- ✓ Ref_number format analysis
- ✓ Document ID diversity

#### 3. Performance Baseline (Pre-Migration)
- ✓ SELECT query benchmark
- ✓ COUNT query benchmark
- ✓ Filtered query benchmark

#### 4. Schema Verification (Post-Migration)
- ✓ New columns created
- ✓ Indexes created
- ✓ Constraints created
- ✓ View created

#### 5. Data Integrity (Post-Migration)
- ✓ No data loss (count unchanged)
- ✓ Canonical count reasonable (80-95%)
- ✓ Duplicates correctly marked
- ✓ All duplicates have canonical links
- ✓ text_hash populated for all
- ✓ No orphaned duplicates

#### 6. Duplicate Detection Accuracy (Post-Migration)
- ✓ True duplicates marked
- ✓ No false positives
- ✓ Each duplicate group has exactly 1 canonical
- ✓ Sample duplicate groups available

#### 7. Cross-Reference Integrity (Post-Migration)
- ✓ Canonical provisions have no parent
- ✓ All duplicates have parent
- ✓ No circular references

#### 8. Edge Case Detection (Post-Migration)
- ✓ NULL values handled
- ✓ Empty text handled
- ✓ Special characters in hash valid

#### 9. Performance Impact (Post-Migration)
- ✓ Canonical query performance
- ✓ View query performance
- ✓ Performance change <20%

---

## Test Output Format

### Example: All Tests Pass

```
================================================================================
PHASE 1 MIGRATION VERIFICATION - POST-MIGRATION
================================================================================

Timestamp: 2025-10-01 14:35:22
Database: nsw_planning

Running POST-MIGRATION tests...

1. SCHEMA VERIFICATION
--------------------------------------------------------------------------------
  ✓ PASS New columns created
       Found: is_canonical, canonical_provision_id, migration_phase, text_hash
  ✓ PASS Indexes created
       Created 3/3 indexes
  ✓ PASS Foreign key constraint created
       fk_canonical_provision exists
  ✓ PASS View 'regulatory_provisions_canonical' created

2. DATA INTEGRITY CHECKS
--------------------------------------------------------------------------------
  ✓ PASS No data loss (count unchanged)
       Pre: 22,648, Post: 22,648
  ✓ PASS Canonical count reasonable (80-95%)
       89.8% (20,329 canonical, 2,319 duplicates)
  ✓ PASS Duplicates were correctly marked
       2,319 duplicates marked from 2,163 groups
  ✓ PASS All duplicates have canonical_provision_id
       100.0% (2,319/2,319 duplicates linked)
  ✓ PASS text_hash populated for all provisions
       100.0% (22,648/22,648 provisions have hash)
  ✓ PASS No orphaned duplicates
       All duplicates point to valid canonical

3. DUPLICATE DETECTION ACCURACY
--------------------------------------------------------------------------------
  ✓ PASS Each duplicate group has exactly 1 canonical
       100.0% (2,163/2,163 groups correct)
  ✓ PASS No false positives (unique provisions marked as duplicates)
       All unique provisions are canonical
  ✓ PASS Duplicate groups exist for verification
       5 sample groups available

4. CROSS-REFERENCE INTEGRITY
--------------------------------------------------------------------------------
  ✓ PASS Canonical provisions have NULL canonical_provision_id
       All canonical records valid
  ✓ PASS All duplicates have canonical_provision_id
       All duplicates linked
  ✓ PASS No circular canonical references
       No cycles detected

5. EDGE CASE DETECTION
--------------------------------------------------------------------------------
  ✓ PASS NULL provision_text handled
       All provisions have text
  ✓ PASS Empty text provisions identified
       No empty texts
  ✓ PASS text_hash format valid (MD5)
       22,648/22,648 valid MD5 hashes

6. PERFORMANCE IMPACT
--------------------------------------------------------------------------------
  ✓ PASS Canonical filter query (1000 rows)
       15.32ms - Post-migration with filter
  ✓ PASS View query (1000 rows)
       14.87ms - Post-migration using view
  ✓ PASS Performance impact acceptable (<20% change)
       +2.3% - Performance within acceptable range

================================================================================
TEST SUMMARY
================================================================================
Total tests:  23
Passed:       23 (100.0%)
Failed:       0 (0.0%)

================================================================================
✓ ALL TESTS PASSED
================================================================================

Report saved: verification_report_post_20251001_143522.json
```

### Example: Test Failure

```
2. DATA INTEGRITY CHECKS
--------------------------------------------------------------------------------
  ✗ FAIL No orphaned duplicates
       5 orphaned!

================================================================================
TEST SUMMARY
================================================================================
Total tests:  23
Passed:       22 (95.7%)
Failed:       1 (4.3%)

================================================================================
FAILED TESTS
================================================================================
✗ No orphaned duplicates
  Expected: 0
  Actual:   5
  Message:  5 orphaned!

================================================================================
✗ 1 TESTS FAILED
================================================================================
```

---

## JSON Report Output

Each verification run generates a JSON report:

```json
{
  "timestamp": "2025-10-01T14:35:22.123456",
  "phase": "post",
  "database": "nsw_planning",
  "metrics": {
    "total_provisions_post": 22648,
    "canonical_count": 20329,
    "duplicate_count": 2319,
    "benchmark_canonical": 15.32,
    "benchmark_view": 14.87
  },
  "summary": {
    "total_tests": 23,
    "passed": 23,
    "failed": 0
  },
  "tests": [
    {
      "name": "New columns created",
      "passed": true,
      "expected": "{'is_canonical', 'canonical_provision_id', 'text_hash', 'migration_phase'}",
      "actual": "{'is_canonical', 'canonical_provision_id', 'text_hash', 'migration_phase'}",
      "message": "Found: is_canonical, canonical_provision_id, migration_phase, text_hash",
      "timestamp": "2025-10-01T14:35:22.234567"
    },
    ...
  ]
}
```

**Report location:** `verification_report_{phase}_{timestamp}.json`

---

## Usage Scenarios

### Scenario 1: Full Verification Before/After Migration

```bash
# Capture baseline
python verify_phase1_migration.py pre > pre_verification.log

# Run migration
python run_phase1_migration.py

# Verify results
python verify_phase1_migration.py post > post_verification.log

# Compare reports
diff pre_verification.log post_verification.log
```

### Scenario 2: Pre-Migration Checks Only

```bash
# Check if database is ready for migration
python verify_phase1_migration.py pre

# Expected output:
# - Table exists: PASS
# - No migration columns: PASS
# - Duplicate patterns identified: PASS (shows how many will be marked)
```

### Scenario 3: Post-Migration Validation Only

```bash
# After running migration, validate everything worked
python verify_phase1_migration.py post

# If all tests pass:
#   ✓ Safe to update frontend queries
#   ✓ Safe to deploy

# If any tests fail:
#   ✗ Review failures
#   ✗ Consider rollback
#   ✗ Investigate issues
```

### Scenario 4: Automated CI/CD Integration

```bash
#!/bin/bash
# migration_test.sh

set -e  # Exit on error

echo "Running pre-migration verification..."
python verify_phase1_migration.py pre || {
    echo "Pre-migration checks failed"
    exit 1
}

echo "Running migration..."
python run_phase1_migration.py || {
    echo "Migration failed"
    exit 1
}

echo "Running post-migration verification..."
python verify_phase1_migration.py post || {
    echo "Post-migration checks failed"
    echo "Rolling back..."
    python rollback_phase1.py
    exit 1
}

echo "Migration complete and verified!"
```

---

## Pass/Fail Criteria

### Critical Tests (Must Pass)

These tests **must pass** or migration should be rolled back:

- ✓ No data loss (count unchanged)
- ✓ No orphaned duplicates
- ✓ All duplicates have canonical_provision_id
- ✓ Canonical provisions have NULL canonical_provision_id
- ✓ No circular references
- ✓ No false positives
- ✓ text_hash populated for all

### Important Tests (Should Pass)

These should pass, but can be investigated:

- ✓ Canonical count reasonable (80-95%)
- ✓ Performance impact <20%
- ✓ Each duplicate group has exactly 1 canonical

### Informational Tests (Always Pass)

These provide metrics but always pass:

- Baseline provision count recorded
- Duplicate patterns identified
- Ref_number format analysis
- Performance benchmarks

---

## Troubleshooting

### Test: "No data loss" fails

**Symptom:** Post count != Pre count

**Causes:**
- Migration deleted records (shouldn't happen)
- Another process modified data during migration
- Pre-verification metrics file missing

**Solution:**
```bash
# Check current count
psql -U postgres -d nsw_planning -c "SELECT COUNT(*) FROM regulatory_provisions;"

# Compare to backup
# If data loss occurred, restore from backup
python rollback_phase1.py
```

### Test: "No orphaned duplicates" fails

**Symptom:** Duplicates point to non-existent or non-canonical provisions

**Causes:**
- Foreign key constraint didn't enforce properly
- Canonical record was deleted
- Race condition during migration

**Solution:**
```sql
-- Find orphaned duplicates
SELECT dup.id, dup.ref_number, dup.canonical_provision_id
FROM regulatory_provisions dup
LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
WHERE dup.is_canonical = FALSE
  AND (canonical.id IS NULL OR canonical.is_canonical = FALSE);

-- Fix: Re-link to correct canonical
-- Or rollback if too many issues
```

### Test: "Performance impact" fails

**Symptom:** Queries >20% slower after migration

**Causes:**
- Indexes not created properly
- Postgres needs VACUUM ANALYZE
- Query planner not using new indexes

**Solution:**
```sql
-- Check indexes exist
\d regulatory_provisions

-- Rebuild statistics
VACUUM ANALYZE regulatory_provisions;

-- Force index usage
SET enable_seqscan = off;
SELECT * FROM regulatory_provisions WHERE is_canonical = TRUE LIMIT 100;
SET enable_seqscan = on;
```

### Test: "False positives" detected

**Symptom:** Unique provisions marked as duplicates

**Causes:**
- Hash collision (extremely rare)
- Text normalization issue
- Bug in migration logic

**Solution:**
```sql
-- Find false positives
WITH unique_provisions AS (
  SELECT document_id, ref_number, md5(provision_text) as text_hash
  FROM regulatory_provisions
  GROUP BY document_id, ref_number, md5(provision_text)
  HAVING COUNT(*) = 1
)
SELECT rp.id, rp.ref_number
FROM regulatory_provisions rp
JOIN unique_provisions up
  ON rp.document_id = up.document_id
  AND rp.ref_number = up.ref_number
  AND md5(rp.provision_text) = up.text_hash
WHERE rp.is_canonical = FALSE;

-- Fix: Mark as canonical
UPDATE regulatory_provisions
SET is_canonical = TRUE, canonical_provision_id = NULL
WHERE id IN (...);
```

---

## Exit Codes

The verification script uses standard exit codes:

- `0` - All tests passed
- `1` - One or more tests failed

Use in scripts:

```bash
if python verify_phase1_migration.py post; then
    echo "Verification passed"
else
    echo "Verification failed"
    exit 1
fi
```

---

## Best Practices

1. **Always run pre-verification first**
   - Establishes baseline metrics
   - Identifies potential issues before migration
   - Provides comparison data for post-verification

2. **Save verification reports**
   ```bash
   python verify_phase1_migration.py pre | tee pre_verification_$(date +%Y%m%d).log
   ```

3. **Review failed tests immediately**
   - Don't proceed if critical tests fail
   - Investigate root cause
   - Consider rollback if multiple failures

4. **Compare pre/post JSON reports**
   ```bash
   # Load and compare metrics
   jq -s '.[0].metrics as $pre | .[1].metrics as $post |
          {pre: $pre, post: $post}' \
       verification_report_pre_*.json \
       verification_report_post_*.json
   ```

5. **Run verification after frontend changes**
   ```bash
   # After updating queries, re-verify
   python verify_phase1_migration.py post
   ```

---

## What Success Looks Like

**Pre-Migration:**
- All baseline tests pass
- ~2,300 duplicates identified
- No critical NULL fields
- Performance benchmarks recorded

**Post-Migration:**
- 100% test pass rate (23/23 tests)
- 0 orphaned duplicates
- 0 false positives
- Performance within ±20%
- ~20,329 canonical provisions
- ~2,319 duplicates marked
- All data preserved

**Frontend:**
- Queries return 10% fewer provisions
- No visible duplicates in UI
- Compliance dashboard shows clean data
- Performance same or better

---

## Support

If verification fails and you can't resolve:

1. **Save all reports**: Pre, post, and error logs
2. **Check rollback safety**: `python rollback_phase1.py`
3. **Review failed tests**: Look for patterns
4. **Restore from backup**: If data integrity compromised

**Files to keep:**
- `verification_report_pre_*.json`
- `verification_report_post_*.json`
- `pre_verification.log`
- `post_verification.log`
- `backups/pre_phase1_migration_*.sql`

These provide complete audit trail for troubleshooting.
