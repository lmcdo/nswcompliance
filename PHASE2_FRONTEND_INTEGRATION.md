# Phase 2: Frontend Integration

## Overview
Phase 2 frontend integration updates the ComplianceDashboard to use the new zone-applicability API endpoint with priority-based display and adds cross-reference/control code inline display in provision panels.

## Components Created/Updated

### 1. ComplianceDashboardV2.tsx
**New Component** - Modern dashboard using Phase 2 APIs

**Key Features:**
- Uses `/api/provisions/zone-applicability` endpoint
- Priority-based progressive disclosure (1=critical, 6=reference)
- Lazy loading for low-priority provisions
- Fetches enhanced provision data with cross-references

**Usage:**
```typescript
import { ComplianceDashboardV2 } from '@/components/compliance/ComplianceDashboardV2';

<ComplianceDashboardV2
  propertyData={propertyData}
  developmentType="dwelling_house"
/>
```

**Display Structure:**
```
┌─────────────────────────────────────┐
│ Property Header                      │
│ - Quick reference (Zone, Height, FSR)│
│ - Stats (Critical/Important/Reference)│
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 🔴 Critical Provisions (Priority 1-2)│
│ - Overrides                          │
│ - Mandatory numeric controls         │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ 🟠 Important Provisions (Priority 3-4)│
│ - Diagram requirements               │
│ - Conditional provisions             │
└─────────────────────────────────────┘

┌─────────────────────────────────────┐
│ ⚪ Reference Provisions (Priority 5-6)│
│ - Cross-references                   │
│ - General provisions                 │
│ [Show/Hide button for lazy loading] │
└─────────────────────────────────────┘
```

### 2. LegalTextPanel.tsx
**Updated Component** - Added cross-reference and control code display

**New Sections:**
1. **Cross-References** - Shows all references with resolution status
   - Green background for resolved references
   - Red badge for mandatory references
   - Displays target provision reference
   - Shows original reference text

2. **Control Codes** - Shows all individual control codes
   - Blue badges for each code
   - Expanded multi-code provisions (C17-C22 → 6 individual badges)

**Interface Changes:**
```typescript
export interface SelectedProvision {
  constraint: {...};
  provisions: ProvisionContent[];
  // Phase 2 additions:
  crossReferences?: Array<{
    referenceType: string;
    referenceNumber: string;
    referenceText: string;
    targetProvisionId: number | null;
    targetReference: string | null;
    resolutionStatus: string;
    isMandatory: boolean;
  }>;
  controlCodes?: string[];
}
```

**Visual Examples:**

Cross-Reference Display:
```
┌──────────────────────────────────────┐
│ Cross-References (3)                 │
│                                      │
│ ┌─────────────────────────────────┐ │
│ │ SECTION 8.3        [Mandatory]  │ │
│ │ "Refer to Section 8.3"          │ │
│ │ → 8.3                           │ │
│ └─────────────────────────────────┘ │
│                                      │
│ ┌─────────────────────────────────┐ │
│ │ FIGURE 11.1c                    │ │
│ │ "See Figure 11.1c"              │ │
│ └─────────────────────────────────┘ │
└──────────────────────────────────────┘
```

Control Codes Display:
```
┌──────────────────────────────────────┐
│ Control Codes (6)                    │
│                                      │
│ [C17] [C18] [C19] [C20] [C21] [C22] │
└──────────────────────────────────────┘
```

## API Integration Flow

### Zone Applicability Query
```typescript
// 1. Fetch provisions for zone
const response = await fetch(
  `/api/provisions/zone-applicability?zone=${zone}&lga=${lga}&limit=100`
);

const data = await response.json();
// data.data.byPriority = { 1: [...], 2: [...], ..., 6: [...] }

// 2. Display by priority
const highPriority = [...byPriority[1], ...byPriority[2]];
const lowPriority = [...byPriority[5], ...byPriority[6]];
```

### Enhanced Provision Fetch
```typescript
// When user clicks provision, fetch enhanced data
const response = await fetch(`/api/provisions/${provisionId}/enhanced`);
const data = await response.json();

// data.data contains:
// - provisionText
// - applicability (zone, LGA, state-wide)
// - crossReferences (array with resolution status)
// - controlCodes (array of individual codes)
```

