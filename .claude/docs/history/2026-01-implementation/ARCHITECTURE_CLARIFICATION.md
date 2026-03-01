# Architecture Clarification: Why ALL Provisions Get Enriched

## Your Question

> "I thought the idea was to concentrate on provisions likely to be of routine use (~20% actionable), yet ALL provisions get zone/layer/dev-type (100%), not topics (44.8%). What is the structure?"

## The Answer: Filter CASCADE vs Pre-Selection

You're confusing two different architectural approaches:

### ❌ REJECTED Approach: Pre-Selection
```
Filter FIRST (select 20% actionable) → Enrich ONLY those → Show to user
```

**Problem:** Can't filter by zone/layer/dev-type if you haven't tagged them yet!

### ✅ ACTUAL Approach: Filter Cascade
```
Enrich ALL with metadata (100%) → Property filters it → User filters it → 50 provisions
```

---

## The Architecture: How 48,374 Becomes 50

### **Step 1: ENRICH ALL PROVISIONS** (Current Status)

ALL 48,374 provisions must have structural metadata BEFORE we can filter:

| Metadata | Coverage | Purpose |
|----------|----------|---------|
| `v2_dcp_layer` | 100% | Determines WHEN provision applies (always/zone/condition/precinct) |
| `v2_applicable_zones` | 100% | Which zones? (R1, R2, etc. or ALL) |
| `v2_applicable_dev_types` | 100% | Which dev types? (residential, commercial, etc. or ALL) |
| `v2_topic` | 44.8% | WHAT is it about? (setbacks, parking, heritage) - for organization AFTER filtering |

**Why 100%?**
- We don't know which provisions are "relevant" until we know the property details
- A "boilerplate" provision in one scenario might be critical in another
- The Planning Portal API tells us zone/heritage/precinct → we filter by these fields

### **Step 2: PROPERTY ADDRESS FILTERS** (Automatic)

User enters address → Planning Portal API returns:
```json
{
  "zone": "R2",
  "heritage": false,
  "precinct": "Precinct 12",
  "flood": false
}
```

Database query filters 48,374 → **~400 provisions**:

```sql
WHERE lga = 'Marrickville'                              -- 48,374 → 5,500
  AND ('R2' = ANY(v2_applicable_zones) OR 'ALL' = ANY(v2_applicable_zones))  -- → 800
  AND (v2_dcp_layer = 'generic'                         -- → 400
       OR (v2_dcp_layer = 'precinct' AND v2_precinct_id = 'precinct_12')
       OR (v2_dcp_layer = 'use_specific')
      )
  AND NOT (v2_site_condition_required = 'heritage' AND heritage = false)  -- → 400
```

### **Step 3: USER SELECTION FILTERS** (Dropdown)

User selects:
- Dev type: `dwelling_addition_rear`
- Assessment: `CDC` (Complying Development)

Further filters **400 → ~50 provisions**:

```sql
  AND ('dwelling_addition_rear' = ANY(v2_applicable_dev_types) OR 'ALL' = ANY(v2_applicable_dev_types))  -- → 90
  AND (assessment_type != 'CDC' OR v2_provision_type = 'control')  -- → 50
```

### **Step 4: DISPLAY** (Grouped by Topic)

The 50 provisions are organized by topic for readability:
- Setbacks (12 provisions)
- Height (8 provisions)
- Privacy (6 provisions)
- Parking (11 provisions)
- Landscaping (9 provisions)
- Other (4 provisions)

**This is why topics are only 44.8%** - they're for organization, not filtering.

---

## What Happened to "Actionable" Classification?

### Original Plan (INDEX.md)
- Classify provisions: 11,835 actionable / 36,539 boilerplate
- Focus workflow on actionable provisions (~24%)

### Current Status (Database)
- **ALL provisions have `v2_is_actionable = False`**
- The November 22 backup didn't include this classification
- Or the classification was never applied to the full dataset

### Why It Doesn't Matter for Current Architecture

The filter cascade REPLACES actionable classification:

| Old Approach | New Approach |
|--------------|--------------|
| Pre-filter to 20% "actionable" | Include all provisions in enrichment |
| Then apply property filters | Property filters reduce to relevant subset |
| | User selections further reduce to ~50 |

**The "actionable" provisions emerge naturally from the cascade:**
- Generic boilerplate gets filtered out by dev-type specificity
- TOC entries get filtered out by lack of controls
- Definitions get filtered out by assessment type (CDC)

---

## Why ALL Provisions Need Structural Metadata

Consider this "boilerplate" example:

```
"Land use zones"
```

Is this actionable? **IT DEPENDS:**

- For a property in R2 zone → This provision defines what R2 means → **RELEVANT**
- For Complying Development → Not a control → **FILTERED OUT**
- For a property in B4 zone → Irrelevant → **FILTERED OUT**

**We can't pre-classify this without knowing the property context.**

That's why:
- ✅ ALL provisions get `v2_applicable_zones` (even if it's `['ALL']`)
- ✅ ALL provisions get `v2_dcp_layer` (even if it's `generic`)
- ✅ ALL provisions get `v2_applicable_dev_types` (even if it's `['ALL']`)
- ⚠️ Only SOME get `v2_topic` (because many don't fit semantic categories)

---

## Summary: The Structure

```
┌─────────────────────────────────────────────────┐
│  DATABASE: 48,374 provisions                    │
│  ALL enriched with structural metadata (100%)   │
│  - v2_dcp_layer                                 │
│  - v2_applicable_zones                          │
│  - v2_applicable_dev_types                      │
│  SOME enriched with semantic metadata (44.8%)   │
│  - v2_topic (for organization)                  │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  PROPERTY FILTERS (Planning Portal API)         │
│  - LGA: Marrickville                            │
│  - Zone: R2                                     │
│  - Heritage: false                              │
│  - Precinct: 12                                 │
│  Result: ~400 provisions                        │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  USER SELECTION FILTERS (Dropdowns)             │
│  - Dev type: dwelling_addition_rear             │
│  - Assessment: CDC                              │
│  Result: ~50 provisions                         │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│  DISPLAY (Grouped by Topic)                     │
│  - Setbacks (12)                                │
│  - Height (8)                                   │
│  - Privacy (6)                                  │
│  - Parking (11)                                 │
│  - Landscaping (9)                              │
│  - Other (4)                                    │
└─────────────────────────────────────────────────┘
```

**The "20% actionable" emerge from the cascade, not pre-selection.**

The current database state (v2_is_actionable = all False) indicates this field is either:
1. Not yet populated
2. Deprecated in favor of the filter cascade approach
3. Lost during the database recovery

The system works correctly without it because the cascade filtering achieves the same goal.
