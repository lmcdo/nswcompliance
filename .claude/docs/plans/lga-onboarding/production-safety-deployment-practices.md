# Production-Safe Deployment Practices for PlotDetect/ComplianceEngine

**Context:** Supabase database + Next.js frontend + Python backend
**Requirement:** Zero-downtime deployments with instant rollback capability
**Criticality:** HIGH (certifiers depend on accurate, always-available compliance data)

---

## Architecture: Two-Environment Strategy

### Environment 1: Staging (Required)

**Purpose:** Exact replica of production for testing deployments

**Setup:**
```bash
# Create staging Supabase project (free tier acceptable)
# - Same schema as production
# - Synced data (can be subset for cost savings)
# - Separate DATABASE_URL

# .env.staging
DATABASE_URL=postgresql://postgres:***@db.staging-project.supabase.co:5432/postgres
NEXT_PUBLIC_SUPABASE_URL=https://staging-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=***
ENVIRONMENT=staging
```

**Data Sync Strategy:**
```bash
# Option A: Full sync (recommended for critical deployments)
pg_dump $PRODUCTION_DATABASE_URL | psql $STAGING_DATABASE_URL

# Option B: Schema-only sync (faster, for testing migrations)
pg_dump --schema-only $PRODUCTION_DATABASE_URL | psql $STAGING_DATABASE_URL

# Option C: Automated nightly sync (Supabase doesn't support this natively)
# Use cron + pg_dump/restore script
```

**When to Sync:**
- Before every major deployment (migration, schema change)
- Weekly for ongoing testing
- After production incidents (to reproduce bugs)

### Environment 2: Production

**Protection Measures:**
```bash
# .env.production (locked down)
DATABASE_URL=postgresql://postgres:***@db.production-project.supabase.co:5432/postgres
ENVIRONMENT=production

# Never run destructive commands directly
# All changes go through staging first
```

**Access Control:**
- Production database: Read-only for developers
- Migrations: Executed by deployment pipeline only
- Manual queries: Require approval + audit log

---

## Database Migration Best Practices

### Rule 1: All Migrations Are Reversible

**GOOD Migration (Reversible):**
```sql
-- Forward migration: 001_add_council_id.sql
BEGIN;

ALTER TABLE regulatory_provisions
ADD COLUMN council_id TEXT;

CREATE INDEX idx_provisions_council
ON regulatory_provisions(council_id);

COMMIT;

-- Reverse migration: 001_add_council_id_rollback.sql
BEGIN;

DROP INDEX IF EXISTS idx_provisions_council;

ALTER TABLE regulatory_provisions
DROP COLUMN IF EXISTS council_id;

COMMIT;
```

**BAD Migration (Irreversible):**
```sql
-- DON'T DO THIS - can't undo if something breaks
DROP TABLE regulatory_provisions;
```

### Rule 2: Migrations Are Additive, Not Destructive

