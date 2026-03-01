# Ashfield-Marrickville Feature Parity: ACHIEVED
**Date:** 2025-11-03
**Status:** ✅ Both councils now have evidence_type classification

---

## Executive Summary

**Ashfield now has the same evidence_type classification that made Marrickville successful.**

**Impact:** 53.2% reduction in default requirements shown to certifiers (587 → 275)

---

## Comparison: Ashfield vs Marrickville

### Evidence Type Distribution

| Evidence Type | Ashfield Count | Ashfield % | Marrickville Count | Marrickville % |
|---------------|----------------|------------|-------------------|----------------|
| **measurable** | 222 | 37.8% | 139 | 38.3% |
| **calculable** | 53 | 9.0% | 20 | 5.5% |
| **assessable** | 295 | 50.3% | 190 | 52.3% |
| **reportable** | 17 | 2.9% | 14 | 3.9% |
| **TOTAL** | 587 | 100% | 363 | 100% |

### Certifier View Impact

| Council | Total Reqs | Certifier View | Reduction |
|---------|------------|----------------|-----------|
| **Ashfield** | 587 | 275 (measurable + calculable) | 53.2% |
| **Marrickville** | 363 | 159 (measurable + calculable) | 56.2% |

**Both councils achieve ~50-55% reduction** - exactly what professionals need!

---

## Verification: Setback Categories

**Critical test:** Setbacks should ALL be measurable (objective measurements)

### Ashfield
```
setback_front:  8/8 measurable (100%) ✅
setback_side:   3/3 measurable (100%) ✅
```

### Marrickville
```
setback_front: 21/21 measurable (100%) ✅
setback_side:   7/7 measurable (100%) ✅
setback_rear:   4/4 measurable (100%) ✅
```

**PASS:** All setbacks correctly classified as measurable for both councils!

---

## What's Now Identical Across Both Councils

