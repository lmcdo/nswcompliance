# LGA Onboarding Automation: Versioning Infrastructure Deployment Plan

**Status:** Ready for staging deployment
**Risk Level:** MEDIUM (adds new tables/columns, does not modify existing data)
**Estimated Effort:** 4-6 hours (staging) + 2-3 hours (production validation)
**Rollback Time:** < 5 minutes (drop new tables/columns)

---

## Context

**Problem:** Provision versioning infrastructure exists as code but was never deployed to production. This blocks:
- LGA onboarding automation (can't track "version 1 baseline" for new councils)
- DCP update handling (can't track provision changes over time)
- Historical compliance queries ("what were the rules on 2024-06-01?")

**Current State:**
- `versions.document_versions`: EXISTS (110 documents, all v1.0-baseline)
- `provision_versions`: DOES NOT EXIST (migration script ready but never run)
- `provision_change_log`: DOES NOT EXIST
- `regulatory_provisions` versioning columns: ALL MISSING (version_id, is_current, current_version_id, text_hash_current)

**Goal:** Deploy provision-level versioning infrastructure with zero downtime and full rollback capability.

---

## Phase 0: Deploy Provision Versioning Infrastructure

### Pre-Deployment Checklist

- [ ] Production database backup created (< 1 hour old)
- [ ] Staging database exists and is synced with production schema
- [ ] Staging deployment completed and validated
- [ ] Rollback SQL script tested in staging
- [ ] API routes querying new tables are behind feature flags (optional but recommended)
- [ ] Monitoring alerts configured for new table queries
- [ ] Team notified of deployment window

### Step 1: Create Database Backup

**Production Backup (CRITICAL - DO FIRST):**
```bash
# Supabase backup via dashboard OR pg_dump
pg_dump $DATABASE_URL > backups/pre-versioning-$(date +%Y%m%d-%H%M%S).sql

# Verify backup file size (should be ~500MB for 46,585 provisions)
ls -lh backups/pre-versioning-*.sql
```

**Expected:** ~500MB dump file with all 58 tables

### Step 2: Run Migration in Staging

**Deploy to staging database:**
```bash
# Set staging database URL
export DATABASE_URL=$STAGING_DATABASE_URL

# Run provision versioning migration
psql $DATABASE_URL -f scripts/migrations/create_version_schema.sql

# Expected output:
# CREATE TABLE provision_versions
# CREATE TABLE provision_change_log
# ALTER TABLE regulatory_provisions ADD COLUMN current_version_id ...
# (5 more ALTER TABLE statements)
# CREATE INDEX idx_pv_provision_id ...
# (11 more index creation statements)
```

**Validation queries:**
```sql
-- Check tables exist
SELECT table_name FROM information_schema.tables
WHERE table_name IN ('provision_versions', 'provision_change_log');
-- Expected: 2 rows

-- Check columns added to regulatory_provisions
SELECT column_name FROM information_schema.columns
WHERE table_name = 'regulatory_provisions'
  AND column_name IN ('current_version_id', 'is_current', 'version_count',
                      'first_seen_date', 'last_modified_date', 'text_hash_current');
-- Expected: 6 rows

-- Check all columns are NULL (no data yet)
SELECT COUNT(*) FROM regulatory_provisions WHERE is_current IS NOT NULL;
-- Expected: 0 (all NULL until backfill)
```

### Step 3: Backfill Version 1 Baseline in Staging

**Run backfill script:**
```bash
# Backfill all 46,585 provisions with version 1
python scripts/backfill_provision_versions.py --batch-size 1000

# Expected output:
# Fetching all provisions from regulatory_provisions...
# [OK] Fetched 46585 provisions
# Preparing 46585 version 1 records...
# [OK] Prepared 46585 version records
# Inserting version records (batch size: 1000)...
#   Processing batch 1/47 (1000 records)...
#   Processing batch 2/47 (1000 records)...
#   ... (45 more batches) ...
# [OK] Inserted 46585 version records
# Updating regulatory_provisions with version references...
# [OK] Updated 46585 provisions with current_version_id
# [OK] Backfill complete
```

**Validation queries:**
```sql
-- All provisions should have version 1
SELECT COUNT(*) FROM provision_versions WHERE version_number = 1;
-- Expected: 46585

-- All provisions should be marked current
SELECT COUNT(*) FROM regulatory_provisions WHERE is_current = true;
-- Expected: 46585

-- All provisions should have current_version_id set
SELECT COUNT(*) FROM regulatory_provisions WHERE current_version_id IS NOT NULL;
-- Expected: 46585

-- No change log entries yet (baseline creation doesn't log)
SELECT COUNT(*) FROM provision_change_log;
-- Expected: 0

-- Check text hashes are populated
SELECT COUNT(*) FROM regulatory_provisions WHERE text_hash_current IS NOT NULL;
-- Expected: 46585
```

### Step 4: Test API Queries in Staging

**Test existing API routes don't break:**
```bash
# Test provisions endpoint (should work unchanged)
curl "https://staging.plotdetect.com/api/provisions/for-property?address=1+Smith+St"

# Test version-aware query (new functionality)
curl "https://staging.plotdetect.com/api/provisions/for-property?address=1+Smith+St&version=current"

# Test historical query (new functionality)
curl "https://staging.plotdetect.com/api/provisions/for-property?address=1+Smith+St&as_at_date=2024-06-01"
```

**Expected:** All queries return data without errors. Historical queries return same results as current (since we haven't created version 2 yet).

### Step 5: Performance Benchmark

**Compare query performance before/after:**
```sql
-- Query without versioning (old approach)
EXPLAIN ANALYZE
SELECT * FROM regulatory_provisions
WHERE document_id LIKE 'Marrickville%'
LIMIT 100;

-- Query with versioning (new approach)
EXPLAIN ANALYZE
SELECT * FROM regulatory_provisions
WHERE document_id LIKE 'Marrickville%'
  AND is_current = true
LIMIT 100;
```

**Expected:** < 10% performance difference (new indexes compensate for additional WHERE clause)

### Step 6: Staging Validation Complete

**Checklist:**
- [ ] `provision_versions` table exists with 46,585 rows
- [ ] `provision_change_log` table exists (empty)
- [ ] `regulatory_provisions` has 6 new columns, all populated
- [ ] All provisions marked `is_current = true`
- [ ] API routes return correct data
- [ ] Query performance acceptable (< 10% regression)
- [ ] No errors in application logs

**If all checks pass:** Proceed to production deployment
**If any check fails:** Investigate, fix, and re-run from Step 2

---

## Production Deployment

### Pre-Production Checklist

- [ ] Staging deployment validated (all checks passed)
- [ ] Production backup created (< 30 minutes old)
- [ ] Rollback script ready and tested
- [ ] Deployment window scheduled (low-traffic period recommended)
- [ ] Team standing by for monitoring
- [ ] Communication sent to stakeholders (if applicable)

### Production Deployment Steps

**1. Create fresh production backup:**
```bash
# Backup production database
pg_dump $PRODUCTION_DATABASE_URL > backups/prod-pre-versioning-$(date +%Y%m%d-%H%M%S).sql

# Verify backup
ls -lh backups/prod-pre-versioning-*.sql
```

**2. Run migration in production:**
```bash
export DATABASE_URL=$PRODUCTION_DATABASE_URL

# Run migration (should take 30-60 seconds)
psql $DATABASE_URL -f scripts/migrations/create_version_schema.sql
```

**3. Run backfill in production:**
```bash
# Backfill all provisions (should take 5-10 minutes)
python scripts/backfill_provision_versions.py --batch-size 1000
```

**4. Immediate validation:**
```sql
-- Quick checks (run immediately after backfill)
SELECT COUNT(*) FROM provision_versions WHERE version_number = 1; -- 46585
SELECT COUNT(*) FROM regulatory_provisions WHERE is_current = true; -- 46585
SELECT COUNT(*) FROM regulatory_provisions WHERE current_version_id IS NULL; -- 0
```

**5. API smoke tests:**
```bash
# Test critical endpoints
curl "https://plotdetect.com/api/provisions/for-property?address=185+Parramatta+Rd"
curl "https://plotdetect.com/api/dcp/provisions?council=marrickville"
```

**6. Monitor for 15 minutes:**
- Check application logs for errors
- Monitor API response times (should be unchanged)
- Check Supabase dashboard for connection pool usage
- Verify no user-facing errors

**If all checks pass:** Deployment complete ✅
**If any issue detected:** Execute rollback immediately

---

## Rollback Procedure

**Time to rollback:** < 5 minutes
**Data loss:** None (only drops new tables/columns, doesn't modify existing data)

### Rollback SQL Script

**Save this as `migrations/rollback_version_schema.sql`:**
```sql
-- ============================================================================
-- ROLLBACK: Provision Versioning Infrastructure
-- ============================================================================
-- Reverts create_version_schema.sql migration
-- Safe to run: Only drops NEW tables/columns, doesn't modify existing data
-- ============================================================================

BEGIN;

-- Drop new tables (CASCADE removes foreign key references)
DROP TABLE IF EXISTS provision_change_log CASCADE;
DROP TABLE IF EXISTS provision_versions CASCADE;

-- Drop new columns from regulatory_provisions
ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS current_version_id;
ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS first_seen_date;
ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS last_modified_date;
ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS version_count;
ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS is_current;
ALTER TABLE regulatory_provisions DROP COLUMN IF EXISTS text_hash_current;

-- Drop new indexes (automatically dropped with tables, but explicit for clarity)
DROP INDEX IF EXISTS idx_pv_provision_id;
DROP INDEX IF EXISTS idx_pv_current;
DROP INDEX IF EXISTS idx_pv_date_range;
DROP INDEX IF EXISTS idx_pv_text_hash;
DROP INDEX IF EXISTS idx_pcl_provision_id;
DROP INDEX IF EXISTS idx_pcl_changed_at;
DROP INDEX IF EXISTS idx_pcl_document;
DROP INDEX IF EXISTS idx_pcl_change_type;
DROP INDEX IF EXISTS idx_rp_current_version;
DROP INDEX IF EXISTS idx_rp_is_current;
DROP INDEX IF EXISTS idx_rp_text_hash;

-- Drop materialized view if it was created
DROP MATERIALIZED VIEW IF EXISTS current_provisions_with_versions CASCADE;

COMMIT;

-- Validation: Verify rollback successful
SELECT
    CASE
        WHEN COUNT(*) = 0 THEN '✅ Rollback successful - provision_versions does not exist'
        ELSE '❌ Rollback failed - provision_versions still exists'
    END AS status
FROM information_schema.tables
WHERE table_name = 'provision_versions';
```

### Execute Rollback

**If deployment fails:**
```bash
# Rollback immediately
psql $DATABASE_URL -f migrations/rollback_version_schema.sql

# Verify rollback
psql $DATABASE_URL -c "SELECT table_name FROM information_schema.tables WHERE table_name IN ('provision_versions', 'provision_change_log');"
# Expected: 0 rows (tables dropped)

# Check regulatory_provisions columns
psql $DATABASE_URL -c "SELECT column_name FROM information_schema.columns WHERE table_name = 'regulatory_provisions' AND column_name IN ('is_current', 'current_version_id');"
# Expected: 0 rows (columns dropped)
```

**Recovery time:** < 5 minutes (database back to pre-deployment state)

---

## Post-Deployment Monitoring

### Day 1: Intensive Monitoring

**Hour 1:**
- Monitor API response times (should be unchanged)
- Check error logs (should be zero new errors)
- Verify Supabase connection pool (should be stable)

**Hours 2-24:**
- Check application logs every 2 hours
- Monitor query performance metrics
- Verify no user-reported issues

### Week 1: Daily Checks

- Run validation queries daily
- Check provision_change_log (should remain empty until first update)
- Monitor database size (expect +10-15% for version tables)

### Ongoing: Alert Setup

**Configure alerts for:**
- Queries to `provision_versions` taking > 500ms
- `provision_change_log` insert errors
- `regulatory_provisions.is_current = false` percentage > 10% (indicates versioning in use)

---

## Known Risks & Mitigations

### Risk 1: Backfill Takes Too Long
**Symptom:** Backfill script runs > 30 minutes
**Impact:** Extended deployment window
**Mitigation:** Increase batch size to 5000 (still safe for Postgres)
**Rollback trigger:** If > 1 hour, rollback and investigate

### Risk 2: API Routes Break Due to NULL Columns
**Symptom:** 500 errors on `/api/provisions/*` endpoints
**Impact:** User-facing errors
**Mitigation:** API routes should handle NULL gracefully (versioning is optional)
**Rollback trigger:** If > 5% error rate on any endpoint, rollback immediately

### Risk 3: Database Size Exceeds Supabase Plan Limits
**Symptom:** Storage usage increases 15-20% after backfill
**Impact:** Potential plan upgrade needed
**Mitigation:** Estimate impact beforehand (46,585 provisions × ~1KB per version = ~50MB additional storage)
**Rollback trigger:** None (storage increase is expected and within limits)

### Risk 4: Performance Degradation on Provision Queries
**Symptom:** Query times increase > 50%
**Impact:** Slow API responses
**Mitigation:** Indexes should prevent this; if detected, run `ANALYZE regulatory_provisions`
**Rollback trigger:** If > 100% regression after re-indexing, rollback and optimize

---

## Success Criteria

**Deployment is successful if:**
- ✅ All 46,585 provisions have `version_number = 1`
- ✅ All provisions marked `is_current = true`
- ✅ API endpoints return correct data (no errors)
- ✅ Query performance within 10% of baseline
- ✅ No user-facing errors for 24 hours post-deployment
- ✅ Application logs show zero version-related errors

**Deployment is considered stable after:**
- 7 days with no version-related errors
- Historical queries tested and validated
- First provision update successfully creates version 2 (future milestone)

---

## Next Steps After Successful Deployment

Once versioning infrastructure is deployed and stable:

**Week 2-3: Deploy Council Schema (Phase 1)**
- Create `councils` reference table
- Add `council_id` to `regulatory_provisions` and `versions.document_versions`
- Migrate existing data
- Update API routes to use `council_id + is_current` filtering

**Week 4-5: Build Automation Tools (Phase 2)**
- LLM-assisted DCP config generator (reduces 4 hours to 1 hour)
- RAG-assisted topic mapper (reduces 1.5 hours to 20 minutes)
- Config-driven marker extraction (reduces 1.5 hours to 15 minutes)

**Week 6-7: Regulatory Update Monitoring**
- NSW Legislation RSS poller (SEPP/LEP automation)
- Council DCP monitoring checklist
- Version comparison UI for certifiers

**Estimated Total Impact:**
- LGA onboarding: 11-19 hours → 2-4 hours (82-88% reduction)
- ROI for 130 LGAs: 1,170-1,950 hours saved

---

## References

**Migration Files:**
- `scripts/migrations/create_version_schema.sql` - Main migration
- `scripts/migrations/optimize_version_performance.sql` - Performance optimization (optional, run after backfill)
- `scripts/backfill_provision_versions.py` - Version 1 baseline creation

**Service Files:**
- `services/version_manager.py` - Document version management
- `services/version_aware_query.py` - Version-aware query wrappers

**API Routes:**
- `frontend-nextjs/app/api/versions/route.ts` - Version management endpoints
- `frontend-nextjs/app/api/provisions/changes/route.ts` - Change tracking endpoints
- `frontend-nextjs/app/api/provisions/for-property/route.ts` - Version-aware provision queries (lines 689-713)

**Documentation:**
- `.claude/plans/lga-onboarding-architecture-review.md` - Original architectural analysis
- `.claude/plans/lga-onboarding-versioning-research-report.md` - Versioning infrastructure research

---

## Deployment Sign-Off

**Staging Deployment:**
- [ ] Completed by: ________________
- [ ] Date: ________________
- [ ] All validation checks passed: ☐ Yes ☐ No

**Production Deployment:**
- [ ] Approved by: ________________
- [ ] Date: ________________
- [ ] Backup created: ☐ Yes ☐ No
- [ ] Deployment successful: ☐ Yes ☐ No
- [ ] Rollback required: ☐ Yes ☐ No

**Post-Deployment Validation:**
- [ ] 24-hour stability confirmed: ☐ Yes ☐ No
- [ ] 7-day stability confirmed: ☐ Yes ☐ No
- [ ] Ready for Phase 1 (council schema): ☐ Yes ☐ No
