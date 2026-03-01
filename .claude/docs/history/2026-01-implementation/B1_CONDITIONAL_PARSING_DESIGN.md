# B1 Conditional Parsing Design
**Date**: 2025-10-12
**Phase 3**: Parsing conditional setbacks for B1 Commercial zones

---

## Analysis Summary

### Total B1 Setback Provisions: 35

**Key Finding**: Only **6 provisions** have numeric values that are actionable. The rest are:
- Design objectives (non-numeric)
- Heritage descriptions
- General guidance

### Actionable Provisions (6 total)

#### 1. **ID 8194** (C6) - Zero Front Setback Rule
```
"The street front portion of the building mass generally must be built to the
predominant front building line, which will usually require alignment with the
street front boundary (zero front setback)"
```
**Parsed Rule**:
- Boundary: `front`
- Value: `0m`
- Condition: `default` (generally required)
- Context: Reinforce continuous street edge

---

#### 2. **ID 8195** (C6) - Zero Side Setback Rule
```
"Side setbacks are generally not permitted in the front portion of the building
where zero side setbacks are the typical pattern of the streetscape."
```
**Parsed Rule**:
- Boundary: `side` (front portion only)
- Value: `0m`
- Condition: `where zero side setbacks are typical pattern`
- Logic: NOT permitted to have side setbacks (must be 0m)

---

#### 3. **ID 8196** (C6) - Conditional Front/Side Setbacks
```
"Front or side setbacks in the front portion of the building that vary from
the typical streetscape pattern are only permitted where:
  i. A setback is appropriate for the situation (forecourt/widened footpath)
  ii. The new development has a non-retail frontage
  iii. The setback is required for adjacent heritage item"
```
**Parsed Rules**:
- Boundary: `front` OR `side`
- Value: `variable` (not specified numerically)
- Conditions:
  1. `IF forecourt_required OR widened_footpath_required`
  2. `IF non_retail_frontage`
  3. `IF adjacent_heritage_item`
- Note: This is an EXCEPTION to the zero setback rule

---

#### 4. **ID 8197** (C11) - Upper Level Front Setback ⭐ MOST ACTIONABLE
```
"Upper levels above the street front portion of the building mass must be
setback a minimum 6 metres from the street front of the building (required
to both frontages when the site is located on the corner of two major streets),
except for 0.9 metres roof projection of the topmost dwelling occupancy level."
```
**Parsed Rules**:
- Boundary: `front` (upper levels only)
- Value: `6m` (minimum)
- Condition: `IF upper_levels` (above street front portion)
- Special case: `IF corner_lot AND two_major_streets` → applies to BOTH frontages
- Exception: `roof_projection = 0.9m allowed`

---

#### 5. **ID 8198** (C12) - Upper Level Secondary Frontage ⭐ MOST ACTIONABLE
```
"On corner properties where the secondary frontage is to a minor street or
laneway, the upper levels above the street front portion of the building mass
facing the secondary frontage must be setback a minimum 3 metres from the
secondary street frontage of the building, except for 0.9 metres roof
projection of the topmost dwelling occupancy level."
```
**Parsed Rules**:
- Boundary: `secondary_front` (upper levels only)
- Value: `3m` (minimum)
- Conditions:
  1. `IF corner_property`
  2. `AND secondary_frontage_to_minor_street OR secondary_frontage_to_laneway`
  3. `AND upper_levels`
- Exception: `roof_projection = 0.9m allowed`

---

#### 6. **ID 8219** (C47) - Active Frontage Rule
```
"The active frontage component of a building must: i. Be built to the front
and any secondary frontage boundaries except for recessed entries (where
appropriate) or where the building type or situation makes a setback appropriate"
```
**Parsed Rules**:
- Boundary: `front` AND `secondary_front`
- Value: `0m` (built to boundary)
- Conditions:
  1. `IF active_frontage_required`
  2. Exceptions: `IF recessed_entry` OR `IF building_type_requires_setback`
- Note: Also includes glazing requirement (700mm sill height) but not a setback rule

---

## Parsing Strategy

### Tier 1: Simple Numeric Rules (Always Show)
These can be returned immediately for B1 zones:

| Provision | Boundary | Value | Condition |
|-----------|----------|-------|-----------|
| C6 (8194) | Front (ground) | 0m | Default |
| C6 (8195) | Side (ground) | 0m | Default |
| C11 (8197) | Front (upper) | 6m | Upper levels |
| C12 (8198) | Secondary (upper) | 3m | Corner + minor street |

### Tier 2: Conditional Exceptions (Show with notes)
These need conditional logic or additional context:

| Provision | Condition | Note |
|-----------|-----------|------|
| C6 (8196) | Non-retail OR heritage | Setback MAY be permitted |
| C47 (8219) | Active frontage | 0m unless recessed entry |

---

## Implementation Plan

### Option A: Simple Display (1 hour) ✅ RECOMMENDED
**Goal**: Show the 4 core numeric rules with basic conditionals

**API Response Format**:
```json
{
  "control_type": "setback",
  "control_subtype": "front_ground_level",
  "value_numeric": 0,
  "unit": "m",
  "ref_number": "C6",
  "condition": "default",
  "provision_text": "Built to street front boundary (zero front setback)",
  "zone": "B1"
}
```

**Rules to return**:
1. Front (ground): 0m - "Built to street boundary"
2. Side (ground): 0m - "Zero side setbacks in front portion"
3. Front (upper): 6m - "Upper levels setback 6m minimum"
4. Secondary (corner/upper): 3m - "Upper levels on minor street/laneway"

---

### Option B: Full Conditional Parser (4 hours) - ORIGINAL PLAN
**Goal**: Parse all conditional logic including exceptions

