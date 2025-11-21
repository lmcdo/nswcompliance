# SEPP Mapping System - Complete Explanation

## Problem: Three Different Naming Conventions

### 1. **NSW Planning Portal API** (what we receive)
Returns SEPP names in "Special Provisions" layer results:

```javascript
{
  "EPI Name": "State Environmental Planning Policy (Sustainable Buildings) 2022",
  "EPI Type": "SEPP",
  "Map Type": "CLM",  // Climate zone map
  "Class": "56",      // Zone 56
  "Label": "2045"     // Postcode
}
```

**Full list of SEPPs the Portal can return:**
- State Environmental Planning Policy (Sustainable Buildings) 2022
- State Environmental Planning Policy (Transport and Infrastructure) 2021
- State Environmental Planning Policy (Housing) 2021
- State Environmental Planning Policy (Biodiversity and Conservation) 2017/2021
- State Environmental Planning Policy (Exempt and Complying Development Codes) 2008
- State Environmental Planning Policy (Planning Systems) 2021
- State Environmental Planning Policy (Resilience and Hazards) 2021
- State Environmental Planning Policy (Industry and Employment) 2021
- State Environmental Planning Policy (Primary Production) 2021
- State Environmental Planning Policy (Precincts—Regional) 2021
- State Environmental Planning Policy (Precincts—Central River City) 2021
- State Environmental Planning Policy (Precincts—Eastern Harbour City) 2021
- State Environmental Planning Policy (Precincts—Western Parkland City) 2021

### 2. **App Identifiers** (what we currently convert to)

Current logic in `nsw-planning-portal.ts` line 565-573:

```typescript
const seppMatch = value.match(/sepp[^\d]*(\d+)/i) ||
                  value.match(/state environmental planning policy[^\d]*(\d+)/i);
if (seppMatch) {
  const seppNumber = seppMatch[1];  // Extracts year only!
  const seppIdentifier = `SEPP_${seppNumber}`;  // e.g., "SEPP_2022"
}
```

**Problem:** This loses specificity!
- "SEPP_2022" - Could be Sustainable Buildings, Resilience, Infrastructure...
- "SEPP_2021" - Could be Housing, Transport, Planning Systems, Industry, Primary Production...

### 3. **Database document_ids** (what actually exists)

Query results show **104 SEPP documents** with **24,869 total provisions**:

#### Main SEPPs (no underscores):
```
State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation
  └─ 8,502 provisions

State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation
  └─ 6,138 provisions

State_Environmental_Planning_Policy_Housing_2021__NSW_Legislation
  └─ 2,784 provisions

State_Environmental_Planning_Policy_Biodiversity_and_Conservation_2021__NSW_Legislation
  └─ 2,100 provisions

State_Environmental_Planning_Policy_Planning_Systems_2021__NSW_Legislation
  └─ 1,302 provisions

State_Environmental_Planning_Policy_Industry_and_Employment_2021__NSW_Legislation
  └─ 860 provisions

State_Environmental_Planning_Policy_Primary_Production_2021__NSW_Legislation
  └─ 518 provisions

State_Environmental_Planning_Policy_Resilience_and_Hazards_2021__NSW_Legislation
  └─ 426 provisions

State_Environmental_Planning_Policy_Sustainable_Buildings_2022__NSW_Legislation
  └─ 292 provisions
```

#### Section-specific documents (with underscores + section suffixes):
```
State_Environmental_Planning_Policy_(Industry_and_Employment)_2021___NSW_Legislation
  └─ 442 provisions

State_Environmental_Planning_Policy_(Exempt_and_Complying_Development_Codes)_2008___NSW_Legislation_section_6
  └─ 141 provisions

State_Environmental_Planning_Policy_(Housing)_2021___NSW_Legislation_section_27
  └─ 72 provisions

... (100+ more section-specific documents)
```

---

## The Current Mapping Problem

### Example: 36 Dalhousie St, Haberfield

**Step 1:** Planning Portal API returns:
```json
{
  "Special Provisions": [
    { "EPI Name": "State Environmental Planning Policy (Sustainable Buildings) 2022" },
    { "EPI Name": "State Environmental Planning Policy (Transport and Infrastructure) 2021" }
  ]
}
```

**Step 2:** App converts to:
```javascript
applicableSepps = ["SEPP_2022", "SEPP_2021"]  // ❌ Lost specificity!
```

**Step 3:** App tries to query database:
```sql
SELECT * FROM regulatory_provisions
WHERE document_id LIKE '%SEPP_2022%'  -- ❌ No match!
```

**Step 4:** Result:
```
No provisions found for SEPP: SEPP_2022
No provisions found for SEPP: SEPP_2021
```

**Why:** Database has `State_Environmental_Planning_Policy_Sustainable_Buildings_2022__NSW_Legislation` (292 provisions) but we're searching for generic "SEPP_2022".

---

## The Solution: Proper Name Mapping

### Strategy A: Direct Name Mapping (Recommended)

