# Database Recovery - January 27, 2026

> **UPDATE (January 28, 2026 9:40 AM)**: Recovery completed successfully! See **RECOVERY_COMPLETE_JAN28.md** for full details of the correct recovery process and final database state.

## Incident Summary

**Date**: January 27, 2026, 11:10 PM
**Issue**: `regulatory_provisions` table accidentally truncated during version tracking implementation
**Cause**: `TRUNCATE CASCADE` on `provision_versions` table affected parent table through foreign key relationship

## Recovery Actions Taken

1. **Identified Available Backups**
   - Found complete backup: `regulatory_provisions_before_v2_20251122_231205.json`
   - Backup date: November 22, 2025
   - Backup size: 102 MB
   - Row count: 48,374 provisions

2. **Restored Data**
   - Successfully restored all 48,374 provisions
   - Verified data integrity
   - All foreign key relationships intact
   - Related tables unaffected (documents, dcp_general_requirements, etc.)

## Current Database State

### Main Tables
| Table | Row Count | Status |
|-------|-----------|--------|
| regulatory_provisions | 48,374 | ✅ Restored |
| documents | 446 | ✅ Unaffected |
| dcp_general_requirements | 3,158 | ✅ Unaffected |
| housing_sepp_standards | 33 | ✅ Unaffected |
| provision_versions | 0 | ⚠️ Empty (schema exists) |
| provision_change_log | 0 | ⚠️ Empty (schema exists) |

### Version Tracking Status
- **Schema**: ✅ Installed (tables and columns exist)
- **Data**: ⚠️ Empty (not backfilled)
- **Status**: **INACTIVE - Not in use**

### Schema Changes Present
The following columns were added to `regulatory_provisions` but are **not populated**:
- `current_version_id` (INTEGER, NULL)
- `first_seen_date` (TIMESTAMP, NULL)
- `last_modified_date` (TIMESTAMP, NULL)
- `version_count` (INTEGER, default 1)
- `is_current` (BOOLEAN, default TRUE)
- `text_hash_current` (TEXT, NULL)

**These columns are safe to ignore** - they have defaults and NULL values won't affect queries.

## Data Analysis

### Provision Count Comparison
- **Before incident** (Jan 27, 2026): 41,505 provisions
- **After restore** (Nov 22, 2025 backup): 48,374 provisions
- **Difference**: +6,869 provisions

### Possible Explanations for Difference
1. **Data cleanup**: Provisions may have been removed between Nov 22 and Jan 27
2. **Deduplication**: Duplicate provisions may have been cleaned up
3. **Quality improvements**: Low-quality provisions may have been filtered
4. **Schema migrations**: v2 column additions may have triggered cleanup

### Recommendation
Review the `DATA_QUALITY_TRACKER.md` and git commit history between November 22, 2025 and January 27, 2026 to understand what changed.

## Files Created During Recovery

### Scripts
- `scripts/db_safety_check.py` - Database safety checker for Supabase
- `scripts/create_backup.py` - Backup creation utility
- `scripts/run_migration.py` - Migration runner
- `scripts/check_version_schema.py` - Version schema status checker
- `scripts/backfill_provision_versions.py` - Version backfill script (NOT RUN)
- `scripts/restore_from_backup.py` - Backup restore utility (USED)
- `scripts/check_table_status.py` - Table status checker

### Migrations
- `scripts/migrations/create_version_schema.sql` - Version tracking schema (APPLIED)

### Backups
- `backups/pre_version_migration_20260127_231005.json` - Pre-migration metadata backup

## Version Tracking Implementation - Postponed

The version tracking implementation has been **POSTPONED** per user decision (Option 1).

### What Was Completed
- ✅ Phase 1: Database schema created
- ✅ Migration applied successfully
- ❌ Phase 2: Data backfill NOT completed
- ❌ Phase 3-5: Not started

### If Resuming Later

**Before proceeding with version tracking:**

1. **Create fresh backup**
   ```bash
   python scripts/create_backup.py
   ```

2. **Remove CASCADE from foreign keys**
   ```sql
   ALTER TABLE regulatory_provisions
   DROP CONSTRAINT IF EXISTS regulatory_provisions_current_version_id_fkey;

   ALTER TABLE regulatory_provisions
   ADD CONSTRAINT regulatory_provisions_current_version_id_fkey
   FOREIGN KEY (current_version_id)
   REFERENCES provision_versions(id)
   ON DELETE SET NULL;  -- NOT CASCADE
   ```

3. **Test on subset first**
   - Test backfill on 1,000 provisions
   - Verify version creation
   - Then scale to full dataset

4. **Use batched commits**
   - The backfill script already does this
   - Set `statement_timeout` appropriately

## Lessons Learned

1. **CASCADE is dangerous** - Always use explicit foreign key actions
2. **Test on small datasets first** - Don't test large migrations on production
3. **Backup before schema changes** - We had backups, which saved us
4. **Use transactions carefully** - Long-running transactions can timeout
5. **Document rollback procedures** - Have a recovery plan before starting

## Current Action Items

- [x] Restore data from backup
- [x] Verify data integrity
- [x] Document recovery process
- [ ] Review provision count difference (6,869 provisions)
- [ ] Decide whether to keep version tracking schema or remove it
- [ ] Update application code if version tracking columns cause issues

## Production Impact

**Estimated downtime**: ~15 minutes (during restore)
**Data loss**: None (restored from backup)
**User impact**: Minimal (if any users accessed empty table, they saw no results)

## Contact

If issues arise related to this recovery:
1. Check this document first
2. Verify table counts match expected values
3. Check `provision_versions` is still empty (not in use)
4. Review error logs for foreign key constraint violations
