# Housing Code Page Ranges - Codes SEPP 2008

**Source:** `sepp_page_mappings.json` (extracted from Codes SEPP PDF)
**Total pages:** 454

## Discovered Structure

Based on clause numbering found in extracted text:

### Schedule 1 Housing Code: **Pages ~100-400**

**Part 1: Land to which code applies and excluded development**
- **Estimated pages: 100-119**
- Clause numbering: 1.1-1.9
- Contains: Exclusions, "not permitted" development

**Part 2: Development standards**
- **Pages: 120-200** (confirmed)
- Clause numbering: 3.10, 3.13, 3.16, 3.20, etc.
- Page 120: Minimum setbacks, boundary walls
- Page 125: Setback tables by lot size
- Page 130: Minimum landscaped area
- Page 135: Car parking requirements
- Page 138: Battle-axe lot calculations
- Page 150: Principal private open space, lot widths

**Part 3: Design criteria**
- **Pages: 200-350** (estimated)
- Page 200: Building elements, articulation zones
- Page 250: Ground level definitions
- Page 300: Dwelling house requirements
- Page 350: Dormer windows

**Part 4: Assessment criteria**
- **Pages: 350-400** (estimated)
- Page 400: Building heights

## What This Means for 217/199/9 Claims

### Exclusions (claimed 217)
- **Location:** Pages ~100-119 (Part 1, clauses 1.1-1.9)
- **Estimated count:** 15-30 exclusion clauses (NOT 217)
- **To verify:** Need to OCR/read pages 100-119 to count actual exclusions

### Numeric Standards (claimed 199)
- **Location:** Pages 120-200 (Part 2, clauses 3.x)
- **Estimated count:** 30-50 numeric standards (NOT 199)
- **To verify:** Count all metric requirements in Part 2 (setbacks, lot sizes, landscaping, parking, etc.)

### Override Rules (claimed 9)
- **Location:** Unknown - not a standard Housing Code Part
- **Possible location:** Scattered throughout as "Despite..." or "Notwithstanding..." clauses
- **To verify:** Search entire document for override/superseding language

## Next Steps

1. **Extract Part 1 text** (pages 100-119)
   - Use OCR or read PDF pages directly
   - Count exclusion clauses (1.1, 1.2, 1.3...)
   - Document exclusion types

2. **Extract Part 2 text** (pages 120-200)
   - Count all numeric standards
   - Categorize by metric type (setback, landscaping, parking, etc.)

3. **Search for overrides**
   - Grep for "despite", "notwithstanding", "supersedes", "prevails over"
   - Count actual override provisions

4. **Update database**
   - Populate `sepp_structured_requirements` with actual data
   - Replace hardcoded 217/199/9 with real counts
