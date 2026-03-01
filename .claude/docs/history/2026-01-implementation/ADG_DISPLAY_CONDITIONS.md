# ADG Component Display Conditions - Complete Flow

**Date:** 2025-11-05
**Status:** Documented from live codebase

---

## Summary

The **ADG Building Separation Table** component displays when **ALL** of the following conditions are met:

1. User has selected a property address
2. User has selected one of three multi-dwelling development types
3. User has entered a building height > 0 meters
4. API confirms ADG standards apply to that development type

---

## Display Flow (Step-by-Step)

### Step 1: User Selects Property
**File:** `frontend-nextjs/app/assessment/page.tsx`
**Component:** `<PropertySearch>`
**Action:** User enters address and selects from autocomplete

```typescript
const [selectedProperty, setSelectedProperty] = useState<any>(null);
```

**Result:** Property data loads from `/api/property?address=...`

---

### Step 2: User Selects Development Type
**File:** `frontend-nextjs/app/assessment/page.tsx:258-277`
**Component:** Dropdown `<select>`
**State:** `const [developmentType, setDevelopmentType] = useState('dwelling_house');`

**Available Options:**
- Dwelling House
- Secondary Dwelling
- Shop Top Housing ✅ (triggers ADG)
- Multi Dwelling Housing ✅ (triggers ADG)
- Residential Flat Building ✅ (triggers ADG)
- Boarding House
- Child Care Centre
- Commercial Premises

**ADG-Triggering Development Types:**
- `multi_dwelling`
- `residential_flat`
- `shop_top_housing`

---

### Step 3: Building Height Input Appears (Conditional)
**File:** `frontend-nextjs/app/assessment/page.tsx:280-302`
**Condition:**
```typescript
{(developmentType === 'multi_dwelling' ||
  developmentType === 'residential_flat' ||
  developmentType === 'shop_top_housing') && (
```

**UI Element:**
```html
<input
  type="number"
  step="0.1"
  min="0"
  max="100"
  value={buildingHeight || ''}
  onChange={(e) => setBuildingHeight(parseFloat(e.target.value) || null)}
  placeholder="e.g., 10.5"
/>
```

**Helper Text:** "Required for ADG building separation standards"

**State:** `const [buildingHeight, setBuildingHeight] = useState<number | null>(null);`

---

### Step 4: ComplianceDashboard Receives Props
**File:** `frontend-nextjs/app/assessment/page.tsx:342-347`

```typescript
<ComplianceDashboard
  propertyData={selectedProperty}
  developmentType={developmentType}
  buildingHeight={buildingHeight}
  className="transition-all duration-300 ease-in-out"
/>
```

---

### Step 5: ComplianceDashboard Conditionally Renders ADG Card
**File:** `frontend-nextjs/components/compliance/ComplianceDashboard.tsx:1149-1172`

**Conditions:**
```typescript
{buildingHeight && buildingHeight > 0 && (
  developmentType === 'multi_dwelling' ||
  developmentType === 'residential_flat' ||
  developmentType === 'shop_top_housing'
) && (
  <Card className="border-red-300">
    <CardHeader className="bg-red-50">
      <CardTitle className="flex items-center gap-2">
        <span className="text-xl">🟥</span>
        NSW Apartment Design Guide - Building Separation
      </CardTitle>
      <p className="text-sm text-gray-600 mt-1">
        Statutory standards under SEPP (Housing) 2021
      </p>
    </CardHeader>
    <CardContent className="pt-4">
      <ADGBuildingSeparationTable
        buildingHeight={buildingHeight}
        developmentType={developmentType}
      />
    </CardContent>
  </Card>
)}
```

**Must ALL be true:**
1. `buildingHeight` exists (not null)
2. `buildingHeight > 0`
3. Development type is one of: `multi_dwelling`, `residential_flat`, `shop_top_housing`

---

### Step 6: ADGBuildingSeparationTable Component Renders
**File:** `frontend-nextjs/components/compliance/ADGBuildingSeparationTable.tsx:41-217`

