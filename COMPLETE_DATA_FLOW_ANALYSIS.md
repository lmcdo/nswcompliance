# Complete Data Flow Analysis

## What's Actually In The Database

### **development_controls table: 4,526 extracted controls**
```
- 380 height controls (value_numeric, unit, confidence_score)
- 198 setback controls (value_numeric, unit, confidence_score)
- 463 parking controls
- Links to regulatory_provisions via provision_id
- For R2 zone: 290 height, 167 setback, 341 parking
```

### **zone_setback_rules table: 6 curated rules**
```
- Ashfield R2: front=6m, side=0.9m, rear=1.2m (confidence 0.95)
- Leichhardt R2: front=3m, side=1.5m, rear=1.1m (confidence 0.95)
- High-confidence, verified sources
```

### **regulatory_provisions table: 22,648 provisions**
```
- Full text of all provisions
- Has zone field populated
- development_type sparsely populated (only ~251 LEP rows)
- Used for full text display
```

---

## Current Broken Flow

### **1. API Request**
```
POST /api/compliance/constraints
{
  zone: "R2",
  lga: "Inner West",
  developmentType: "dwelling_house"
}
```

### **2. API Query (WRONG)**
```sql
-- Lines 74-96 in route.ts
SELECT * FROM provisions_with_category
WHERE zone = 'R2'
  AND provision_type IS NOT NULL
  AND (development_type = 'dwelling_house' OR development_type IS NULL)
LIMIT 50
```

**Problems:**
- Queries wrong table (provisions directly instead of extracted controls)
- Returns provisions with provision_type like "informal_should_statement", "context_character_description"
- No extracted numeric values
- No confidence scores
- Returns 50 random provisions

### **3. API Transform (BROKEN)**
```typescript
// Lines 202-218
const typeMap = {
  'height_limit': 'height',     // Database has 'provision_height'
  'setback': 'setback',          // Database has 'formal_setback'
  'car_parking': 'special'       // Database has 'formal_parking'
}
```

**Problem:** typeMap doesn't match database schema → everything defaults to 'special'

### **4. API Response (WRONG)**
```json
{
  building_envelope: [],  // Empty or wrong
  environmental: [],      // Empty or wrong
  special_provisions: [50 provisions],  // Everything goes here
  sepp_overrides: [10 items]
}
```

### **5. Frontend Assembly (BROKEN)**
```typescript
// Lines 333-345
setComplianceData({
  building_envelope: [
    ...lepConstraints,  // 2 LEP items ✓
    ...apiResponse.data.building_envelope  // Empty ✗
  ],
  environmental: [
    ...apiResponse.data.environmental  // Empty ✗
  ],
  special_provisions: [
    ...planningAPIProvisions,  // 3-4 Planning API SEPPs ✓
    ...apiResponse.data.special_provisions  // 50 wrong items ✗
  ]
})
```

**Result:** 57 items in special provisions (3-4 + 50 + 10), 0 DCP provisions

---

## Optimal Flow (What Should Happen)

### **1. API Query Strategy**

#### **Query A: High-Confidence Extracted Controls**
```sql
SELECT
  dc.control_type,
  dc.control_subtype,
  dc.value_numeric,
  dc.unit,
  dc.confidence_score,
  rp.id as provision_id,
  rp.provision_text,
  rp.ref_number,
  rp.section_header,
  rp.document_id,
  rp.zone
FROM development_controls dc
JOIN regulatory_provisions rp ON dc.provision_id::integer = rp.id
WHERE rp.zone = $1  -- 'R2'
  AND dc.control_type IN ('height', 'setback', 'parking', 'fsr', 'open_space')
  AND dc.confidence_score::numeric > 0.75
  AND dc.value_numeric IS NOT NULL
ORDER BY
  dc.confidence_score::numeric DESC,
  CASE dc.control_type
    WHEN 'height' THEN 1
    WHEN 'fsr' THEN 2
    WHEN 'setback' THEN 3
    ELSE 4
  END
LIMIT 15;
```

**Returns:** 15 high-confidence DCP controls with actual numeric values

#### **Query B: Curated Setback Rules**
```sql
SELECT
  zone,
  boundary_type,
  base_value,
  unit,
  confidence,
  source_clause,
  source_document
FROM zone_setback_rules
WHERE zone = $1  -- 'R2'
  AND confidence::numeric > 0.90
ORDER BY boundary_type;
```

**Returns:** 6 verified setback rules (front, side, rear for 2 areas)

#### **Query C: SEPP Overrides** (Keep existing)
```sql
SELECT * FROM sepp_lep_overrides
WHERE confidence_score::numeric > 0.5
LIMIT 10;
```

**Returns:** 10 SEPP override provisions (already working)

### **2. API Transform**

```typescript
// For development_controls:
{
  type: dc.control_type,  // Direct mapping: 'height' → 'height'
  value: parseFloat(dc.value_numeric),  // 9.0
  unit: dc.unit,  // 'm'
  source: {
    clause: rp.ref_number,
    document: extractDocName(rp.document_id),
    authority_level: 'DCP'
  },
  provision_id: rp.id,
  full_text: rp.provision_text,
  confidence: parseFloat(dc.confidence_score),
  subtype: dc.control_subtype  // 'rear', 'storeys', etc.
}

// For zone_setback_rules:
{
  type: 'setback',
  value: parseFloat(zsr.base_value),  // 6.0
  unit: zsr.unit,  // 'metres'
  source: {
    clause: zsr.source_clause,
    document: zsr.source_document,
    authority_level: 'DCP'
  },
  confidence: parseFloat(zsr.confidence),
  subtype: zsr.boundary_type  // 'front', 'side', 'rear'
}
```

