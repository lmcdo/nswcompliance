# HABERFIELD - The Correct Structure

## You Were Right!

Haberfield residential IS important and was missing. It's in **Chapter E2**, NOT Chapter D!

## The Complete Picture

### Chapter D - Precinct Guidelines (Commercial/Mixed Use)

| Precinct | What It Actually Covers | Suburb |
|----------|------------------------|---------|
| D1 | Ashfield Town Centre | Ashfield |
| D2 | **Ashfield East** (Liverpool Rd gateway, NOT Haberfield proper) | Ashfield |
| D3 | **Ashfield West** (Liverpool Rd + Thomas St commercial strip) | Ashfield |
| D4 | Croydon Urban Village | Croydon |
| D5 | Neighbourhood Centre B1 zones | Multiple |
| D6 | **Parramatta Road Enterprise Corridor** (runs ALONG Haberfield, not IN it) | Mixed |
| D7 | Hurlstone Park Enterprise Zone | Hurlstone Park |
| D8 | Summer Hill Urban Village | Summer Hill |

### Chapter E2 - Haberfield Neighbourhood (THE REAL HABERFIELD!)

**Location:** `./output/Chapter E2 Haberfield Neighbourhood/`

**What it covers:**
- Haberfield Heritage Conservation Area (C54)
- Australia's first Garden Suburb (designed by Richard Stanton, 1901)
- Single-storey Federation houses on garden lots
- Strict heritage controls for:
  - Building setbacks (uniform ~6m)
  - Extensions (rear only, not visible from street)
  - Materials (brick, stone, slate/tile roofs)
  - Site coverage patterns
  - Landscape character

**Key Requirements:**
- Maintain single-storey appearance
- Extensions only to rear, not wider than existing dwelling
- No filling in side setbacks
- Preserve garden suburb character
- Front setback consistency

**Boundary:** See Figure 1 in Chapter E2 (has a map!)

## Address Lookup Logic - CORRECTED

### Example 1: "25 Ramsay Street, Haberfield"

**Location:** Heart of residential Haberfield
**Applies:** Chapter E2 - Haberfield Neighbourhood ✓
**Does NOT apply:** Chapter D provisions ✗

### Example 2: "123 Parramatta Road, Haberfield"

**Location:** Commercial strip along Haberfield edge
**Applies:** Chapter D Part 6 - Enterprise Zone ✓
**Does NOT apply:** Chapter E2 (outside Heritage Conservation Area) ✗

### Example 3: "45 Liverpool Road, Ashfield"

**Location:** Could be D2 (Ashfield East) OR D3 (Ashfield West)
**Applies:** Chapter D Part 2 or Part 3 (depends on exact coordinates) ✓
**Does NOT apply:** Chapter E2 ✗

## What Needs to be Extracted & Imported

| Chapter | Status | Precincts | Priority |
|---------|--------|-----------|----------|
| **Chapter D** | 7/8 extracted (D3 missing heading) | D1, D2, D4-D8 | HIGH |
| **Chapter E2** | Not yet extracted | Haberfield Neighbourhood (1 precinct) | **CRITICAL** |

## Revised Suburb Coverage

| Suburb You Wanted | What Covers It | Extraction Status |
|-------------------|----------------|-------------------|
| Ashfield | Chapter D: D1 (Town Centre) + D3 (West) | D1: ✓ / D3: Partial |
| **Haberfield residential** | **Chapter E2: Haberfield Neighbourhood** | **NOT YET EXTRACTED** |
| Haberfield commercial | Chapter D: D6 (Parramatta Road) | ✓ |
| Croydon | Chapter D: D4 (Urban Village) | ✓ |
| Summer Hill | Chapter D: D8 (Urban Village) | ✓ |
| Hurlstone Park | Chapter D: D7 (Enterprise) | ✓ |

## Next Steps - REVISED

1. **Extract Chapter E2 (Haberfield)** - Same process as Chapter D
2. **Fix Chapter D Part 3** - Extract Ashfield West manually
3. **Import both** into `dcp_precinct_provisions`:
   - Chapter D: 7-8 precincts (D1-D8)
   - Chapter E2: 1 precinct (Haberfield Neighbourhood)
4. **LLM categorization** on all provisions
5. **Georeference boundaries:**
   - Chapter D: 6-7 boundary maps
   - Chapter E2: Figure 1 (Haberfield map)
6. **Test** with addresses from all 5 suburbs

## The Image You Need for Haberfield

Chapter E2 contains:
- **Figure 1:** "Map of Haberfield Neighbourhood"
- Image: `edc040d35f5ed74a46f45b787053d882acada90b8fe635d1d24cb4df05714635.jpg`
- Location: `./output/Chapter E2 Haberfield Neighbourhood/auto/images/`

This is the boundary map you need to georeference for **actual residential Haberfield**!

## Bottom Line

You were 100% correct - Haberfield residential was missing. It's a separate chapter (E2) focused entirely on the Heritage Conservation Area. We need to extract and import this separately from Chapter D.

**Ready to extract Chapter E2?**
