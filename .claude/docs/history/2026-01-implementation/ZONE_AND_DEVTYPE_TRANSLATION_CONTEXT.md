# Zone and Development Type Translation - Complete Context History

## Background: The Problem

### Issue Discovered
**Date:** November 20, 2025
**Symptom:** 40 Lackey St, Summer Hill NSW (E1 zone) returned 0 general DCP requirements
**Expected:** Should return ~165 requirements based on Ashfield DCP Chapter F data

### Root Causes (Two Separate Issues)

#### Issue #1: Zone Translation Missing
**NSW Employment Zones Reform (April 26, 2023):**
- LEP zones changed from Business (B1, B2, B3, etc.) → Employment (E1, E2, E3, etc.)
- Example: B1 (Neighbourhood Centre) + B2 (Local Centre) → E1 (Local Centre)

**Database Reality:**
- Ashfield DCP extracted pre-2023 uses **legacy B1/B2 zone codes**
- Database stores: `applicable_zones: ['B1', 'B2']`

**API Query Reality:**
- NSW Planning Portal returns: `zone: "E1"`
- Old query: `WHERE 'E1' = ANY(applicable_zones)` → 0 matches (E1 ≠ B1/B2)

**Solution Implemented:** Zone translation via `getZoneAliases()`
- E1 → ['E1', 'B1', 'B2']
- Query: `WHERE applicable_zones && ARRAY['E1', 'B1', 'B2']::text[]` → Matches!

---

#### Issue #2: Development Type Mismatch
**Frontend Inference Logic:**
```typescript
// lib/requirement-prioritization.ts:113-116
if (zoneUpper.startsWith('B') || zoneUpper.startsWith('E')) {
  return 'commercial';  // Generic category inferred from zone
}
```

**Database Reality (Ashfield):**
```sql
-- NO generic "commercial" dev type exists!
-- Only specific types:
'shop'                      (4 requirements)
'food_and_drink_premises'  (18 requirements)
'neighbourhood_shop'        (4 requirements)
'take_away_food'           (18 requirements)
'child_care_centre'         (3 requirements)
```

**API Query Reality:**
- Query: `WHERE 'commercial' = ANY(development_types)` → 0 matches

---

## Data Flow Architecture

### 1. NSW Planning Portal → Property Data Service

**Planning Portal Returns:**
```json
{
  "zone": "E1",
  "zoneDescription": "E1: Local Centre",
  "landUse": "Local Centre",
  // NO development_type field!
}
```

**Key Point:** Planning Portal provides ZONE, not ACTUAL PROPERTY USE.

### 2. Frontend Inference → Development Type Detection

**File:** `lib/requirement-prioritization.ts`

```typescript
export function detectDevTypeFromZone(zone?: string): string {
  if (!zone) return 'dwelling_house';

  const zoneUpper = zone.toUpperCase();

  // Residential zones → dwelling_house
  if (zoneUpper.startsWith('R')) {
    return 'dwelling_house';
  }

  // Commercial/Employment zones → generic "commercial"
  if (zoneUpper.startsWith('B') || zoneUpper.startsWith('E')) {
    return 'commercial';  // ← INFERRED, NOT FROM API
  }

  // Industrial → commercial
  if (zoneUpper.startsWith('IN')) {
    return 'commercial';
  }

  // Mixed Use → shop_top_housing
  if (zoneUpper.startsWith('MU')) {
    return 'shop_top_housing';
  }

  return 'dwelling_house';
}
```

**Called From:** `app/assessment/page.tsx:38`
```typescript
useEffect(() => {
  if (selectedProperty?.constraints?.zone) {
    const detectedDevType = detectDevTypeFromZone(selectedProperty.constraints.zone);
    setDevelopmentType(detectedDevType);
  }
}, [selectedProperty?.constraints?.zone]);
```

### 3. Multiple Queries for Mixed-Use Zones

**For E1 Zone (allows residential + commercial):**

UI makes **TWO queries** to `/api/compliance/dcp-complete`:
1. `zone: E1, developmentType: 'dwelling_house'` (residential in E1)
2. `zone: E1, developmentType: 'commercial'` (commercial in E1)

**Why?** E1 zones are mixed-use - can have shop-top housing, standalone residential, or pure commercial.

### 4. Database Query Construction

**File:** `app/api/compliance/dcp-complete/route.ts`

