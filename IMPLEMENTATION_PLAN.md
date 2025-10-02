# Implementation Plan - Fix Compliance Constraints

## Root Cause

**The API queries the wrong table and uses a broken typeMap, causing all provisions to be categorized as 'special'**

- API queries `provisions_with_category` directly (has no extracted numeric values)
- API uses typeMap expecting 'height_limit', 'setback' but database has 'provision_height', 'formal_setback'
- Result: Everything defaults to 'special' type
- Frontend receives 50+ items in special_provisions, 0 in building_envelope

## The Data That Actually Exists

### **development_controls table (4,526 rows)**
- Already has extracted numeric values (value_numeric, unit, confidence_score)
- For R2 zone: 290 height, 167 setback, 341 parking controls
- Links to regulatory_provisions via provision_id for full text
- Control types: 'height', 'setback', 'parking', 'fsr', 'open_space', etc.

### **zone_setback_rules table (6 rows)**
- Curated, verified setback rules for R2
- Ashfield: front=6m, side=0.9m, rear=1.2m
- Leichhardt: front=3m, side=1.5m, rear=1.1m
- Confidence: 0.95 (very high quality)

### **regulatory_provisions table (22,648 rows)**
- Full text of all provisions
- Used for "View Full Text" functionality
- Has zone field populated
- development_type sparsely populated (only ~251 rows)

## Changes Required

### **1. API Route (`frontend-nextjs/app/api/compliance/constraints/route.ts`)**

#### **REPLACE Lines 74-98 (Current broken query)**

**Current:**
```typescript
const provisionsQuery = `
  SELECT * FROM provisions_with_category
  WHERE zone = $1 AND provision_type IS NOT NULL
  LIMIT 50
`;
```

**NEW:**
```typescript
// Query 1: Get high-confidence extracted controls
const controlsQuery = `
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
  WHERE rp.zone = $1
    AND dc.control_type IN ('height', 'setback', 'parking', 'fsr', 'open_space')
    AND dc.confidence_score::numeric > 0.75
    AND dc.value_numeric IS NOT NULL
    AND (
      $2::text IS NULL
      OR rp.development_type = $2::text
      OR rp.development_type IS NULL
    )
  ORDER BY
    dc.confidence_score::numeric DESC,
    CASE dc.control_type
      WHEN 'height' THEN 1
      WHEN 'fsr' THEN 2
      WHEN 'setback' THEN 3
      WHEN 'parking' THEN 4
      ELSE 5
    END
  LIMIT 15
`;

const controlsResult = await pool.query(controlsQuery, [zone, developmentType || null]);
console.log(`[Constraints API] Found ${controlsResult.rows.length} extracted controls for zone ${zone}`);

// Query 2: Get curated setback rules
const setbackQuery = `
  SELECT
    zone,
    boundary_type as control_subtype,
    base_value as value_numeric,
    unit,
    confidence,
    source_clause as ref_number,
    source_document as document_id,
    'setback' as control_type
  FROM zone_setback_rules
  WHERE zone = $1
    AND confidence::numeric > 0.90
  ORDER BY
    CASE boundary_type
      WHEN 'front' THEN 1
      WHEN 'side' THEN 2
      WHEN 'rear' THEN 3
      ELSE 4
    END
`;

const setbackResult = await pool.query(setbackQuery, [zone]);
console.log(`[Constraints API] Found ${setbackResult.rows.length} curated setback rules for zone ${zone}`);

// Combine controls and setbacks
const allControls = [...controlsResult.rows, ...setbackResult.rows];
```

#### **REPLACE Lines 194-259 (transformProvisionsToConstraints function)**

**DELETE:** Entire function with broken typeMap

**NEW:**
```typescript
function transformControlsToConstraints(
  controls: any[]
): ComplianceConstraint[] {
  return controls.map(control => {
    // Map control types to UI types
    let uiType: ComplianceConstraint['type'];
    switch (control.control_type) {
      case 'height':
        uiType = 'height';
        break;
      case 'fsr':
        uiType = 'fsr';
        break;
      case 'setback':
        uiType = 'setback';
        break;
      case 'parking':
      case 'open_space':
        uiType = 'special';
        break;
      default:
        uiType = 'environmental';
    }

    // Parse numeric value
    const numericValue = control.value_numeric ? parseFloat(control.value_numeric) : null;

    return {
      type: uiType,
      value: numericValue || control.value_numeric || 'See provision',
      unit: control.unit || undefined,
      source: {
        clause: control.ref_number || 'N/A',
        document: extractDocumentName(control.document_id || ''),
        authority_level: inferAuthorityLevel(control.document_id || '') as 'LEP' | 'DCP' | 'SEPP'
      },
      provision_id: control.provision_id || 0,
      full_text: control.provision_text || '',
      confidence: control.confidence_score ? parseFloat(control.confidence_score) : control.confidence ? parseFloat(control.confidence) : undefined,
      subtype: control.control_subtype
    };
  });
}

// Helper function to extract readable document name
function extractDocumentName(documentId: string): string {
  if (!documentId) return 'Unknown Document';

  // Remove underscores and long suffixes
  const parts = documentId.split('___');
  const mainPart = parts[0] || documentId;

  return mainPart.replace(/_/g, ' ');
}
```

#### **UPDATE Lines 145-150 (Call new transform function)**

