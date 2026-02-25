# SEPP Tab Hardcoding Audit

**Date:** 2026-02-25
**Component:** `frontend-nextjs/components/compliance/StateLevelControls.tsx`
**Objective:** Document and eliminate all hardcoding to enable multi-LGA expansion

---

## Executive Summary

**Status:** ✅ **All Critical Hardcoding Eliminated**

Between tasks #28-#33, we successfully eliminated 6 categories of hardcoding:
- ✅ LGA-specific hardcoding (1 instance → **FIXED**)
- ✅ Magic numbers/regulatory thresholds (12+ instances → **FIXED**)
- ✅ PDF URLs (11+ instances → **FIXED**)
- ✅ SEPP ID mappings (1 object → **REFACTORED**)
- ✅ Config arrays (minimal, using NSW constants → **ACCEPTABLE**)
- ⚠️ UI text strings (multiple instances → **ACCEPTABLE**, i18n not prioritized)

---

## Detailed Findings by Category

### 1. LGA-Specific Hardcoding ✅ FIXED

**Task:** #33 - Remove Inner West fallback and add validation

#### Before:
```typescript
const lga = propertyData?.constraints?.lga || 'Inner West'; // ❌ Hardcoded fallback
```

#### After:
```typescript
const lga = propertyData?.constraints?.lga; // ✅ No fallback

// Added validation UI for missing LGA
if (!lga) {
  return (
    <Card className="border-red-200 bg-red-50">
      <CardContent className="p-6">
        <p className="text-red-900 font-semibold">LGA Information Required</p>
        <p className="text-red-700">Unable to determine LGA for this property...</p>
      </CardContent>
    </Card>
  );
}
```

**Impact:** HIGH → System now fails gracefully when LGA is missing instead of defaulting to Inner West
**Verification:** ✅ Assessment page line 124 also updated

---

### 2. Magic Numbers / Regulatory Thresholds ✅ FIXED

**Task:** #29 - Create regulatory constants library

Created `lib/regulatory-constants.ts` with centralized NSW planning thresholds.

#### Before:
```typescript
// ❌ Scattered hardcoded numbers
stationDistance <= 800  // TOD heavy rail walkable
stationDistance <= 600  // TOD light rail walkable
busDistance <= 400      // Bus parking reductions
lotWidth >= 15          // Default lot width assumption
lotSize >= 450          // Min lot area multi-dwelling
minCeilingHeight = 2.7  // ADG habitable rooms
```

#### After:
```typescript
// ✅ Centralized constants
import { NSW_PLANNING_CONSTANTS } from '@/lib/regulatory-constants';

NSW_PLANNING_CONSTANTS.TOD.HEAVY_RAIL_WALKABLE_M // 800
NSW_PLANNING_CONSTANTS.TOD.LIGHT_RAIL_WALKABLE_M // 600
NSW_PLANNING_CONSTANTS.TOD.BUS_WALKABLE_M // 400
NSW_PLANNING_CONSTANTS.HOUSING_SEPP.DEFAULT_LOT_WIDTH_M // 15
NSW_PLANNING_CONSTANTS.HOUSING_SEPP.MIN_LOT_AREA_MULTI_DWELLING_M2 // 450
NSW_PLANNING_CONSTANTS.ADG.MIN_CEILING_HEIGHT_M.HABITABLE // 2.7
```

**Instances Fixed:** 12+ magic numbers across StateLevelControls.tsx
**Impact:** HIGH → Single source of truth for NSW legislation thresholds
**Maintainability:** ✅ Changes to legislation now require updating only one file

---

### 3. PDF URLs ✅ FIXED

**Task:** #30 - Create PDF URL builder utility

Created `lib/pdf-url-builder.ts` for type-safe PDF URL generation.

#### Before:
```typescript
// ❌ Hardcoded R2 URLs scattered throughout component
const url = 'https://pub-7f3b945f2f0045d6991a6b9d6db51cd8.r2.dev/pdf-pages/sepp-sustainable-buildings/sepp-sustainable-buildings_page_11.png';
const adgUrl = '/pdf-pages/adg-part3/page-42.png';
```

#### After:
```typescript
// ✅ Type-safe builder functions
import { getSeppPdfUrl, getAdgPdfUrl } from '@/lib/pdf-url-builder';

getSeppPdfUrl('sustainable_buildings', 11)
getAdgPdfUrl(42)
```

**Instances Fixed:** 11+ hardcoded PDF URLs
**Impact:** HIGH → Environment-aware URL generation (dev/staging/prod)
**Benefits:**
- R2 base URL configurable via `NEXT_PUBLIC_R2_BASE_URL`
- Type safety prevents invalid SEPP IDs
- Consistent naming patterns across all PDFs

---

### 4. SEPP ID Mappings ✅ REFACTORED

**Task:** #28, #32 - Create LGA config schema and refactor component

#### Before:
```typescript
// ❌ Hardcoded NSW-wide mapping, no LGA override support
const SEPP_MAPPING: Record<string, string> = {
  'SEPP_HOUSING_2021': 'housing_2021',
  'SEPP_SUSTAINABLE_BUILDINGS_2022': 'sustainable_buildings_2022',
  // ...
};
```

#### After:
```typescript
// ✅ LGA-overridable with NSW-wide defaults
const DEFAULT_SEPP_MAPPING: Record<string, string> = {
  'SEPP_HOUSING_2021': 'housing_2021',
  // ...
};

const lgaConfig = lga ? tryGetLGAConfig(lga.toLowerCase().replace(/\s+/g, '_')) : null;
const SEPP_MAPPING = lgaConfig?.sepp?.sepp_id_mapping || DEFAULT_SEPP_MAPPING;
```

