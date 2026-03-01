# Smart Prioritization Implementation Plan

**Goal:** Organize requirements by actionability, not hide them
**Time:** 3.5 hours
**Approach:** Numeric first, qualitative available, honest UI

---

## Phase 1: Fix the Grandiose Dropdown (30 min)

### Current Problem
```tsx
<label className="text-sm font-semibold">What type of development are you planning?</label>
<p className="text-xs">Select the development type to see relevant planning controls</p>
<select>...</select>
<p className="text-xs">Filters out clearly irrelevant DCP controls</p>
```
**Visual weight:** 4 lines of text + dropdown = looks important
**Actual impact:** 3.6% (37 requirements filtered)

### Solution: One Honest Line

```tsx
<div className="flex items-center gap-2">
  <label className="text-sm text-gray-700">Development:</label>
  <select
    value={developmentType}
    onChange={(e) => setDevelopmentType(e.target.value)}
    className="text-sm px-2 py-1 border rounded"
  >
    {/* existing options */}
  </select>
  <span className="text-xs text-gray-500">(removes commercial signage)</span>
</div>
```

**Visual weight:** 1 line
**Honesty:** Shows what it actually does

**File:** `frontend-nextjs/app/assessment/page.tsx`
**Lines:** ~285-310

---

## Phase 2: Numeric Prioritization (1 hour)

### 2.1 Create Prioritization Logic (30 min)

**New file:** `frontend-nextjs/lib/requirement-prioritization.ts`

```typescript
export interface FilterableRequirement {
  id: number;
  category: string;
  requirement_text: string;
  value_numeric?: number;
  value_min?: number;
  value_max?: number;
  unit?: string;
  section_type?: string;
  // ... existing fields
}

export interface PrioritizedRequirements {
  numeric: FilterableRequirement[];      // Has measurable values
  qualitative: FilterableRequirement[];  // Design principles, character
  objectives: FilterableRequirement[];   // Informational only
}

/**
 * Split requirements into actionable (numeric) vs qualitative
 */
export function prioritizeRequirements(
  requirements: FilterableRequirement[]
): PrioritizedRequirements {
  const numeric: FilterableRequirement[] = [];
  const qualitative: FilterableRequirement[] = [];
  const objectives: FilterableRequirement[] = [];

  for (const req of requirements) {
    // Objectives are purely informational
    if (req.section_type === 'objective') {
      objectives.push(req);
      continue;
    }

    // Numeric requirements have actionable values
    if (req.value_numeric != null || req.value_min != null || req.value_max != null) {
      numeric.push(req);
    } else {
      qualitative.push(req);
    }
  }

  return { numeric, qualitative, objectives };
}

/**
 * Get priority stats for UI feedback
 */
export function getPriorityStats(prioritized: PrioritizedRequirements) {
  const total = prioritized.numeric.length +
                prioritized.qualitative.length +
                prioritized.objectives.length;

  return {
    total,
    numericCount: prioritized.numeric.length,
    qualitativeCount: prioritized.qualitative.length,
    objectivesCount: prioritized.objectives.length,
    numericPercentage: ((prioritized.numeric.length / total) * 100).toFixed(1),
  };
}
```

### 2.2 Update ComplianceDashboard (30 min)

**File:** `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`

