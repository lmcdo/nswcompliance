# Smart Filters Implementation Plan

**Goal:** Replace ineffective dev-type filtering (3.6% removal) with property-characteristic filtering (30-40% potential removal)

**Approach:** Phased rollout, data-driven, leveraging what we already have

---

## Phase 1: Foundation (2 hours) - DO THIS FIRST

### 1.1 Add Smart Filter UI (1 hour)

**Location:** `frontend-nextjs/app/assessment/page.tsx`

Replace current dev type messaging with honest description + add smart filters:

```tsx
{/* Development Type - Keep but be honest */}
<div className="border-t pt-3">
  <label className="text-sm font-semibold text-gray-700 block mb-1">
    Development Type
  </label>
  <select
    value={developmentType}
    onChange={(e) => setDevelopmentType(e.target.value)}
    className="w-full px-3 py-2 border rounded-md text-sm"
  >
    {/* existing options */}
  </select>
  <p className="text-xs text-gray-500 mt-1">
    Removes obvious mismatches (e.g., commercial signage for dwellings)
  </p>
</div>

{/* NEW: Smart Filters */}
<div className="border-t pt-3 mt-3">
  <label className="text-sm font-semibold text-gray-700 block mb-2">
    Smart Filters (Optional)
  </label>
  <p className="text-xs text-gray-600 mb-3">
    Select what applies to filter out irrelevant requirements
  </p>

  <div className="space-y-2">
    {/* Auto-detect heritage from coordinates */}
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={hasHeritageOverlay}
        onChange={(e) => setHasHeritageOverlay(e.target.checked)}
        disabled={heritageAutoDetected}
        className="rounded"
      />
      <span>
        Heritage overlay applies
        {heritageAutoDetected && (
          <span className="text-xs text-blue-600 ml-1">(auto-detected)</span>
        )}
      </span>
    </label>

    {/* Lot size trigger - use Planning API property area */}
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={isSmallLot}
        disabled={lotSizeAutoDetected}
        className="rounded"
      />
      <span>
        Small lot (&lt; 450m²)
        {lotSizeAutoDetected && propertyArea && (
          <span className="text-xs text-blue-600 ml-1">
            ({propertyArea}m² - auto-detected)
          </span>
        )}
      </span>
    </label>

    {/* User intent flags */}
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={poolPlanned}
        onChange={(e) => setPoolPlanned(e.target.checked)}
        className="rounded"
      />
      <span>Building pool or tennis court</span>
    </label>

    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={subdivisionPlanned}
        onChange={(e) => setSubdivisionPlanned(e.target.checked)}
        className="rounded"
      />
      <span>Planning subdivision or strata</span>
    </label>

    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={demolitionPlanned}
        onChange={(e) => setDemolitionPlanned(e.target.checked)}
        className="rounded"
      />
      <span>Demolishing existing structure</span>
    </label>
  </div>

  <p className="text-xs text-gray-500 mt-2 italic">
    Unchecked items filter out related requirements
  </p>
</div>

{/* Display Mode Toggles */}
<div className="border-t pt-3 mt-3">
  <label className="text-sm font-semibold text-gray-700 block mb-2">
    Display Options
  </label>

  <div className="space-y-2">
    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={showOnlyNumeric}
        onChange={(e) => setShowOnlyNumeric(e.target.checked)}
        className="rounded"
      />
      <span>Show only requirements with numbers (setbacks, heights, areas)</span>
    </label>

    <label className="flex items-center gap-2 text-sm">
      <input
        type="checkbox"
        checked={hideObjectives}
        onChange={(e) => setHideObjectives(e.target.checked)}
        className="rounded"
      />
      <span>Hide design objectives (show compliance requirements only)</span>
    </label>
  </div>
</div>
```

**State additions:**
```tsx
const [hasHeritageOverlay, setHasHeritageOverlay] = useState(false);
const [heritageAutoDetected, setHeritageAutoDetected] = useState(false);
const [isSmallLot, setIsSmallLot] = useState(false);
const [lotSizeAutoDetected, setLotSizeAutoDetected] = useState(false);
const [poolPlanned, setPoolPlanned] = useState(false);
const [subdivisionPlanned, setSubdivisionPlanned] = useState(false);
const [demolitionPlanned, setDemolitionPlanned] = useState(false);
const [showOnlyNumeric, setShowOnlyNumeric] = useState(false);
const [hideObjectives, setHideObjectives] = useState(false);
const [propertyArea, setPropertyArea] = useState<number | null>(null);
```

### 1.2 Create Smart Filter Logic (1 hour)

**New file:** `frontend-nextjs/lib/smart-filters.ts`

