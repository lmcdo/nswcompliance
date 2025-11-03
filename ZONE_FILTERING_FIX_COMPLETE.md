# Zone Filtering Fix - Complete Implementation

**Date:** 2025-11-03
**Status:** ✅ COMPLETE - All three councils now return 100% of setback provisions

## Problem

Zone filtering logic in `/api/capacity/calculate/route.ts` was dropping 95-98% of setback provisions because it only handled one convention for "applies to all zones":

- **Old query:** `WHERE (zone = ANY(applicable_zones) OR applicable_zones IS NULL)`
- **Result:** Only provisions with NULL zones or explicit zone arrays were returned
- **Impact:**
  - Ashfield: 1/20 provisions (5%)
  - Leichhardt: 1/39 provisions (3%)
  - Marrickville: 2/102 provisions (2%)

## Root Cause

Database used **3 different conventions** for marking provisions as "applies to all zones":
1. `applicable_zones = NULL` (Leichhardt mostly)
2. `applicable_zones = '{}'` (empty array - Marrickville mostly)
3. `applicable_zones = ['ALL']` (Ashfield - 586 provisions)

## Solution

### 1. Updated API Query Logic
**File:** `frontend-nextjs/app/api/capacity/calculate/route.ts:295-303`

```typescript
WHERE lga = $1
  AND former_council = $2
  AND requirement_text ILIKE '%setback%'
  AND (
    $3 = ANY(applicable_zones)     -- Zone-specific provisions
    OR applicable_zones IS NULL     -- Universal (NULL = applies to all)
    OR applicable_zones = '{}'      -- Universal (empty array = applies to all)
    OR 'ALL' = ANY(applicable_zones)  -- Universal (explicit 'ALL' marker)
  )
```

### 2. Fixed Ashfield Data
**File:** `fix_ashfield_zone_tags.py`

Converted 586 Ashfield provisions from `applicable_zones = ['ALL']` to `applicable_zones = '{}'` for consistency.

```sql
UPDATE dcp_general_requirements
SET applicable_zones = '{}'
WHERE lga = 'Inner West'
  AND former_council = 'Ashfield'
  AND applicable_zones = ARRAY['ALL']
```

### 3. Fixed LGA Case Mismatch
**File:** `fix_lga_case_mismatch.py`

Normalized 879 rows from `'INNER WEST'` → `'Inner West'` across 9 tables to enable spatial queries.

## Results

### Before Fix
| Council | Returned | Total | Coverage |
|---------|----------|-------|----------|
| Ashfield | 1 | 20 | 5% |
| Leichhardt | 1 | 39 | 3% |
| Marrickville | 2 | 102 | 2% |

### After Fix
| Council | Returned | Total | Coverage |
|---------|----------|-------|----------|
| Ashfield | 20 | 20 | **100%** ✅ |
| Leichhardt | 39 | 39 | **100%** ✅ |
| Marrickville | 102 | 102 | **100%** ✅ |

## API Response Samples

### Ashfield (R2 zone)
Returns 20 provisions including:
- **1 numeric:** 0.9m side setback for dwelling houses
- **19 text guidance:** Heritage setbacks, character-based requirements

### Leichhardt (R2 zone)
Returns 39 provisions including:
- **Multiple numeric:** 47.2m, 43.6m, 4m setbacks with height controls
- **Text guidance:** Neighbourhood-specific requirements

### Marrickville (R2 zone)
Returns 102 provisions including:
- **Multiple numeric:** 900mm side setbacks (common requirement)
- **Text guidance:** Character-based, prevailing pattern requirements

## Files Modified

### API Routes
1. `frontend-nextjs/app/api/capacity/calculate/route.ts`
   - Lines 295-303: Added 3-convention zone filtering logic
   - Lines 195: Fixed `boundary_geom` → `boundary` column name

### Database Fixes
1. `fix_ashfield_zone_tags.py` - Convert ['ALL'] to empty array (586 rows)
2. `fix_lga_case_mismatch.py` - Normalize 'INNER WEST' to 'Inner West' (879 rows)

### Verification Scripts
1. `analyze_zone_filtering_issue.py` - Diagnosed the problem
2. `verify_zone_fix_complete.py` - Confirmed 100% coverage

## Technical Details

### PostgreSQL Array Operators
- `zone = ANY(applicable_zones)` - Check if zone exists in array
- `applicable_zones IS NULL` - Check for NULL value
- `applicable_zones = '{}'` - Check for empty array

### Why 3 Conventions Existed
1. **NULL:** Original extraction approach for general provisions
2. **Empty array:** Explicit "no zone filtering" marker
3. **['ALL']:** Extraction script interpretation during Ashfield import

### Future Prevention
When extracting provisions, consistently use **empty array `'{}'`** for universal applicability instead of mixing NULL and 'ALL' markers.

## Verification

Run `verify_zone_fix_complete.py` to confirm:
```bash
python verify_zone_fix_complete.py
```

Expected output:
```
Ashfield: 20/20 provisions (100% coverage)
Leichhardt: 39/39 provisions (100% coverage)
Marrickville: 102/102 provisions (100% coverage)
```

## Impact on User Experience

**Before:** Users saw 1-2 provisions for any residential address, making the tool appear incomplete.

**After:** Users now see comprehensive setback guidance:
- All numeric setbacks in the database
- All text-based character requirements
- Complete neighbourhood-specific guidance
- Proper fallback hierarchy: precinct → general → guidance

## Related Work

This fix builds on the earlier coordinates flow fix:
- `assessment/page.tsx` - Pass coordinates from PropertySearch
- `CapacityCalculator.tsx` - Forward coordinates to API
- Spatial filtering in API - Use coordinates for precinct matching

Together, these provide:
1. **Spatial precision:** Correct precinct identification
2. **Complete data:** All applicable provisions returned
3. **Proper hierarchy:** Precinct-specific → General → Fallback guidance
