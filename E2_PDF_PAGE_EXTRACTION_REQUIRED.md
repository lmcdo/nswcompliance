# E2 Haberfield Heritage Requirements: PDF Page Extraction Required

**Date:** 2025-11-21
**Status:** 🔴 CRITICAL ISSUE IDENTIFIED
**Priority:** P1 - Affects all 12 E2 heritage requirements
**Issue Type:** Missing Data + Wrong Image Mapping

---

## Executive Summary

**Problem:** E2 Haberfield heritage requirements currently display **diagram illustrations** (roof diagrams, setback diagrams) instead of **actual PDF pages** containing the verbatim requirement text.

**Root Cause:**
1. E2 requirements were extracted with MinerU diagrams as images
2. PDF pages were never extracted and converted to PNGs
3. Database has `pdf_pages = NULL` for all 12 E2 requirements
4. `pdf_page_image_url` points to diagrams, not PDF pages

**Impact:** Users cannot see the original DCP text that requirements were extracted from.

---

## Current State (WRONG)

### Database Reality
```sql
SELECT id, requirement_text, pdf_pages, pdf_page_image_url
FROM dcp_precinct_requirements
WHERE precinct_id = 'E2';

-- Results: All 12 requirements have:
--   pdf_pages: NULL
--   pdf_page_image_url: images/[diagram-hash].jpg (MinerU diagrams)
```

### What Users See
```
Character Requirements
✓ Haberfield is characterized by single storey brick houses...
  [View heritage controls] ← Shows roof/setback DIAGRAM (wrong)

Expected: Shows actual PDF page 2 with verbatim text
Actual: Shows illustration diagram extracted by MinerU
```

### Current Image Mapping
| Requirement ID | Text | Current Image | Image Type |
|----------------|------|---------------|------------|
| 2329 | Haberfield is characterized... | d8e25d20a3d58f76... | Roof diagram |
| 2330 | Facilitate development... | edc040d35f5ed74a... | Boundary map |
| 2333 | Uniform front setback... | 6fe537c7ca210592... | Setback diagram |
| 2335 | Extensions to rear... | fcd198be5ed0a08e... | Extension diagram |
| 2337 | New roofs lower... | d8e25d20a3d58f76... | Roof diagram |

**Problem:** These are illustrative diagrams FROM the PDF, not the PDF pages themselves.

---

## Expected State (CORRECT)

### What Should Exist
```bash
# PDF page PNGs should exist:
frontend-nextjs/public/pdf-pages/leichhardt-e2/page_1.png  # Cover
frontend-nextjs/public/pdf-pages/leichhardt-e2/page_2.png  # Character section
frontend-nextjs/public/pdf-pages/leichhardt-e2/page_3.png  # Pattern of Development
frontend-nextjs/public/pdf-pages/leichhardt-e2/page_4.png  # Building Form
frontend-nextjs/public/pdf-pages/leichhardt-e2/page_5.png  # Setbacks
...
```

### Database Should Have
```sql
-- Example after fix:
ID 2329: "Haberfield is characterized..."
  pdf_pages: [2]  -- Page 2 in E2 PDF
  pdf_page_image_url: /pdf-pages/leichhardt-e2/page_2.png

ID 2333: "Uniform front setback..."
  pdf_pages: [5]  -- Page 5 in E2 PDF
  pdf_page_image_url: /pdf-pages/leichhardt-e2/page_5.png
```

### What Users Should See
```
Character Requirements
✓ Haberfield is characterized by single storey brick houses...
  [View heritage controls] ← Shows PDF page 2 with VERBATIM TEXT
```

---

## How Other Councils Were Done (Reference)

### Ashfield Chapter F (CORRECT APPROACH)
**Files Created:**
- `extract_ashfield_chapter_f_pages.py` - Extracted 73 PDF pages
- Created PNGs: `public/pdf-pages/ashf_..._page_X.png`
- Database populated: ALL 186 requirements have page numbers

