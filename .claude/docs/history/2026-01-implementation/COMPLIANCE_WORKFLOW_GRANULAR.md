# NSW Planning Compliance Engine - Granular DCP Workflow

## Complete 4-Layer DCP Filtering Per Address

### Example: 168 Norton Street, Leichhardt NSW 2040

---

## DCP Tab: 4-Layer Provision Filtering

### Input Parameters:
```
former_council: "Leichhardt" (from suburb detection)
zone: "R2"
heritage: true
hca: "norton_street" (C48 → db_slug lookup)
precinct_id: "Part_5_1" (Norton Street Precinct)
```

### Layer 1: Generic (Always Apply) - 45 provisions
**Filter**: `v2_dcp_layer = 'generic'` AND `document_id LIKE '%Leichhardt%'`

**Always included** regardless of property characteristics:
- Part 2.1 Site Analysis
- Part 2.2 Parking & Access (general requirements)
- Part 2.5 Tree Preservation
- Part 2.6 Stormwater Management
- Part 2.7 Waste Management
- Part 2.8 Excavation & Landfill
- Part 2.9 Site Facilities

### Layer 2: Use-Specific (Zone R2) - 38 provisions
**Filter**: `v2_dcp_layer = 'use_specific'` AND `'R2' = ANY(v2_applicable_zones)`

**Matched** because zone=R2:
- Part 3.2 Dwelling Houses (zones: R1, R2)
- Part 3.3 Dual Occupancies (zones: R1, R2, R3)
- Part 3.4 Secondary Dwellings (zones: All residential)
- Part 3.5 Multi-Dwelling Housing (zones: R2, R3, R4)

**NOT matched** (wrong zone):
- Part 3.6 Residential Flat Buildings (zones: R3, R4, B zones only)
- Part 4.1 Commercial & Retail (zones: B, MU zones only)

### Layer 3: Heritage (Norton Street HCA) - 67 provisions
**Filter**: `v2_dcp_layer = 'condition'` AND `(v2_heritage_hca IS NULL OR v2_heritage_hca = 'norton_street')`

**Two types of provisions**:
1. **General heritage** (v2_heritage_hca = NULL): Apply to ALL heritage properties
2. **HCA-specific** (v2_heritage_hca = 'norton_street'): Only this HCA

**Part 6.2 Norton Street HCA provisions**:
- 6.2.1 Character Statement
- 6.2.2 Building Materials (face brick/render only)
- 6.2.3 Roof Design (30-35° pitch, terracotta tiles)
- 6.2.4 Window Proportions
- 6.2.5 Front Fences (1.2m max, open paling)
- 6.2.6 Garages (behind building line)
- 6.2.7 Landscaping
... (60 more HCA-specific controls)

### Layer 4: Precinct (Norton Street) - 22 provisions
**Filter**: `v2_dcp_layer = 'precinct'` AND `v2_precinct_id = 'Part_5_1'`

**Only matched** if property is in Norton Street Precinct:
- Part 5.1.1 Character Statement
- Part 5.1.2 Active Frontages (ground floor commercial required)
- Part 5.1.3 Continuous Awnings
- Part 5.1.4 Outdoor Dining Setbacks
- Part 5.1.5 Signage Design
- Part 5.1.6 Materials Palette
... (16 more precinct controls)

---

## Counter-Example: Different Address Produces Different Results

### Property: 25 Ramsay Street, Haberfield NSW 2042

### Input Parameters Change:
```
former_council: "Ashfield" (Haberfield suburb)
zone: "R2" (same)
heritage: true
hca: "haberfield" (C54 → db_slug lookup)
precinct_id: null (NOT in a special precinct)
```

### Layer Changes:

**Layer 1**: Same 45 generic provisions (but from Ashfield DCP, not Leichhardt DCP)

**Layer 2**: Same 38 R2 provisions (but Ashfield-specific text)

