# Implementation Plan: DQ-16 Heritage Topic Consolidation

## Problem Statement
Ashfield Heritage chapter provisions (364 total) are fragmented across multiple topics:
- Heritage: 187 (category='heritage')
- Character: 80 (category='character')
- Fencing: 22, Streetscape: 22, Setback Front: 11, etc.

All 364 are from `part_name='Heritage'` and are heritage-specific controls.
User sees them as separate topics, causing confusion.

## Goal
Consolidate all Heritage chapter provisions under single "Heritage" topic, with subcategory grouping.

## Pre-Implementation Verification

### 1. Confirm Ashfield-only scope
- [x] Ashfield: part_name='Heritage' → 364 provisions, split by category
- [x] Marrickville: part_name='Heritage' → 12 provisions, category mostly 'heritage'/'landscaping'
- [x] Leichhardt: No part_name='Heritage', has "Connections (Heritage and Transport)" which is NOT heritage

### 2. Confirm query path
- [x] Only `queryHeritageFromDcpGeneralRequirements()` in `for-property/route.ts` is affected
- [x] `dcp-complete` API uses different logic (not affected)
- [x] Other APIs don't touch this query

### 3. Confirm no topics become empty
- [x] Every topic has provisions from non-Heritage parts
- [x] Character: 80 from Heritage, 15 from other parts → 15 remain
- [x] BUT: Those 15 are orphaned (DQ-17) - not currently returned by API

## Implementation Steps

### Step 1: Modify API Query (for-property/route.ts)
**File:** `frontend-nextjs/app/api/provisions/for-property/route.ts`
**Function:** `queryHeritageFromDcpGeneralRequirements()` (lines 350-389)

**Current:**
```sql
SELECT
  ...
  INITCAP(REPLACE(category, '_', ' ')) as v2_topic,
  ...
FROM dcp_general_requirements
WHERE (category = 'heritage' OR part_name ILIKE '%Heritage%')
```

**Change to:**
```sql
SELECT
  ...
  CASE
    WHEN part_name = 'Heritage' THEN 'Heritage'
    ELSE INITCAP(REPLACE(category, '_', ' '))
  END as v2_topic,
  INITCAP(REPLACE(category, '_', ' ')) as v2_heritage_subcategory,
  ...
FROM dcp_general_requirements
WHERE (category = 'heritage' OR part_name = 'Heritage')
```

**Also remove Leichhardt false positive:**
- Change: `part_name ILIKE '%Heritage%'`
- To: `part_name = 'Heritage'`
- Reason: "Connections (Heritage and Transport)" is transport, not heritage

### Step 2: Update TypeScript Types
**File:** `frontend-nextjs/components/compliance/ProvisionsByTopic.tsx`

Add to Provision interface:
```typescript
v2_heritage_subcategory?: string;
```

### Step 3: Update UI to Show Subcategory Grouping
**File:** `frontend-nextjs/components/compliance/ProvisionsByTopic.tsx`

Within Heritage topic rendering, group by `v2_heritage_subcategory`:
- Show collapsible sections: "Character (80)", "Fencing (22)", "Heritage (187)", etc.
- Each subcategory section shows its provisions
- Default expanded: show all

### Step 4: Verify Other Councils Not Affected
After implementation, verify:
- Marrickville: Still returns category='heritage' provisions correctly
- Leichhardt: No longer returns "Connections" part provisions incorrectly

## Expected Outcome

**Before:**
```
Topics:
  Heritage: 187
  Character: 80
  Fencing: 22
  Streetscape: 22
  ...
```

**After:**
```
Topics:
  Heritage: 364
    └─ Heritage (187)
    └─ Character (80)
    └─ Fencing (22)
    └─ Streetscape (22)
    └─ ...
```

## Rollback Plan
If issues arise:
1. Revert API change (single line)
2. UI gracefully handles missing `v2_heritage_subcategory` (already optional)

## Testing Checklist
- [ ] Ashfield heritage property: Heritage shows 364, subcategorized
- [ ] Ashfield non-heritage property: No condition layer provisions
- [ ] Marrickville heritage property: Heritage provisions still work
- [ ] Leichhardt heritage property: No false positives from "Connections" part
- [ ] Character topic for Ashfield: Should now be empty (or show orphaned 15 if DQ-17 fixed)

## Files to Modify
1. `frontend-nextjs/app/api/provisions/for-property/route.ts` - API query
2. `frontend-nextjs/components/compliance/ProvisionsByTopic.tsx` - UI grouping