**Before Fix (Broken):**
```typescript
// Line 869-874
WHERE dgr.lga = $1
AND $2 = ANY(dgr.applicable_zones)        // 'E1' = ANY(['B1','B2']) → FALSE
AND $3 = ANY(dgr.development_types)       // 'commercial' = ANY(['shop',...]) → FALSE
AND dgr.former_council = $4
```
Result: 0 rows

**After Zone Translation Fix (Partial):**
```typescript
// Line 869-874
WHERE dgr.lga = $1
AND dgr.applicable_zones && $2::text[]    // ['B1','B2'] && ['E1','B1','B2'] → TRUE
AND $3 = ANY(dgr.development_types)       // 'commercial' = ANY(['shop',...]) → FALSE
AND dgr.former_council = $4
```
Result: Still 0 rows (dev type still fails)

---

## Database Schema Reality

### DCP General Requirements Table

```sql
CREATE TABLE dcp_general_requirements (
  id INTEGER PRIMARY KEY,
  former_council TEXT,                -- 'Ashfield', 'Marrickville', 'Leichhardt'
  lga TEXT,                           -- 'Inner West'
  category TEXT,                      -- 'landscaping', 'setback_front', etc.
  applicable_zones TEXT[],            -- ['B1', 'B2'] or ['R2', 'R3', 'R4']
  development_types TEXT[],           -- ['shop', 'food_and_drink_premises']
  requirement_text TEXT,
  ...
);
```

### Ashfield Data Breakdown

**Total Ashfield Requirements:** 270

**Zone Distribution:**
```sql
-- With zone data:
101 records: applicable_zones = ['B1'], ['R2','R3'], etc.

-- Without zone data (universal):
165 records: applicable_zones = [] (empty array)
4 records:   applicable_zones populated, development_types = []
```

**For E1/B1/B2 Zones:**
```sql
-- Total with E1/B1/B2 zone match:
25 requirements

-- Breakdown by dev type:
food_and_drink_premises: 18
take_away_food:          18  (same requirements, both types tagged)
neighbourhood_shop:       4
shop:                     4
child_care_centre:        3
```

**Key Finding:** NO generic "commercial" dev type exists in database!

---

## Zone Translation System

### Implementation

**File:** `lib/zone-translation.ts`

```typescript
export const ZONE_TRANSLATION_MAP: Record<string, string[]> = {
  // E1 Local Centre (replaces B1 + B2)
  'E1': ['E1', 'B1', 'B2'],

  // E2 Commercial Centre (replaces B3 + B4 + B8)
  'E2': ['E2', 'B3', 'B4', 'B8'],

  // E3 Productivity Support (replaces B5 + B6 + B7)
  'E3': ['E3', 'B5', 'B6', 'B7'],

  // E4 General Industrial (replaces IN1 + IN4)
  'E4': ['E4', 'IN1', 'IN4'],

  // E5 Heavy Industrial (replaces IN2 + IN3)
  'E5': ['E5', 'IN2', 'IN3'],

  // Residential zones (no legacy equivalents)
  'R1': ['R1'],
  'R2': ['R2'],
  'R3': ['R3'],
  'R4': ['R4'],
  'R5': ['R5'],
  // ... etc
};

export function getZoneAliases(zone: string): string[] {
  if (zone in ZONE_TRANSLATION_MAP) {
    return ZONE_TRANSLATION_MAP[zone];
  }

  // If zone is legacy (B1, IN1, etc), find current equivalent
  if (LEGACY_ZONES.includes(zone)) {
    for (const [currentZone, aliases] of Object.entries(ZONE_TRANSLATION_MAP)) {
      if (aliases.includes(zone)) {
        return aliases;
      }
    }
  }

  return [zone];
}
```

### Usage in API

**Applied in TWO places:**

1. **General Provisions Query** (line 211-216)
```typescript
generalProvisionsQuery = `
  WHERE lga = $1
  AND applicable_zones && $2::text[]  -- Array overlap operator
  AND $3 = ANY(development_types)
`;
generalProvisionsParams = [queryLGA, zoneAliases, developmentType];
```

2. **General Requirements Query** (line 870-875)
```typescript
generalRequirementsQuery = `
  WHERE dgr.lga = $1
  AND dgr.applicable_zones && $2::text[]
  AND $3 = ANY(dgr.development_types)
  AND dgr.former_council = $4
`;
queryParams = [queryLGA, zoneAliases, developmentType, councilForQuery];
```

