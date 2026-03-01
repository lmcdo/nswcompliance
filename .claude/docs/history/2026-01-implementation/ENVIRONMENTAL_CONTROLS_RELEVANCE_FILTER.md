# Environmental Controls Relevance Filter - Design Document

## Problem Statement

The NSW Planning Portal returns **6 environmental controls** for 180 Addison Rd, Marrickville:
1. ✅ **SEPP Water Use 40%** - RELEVANT (applies to all new dwellings)
2. ✅ **SEPP Climate Zone 56** - RELEVANT (applies to new buildings)
3. ✅ **SEPP Climate Zone 5** - RELEVANT (applies to alterations)
4. ❌ **Thermal Energy from Waste Prohibition** - IRRELEVANT (only affects industrial waste facilities)
5. ⚠️ **Acid Sulfate Soils Class 5** - BORDERLINE (Class 5 = no action required, but informational)
6. ⚠️ **Tree Canopy 21.95%** - BORDERLINE (informational, may affect tree preservation)

**Current behavior:** All 6 displayed
**Desired behavior:** Filter out #4, optionally show #5-6 with context

---

## Existing Relevance Filter Code

### Location
`frontend-nextjs/components/compliance/ComplianceDashboard.tsx`
- Lines 90-159: `extractPlanningAPIProvisions()`

### Current Logic
```typescript
// Extracts ALL Special Provisions from NSW Planning API
// No filtering based on development type or property characteristics
specialProvisionsLayer.results.forEach((result) => {
  provisions.push({
    type: 'special',
    value: displayValue,
    description: description,
    source: { authority_level: 'SEPP' }
  });
});
```

**Result:** Everything from Planning API is displayed

---

## Relevance Filter Strategy

### Principle: Conservative Filtering
- **Never filter controls that might have edge cases**
- **Only filter controls that are 100% irrelevant to the development type**
- **Provide clear reasoning in UI when controls are shown but don't require action**

### Filter Categories

#### Category 1: ALWAYS IRRELEVANT (Safe to filter)
- Thermal Energy from Waste Prohibition (for residential properties)
- Industrial zone overlays (for non-industrial development)
- Mining/extractive industry controls (for non-mining development)

#### Category 2: INFORMATIONAL ONLY (Show with context)
- Tree Canopy Coverage (informational reference)
- Acid Sulfate Soils Class 5 (lowest risk, no management required)
- Contaminated land Class 5 (no action required)

#### Category 3: CONDITIONALLY RELEVANT (Always show)
- BASIX Water/Energy (always relevant for new dwellings/alterations)
- Flood/Bushfire overlays (even if not in affected area, shows clearance)
- Heritage (even if not heritage, shows clearance)

---

## Implementation Approach

### Option 1: Filter in `extractPlanningAPIProvisions()` (Frontend)

**Pros:**
- Quick to implement
- No database changes
- Can be updated easily

**Cons:**
- Business logic in frontend
- Harder to maintain across different pages
- Can't be reused by API consumers

### Option 2: Filter in `/api/compliance/constraints` (Backend)

**Pros:**
- Centralized business logic
- Consistent across all API consumers
- Easier to test and maintain

**Cons:**
- Planning API provisions bypass the constraints API currently
- Would need refactoring

### Option 3: Hybrid Approach (RECOMMENDED)

**Filter in frontend with clear separation:**
1. Create `lib/relevance-filters.ts` with reusable filter functions
2. Apply filters in `extractPlanningAPIProvisions()`
3. Add optional "Show all controls" toggle for power users

---

## Proposed Filter Rules

### Rule 1: Development Type Filter

```typescript
interface FilterContext {
  developmentType: string;
  zone: string;
  propertyUse: 'residential' | 'commercial' | 'industrial' | 'mixed';
}

function isRelevantControl(
  control: PlanningAPIControl,
  context: FilterContext
): boolean {
  const { developmentType, propertyUse } = context;
  const controlType = control.Type || '';
  const epiName = control['EPI Name'] || '';

  // Rule 1: Thermal waste prohibition only relevant for industrial
  if (controlType.toLowerCase().includes('thermal') &&
      controlType.toLowerCase().includes('waste')) {
    return propertyUse === 'industrial';
  }

  // Rule 2: BASIX always relevant for residential development
  if (epiName.includes('Sustainable Buildings')) {
    return true; // Always show BASIX
  }

  // Rule 3: Tree canopy is informational only
  if (controlType.toLowerCase().includes('tree canopy')) {
    return false; // Filter out, can be added to metadata instead
  }

  // Default: show control (conservative approach)
  return true;
}
```

