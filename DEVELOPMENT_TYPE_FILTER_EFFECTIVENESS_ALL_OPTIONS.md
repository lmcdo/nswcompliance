# Development Type Filter Effectiveness - All Dropdown Options

**Analysis Date:** 2025-11-10
**Question:** How effective is the filter for ALL 8 development types in the dropdown?

---

## Dropdown Options (8 Total)

1. **Dwelling House** (single detached home)
2. **Secondary Dwelling** (granny flat)
3. **Shop Top Housing**
4. **Multi Dwelling Housing**
5. **Residential Flat Building**
6. **Boarding House**
7. **Child Care Centre**
8. **Commercial Premises**

---

## Filter Effectiveness by Development Type

### Category 1: RESIDENTIAL TYPES (6 options)

**Recognized residential types in filter:**
- `dwelling_house` ✅
- `secondary_dwelling` ✅
- `dual_occupancy` (not in dropdown, but supported)
- `multi_dwelling_housing` (close match to `multi_dwelling`)
- `residential_flat_building` (close match to `residential_flat`)
- `manor_house` (not in dropdown)
- `attached_dwelling` (not in dropdown)
- `semi_detached_dwelling` (not in dropdown)

#### 1. Dwelling House (single detached home)
**Dev Type:** `dwelling_house`
**Category Mapping:** → Residential
**Filter Status:** ✅ FULLY SUPPORTED

**What Gets Filtered Out:**
- Commercial signage (70% confidence)
- Loading docks (70% confidence)
- Outdoor dining areas (70% confidence)
- Shop fronts (70% confidence)
- Commercial premises controls (70% confidence)

**Expected Removal Rate:** 3-8%
- **Low rate because:** Most DCP controls are genuinely universal (setbacks, heritage, parking)
- **Real-world example:** Leichhardt dwelling house: 861 → 830 (3.6% removal)

**Effectiveness:** ⭐⭐⭐⭐ (4/5)
- Excellent at removing obvious commercial requirements
- Conservative approach keeps borderline cases (good for compliance)

---

#### 2. Secondary Dwelling (granny flat)
**Dev Type:** `secondary_dwelling`
**Category Mapping:** → Residential
**Filter Status:** ✅ FULLY SUPPORTED

**What Gets Filtered Out:**
- Same as Dwelling House (commercial signage, loading docks, etc.)

**Expected Removal Rate:** 3-8%

**Effectiveness:** ⭐⭐⭐⭐ (4/5)
- Same filtering logic as dwelling house
- Granny flats have similar requirements to main dwellings

---

#### 3. Shop Top Housing
**Dev Type:** `shop_top_housing`
**Category Mapping:** → ❌ UNKNOWN (not in RESIDENTIAL_DEV_TYPES list!)
**Filter Status:** ⚠️ PARTIALLY SUPPORTED

**Critical Issue:**
- `shop_top_housing` is NOT in the `RESIDENTIAL_DEV_TYPES` array
- Filter will treat this as `unknown` category
- **Result:** DEFAULT BEHAVIOR = Show everything (no filtering)

**What Gets Filtered Out:**
- ❌ NOTHING - falls through to default "show all" behavior

**Expected Removal Rate:** 0% ⚠️

**Effectiveness:** ⭐ (1/5)
- **MAJOR GAP:** Filter doesn't recognize this hybrid type
- Users selecting this won't get ANY filtering benefit
- Should be added to both RESIDENTIAL_DEV_TYPES and COMMERCIAL_DEV_TYPES

**Recommended Fix:**
```typescript
const MIXED_USE_DEV_TYPES = [
  'shop_top_housing',
  // Don't exclude residential OR commercial categories
  // These developments need both sets of controls
];
```

---

#### 4. Multi Dwelling Housing
**Dev Type:** `multi_dwelling`
**Category Mapping:** → ❌ MISMATCH (filter expects `multi_dwelling_housing`)
**Filter Status:** ⚠️ PARTIALLY SUPPORTED