### PostgreSQL Array Operators

**Array Overlap (`&&`):**
```sql
-- Returns TRUE if arrays have ANY common elements
ARRAY['E1','B1','B2'] && ARRAY['B1','B2']  → TRUE
ARRAY['E1','B1','B2'] && ARRAY['R2']       → FALSE
```

**Array Contains (`= ANY`):**
```sql
-- Returns TRUE if value exists in array
'B1' = ANY(ARRAY['B1','B2'])  → TRUE
'E1' = ANY(ARRAY['B1','B2'])  → FALSE
```

---

## Development Type Translation (Proposed Solution)

### The Mismatch Table

| **Source**              | **Type**                        | **Level**        |
|-------------------------|---------------------------------|------------------|
| Planning Portal         | *(none - only zone)*            | N/A              |
| Frontend Inference      | `'commercial'` (generic)        | Category         |
| Ashfield Database       | `'shop'` (specific)             | Type             |
| Ashfield Database       | `'food_and_drink_premises'`     | Type             |
| Ashfield Database       | `'neighbourhood_shop'`          | Type             |

### Proposed Solution: Conditional Dev Type Expansion

**Concept:** Only expand "commercial" for commercial zones (E1, B1-B8), keep everything else precise.

```typescript
// In dcp-complete route.ts
function buildDevTypeFilter(developmentType: string, zoneAliases: string[]): string {
  // Check if querying commercial zones
  const isCommercialZone = zoneAliases.some(z =>
    z.startsWith('E') || z.startsWith('B')
  );

  if (developmentType === 'commercial' && isCommercialZone) {
    // Expand generic "commercial" to all commercial subtypes
    return `(
      'commercial' = ANY(dgr.development_types) OR
      'shop' = ANY(dgr.development_types) OR
      'food_and_drink_premises' = ANY(dgr.development_types) OR
      'neighbourhood_shop' = ANY(dgr.development_types) OR
      'office_premises' = ANY(dgr.development_types) OR
      'business_premises' = ANY(dgr.development_types) OR
      'neighbourhood_centre' = ANY(dgr.development_types) OR
      'commercial_core' = ANY(dgr.development_types) OR
      'take_away_food' = ANY(dgr.development_types) OR
      'child_care_centre' = ANY(dgr.development_types)
    )`;
  } else {
    // All other cases: precise matching
    return `$X = ANY(dgr.development_types)`;
  }
}
```

### Alternative: Remove Dev Type Filter for Commercial

**Simpler approach:**
```typescript
if (councilForQuery?.toLowerCase() === 'ashfield') {
  // For commercial zones: filter by zone only (no dev type)
  const isCommercialZone = zoneAliases.some(z =>
    z.startsWith('E') || z.startsWith('B')
  );

  if (isCommercialZone) {
    generalRequirementsQuery = `
      WHERE dgr.lga = $1
      AND dgr.applicable_zones && $2::text[]
      AND dgr.former_council = $3
      -- NO dev type filter
    `;
    queryParams = [queryLGA, zoneAliases, councilForQuery];
  } else {
    // Residential zones: keep precise dev type filtering
    generalRequirementsQuery = `
      WHERE dgr.lga = $1
      AND dgr.applicable_zones && $2::text[]
      AND $3 = ANY(dgr.development_types)
      AND dgr.former_council = $4
    `;
    queryParams = [queryLGA, zoneAliases, developmentType, councilForQuery];
  }
}
```

**Trade-offs:**
- ✅ Simpler logic
- ✅ Zone filtering (E1/B1/B2) is already specific enough
- ✅ No maintenance of dev type lists
- ⚠️ Returns all 25 commercial requirements (shop + restaurant + office)
- ⚠️ User must manually filter if property is specific type

---

## Two-API Architecture

### Why Two APIs?

1. **`/api/compliance/constraints`** (Created Sept-Oct 2025)
   - Purpose: Height, FSR, setback CONSTRAINTS (numeric values)
   - Returns: `{ building_envelope: [...], environmental: [...] }`
   - Has zone translation: ✓

2. **`/api/compliance/dcp-complete`** (Created Oct 31, 2025)
   - Purpose: Full DCP provisions/requirements (all categories)
   - Returns: `{ general_provisions: {...}, precinct_provisions: {...} }`
   - Had zone translation: ✗ (Fixed Nov 20, 2025)