**Props Received:**
```typescript
interface ADGBuildingSeparationTableProps {
  buildingHeight: number;
  developmentType: string;
}
```

**Component Behavior:**

1. **Fetches API Data:**
   ```typescript
   const response = await fetch(
     `/api/setbacks/adg?building_height=${buildingHeight}&development_type=${developmentType}`
   );
   ```

2. **Checks if ADG Applies:**
   ```typescript
   if (!result.applies) {
     setData(null);
     return null;  // Component renders nothing
   }
   ```

3. **Displays if applicable:**
   - Red alert: "Statutory Requirement"
   - Building height category badge
   - Setback table (side/rear × habitable/non-habitable)
   - Additional requirements (collapsible)
   - Source citation with PDF link

---

### Step 7: API Route Validates and Returns Data
**File:** `frontend-nextjs/app/api/setbacks/adg/route.ts:25-180`

**Query Parameters Required:**
- `building_height` (number, > 0)
- `development_type` (string)

**Development Type Validation:**
```typescript
const adgApplicableTypes = [
  'multi_dwelling_housing',
  'residential_flat_building',
  'shop_top_housing'
];

if (!adgApplicableTypes.includes(developmentType)) {
  return NextResponse.json({
    applies: false,
    reason: 'ADG building separation standards only apply to multi-dwelling housing, residential flat buildings, and shop-top housing developments',
    development_type: developmentType
  });
}
```

**Height Category Determination:**
```typescript
if (buildingHeight <= 12) {
  heightCondition = 'building_height_up_to_12m';
  heightLabel = 'Up to 12m';
  storeyRange = '4 storeys';
} else if (buildingHeight <= 25) {
  heightCondition = 'building_height_12m_to_25m';
  heightLabel = 'Up to 25m';
  storeyRange = '5-8 storeys';
} else {
  heightCondition = 'building_height_over_25m';
  heightLabel = 'Over 25m';
  storeyRange = '9+ storeys';
}
```

**Database Query:**
```sql
SELECT
  ref_number,
  boundary_type,
  setback_meters,
  exceptions,
  source_text,
  document_name,
  notes
FROM setback_rules
WHERE ref_number LIKE 'ADG 3F-1%'
  AND $1 = ANY(site_condition)
  AND $2 = ANY(development_type)
ORDER BY
  boundary_type,
  CASE WHEN ref_number LIKE '%Non-habitable%' THEN 2 ELSE 1 END
```

---

## Complete Conditional Logic Chain

```
User Action → Condition → Result
─────────────────────────────────────────────────────────────

1. Select Address
   → selectedProperty !== null
   → ✅ ComplianceDashboard renders

2. Select "Multi Dwelling Housing"
   → developmentType === 'multi_dwelling'
   → ✅ Building height input appears

3. Enter "15" in Building Height
   → buildingHeight = 15
   → ✅ Passes to ComplianceDashboard

4. ComplianceDashboard Conditional Check
   → buildingHeight > 0 ? YES ✅
   → developmentType is multi_dwelling/residential_flat/shop_top ? YES ✅
   → ✅ ADG Card renders with ADGBuildingSeparationTable

5. ADGBuildingSeparationTable Fetches API
   → GET /api/setbacks/adg?building_height=15&development_type=multi_dwelling
   → API validates: developmentType in ['multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing']
   → ✅ Returns standards for 12-25m height category

6. Component Displays Data
   → result.applies === true
   → ✅ Shows red alert + setback table
```

---

## Display Hierarchy in UI

**Order of appearance on assessment page:**

1. **SEPP Requirements** (red cards)
2. **ADG Building Separation** ⬅️ HERE (red card, STATUTORY badge)
3. **Heritage Details** (if in HCA)
4. **LEP Building Envelope** (blue cards)
5. **DCP Precinct Requirements** (green cards)
6. **DCP General Requirements** (green cards)

**Visual Styling:**
- Border: Red (`border-red-300`)
- Header Background: Red (`bg-red-50`)
- Icon: 🟥
- Alert: Red with "STATUTORY REQUIREMENT" text