**Critical Issue:**
- Dropdown uses: `multi_dwelling`
- Filter expects: `multi_dwelling_housing`
- **Result:** DEFAULT BEHAVIOR = Show everything (no filtering)

**What Gets Filtered Out:**
- ❌ NOTHING - name mismatch prevents recognition

**Expected Removal Rate:** 0% ⚠️

**Effectiveness:** ⭐ (1/5)
- **BUG:** Naming inconsistency breaks filtering
- Users get NO benefit despite filter supporting this type

**Recommended Fix:**
```typescript
// Option 1: Update filter to accept both
const RESIDENTIAL_DEV_TYPES = [
  'dwelling_house',
  'secondary_dwelling',
  'multi_dwelling',        // Add this
  'multi_dwelling_housing', // Keep existing
  // ...
];

// Option 2: Update dropdown to match filter
<option value="multi_dwelling_housing">Multi Dwelling Housing</option>
```

---

#### 5. Residential Flat Building
**Dev Type:** `residential_flat`
**Category Mapping:** → ❌ MISMATCH (filter expects `residential_flat_building`)
**Filter Status:** ⚠️ PARTIALLY SUPPORTED

**Critical Issue:**
- Dropdown uses: `residential_flat`
- Filter expects: `residential_flat_building`
- **Result:** DEFAULT BEHAVIOR = Show everything (no filtering)

**What Gets Filtered Out:**
- ❌ NOTHING - name mismatch prevents recognition

**Expected Removal Rate:** 0% ⚠️

**Effectiveness:** ⭐ (1/5)
- **BUG:** Same naming inconsistency as multi_dwelling

**Recommended Fix:** Same as Multi Dwelling Housing

---

#### 6. Boarding House
**Dev Type:** `boarding_house`
**Category Mapping:** → ❌ UNKNOWN (not in RESIDENTIAL_DEV_TYPES list!)
**Filter Status:** ⚠️ NOT SUPPORTED

**Critical Issue:**
- `boarding_house` is NOT in any category array
- Filter will treat this as `unknown` category
- **Result:** DEFAULT BEHAVIOR = Show everything (no filtering)

**What Gets Filtered Out:**
- ❌ NOTHING - not recognized

**Expected Removal Rate:** 0% ⚠️

**Effectiveness:** ⭐ (1/5)
- **MAJOR GAP:** Not in filter's type lists
- Should be added to RESIDENTIAL_DEV_TYPES

**Recommended Fix:**
```typescript
const RESIDENTIAL_DEV_TYPES = [
  'dwelling_house',
  'secondary_dwelling',
  'boarding_house',  // Add this
  // ...
];
```

---

### Category 2: COMMERCIAL TYPES (1 option)

#### 7. Commercial Premises
**Dev Type:** `commercial`
**Category Mapping:** → ❌ MISMATCH (filter expects `shop`, `business_premises`, etc.)
**Filter Status:** ⚠️ NOT SUPPORTED

**Critical Issue:**
- Dropdown uses: `commercial`
- Filter expects: `shop`, `business_premises`, `office_premises`, etc.
- **Result:** DEFAULT BEHAVIOR = Show everything (no filtering)

**What SHOULD Get Filtered Out (if working):**
- Private open space requirements (70% confidence)
- Solar access standards (70% confidence)
- Bedroom size requirements (70% confidence)
- Apartment mix requirements (70% confidence)
- Dwelling size requirements (70% confidence)

**Expected Removal Rate:** 0% (currently) / 15-25% (if fixed) ⚠️

**Effectiveness:** ⭐ (1/5)
- **MAJOR BUG:** Generic "commercial" not in COMMERCIAL_DEV_TYPES array
- High-value filtering opportunity LOST

**Recommended Fix:**
```typescript
const COMMERCIAL_DEV_TYPES = [
  'commercial',              // Add this generic catch-all
  'commercial_premises',     // Add this too
  'shop',
  'business_premises',
  // ...
];
```

---

### Category 3: SPECIAL USE TYPES (1 option)

