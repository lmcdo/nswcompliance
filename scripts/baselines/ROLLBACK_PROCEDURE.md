# Cross-Reference Resolution — Rollback Procedure

**Created:** 2026-03-16T15:30:43.155894
**Backup table:** `regulatory_provisions_backup_20260316_pre_xref`
**Row count at backup time:** 34,911

## When to rollback

- Resolution pipeline produced wrong resolutions at scale (>2% false positive rate)
- Schema change caused unexpected data corruption
- QA check on eval set fails after enrichment run

## Rollback steps

### Option A: Revert v2_extracted_rules only (preferred)

If resolution data was appended to the `references` array within `v2_extracted_rules`,
revert just that field:

```sql
-- Verify counts first
SELECT COUNT(*) FROM regulatory_provisions_backup_20260316_pre_xref;
SELECT COUNT(*) FROM regulatory_provisions;

-- Revert (SLOW — ~47k rows, run during off-peak)
UPDATE regulatory_provisions r
SET v2_extracted_rules = b.v2_extracted_rules
FROM regulatory_provisions_backup_20260316_pre_xref b
WHERE r.id = b.id;

-- Verify
SELECT COUNT(*) FROM regulatory_provisions WHERE v2_extracted_rules IS NOT NULL;
```

### Option B: Drop new table(s) only

If resolution data was stored in a new `provision_cross_refs` table:

```sql
DROP TABLE IF EXISTS provision_cross_refs;
-- v2_extracted_rules is untouched, no provision data changed
```

### Option C: Full table restore (nuclear option)

Only if schema columns were added AND data was corrupted:

```sql
-- Drop and recreate from backup (extreme — loses any other changes since backup)
-- NEVER run without explicit confirmation
DROP TABLE regulatory_provisions;
ALTER TABLE regulatory_provisions_backup_20260316_pre_xref RENAME TO regulatory_provisions;
```

**Option C requires re-applying any unrelated changes made after 2026-03-16.**
Do NOT use Option C without checking git log for any other DB changes made after this backup.

## Verify rollback succeeded

```sql
SELECT v2_extraction_status, COUNT(*)
FROM regulatory_provisions
GROUP BY 1;
-- Should match baseline_metrics.json extraction_status values exactly
```

## Keep the backup table

Do NOT drop `regulatory_provisions_backup_20260316_pre_xref` until cross-ref resolution is:
- Fully deployed and validated
- QA report signed off
- At least 30 days of production running without incidents

```sql
-- Only when safe to drop:
DROP TABLE regulatory_provisions_backup_20260316_pre_xref;
```
