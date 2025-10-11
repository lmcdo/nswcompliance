# DCP Control Categorization Strategy

## Problem Analysis

**Current Issue:**
Backend API categorizes unknown `control_type` values as "environmental", causing DCP design controls to appear in the wrong section.

**Example from 180 Addison Rd:**
- C59, C66, C72: Building form and design controls
- SEPP 65: Apartment design quality standards
- "Showroom Development": Commercial building type control
- "active frontages": Street interface design control

These are categorized as "environmental" but should be "special" or filtered entirely.

---

## Root Cause

```typescript
// Current logic in transformControlsToConstraints()
switch (control.control_type) {
  case 'height': uiType = 'height'; break;
  case 'fsr': uiType = 'fsr'; break;
  case 'setback': uiType = 'setback'; break;
  case 'parking':
  case 'open_space': uiType = 'special'; break;
  default:
    uiType = 'environmental';  // ❌ CATCH-ALL
}
```

**Problem:** `control_type` comes from the database and may be:
1. NULL (no type extracted)
2. An unexpected value (e.g., "design", "character", "building_form")
3. A text description instead of a structured type

---

## Solution Design Principles

### 1. **Conservative Filtering**
- Only hide controls that are 100% irrelevant to the development type
- When in doubt, show the control (but in the correct category)

### 2. **Context-Aware Categorization**
- Consider: development type, zone, LGA, provision text
- Use multiple signals, not just `control_type`

### 3. **Explicit Allow/Block Lists**
- Maintain lists of known irrelevant keywords per development type
- Allow for override based on provision content

### 4. **Graceful Degradation**
- If categorization is uncertain, default to "special" (not "environmental")
- Log uncategorized controls for improvement

---

## Proposed Categorization Strategy

### Tier 1: Structural Controls (Always Relevant)
```
height, fsr, setback, parking, open_space, lot_size
→ Map to building_envelope or special
```

### Tier 2: Environmental Overlays (Based on Content)
```
Keywords in provision text:
- "flood", "bushfire", "contamination", "acid sulfate"
- "heritage", "archaeological", "aboriginal"
- "biodiversity", "vegetation", "tree preservation"
- "water quality", "stormwater", "drainage"
→ Category: environmental

Edge case: "SEPP 65" contains "vegetation" but is design quality, not environmental
→ Solution: Check document_id first (SEPP 65 → special)
```

### Tier 3: Design Quality Controls
```
Keywords:
- "building design", "architectural", "materials", "facade"
- "SEPP 65", "apartment design guide", "ADG"
- "solar access", "natural ventilation", "communal open space"
→ Category: special

Document patterns:
- Contains "SEPP_65" or "State_Environmental_Planning_Policy_No_65"
→ Category: special (design quality)
```

### Tier 4: Development Type Filters (Relevance)
```
Dwelling house (R2):
  IRRELEVANT:
  - "showroom", "warehouse", "factory"
  - "active frontages" (commercial street interface)
  - "shop", "retail", "commercial premises"

  RELEVANT:
  - "dwelling", "residential", "housing"
  - "private open space", "landscaping"
  - "building envelope", "character"

Multi-dwelling/Apartment:
  RELEVANT:
  - "SEPP 65", "apartment design"
  - "communal", "common areas"
  - "building separation"

Commercial (B zones):
  RELEVANT:
  - "active frontages", "shop front"
  - "commercial premises", "retail"
```

---

## Implementation Options

### Option 1: Backend Filter (Recommended)
**Pros:**
- Centralized logic
- Consistent across all API consumers
- Can leverage database metadata

**Cons:**
- Requires backend changes
- Must handle all LGAs/DCPs

**Implementation:**
```typescript
function categorizeControl(
  control: any,
  developmentType: string,
  zone: string
): { category: string; isRelevant: boolean } {

  // Step 1: Check document type
  if (control.document_id?.includes('SEPP_65')) {
    return { category: 'special', isRelevant: true };
  }

  // Step 2: Structural controls
  if (['height', 'fsr', 'setback', 'parking'].includes(control.control_type)) {
    return {
      category: control.control_type === 'parking' ? 'special' : control.control_type,
      isRelevant: true
    };
  }

  // Step 3: Analyze provision text
  const text = (control.provision_text || '').toLowerCase();
  const refNum = (control.ref_number || '').toLowerCase();

  // Environmental keywords
  const envKeywords = ['flood', 'bushfire', 'contamination', 'acid sulfate',
                       'heritage', 'biodiversity', 'tree preservation'];
  if (envKeywords.some(kw => text.includes(kw))) {
    return { category: 'environmental', isRelevant: true };
  }

  // Development type relevance
  const isDwellingHouse = developmentType === 'dwelling_house';
  const isResidentialZone = ['R1', 'R2', 'R3', 'R4'].some(z => zone.startsWith(z));

  if (isDwellingHouse || isResidentialZone) {
    // Filter commercial controls
    const commercialKeywords = ['showroom', 'shop', 'retail', 'warehouse',
                                'active frontage', 'commercial premises'];
    if (commercialKeywords.some(kw => text.includes(kw) || refNum.includes(kw))) {
      return { category: 'special', isRelevant: false }; // ❌ FILTER OUT
    }
  }

  // Default: show as special provision
  return { category: 'special', isRelevant: true };
}
```

