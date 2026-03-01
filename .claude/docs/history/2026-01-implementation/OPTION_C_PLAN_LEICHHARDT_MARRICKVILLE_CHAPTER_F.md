# Option C Plan: Extract Leichhardt & Marrickville Chapter F

## Critical Finding

**Leichhardt and Marrickville have NO general provisions in the database!**

### Current State:
- **Ashfield**: 65 general provisions (Chapter F) ✅ + Precinct provisions ✅
- **Leichhardt**: 0 general provisions ❌ + Precinct provisions only ✅
- **Marrickville**: 0 general provisions ❌ + Precinct provisions only ✅

### Impact:
- Ashfield addresses: Get zone-filtered general + precinct provisions
- Leichhardt addresses: Get ONLY precinct provisions (if in neighbourhood)
- Marrickville addresses: Get ONLY precinct provisions (if in neighbourhood)
- **Leichhardt/Marrickville addresses NOT in neighbourhoods: Get NOTHING**

### Conclusion:
**Option C is MANDATORY - not optional. Without it, Leichhardt/Marrickville have zero coverage outside neighbourhoods.**

---

## Option C Implementation Plan

### Goal:
Extract Chapter F general provisions for Leichhardt and Marrickville with zone/devtype filtering, matching Ashfield implementation.

### Total Estimated Time: 12-16 hours

---

## Phase 1: Leichhardt Chapter F Extraction (4-5 hours)

### Step 1.1: Locate Source Document (30 min)
**File to find:**
- `Inner West Leichhardt DCP 2013 - Chapter F - Development Category.md`
- Or equivalent PDF if markdown not available

**Verify:**
```bash
# Search for Leichhardt Chapter F
find . -name "*leichhardt*chapter*f*.md" -o -name "*leichhardt*chapter*f*.pdf"
```

### Step 1.2: Extract Provisions (2 hours)
**Create:** `extract_leichhardt_chapter_f.py`

**Based on:** `extract_ashfield_chapter_f.py` (proven methodology)

**Leichhardt Chapter F Parts to Extract:**
```python
LEICHHARDT_CHAPTER_F_PARTS = {
    "F1": {
        "name": "Dwelling Houses",
        "zones": ["R2", "R3", "R4"],  # Update based on Leichhardt LEP
        "dev_types": ["dwelling_house", "alterations_additions"]
    },
    "F2": {
        "name": "Semi-Detached Dwellings",
        "zones": ["R2", "R3"],
        "dev_types": ["semi_detached"]
    },
    "F3": {
        "name": "Multi Dwelling Housing",
        "zones": ["R3", "R4"],
        "dev_types": ["multi_dwelling"]
    },
    "F4": {
        "name": "Residential Flat Buildings",
        "zones": ["R3", "R4", "B4"],
        "dev_types": ["residential_flat"]
    },
    # ... Continue for all Leichhardt Chapter F parts
}
```

**Actions:**
1. Copy `extract_ashfield_chapter_f.py` → `extract_leichhardt_chapter_f.py`
2. Update `CHAPTER_F_PARTS` dictionary for Leichhardt structure
3. Update LGA to "INNER WEST"
4. Update source file path
5. Run extraction: `python extract_leichhardt_chapter_f.py`
6. Output: `leichhardt_chapter_f_general_provisions.json`

**Expected Output:**
- 50-70 provisions
- 8-12 parts extracted

### Step 1.3: Import to Database (30 min)
**Create:** `import_leichhardt_general_provisions.py`

**Based on:** `import_ashfield_general_provisions.py`

**Actions:**
1. Copy Ashfield import script
2. Update source JSON path
3. Update LGA if needed
4. Run import: `python import_leichhardt_general_provisions.py`
5. Verify zone filtering works

**Validation Queries:**
```sql
-- Should return Leichhardt R2 provisions
SELECT COUNT(*)
FROM dcp_general_provisions
WHERE lga = 'INNER WEST'
AND dcp_chapter = 'F'
AND 'R2' = ANY(applicable_zones)
AND 'dwelling_house' = ANY(development_types);
```