#### 8. Child Care Centre
**Dev Type:** `child_care`
**Category Mapping:** → ❌ UNKNOWN (not in any category!)
**Filter Status:** ⚠️ NOT SUPPORTED

**Critical Issue:**
- `child_care` is NOT in any category array
- Filter will treat this as `unknown` category
- **Result:** DEFAULT BEHAVIOR = Show everything (no filtering)

**What Gets Filtered Out:**
- ❌ NOTHING - not recognized

**Expected Removal Rate:** 0% ⚠️

**Effectiveness:** ⭐ (1/5)
- **MAJOR GAP:** Child care has unique requirements
- Should filter out residential bedroom/solar AND commercial signage/loading
- Needs custom category

**Recommended Fix:**
```typescript
const CHILDCARE_DEV_TYPES = [
  'child_care',
  'child_care_centre',
];

const CATEGORY_EXCLUSIONS: Record<string, string[]> = {
  residential: [...],
  commercial: [...],
  industrial: [...],
  childcare: [
    'bedroom_size',        // Not residential dwelling
    'apartment_mix',       // Not multi-res
    'loading_dock',        // Not commercial loading
    'shop_front',          // Not retail
  ],
};
```

---

## Summary Matrix

| Development Type | Value in Dropdown | Recognized by Filter? | Filter Category | Expected Removal | Effectiveness | Status |
|-----------------|-------------------|----------------------|-----------------|------------------|---------------|---------|
| Dwelling House | `dwelling_house` | ✅ YES | Residential | 3-8% | ⭐⭐⭐⭐ 4/5 | ✅ Working |
| Secondary Dwelling | `secondary_dwelling` | ✅ YES | Residential | 3-8% | ⭐⭐⭐⭐ 4/5 | ✅ Working |
| Shop Top Housing | `shop_top_housing` | ❌ NO | Unknown | 0% | ⭐ 1/5 | ⚠️ Broken |
| Multi Dwelling | `multi_dwelling` | ❌ NO (mismatch) | Unknown | 0% | ⭐ 1/5 | ⚠️ Broken |
| Residential Flat | `residential_flat` | ❌ NO (mismatch) | Unknown | 0% | ⭐ 1/5 | ⚠️ Broken |
| Boarding House | `boarding_house` | ❌ NO | Unknown | 0% | ⭐ 1/5 | ⚠️ Broken |
| Child Care Centre | `child_care` | ❌ NO | Unknown | 0% | ⭐ 1/5 | ⚠️ Broken |
| Commercial Premises | `commercial` | ❌ NO (mismatch) | Unknown | 0% | ⭐ 1/5 | ⚠️ Broken |

---

## Critical Findings

### ONLY 2 OUT OF 8 OPTIONS WORK ⚠️

**Working Options:**
1. ✅ Dwelling House
2. ✅ Secondary Dwelling

**Broken Options (6/8 = 75% FAILURE RATE):**
3. ⚠️ Shop Top Housing - not in type arrays
4. ⚠️ Multi Dwelling - name mismatch (`multi_dwelling` vs `multi_dwelling_housing`)
5. ⚠️ Residential Flat - name mismatch (`residential_flat` vs `residential_flat_building`)
6. ⚠️ Boarding House - not in type arrays
7. ⚠️ Child Care Centre - not in type arrays
8. ⚠️ Commercial Premises - name mismatch (`commercial` vs `shop`, `business_premises`, etc.)

---

## Root Cause Analysis

### Issue 1: Naming Inconsistency (affects 3 types)
**Problem:** Dropdown uses abbreviated values, filter expects full NSW LEP standard terms

**Examples:**
- Dropdown: `multi_dwelling` | Filter: `multi_dwelling_housing`
- Dropdown: `residential_flat` | Filter: `residential_flat_building`
- Dropdown: `commercial` | Filter: `shop`, `business_premises`, etc.

**Impact:** 3/8 types (37.5%) broken due to naming mismatch

---

### Issue 2: Missing Type Definitions (affects 3 types)
**Problem:** Filter only defines common residential/commercial/industrial types

**Missing from RESIDENTIAL_DEV_TYPES:**
- `boarding_house`

