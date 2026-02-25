# Pattern Book Implementation - Next Steps

**Date:** 2026-02-26
**Status:** ✅ Investigation Complete - Ready for Implementation

---

## What We Discovered

### The 217/199/9 Numbers Are FAKE

| Metric | Claimed | Actual | Status |
|--------|---------|--------|--------|
| Exclusion triggers | 217 | **51** | ❌ 76% inflated |
| Numeric standards | 199 | **87** | ❌ 56% inflated |
| Override rules | 9 | **76** | ❌ 744% undercount |

**Source:** SEPP (Exempt and Complying Development Codes) 2008 Schedule 1 (Housing Code)

**See:** `PATTERN-BOOK-VERIFICATION-REPORT.md` for full analysis

---

## What We Have

✅ **All 454 Codes SEPP PDF pages extracted** at `pdf-pages/sepp-exempt-complying/page_*.png`

✅ **Housing Code pages identified:**
- Pages 115-200: Core exclusions and standards
- Page 115-130: Exclusion clauses (3.2, lot types, initial standards)
- Page 130-180: Development standards (setbacks, landscaping, parking, heights)
- Page 180-200: Additional standards and special provisions

✅ **Complete markdown source** at:
```
archive/2026-01-extraction-outputs/extraction_outputs/sepps/
State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation/auto/
State Environmental Planning Policy (Exempt and Complying Development Codes) 2008 - NSW Legislation.md
```

✅ **Database schema ready** (`sepp_structured_requirements` table exists with proper columns)

❌ **Database has only 3 rows** (needs 214+ rows of actual Housing Code data)

---

## Implementation Tasks

### 1. Update Frontend Numbers (15 min)

**Files to update:**

**A. PatternBookEligibilityCard.tsx (lines 344-354)**
```typescript
// Change hardcoded numbers
51 exclusion triggers checked     // was 217
87 numeric standards verified     // was 199
76 override rules evaluated       // was 9
```

**B. regulatory-constants.ts**
```typescript
export const PATTERN_BOOK_CDC = {
  EXCLUSION_TRIGGERS_COUNT: 51,    // was 217
  NUMERIC_STANDARDS_COUNT: 87,     // was 199
  OVERRIDE_RULES_COUNT: 76,        // was 9
  SOURCE: 'SEPP Codes 2008 Schedule 1',
  VERIFIED_DATE: '2026-02-26',
};
```

**C. route.ts API comment (line 12-15)**
```typescript
/**
 * Housing Code Schedule 1 requirements:
 * - 51 exclusion triggers
 * - 87 numeric standards
 * - 76 override clauses
 */
```

### 2. Extract Structured Data from Housing Code (2-3 hours)

**Input:** Markdown file (lines 3897-8000)
**Output:** 214 rows for `sepp_structured_requirements`

**Extraction script needed:**

```python
# Script: extract_housing_code_provisions.py

# Parse markdown lines 3897-8000
# For each clause:
#   - Extract clause number (3.2, 3.10, 3A.1A, etc.)
#   - Extract clause title
#   - Extract full clause text
#   - Categorize as exclusion, numeric_standard, or override
#   - Parse numeric values and units
#   - Extract exclusion types (heritage, flood, bushfire, etc.)
#   - Map to provision_id in regulatory_provisions table
#   - Insert into sepp_structured_requirements

# Expected output:
#   - 51 exclusion rows
#   - 87 numeric_standard rows
#   - 76 override rows
```

**Key fields to populate:**
- `requirement_category`: 'exclusion', 'numeric_standard', 'override'
- `exclusion_type`: 'heritage', 'flood_planning_area', 'bushfire_prone', etc.
- `metric_name`: 'setback_front_m', 'landscaped_area_percent', etc.
- `metric_value`, `metric_unit`, `metric_operator`
- `applies_to`: 'Pattern_Book'
- `source_clause`: 'Schedule 1, Clause 3.2', etc.

### 3. Update Pattern Book Eligibility Logic (1 hour)

**File:** `frontend-nextjs/lib/pattern-book-eligibility/check-exclusions.ts`

Current logic queries `sepp_structured_requirements` but table only has 3 rows.

**After populating database:**
- Query will return actual exclusions (51 rows)
- Check-exclusions.ts will work as designed
- API will return real exclusion results, not 0

### 4. Add PDF Page Links (30 min)

**File:** `pdf-url-builder.ts`

Add Housing Code PDF URL function:
```typescript
export function getHousingCodePdfUrl(page: number): string {
  return getSeppPdfUrl('exempt_complying', page);
}
```

Use in PatternBookEligibilityCard to link to relevant pages for each exclusion/standard.

### 5. Test Pattern Book Eligibility Flow (30 min)

**Test cases:**
1. Property with heritage → should trigger exclusion from clause 3.2(various)
2. Property in flood zone → should trigger exclusion
3. Property in R1/R2/R3 zone → should pass zone eligibility
4. Property with correct lot size → should pass standards check

### 6. Documentation Updates (15 min)

- Update README with corrected statistics
- Add source citations to all Pattern Book claims
- Link to PATTERN-BOOK-VERIFICATION-REPORT.md

---

## Priority Order

**P0 - Immediate (do first):**
1. Update frontend numbers (217→51, 199→87, 9→76)
2. Add source citations

**P1 - This Week:**
3. Extract structured data to database (214 rows)
4. Test eligibility logic with real data

**P2 - Next Sprint:**
5. Add PDF page links
6. Full integration testing

---

## File Locations Reference

```
PDF pages:
  pdf-pages/sepp-exempt-complying/page_115.png through page_200.png

Markdown source:
  archive/2026-01-extraction-outputs/extraction_outputs/sepps/
  State Environmental Planning Policy.../auto/...md
  Lines 3897-8000 (Housing Code Schedule 1)

Frontend:
  frontend-nextjs/components/compliance/PatternBookEligibilityCard.tsx
  frontend-nextjs/lib/regulatory-constants.ts
  frontend-nextjs/lib/pattern-book-eligibility/check-exclusions.ts
  frontend-nextjs/app/api/pathway/pattern-book-eligibility/route.ts

Database:
  Table: sepp_structured_requirements (currently 3 rows, needs 214)
  Schema: frontend-nextjs/migrations/001_create_sepp_structured_requirements.sql
```

---

## Questions Resolved

✅ **Q: Where do 217/199/9 numbers come from?**
A: Fabricated. No legislative basis.

✅ **Q: Are Pattern Book PDFs needed?**
A: No. Pattern Book PDFs are design guides. Eligibility criteria are in Codes SEPP.

✅ **Q: What pages need extraction?**
A: Already extracted. Pages 115-200 contain all Housing Code provisions.

✅ **Q: What's the actual provision count?**
A: 51 exclusions, 87 standards, 76 overrides = 214 total provisions
