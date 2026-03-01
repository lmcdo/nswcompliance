# Housing Code Section Mapping Plan

**Objective:** Locate and verify the 217/199/9 Pattern Book statistics in SEPP (Exempt and Complying Development Codes) 2008 Schedule 1 (Housing Code)

## Current Status

- ✅ Have 454 Codes SEPP PDF pages extracted locally (`pdf-pages/sepp-exempt-complying/page_*.png`)
- ✅ Fixed filename bug in pdf-url-builder.ts (hyphen → underscore)
- ✅ Identified Pattern Book PDFs are design guides only, NOT eligibility criteria
- ❌ Need to locate Housing Code sections within the 454 pages

## Housing Code Structure (Expected)

SEPP (Exempt and Complying Development Codes) 2008 Schedule 1 contains:

### Part 1: Land to which code applies and excluded development
**This is where "217 exclusion triggers" would be**
- Clause 1.8: Land to which code applies
- Clause 1.9: Development that is not permitted
- Clause 1.10-1.19: Specific exclusions (development types, zones, overlays, etc.)

Expected count: ~15-30 exclusion clauses (NOT 217)

### Part 2: Development standards
**This is where "199 numeric standards" would be**
- Lot size requirements (Type A/B/C/D)
- Setback requirements
- Height limits
- Floor space ratio
- Landscaped area
- Parking requirements
- Access requirements

Expected count: ~30-50 numeric standards (NOT 199)

### Part 3: Design criteria
- Building design
- Visual amenity
- Solar access
- Ventilation
- Storage
- Common area

Expected count: ~20-30 design criteria

### Part 4: Assessment criteria
- Site suitability
- Context and setting
- Built form and scale

Expected count: ~10-15 assessment criteria

## The 217/199/9 Mystery

The claimed numbers (217 exclusions, 199 numeric standards, 9 override rules) **do NOT match typical Housing Code structure**.

Possible explanations:
1. **Marketing numbers** - not actual legislative provision counts
2. **Counting sub-clauses** - e.g., Clause 1.9 might have 217 individual dot points across all sub-clauses
3. **Wrong source** - numbers from a different document/process
4. **Fabricated** - placeholder numbers without legislative basis

## Next Steps

### Task #47: Locate Schedule 1 Start Page
1. Check pages 20-50 for "Schedule 1" or "Housing Code" headers
2. Document the exact page number where Schedule 1 begins

### Task #48: Map Part page ranges
Once Schedule 1 is found:
1. Find Part 1 start page (exclusions)
2. Find Part 2 start page (development standards)
3. Find Part 3 start page (design criteria)
4. Find Part 4 start page (assessment criteria)
5. Document end pages for each Part

### Task #37-39: Count actual provisions
For each Part:
1. Count clauses (e.g., 1.8, 1.9, 1.10, ...)
2. Count sub-clauses if needed (e.g., 1.9(1)(a), 1.9(1)(b), ...)
3. Document actual counts vs claimed 217/199/9

## Verification Method

**Option 1: Manual page inspection**
- Open `pdf-pages/sepp-exempt-complying/page_X.png` files
- Find section headers visually
- Count provisions by reading pages

**Option 2: OCR text extraction**
- Use `tesseract` to extract text from relevant pages
- Parse clause numbers programmatically
- Generate accurate counts

**Option 3: HTML scraping** (if Cloudflare can be bypassed)
- Access https://legislation.nsw.gov.au/view/html/inforce/current/epi-2008-0572
- Parse HTML to extract Schedule 1 structure
- Count provisions from structured HTML

## Recommended Approach

Start with Option 1 (manual) to get a quick sense of structure, then use Option 2 (OCR) for accurate counting.

Estimated time: 2-3 hours to complete full mapping and verification.