Convert Planning Portal names DIRECTLY to database document_id format:

```typescript
// In nsw-planning-portal.ts
function mapPortalSeppToDocumentId(portalName: string): string {
  // "State Environmental Planning Policy (Sustainable Buildings) 2022"
  // → "State_Environmental_Planning_Policy_Sustainable_Buildings_2022__NSW_Legislation"

  return portalName
    .replace(/\s+/g, '_')                    // Spaces → underscores
    .replace(/[()]/g, '')                    // Remove parentheses
    .replace(/__+/g, '_')                    // Collapse multiple underscores
    + '__NSW_Legislation';                   // Add suffix
}
```

**Mapping table:**

| Planning Portal Name | Database document_id |
|---------------------|---------------------|
| State Environmental Planning Policy (Sustainable Buildings) 2022 | `State_Environmental_Planning_Policy_Sustainable_Buildings_2022__NSW_Legislation` |
| State Environmental Planning Policy (Transport and Infrastructure) 2021 | `State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation` |
| State Environmental Planning Policy (Housing) 2021 | `State_Environmental_Planning_Policy_Housing_2021__NSW_Legislation` |
| State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 | `State_Environmental_Planning_Policy_Exempt_and_Complying_Development_Codes_2008__NSW_Legislation` |
| State Environmental Planning Policy (Biodiversity and Conservation) 2021 | `State_Environmental_Planning_Policy_Biodiversity_and_Conservation_2021__NSW_Legislation` |

### Strategy B: Maintain Identifier + Lookup Table

Keep using identifiers like "SEPP_SUSTAINABLE_BUILDINGS_2022" but with proper mapping:

```typescript
// In sepp-router.ts - Update SEPP_MAPPINGS
const SEPP_MAPPINGS: SeppMapping[] = [
  {
    identifier: 'SEPP_SUSTAINABLE_BUILDINGS_2022',
    name: 'SEPP (Sustainable Buildings) 2022',
    portal_names: ['State Environmental Planning Policy (Sustainable Buildings) 2022'],
    database_patterns: [
      'State_Environmental_Planning_Policy_Sustainable_Buildings_2022__NSW_Legislation',
      'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation'
    ],
    provision_count: 292
  },
  {
    identifier: 'SEPP_TRANSPORT_INFRASTRUCTURE_2021',
    name: 'SEPP (Transport and Infrastructure) 2021',
    portal_names: ['State Environmental Planning Policy (Transport and Infrastructure) 2021'],
    database_patterns: [
      'State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation',
      'State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021___NSW_Legislation'
    ],
    provision_count: 6138
  },
  // ... etc
];
```

---

## Implementation Plan

### Phase 1: Fix Portal → Identifier Mapping ✅ RECOMMENDED

**File:** `frontend-nextjs/lib/nsw-planning-portal.ts`

**Change line 565-573 from:**
```typescript
const seppMatch = value.match(/sepp[^\d]*(\d+)/i);  // ❌ Year only!
const seppIdentifier = `SEPP_${seppNumber}`;
```

**To:**
```typescript
function extractSeppIdentifier(portalName: string): string {
  // Extract specific SEPP type from portal name
  const seppPatterns = [
    { pattern: /sustainable buildings/i, id: 'SEPP_SUSTAINABLE_BUILDINGS_2022' },
    { pattern: /transport.*infrastructure/i, id: 'SEPP_TRANSPORT_INFRASTRUCTURE_2021' },
    { pattern: /housing/i, id: 'SEPP_HOUSING_2021' },
    { pattern: /biodiversity.*conservation/i, id: 'SEPP_BIODIVERSITY_CONSERVATION_2021' },
    { pattern: /exempt.*complying/i, id: 'SEPP_EXEMPT_COMPLYING_2008' },
    { pattern: /planning systems/i, id: 'SEPP_PLANNING_SYSTEMS_2021' },
    { pattern: /resilience.*hazards/i, id: 'SEPP_RESILIENCE_HAZARDS_2021' },
    { pattern: /industry.*employment/i, id: 'SEPP_INDUSTRY_EMPLOYMENT_2021' },
    { pattern: /primary production/i, id: 'SEPP_PRIMARY_PRODUCTION_2021' }
  ];

  for (const { pattern, id } of seppPatterns) {
    if (pattern.test(portalName)) return id;
  }

  // Fallback to year-based (but warn)
  const yearMatch = portalName.match(/(\d{4})/);
  if (yearMatch) {
    console.warn(`[SEPP] Unknown SEPP type, using year: ${portalName}`);
    return `SEPP_${yearMatch[1]}`;
  }

  return 'SEPP_UNKNOWN';
}
```

### Phase 2: Fix Identifier → Database Mapping ✅ REQUIRED

**File:** `frontend-nextjs/lib/sepp-router.ts`

**Update SEPP_MAPPINGS with correct database_patterns:**