### Option 2: Frontend Filter
**Pros:**
- Quick to implement
- No backend changes

**Cons:**
- Duplicates logic with frontend SEPP filter
- Doesn't help other API consumers

**Implementation:**
Add to `ComplianceDashboard.tsx` when processing API response:
```typescript
const filterDCPControls = (constraints: ComplianceConstraint[]) => {
  return constraints.filter(c => {
    // Only filter DCP controls
    if (c.source.authority_level !== 'DCP') return true;

    const text = c.full_text?.toLowerCase() || '';
    const clause = c.source.clause?.toLowerCase() || '';

    // For residential development, filter commercial controls
    if (developmentType === 'dwelling_house') {
      const commercialKeywords = ['showroom', 'shop', 'active frontage'];
      if (commercialKeywords.some(kw => text.includes(kw) || clause.includes(kw))) {
        console.log('[DCP Filter] Filtered commercial control:', clause);
        return false;
      }
    }

    return true;
  });
};
```

### Option 3: Hybrid Approach (Best)
**Backend:** Fix categorization (environmental vs special)
**Frontend:** Filter irrelevant controls based on development type

---

## Edge Cases to Handle

### 1. **SEPP 65 (Design Quality)**
```
Issue: Contains "vegetation" keyword but is design quality, not environmental
Solution: Check document_id first before keyword matching
Priority: Document type > Keywords
```

### 2. **Mixed-Use Development**
```
Issue: "shop_top_housing" needs both residential AND commercial controls
Solution: Don't filter commercial controls for mixed-use types
```

### 3. **Heritage Controls**
```
Issue: "Heritage conservation area character" - environmental or design?
Solution: If mentions "heritage" → environmental (conservation overlay)
         If mentions "character" + no heritage → special (design quality)
```

### 4. **Precinct-Specific Controls**
```
Issue: "Precinct 9.47 building character" - relevant to all properties in precinct
Solution: Don't filter precinct controls based on development type
         (they apply to the location, not the development)
```

### 5. **Generic Controls**
```
Issue: "Development must be compatible with neighborhood character"
Solution: Keep as special provision (applies to all development types)
```

### 6. **Future-Proofing**
```
Issue: New control types added to database
Solution: Default to 'special' (not 'environmental')
         Log unknown types for analysis
```

---

## Recommended Implementation Plan

### Phase 1: Fix Backend Categorization (30 min)
1. Change default from `'environmental'` to `'special'`
2. Add SEPP 65 detection
3. Add environmental keyword detection
4. Log uncategorized controls

### Phase 2: Add Development Type Filtering (20 min)
1. Create irrelevant keyword lists per development type
2. Filter in backend `transformControlsToConstraints()`
3. Return filtered controls with reason in metadata

### Phase 3: Testing (20 min)
1. Test 180 Addison Rd (dwelling_house, R2)
2. Test multi-dwelling development
3. Test commercial property (B zone)
4. Test mixed-use (shop_top_housing)

---

## Testing Matrix

| Property Type | Zone | Should Show | Should Hide |
|--------------|------|-------------|-------------|
| Dwelling house | R2 | Height, setbacks, SEPP 65 | Showroom, active frontages |
| Multi-dwelling | R4 | Height, SEPP 65, communal | Showroom, commercial |
| Shop top housing | B4 | Height, SEPP 65, active frontages | (none - mixed use) |
| Commercial | B2 | Height, active frontages, shop | Residential setbacks |

---

## Monitoring & Improvement

### Logging Strategy
```typescript
console.log('[Control Categorization]', {
  control_type: control.control_type,
  assigned_category: category,
  reason: 'keyword_match | document_type | default',
  filtered: !isRelevant,
  filter_reason: 'commercial_in_residential | ...'
});
```

### Feedback Loop
1. Monitor console logs for uncategorized controls
2. Weekly review of filtered controls
3. Update keyword lists based on false positives/negatives
4. Document edge cases in this file

---

## Decision: Hybrid Approach

**Backend Changes:**
- Fix default category (`environmental` → `special`)
- Add SEPP 65 detection
- Add environmental keyword detection

**Frontend Changes:**
- Keep existing SEPP relevance filter
- Add DCP relevance filter for development type mismatch
- Group controls by "Action Required" vs "Informational"

**Result:**
- Cleaner categorization for all API consumers
- Development-type aware filtering in UI
- Conservative approach (show when uncertain)
- Comprehensive logging for improvement

---

## Estimated Impact

**180 Addison Rd (dwelling_house, R2):**
- Before: 6 "environmental" controls (all DCP)
- After: 0-2 relevant controls
  - C59, C66, C72: Keep (building form - applies to dwellings)
  - SEPP 65: Keep (design quality - applies if >3 storeys, otherwise informational)
  - Showroom: **FILTER** (commercial only)
  - Active frontages: **FILTER** (commercial only)

**Net reduction: 6 → 2-3 controls**
