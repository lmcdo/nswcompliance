# End-to-End Workflow Test - Address Search with Dev Type Filtering

## Complete User Journey

### 1. User enters address: "30 Illawarra Road, Marrickville NSW 2204"

**Frontend:** `app/assessment/page.tsx`
- User types address in PropertySearch component
- Calls: `GET /api/property?address=30+Illawarra+Road+Marrickville`

**Backend:** `app/api/property/route.ts`
- Fetches data from NSW Planning Portal API
- Returns property data including:
  - zone: "R2"
  - lga: "Inner West"
  - heritage: false
  - constraints (height, FSR, etc.)

**Result:** Property card displays on left panel

---

### 2. User selects development type: "Multi Dwelling Housing"

**Frontend:** `app/assessment/page.tsx`
- User changes dropdown from "Dwelling House" to "Multi Dwelling Housing"
- `developmentType` state updates to `multi_dwelling`
- Passes to ComplianceDashboard: `<ComplianceDashboard developmentType={developmentType} />`

**Result:** Dev type selector shows "Multi Dwelling Housing"

---

### 3. ComplianceDashboard fetches provisions

**Frontend:** `components/compliance/ComplianceDashboard.tsx`
- useEffect triggers when `developmentType` changes
- Calculates DCP section: `getDCPSection("R2", "multi_dwelling")` → returns "F.4"
- Calls: `POST /api/compliance/constraints`
  ```json
  {
    "address": "30 Illawarra Road...",
    "zone": "R2",
    "developmentType": "multi_dwelling"
  }
  ```

**Backend:** `app/api/compliance/constraints/route.ts`
- **NEW:** Queries `provisions_with_category` VIEW (not `regulatory_provisions` table)
- SQL:
  ```sql
  SELECT * FROM provisions_with_category
  WHERE zone = 'R2'
  AND (development_type = 'multi_dwelling' OR development_type IS NULL)
  ```
- **NEW:** Uses `document_category` column (not `inferAuthorityLevel` function)
- Returns provisions:
  - SEPP provisions: `WHERE document_category = 'SEPP'`
  - LEP provisions: `WHERE document_category = 'LEP'`
  - DCP provisions: `WHERE document_category = 'DCP'`

**Result:** Provisions filtered for multi-dwelling in R2 zone

---

### 4. Frontend displays provisions

**Frontend:** `components/compliance/ComplianceDashboard.tsx`
- Groups provisions:
  - **Building Envelope:** LEP height/FSR + DCP setbacks
  - **Environmental:** DCP landscaping
  - **Special Provisions:** SEPP overlays + DCP parking
- Color codes by authority:
  - Red: SEPP
  - Blue: LEP
  - Green: DCP

**Result:** User sees:
```
Building Envelope:
  [Blue] LEP Height: 9.5m (Inner West LEP 2022 - Clause 4.3)
  [Blue] LEP FSR: 0.6:1 (Inner West LEP 2022 - Clause 4.4)
  [Green] DCP Setbacks: See DCP (Inner West DCP 2016 - F.4 Multi Dwelling Housing)

Special Provisions:
  [Red] SEPP BASIX (State Environmental Planning Policy - Sustainable Buildings)
  [Green] DCP Parking: See DCP (Inner West DCP 2016 - F.4 Multi Dwelling Housing)
```

---

### 5. User clicks "View Full Text" on DCP Setbacks

**Frontend:** ComplianceDashboard
- Calls: `handleViewProvision(constraint)`
- Opens LegalTextPanel slide-out

**Fetching full text:**
- If SEPP: calls `/api/sepp/full-text` with EPI name
  - **NEW:** Queries `provisions_with_category` WHERE `document_category = 'SEPP'`
- If LEP: uses LEP metadata to fetch from database
- If DCP: uses DCP metadata (documentId + controlNumber) to fetch

**Result:** Slide-out panel shows full legal text for F.4 Multi Dwelling setbacks

---

## What Changed with Migrations

### Before Migrations:
```typescript
// Old API query
SELECT * FROM regulatory_provisions
WHERE document_id LIKE '%SEPP%'  // Fragile pattern matching!

// Authority level inference
function inferAuthorityLevel(documentId) {
  if (documentId.includes('SEPP')) return 'SEPP';
  if (documentId.includes('LEP')) return 'LEP';
  return 'DCP';  // Guess!
}

// Dev type filtering
// ❌ Not implemented
```

### After Migrations:
```typescript
// New API query
SELECT * FROM provisions_with_category
WHERE document_category = 'SEPP'  // Clean!
AND (development_type = 'multi_dwelling' OR development_type IS NULL)

// Authority level from VIEW
provision.document_category  // Direct column access

// Dev type filtering
// ✓ Implemented with SQL WHERE clause
```

---

## Files Changed

### Database:
1. ✓ `migrations/perfect_sepp_view.sql` - Created `provisions_with_category` VIEW
2. ✓ `migrations/tag_lep_dev_type_exceptions.sql` - Tagged 251 LEP provisions

### Backend APIs:
3. ✓ `app/api/compliance/constraints/route.ts` - Uses VIEW + dev type filtering
4. ✓ `app/api/sepp/full-text/route.ts` - Uses VIEW for SEPP queries

### Frontend:
5. ✓ `app/assessment/page.tsx` - Already had dev type selector
6. ✓ `components/compliance/ComplianceDashboard.tsx` - Fixed to pass `developmentType` prop

---

## Testing Checklist

### Manual Test:
1. [ ] Start dev server: `npm run dev` (port 3007)
2. [ ] Navigate to: `http://localhost:3007/assessment`
3. [ ] Search address: "30 Illawarra Road, Marrickville"
4. [ ] Verify property loads (zone R2, Inner West)
5. [ ] Change dev type dropdown to "Multi Dwelling Housing"
6. [ ] Verify DCP section changes to "F.4" in constraint cards
7. [ ] Verify provisions reload (check console logs)
8. [ ] Click "View Full Text" on any provision
9. [ ] Verify slide-out panel opens with legal text

### Expected Console Logs:
```
[ComplianceDashboard] Fetching constraints for zone: R2
[Constraints API] Query: zone=R2, devType=multi_dwelling
[Constraints API] Found X provisions for zone R2
[ComplianceDashboard] Extracted 3 DCP constraints for F.4 (Multi Dwelling Housing)
```

### Database Verification:
```sql
-- Test VIEW exists
SELECT COUNT(*) FROM provisions_with_category;
-- Expected: 22,648 provisions

-- Test no NULLs
SELECT COUNT(*) FROM provisions_with_category WHERE document_category IS NULL;
-- Expected: 0

-- Test dev type filtering
SELECT COUNT(*) FROM provisions_with_category
WHERE zone = 'R2'
AND (development_type = 'multi_dwelling' OR development_type IS NULL);
-- Expected: 50-200 provisions
```

---

## Summary

**The complete workflow now:**
1. ✓ Uses `provisions_with_category` VIEW for perfect SEPP/LEP/DCP classification
2. ✓ Filters provisions by development type (multi_dwelling, dwelling_house, etc.)
3. ✓ Matches DCP sections to dev types (F.1, F.4, etc.)
4. ✓ Zero NULL document_category values
5. ✓ 251 LEP provisions tagged with dev-type-specific rules

**Next step:** Test in browser to verify end-to-end!