### Step 1.4: LLM Categorization (1.5 hours)
**Create:** `categorize_leichhardt_general_provisions.py`

**Based on:** `categorize_general_provisions.py` (proven methodology)

**Actions:**
1. Copy Ashfield categorization script
2. Update to filter for Leichhardt provisions
3. Run categorization: `python categorize_leichhardt_general_provisions.py`
4. Expected: 80-120 structured requirements

**Validation:**
```sql
-- Check Leichhardt requirements created
SELECT category, COUNT(*)
FROM dcp_general_requirements
WHERE lga = 'INNER WEST'
AND extraction_context->>'part_name' ILIKE '%leichhardt%'
GROUP BY category
ORDER BY COUNT(*) DESC;
```

---

## Phase 2: Marrickville Chapter F Extraction (4-5 hours)

### Step 2.1: Locate Source Document (30 min)
**File to find:**
- `Inner West Marrickville DCP 2011 - Chapter F - Development Category.md`
- Or equivalent PDF

### Step 2.2: Extract Provisions (2 hours)
**Create:** `extract_marrickville_chapter_f.py`

**Based on:** `extract_ashfield_chapter_f.py` (same methodology)

**Marrickville Chapter F Parts to Extract:**
```python
MARRICKVILLE_CHAPTER_F_PARTS = {
    "F1": {
        "name": "Dwelling Houses",
        "zones": ["R2", "R3", "R4"],
        "dev_types": ["dwelling_house", "alterations_additions"]
    },
    # ... Continue for all Marrickville Chapter F parts
}
```

**Actions:**
1. Copy extraction script template
2. Update for Marrickville structure
3. Run extraction
4. Output: `marrickville_chapter_f_general_provisions.json`

**Expected Output:**
- 50-70 provisions
- 8-12 parts extracted

### Step 2.3: Import to Database (30 min)
**Create:** `import_marrickville_general_provisions.py`

**Actions:**
1. Copy import script template
2. Update for Marrickville JSON
3. Run import
4. Verify filtering

### Step 2.4: LLM Categorization (1.5 hours)
**Create:** `categorize_marrickville_general_provisions.py`

**Actions:**
1. Copy categorization script template
2. Update for Marrickville provisions
3. Run categorization
4. Expected: 80-120 structured requirements

---

## Phase 3: API Updates (1-2 hours)

### Step 3.1: Verify API Handles Multiple LGAs (30 min)

**Current API:** `frontend-nextjs/app/api/compliance/dcp-complete/route.ts`

**Already handles any LGA:**
```typescript
// Query uses LGA parameter - no changes needed!
SELECT * FROM dcp_general_provisions
WHERE lga = $1  // ← Works for any LGA
AND $2 = ANY(applicable_zones)
AND $3 = ANY(development_types)
```

**Validation Tests:**
```javascript
// Test Leichhardt
{
  zone: 'R2',
  developmentType: 'dwelling_house',
  lga: 'Inner West',
  address: '123 Norton Street, Leichhardt'
}

// Test Marrickville
{
  zone: 'R4',
  developmentType: 'residential_flat',
  lga: 'Inner West',
  address: '456 King Street, Newtown'
}
```

### Step 3.2: Update Test Script (30 min)

**Update:** `test_dcp_complete_api.js`

**Add tests:**
```javascript
// Test 4: Leichhardt R2 + dwelling
// Test 5: Marrickville R4 + residential_flat
// Test 6: Leichhardt with neighbourhood (G precinct)
```

---

## Phase 4: Frontend Component (2-3 hours)

### Step 4.1: Create GeneralDCPSection Component (2 hours)

**Create:** `frontend-nextjs/components/compliance/GeneralDCPSection.tsx`

**Design Requirements:**
- Shows general provisions (Chapter F) for ALL LGAs
- Shows precinct provisions when applicable
- Clear visual distinction:
  - General: Blue/gray theme with "📘 General Controls" header
  - Precinct: Green/accent theme with "🎯 Precinct-Specific" header
- Category grouping (setbacks, parking, landscaping, etc.)
- Expandable/collapsible sections
- Responsive to zone/devtype changes