```typescript
const SEPP_MAPPINGS: SeppMapping[] = [
  {
    identifier: 'SEPP_SUSTAINABLE_BUILDINGS_2022',
    name: 'SEPP (Sustainable Buildings) 2022',
    database_patterns: [
      'State_Environmental_Planning_Policy_Sustainable_Buildings_2022__NSW_Legislation',
      'State_Environmental_Planning_Policy_(Sustainable_Buildings)_2022___NSW_Legislation'
    ],
    description: 'BASIX, energy efficiency, water use standards'
  },
  {
    identifier: 'SEPP_TRANSPORT_INFRASTRUCTURE_2021',
    name: 'SEPP (Transport and Infrastructure) 2021',
    database_patterns: [
      'State_Environmental_Planning_Policy_Transport_and_Infrastructure_2021__NSW_Legislation',
      'State_Environmental_Planning_Policy_(Transport_and_Infrastructure)_2021___NSW_Legislation'
    ],
    description: 'Roads, railways, ports, telecommunications'
  },
  // ... etc (add all 9 main SEPPs)
];
```

### Phase 3: Query Database Correctly ✅ CRITICAL

**File:** `frontend-nextjs/lib/sepp-router.ts`

**Fix findProvisionsForSepp() method:**

```typescript
private findProvisionsForSepp(seppId: string, seppData: any[]): any[] {
  const mapping = SEPP_MAPPINGS.find(m => m.identifier === seppId);

  if (!mapping) {
    console.warn(`No mapping found for SEPP: ${seppId}`);
    return [];
  }

  // Query database using correct document_id patterns
  const query = `
    SELECT *
    FROM regulatory_provisions
    WHERE ${mapping.database_patterns.map((pattern, i) =>
      `document_id ILIKE '%${pattern}%'`
    ).join(' OR ')}
    LIMIT 100
  `;

  // Execute query and return provisions
}
```

---

## Expected Results After Fix

### For 36 Dalhousie St, Haberfield:

**Before Fix:**
```
Added SEPP identifier: SEPP_2022
Added SEPP identifier: SEPP_2021
No provisions found for SEPP: SEPP_2022  ❌
No provisions found for SEPP: SEPP_2021  ❌
```

**After Fix:**
```
Added SEPP identifier: SEPP_SUSTAINABLE_BUILDINGS_2022
Added SEPP identifier: SEPP_TRANSPORT_INFRASTRUCTURE_2021
Matched 292 provisions for SEPP_SUSTAINABLE_BUILDINGS_2022  ✅
Matched 6,138 provisions for SEPP_TRANSPORT_INFRASTRUCTURE_2021  ✅
```

---

## Complete SEPP Database Coverage

| SEPP | Main Document Provisions | Section Documents | Total |
|------|-------------------------|-------------------|-------|
| Exempt and Complying 2008 | 8,502 | ~3,000 | ~11,500 |
| Transport and Infrastructure 2021 | 6,138 | 174 | 6,312 |
| Housing 2021 | 2,784 | ~1,000 | ~3,784 |
| Biodiversity and Conservation 2021 | 2,100 | 96 | 2,196 |
| Planning Systems 2021 | 1,302 | 394 | 1,696 |
| Industry and Employment 2021 | 860 | 442 | 1,302 |
| Primary Production 2021 | 518 | 234 | 752 |
| Resilience and Hazards 2021 | 426 | 207 | 633 |
| Sustainable Buildings 2022 | 292 | 149 | 441 |
| **TOTAL** | **22,922** | **~6,000** | **~28,922** |

---

## Summary

### Question 1: "What is the range of possible SEPP values that the planning portal will use?"

**Answer:** The Portal returns full SEPP names in the "EPI Name" field like:
- "State Environmental Planning Policy (Sustainable Buildings) 2022"
- "State Environmental Planning Policy (Transport and Infrastructure) 2021"
- etc. (see full list above)

These come with additional metadata (Map Type, Class, Label) that indicates what specific provision applies.

### Question 2: "How are we to get the relevant SEPP provisions?"

**Answer:** Three-step process:

1. **Extract specific SEPP type from Portal name** (not just year!)
   - Use pattern matching on full name
   - Map to specific identifier (e.g., SEPP_SUSTAINABLE_BUILDINGS_2022)

2. **Map identifier to database document_id pattern**
   - Use SEPP_MAPPINGS lookup table
   - Account for both formats (with/without parentheses)

3. **Query database using correct document_id**
   ```sql
   SELECT * FROM regulatory_provisions
   WHERE document_id ILIKE '%State_Environmental_Planning_Policy_Sustainable_Buildings_2022%'
   ```

### Current Status: ❌ NOT WORKING

- Portal → Identifier: ❌ Too generic (year only)
- Identifier → Database: ❌ Wrong patterns (using SEPP_2022 instead of full name)
- Database Query: ❌ No matches found

### After Fix: ✅ WILL WORK

- Portal → Identifier: ✅ Specific (SEPP_SUSTAINABLE_BUILDINGS_2022)
- Identifier → Database: ✅ Correct patterns
- Database Query: ✅ 292-6,138 provisions per SEPP