```tsx
import { prioritizeRequirements, getPriorityStats } from '@/lib/requirement-prioritization';

// In component, after dev-type filtering
const prioritized = prioritizeRequirements(
  dcpCompleteData.general_provisions.requirements
);
const stats = getPriorityStats(prioritized);

// Display prioritized sections
<div className="space-y-4">
  {/* Numeric Requirements - Show First */}
  <div className="border-l-4 border-blue-500 bg-blue-50 rounded-r-lg p-4">
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        <span className="text-lg">📏</span>
        <h3 className="font-semibold text-blue-900">
          Numeric Requirements ({stats.numericCount})
        </h3>
      </div>
      <Badge className="bg-blue-600 text-white">Action Required</Badge>
    </div>
    <p className="text-sm text-blue-800 mb-4">
      Requirements with specific measurements - check these first
    </p>

    {/* Group by category */}
    {Object.entries(groupByCategory(prioritized.numeric)).map(([category, reqs]) => (
      <CategorySection
        key={category}
        category={category}
        requirements={reqs}
        defaultExpanded={true}
      />
    ))}
  </div>

  {/* Qualitative Requirements - Collapsible */}
  <div className="border-l-4 border-gray-300 rounded-r-lg">
    <button
      onClick={() => setShowQualitative(!showQualitative)}
      className="w-full p-4 hover:bg-gray-50 transition-colors flex items-center justify-between"
    >
      <div className="flex items-center gap-2">
        <span className="text-lg">📋</span>
        <h3 className="font-semibold text-gray-900">
          Qualitative Requirements ({stats.qualitativeCount})
        </h3>
        <span className="text-xs text-gray-500">
          (design principles, character, context)
        </span>
      </div>
      <div className="flex items-center gap-2">
        <span className="text-sm text-gray-600">
          {showQualitative ? 'Collapse' : 'Expand'}
        </span>
        {showQualitative ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </div>
    </button>

    {showQualitative && (
      <div className="p-4 pt-0">
        <p className="text-sm text-gray-600 mb-4 italic">
          These requirements describe design principles and character expectations.
          Less prescriptive but still important for DA approval.
        </p>
        {Object.entries(groupByCategory(prioritized.qualitative)).map(([category, reqs]) => (
          <CategorySection
            key={category}
            category={category}
            requirements={reqs}
            defaultExpanded={false}
          />
        ))}
      </div>
    )}
  </div>

  {/* Objectives - Collapsed by default */}
  {prioritized.objectives.length > 0 && (
    <div className="border-l-4 border-gray-200 rounded-r-lg">
      <button
        onClick={() => setShowObjectives(!showObjectives)}
        className="w-full p-4 hover:bg-gray-50 transition-colors flex items-center justify-between"
      >
        <div className="flex items-center gap-2">
          <span className="text-lg">💡</span>
          <h3 className="font-medium text-gray-700">
            Design Objectives ({stats.objectivesCount})
          </h3>
          <Badge variant="outline" className="text-xs">Informational</Badge>
        </div>
        {showObjectives ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
      </button>

      {showObjectives && (
        <div className="p-4 pt-0">
          <p className="text-sm text-gray-600 mb-4 italic">
            These are design objectives, not compliance requirements.
            Useful for understanding council's intent.
          </p>
          {prioritized.objectives.map(req => (
            <div key={req.id} className="text-sm text-gray-700 mb-2 pl-4 border-l-2 border-gray-200">
              {req.requirement_text}
            </div>
          ))}
        </div>
      )}
    </div>
  )}
</div>
```

**Helper function:**
```tsx
function groupByCategory(requirements: FilterableRequirement[]) {
  return requirements.reduce((acc, req) => {
    if (!acc[req.category]) acc[req.category] = [];
    acc[req.category].push(req);
    return acc;
  }, {} as Record<string, FilterableRequirement[]>);
}
```

---

## Phase 3: Smart Collapse/Expand (2 hours)

### 3.1 Add Optional Filters UI (1 hour)

**File:** `frontend-nextjs/app/assessment/page.tsx`

**Add after dev type dropdown:**

```tsx
{/* Optional: Smart Filters */}
<details className="border-t pt-3 mt-2">
  <summary className="text-sm font-medium text-gray-700 cursor-pointer hover:text-blue-600 flex items-center gap-2">
    <ChevronRight className="h-3 w-3" />
    Optional filters (pool, subdivision, etc.)
  </summary>

  <div className="mt-3 space-y-2 pl-5">
    <label className="flex items-center gap-2 text-sm text-gray-700">
      <input
        type="checkbox"
        checked={showPool}
        onChange={(e) => setShowPool(e.target.checked)}
        className="rounded"
      />
      Show pool/tennis court requirements
    </label>

    <label className="flex items-center gap-2 text-sm text-gray-700">
      <input
        type="checkbox"
        checked={showSubdivision}
        onChange={(e) => setShowSubdivision(e.target.checked)}
        className="rounded"
      />
      Show subdivision requirements
    </label>

    <label className="flex items-center gap-2 text-sm text-gray-700">
      <input
        type="checkbox"
        checked={showDemolition}
        onChange={(e) => setShowDemolition(e.target.checked)}
        className="rounded"
      />
      Show demolition requirements
    </label>

    <p className="text-xs text-gray-500 italic mt-2">
      Unchecked filters collapse related requirements (still accessible)
    </p>
  </div>
</details>
```

**State:**
```tsx
const [showPool, setShowPool] = useState(false);
const [showSubdivision, setShowSubdivision] = useState(false);
const [showDemolition, setShowDemolition] = useState(false);
const [showQualitative, setShowQualitative] = useState(false);
const [showObjectives, setShowObjectives] = useState(false);
```

### 3.2 Apply Smart Collapsing (1 hour)

**Update:** `frontend-nextjs/lib/requirement-prioritization.ts`