**Component Interface:**
```typescript
interface GeneralDCPSectionProps {
  generalData: {
    count: number;
    requirements_count: number;
    provisions: GeneralProvision[];
    requirements: GeneralRequirement[];
    by_category: Record<string, GeneralRequirement[]>;
  };
  precinctData?: {
    precinct_name: string;
    count: number;
    requirements_count: number;
    provisions: PrecinctProvision[];
    requirements: PrecinctRequirement[];
    by_category: Record<string, PrecinctRequirement[]>;
  } | null;
  combinedCategories: CategorySummary[];
  zone: string;
  developmentType: string;
}
```

### Step 4.2: Update ComplianceDashboard (1 hour)

**Update:** `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`

**Changes:**
1. Add call to `/api/compliance/dcp-complete`
2. Pass zone + developmentType from dropdowns
3. Render `<GeneralDCPSection />` component
4. Remove old DCP display logic (if any)

**Integration:**
```typescript
const { data: dcpData, loading: dcpLoading } = useDCPComplete({
  address: selectedAddress,
  zone: planningData.zone,
  developmentType: selectedDevType,
  lga: 'Inner West',
  coordinates: planningData.coordinates
});

return (
  <div>
    {/* LEP Section */}
    {/* SEPP Section */}

    {/* NEW: General DCP Section */}
    {dcpData && (
      <GeneralDCPSection
        generalData={dcpData.general_provisions}
        precinctData={dcpData.precinct_provisions}
        combinedCategories={dcpData.combined.categories}
        zone={planningData.zone}
        developmentType={selectedDevType}
      />
    )}
  </div>
);
```

---

## Phase 5: Testing & Validation (1-2 hours)

### Step 5.1: API Testing (30 min)

**Test addresses:**
```javascript
// Ashfield (already working)
{ address: '123 Smith St, Ashfield', zone: 'R2', devType: 'dwelling_house' }

// Leichhardt
{ address: '123 Norton St, Leichhardt', zone: 'R2', devType: 'dwelling_house' }
{ address: '456 Marion St, Leichhardt', zone: 'R4', devType: 'residential_flat' }

// Marrickville
{ address: '789 King St, Newtown', zone: 'R4', devType: 'residential_flat' }
{ address: '10 Marrickville Rd, Marrickville', zone: 'R2', devType: 'dwelling_house' }
```

**Expected Results:**
- All return 7-40 provisions (zone-filtered)
- All return 10-30 requirements (categorized)
- Response time <100ms
- Different results for R2 vs R4, dwelling vs RFB

### Step 5.2: Frontend Testing (30 min)

**Manual UI Tests:**
1. Enter Ashfield address → See general + precinct provisions
2. Enter Leichhardt address → See general + neighbourhood provisions
3. Enter Marrickville address → See general + neighbourhood provisions
4. Change zone dropdown → Provisions update instantly
5. Change dev type dropdown → Provisions update instantly

**UX Validation:**
- Clear visual distinction between general and precinct
- Category grouping clear and logical
- Expandable sections work
- No loading states >3s

### Step 5.3: Data Quality Validation (30 min)

**SQL Validation Queries:**
```sql
-- 1. Coverage check
SELECT
  lga,
  dcp_chapter,
  COUNT(*) as provision_count,
  COUNT(DISTINCT part_number) as part_count
FROM dcp_general_provisions
GROUP BY lga, dcp_chapter;

-- Expected:
-- INNER WEST | F | ~180-200 | ~24-30 parts (Ashfield + Leichhardt + Marrickville)

-- 2. Zone filtering check
SELECT
  dcp_chapter,
  COUNT(*) as count
FROM dcp_general_provisions
WHERE 'R2' = ANY(applicable_zones)
AND 'dwelling_house' = ANY(development_types)
GROUP BY dcp_chapter;

-- Expected: All 3 DCP chapters represented

-- 3. Requirements check
SELECT
  category,
  COUNT(*) as count
FROM dcp_general_requirements
WHERE lga = 'INNER WEST'
GROUP BY category
ORDER BY count DESC;

-- Expected: ~250-350 total requirements across all suburbs
```