### Why Split?

**Historical:** Different data structures and use cases.
- Constraints API: Focused queries for specific numeric controls
- DCP Complete API: Comprehensive provisions for full compliance view

**Current Status:** Both should use zone translation. Constraints API got it first, DCP Complete was missing it.

---

## Council-Specific Behavior

### Ashfield
- **Zone filtering:** Uses zone translation (E1 → B1/B2)
- **Dev type filtering:** CURRENTLY REQUIRED but causes "commercial" mismatch
- **Data structure:** 270 requirements, zones and dev types populated (mostly)
- **DCP organization:** Chapter F organized by dev type (F.1 = dwelling, F.6 = commercial)

### Marrickville
- **Zone filtering:** NONE (all zones NULL in database)
- **Dev type filtering:** NONE (all dev types NULL in database)
- **Data structure:** 163 requirements, NO zone/devtype data
- **DCP organization:** Neighbourhood-based (Part 1-9), not zone-based

### Leichhardt
- **Zone filtering:** NONE (uses fallback to regulatory_provisions)
- **Dev type filtering:** NONE (universal controls)
- **Data structure:** 0 records in dcp_general_requirements (uses regulatory_provisions)
- **DCP organization:** Universal controls (Part A-G), not zone/devtype specific

---

## Universal Requirements - How They Work

### What Are Universal Requirements?

**Universal requirements** = DCP controls that apply to **ALL zones**, not just specific ones.

In the database, these are represented by:
- `applicable_zones = []` (empty array) - Ashfield approach
- `applicable_zones = NULL` - Marrickville approach
- Stored in separate table - Leichhardt approach (regulatory_provisions)

### Council Comparison

#### Ashfield Approach: Mixed (Universal + Zone-Specific)

**Total Requirements:** 270

**Zone Distribution:**
```sql
-- Universal (apply to all zones):
165 requirements: applicable_zones = []

-- Zone-specific:
105 requirements: applicable_zones = ['B1','B2'] or ['R2'] or ['R3'], etc.
```

**Examples of Universal Requirements:**
- Heritage controls (apply regardless of zone)
- Tree preservation requirements
- Waste management standards
- Accessibility requirements
- Acoustic requirements
- Stormwater management

**Examples of Zone-Specific Requirements:**
- Building height (varies by zone)
- Setbacks (different for residential vs commercial)
- FSR (different by zone)
- Landscaping percentages (vary by zone)

#### Marrickville Approach: All Universal

**Total Requirements:** 163

**Why All Universal?**
- Marrickville DCP is **neighbourhood-based**, not zone-based
- Controls organized by geographic area (Dulwich Hill, Sydenham, Enmore, etc.)
- Filtering happens by **precinct**, not by zone
- ALL requirements have `applicable_zones = NULL`

**Database Reality:**
```sql
SELECT COUNT(*), applicable_zones
FROM dcp_general_requirements
WHERE former_council = 'Marrickville'
GROUP BY applicable_zones;

-- Result:
163 requirements | NULL
```

#### Leichhardt Approach: Separate Universal Table

**Total Requirements:** 3,355 (in regulatory_provisions table)

**Why Separate Table?**
- Leichhardt DCP has comprehensive universal controls (Parts A-G)
- Too granular to fit in standard requirements structure
- Uses fallback to `regulatory_provisions` table
- No zone or dev type filtering

### How Queries Handle Universal Requirements

#### Before Fix (Broken)
```sql
-- Query for E1 zone
WHERE lga = 'Inner West'
AND 'E1' = ANY(applicable_zones)  -- Matches NOTHING
AND former_council = 'Ashfield'

-- Result: 0 rows (missed all universal requirements!)
```

#### After Zone Translation (Still Incomplete)
```sql
-- Query for E1 zone with translation
WHERE lga = 'Inner West'
AND applicable_zones && ARRAY['E1','B1','B2']::text[]  -- Matches zone-specific only
AND 'commercial' = ANY(development_types)  -- Still fails
AND former_council = 'Ashfield'

-- Result: 0 rows (zone translation works, but dev type still fails)
```

#### After Full Fix (Current)
```sql
-- Query for E1 zone (commercial zones path)
WHERE lga = 'Inner West'
-- NO zone filter → Returns ALL Ashfield requirements
AND former_council = 'Ashfield'

-- Result: 270 rows (165 universal + 105 zone-specific)
-- Frontend filters by relevance
```