---

## When ADG Component DOES NOT Display

| Condition | Result |
|-----------|--------|
| No property selected | ❌ Entire ComplianceDashboard hidden |
| Development type is "dwelling_house" | ❌ Building height input hidden, ADG not rendered |
| Development type is "commercial" | ❌ Building height input hidden, ADG not rendered |
| Building height is null | ❌ ADG card not rendered |
| Building height is 0 | ❌ ADG card not rendered |
| API returns `applies: false` | ❌ Component renders nothing (returns `null`) |
| Database has no ADG data | ⚠️ Shows error message inside component |

---

## User Experience Flow

### Example: Assessing a 6-storey apartment building

1. **User enters:** "180 Addison Road, Marrickville"
   - Property data loads
   - Development Type dropdown shows "Dwelling House" (default)
   - Building height input HIDDEN

2. **User selects:** "Residential Flat Building" from dropdown
   - Building height input APPEARS
   - Helper text: "Required for ADG building separation standards"
   - ADG card NOT YET visible (buildingHeight is null)

3. **User types:** "18" in Building Height field
   - ADG card APPEARS instantly
   - Shows "Up to 25m (5-8 storeys)"
   - Displays side/rear setbacks: 9m habitable, 4.5m non-habitable
   - Red "STATUTORY REQUIREMENT" alert visible
   - Link to official PDF document

4. **User changes height to:** "30"
   - ADG card updates instantly
   - Shows "Over 25m (9+ storeys)"
   - Setbacks update: 12m habitable, 6m non-habitable

5. **User changes development type to:** "Dwelling House"
   - Building height input DISAPPEARS
   - ADG card DISAPPEARS

---

## Technical Details

### State Management

**Page-level state (assessment/page.tsx):**
```typescript
const [developmentType, setDevelopmentType] = useState('dwelling_house');
const [buildingHeight, setBuildingHeight] = useState<number | null>(null);
```

**Component-level state (ADGBuildingSeparationTable.tsx):**
```typescript
const [data, setData] = useState<ADGStandards | null>(null);
const [loading, setLoading] = useState(true);
const [error, setError] = useState<string | null>(null);
```

### Re-rendering Triggers

**Component re-fetches API when:**
```typescript
useEffect(() => {
  fetchADGStandards();
}, [buildingHeight, developmentType]);
```

Changes to `buildingHeight` or `developmentType` trigger new API call.

---

## API Request/Response Examples

### Valid Request (Applies)
**Request:**
```
GET /api/setbacks/adg?building_height=15&development_type=residential_flat_building
```

**Response:**
```json
{
  "applies": true,
  "building_height_meters": 15,
  "height_category": "Up to 25m",
  "storey_range": "5-8 storeys",
  "development_type": "residential_flat_building",
  "setbacks": {
    "side": {
      "habitable_rooms_and_balconies": 9,
      "non_habitable_rooms": 4.5
    },
    "rear": {
      "habitable_rooms_and_balconies": 9,
      "non_habitable_rooms": 4.5
    }
  },
  "source": {
    "document": "NSW Apartment Design Guide - Part 3: Siting the Development",
    "section": "3F-1 Visual Privacy",
    "authority": "SEPP (Housing) 2021",
    "legal_status": "STATUTORY",
    "url": "https://www.planning.nsw.gov.au/sites/default/files/2023-03/apartment-design-guide-part-3-siting-the-development.pdf",
    "page": 63
  }
}
```

### Invalid Request (Does Not Apply)
**Request:**
```
GET /api/setbacks/adg?building_height=10&development_type=dwelling_house
```

**Response:**
```json
{
  "applies": false,
  "reason": "ADG building separation standards only apply to multi-dwelling housing, residential flat buildings, and shop-top housing developments",
  "development_type": "dwelling_house"
}
```

### Missing Parameters
**Request:**
```
GET /api/setbacks/adg?building_height=10
```