**Safe Migration Patterns:**
- ✅ Add new tables
- ✅ Add new columns (with DEFAULT or NULL)
- ✅ Add new indexes
- ✅ Create views (doesn't lock tables)
- ✅ Insert new data

**Unsafe Migration Patterns (Require Extra Care):**
- ⚠️ Drop columns (must verify nothing reads them first)
- ⚠️ Rename columns (breaks API contracts)
- ⚠️ Change column types (can cause data loss)
- ⚠️ Drop tables (must verify nothing queries them)
- ❌ Truncate data (irreversible data loss)

### Rule 3: Test Migrations on Staging First

**Mandatory Staging Tests:**
```bash
# 1. Apply migration to staging
psql $STAGING_DATABASE_URL -f migrations/001_add_versioning.sql

# 2. Run application test suite
npm run test:integration

# 3. Smoke test critical API endpoints
curl "https://staging.plotdetect.com/api/provisions/for-property?address=185+Parramatta+Rd"

# 4. Benchmark query performance
psql $STAGING_DATABASE_URL -f tests/benchmark_queries.sql

# 5. Test rollback
psql $STAGING_DATABASE_URL -f migrations/001_add_versioning_rollback.sql

# 6. Verify application still works after rollback
curl "https://staging.plotdetect.com/api/provisions/for-property?address=185+Parramatta+Rd"

# 7. Re-apply migration (verify idempotency)
psql $STAGING_DATABASE_URL -f migrations/001_add_versioning.sql
```

**If ALL tests pass:** Migration is safe for production
**If ANY test fails:** Fix migration, retest from step 1

---

## Code Deployment Best Practices

### Strategy 1: Feature Flags (Recommended for PlotDetect)

**Concept:** Deploy code in "off" state, enable gradually

**Implementation:**
```typescript
// lib/feature-flags.ts
export const FEATURE_FLAGS = {
  PROVISION_VERSIONING: process.env.NEXT_PUBLIC_ENABLE_VERSIONING === 'true',
  COUNCIL_ID_FILTERING: process.env.NEXT_PUBLIC_ENABLE_COUNCIL_ID === 'true',
} as const;

// app/api/provisions/for-property/route.ts
import { FEATURE_FLAGS } from '@/lib/feature-flags';

export async function GET(request: Request) {
  // Old code path (always works)
  if (!FEATURE_FLAGS.PROVISION_VERSIONING) {
    const query = `
      SELECT * FROM regulatory_provisions
      WHERE document_id LIKE '${council}%'
    `;
    return query(query);
  }

  // New code path (enabled by flag)
  const query = `
    SELECT * FROM regulatory_provisions
    WHERE council_id = $1 AND is_current = true
  `;
  return query(query, [council]);
}
```

**Deployment Workflow:**
1. Deploy code with feature flag OFF
2. Verify application works (flag defaults to old behavior)
3. Enable flag in staging, test
4. Enable flag in production, monitor
5. If issues: Disable flag instantly (no code deploy needed)
6. If stable for 7 days: Remove flag, make new behavior default

**Rollback Time:** < 1 minute (just toggle environment variable)

### Strategy 2: Blue-Green Deployment (Vercel Native)

**Concept:** Deploy to new environment, switch traffic instantly

**Vercel Automatic Setup:**
```bash
# Every git push creates a preview deployment
git push origin feature/add-versioning
# Vercel creates: https://compliance-engine-feature-versioning-abc123.vercel.app

# Test preview deployment thoroughly
curl "https://compliance-engine-feature-versioning-abc123.vercel.app/api/provisions/for-property?address=..."

# If tests pass, merge to main
git checkout main && git merge feature/add-versioning && git push

# Vercel promotes to production automatically
# Old version still available at: https://compliance-engine-git-main-previous-abc456.vercel.app
```

**Rollback Time:** < 30 seconds (via Vercel dashboard: Deployments → Redeploy previous)

### Strategy 3: Database Schema Versioning

**Problem:** Frontend deployed with new schema, but database migration hasn't run yet → 500 errors

**Solution:** Make code backward-compatible for 1 deployment cycle

**Example:**
```typescript
// Week 1: Deploy code that works with OR without new column
export async function GET(request: Request) {
  const query = `
    SELECT
      *,
      ${await columnExists('regulatory_provisions', 'council_id')
        ? 'council_id'
        : 'substring(document_id, 1, position(\'_\' in document_id) - 1) as council_id'
      }
    FROM regulatory_provisions
  `;
}

// Week 2: Run database migration (adds council_id column)
// Code already handles both cases, so zero downtime

// Week 3: Remove backward-compatibility shim
export async function GET(request: Request) {
  const query = `SELECT *, council_id FROM regulatory_provisions`;
}
```

**Deployment Order:**
1. Deploy backward-compatible code (works with old AND new schema)
2. Run database migration
3. Verify both old and new code work
4. Deploy final code (removes backward-compatibility shim)

**Rollback Time:** Instant (old code still works with new schema)

---

## Backup & Restore Strategy

### Automated Backups (Supabase Built-In)

**Supabase Free Tier:**
- Daily automated backups (retained for 7 days)
- Access via: Dashboard → Database → Backups

**Supabase Pro Tier:**
- Point-in-time recovery (restore to any moment in last 7 days)
- Automated backups every 24 hours (retained for 30 days)

**Limitations:**
- Cannot automate backup before each deployment
- Must create manual backup via pg_dump

### Manual Backups (Critical Deployments)

**When to Create Manual Backup:**
- Before EVERY database migration
- Before major data updates (e.g., backfill 46,585 provisions)
- Before risky operations (drop column, change type)

**Backup Procedure:**
```bash
# Create timestamped backup directory
mkdir -p backups/$(date +%Y-%m-%d)

# Full database backup (includes schema + data)
pg_dump $DATABASE_URL --format=custom --file=backups/$(date +%Y-%m-%d)/full-backup-$(date +%H%M%S).dump

# Schema-only backup (for quick rollback of schema changes)
pg_dump $DATABASE_URL --schema-only --file=backups/$(date +%Y-%m-%d)/schema-backup-$(date +%H%M%S).sql

# Verify backup file size (should be ~500MB for full backup)
ls -lh backups/$(date +%Y-%m-%d)/

# Upload backup to cloud storage (DO NOT RELY ON LOCAL ONLY)
aws s3 cp backups/$(date +%Y-%m-%d)/ s3://plotdetect-backups/$(date +%Y-%m-%d)/ --recursive
# OR: Upload to Google Drive, Dropbox, etc.
```

**Restore Procedure:**
```bash
# Restore full database (DESTRUCTIVE - only for disasters)
pg_restore --clean --if-exists --no-owner --no-acl \
  -d $DATABASE_URL backups/2026-02-11/full-backup-143022.dump

# Restore specific table (less destructive)
pg_restore --table=regulatory_provisions --data-only \
  -d $DATABASE_URL backups/2026-02-11/full-backup-143022.dump

# Restore schema only (to undo migration)
psql $DATABASE_URL -f backups/2026-02-11/schema-backup-143022.sql
```

**Restore Time:**
- Schema only: < 1 minute
- Full database: 5-10 minutes (for 500MB)

### Backup Retention Policy

**Local Backups:**
- Critical deployments: Keep for 90 days
- Weekly backups: Keep for 30 days
- Automated daily: Keep for 7 days

**Cloud Backups (S3/GCS):**
- Critical deployments: Keep for 1 year
- Weekly backups: Keep for 90 days
- Compress old backups (gzip) to save storage costs

---

## Deployment Workflow: Step-by-Step

### Pre-Deployment Phase (1-2 days before)

**Day -2:**
- [ ] Sync production data to staging
- [ ] Test migration on staging
- [ ] Run application test suite
- [ ] Benchmark query performance
- [ ] Test rollback procedure
- [ ] Document expected behavior changes

**Day -1:**
- [ ] Review migration with team
- [ ] Schedule deployment window (low-traffic time)
- [ ] Prepare rollback SQL script
- [ ] Notify stakeholders (if user-facing changes)
- [ ] Set up monitoring alerts

### Deployment Day

**30 minutes before:**
- [ ] Create production database backup
- [ ] Verify backup file integrity
- [ ] Upload backup to cloud storage
- [ ] Confirm team availability for monitoring

**Deployment:**
```bash
# Step 1: Create backup (5 minutes)
pg_dump $DATABASE_URL --format=custom --file=backups/pre-deployment-$(date +%Y%m%d-%H%M%S).dump

# Step 2: Run migration (1-2 minutes)
psql $DATABASE_URL -f migrations/001_add_versioning.sql

# Step 3: Immediate validation (1 minute)
psql $DATABASE_URL -c "SELECT COUNT(*) FROM provision_versions;" # Should return 0 (or expected count)

# Step 4: Run backfill/data update (5-10 minutes)
python scripts/backfill_provision_versions.py --batch-size 1000

# Step 5: Validation queries (2 minutes)
psql $DATABASE_URL -f tests/validate_versioning.sql

# Step 6: API smoke tests (2 minutes)
curl "https://plotdetect.com/api/provisions/for-property?address=185+Parramatta+Rd"
curl "https://plotdetect.com/api/dcp/provisions?council=marrickville"

# Step 7: Monitor for 15 minutes
# - Check application logs
# - Monitor API response times
# - Watch Supabase dashboard for errors
```

**Total deployment time:** 20-30 minutes

**Post-Deployment:**
- [ ] Monitor logs for 1 hour (intensive)
- [ ] Check metrics every 2 hours for 24 hours
- [ ] Daily check for 7 days
- [ ] Mark deployment as stable after 7 days

### Rollback Decision Tree

**Minor Issue (slow query, 5% error rate):**
- Keep deployment live
- Investigate and fix forward
- No rollback needed

**Moderate Issue (10-25% error rate, user complaints):**
- Disable feature flag (if applicable)
- If no flag: Rollback database schema
- Investigate root cause
- Re-deploy with fix

**Critical Issue (> 25% error rate, site down, data corruption):**
- **IMMEDIATE ROLLBACK** (< 5 minutes)
- Restore database from backup
- Redeploy previous Vercel deployment
- Incident post-mortem required

---

## Specific Strategy for Versioning Infrastructure Deployment

### Why This Deployment Is Low-Risk

**What it does:**
- Adds NEW tables (`provision_versions`, `provision_change_log`)
- Adds NEW columns to `regulatory_provisions` (all nullable initially)
- Does NOT modify existing columns
- Does NOT delete any data
- Does NOT change existing query behavior (new columns are NULL)

**Failure modes:**
- ❌ Migration fails due to syntax error → Rollback via BEGIN/ROLLBACK transaction
- ❌ Backfill script fails halfway → Rollback and re-run (idempotent)
- ❌ API breaks due to NULL columns → Unlikely (code should handle NULL gracefully)
- ❌ Query performance degrades → Rollback or add more indexes

**All failure modes are recoverable via rollback.**

### Recommended Approach: Phased Deployment

**Phase 1: Schema Only (Week 1)**
```bash
# Deploy tables and columns WITHOUT backfill
psql $DATABASE_URL -f migrations/create_version_schema.sql

# Verify tables exist but are empty
psql $DATABASE_URL -c "SELECT COUNT(*) FROM provision_versions;" # 0

# All columns are NULL (no impact on existing queries)
psql $DATABASE_URL -c "SELECT COUNT(*) FROM regulatory_provisions WHERE is_current IS NOT NULL;" # 0

# Monitor for 24 hours
# If stable: Proceed to Phase 2
# If issues: Rollback (no data loss, just drop empty tables)
```

**Phase 2: Backfill Data (Week 2)**
```bash
# Run backfill to populate version 1 baseline
python scripts/backfill_provision_versions.py --batch-size 1000

# Verify all provisions have version 1
psql $DATABASE_URL -c "SELECT COUNT(*) FROM provision_versions WHERE version_number = 1;" # 46585

# Monitor for 7 days
# If stable: Mark deployment complete
# If issues: Rollback data (truncate provision_versions, set columns to NULL)
```

**Phase 3: Enable Version-Aware Queries (Week 3)**
```bash
# Deploy code with feature flag
export NEXT_PUBLIC_ENABLE_VERSIONING=true

# Test in staging first
# If stable: Enable in production
# If issues: Disable flag (instant rollback to old query logic)
```

**Total timeline:** 3 weeks (conservative, can compress to 1 week if aggressive)

---

## Monitoring & Alerting

### Critical Metrics to Track

**Database Metrics:**
- Query response time (p50, p95, p99)
- Connection pool utilization
- Table sizes (watch for unexpected growth)
- Index usage (verify new indexes are used)

**Application Metrics:**
- API endpoint response times
- Error rates (per endpoint)
- User-facing errors (via Sentry/logging)
- Deployment frequency (track stability)

**Business Metrics:**
- Provision queries returning zero results (indicates data issue)
- Version queries returning unexpected counts
- Certifier feedback (are compliance reports accurate?)

### Alert Thresholds

**Immediate Alert (Page Engineer):**
- API error rate > 5% for 5 minutes
- Database connection pool > 90% for 1 minute
- Query response time > 5 seconds (p95)

**Warning Alert (Investigate Next Business Day):**
- API error rate > 1% for 15 minutes
- Query response time degradation > 50%
- Provision count discrepancy (unexpected increase/decrease)

**Info Alert (Weekly Review):**
- New table size > 100MB (expected for version tables)
- Index usage < 50% (indicates unused index)

---

## Best Practices Summary

### Golden Rules

1. **Always test on staging first** (no exceptions)
2. **Always create backup before migrations** (no exceptions)
3. **Always have a rollback plan** (tested on staging)
4. **Always monitor after deployment** (15 min intensive, 24 hour regular)
5. **Always deploy during low-traffic windows** (if possible)

### Two-Database Strategy

**Staging Database:**
- Purpose: Test migrations and deployments
- Data: Synced from production before major deployments
- Access: Open to developers (can break without impact)
- Cost: Free tier acceptable (data can be subset)

**Production Database:**
- Purpose: Serve live users
- Data: Sacred (never test on production)
- Access: Read-only for developers, write-only via deployment pipeline
- Cost: Pro tier recommended (point-in-time recovery)

### Code Deployment

**Vercel Automatic (Current Setup):**
- Every git push to `main` → Production deploy
- Preview deployments for branches
- Instant rollback via dashboard

**Recommended Enhancement:**
- Add feature flags for risky changes
- Use preview deployments for testing
- Gradual rollout (Vercel A/B testing)

### Database Deployment

**Current Process (Risky):**
- Direct psql to production

**Recommended Process:**
1. Test migration on staging
2. Create production backup
3. Run migration in transaction (BEGIN/COMMIT)
4. Validate immediately
5. Monitor for 15 minutes
6. Rollback if any issues

---

## Deployment Checklist Template

**Pre-Deployment:**
- [ ] Migration tested on staging (all tests pass)
- [ ] Rollback script tested on staging
- [ ] Production backup created (< 30 min old)
- [ ] Backup uploaded to cloud storage
- [ ] Team notified and available
- [ ] Monitoring dashboards open

**Deployment:**
- [ ] Migration executed successfully
- [ ] Validation queries pass
- [ ] API smoke tests pass
- [ ] No errors in logs
- [ ] Query performance acceptable

**Post-Deployment:**
- [ ] 15-minute intensive monitoring (no issues)
- [ ] 1-hour check (no issues)
- [ ] 24-hour check (no issues)
- [ ] 7-day stability confirmed
- [ ] Deployment marked as successful

**Rollback (If Needed):**
- [ ] Rollback SQL executed
- [ ] Validation queries confirm rollback
- [ ] Application functioning normally
- [ ] Incident post-mortem scheduled
- [ ] Root cause identified
- [ ] Fix applied to staging
- [ ] Re-deployment scheduled

---

## Tools & Scripts

### Backup Script

**Save as `scripts/backup_production.sh`:**
```bash
#!/bin/bash
set -e

TIMESTAMP=$(date +%Y%m%d-%H%M%S)
BACKUP_DIR="backups/$(date +%Y-%m-%d)"
BACKUP_FILE="$BACKUP_DIR/production-backup-$TIMESTAMP.dump"

echo "Creating backup directory: $BACKUP_DIR"
mkdir -p "$BACKUP_DIR"

echo "Backing up production database..."
pg_dump $DATABASE_URL --format=custom --file="$BACKUP_FILE"

echo "Verifying backup..."
ls -lh "$BACKUP_FILE"

FILE_SIZE=$(stat -f%z "$BACKUP_FILE" 2>/dev/null || stat -c%s "$BACKUP_FILE")
if [ $FILE_SIZE -lt 100000000 ]; then  # < 100MB is suspicious
    echo "WARNING: Backup file seems small ($FILE_SIZE bytes)"
    echo "Expected > 100MB for production database"
    exit 1
fi

echo "✅ Backup created successfully: $BACKUP_FILE"
echo "Next: Upload to cloud storage"
echo "  aws s3 cp $BACKUP_FILE s3://plotdetect-backups/"
```

### Validation Script

**Save as `tests/validate_versioning.sql`:**
```sql
-- Validation queries for versioning deployment
-- Run immediately after migration/backfill

\echo 'Checking provision_versions table...'
SELECT COUNT(*) as version_count FROM provision_versions WHERE version_number = 1;
-- Expected: 46585

\echo 'Checking regulatory_provisions is_current...'
SELECT COUNT(*) as current_count FROM regulatory_provisions WHERE is_current = true;
-- Expected: 46585

\echo 'Checking NULL current_version_id...'
SELECT COUNT(*) as null_count FROM regulatory_provisions WHERE current_version_id IS NULL;
-- Expected: 0

\echo 'Checking provision_change_log...'
SELECT COUNT(*) as change_count FROM provision_change_log;
-- Expected: 0 (no changes yet)

\echo 'Checking text hashes...'
SELECT COUNT(*) as hash_count FROM regulatory_provisions WHERE text_hash_current IS NOT NULL;
-- Expected: 46585

\echo '✅ All validation checks complete'
```

---

## Emergency Contacts & Escalation

**Database Issues:**
- Primary: [Database Admin Email]
- Secondary: Supabase Support (support@supabase.io)
- Escalation: Post in Supabase Discord (#support)

**Application Issues:**
- Primary: [Lead Developer]
- Secondary: Vercel Support (via dashboard)

**Data Integrity Issues:**
- Primary: [Data Engineer]
- Critical: Restore from backup immediately, investigate later

**User Impact:**
- Primary: [Product Owner]
- Communication: Update status page, email users if > 15 min downtime

---

## Post-Mortem Template (If Rollback Occurs)

**Incident:** [Brief description]
**Date:** [YYYY-MM-DD]
**Duration:** [Downtime/degradation duration]
**Impact:** [Users affected, error rate, etc.]

**Timeline:**
- [HH:MM] Deployment initiated
- [HH:MM] Issue detected
- [HH:MM] Rollback decision made
- [HH:MM] Rollback completed
- [HH:MM] Service restored

**Root Cause:**
- [Technical explanation]

**Why It Wasn't Caught in Staging:**
- [Analysis]

**Lessons Learned:**
- [What we'll do differently]

**Action Items:**
- [ ] [Preventive measure 1]
- [ ] [Preventive measure 2]
- [ ] [Process improvement]

---

## Conclusion

**For the versioning infrastructure deployment specifically:**

**Risk Level:** LOW-MEDIUM
- Adds new tables/columns (non-destructive)
- Doesn't modify existing data
- All changes are reversible
- Rollback time < 5 minutes

**Recommended Approach:**
1. **Week 1:** Deploy schema only (tables + columns, no data)
2. **Week 2:** Backfill version 1 baseline
3. **Week 3:** Enable version-aware queries via feature flag
4. **Week 4:** Remove feature flag, make permanent

**Total Timeline:** 4 weeks (conservative)
**Fast-Track:** 1 week (if staging tests are perfect)

**Confidence Level:** HIGH (infrastructure is well-designed, migration is additive, rollback is trivial)

---

**Next Steps:**
1. Set up staging database (if not already exists)
2. Sync production schema to staging
3. Run full deployment workflow on staging
4. Schedule production deployment window
5. Execute deployment with monitoring