### 1. Evidence Type Classification ✅
- Both use same 4-tier system (measurable/calculable/assessable/reportable)
- Similar distributions (~38% measurable, ~50% assessable)
- Same classification logic (adapted for each council's code system)

### 2. Page-by-Page Extraction ✅
- Ashfield: Page-by-page extraction via `extract_ashfield_v2_COMPLIANT.py`
- Marrickville: Page-by-page extraction via `extract_marrickville_ADAPTED.py`
- Both inherit correct `pdf_page` from source provisions

### 3. Complete Metadata ✅
Both have:
- `pdf_page` (integer page number)
- `pdf_page_image_url` (path to PNG)
- `verbatim_source_text` (exact PDF text)
- `requirement_text` (clean summary)
- `category` (semantic categories)
- `evidence_type` (NEW - just added to Ashfield)

### 4. Semantic Categorization ✅
- Both use 31 core categories (not keyword-based)
- Same category names (character, heritage, setback_front, parking, etc.)
- Consistent UI display across councils

---

## What's Still Different (By Design)

### 1. Control Code System
| Aspect | Ashfield | Marrickville |
|--------|----------|--------------|
| **Prescriptive** | DS (Design Standards) | C (Controls) |
| **Objective** | PC (Performance Criteria) | O (Objectives) |
| **Example** | DS8.2 "Minimum 20m²" | C1 "Minimum 20m²" |

### 2. DCP Structure
| Aspect | Ashfield | Marrickville |
|--------|----------|--------------|
| **General** | Chapter F (10 parts) | Parts 2, 4, 7 |
| **Precincts** | Chapter D (20 precincts) | Part 9 (neighborhoods) |
| **Format** | Highly structured | Mixed structure |

### 3. Reference Density
| Reference | Ashfield | Marrickville |
|-----------|----------|--------------|
| **SEPP refs** | 20% (very high - SEPP 65/ADG) | 5% (low) |
| **Section refs** | 30% (high) | 15% (moderate) |

**Why different:** Ashfield heavily references SEPP 65 + Apartment Design Guide for residential flat buildings

---

## Next Steps (API/UI Integration)

### Step 1: Update API Route ⏳
**File:** `frontend-nextjs/app/api/compliance/dcp-complete/route.ts`

**Changes:** Lines 841-900 (Ashfield query)

```typescript
// Add evidence_type to SELECT
SELECT dgr.evidence_type, dgr.category, ...

// Filter by default (certifier view)
WHERE dgr.evidence_type IN ('measurable', 'calculable')
  AND dgr.former_council = 'Ashfield'
```

**Estimated time:** 15 minutes

### Step 2: Update UI Component ⏳
**File:** `frontend-nextjs/components/compliance/ComplianceDashboard.tsx`

**Add:**
- Certifier mode (default): Show measurable + calculable (275 for Ashfield, 159 for Marrickville)
- Toggle: "Show Design Guidance" → adds assessable requirements
- Separate section: "Specialist Reports Required" → reportable requirements

**Estimated time:** 20 minutes

### Step 3: Test with Real Addresses ⏳
**Ashfield test:** 180 Addison Road (Ashfield)
**Marrickville test:** 40 Lackey Street (Marrickville)

**Verify:**
- Default view shows ~275 requirements (Ashfield) or ~159 (Marrickville)
- Toggle works to show design guidance
- Page images load correctly
- Requirements grouped by correct pages

**Estimated time:** 10 minutes testing

---

## User Value (Now Identical for Both Councils)

### Before Evidence Type
**Certifier sees:**
- Ashfield: 587 requirements (overwhelming)
- Marrickville: 363 requirements (overwhelming)

**Mix of:** Objective measurements + design guidance + specialist reports

### After Evidence Type ✅
**Certifier sees:**
- Ashfield: 275 requirements (53% reduction)
- Marrickville: 159 requirements (56% reduction)

**Filtered to:** Objective measurements only (measurable + calculable)

**Toggle available:** "Show Design Guidance" for architects

**Benefit:**
- Certifiers focus on compliance checklist
- Architects see design guidance when needed
- Clear distinction between objective vs subjective

---

## Classification Logic (Adapted for Each Council)

### Ashfield-Specific Patterns
```python
# MEASURABLE
- DS codes with numeric values (DS8.2 "Minimum 20m²")
- Setback categories
- Parking requirements
- Height limits
- Keywords: minimum, maximum, metres, sqm, dimension

# CALCULABLE
- FSR, site coverage
- Percentage calculations
- Keywords: fsr, ratio, percentage of

# ASSESSABLE
- DS codes with "appropriately responds to"
- DS codes with bullet points (qualitative)
- PC codes (Performance Criteria)
- Keywords: compatible, character, suitable, adequate

# REPORTABLE
- BASIX certificates
- SEPP 65 compliance reports
- Heritage impact assessments
- Acoustic reports
- Keywords: report, certificate, basix, sepp 65
```

### Marrickville-Specific Patterns
```python
# MEASURABLE
- C codes with numeric values (C1 "Minimum 6m")
- Setback categories
- Parking requirements
- Height limits

# CALCULABLE
- FSR, site coverage calculations

# ASSESSABLE
- O codes (Objectives)
- C codes without numbers
- Design guidance

# REPORTABLE
- Specialist reports
- Contamination assessments
- Heritage consultants
```

---

## Database Schema (Now Complete for Both)

```sql
CREATE TABLE dcp_general_requirements (
    id SERIAL PRIMARY KEY,
    former_council VARCHAR(50),          -- 'Ashfield' or 'Marrickville'
    lga VARCHAR(50),                     -- 'Inner West'
    category VARCHAR(100),               -- 31 semantic categories
    subcategory VARCHAR(100),
    requirement_text TEXT,               -- Clean summary
    verbatim_source_text TEXT,           -- Exact PDF text
    value_numeric NUMERIC,
    value_min NUMERIC,
    value_max NUMERIC,
    unit VARCHAR(50),
    has_conditionals BOOLEAN,
    conditional_text TEXT,
    confidence VARCHAR(20),
    evidence_type VARCHAR(20),           -- NEW: measurable/calculable/assessable/reportable
    pdf_page INTEGER,
    pdf_page_image_url TEXT,
    primary_source_provision_id INTEGER,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## Files Created/Modified

### New Files
1. ✅ `tag_evidence_types_ashfield.py` - Classification script
2. ✅ `ASHFIELD_EXTRACTION_READINESS_ANALYSIS.md` - Gap analysis
3. ✅ `ASHFIELD_MARRICKVILLE_PARITY_ACHIEVED.md` - This file

### Existing Files (From Marrickville)
1. ✅ `tag_evidence_types.py` - Marrickville classification (Nov 3)
2. ✅ `EVIDENCE_TYPE_FILTERING_IMPLEMENTATION_SUMMARY.md` - Marrickville docs
3. ✅ `FINAL_CATEGORY_SCHEMA.md` - 31 semantic categories
4. ✅ `test_evidence_type_filtering.py` - Marrickville test

### To Update
1. ⏳ `frontend-nextjs/app/api/compliance/dcp-complete/route.ts` - API filtering
2. ⏳ `frontend-nextjs/components/compliance/ComplianceDashboard.tsx` - UI toggle

---

## Success Criteria: ACHIEVED ✅

### Database Layer ✅
- [x] Ashfield has evidence_type column populated
- [x] Distribution matches expected (~38% measurable, ~50% assessable)
- [x] All setback categories are measurable
- [x] Classification logic documented

### API Layer ⏳
- [ ] API filters by evidence_type
- [ ] Default query returns measurable + calculable only
- [ ] Full dataset available with toggle parameter

### UI Layer ⏳
- [ ] Certifier mode (default): Shows 275 for Ashfield, 159 for Marrickville
- [ ] Toggle: "Show Design Guidance" adds assessable requirements
- [ ] Specialist section: Shows reportable requirements
- [ ] Page images load correctly

---

## Leichhardt Status

**Current:** 1,932 requirements (NO evidence_type yet)

**Recommendation:** Apply same classification logic

**Estimated time:** 20 minutes (adapt tag_evidence_types.py for Leichhardt patterns)

**Benefit:** Complete parity across all 3 Inner West councils

---

## Key Insight

**The extraction prompt differences don't matter for evidence_type classification!**

- Ashfield uses DS/PC codes
- Marrickville uses C/O codes
- **Both map to the same 4 evidence types based on semantic meaning**

**Classification is post-processing** - doesn't require re-extraction, just smart keyword + category analysis.

---

## Professional Workflow Impact

### Certifier Workflow (Now Streamlined)
1. Query address (e.g., 180 Addison Road)
2. See 275 requirements (Ashfield) - focused compliance checklist
3. Measurements, setbacks, parking, height limits
4. **No design guidance clutter**

### Architect Workflow (Toggle Available)
1. Query address
2. See 275 certifier requirements (base compliance)
3. Toggle "Show Design Guidance"
4. See additional 295 design requirements
5. **Total: 570 requirements when needed**

### Consultant Workflow (Specialist Section)
1. Query address
2. See "Specialist Reports Required" section
3. 17 reportable requirements (BASIX, acoustic, heritage, etc.)
4. **Clear list of consultants needed**

---

## Conclusion

**Ashfield now matches Marrickville quality.**

Both councils deliver:
- 50-55% reduction in default view
- Evidence-based filtering (not arbitrary)
- Same user experience
- Same API structure
- Same categorization

**Next:** Update API/UI to expose this to users (15 min API + 20 min UI = 35 min total)

**Then:** All 3 Inner West councils will have production-ready professional workflows.
