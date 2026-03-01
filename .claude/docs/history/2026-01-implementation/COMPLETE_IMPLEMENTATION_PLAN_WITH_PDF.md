# Complete Re-Extraction Plan - With Full PDF Metadata
## All 3 Councils - NO Shortcuts

**Date:** 2025-10-31
**Objective:** Re-extract all general provisions with development_types + full PDF metadata

---

## Current State (From Database)

### Ashfield
- Source: regulatory_provisions (10 provisions)
- PDF metadata: **100% complete** ✓
  - pdf_page: 10/10 (100%)
  - pdf_page_image_url: 10/10 (100%)
- **READY for extraction**

### Marrickville
- Source: regulatory_provisions (152 provisions - Section 1 + 2.X)
- PDF metadata: **100% complete** ✓
  - pdf_page: 152/152 (100%)
  - pdf_page_image_url: 152/152 (100%)
- **READY for extraction**

### Leichhardt
- Source: regulatory_provisions (1,004 provisions - Parts A-F)
- PDF metadata: **0% complete** ✗
  - pdf_page: 0/1,004 (0%)
  - pdf_page_image_url: 0/1,004 (0%)
  - pdf_source_file: 0/1,004 (0%)
- **NEEDS PDF metadata population**

### PDF Files Exist
```
✓ Part A: output/Leichhardt DCP 2013 - 3 - Part A  Introduction.../..._origin.pdf
✓ Part B: output/Leichhardt DCP 2013 - 4 - Part B Connections.../..._origin.pdf
✓ Part C: output/Leichhardt DCP 2013 - 5 -  Part C Place Section 1.../..._origin.pdf
✓ Part D: output/Leichhardt DCP 2013 - 9 - Part D Energy.../..._origin.pdf
✓ Part E: output/Leichhardt DCP 2013 - 10 - Part E Water.../..._origin.pdf
✓ Part F: output/Leichhardt DCP 2013 - 11 - Part F Food.../..._origin.pdf
```

---

## Phase 0: Leichhardt PDF Metadata Population

### Step 1: Populate pdf_page + pdf_source_file in regulatory_provisions

**Script to create:** `populate_leichhardt_pdf_metadata.py`

**Process:**
1. For each of Parts A, B, C, D, E, F:
   - Find provisions in regulatory_provisions
   - Find corresponding PDF file in output/
   - Open PDF and get page_number from provision.page_number
   - Update regulatory_provisions:
     - SET pdf_page = page_number
     - SET pdf_source_file = '/path/to/pdf_origin.pdf'
2. Verify 100% updated

**Expected result:**
- 1,004 Leichhardt provisions have pdf_page populated
- 1,004 Leichhardt provisions have pdf_source_file populated

**Time:** 10-15 minutes

### Step 2: Generate PDF Page Images

**Script to use:** `scripts/extract_all_dcp_page_images.py`

**Requirements:**
- Input: regulatory_provisions WHERE pdf_page IS NOT NULL
- Process: Extract page images from PDFs using PyMuPDF
- Output: Save to `frontend-nextjs/public/pdf-pages/leichhardt-part-{X}/page_{N}.png`
- Update: SET pdf_page_image_url = '/pdf-pages/leichhardt-part-{X}/page_{N}.png'

**Expected result:**
- 1,004 PNG images generated
- 1,004 provisions have pdf_page_image_url populated

**Time:** 20-30 minutes (image generation is slow)

### Phase 0 Total: 30-45 minutes

---

## Phase 1: Ashfield Re-Extraction (15-20 min)

### Source Data
- regulatory_provisions: 10 provisions (1 per Part)
- PDF metadata: 100% available ✓

### Extraction Script
**File:** `reextract_ashfield_chapter_f_complete.py`

**Process:**
1. DELETE FROM dcp_general_requirements WHERE former_council = 'Ashfield'
2. For each of 10 Parts:
   - Get provision from regulatory_provisions (with PDF metadata)
   - LLM extracts actionable requirements (batch size 50)
   - Tag each requirement:
     - development_types: Part-specific per ASHFIELD_REEXTRACTION_SPEC.json
     - applicable_zones: NULL (no zone filtering)
     - pdf_page: from source provision
     - pdf_page_image_url: from source provision
     - source_provision_ids: [source_provision_id]
   - Import to dcp_general_requirements
3. Validate: 100% have development_types, 100% have PDF metadata

### Expected Output
- Delete: 775 old requirements
- Create: 80-150 new requirements
- Development types populated:
  - Part 1: ['dwelling_house']
  - Part 2: ['secondary_dwelling']
  - Part 4: ['multi_dwelling_housing', 'townhouse', 'manor_house']
  - Part 5: ['residential_flat_building', 'shop_top_housing']
  - (etc. per spec)
- Zones: NULL (all parts)
- PDF metadata: 100%

---

## Phase 2: Marrickville Re-Extraction (35-45 min)

### Source Data
- regulatory_provisions: 152 provisions (Section 1 + 2.X)
- PDF metadata: 100% available ✓

### Extraction Script
**File:** `reextract_marrickville_sections_1_2x.py`

