# Precinct Requirements Bug - Root Cause and Fix

**Date:** 2025-11-03
**Priority:** P0 CRITICAL - Core functionality broken

## The Bug

**Symptom:** API returns `precinct_provisions: null` even when precinct requirements exist in database

**Affected Addresses:**
- 180 Addison Road, Marrickville (has 7 precinct requirements in DB, API returns 0)
- 30 Hubert Street, Leichhardt (has 9 precinct requirements in DB, API returns 0)

## Root Cause

**File:** `frontend-nextjs/app/api/compliance/dcp-complete/route.ts`
**Lines:** 1035-1040, 1143

### The Logic Error:

```typescript
// Line 1028-1033: Fetch precinct requirements
const precinctRequirementsResult = await query<PrecinctRequirement>(
  precinctRequirementsQuery,
  [detectedPrecinctId]
);
precinctRequirements = precinctRequirementsResult.rows; // POPULATED WITH DATA

// Line 1035-1040: Set precinctInfo ONLY if provisions exist
if (precinctProvisions.length > 0) {  // ← BUG: WRONG CHECK
  precinctInfo = {
    precinct_id: precinctProvisions[0].precinct_id,
    precinct_name: precinctProvisions[0].precinct_name
  };
}
// If precinctProvisions is empty, precinctInfo stays NULL

// Line 1143: Response depends on precinctInfo
precinct_provisions: precinctInfo ? {  // ← BUG: NULL even when requirements exist!
  ...
  requirements: precinctRequirements,  // Has data but never returned!
} : null
```

### Why This Happens:

1. **Two separate queries:**
   - `dcp_precinct_provisions` - Raw text provisions from PDF extraction
   - `dcp_precinct_requirements` - Categorized requirements from LLM processing

2. **The bug:** `precinctInfo` checks if `precinctProvisions` (raw text) exists
3. **Reality:** Many precincts have requirements but NO raw provisions
4. **Result:** `precinctInfo = null`, so response returns `precinct_provisions: null`
5. **Consequence:** Requirements are fetched but NEVER returned to user!

## Database Evidence

### 180 Addison Road (Henson Park Precinct 13):
```
Precinct ID: 13_
precinctProvisions: 0 rows (no raw text)
precinctRequirements: 7 rows (has categorized data!)
  - 4 character requirements
  - 1 landscaping requirement
  - 1 parking requirement
  - 1 front setback requirement
```

### 30 Hubert Street (West Leichhardt):
```
Precinct ID: C2.2.3.2
precinctProvisions: 0 rows (no raw text)
precinctRequirements: 9 rows (has categorized data!)
  - 3 building height requirements
  - 4 character requirements
  - 2 other requirements
```

## The Fix

**Change the condition from checking provisions to checking requirements:**

```typescript
// BEFORE (BROKEN):
if (precinctProvisions.length > 0) {
  precinctInfo = {
    precinct_id: precinctProvisions[0].precinct_id,
    precinct_name: precinctProvisions[0].precinct_name
  };
}

// AFTER (FIXED):
if (precinctRequirements.length > 0 || precinctProvisions.length > 0) {
  // Get info from whichever source has data
  const source = precinctRequirements.length > 0
    ? precinctRequirements[0]
    : precinctProvisions[0];

  precinctInfo = {
    precinct_id: source.precinct_id,
    precinct_name: source.precinct_name
  };
}
```

**Alternative simpler fix (use detectedPrecinctId which we already have):**

```typescript
// AFTER (SIMPLER):
if (precinctRequirements.length > 0 || precinctProvisions.length > 0) {
  precinctInfo = {
    precinct_id: detectedPrecinctId!,  // Already detected from spatial query
    precinct_name: detectedNeighbourhoodName || precinctRequirements[0]?.precinct_name || precinctProvisions[0]?.precinct_name
  };
}
```

## Expected Impact

### Before Fix:
- 180 Addison Road: 0 precinct requirements
- 30 Hubert Street: 0 precinct requirements
- ALL precinct addresses: Missing precinct-specific controls

### After Fix:
- 180 Addison Road: 7 precinct requirements ✓
- 30 Hubert Street: 9 precinct requirements ✓
- ALL precinct addresses: Complete precinct-specific controls returned

## Additional Issues Found

### Issue #2: Ashfield General Requirements Still Returns 0

**File:** Same file, line 844
**Problem:** Still has old zone filtering bug (only checks `= ANY`, not NULL/empty/'ALL')

**Fix:** Apply same 3-convention fix we did to capacity API:

```typescript
// Line 844 CURRENT (BROKEN):
AND $2 = ANY(dgr.applicable_zones)

// SHOULD BE (FIXED):
AND (
  $2 = ANY(dgr.applicable_zones)
  OR dgr.applicable_zones IS NULL
  OR dgr.applicable_zones = '{}'
  OR 'ALL' = ANY(dgr.applicable_zones)
)
```

## Implementation Priority

**P0 (This session):**
1. Fix precinct requirements bug (lines 1035-1040)
2. Test 180 Addison Road and 30 Hubert Street
3. Verify precinct requirements now returned

**P1 (Next):**
1. Fix Ashfield zone filtering (line 844)
2. Apply to all zone filtering locations in dcp-complete
3. Comprehensive test of all councils

## Files to Modify

1. `frontend-nextjs/app/api/compliance/dcp-complete/route.ts`
   - Lines 1035-1040: Fix precinctInfo condition
   - Line 844: Fix zone filtering for Ashfield
   - Lines 199, 257: Review zone filtering for precinct provisions (may also be broken)