## Migration Path

### Option 1: Side-by-Side (Recommended)
Keep both ComplianceDashboard (original) and ComplianceDashboardV2:

```typescript
// In assessment/page.tsx
import { ComplianceDashboard } from '@/components/compliance/ComplianceDashboard';
import { ComplianceDashboardV2 } from '@/components/compliance/ComplianceDashboardV2';

// Feature flag for testing
const useV2 = process.env.NEXT_PUBLIC_USE_DASHBOARD_V2 === 'true';

{useV2 ? (
  <ComplianceDashboardV2 propertyData={selectedProperty} developmentType={developmentType} />
) : (
  <ComplianceDashboard propertyData={selectedProperty} developmentType={developmentType} />
)}
```

### Option 2: Direct Replacement
Replace ComplianceDashboard with V2:

```typescript
// In assessment/page.tsx
import { ComplianceDashboardV2 as ComplianceDashboard } from '@/components/compliance/ComplianceDashboardV2';

// Use as normal
<ComplianceDashboard propertyData={selectedProperty} developmentType={developmentType} />
```

## Performance Improvements

### Before (Original ComplianceDashboard):
- Uses `/api/compliance/constraints` (complex endpoint with multiple lookups)
- No priority-based loading
- All provisions loaded at once
- No cross-reference resolution
- Multi-code provisions not searchable individually

### After (ComplianceDashboardV2):
- Uses `/api/provisions/zone-applicability` (indexed Phase 1 table)
- Priority-based progressive disclosure
- Low-priority provisions lazy-loaded on demand
- Cross-references resolved instantly via FK relationships
- Control codes searchable individually

**Expected Performance:**
- Initial page load: ~100ms (vs ~300ms)
- Provision fetch: ~50ms (vs ~150ms)
- Enhanced provision: ~90ms (includes cross-refs + codes)
- Lazy load low-priority: ~80ms (only when user clicks "Show")

## Testing

### Manual Testing:
1. Start Next.js dev server: `npm run dev` in `frontend-nextjs/`
2. Navigate to `/assessment`
3. Enter test address: "330 Illawarra Road, Marrickville"
4. Verify:
   - Provisions grouped by priority (Critical/Important/Reference)
   - Stats show correct counts
   - Low-priority provisions hidden by default
   - Click "Show" reveals low-priority provisions
   - Click any provision opens panel with cross-references and control codes

### Integration Testing:
```bash
# Ensure database has Phase 1 linking tables populated
python phase1_validation_test.py

# Test API endpoints
python phase2_api_tests.py

# Start Next.js server and test frontend
cd frontend-nextjs
npm run dev
# Visit http://localhost:3000/assessment
```

## Known Limitations

1. **V2 Dashboard Simplifications:**
   - Does not yet integrate Planning API SEPP provisions (only database provisions)
   - Does not include SeppOverlayIndicator component
   - Permission status display not yet implemented
   - Environmental constraints section simplified

2. **Future Enhancements:**
   - Merge Planning API provisions with database provisions
   - Add permission status detection (exempt/complying/consent_required)
   - Implement control code filtering UI
   - Add diagram linking (Phase 3)

## Rollback Plan

If issues arise with V2:

```bash
# In assessment/page.tsx, revert import:
- import { ComplianceDashboardV2 as ComplianceDashboard } from ...
+ import { ComplianceDashboard } from '@/components/compliance/ComplianceDashboard';

# Or set feature flag to false:
NEXT_PUBLIC_USE_DASHBOARD_V2=false
```

Original ComplianceDashboard remains fully functional.

## Next Steps

1. **Test V2 Dashboard:**
   - Verify all provisions display correctly
   - Test cross-reference resolution
   - Confirm control code display

2. **Add Control Code Filters:**
   - Create filter UI component
   - Integrate with `/api/provisions/control-codes` endpoint
   - Allow searching by code (C17, H01, etc.)

3. **Merge SEPP Provisions:**
   - Integrate Planning API SEPP data with database provisions
   - Restore SeppOverlayIndicator
   - Add permission status detection

4. **Phase 3 (Optional):**
   - Implement diagram linking
   - Add visual element display in provision panels