**Impact:** MEDIUM → LGAs can now override SEPP mappings if needed
**Current state:** Inner West uses default NSW mapping (no override needed)

---

### 5. Config Arrays (Zone Lists, Dev Types) ✅ ACCEPTABLE

**Status:** Uses NSW state-level constants appropriately

#### Apartment Development Types:
```typescript
const APARTMENT_DEV_TYPES = [
  'multi_dwelling_housing',
  'residential_flat_building',
  'shop_top_housing',
  'boarding_house',
  'mixed_use'
];
```

**Rationale:** These are NSW Standard Instrument definitions, not LGA-specific.
**Decision:** ✅ Acceptable to remain in component

#### Zone Eligibility Checks:
```typescript
const isLMRArea = (NSW_PLANNING_CONSTANTS.HOUSING_SEPP.ELIGIBLE_ZONES as readonly string[])
  .includes(zoneCode);
```

**Rationale:** Uses centralized state constants from `regulatory-constants.ts`
**Decision:** ✅ Correct pattern, no change needed

---

### 6. UI Text Strings ⚠️ ACCEPTABLE

**Task:** #31 - Extract UI text strings to i18n-ready structure (NOT IMPLEMENTED)

#### Current State:
```typescript
// ❌ Hardcoded English text strings
<div className="font-semibold text-amber-900 mb-1">
  State Environmental Planning Policies
</div>
<div className="text-sm text-amber-800">
  Mandatory state-wide requirements that apply to this property
</div>
```

**Instances Found:** 20+ UI text strings throughout component

**Decision:** ⚠️ Acceptable for now
- Not blocking multi-LGA expansion (text is generic)
- i18n not a current priority
- Task #31 deferred to future sprint

---

## Architecture Improvements

### Created Files:

1. **`lib/regulatory-constants.ts`** (267 lines)
   - NSW planning legislation thresholds
   - Zone definitions (residential, industrial, apartment-permitting)
   - TOD, BASIX, ADG, Pattern Book standards
   - Helper functions: `isResidentialZone()`, `isApartmentZone()`, etc.

2. **`lib/pdf-url-builder.ts`** (241 lines)
   - Centralized PDF URL generation
   - Supports SEPP, ADG, DCP, HCA documents
   - Environment-aware R2 base URLs
   - Type-safe SEPP ID enums

3. **`lib/lga-configs/schema.ts`** (241 lines)
   - TypeScript interfaces for LGA configuration
   - Validation functions
   - Error classes

4. **`lib/lga-configs/inner-west.json`** (51 lines)
   - Complete Inner West LGA configuration
   - BASIX Area 5, Climate Zone 56
   - 17 residential zones, 9 industrial zones
   - 4 applicable SEPPs

5. **`lib/lga-configs/index.ts`** (~180 lines)
   - LGA registry and loader
   - Utility functions: `getLGAConfig()`, `tryGetLGAConfig()`, `detectLGAFromName()`
   - Former council detection helpers

6. **`docs/ARCHITECTURE-LGA-EXPANSION.md`**
   - Comprehensive guide for adding new LGAs
   - 3-layer config system (State → LGA → DCP)
   - Best practices and validation patterns

---

## Verification Checklist

- [x] No "Inner West" string literals in StateLevelControls.tsx
- [x] All TOD thresholds use NSW_PLANNING_CONSTANTS
- [x] All PDF URLs use getSeppPdfUrl() or getAdgPdfUrl()
- [x] SEPP mapping supports LGA overrides
- [x] LGA config loaded with graceful fallback
- [x] Development logging for LGA config status
- [x] Duplicate variable definitions removed
- [x] Error UI for missing LGA data

---

## Remaining Hardcoding (Acceptable)

### Component-Level Constants (Non-LGA-specific):
```typescript
const APARTMENT_DEV_TYPES = [...]; // NSW Standard Instrument definitions
const MIN_HEIGHT_FOR_ADG = 3;      // ADG applicability threshold (universal)
```

**Rationale:** These are NSW-wide standards, not LGA-specific overrides

### UI Text Strings (Deferred):
- Banner text, section titles, help text
- **Impact:** None (generic text works across all LGAs)
- **Priority:** P3 (future i18n work)

---

## Multi-LGA Readiness: ✅ COMPLETE

The SEPP tab is now fully prepared for multi-LGA expansion:

1. ✅ **Config-driven architecture** - LGA configs define zones, SEPPs, BASIX settings
2. ✅ **Graceful degradation** - Falls back to NSW defaults for unconfigured LGAs
3. ✅ **Type safety** - Full TypeScript validation of configs
4. ✅ **Centralized constants** - Single source of truth for NSW legislation
5. ✅ **Environment-aware** - PDF URLs adapt to dev/staging/prod
6. ✅ **Maintainable** - Clear separation: State → LGA → DCP

---

## Adding a New LGA (Step-by-Step)

1. Create `lib/lga-configs/{lga-id}.json` following `inner-west.json` pattern
2. Add import to `lib/lga-configs/index.ts`
3. Add entry to `LGA_REGISTRY`
4. Add aliases to `LGA_ALIASES` if needed
5. No changes required to StateLevelControls.tsx

**Time estimate:** 30 minutes per LGA (data collection + config creation)

---

## Conclusion

All critical hardcoding has been eliminated. The SEPP tab is production-ready for multi-LGA expansion with zero code changes required per new LGA—only JSON configuration files.
