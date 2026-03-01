# Frontend Update Plan for Canonical Provisions

## Files That Need Updating

Based on grep analysis, the following files query `regulatory_provisions`:

### Core Database Clients (HIGH PRIORITY)
1. ✅ `lib/database/postgres-compliance-client.ts` - 2 queries (lines 130, 200)
2. ✅ `lib/database/client.ts` - 6 queries (lines 65, 90, 116, 153, 187, 350)
3. ⚠️ `lib/database/postgres-client.ts` - Uses `regulatory_provisions_clean` (different table?)
4. ⚠️ `lib/database/prp-k7-client.ts` - Uses `regulatory_provisions_clean_clean` (different table?)

### API Routes (HIGH PRIORITY)
5. ✅ `app/api/compliance/constraints/route.ts` - 2 JOINs (lines 107, 341)
6. ✅ `app/api/clause/[id]/route.ts` - 1 query (line 34)
7. ✅ `app/api/dcp/full-text/route.ts` - 2 queries (lines 45, 88)
8. ✅ `app/api/provisions/[id]/complete/route.ts` - 1 query (line 129)

### Specialized Clients (MEDIUM PRIORITY)
9. ⚠️ `lib/database/specialized/version-client.ts`
10. ⚠️ `lib/database/specialized/provision-search-client.ts`
11. ⚠️ `lib/database/specialized/live-compliance-client.ts`

### Test Files (LOW PRIORITY)
12. `test-prp-a2.js`
13. `check_postgres_zones.js`
14. `analyze_r_zones.js`

## Update Strategy

### Option A: Replace table name (Simple)
```sql
-- Before
FROM regulatory_provisions

-- After
FROM regulatory_provisions_canonical
```

### Option B: Add WHERE filter (Explicit)
```sql
-- Before
FROM regulatory_provisions
WHERE ...

-- After
FROM regulatory_provisions
WHERE is_canonical = TRUE
  AND ...
```

### Option C: Hybrid (Recommended)
- Use view for simple SELECTs
- Add WHERE for complex JOINs (better query planner optimization)

## Implementation

I'll update files in priority order:
1. Core clients first (affects all queries)
2. API routes second (user-facing)
3. Specialized clients third
4. Test files last (optional)