**Why Remove Zone Filter for Commercial?**
1. **Includes universal requirements** - The 165 requirements with `applicable_zones = []`
2. **Dev type mismatch safety** - Avoids filtering out requirements due to generic "commercial" vs specific "shop"
3. **Consistency** - Matches Marrickville and Leichhardt approach (no zone filtering)

### Actual Results for 40 Lackey St

**Address:** 40 Lackey St, Summer Hill NSW 2130
**Zone:** E1 (Local Centre)
**Former Council:** Ashfield

**Query Returns:**
```
✓ General requirements: 165 (former_council=Ashfield)
✓ Precinct requirements: 55 (ashfield_1 = SummerHill Urban Village)
Total: 220 requirements
```

**Breakdown of 165 General Requirements:**
- **165 universal** (empty zones = applies to E1 and all other zones)
- The 18 B1/B2 commercial-specific requirements are included in the 165 count

**Why 165 Instead of 25?**
- The API now returns ALL 270 Ashfield requirements when querying commercial zones
- The 165 with empty zones are universal and correctly apply to E1
- Frontend must filter/prioritize based on relevance

### Summary Table

| Council | Total Reqs | Universal | Zone-Specific | How Universal Works |
|---------|------------|-----------|---------------|---------------------|
| **Ashfield** | 270 | 165 (empty array) | 105 (populated) | Mixed approach - some universal, some zone-specific |
| **Marrickville** | 163 | 163 (all NULL) | 0 | All universal - neighbourhood-based, not zone-based |
| **Leichhardt** | 3,355 | 3,355 (separate table) | 0 | All universal - uses regulatory_provisions fallback |

### Query Behavior by Council and Zone Type

| Council | Zone Type | Zone Filter? | Dev Type Filter? | Returns Universal? | Count |
|---------|-----------|--------------|------------------|-------------------|-------|
| **Ashfield (E1)** | Commercial | ❌ No | ❌ No | ✅ Yes (all 165) | 165 + precinct |
| **Ashfield (R2)** | Residential | ✅ Yes | ✅ Yes | ⚠️ Only if zone = [] | Varies |
| **Marrickville** | Any | ❌ No | ❌ No | ✅ Yes (all 163) | 163 + precinct |
| **Leichhardt** | Any | ❌ No | ❌ No | ✅ Yes (all 3,355) | 3,355 + precinct |

**Key Insight:** Universal requirements (empty zones) are correctly included when we skip the zone filter for commercial zones. This is the expected behavior!

---

## Testing Reference

### Test Addresses

**40 Lackey St, Summer Hill NSW 2130:**
- **Planning Portal:** E1 zone, INNER WEST LGA
- **Spatial Match:** ashfield_1 (SummerHill Urban Village)
- **Former Council:** Ashfield
- **Expected Results:**
  - With zone translation + dev type fix: 25 general + 55 precinct = 80 requirements
  - With zone translation only: 0 general + 55 precinct = 55 requirements (current)
  - Without zone translation: 0 general + 55 precinct = 55 requirements (broken)

**180 Addison Rd, Marrickville NSW 2204:**
- **Planning Portal:** R2 zone, INNER WEST LGA
- **Former Council:** Ashfield (boundary property)
- **Expected Results:** 74 R2 requirements + 8 precinct = 82 requirements

**181 Addison Rd, Haberfield NSW 2045:**
- **Planning Portal:** R2 zone, INNER WEST LGA
- **Former Council:** Leichhardt
- **Expected Results:** 843 universal + 9 precinct = 852 requirements

---

## Git Commit History

### Key Commits

**Zone Translation Added:**
- `edf2e9d1` (Nov 11, 2025): "Add all missing frontend files for complete deployment"
  - Created `lib/zone-translation.ts`
  - Applied to `/api/compliance/constraints`
  - NOT applied to `/api/compliance/dcp-complete`

**Zone Translation Applied to DCP Complete:**
- `dc1175bb` (Nov 20, 2025): "fix: Add zone translation to dcp-complete API for E1→B1/B2 matching"
  - Imported `getZoneAliases` in dcp-complete route
  - Changed SQL from `$2 = ANY(applicable_zones)` to `applicable_zones && $2::text[]`
  - Applied to both general provisions and general requirements queries