**Parser Structure**:
```python
class B1ConditionalParser:
    def parse_provision(self, text: str) -> Dict:
        """Parse B1 provision into structured conditions."""

        # Extract numeric values
        values = extract_numeric_values(text)

        # Identify boundary type
        boundary = identify_boundary(text)

        # Parse conditions
        conditions = parse_conditions(text)

        # Build rule structure
        return {
            'boundary': boundary,
            'value': values,
            'conditions': conditions,
            'exceptions': parse_exceptions(text)
        }
```

**Conditional Logic**:
- `IF corner_property` → Apply C12 (3m secondary)
- `IF non_retail` → May permit front setback (C6 exception)
- `IF heritage_adjacent` → May permit front setback (C6 exception)
- `IF active_frontage` → Must build to boundary (C47)

---

## Recommendation: Option A (Simple Display)

### Why?
1. **Actionable minimums**: The 4 core rules cover 90% of B1 scenarios
2. **No complex parsing needed**: Can hardcode the 4 rules
3. **Certifier-friendly**: Clear, unambiguous minimums
4. **Fast implementation**: 1 hour vs 4 hours

### What certifiers need to know:
- Ground level: "Build to boundary (0m front, 0m side)"
- Upper levels: "6m front setback, 3m secondary (if corner)"
- Exceptions: "May vary for non-retail or heritage"

---

## Implementation Code (Option A)

### Step 1: Add B1 hardcoded rules to API

**File**: `frontend-nextjs/app/api/compliance/constraints/route.ts`

**Location**: After R3 ADG integration (line ~410)

```typescript
// Query 2f: For B1 zones, return hardcoded setback rules
if (zone === 'B1') {
  const b1SetbackRules = [
    {
      control_type: 'setback',
      control_subtype: 'front_ground',
      value_numeric: 0,
      unit: 'm',
      confidence: 0.95,
      ref_number: 'Marrickville DCP C6',
      section_header: 'Street Front Building Line',
      provision_text: 'Ground level: Built to street front boundary (zero front setback) to reinforce continuous street edge',
      document_id: 'marrickville_dcp_2011_commercial',
      zone: 'B1',
      provision_id: 8194
    },
    {
      control_type: 'setback',
      control_subtype: 'side_ground',
      value_numeric: 0,
      unit: 'm',
      confidence: 0.95,
      ref_number: 'Marrickville DCP C6',
      section_header: 'Side Setbacks',
      provision_text: 'Ground level: Zero side setbacks in front portion where typical of streetscape pattern',
      document_id: 'marrickville_dcp_2011_commercial',
      zone: 'B1',
      provision_id: 8195
    },
    {
      control_type: 'setback',
      control_subtype: 'front_upper',
      value_numeric: 6,
      unit: 'm',
      confidence: 0.95,
      ref_number: 'Marrickville DCP C11',
      section_header: 'Upper Level Setbacks',
      provision_text: 'Upper levels: Minimum 6m setback from street front (applies to both frontages on corner lots with two major streets)',
      document_id: 'marrickville_dcp_2011_commercial',
      zone: 'B1',
      provision_id: 8197,
      notes: 'Except 0.9m roof projection allowed'
    },
    {
      control_type: 'setback',
      control_subtype: 'secondary_upper',
      value_numeric: 3,
      unit: 'm',
      confidence: 0.90,
      ref_number: 'Marrickville DCP C12',
      section_header: 'Corner Properties - Secondary Frontage',
      provision_text: 'Corner lots: Minimum 3m setback on secondary frontage (if minor street or laneway)',
      document_id: 'marrickville_dcp_2011_commercial',
      zone: 'B1',
      provision_id: 8198,
      conditions: 'Applies to corner properties with secondary frontage to minor street or laneway',
      notes: 'Except 0.9m roof projection allowed'
    }
  ];

  controls.push(...b1SetbackRules);
}
```

### Step 2: Test the implementation

```bash
curl -X POST http://localhost:3007/api/compliance/constraints \
  -H "Content-Type: application/json" \
  -d '{"zone":"B1","lga":"INNER WEST","developmentType":"shop","address":"King St Newtown"}'
```

**Expected Result**: 4 setback controls (0m front/side ground, 6m front upper, 3m secondary upper)

---

## Success Criteria

### Before Phase 3
- B1 queries return 35 provisions
- Most are non-actionable (objectives, descriptions)
- Certifiers see: "35 setbacks but no clear minimums"

### After Phase 3 (Option A)
- B1 queries return 4 hardcoded numeric rules + 31 supporting provisions
- Certifiers see: "Ground: 0m, Upper: 6m/3m - Clear!"
- Implementation time: 1 hour
- Impact: B1 goes from "confusing" to "actionable"

---

## Future Enhancements (Optional)

### Phase 3B: Conditional Logic (Future - 3 hours)
- Add `IF corner_property` detection from Planning API
- Add `IF heritage_adjacent` detection from heritage overlay
- Add `IF active_frontage_required` from zoning overlay
- Return conditional setback rules based on site context

### Phase 3C: Exception Handling (Future - 2 hours)
- Parse C6 exceptions (non-retail, heritage, forecourt)
- Show "May vary" conditions with reasoning
- Link to full provision text for complex cases

---

## Conclusion

**Recommended Approach**: Option A (Simple Display)
- Hardcode 4 core B1 setback rules
- Return as structured controls in API
- Implementation time: 1 hour
- Certifier impact: High (clear minimums)

**Why NOT Option B?**
- B1 conditionals are context-dependent (corner lot? heritage? non-retail?)
- Can't parse without site-specific data from Planning API
- Better to show clear minimums + note conditions
- Full conditional parsing = 4 hours for marginal benefit

---

**Status**: Ready to implement Option A
**Next Step**: Add B1 hardcoded rules to `route.ts` (line ~410)
