# LGA Case Mismatch - Impact Assessment & Fix Plan

**Date**: 2025-11-03
**Issue**: Database has mixed case LGA values (`'INNER WEST'` vs `'Inner West'`) causing spatial queries to fail
**Impact**: Users cannot get precinct-specific setbacks - spatial filtering returns 0 results

---

## Impact Assessment Results

### Tables Affected (18 total with `lga` column)

#### **CRITICAL - User-Facing Tables** (must fix)
1. **`dcp_precinct_boundaries`** - 71 rows `'INNER WEST'`, 1 row `'INNER WESTR'` (typo)
   - **Impact**: Spatial queries fail, no precinct filtering works
   - **User Impact**: HIGH - breaks coordinates-based precinct lookup

2. **`dcp_precinct_requirements`** - 893 rows `'Inner West'` (correct)
   - **Impact**: None - already correct
   - **User Impact**: None

3. **`dcp_general_requirements`** - 4460 rows `'Inner West'`, 93 rows `'INNER WEST'`
   - **Impact**: 93 rows unreachable by queries using `'Inner West'`
   - **User Impact**: MEDIUM - some general provisions missing

4. **`dcp_general_provisions`** - 1040 rows `'Inner West'`, 132 rows `'INNER WEST'`
   - **Impact**: 132 rows unreachable
   - **User Impact**: MEDIUM - some provisions missing

5. **`dcp_all_provisions`** - 1040 rows `'Inner West'`, 249 rows `'INNER WEST'`
   - **Impact**: 249 rows unreachable
   - **User Impact**: MEDIUM - some provisions missing

6. **`lep_development_type_clauses`** - 29 rows `'Inner West'` (correct)
   - **Impact**: None
   - **User Impact**: None

7. **`lep_land_use_table`** - 390 rows `'Inner West'` (correct)
   - **Impact**: None
   - **User Impact**: None

#### **NON-CRITICAL - Backup/Archive Tables**
- `dcp_precinct_boundaries_backup_polygon` - 45 rows `'INNER WEST'`, 1 row `'INNER WESTR'`
- `dcp_general_requirements_backup_20251030` - mixed
- `dcp_general_provisions_backup_r1_fix` - 130 rows `'INNER WEST'`
- `dcp_general_provisions_corrupted_f1_backup` - 7 rows `'INNER WEST'`
- `dcp_general_requirements_old_broad_linking` - 189 rows `'INNER WEST'`
- `dcp_precinct_provisions` - 117 rows `'INNER WEST'`

**Decision**: Fix backups for data integrity, but not critical for users

---

## Affected User Queries

### API Routes Using `WHERE lga = ...`

1. **`/api/compliance/dcp-complete/route.ts`** (8 queries)
   - Lines: 198, 219, 238, 256, 843, 871, 897, 923
   - Queries: `dcp_general_provisions`, `dcp_general_requirements`
   - **Impact**: Missing 93-249 provisions depending on query

2. **`/api/capacity/calculate/route.ts`** (5+ queries)
   - Precinct boundaries spatial query
   - General requirements queries
   - **Impact**: CRITICAL - spatial filtering completely broken

3. **`/api/permissibility/check/route.ts`**
   - LEP land use table queries
   - **Impact**: None - LEP tables already correct

### Current Behavior

**Before Fix:**
```typescript
// User query with coordinates for Marrickville address
WHERE lga = 'Inner West'  // From normalized input
// Database has lga = 'INNER WEST'
// Result: 0 rows returned ❌
```

**After Fix:**
```typescript
// User query with coordinates
WHERE lga = 'Inner West'
// Database now has lga = 'Inner West'
// Result: 72 precinct boundaries returned ✅
```

---

## Fix Strategy

### Option A: Normalize Database (RECOMMENDED)

**Pros:**
- ✅ Permanent fix - no ongoing case handling needed
- ✅ Consistent with other tables (LEP, most DCP tables already use Title Case)
- ✅ No query performance overhead
- ✅ Simple SQL UPDATE statements

**Cons:**
- ⚠️ Requires database backup first
- ⚠️ Must update 12 tables (including backups)

### Option B: Case-Insensitive Queries

**Pros:**
- ✅ No database changes needed
- ✅ Handles future case mismatches

**Cons:**
- ❌ Performance overhead on every query (`UPPER(lga) = UPPER($1)`)
- ❌ Must update every query in codebase
- ❌ Doesn't fix underlying data quality issue
- ❌ Index on `lga` column becomes useless

**DECISION: Choose Option A** - normalize database to Title Case

---

## Implementation Plan

### Phase 1: Backup (5 minutes)

```bash
cd "C:\Users\lawre\Downloads\solvyra\projects\compliance engine\compliance-engine"

# Create timestamped backup
pg_dump -h localhost -U postgres -d nsw_planning \
  -t dcp_precinct_boundaries \
  -t dcp_general_requirements \
  -t dcp_general_provisions \
  -t dcp_all_provisions \
  > backups/lga_case_fix_backup_$(date +%Y%m%d_%H%M%S).sql
```