**Process:**
1. DELETE FROM dcp_general_requirements WHERE former_council = 'Marrickville' AND (part_number LIKE 'Section 1%' OR part_number LIKE 'Section 2.%')
2. For each of 17 sections:
   - Get provisions from regulatory_provisions (with PDF metadata)
   - LLM extracts actionable requirements (batch size 50)
   - Tag each requirement:
     - development_types: ['ALL'] (general provisions apply to all dev types)
     - applicable_zones: NULL (no zone filtering)
     - pdf_page: from source provision
     - pdf_page_image_url: from source provision
     - source_provision_ids: [source_provision_id]
   - Import to dcp_general_requirements
3. Validate: 100% have development_types = ['ALL'], 100% have PDF metadata

### Expected Output
- Delete: ~400 old requirements (Section 1 + 2.X)
- Create: 250-400 new requirements
- Development types: ['ALL'] for all requirements
- Zones: NULL
- PDF metadata: 100%

---

## Phase 3: Leichhardt Re-Extraction (60-75 min)

### Source Data
- regulatory_provisions: 1,004 provisions (Parts A-F)
- PDF metadata: **100% available after Phase 0** ✓

### Extraction Script
**File:** `reextract_leichhardt_parts_abcdef.py`

**Process:**
1. DELETE FROM dcp_general_requirements WHERE former_council = 'Leichhardt' AND part_number IN ('Part A', 'Part B', 'Part C Section 1', 'Part D', 'Part E', 'Part F')
2. For each of 6 parts (A, B, C Section 1, D, E, F):
   - Get provisions from regulatory_provisions (with PDF metadata)
   - LLM extracts actionable requirements (batch size 50)
   - Tag each requirement:
     - development_types: ['ALL'] (general provisions apply to all dev types)
     - applicable_zones: NULL (no zone filtering)
     - pdf_page: from source provision
     - pdf_page_image_url: from source provision
     - source_provision_ids: [source_provision_id]
   - Import to dcp_general_requirements
3. Validate: 100% have development_types = ['ALL'], 100% have PDF metadata

### Expected Output
- Delete: ~700 old requirements (Parts A-F)
- Create: 600-900 new requirements
- Development types: ['ALL'] for all requirements
- Zones: NULL
- PDF metadata: 100%

---

## Final Verification

### Database Checks
```sql
-- Check all 3 councils have development_types
SELECT former_council,
       COUNT(*) as total,
       COUNT(CASE WHEN development_types IS NOT NULL THEN 1 END) as has_devtypes,
       COUNT(pdf_page) as has_pdf_page,
       COUNT(pdf_page_image_url) as has_pdf_url
FROM dcp_general_requirements
WHERE former_council IN ('Ashfield', 'Marrickville', 'Leichhardt')
GROUP BY former_council;

-- Expected:
-- Ashfield: 80-150 requirements, 100% devtypes, 100% PDF
-- Marrickville: 250-400 requirements, 100% devtypes, 100% PDF
-- Leichhardt: 600-900 requirements, 100% devtypes, 100% PDF
```

### API Tests
```javascript
// Test 1: Ashfield
POST /api/compliance/dcp-complete
{
  "address": "10 Pile Street, Haberfield NSW 2045",
  "zone": "R2",
  "developmentType": "dwelling_house"
}
// Expected: Returns Part 1 requirements with PDF links

// Test 2: Marrickville
POST /api/compliance/dcp-complete
{
  "address": "181 Addison Road, Marrickville NSW 2200",
  "zone": "R3",
  "developmentType": "dwelling_house"
}
// Expected: Returns Section 2.X requirements with PDF links

// Test 3: Leichhardt
POST /api/compliance/dcp-complete
{
  "address": "30 Hubert Street, Leichhardt NSW 2040",
  "zone": "R1",
  "developmentType": "dwelling_house"
}
// Expected: Returns Parts A-F requirements with PDF links
```

---

## Total Time Estimate

- Phase 0 (Leichhardt PDF): 30-45 minutes
- Phase 1 (Ashfield): 15-20 minutes
- Phase 2 (Marrickville): 35-45 minutes
- Phase 3 (Leichhardt): 60-75 minutes
- Verification: 15-20 minutes

**Total: 2.5-3.5 hours**

---

## Files to Create

1. **Phase 0:**
   - `populate_leichhardt_pdf_metadata.py` (NEW)

2. **Phase 1:**
   - `reextract_ashfield_chapter_f_complete.py` (adapt from ASHFIELD_REEXTRACTION_SPEC.json)

3. **Phase 2:**
   - `reextract_marrickville_sections_1_2x.py` (adapt from extract_marrickville_general_COMPLIANT.py)

4. **Phase 3:**
   - `reextract_leichhardt_parts_abcdef.py` (adapt from extract_leichhardt_COMPLIANT.py)

5. **Verification:**
   - `verify_complete_reextraction.py`

---

## Success Criteria

1. ✅ All 2,638 old NULL-metadata requirements deleted
2. ✅ 930-1,450 new properly-tagged requirements created
3. ✅ **100% have development_types populated** (Ashfield: specific, Marrickville/Leichhardt: ['ALL'])
4. ✅ **100% have PDF metadata** (pdf_page, pdf_page_image_url)
5. ✅ 0% have zones (intentionally NULL per professional practice)
6. ✅ API returns results for all 3 test addresses
7. ✅ Users can click "View PDF" button for all requirements

---

## Next Step

**User approval required to proceed with Phase 0:**

Create `populate_leichhardt_pdf_metadata.py` script that:
1. Reads provisions from regulatory_provisions for Parts A-F
2. Finds corresponding PDF files in output/
3. Populates pdf_page and pdf_source_file
4. Verifies 100% updated

Should I proceed?