**Result:** ✅ Working correctly - users see actual DCP pages

### Leichhardt Parts A-G (CORRECT APPROACH)
**Files Created:**
- Multiple extraction scripts for each part
- Created folders: `public/pdf-pages/leichhardt-part-{a,b,c1,c2,d,e,f,g}/`
- Database populated: ALL 1,932 requirements have page numbers

**Result:** ✅ Working correctly - users see actual DCP pages

### Marrickville (CORRECT APPROACH)
**Files Created:**
- Part-by-part extraction
- Created PNGs in `public/pdf-pages/`
- Database populated: ALL 363 requirements have page numbers

**Result:** ✅ Working correctly - users see actual DCP pages

---

## Why E2 Is Different (The Problem)

### What Happened During E2 Extraction

**Step 1: MinerU Markdown Extraction** ✅ (Nov 2024)
- MinerU extracted E2 PDF → markdown
- Output: `output/Chapter E2 Haberfield Neighbourhood/auto/Chapter E2 Haberfield Neighbourhood.md`
- Included 14 images (diagrams, maps, illustrations)

**Step 2: LLM Categorization** ✅ (Nov 2024)
- LLM extracted 12 structured requirements from markdown
- Stored in `dcp_precinct_requirements`
- **BUT:** Used MinerU diagram images, not PDF pages

**Step 3: PDF Page Extraction** ❌ **NEVER DONE**
- No script created to extract E2 PDF pages
- No PNGs generated
- No page number mapping

**Step 4: Image Mapping (Yesterday)** ⚠️ **WRONG IMAGES**
- `map_e2_correctly.js` mapped requirements → MinerU diagrams
- Keyword matching: "setback" → setback diagram
- **Result:** Requirements show diagrams, not PDF pages

---

## Technical Analysis

### Source Document
**File:** `Inner West Leichhardt DCP 2013 - Part E2 - Haberfield Heritage Conservation Area.pdf`
**Location:** Original PDF should be in source documents

### MinerU Extraction Output
```bash
output/Chapter E2 Haberfield Neighbourhood/auto/
├── Chapter E2 Haberfield Neighbourhood.md  # Markdown with text
├── Chapter E2 Haberfield Neighbourhood_content_list.json  # Page metadata
└── images/
    ├── edc040d35f5ed74a46f45b787053d882acada90b8fe635d1d24cb4df05714635.jpg  # Boundary map (Figure 1)
    ├── fcd198be5ed0a08e199fa3ee2c42c84599ade7da078b7725f714c39c0deef058.jpg  # Extension diagram (Figure 2)
    ├── d8e25d20a3d58f7642ae614aba7c6b3a1cc06b2f1836d75d1586b95290f7cbb3.jpg  # Roof diagram (Figure 4)
    ├── 6fe537c7ca2105929b439db5105d67f266a2e7d5e99a108b06299b6de2cbc384.jpg  # Setback diagram (Figure 5)
    └── ... (10 more diagrams)
```

**These are illustrations FROM the PDF, not the PDF pages themselves!**

### Requirement → PDF Page Mapping (Unknown)

Current database has 12 requirements but no page numbers. Need to determine:

| Requirement | Topic | Likely PDF Page | Section |
|-------------|-------|-----------------|---------|
| 2329 | Character description | Page 1-2 | Existing Character |
| 2330 | Facilitate development | Page 2 | Objectives O1 |
| 2331 | Maintain heritage | Page 2 | Objectives O2 |
| 2332 | Carefully designed | Page 2 | Objectives O3 |
| 2333 | Front setback 6m | Page 5 | Controls C22 (Setbacks) |
| 2334 | Side setbacks | Page 5 | Controls C22 |
| 2335 | Extensions to rear | Page 2 | Controls C3 |
| 2336 | Site coverage | Page 2 | Controls C1 |
| 2337 | New roofs lower | Page 4 | Controls C9 (Building Form) |
| 2338 | Attic within roof | Page 4 | Controls C11 |
| 2339 | Attic modest scale | Page 4 | Controls C12 |
| 2340 | Remove detrimental | Page 2 | Objectives O7 |