**Missing from any category:**
- `shop_top_housing` (hybrid type - needs special handling)
- `child_care` (special use - needs custom category)

**Impact:** 3/8 types (37.5%) get zero filtering

---

## Recommended Fixes

### Priority 1: Fix Naming Mismatches (Quick Win - 15 minutes)

```typescript
// lib/dev-type-filter.ts
const RESIDENTIAL_DEV_TYPES = [
  'dwelling_house',
  'secondary_dwelling',
  'dual_occupancy',
  'multi_dwelling_housing',
  'multi_dwelling',              // ADD THIS
  'residential_flat_building',
  'residential_flat',            // ADD THIS
  'boarding_house',              // ADD THIS
  'manor_house',
  'attached_dwelling',
  'semi_detached_dwelling',
];

const COMMERCIAL_DEV_TYPES = [
  'commercial',                  // ADD THIS
  'commercial_premises',         // ADD THIS
  'shop',
  'business_premises',
  'office_premises',
  'retail_premises',
  'food_and_drink_premises',
  'restaurant',
  'cafe',
];
```

**Expected Result:** 5/8 types now working (62.5% → brings Multi Dwelling, Residential Flat, Commercial online)

---

### Priority 2: Add Special Use Types (Medium Priority - 30 minutes)

```typescript
const CHILDCARE_DEV_TYPES = [
  'child_care',
  'child_care_centre',
  'early_education_and_care_facility',
];

const MIXED_USE_DEV_TYPES = [
  'shop_top_housing',
  'mixed_use_development',
];

const CATEGORY_EXCLUSIONS: Record<string, string[]> = {
  residential: [...],
  commercial: [...],
  industrial: [...],
  childcare: [
    'bedroom_size',
    'apartment_mix',
    'balcony_size',
    'loading_dock',
    'shop_front',
    'outdoor_dining',
  ],
  mixed_use: [
    // Don't exclude much - these need both residential + commercial
  ],
};
```

**Expected Result:** 7/8 types working (87.5%)

---

### Priority 3: Add Filter Diagnostics (Low Priority - 1 hour)

Add console logging to detect unrecognized types:

```typescript
function calculateApplicability(
  requirement: FilterableRequirement,
  developmentType: string
): boolean {
  let devTypeCategory: 'residential' | 'commercial' | 'industrial' | 'unknown' = 'unknown';

  if (RESIDENTIAL_DEV_TYPES.includes(developmentType)) {
    devTypeCategory = 'residential';
  } else if (COMMERCIAL_DEV_TYPES.includes(developmentType)) {
    devTypeCategory = 'commercial';
  } else if (INDUSTRIAL_DEV_TYPES.includes(developmentType)) {
    devTypeCategory = 'industrial';
  } else {
    console.warn(`⚠️ Unrecognized dev type: "${developmentType}" - defaulting to show all`);
  }

  // ...
}
```

---

## Impact Assessment

### Current State (Before Fixes)
- **Working properly:** 2/8 types (25%)
- **Zero filtering:** 6/8 types (75%)
- **User experience:** Confusing - filter only works for dwelling houses and granny flats

### After Priority 1 Fixes (15 min)
- **Working properly:** 5/8 types (62.5%)
- **Zero filtering:** 3/8 types (37.5%)
- **User experience:** Much better - most common residential and all commercial now work

### After Priority 2 Fixes (45 min total)
- **Working properly:** 7/8 types (87.5%)
- **Zero filtering:** 1/8 types (12.5%) - only shop_top_housing remains complex
- **User experience:** Excellent - nearly all types supported

---

## Conclusion

**Current Effectiveness: 2/10** ⚠️

The filter is well-designed (75-85% accuracy when it runs) BUT only works for 25% of dropdown options due to naming inconsistencies and missing type definitions.

**After Fixes: 9/10** ✅

With 45 minutes of fixes, effectiveness would jump to 87.5% coverage with the same high-quality filtering logic.

**Recommendation:** Implement Priority 1 fixes immediately (15 min) to bring 5/8 types online.