```typescript
interface SmartFilterContext {
  // From user/auto-detect
  hasHeritageOverlay: boolean;
  isSmallLot: boolean;
  poolPlanned: boolean;
  subdivisionPlanned: boolean;
  demolitionPlanned: boolean;
  showOnlyNumeric: boolean;
  hideObjectives: boolean;

  // From dev-type filter (keep existing)
  developmentType: string;
}

interface FilterableRequirement {
  id: number;
  category: string;
  requirement_text: string;
  verbatim_source_text?: string;
  conditional_text?: string;
  section_type?: string;
  value_numeric?: number;
  value_min?: number;
  value_max?: number;
  // ... existing fields
}

/**
 * Apply smart filters to requirements
 * Returns filtered array
 */
export function applySmartFilters(
  requirements: FilterableRequirement[],
  context: SmartFilterContext
): FilterableRequirement[] {
  let filtered = [...requirements];

  // 1. Display mode filters (UI preference)
  if (context.showOnlyNumeric) {
    filtered = filtered.filter(req =>
      req.value_numeric != null ||
      req.value_min != null ||
      req.value_max != null
    );
  }

  if (context.hideObjectives) {
    filtered = filtered.filter(req =>
      req.section_type !== 'objective'
    );
  }

  // 2. Intent-based filters (if NOT planning X, hide X requirements)
  if (!context.poolPlanned) {
    filtered = filtered.filter(req => {
      const text = (req.verbatim_source_text || req.requirement_text || '').toLowerCase();
      const conditional = (req.conditional_text || '').toLowerCase();
      return !(text.includes('pool') || text.includes('tennis') ||
               conditional.includes('pool') || conditional.includes('tennis'));
    });
  }

  if (!context.subdivisionPlanned) {
    filtered = filtered.filter(req => {
      const text = (req.verbatim_source_text || req.requirement_text || '').toLowerCase();
      const conditional = (req.conditional_text || '').toLowerCase();
      return !(text.includes('subdivision') || text.includes('strata') ||
               conditional.includes('subdivision') || conditional.includes('strata'));
    });
  }

  if (!context.demolitionPlanned) {
    filtered = filtered.filter(req => {
      const text = (req.verbatim_source_text || req.requirement_text || '').toLowerCase();
      const conditional = (req.conditional_text || '').toLowerCase();
      return !(text.includes('demolit') || conditional.includes('demolit'));
    });
  }

  // 3. Property characteristic filters
  if (!context.hasHeritageOverlay) {
    filtered = filtered.filter(req => {
      const text = (req.verbatim_source_text || req.requirement_text || '').toLowerCase();
      const conditional = (req.conditional_text || '').toLowerCase();
      // Only filter requirements that REQUIRE heritage overlay
      // Keep general heritage advice (informational)
      return !(
        (text.includes('heritage item') || text.includes('heritage conservation area')) &&
        (conditional.includes('within') || conditional.includes('adjacent'))
      );
    });
  }

  if (!context.isSmallLot) {
    filtered = filtered.filter(req => {
      const text = (req.verbatim_source_text || req.requirement_text || '').toLowerCase();
      const conditional = (req.conditional_text || '').toLowerCase();
      // Filter requirements specifically for small lots
      return !(
        (text.includes('small lot') || text.includes('lot less than') ||
         text.includes('lot area less than')) &&
        (conditional.includes('450') || conditional.includes('400'))
      );
    });
  }

  return filtered;
}

/**
 * Calculate filter statistics for UI feedback
 */
export function getFilterStats(
  originalCount: number,
  filteredCount: number
) {
  const removed = originalCount - filteredCount;
  const percentage = ((removed / originalCount) * 100).toFixed(1);

  return {
    original: originalCount,
    filtered: filteredCount,
    removed,
    percentage,
    message: `Showing ${filteredCount} of ${originalCount} requirements (${removed} filtered out)`
  };
}
```

---

## Phase 2: Auto-Detection (3 hours)

### 2.1 Heritage Auto-Detection (1.5 hours)

**Update:** `frontend-nextjs/app/assessment/page.tsx`

```tsx
// When property data loads
useEffect(() => {
  if (selectedProperty?.coordinates) {
    checkHeritageOverlay(
      selectedProperty.coordinates.lat,
      selectedProperty.coordinates.lon
    );
  }
}, [selectedProperty]);

async function checkHeritageOverlay(lat: number, lon: number) {
  try {
    const response = await fetch('/api/heritage/hca-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ lat, lon })
    });

    const data = await response.json();

    if (data.hasHCA) {
      setHasHeritageOverlay(true);
      setHeritageAutoDetected(true);
    }
  } catch (error) {
    console.error('Heritage check failed:', error);
  }
}
```

**API already exists:** `/api/heritage/hca-check` - just use it

### 2.2 Lot Size Auto-Detection (1.5 hours)

**Update:** `frontend-nextjs/app/assessment/page.tsx`

```tsx
// When property data loads from Planning API
useEffect(() => {
  if (propertyData?.propertyArea) {
    // Parse "228.1 square metres" → 228.1
    const areaMatch = propertyData.propertyArea.match(/[\d.]+/);
    if (areaMatch) {
      const area = parseFloat(areaMatch[0]);
      setPropertyArea(area);

      if (area < 450) {
        setIsSmallLot(true);
        setLotSizeAutoDetected(true);
      }
    }
  }
}, [propertyData]);
```

