# Marrickville DCP Extraction - Requirements Specification

## Purpose

Fix the page grouping bug where 180 Addison Road shows all landscaping requirements incorrectly grouped to one PDF page, when they actually span multiple pages.

## Original Issue

**Bug:** Requirements from multi-page sections all assigned to same `pdf_page`
- Example: Section 2.18 Landscaping spans pages 6-10
- Current behavior: All 22 requirements show `pdf_page = 10`
- Expected: Requirements distributed across correct pages (6, 7, 8, 9, 10)

**Root Cause:** LLM extracted entire multi-page sections at once, assigned all requirements to first provision's page number

**User Impact:** When viewing 180 Addison Road, clicking a requirement shows wrong PDF page image

## Solution Approach

Extract requirements **page-by-page** instead of section-by-section, so each requirement inherits correct `pdf_page` from its source provision.

## Data Architecture

### Source Data (Already Complete)
- `regulatory_provisions` table: 1,303 Marrickville pages
  - 851 general pages (Parts 1-8, 10)
  - 452 precinct pages (Part 9.X)
- Each provision has:
  - `page_number` (text)
  - `pdf_page_image_url` (path to PNG)
  - `provision_text` (plain text, no LaTeX)

### Target Tables

**dcp_general_requirements** (for Parts 1-8, 10):
- Apply to ALL properties in former Marrickville area
- Used for baseline compliance checks

**dcp_precinct_requirements** (for Part 9.X):
- Apply ONLY to properties within specific geographic boundaries
- Require spatial matching (point-in-polygon)

## Required Fields (Based on API/UI Analysis)

### Critical Fields (Must Have)
1. **pdf_page** (integer) - Page number for UI linking
2. **pdf_page_image_url** (text) - Path to page image
3. **category** (text) - For UI grouping/display
4. **requirement_text** (text) - Display text
5. **verbatim_source_text** (text) - For PDF matching
6. **primary_source_provision_id** (integer) - Link to source

### Important Fields (Should Have)
7. **subcategory** (text) - Finer categorization
8. **confidence** (text) - LLM confidence score
9. **has_conditionals** (boolean) - Has exceptions/conditions
10. **value_numeric** (numeric) - Extracted numeric values
11. **unit** (text) - Units of measurement

### Optional Fields (Nice to Have)
12. **value_min/value_max** - For ranges
13. **conditional_text** - Exception clauses
14. **extraction_context** (jsonb) - Additional metadata

## Category Requirements

### Question: Must categories match Ashfield/Leichhardt exactly?

**Analysis:**
- UI component `CategorizedRequirementsCard.tsx` groups by category
- API returns `category` field
- UI displays categories as collapsible sections

**Conclusion:** YES - Categories should be consistent for:
1. **User experience** - Same category names across all councils
2. **UI functionality** - Category grouping/filtering works consistently
3. **Data consistency** - Professional product quality

### Existing Category Schema (56 categories)

**Most Used Categories (from Ashfield/Leichhardt):**
- `other`, `heritage`, `character`, `parking`
- `waste_management`, `sustainability`, `contamination`
- `water_management`, `landscaping`, `tree_preservation`
- `da_requirements`, `signage`, `drainage`
- `building_form`, `safety`, `stormwater`, `accessibility`
- `building_height`, `setback_front/side/rear`
- `environmental`, `streetscape`, `privacy`, `energy_efficiency`
- `solar_access`, `fencing`, `subdivision`, etc.

**Decision:** Use existing category schema for consistency

## Extraction Approach

### Method: Page-by-Page LLM Extraction

**Input:** ONE provision (page) at a time from regulatory_provisions
**Process:** LLM extracts requirements from that page only
**Output:** Requirements with correct pdf_page inherited from provision

**Why This Fixes The Bug:**
- OLD: Process pages 6-10 together → all get page 10
- NEW: Process page 6 alone → requirements get page 6, page 7 → page 7, etc.

### LLM Model

Use **GPT-4o-mini** (OpenAI):
- ✅ API key available and working
- ✅ Successfully used for Ashfield/Leichhardt/Marrickville V2
- ✅ Cost-effective for 1,303 pages
- ❌ Claude API key expired/invalid

### Prompt Requirements

**Must Include:**
1. Full list of 56 categories (match existing schema)
2. Examples of category mapping
3. Clear instructions: "Extract from THIS PAGE only"
4. JSON schema with all required fields
5. Plain verbatim text requirement (no LaTeX)

## Success Criteria

### Functional Requirements
1. ✅ Each requirement has correct `pdf_page` matching actual PDF page
2. ✅ `pdf_page_image_url` links work in UI
3. ✅ General vs precinct correctly routed to separate tables
4. ✅ Categories match existing Ashfield/Leichhardt schema
5. ✅ No LaTeX formatting in `verbatim_source_text`

### Data Quality Requirements
1. ✅ Success rate >80% (pages successfully processed)
2. ✅ Total requirements ~1,800-2,400 (based on page count)
3. ✅ Category distribution similar to Ashfield/Leichhardt
4. ✅ Each provision (page) produces 0-10 requirements (reasonable range)

### User Experience Requirements
1. ✅ 180 Addison Road shows requirements grouped by actual pages
2. ✅ Clicking requirement displays correct PDF page image
3. ✅ Categories display consistently across all councils
4. ✅ General + precinct requirements both appear for applicable properties

## Implementation Plan

### Phase 1: Preparation (COMPLETE)
- ✅ Extract 1,303 PDF pages to regulatory_provisions
- ✅ Generate 1,150 page images (PNG files)
- ✅ Populate pdf_page_image_url metadata

### Phase 2: LLM Extraction (IN PROGRESS)
1. Create extraction prompt with:
   - All 56 categories
   - Category mapping examples
   - Complete JSON schema
2. Route to correct tables based on document type:
   - Part 9.X → dcp_precinct_requirements
   - Parts 1-8, 10 → dcp_general_requirements
3. Process 1,303 provisions page-by-page
4. Validate and commit every 10 pages

### Phase 3: Verification
1. Check counts and success rate
2. Test 180 Addison Road page grouping
3. Verify category consistency
4. Test UI integration

## Out of Scope

❌ **NOT** changing existing Ashfield/Leichhardt data
❌ **NOT** modifying category schema (use as-is)
❌ **NOT** re-extracting PDF pages (already complete)
❌ **NOT** creating new tables or fields
❌ **NOT** changing API or UI code

## Next Steps

1. **READ** this spec document fully
2. **VERIFY** all requirements understood
3. **CREATE** comprehensive extraction prompt with all 56 categories
4. **TEST** with 10 pages first
5. **RUN** full extraction only after test succeeds
6. **VERIFY** results meet success criteria

## Questions to Resolve

None - all requirements are clear based on:
- ✅ Original bug report (page grouping)
- ✅ API code analysis (fields used)
- ✅ UI code analysis (category grouping)
- ✅ Existing data analysis (category schema)
- ✅ Architecture analysis (general vs precinct tables)