**Current:**
```typescript
const constraints = transformProvisionsToConstraints(
  provisionsResult.rows,
  permissions,
  seppResult.rows
);
```

**NEW:**
```typescript
// Transform controls to constraints
const constraints = transformControlsToConstraints(allControls);

// Add SEPP overrides as special constraints
for (const sepp of seppResult.rows) {
  const overrideText = sepp.extracted_text || sepp.sepp_text || 'SEPP override applies';
  const overrideType = sepp.override_type || 'modifies';

  constraints.push({
    type: 'special',
    value: `SEPP ${overrideType} LEP clause ${sepp.lep_clause_reference || 'N/A'}`,
    source: {
      clause: `Override: ${sepp.lep_clause_reference || 'N/A'}`,
      document: `SEPP Override (Provision ${sepp.sepp_provision_id || 'Unknown'})`,
      authority_level: 'SEPP'
    },
    provision_id: sepp.sepp_provision_id || 0,
    full_text: overrideText.substring(0, 500)
  });
}
```

#### **KEEP Lines 154-178 (Response structure is correct)**

The response structure already filters correctly:
```typescript
return NextResponse.json({
  success: true,
  data: {
    building_envelope: constraints.filter(c =>
      ['height', 'fsr', 'setback'].includes(c.type)
    ),
    environmental: constraints.filter(c =>
      ['heritage', 'environmental'].includes(c.type)
    ),
    special_provisions: constraints.filter(c =>
      c.type === 'special'
    ),
    development_permissions: permissions,
    sepp_overrides: seppResult.rows
  },
  ...
});
```

This is fine - once constraints have correct types, this will work.

### **2. Frontend (`frontend-nextjs/components/compliance/ComplianceDashboard.tsx`)**

#### **DELETE Lines 199-278 (Unused extractDCPConstraints function)**

**Current:** Function exists but is never called (see line 301 comment)

**Action:** Delete entire function

#### **KEEP Lines 295-345 (Data assembly is correct)**

The frontend assembly is already correct:
```typescript
setComplianceData({
  building_envelope: [
    ...lepConstraints,  // LEP Height/FSR
    ...(apiResponse.data.building_envelope || [])  // DCP controls
  ],
  environmental: [
    ...(apiResponse.data.environmental || [])
  ],
  special_provisions: [
    ...planningAPIProvisions,  // Planning API SEPPs
    ...(apiResponse.data.special_provisions || [])  // SEPP overrides
  ]
});
```

Once API returns correct data, this will work.

## Expected Result After Fix

### **API Response for R2 + dwelling_house:**
```json
{
  "building_envelope": [
    { "type": "setback", "value": 6, "unit": "m", "subtype": "front", "confidence": 0.95 },
    { "type": "setback", "value": 0.9, "unit": "m", "subtype": "side", "confidence": 0.95 },
    { "type": "setback", "value": 1.2, "unit": "m", "subtype": "rear", "confidence": 0.95 },
    { "type": "height", "value": 9, "unit": "m", "confidence": 0.85 },
    { "type": "fsr", "value": 0.6, "unit": ":1", "confidence": 0.80 }
  ],
  "environmental": [],
  "special_provisions": [
    { "type": "special", "value": "SEPP modifies LEP clause 4.3", ... }
  ]
}
```

### **UI Display:**

**Building Envelope (8-10 cards):**
- LEP: Height 9m (from Planning API)
- LEP: FSR 0.6:1 (from Planning API)
- DCP: Front setback 6m (from zone_setback_rules)
- DCP: Side setback 0.9m (from zone_setback_rules)
- DCP: Rear setback 1.2m (from zone_setback_rules)
- DCP: Other height/fsr controls (from development_controls)

**Environmental (2-3 cards):**
- DCP environmental controls if any

**Special Provisions (13-14 cards):**
- 3-4 Planning API SEPPs (Water, Climate, BASIX)
- 10 SEPP override provisions

**Total: ~25-30 relevant provision cards with confidence scores**

## Testing Steps

1. Search address: "30 Illawarra Road, Marrickville"
2. Zone should be R2, LGA "Inner West"
3. Select development type: "Dwelling House"
4. Check API logs:
   - Should show "Found X extracted controls for zone R2"
   - Should show "Found Y curated setback rules for zone R2"
5. Check UI:
   - Building envelope should show 8-10 cards (LEP + DCP setbacks + height)
   - Special provisions should show ~13-14 cards (Planning SEPPs + SEPP overrides)
   - NOT 57 special provision cards

## Files to Modify

1. `frontend-nextjs/app/api/compliance/constraints/route.ts`
   - Replace provisions query with controls queries (lines 74-98)
   - Replace transformProvisionsToConstraints function (lines 194-259)
   - Update function call (lines 145-150)

2. `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`
   - Delete extractDCPConstraints function (lines 199-278)
   - No other changes needed

## No Changes Needed

- Frontend data assembly (lines 333-345) ✓
- Frontend Planning API SEPP extraction (lines 79-137) ✓
- Frontend LEP extraction (lines 140-196) ✓
- API response structure (lines 154-178) ✓
- API SEPP overrides query (lines 124-143) ✓

## Summary

**Problem:** API queries wrong table with broken typeMap, returns everything as 'special'

**Solution:** Query `development_controls` + `zone_setback_rules` tables that have extracted numeric values, transform directly without typeMap

**Result:** ~25-30 relevant, high-confidence provisions instead of 60+ random ones