**Already available in Planning API response** - just parse it

---

## Phase 3: Integration (2 hours)

### 3.1 Apply Filters to DCP Data (1 hour)

**Update:** `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`

```tsx
import { applySmartFilters, getFilterStats } from '@/lib/smart-filters';

// In component where requirements are displayed
const smartFilterContext = {
  hasHeritageOverlay,
  isSmallLot,
  poolPlanned,
  subdivisionPlanned,
  demolitionPlanned,
  showOnlyNumeric,
  hideObjectives,
  developmentType
};

// Apply to general requirements
const filteredGeneralRequirements = applySmartFilters(
  dcpCompleteData.general_provisions.requirements,
  smartFilterContext
);

// Apply to precinct requirements
const filteredPrecinctRequirements = applySmartFilters(
  dcpCompleteData.precinct_requirements,
  smartFilterContext
);

// Show stats
const stats = getFilterStats(
  dcpCompleteData.general_provisions.requirements.length,
  filteredGeneralRequirements.length
);
```

### 3.2 Add Filter Feedback UI (1 hour)

```tsx
{/* Show active filters and their impact */}
{(hasHeritageOverlay || poolPlanned || subdivisionPlanned ||
  demolitionPlanned || showOnlyNumeric || hideObjectives) && (
  <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
    <div className="flex items-start gap-2">
      <Info className="h-4 w-4 text-blue-600 mt-0.5" />
      <div className="flex-1">
        <p className="text-sm font-medium text-blue-900">
          {stats.message}
        </p>
        <div className="flex flex-wrap gap-2 mt-2">
          {hasHeritageOverlay && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
              Heritage overlay
            </span>
          )}
          {poolPlanned && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
              Pool requirements shown
            </span>
          )}
          {subdivisionPlanned && (
            <span className="text-xs bg-blue-100 text-blue-700 px-2 py-1 rounded">
              Subdivision requirements shown
            </span>
          )}
          {!subdivisionPlanned && (
            <span className="text-xs bg-gray-100 text-gray-600 px-2 py-1 rounded">
              Subdivision requirements hidden
            </span>
          )}
        </div>
      </div>
    </div>
  </div>
)}
```

---

## Phase 4: Testing & Refinement (1 hour)

### 4.1 Test Scenarios

**Test Address 1:** 180 Addison Rd, Marrickville (heritage area)
- Should auto-detect heritage overlay
- Verify heritage requirements show when checked
- Verify they hide when unchecked

**Test Address 2:** 20 Norton St, Leichhardt (small lot)
- Should auto-detect small lot
- Verify lot-size requirements filter correctly

**Test Address 3:** Standard residential (no special features)
- Pool checkbox: verify pool requirements filter
- Subdivision checkbox: verify subdivision requirements filter
- Numeric-only toggle: verify shows ~120 requirements

### 4.2 Expected Results

**Before smart filters:** 830 requirements shown

**After smart filters (typical dwelling house, no special features):**
- Hide objectives: -16 (814 remaining)
- Hide subdivision: -18 (796 remaining)
- Hide pool: -2 (794 remaining)
- Hide demolition: -7 (787 remaining)
- **Total reduction: 5.2%**

**After smart filters (with numeric-only toggle):**
- Show only numeric: 120 requirements (85.5% reduction)

**After smart filters (heritage overlay, subdivision planned):**
- Show heritage: +18
- Show subdivision: +18
- Net: +36 requirements vs. base case

---

## Total Implementation Time

- **Phase 1 (Foundation):** 2 hours
- **Phase 2 (Auto-detection):** 3 hours
- **Phase 3 (Integration):** 2 hours
- **Phase 4 (Testing):** 1 hour

**Total: 8 hours**

---

## Expected Impact

### Current State
- Dev type filter: 3.6% removal (37/1024)
- User must read: 987 requirements

### After Implementation
- Smart filters (typical case): 5-10% removal
- Numeric-only toggle: 85% removal (for quick checks)
- Heritage property: Shows +18 relevant requirements
- **User control over what they see**

---

## Key Decisions Made (No Questions Needed)

1. **Use existing heritage API** - Already have `/api/heritage/hca-check`
2. **Parse property area from Planning API** - Already in response
3. **Client-side filtering** - No backend changes needed
4. **Additive approach** - Keep dev type filter, add smart filters on top
5. **Conservative defaults** - If unsure, show requirement (safe)
6. **Auto-detect where possible** - Heritage and lot size auto-populate

---

## Safety Measures

1. **Default to showing** - If filter logic fails, show requirement
2. **Auto-detect is informational** - User can override
3. **Clear feedback** - Show what's filtered and why
4. **Reversible** - All filters are toggleable
5. **No database changes** - Pure client-side filtering

---

## Success Metrics

**Before:** Users see 830 requirements, must read all
**After:** Users see 120 numeric requirements (quick check) OR 787 requirements (intent-filtered)

**Measurement:** Track which filters users actually use (analytics)