**Layer 3**: DIFFERENT - 82 provisions
- Part 6.1 Haberfield HCA (instead of 6.2 Norton St)
- **More restrictive** controls (Haberfield is stricter than Norton St)
- California Bungalow character requirements
- Original fabric retention mandates
- Front setback must match neighbors exactly
- NO driveways permitted (vs Norton St allows with conditions)

**Layer 4**: ZERO provisions
- Not in a precinct
- No Part 5 provisions apply

**Total**: 165 provisions (vs 172 for Norton St)

---

## How Filtering Produces Accurate Per-Address Output

### Example Provision: "3.2.7 Driveway Design"

**In Database**:
```sql
v2_dcp_layer = 'use_specific'
v2_applicable_zones = ['R1', 'R2', 'R3']
v2_precinct_id = NULL
document_id = 'Leichhardt_DCP_2023_Part_3_Residential'
```

**For 168 Norton St (Leichhardt, R2, Norton St Precinct)**:
✓ Layer 2 matched (use_specific + R2 zone)
✓ Includes provision
⚠️ BUT Part 5.1 precinct controls MODIFY this provision
→ Shows base provision + precinct overlay note

**For 25 Ramsay St (Ashfield, R2, Haberfield HCA)**:
✓ Layer 2 matched (use_specific + R2 zone) 
✓ Includes provision from Ashfield DCP
⚠️ BUT Part 6.1 HCA controls PROHIBIT driveways entirely
→ Shows provision with HCA override warning

---

## TOC-Based Navigation Shows Context

### Left Sidebar Navigation:
```
Part 3: Residential Development
├─ 3.1 Residential Character
├─ 3.2 Dwelling Houses ◀ USER CLICKS HERE
│   ├─ 3.2.1 Building Height (Page 45)
│   ├─ 3.2.2 Floor Space Ratio (Page 46)
│   ├─ 3.2.3 Front Setbacks (Page 47)
│   ├─ 3.2.4 Side Setbacks (Page 48)
│   ├─ 3.2.5 Private Open Space (Page 49)
│   ├─ 3.2.6 Parking (Page 50)
│   └─ 3.2.7 Driveways (Page 51)
├─ 3.3 Dual Occupancies
└─ 3.4 Secondary Dwellings
```

### Right Panel: Page-Grouped Display
```
Part 3.2 Dwelling Houses
Showing all provisions from this section

━━━ Page 45-46: Building Envelope ━━━
[3.2.1 Building Height - provision card]
[3.2.2 FSR - provision card]

━━━ Page 47-48: Setbacks ━━━
[3.2.3 Front Setbacks - provision card]
[3.2.4 Side Setbacks - provision card]

━━━ Page 49: Open Space ━━━
[3.2.5 Private Open Space - provision card]

━━━ Page 50-51: Parking ━━━
[3.2.6 Parking - provision card]
[3.2.7 Driveways - provision card]
  ⚠️ Modified by Part 5.1 Norton St Precinct
  ⚠️ See also Part 6.2 HCA garage controls
```

---

## Key Insight: Granular = Accurate + Context-Aware

**What makes this granular**:
1. **4-layer filtering** eliminates irrelevant provisions
2. **Address-specific** detection (precinct, HCA, zone)
3. **Cross-referencing** shows when provisions interact
4. **Page grouping** preserves document context
5. **Expandable cards** let users drill down to exact text

**What the user sees**:
- ~172 provisions instead of 940+ pages
- Every provision IS relevant to their property
- Clear hierarchy: Generic → Zone → Heritage → Precinct
- PDF page numbers for legal verification
- Interactive expansion for detailed controls

---

## Documentation Purpose

This workflow should be used for the "Learn More" page to explain:
1. How address input triggers multi-source data retrieval
2. How SEPP/LEP/DCP layers work together
3. How 4-layer DCP filtering produces accurate results
4. Why different addresses get different provisions
5. How to navigate and understand the compliance output

**Target audience**: 
- Town planners
- Architects
- Property developers
- Homeowners doing preliminary research
- Council staff reviewing applications
