# Phase 1 Migration: Mark True Duplicates

## Overview

This migration fixes the duplicate provisions problem by marking true duplicates without deleting any data.

**Status:** ✅ SAFE & REVERSIBLE
**Risk Level:** 0/10 (No data loss, no breaking changes)
**Impact:** Reduces query results by ~10% (2,319 duplicates marked)

---

## What This Does

### Before Migration
```
22,648 provisions in database
- Many are exact duplicates (same text, same document, same ref_number)
- Queries return duplicates, confusing users
- No way to distinguish canonical vs duplicate records
```

### After Migration
```
22,648 provisions still in database (NO deletions)
- 20,329 marked as canonical (is_canonical = TRUE)
- 2,319 marked as duplicates (is_canonical = FALSE)
- Duplicates linked to canonical via canonical_provision_id
- Queries filter to canonical only
```

---

## Database Changes

### New Columns Added

| Column | Type | Purpose |
|--------|------|---------|
| `is_canonical` | BOOLEAN | TRUE = keep this record, FALSE = duplicate |
| `canonical_provision_id` | INT | Points to the canonical record (for duplicates) |
| `text_hash` | TEXT | MD5 hash of provision_text (for deduplication) |
| `migration_phase` | TEXT | Tracks which migration phase marked this record |

### New View Created

```sql
CREATE VIEW regulatory_provisions_canonical AS
SELECT * FROM regulatory_provisions WHERE is_canonical = TRUE;
```

Use this view for backward compatibility - it automatically filters to canonical provisions only.

---

## How to Run

### Step 1: Run Migration Script

```bash
python run_phase1_migration.py
```

The script will:
1. ✅ Check prerequisites
2. ✅ Create full database backup
3. ✅ Run migration SQL
4. ✅ Validate results
5. ✅ Print summary

**Expected output:**
```
================================================================================
PHASE 1 MIGRATION: MARK TRUE DUPLICATES
================================================================================

STEP 0: PRE-FLIGHT CHECKS
✓ Table 'regulatory_provisions' exists
✓ No conflicting columns found
✓ Found 22,648 provisions to process

Ready to proceed? Type 'yes' to continue: yes

STEP 1: CREATE BACKUP
→ Creating backup: backups/pre_phase1_migration_20251001_123456.sql
✓ Backup created: backups/pre_phase1_migration_20251001_123456.sql (45.2 MB)

STEP 2: RUN MIGRATION
→ Executing 12 SQL statements...
✓ Migration completed successfully

STEP 3: VALIDATE RESULTS
  Canonical        : 20,329 (89.8%)
  Duplicate        :  2,319 (10.2%)
✓ No orphaned duplicates (expected: 0, found: 0)
✓ All 22,648 provisions have text_hash
✓ Validation complete

MIGRATION COMPLETE
What changed:
  • Added 4 new columns
  • Marked ~2,319 provisions as duplicates
  • NO data was deleted

Backup location: backups/pre_phase1_migration_20251001_123456.sql
```

### Step 2: Update Frontend Queries

**Option A: Add WHERE clause (minimal change)**

```typescript
// Before
const query = `
  SELECT * FROM regulatory_provisions
  WHERE document_id = $1;
`;

// After
const query = `
  SELECT * FROM regulatory_provisions
  WHERE document_id = $1
    AND is_canonical = TRUE;  -- ✅ Add this line
`;
```

**Option B: Use the view (cleaner)**

```typescript
// Before
const query = `
  SELECT * FROM regulatory_provisions
  WHERE document_id = $1;
`;

// After
const query = `
  SELECT * FROM regulatory_provisions_canonical
  WHERE document_id = $1;
`;
```

**Files to Update:**

1. `frontend-nextjs/lib/database/compliance-client.ts`
2. `frontend-nextjs/lib/database/postgres-compliance-client.ts`
3. Any other files with `SELECT * FROM regulatory_provisions`

Search for:
```bash
grep -r "FROM regulatory_provisions" frontend-nextjs/
```

### Step 3: Test

```bash
# Start dev server
cd frontend-nextjs
npm run dev

# Test provision queries return correct count
# Before: 22,648 provisions
# After: 20,329 provisions (no duplicates)
```

---

## Rollback (If Needed)

If something goes wrong:

```bash
python rollback_phase1.py
```

This will:
- ✅ Drop all Phase 1 columns
- ✅ Drop indexes and constraints
- ✅ Restore database to pre-migration state

**OR** restore from backup:

```bash
psql -U postgres -d nsw_planning < backups/pre_phase1_migration_YYYYMMDD_HHMMSS.sql
```

---

## Verification Queries

After migration, run these queries to verify:

### 1. Count Canonical vs Duplicates

```sql
SELECT
  is_canonical,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (), 1) as percentage
FROM regulatory_provisions
GROUP BY is_canonical;
```

**Expected:**
```
 is_canonical | count  | percentage
--------------+--------+------------
 TRUE         | 20,329 |       89.8
 FALSE        |  2,319 |       10.2
```

### 2. Sample Duplicate Groups

```sql
SELECT
  canonical.ref_number,
  LEFT(canonical.provision_text, 80) as text,
  COUNT(*) as duplicate_count
FROM regulatory_provisions dup
JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
WHERE dup.is_canonical = FALSE
GROUP BY canonical.id, canonical.ref_number, canonical.provision_text
ORDER BY COUNT(*) DESC
LIMIT 10;
```

### 3. Check for Orphaned Duplicates

```sql
SELECT COUNT(*)
FROM regulatory_provisions dup
LEFT JOIN regulatory_provisions canonical ON dup.canonical_provision_id = canonical.id
WHERE dup.is_canonical = FALSE
  AND (canonical.id IS NULL OR canonical.is_canonical = FALSE);
```

**Expected:** `0` (no orphaned duplicates)

---

## FAQ

### Q: Will this break existing queries?

**A:** No, but queries will return duplicates until you add `WHERE is_canonical = TRUE`. Existing queries continue to work unchanged.

### Q: Can I still access duplicate records?

**A:** Yes! All records are preserved. Query with `WHERE is_canonical = FALSE` to see duplicates.

### Q: Which duplicate is kept as canonical?

**A:** The **oldest** record (earliest `created_at`, lowest `id`). This preserves the original extraction.

### Q: What about the other duplicate types (subsection collapse, cross-refs)?

**A:** Those are Phase 2 & 3. This migration only handles TRUE duplicates (same text, same doc, same ref).

### Q: Can I run this multiple times?

**A:** Yes, it's idempotent. Re-running won't cause issues (columns already exist checks are in place).

---

## Next Steps After Phase 1

Once Phase 1 is stable, consider:

**Phase 2:** Fix cross-reference arrows in `ref_number`
- Complexity: Medium
- Risk: 3/10
- Impact: Cleans 2,645 ref_numbers, reveals 297 more duplicates

**Phase 3:** Fix subsection collapse
- Complexity: High
- Risk: 8/10
- Impact: Differentiates 1,735 collapsed ref_numbers
- **Requires:** Re-parsing PDFs or manual differentiation

---

## Support

If you encounter issues:

1. Check backup was created successfully
2. Run validation queries above
3. Check `rollback_phase1.py` if you need to undo changes
4. Restore from backup if needed

**Backup location:** `backups/pre_phase1_migration_[timestamp].sql`