**Dev Type Filter Removed (Early Attempt):**
- `efe20530` (Nov 12, 2025): "fix: Remove development_type filter from Ashfield DCP query"
  - Removed dev type filter because "generic 'commercial' causes 0 results"
  - Comment: "Chapter F is organized by devtype but frontend infers generic 'commercial'"

**Dev Type Filter Re-Added:**
- Later commit (unknown): Re-added strict dev type filter
  - Caused regression: 40 Lackey St returns 0 again
  - Reason for re-adding: Unknown (possibly thought it was needed for precision)

---

## Decision Matrix: Dev Type Handling

### Option 1: Dev Type Translation
**Pros:**
- Precise for known types
- Maintains semantic meaning
- Can expand over time

**Cons:**
- Maintenance burden (map per council?)
- Still over-inclusive (restaurant gets all commercial)
- Complex conditional logic

### Option 2: Remove Dev Type Filter for Commercial
**Pros:**
- Simplest implementation
- Zone already provides specificity
- Matches Marrickville/Leichhardt pattern

**Cons:**
- Returns more than needed (25 items)
- User must manually identify relevant ones
- Inconsistent with residential zones

### Option 1.5: Conditional Expansion (Recommended)
**Pros:**
- Balances precision and coverage
- Only affects commercial zones
- Residential zones stay precise
- No user input needed

**Cons:**
- Slight complexity (if/else logic)
- Still returns all commercial types

---

## Future Considerations

### When Adding New Councils

**Check:**
1. What zone codes does the DCP use? (Legacy B1-B8 or new E1-E5?)
2. Does the DCP filter by zone? (Ashfield: Yes, Marrickville: No)
3. Does the DCP filter by dev type? (Ashfield: Yes, Marrickville: No)
4. Are dev types specific or generic? (Check database values)

**Add to Zone Translation Map:**
```typescript
// If council uses legacy zones
'E1': ['E1', 'B1', 'B2', 'LOCAL_LEGACY_CODE']
```

### Dev Type Standardization Project

**Long-term solution:** Standardize dev types across all councils

**Hierarchy:**
```
Level 1 (Category):    residential, commercial, industrial
Level 2 (Subcategory): dwelling_house, shop, office, warehouse
Level 3 (Specific):    detached_house, neighbourhood_shop, medical_centre
```

**Database Migration:**
```sql
-- Add category column
ALTER TABLE dcp_general_requirements
ADD COLUMN development_category TEXT;

-- Populate categories
UPDATE dcp_general_requirements
SET development_category = 'commercial'
WHERE 'shop' = ANY(development_types)
   OR 'food_and_drink_premises' = ANY(development_types)
   OR 'neighbourhood_shop' = ANY(development_types);

-- Query by category
WHERE development_category = 'commercial'
```

---

## Quick Reference

### Files to Check

**Zone Translation:**
- `lib/zone-translation.ts` - Zone mapping logic
- `app/api/compliance/constraints/route.ts` - Uses zone translation ✓
- `app/api/compliance/dcp-complete/route.ts` - Uses zone translation ✓

**Dev Type Inference:**
- `lib/requirement-prioritization.ts:103-130` - Infers dev type from zone
- `app/assessment/page.tsx:36-41` - Calls inference on zone change

**Database Queries:**
- `app/api/compliance/dcp-complete/route.ts:841-875` - Ashfield requirements query
- `app/api/compliance/dcp-complete/route.ts:196-216` - Ashfield provisions query

### Common Patterns

**Array Overlap Check:**
```sql
WHERE applicable_zones && ARRAY['E1','B1','B2']::text[]
```

**Zone Translation Call:**
```typescript
const zoneAliases = getZoneAliases(zone);  // E1 → ['E1','B1','B2']
```

**Dev Type from Zone:**
```typescript
const devType = detectDevTypeFromZone(zone);  // E1 → 'commercial'
```

---

## Summary

**Two Translation Layers Needed:**
1. ✅ **Zone Translation:** E1 → [E1, B1, B2] (IMPLEMENTED)
2. ⚠️ **Dev Type Translation:** commercial → [shop, food_and_drink_premises, ...] (PENDING)

**Root Issue:** Planning Portal provides ZONE → Frontend infers GENERIC dev type → Database has SPECIFIC dev types → Query fails.

**Current Status:** Zone translation working, dev type mismatch still causing 0 results for commercial zones.

**Next Step:** Implement Option 1.5 (conditional dev type expansion for commercial zones).