### Rule 2: Risk Level Filter

```typescript
function requiresAction(control: PlanningAPIControl): boolean {
  const classValue = control.Class || '';
  const type = control.Type || '';

  // Acid Sulfate Soils Class 5 = no action required
  if (type.includes('Acid Sulfate') && classValue === 'Class 5') {
    return false;
  }

  // Contaminated land Class 5 = no action required
  if (type.includes('Contamination') && classValue === 'Class 5') {
    return false;
  }

  // Default: assume action required
  return true;
}
```

---

## UI Enhancement Proposal

### Before Filtering
```
🌳 Environmental Constraints (6)
  • SEPP Water Use: 40%
  • SEPP Climate Zone: Class 56
  • SEPP Climate Zone: Class 5
  • Thermal Energy from Waste: Greater Sydney Prohibition
  • Acid Sulfate Soils: Class 5
  • Tree Canopy: 21.95%
```

### After Filtering (Option A: Hide completely)
```
🌳 Environmental Constraints (3)
  • SEPP Water Use: 40% (BASIX certificate required)
  • SEPP Climate Zone: Class 56 (New buildings)
  • SEPP Climate Zone: Class 5 (Alterations)
```

### After Filtering (Option B: Show with context - RECOMMENDED)
```
🌳 Environmental Constraints (3 require action, 2 informational)

BASIX Requirements:
  • Water Use: 40% minimum efficiency
  • Climate Zone (Buildings): Class 56
  • Climate Zone (Alterations): Class 5

Environmental Clearances:
  ✓ Acid Sulfate Soils: Class 5 (No management plan required)
  ℹ️ Tree Canopy: 21.95% existing coverage
```

---

## Edge Cases to Consider

### Case 1: Thermal Waste + Industrial Property
**Scenario:** Industrial property in Greater Sydney
**Filter behavior:** Show prohibition (relevant for industrial use)

### Case 2: Acid Sulfate Class 1-4
**Scenario:** Property in high-risk acid sulfate area
**Filter behavior:** Always show (requires management plan)

### Case 3: Tree Canopy + Heritage Area
**Scenario:** Property in HCA with significant trees
**Filter behavior:** Show tree canopy (relevant for tree preservation)

### Case 4: Flood/Bushfire Clearance
**Scenario:** Property NOT in flood/bushfire zone
**Filter behavior:** Show as clearance/exemption (confirms no constraints)

---

## Recommended Implementation

### Step 1: Create relevance filter utility

**File:** `frontend-nextjs/lib/environmental-relevance-filter.ts`

```typescript
export interface EnvironmentalControl {
  Type: string;
  Class: string;
  'EPI Name': string;
  'Map Type': string;
  title: string;
}

export interface FilterContext {
  developmentType: string;
  zone: string;
  isResidential: boolean;
  isCommercial: boolean;
  isIndustrial: boolean;
}

export interface FilterResult {
  isRelevant: boolean;
  requiresAction: boolean;
  reason?: string;
}

export function assessControlRelevance(
  control: EnvironmentalControl,
  context: FilterContext
): FilterResult {
  const type = (control.Type || '').toLowerCase();
  const classValue = control.Class || '';
  const epiName = control['EPI Name'] || '';

  // BASIX - always relevant for residential
  if (epiName.includes('Sustainable Buildings')) {
    return {
      isRelevant: true,
      requiresAction: true,
      reason: 'BASIX certificate required for new dwellings/alterations'
    };
  }

  // Thermal waste - only relevant for industrial
  if (type.includes('thermal') && type.includes('waste')) {
    if (context.isIndustrial) {
      return {
        isRelevant: true,
        requiresAction: true,
        reason: 'Thermal waste facilities prohibited'
      };
    }
    return {
      isRelevant: false,
      requiresAction: false,
      reason: 'Not applicable to residential development'
    };
  }

  // Acid Sulfate Soils
  if (type.includes('acid sulfate') || type.includes('ass')) {
    if (classValue === 'Class 5') {
      return {
        isRelevant: true,
        requiresAction: false,
        reason: 'Class 5 = lowest risk, no management plan required'
      };
    }
    return {
      isRelevant: true,
      requiresAction: true,
      reason: `Class ${classValue} requires acid sulfate soil management plan`
    };
  }

  // Tree Canopy
  if (type.includes('tree canopy') || type.includes('canopy cover')) {
    return {
      isRelevant: true,
      requiresAction: false,
      reason: 'Informational - reference for tree preservation requirements'
    };
  }

  // Default: show everything else
  return {
    isRelevant: true,
    requiresAction: true,
    reason: undefined
  };
}
```