```typescript
export interface SmartCollapseConfig {
  showPool: boolean;
  showSubdivision: boolean;
  showDemolition: boolean;
}

export interface CollapsedRequirements {
  visible: FilterableRequirement[];
  collapsed: {
    pool: FilterableRequirement[];
    subdivision: FilterableRequirement[];
    demolition: FilterableRequirement[];
  };
}

/**
 * Organize requirements into visible vs collapsed based on user intent
 */
export function applySmartCollapse(
  requirements: FilterableRequirement[],
  config: SmartCollapseConfig
): CollapsedRequirements {
  const visible: FilterableRequirement[] = [];
  const collapsed = {
    pool: [] as FilterableRequirement[],
    subdivision: [] as FilterableRequirement[],
    demolition: [] as FilterableRequirement[],
  };

  for (const req of requirements) {
    const text = (req.verbatim_source_text || req.requirement_text || '').toLowerCase();

    // Check if pool-related
    const isPool = text.includes('pool') || text.includes('tennis');
    // Check if subdivision-related
    const isSubdivision = text.includes('subdivision') || text.includes('strata');
    // Check if demolition-related
    const isDemolition = text.includes('demolit');

    // Collapse if not showing and is topic-specific
    if (!config.showPool && isPool) {
      collapsed.pool.push(req);
    } else if (!config.showSubdivision && isSubdivision) {
      collapsed.subdivision.push(req);
    } else if (!config.showDemolition && isDemolition) {
      collapsed.demolition.push(req);
    } else {
      visible.push(req);
    }
  }

  return { visible, collapsed };
}
```

**Update ComplianceDashboard:**

```tsx
// Apply smart collapse before prioritization
const smartConfig = { showPool, showSubdivision, showDemolition };
const collapsed = applySmartCollapse(
  dcpCompleteData.general_provisions.requirements,
  smartConfig
);

// Prioritize only visible requirements
const prioritized = prioritizeRequirements(collapsed.visible);

// Show collapsed counts
{(collapsed.collapsed.pool.length > 0 ||
  collapsed.collapsed.subdivision.length > 0 ||
  collapsed.collapsed.demolition.length > 0) && (
  <div className="bg-gray-50 border border-gray-200 rounded-lg p-3 mb-4">
    <p className="text-sm text-gray-700 font-medium mb-2">
      Collapsed requirements (expand in filters):
    </p>
    <div className="flex flex-wrap gap-2">
      {collapsed.collapsed.pool.length > 0 && (
        <Badge variant="outline" className="text-xs">
          Pool/tennis: {collapsed.collapsed.pool.length}
        </Badge>
      )}
      {collapsed.collapsed.subdivision.length > 0 && (
        <Badge variant="outline" className="text-xs">
          Subdivision: {collapsed.collapsed.subdivision.length}
        </Badge>
      )}
      {collapsed.collapsed.demolition.length > 0 && (
        <Badge variant="outline" className="text-xs">
          Demolition: {collapsed.collapsed.demolition.length}
        </Badge>
      )}
    </div>
  </div>
)}
```

---

## Testing Plan (included in 3.5 hours)

### Test Scenario 1: Dwelling House (typical)
1. Select "Dwelling House"
2. Verify numeric requirements show first (~120 items)
3. Verify qualitative collapsed by default
4. Expand qualitative, verify ~700 items show
5. Verify objectives collapsed (~16 items)

### Test Scenario 2: With Pool Filter
1. Check "Show pool requirements"
2. Verify pool requirements appear in numeric section
3. Uncheck "Show pool requirements"
4. Verify "Pool: 2" badge appears in collapsed notice

### Test Scenario 3: Commercial Premises
1. Select "Commercial"
2. Verify solar_access, bedroom_size filtered out
3. Verify numeric requirements still prioritized first

---

## Expected Results

**Before implementation:**
- User sees: 830 requirements in one long list
- Must read: All 830 to find numeric ones
- Dev type dropdown: Looks important, does 3.6%

**After implementation:**
- User sees: 120 numeric requirements first (priority)
- Qualitative: Available but collapsed
- Dev type: Honest one-line UI, still works
- Optional filters: Collapse pool/subdivision/demolition
- Nothing hidden, just organized

---

## Files to Modify

1. **New file:** `frontend-nextjs/lib/requirement-prioritization.ts` (200 lines)
2. **Edit:** `frontend-nextjs/app/assessment/page.tsx` (lines 285-310, add state)
3. **Edit:** `frontend-nextjs/components/compliance/ComplianceDashboard.tsx` (major refactor of display)

---

## Total Time: 3.5 hours

- Phase 1 (Dropdown): 30 min
- Phase 2 (Numeric priority): 1 hour
- Phase 3 (Smart collapse): 2 hours

---

## What We're NOT Doing

❌ Hiding qualitative requirements
❌ Complex 4-tier systems
❌ LLM re-classification
❌ Database changes
❌ Pretending the filter does more than it does

## What We ARE Doing

✅ Prioritize by actionability (numeric first)
✅ Organize by topic (collapse pool/subdivision)
✅ Honest UI (dropdown shows what it does)
✅ Everything still accessible
✅ User controls what they see