**Note:** These page numbers are estimates from markdown structure. Need actual PDF to confirm.

---

## Implementation Plan

### Phase 1: PDF Page Extraction

**Script to Create:** `extract_e2_pdf_pages.py`

```python
# Extract all pages from E2 PDF as PNG images
# Output: frontend-nextjs/public/pdf-pages/leichhardt-e2/page_X.png
# Similar to extract_ashfield_chapter_f_pages.py
```

**Requirements:**
- Input: E2 PDF file path
- Library: PyMuPDF (fitz) for PDF→PNG conversion
- Output folder: `frontend-nextjs/public/pdf-pages/leichhardt-e2/`
- DPI: 150 (same as other councils)
- Format: PNG

**Expected Output:**
```bash
frontend-nextjs/public/pdf-pages/leichhardt-e2/
├── page_1.png   # Cover/title
├── page_2.png   # Character & Objectives
├── page_3.png   # Pattern of Development
├── page_4.png   # Building Form
├── page_5.png   # Setbacks
├── page_6.png   # Walls
└── ... (estimated 10-15 pages)
```

### Phase 2: Requirement → Page Mapping

**Script to Create:** `map_e2_requirements_to_pdf_pages.py`

```python
# Map each of 12 requirements to their source PDF page number
# Method 1: Text matching (compare requirement text to page text)
# Method 2: Manual mapping from markdown structure
# Method 3: Use MinerU content_list.json page metadata
```

**Process:**
1. Read E2 markdown to understand section structure
2. Read MinerU `content_list.json` for page boundaries
3. For each requirement, determine source page number
4. Generate SQL to update `pdf_pages` array and `pdf_page_image_url`

**Output:** SQL file with updates like:
```sql
-- Update requirement ID 2329 (character)
UPDATE dcp_precinct_requirements
SET
  pdf_pages = ARRAY[2],
  pdf_page_image_url = '/pdf-pages/leichhardt-e2/page_2.png'
WHERE id = 2329;

-- Update requirement ID 2333 (setbacks)
UPDATE dcp_precinct_requirements
SET
  pdf_pages = ARRAY[5],
  pdf_page_image_url = '/pdf-pages/leichhardt-e2/page_5.png'
WHERE id = 2333;
```

### Phase 3: Database Update

**Script to Create:** `update_e2_pdf_page_mappings.sql`

```sql
-- Backup first
CREATE TABLE dcp_precinct_requirements_backup_e2_fix AS
SELECT * FROM dcp_precinct_requirements WHERE precinct_id = 'E2';

-- Apply updates (generated from Phase 2)
UPDATE dcp_precinct_requirements SET ... WHERE id = 2329;
UPDATE dcp_precinct_requirements SET ... WHERE id = 2330;
-- ... (12 updates total)

-- Verification
SELECT id, pdf_pages, pdf_page_image_url
FROM dcp_precinct_requirements
WHERE precinct_id = 'E2';
```

### Phase 4: Frontend Verification

**Test with:** 34 Dalhousie St, Haberfield NSW 2045

**Expected Result:**
```
Character Requirements
✓ Haberfield is characterized by single storey brick houses...
  [View heritage controls] ← Opens PDF page 2 (not diagram)

✓ Uniform front building setback of approximately 6 metres.
  [View heritage controls] ← Opens PDF page 5 (not diagram)
```

---

## Success Criteria

### Database
- ✅ All 12 E2 requirements have `pdf_pages != NULL`
- ✅ All 12 requirements have `pdf_page_image_url` pointing to PNG files
- ✅ PNG paths are `/pdf-pages/leichhardt-e2/page_X.png` format