### **3. API Response Structure**

```json
{
  "success": true,
  "data": {
    "building_envelope": [
      // 3 setbacks from zone_setback_rules (front, side, rear)
      { "type": "setback", "value": 6, "unit": "m", "subtype": "front", "confidence": 0.95 },
      { "type": "setback", "value": 0.9, "unit": "m", "subtype": "side", "confidence": 0.95 },
      { "type": "setback", "value": 1.2, "unit": "m", "subtype": "rear", "confidence": 0.95 },

      // 2-3 height controls from development_controls
      { "type": "height", "value": 9, "unit": "m", "confidence": 0.85 },

      // 1-2 FSR controls from development_controls
      { "type": "fsr", "value": 0.6, "unit": ":1", "confidence": 0.80 }
    ],
    "environmental": [
      // 2-3 environmental controls from development_controls
      { "type": "environmental", "value": "40% min", "confidence": 0.80 }
    ],
    "special_provisions": [
      // Only SEPP overrides (10 items)
      // Planning API SEPPs will be added by frontend
    ]
  },
  "metadata": {
    "lga": "Inner West",
    "zone": "R2",
    "developmentType": "dwelling_house",
    "dcpSection": { ... },
    "totalConstraints": 15,
    "dataSource": {
      "curated_setbacks": 3,
      "extracted_controls": 12,
      "sepp_overrides": 10
    }
  }
}
```

### **4. Frontend Assembly**

```typescript
// Keep existing extractions
const planningAPIProvisions = extractPlanningAPIProvisions(); // 3-4 SEPPs
const lepConstraints = extractLEPConstraints(); // 2 LEP (Height, FSR)

// Remove extractDCPConstraints() - not needed

// Call API
const apiResponse = await fetch('/api/compliance/constraints', {
  body: JSON.stringify({ zone, lga, developmentType })
});

// Assemble correctly
setComplianceData({
  building_envelope: [
    ...lepConstraints,  // 2 LEP items (Height 9m, FSR 0.6:1)
    ...apiResponse.data.building_envelope  // 6-8 DCP items (setbacks, height, fsr)
    // Total: 8-10 items
  ],
  environmental: [
    ...apiResponse.data.environmental  // 2-3 DCP items
  ],
  special_provisions: [
    ...planningAPIProvisions,  // 3-4 Planning API SEPPs
    ...apiResponse.data.special_provisions  // 10 SEPP overrides
    // Total: 13-14 items
  ]
});
```

### **5. Expected UI Result**

**Building Envelope Section: 8-10 cards**
- 2 LEP: Height 9m, FSR 0.6:1
- 3 DCP Setbacks: Front 6m, Side 0.9m, Rear 1.2m
- 2-3 Other DCP controls

**Environmental Section: 2-3 cards**
- DCP landscaping requirements
- Environmental controls if applicable

**Special Provisions Section: 13-14 cards**
- 3-4 Planning API SEPPs (Water, Climate, BASIX)
- 10 SEPP override provisions

**Total: ~25-30 provision cards (relevant, high-confidence)**

---

## Critical Changes Needed

### **API Route (`/api/compliance/constraints/route.ts`)**

**Line 74-96:** ✗ DELETE - Query to provisions_with_category
**Line 202-218:** ✗ DELETE - typeMap (not needed)

**NEW:** Add queries to:
1. `development_controls` JOIN `regulatory_provisions` (15 rows)
2. `zone_setback_rules` (3-6 rows)
3. Keep SEPP overrides query (10 rows)

**NEW:** Transform directly from controls table:
- Use `control_type` as constraint type (already correct)
- Use `value_numeric` as value (already extracted)
- Use `unit` as unit (already present)
- Use `confidence_score` for quality
- Link to provision via `provision_id` for full text

### **Frontend (`ComplianceDashboard.tsx`)**

**Line 199-278:** ✗ DELETE - `extractDCPConstraints()` function (not called anyway)

**Line 333-345:** ✓ KEEP - Data assembly is correct, just needs API to return right data

**Line 295-299:** ✓ KEEP - Planning API SEPP extraction (working)

**Line 140-196:** ✓ KEEP - LEP extraction (working)

---

## Why This Will Work

### **Data Quality:**
- ✓ development_controls has 4,526 extracted values with confidence scores
- ✓ zone_setback_rules has 6 verified, curated setbacks for R2
- ✓ For R2 zone: 290 height + 167 setback + 341 parking controls available
- ✓ All linked to regulatory_provisions for full text

### **Query Efficiency:**
- Query A returns 15 high-confidence controls (filtered, sorted, limited)
- Query B returns 3-6 curated setbacks (high confidence 0.95)
- Query C returns 10 SEPP overrides (existing, working)
- Total: ~25-30 provisions (not 50+)

### **Frontend Alignment:**
- Frontend already extracts Planning API SEPPs ✓
- Frontend already extracts LEP constraints ✓
- Frontend just needs API to return DCP controls correctly
- No hard-coded DCP extraction needed

### **User Experience:**
- Building envelope: Actual numeric setbacks/height/FSR with values
- Environmental: Relevant environmental controls
- Special provisions: Planning API SEPPs + SEPP overrides (13-14 items, not 57)
- All provisions clickable for full text
- All provisions show confidence scores
- All provisions relevant to R2 + dwelling_house

---

## Summary

**Current problem:** API queries wrong table, uses broken typeMap, returns 50 random provisions as 'special'

**Solution:** API should query `development_controls` + `zone_setback_rules`, use extracted values directly, return structured controls

**Result:** 25-30 relevant, high-confidence provisions instead of 60+ random ones