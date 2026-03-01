# Ashfield Precinct to Suburb Mapping

## Critical Understanding: Precincts ≠ Suburbs

**IMPORTANT:** The provisions are organized by **precinct boundaries**, NOT by suburb names!

- A single suburb (e.g., Haberfield) can contain MULTIPLE precincts
- An address lookup uses **spatial intersection** with precinct boundaries
- The suburb name alone does NOT determine which provisions apply

## Extracted Precincts vs Suburbs

| Precinct ID | Precinct Name | Maps to Suburb(s) | Provisions | Has Boundary Map |
|-------------|---------------|-------------------|------------|------------------|
| **D1** | Ashfield Town Centre | Ashfield (town centre area) | 11 | YES (Page 3) |
| **D2** | Ashfield East | **Haberfield (residential)** | 17 | YES (Page 40) |
| **D3** | Ashfield West | Ashfield (western area) | **MISSING** | NO |
| **D4** | Croydon Urban Village | Croydon | 5 | YES (Page 83) |
| **D5** | Neighbourhood Centre (B1) | Multiple suburbs (B1 zones) | 5 | NO |
| **D6** | Enterprise Zone - Parramatta Rd | **Haberfield (commercial strip)** | 18 | Unknown |
| **D7** | Enterprise Zone - Hurlstone Park | Hurlstone Park | 6 | Unknown |
| **D8** | Summer Hill Urban Village | Summer Hill | 6 | YES (Page 169) |

## How Address Lookup Works

### Example: "45 Ramsay Street, Haberfield"

1. **Geocode address** → Get coordinates (lat/lon)
2. **Spatial query** → Check which precinct boundary contains these coordinates
3. **Possible results:**
   - If in residential area → **D2 (Ashfield East)** provisions apply
   - If on Parramatta Road → **D6 (Enterprise Zone)** provisions apply
4. **Return** → Provisions for that specific precinct

### This Means:

- **Suburb = "Haberfield"** could return **D2 OR D6** provisions (different rules!)
- We CANNOT just match on suburb name
- **MUST georeference the boundary maps** for this to work

## Alignment with Your 5 Suburbs

From your original question about "5 Ashfield suburbs":

| Your Expected Suburb | Precinct Coverage | Status |
|---------------------|-------------------|--------|
| **Ashfield** | D1 (Town Centre) + D3 (West) | D1: READY / D3: MISSING |
| **Haberfield** | D2 (Residential) + D6 (Commercial) | BOTH READY |
| **Croydon** | D4 (Urban Village) | READY |
| **Summer Hill** | D8 (Urban Village) | READY |
| **Hurlstone Park** | D7 (Enterprise Zone) | READY |

### Coverage Analysis:

- **4 out of 5 suburbs:** FULLY COVERED
- **Ashfield suburb:** PARTIAL (missing D3 - Ashfield West from extraction)
- **Total:** 7 out of 8 precincts extracted

## What Happens When User Enters Address

### Current Marrickville/Leichhardt Pattern:

```sql
-- User enters: "123 Smith St, Marrickville"
-- System does:
SELECT provisions
FROM dcp_precinct_provisions p
JOIN dcp_precinct_boundaries b ON p.precinct_id = b.precinct_id
WHERE ST_Contains(b.geometry, ST_Point(lon, lat))
```

### Ashfield Will Work the Same:

```sql
-- User enters: "45 Ramsay St, Haberfield"
-- System does:
SELECT provisions
FROM dcp_precinct_provisions p
JOIN dcp_precinct_boundaries b ON p.precinct_id = b.precinct_id
WHERE ST_Contains(b.geometry, ST_Point(151.1234, -33.8765))
  AND p.precinct_id LIKE 'D%'  -- Ashfield precincts
```

**Result:** Returns D2 (Ashfield East) provisions for residential Haberfield address

## Action Items for You

1. **Georeference these boundary maps** (you will do in QGIS):
   - D1: Ashfield Town Centre (page 3 area)
   - D2: Ashfield East / Haberfield residential (page 40 area)
   - D4: Croydon Urban Village (page 83 area)
   - D8: Summer Hill Urban Village (page 169 area)

2. **For D5, D6, D7** (no clear boundary maps):
   - Option A: Create from zone maps in LEP
   - Option B: Use approximate boundaries from suburb + zoning data
   - Option C: Mark as "requires manual georeferencing"

3. **D3 (Ashfield West)** - MISSING:
   - Check if original PDF has this section
   - May need manual extraction or skip if not in source

## Bottom Line

**YES, the provisions will align with your 5 suburbs**, but:
- ✓ Structure is correct (precinct_id like D1, D2, etc.)
- ✓ Content is extracted (68 provisions)
- ✓ 7 out of 8 precincts ready
- ⚠ **CRITICAL DEPENDENCY:** You must georeference the boundaries correctly
- ⚠ Without boundaries, address lookup will NOT work (no spatial match)

**The provisions are ready. The georeferencing is on you!**