### Phase 2: Fix Critical Tables (2 minutes)

```sql
BEGIN;

-- 1. Fix precinct boundaries (CRITICAL - enables spatial filtering)
UPDATE dcp_precinct_boundaries
SET lga = 'Inner West'
WHERE lga ILIKE 'inner west%';

-- 2. Fix typo
UPDATE dcp_precinct_boundaries
SET lga = 'Inner West'
WHERE lga = 'INNER WESTR';

-- 3. Fix general requirements (93 rows missing from queries)
UPDATE dcp_general_requirements
SET lga = 'Inner West'
WHERE lga = 'INNER WEST';

-- 4. Fix general provisions (132 rows missing)
UPDATE dcp_general_provisions
SET lga = 'Inner West'
WHERE lga = 'INNER WEST';

-- 5. Fix all provisions (249 rows missing)
UPDATE dcp_all_provisions
SET lga = 'Inner West'
WHERE lga = 'INNER WEST';

-- Verify
SELECT 'dcp_precinct_boundaries' as table_name, lga, COUNT(*)
FROM dcp_precinct_boundaries GROUP BY lga
UNION ALL
SELECT 'dcp_general_requirements', lga, COUNT(*)
FROM dcp_general_requirements GROUP BY lga
UNION ALL
SELECT 'dcp_general_provisions', lga, COUNT(*)
FROM dcp_general_provisions GROUP BY lga
UNION ALL
SELECT 'dcp_all_provisions', lga, COUNT(*)
FROM dcp_all_provisions GROUP BY lga
ORDER BY table_name, lga;

-- If verification looks good:
COMMIT;
-- If issues found:
-- ROLLBACK;
```

### Phase 3: Fix Backup Tables (1 minute)

```sql
BEGIN;

UPDATE dcp_precinct_boundaries_backup_polygon
SET lga = 'Inner West'
WHERE lga ILIKE 'inner west%';

UPDATE dcp_general_requirements_backup_20251030
SET lga = 'Inner West'
WHERE lga = 'INNER WEST';

UPDATE dcp_general_provisions_backup_r1_fix
SET lga = 'Inner West'
WHERE lga = 'INNER WEST';

UPDATE dcp_general_provisions_corrupted_f1_backup
SET lga = 'Inner West'
WHERE lga = 'INNER WEST';

UPDATE dcp_general_requirements_old_broad_linking
SET lga = 'Inner West'
WHERE lga = 'INNER WEST';

UPDATE dcp_precinct_provisions
SET lga = 'Inner West'
WHERE lga = 'INNER WEST';

COMMIT;
```

### Phase 4: Verification (2 minutes)

Run the comprehensive end-to-end test:
```bash
python test_complete_pipeline_e2e.py
```

Expected results:
- ✅ Precinct boundaries: 72 total, 72 with geometry
- ✅ Spatial query finds correct precinct for test addresses
- ✅ General provisions queries return all rows
- ✅ Integration checks: 3/3 passed

### Phase 5: Test Real User Flow (3 minutes)

Test in browser:
1. Navigate to `/assessment`
2. Enter address: "180 Addison Road, Marrickville"
3. Select development type
4. Click "Calculate Capacity"
5. **Expected**: Should show precinct-specific setbacks if address is in a precinct

---

## Rollback Plan

If any issues occur:

```bash
# Restore from backup
psql -h localhost -U postgres -d nsw_planning < backups/lga_case_fix_backup_YYYYMMDD_HHMMSS.sql
```

---

## Success Criteria

1. ✅ All `lga` columns in user-facing tables use `'Inner West'` (Title Case)
2. ✅ No rows with `'INNER WESTR'` typo
3. ✅ Spatial queries return 72 precinct boundaries
4. ✅ Test addresses find correct precincts
5. ✅ General provisions queries return all rows (no missing 93/132/249 rows)
6. ✅ End-to-end test passes with 3/3 integration checks

---

## Estimated Time

- Total: **15 minutes**
  - Backup: 5 min
  - Fix critical tables: 2 min
  - Fix backup tables: 1 min
  - Verification: 2 min
  - User flow test: 3 min
  - Buffer: 2 min

---

## Risk Assessment

**Risk Level**: LOW

**Why Low Risk:**
- ✅ Simple string replacement (`'INNER WEST'` → `'Inner West'`)
- ✅ Wrapped in transaction (can ROLLBACK)
- ✅ Backup created before changes
- ✅ Only affects one LGA (Inner West)
- ✅ No schema changes, no data loss
- ✅ Aligns with existing convention (most tables already use Title Case)

**Risks:**
- ⚠️ If queries have hardcoded `'INNER WEST'` somewhere, they'll break
  - **Mitigation**: All API routes use normalized input from user (Title Case)
  - **Mitigation**: Grep confirmed no hardcoded uppercase LGA in TypeScript