### File System
- ✅ Folder `frontend-nextjs/public/pdf-pages/leichhardt-e2/` exists
- ✅ Contains 10-15 PNG files (one per PDF page)
- ✅ Each PNG is actual PDF page, not diagram

### User Experience
- ✅ Clicking "View heritage controls" opens actual DCP page
- ✅ User can read verbatim requirement text on page
- ✅ Page numbers match DCP document structure
- ✅ No diagrams shown (unless user specifically wants them)

---

## Comparison: Diagrams vs PDF Pages

### Current (WRONG): Diagrams
**User clicks "View heritage controls"**
→ Sees: Illustration/diagram (e.g., roof shapes sketch)
→ Problem: No verbatim text, no context, no DCP reference

**Example:** Setback requirement shows abstract setback diagram
- ❌ No actual setback distance visible
- ❌ No DCP clause reference
- ❌ No complete sentence/context

### Expected (CORRECT): PDF Pages
**User clicks "View heritage controls"**
→ Sees: Actual DCP page with full text
→ Contains: Complete requirement, clause number, context

**Example:** Setback requirement shows PDF page 5
- ✅ Full text: "C22. The established pattern of front and side setbacks should be kept..."
- ✅ Shows surrounding controls
- ✅ Includes diagrams IN CONTEXT of text

---

## Related Files & Documentation

### Existing Scripts (Reference)
- `extract_ashfield_chapter_f_pages.py` - Ashfield PDF extraction (WORKING)
- `extract_leichhardt_part_*.py` - Leichhardt PDF extraction (WORKING)
- `map_e2_correctly.js` - Current E2 mapping (WRONG - uses diagrams)

### Documentation
- `ASHFIELD_EXTRACTION_COMPLETE_FINAL.md` - How Ashfield Chapter F was done
- `ASHFIELD_HABERFIELD_COMPLETE_SUMMARY.md` - Original E2 extraction (incomplete)
- `HERITAGE_PRECINCT_AND_PDF_PAGE_FIX.md` - Recent heritage fixes

### Source Files
- `output/Chapter E2 Haberfield Neighbourhood/auto/Chapter E2 Haberfield Neighbourhood.md` - MinerU markdown
- `output/Chapter E2 Haberfield Neighbourhood/auto/Chapter E2 Haberfield Neighbourhood_content_list.json` - Page metadata

---

## Lessons Learned

### What Went Wrong
1. **Assumed MinerU images = PDF pages** (they're not)
2. **Never extracted actual PDF pages** for E2
3. **Yesterday's "fix"** mapped requirements to wrong image type

### Why This Matters
- **User need:** See verbatim DCP text to understand requirement
- **Legal need:** Reference exact clause and page number
- **Professional use:** Certifiers need to cite specific DCP sections

### How to Prevent
- **Always extract PDF pages** when extracting requirements
- **Diagrams ≠ PDF pages** - diagrams supplement, don't replace
- **Check file system** before claiming images exist

---

## Next Steps

1. ✅ **Document issue** (this file)
2. ⏳ **Create `extract_e2_pdf_pages.py`** (convert PDF → PNGs)
3. ⏳ **Create `map_e2_requirements_to_pdf_pages.py`** (determine page numbers)
4. ⏳ **Generate and run SQL** to update database
5. ⏳ **Test in UI** with Haberfield address
6. ⏳ **Verify all 12 requirements** show correct pages

---

## Bottom Line

**Current State:** E2 requirements show MinerU diagram illustrations (wrong)

**Required Fix:** Extract actual E2 PDF pages and map requirements to pages

**Estimated Time:** 30-45 minutes
- PDF extraction: 10 min
- Page mapping: 15-20 min
- Database update: 5 min
- Testing: 5-10 min

**Priority:** P1 - Blocks E2 functionality from being production-ready

---

**Status:** 🔴 BLOCKING - E2 requirements unusable until fixed