**Response (400 Bad Request):**
```json
{
  "error": "Missing required parameters: building_height and development_type"
}
```

---

## Database Table Structure

**Table:** `setback_rules`

**ADG Records:**
- `ref_number`: 'ADG 3F-1 Habitable' or 'ADG 3F-1 Non-habitable'
- `boundary_type`: 'side' or 'rear'
- `development_type[]`: Array including 'multi_dwelling_housing', 'residential_flat_building', 'shop_top_housing'
- `site_condition[]`: Array including 'building_height_up_to_12m', 'building_height_12m_to_25m', 'building_height_over_25m'
- `setback_meters`: 6.0, 9.0, 12.0 (habitable) or 3.0, 4.5, 6.0 (non-habitable)

**Total Records:** 12 standards (3 height categories × 2 boundaries × 2 room types)

---

## Summary: Display Conditions

✅ **DISPLAYS when:**
1. Property is selected
2. Development type is one of: `multi_dwelling`, `residential_flat`, `shop_top_housing`
3. Building height is entered and > 0
4. API confirms ADG applies to this development type

❌ **DOES NOT DISPLAY when:**
1. No property selected
2. Development type is single dwelling, commercial, child care, or boarding house
3. Building height is not entered (null) or is 0
4. API returns `applies: false` for the development type

⚠️ **SHOWS ERROR when:**
1. Database has no ADG data (empty `setback_rules` table)
2. API request fails
3. Network error

---

## Files Involved

| File | Role |
|------|------|
| `frontend-nextjs/app/assessment/page.tsx` | User inputs, state management, conditional rendering |
| `frontend-nextjs/components/compliance/ComplianceDashboard.tsx` | Conditional ADG card rendering |
| `frontend-nextjs/components/compliance/ADGBuildingSeparationTable.tsx` | ADG display component |
| `frontend-nextjs/app/api/setbacks/adg/route.ts` | API route for ADG standards |
| `insert_adg_statutory_standards.py` | Database population script |

---

## Testing Scenarios

### Scenario 1: Single Dwelling (Should NOT show ADG)
1. Select any property
2. Keep "Dwelling House" selected
3. **Expected:** No building height input, no ADG card

### Scenario 2: Apartment, No Height (Should NOT show ADG yet)
1. Select any property
2. Select "Residential Flat Building"
3. **Expected:** Building height input appears, but ADG card NOT visible yet

### Scenario 3: Apartment with Height (Should SHOW ADG)
1. Select any property
2. Select "Residential Flat Building"
3. Enter building height: 15
4. **Expected:** ADG card appears with 12-25m standards

### Scenario 4: Change Height Category
1. Continue from Scenario 3
2. Change height to 8m
3. **Expected:** ADG updates to "Up to 12m" standards (6m habitable, 3m non-habitable)

### Scenario 5: Change to Non-ADG Type
1. Continue from Scenario 3
2. Change development type to "Child Care Centre"
3. **Expected:** Building height input disappears, ADG card disappears

---

## Known Development Type Mapping Issue

**UI uses underscores:**
- `multi_dwelling`
- `residential_flat`
- `shop_top_housing`

**API expects full names with underscores:**
- `multi_dwelling_housing`
- `residential_flat_building`
- `shop_top_housing`

**Current workaround:** API route doesn't validate exact match, it checks if development type string is in the array. This may cause mismatches.

**Recommendation:** Standardize naming between frontend and backend, or add mapping function.

---

## Regulatory Context

**Authority:** SEPP (Housing) 2021
**Document:** NSW Apartment Design Guide - Part 3: Siting the Development
**Section:** 3F-1 Visual Privacy - Design Criteria 1
**Page:** 63
**Legal Status:** STATUTORY (not discretionary)
**Applicability:** State-wide (all of NSW)
**Cannot be varied:** Consent authority cannot reduce these standards

**User Impact:**
- Same priority as SEPP provisions (red styling)
- Clear warning that these are non-negotiable
- Link to official source document for verification
- Professional compliance assessment requires these standards
