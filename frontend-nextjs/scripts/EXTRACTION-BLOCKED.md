# SEPP Extraction - BLOCKED on Database Persistence Issue

**Date:** 2026-02-20
**Status:** ❌ BLOCKED - Data not persisting to database

## Problem

Extraction script runs successfully, INSERTs report success, but **zero records appear in database**.

## Reproduction

```bash
cd frontend-nextjs/scripts
npm exec tsx extract-sepp-structured.ts -- --limit=3
# Output shows: "✅ Extracted X requirement(s)" and "💾 Saved X requirement(s)"
# But: SELECT COUNT(*) FROM sepp_structured_requirements returns 0
```

## What's Been Fixed

1. ✅ Renamed conflicting table (`sepp_curated_requirements`)
2. ✅ Created proper schema (29 columns)
3. ✅ Converted script from JS/CommonJS to TS/ES modules
4. ✅ Fixed entry point (`require.main === module` → direct `main()` call)
5. ✅ Made `requirement_category` and `applies_to` nullable
6. ✅ Verified INSERTs report `rowCount: 1`

## What's Still Broken

**Symptom:** Data vanishes after INSERT
- `pool.query(insertQuery, [...])` returns `{ rowCount: 1 }`
- Immediate `SELECT COUNT(*)` returns `0`
- Manual test INSERTs in isolation work fine
- Suggests transaction/connection pooling issue

## Hypothesis

Possible causes:
1. **Transaction mode mismatch** - Using port 5432 (session) instead of 6543 (transaction)?
2. **Connection pool isolation** - Each query using different connection?
3. **Implicit rollback** - Some error causing silent rollback?
4. **Supabase pooler behavior** - Pooler not committing transactions?

## Next Steps

1. **Test with direct connection** (not pooled) - Does data persist?
2. **Add explicit COMMIT** - Force transaction commit after each INSERT?
3. **Check Supabase logs** - Are transactions being rolled back server-side?
4. **Use port 6543** - Switch to transaction mode as pool-manager.ts comment suggests?

## Files Modified

- `scripts/extract-sepp-structured.ts` - Converted to TypeScript, fixed entry point
- Schema migration - Created `sepp_structured_requirements` table with 29 columns
- Made `requirement_category` and `applies_to` nullable

## Cost Impact

Multiple test runs have called Anthropic API without persisting results. Estimate: 10-20 provisions × $0.05 = ~$0.50-$1.00 wasted.

**HALT extraction until persistence issue resolved.**