---

## Success Criteria

### Data Layer:
- [x] Ashfield: 65 general provisions ✅
- [ ] Leichhardt: 50-70 general provisions
- [ ] Marrickville: 50-70 general provisions
- [ ] Ashfield: 100 structured requirements ✅
- [ ] Leichhardt: 80-120 structured requirements
- [ ] Marrickville: 80-120 structured requirements
- [ ] All provisions have zone/devtype arrays
- [ ] All provisions filterable by zone AND devtype

### API Layer:
- [ ] API returns general provisions for ALL Inner West addresses
- [ ] Zone filtering works (R2 ≠ R4 results)
- [ ] Dev type filtering works (dwelling ≠ RFB results)
- [ ] Precinct provisions included when applicable
- [ ] Response time <100ms

### Frontend Layer:
- [ ] GeneralDCPSection component displays general + precinct
- [ ] Clear visual distinction (blue vs green)
- [ ] Category grouping works
- [ ] Provisions update when zone dropdown changes
- [ ] Provisions update when devtype dropdown changes
- [ ] Works for Ashfield, Leichhardt, AND Marrickville addresses

### UX Consistency:
- [ ] **All Inner West users get same high-quality experience**
- [ ] No "Ashfield works better than Leichhardt" perception
- [ ] Professional-grade filtering for all suburbs
- [ ] Consistent performance (<100ms) across all suburbs

---

## Risk Assessment

### Low Risk:
- Extraction methodology proven (Ashfield already working)
- Database schema supports multiple LGAs
- API already LGA-agnostic
- Import scripts proven

### Medium Risk:
- Leichhardt/Marrickville DCP structure may differ from Ashfield
- Zone mappings may differ (R2 in one LGA might not exist in another)
- Development type naming may vary between DCPs

### Mitigation:
- Carefully review source documents before extraction
- Verify zone lists for each LGA from LEP
- Test with sample provisions early to catch structure issues
- Create backup before any database imports

---

## Timeline Summary

| Phase | Task | Time |
|-------|------|------|
| Phase 1 | Leichhardt extraction, import, categorization | 4-5 hours |
| Phase 2 | Marrickville extraction, import, categorization | 4-5 hours |
| Phase 3 | API updates | 1-2 hours |
| Phase 4 | Frontend component + integration | 2-3 hours |
| Phase 5 | Testing & validation | 1-2 hours |
| **TOTAL** | **End-to-end implementation** | **12-17 hours** |

---

## Next Steps

**Immediate:**
1. Locate Leichhardt Chapter F markdown/PDF
2. Locate Marrickville Chapter F markdown/PDF
3. Verify document structure matches Ashfield pattern
4. Create database backup before starting

**Then:**
1. Start with Leichhardt extraction (Phase 1)
2. Test Leichhardt API before starting Marrickville
3. Complete Marrickville extraction (Phase 2)
4. Build frontend (Phase 4)
5. Full testing (Phase 5)

---

## Files to Create

### Extraction:
1. `extract_leichhardt_chapter_f.py`
2. `extract_marrickville_chapter_f.py`
3. `leichhardt_chapter_f_general_provisions.json` (output)
4. `marrickville_chapter_f_general_provisions.json` (output)

### Import:
5. `import_leichhardt_general_provisions.py`
6. `import_marrickville_general_provisions.py`

### Categorization:
7. `categorize_leichhardt_general_provisions.py`
8. `categorize_marrickville_general_provisions.py`

### Testing:
9. Update `test_dcp_complete_api.js` (add Leichhardt/Marrickville tests)

### Frontend:
10. `frontend-nextjs/components/compliance/GeneralDCPSection.tsx` (new)
11. Update `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`

### Documentation:
12. This file: `OPTION_C_PLAN_LEICHHARDT_MARRICKVILLE_CHAPTER_F.md`

---

**Status:** Plan Complete - Ready to Execute ✅

**Decision Required:** Approve to proceed with Phase 1 (Leichhardt extraction)