### Step 2: Apply filter in ComplianceDashboard

```typescript
// In extractPlanningAPIProvisions()
import { assessControlRelevance } from '@/lib/environmental-relevance-filter';

const filterContext = {
  developmentType: developmentType || 'dwelling_house',
  zone: propertyData.constraints?.zone || '',
  isResidential: ['R1', 'R2', 'R3', 'R4'].some(z =>
    propertyData.constraints?.zone?.startsWith(z)
  ),
  isCommercial: ['B1', 'B2', 'B3', 'B4', 'B5', 'B6'].some(z =>
    propertyData.constraints?.zone?.startsWith(z)
  ),
  isIndustrial: ['IN1', 'IN2', 'IN3'].some(z =>
    propertyData.constraints?.zone?.startsWith(z)
  )
};

special ProvisionsLayer.results.forEach((result) => {
  const relevance = assessControlRelevance(result, filterContext);

  // Only add if relevant
  if (relevance.isRelevant) {
    provisions.push({
      type: 'special',
      value: displayValue,
      description: relevance.reason || description,
      requiresAction: relevance.requiresAction,
      // ... rest of fields
    });
  }
});
```

### Step 3: UI Enhancement

```typescript
// Group controls by requiresAction
const actionRequired = provisions.filter(p => p.requiresAction);
const informationalOnly = provisions.filter(p => !p.requiresAction);

<CardHeader>
  <CardTitle>
    🌳 Environmental Constraints
    ({actionRequired.length} require action
    {informationalOnly.length > 0 && `, ${informationalOnly.length} informational`})
  </CardTitle>
</CardHeader>
```

---

## Testing Plan

### Test Case 1: R2 Residential (180 Addison Rd)
**Input:** R2 zone, dwelling_house
**Expected:**
- ✅ Show: BASIX Water (40%)
- ✅ Show: BASIX Climate (56, 5)
- ❌ Hide: Thermal waste prohibition
- ⚠️ Show as informational: Acid Sulfate Class 5
- ⚠️ Show as informational: Tree Canopy

### Test Case 2: IN1 Industrial
**Input:** IN1 zone, warehouse
**Expected:**
- ✅ Show: Thermal waste prohibition (relevant)
- ❌ Hide: BASIX (not applicable to industrial)
- ✅ Show: Acid Sulfate (if present)

### Test Case 3: B2 Commercial
**Input:** B2 zone, shop_top_housing
**Expected:**
- ✅ Show: BASIX (residential component)
- ❌ Hide: Thermal waste
- ✅ Show: All other overlays

---

## Decision Matrix

| Control Type | Residential | Commercial | Industrial | Action |
|-------------|-------------|------------|------------|--------|
| BASIX Water/Energy | ✅ Show | ✅ Show (if dwelling) | ❌ Hide | Required |
| Thermal Waste | ❌ Hide | ❌ Hide | ✅ Show | Required |
| Acid Sulfate Class 5 | ⚠️ Show | ⚠️ Show | ⚠️ Show | Informational |
| Acid Sulfate Class 1-4 | ✅ Show | ✅ Show | ✅ Show | Required |
| Tree Canopy | ⚠️ Show | ⚠️ Show | ⚠️ Show | Informational |
| Flood/Bushfire | ✅ Show | ✅ Show | ✅ Show | Conditional |

---

## Recommendation

**Implement Option B (Show with context) using the hybrid approach:**

1. Create `environmental-relevance-filter.ts` utility
2. Filter thermal waste for non-industrial properties
3. Keep acid sulfate/tree canopy but mark as "informational"
4. Group controls in UI: "Action Required" vs "Informational"
5. Add optional "Show all controls" toggle for power users

**Benefits:**
- Conservative approach (doesn't hide edge cases)
- Clear user communication (why controls are shown)
- Maintainable (centralized filter logic)
- Flexible (can be extended for other control types)

**Estimated effort:** 2-3 hours implementation + testing
