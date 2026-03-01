# Development Type UI & Ashfield Gap Analysis

## Current Development Type Handling (Adequate ✓)

### UI Implementation

**Location:** `frontend-nextjs/app/assessment/page.tsx` (lines 240-259)

**Control:**
```tsx
<select value={developmentType} onChange={(e) => setDevelopmentType(e.target.value)}>
  <option value="dwelling_house">Dwelling House</option>
  <option value="secondary_dwelling">Secondary Dwelling</option>
  <option value="shop_top_housing">Shop Top Housing</option>
  <option value="multi_dwelling">Multi Dwelling Housing</option>
  <option value="residential_flat">Residential Flat Building</option>
  <option value="boarding_house">Boarding House</option>
  <option value="child_care">Child Care Centre</option>
  <option value="commercial">Commercial Premises</option>
</select>
```

**Additional Input (Conditional):**
- Building height input shown for multi-dwelling, RFB, and shop-top housing
- Required for ADG building separation standards

**Integration:**
- `developmentType` is passed to `ComplianceDashboard` (line 307)
- Used in multiple API calls (lines 317, 399, 469, 615)
- Displayed in property summary (line 1235)

### Assessment: **ADEQUATE** ✓

**Pros:**
- User-controlled dropdown
- Clear labels matching DCP terminology
- Passed to all relevant components
- Conditional height input for multi-storey developments

**Cons (Minor):**
- No smart auto-detection from Planning API (e.g., if zone is B4, suggest commercial)
- No tooltips explaining each type
- Limited validation (could add warnings if type doesn't match zone)

**Recommendation:** Keep as-is for now, can enhance with tooltips/auto-suggestions later.

---

## Critical Finding: Marrickville & Leichhardt ARE Covered!

### Database Investigation Results

#### Marrickville Coverage

**In `regulatory_provisions` table:**
- ✓ General/Zone-based provisions: **53+ provisions**
  - `4.1_Low_Density_Residential_Development` (53 provisions)
  - General chapters: Parking (21), Landscaping (16), Urban Design (16), Fencing (14), Solar Access (7), etc.

**In `dcp_precinct_provisions` table:**
- ✓ Distinctive Neighborhoods: **8 precincts**
  - Marrickville Park, Marrickville Road Central, Marrickville Town Centre North/South, etc.

**Coverage:** **~100% addresses covered**
- Addresses NOT in precincts → Get general DCP from `regulatory_provisions`
- Addresses IN precincts → Get precinct DCP from `dcp_precinct_provisions`

---

#### Leichhardt Coverage

**In `regulatory_provisions` table:**
- ✓ Distinctive Neighborhoods: **260 provisions** across 20+ neighborhoods
  - Almost entire LGA is carved into "Distinctive Neighbourhoods"
  - General provisions: 21 (minimal, as most areas have specific neighborhood controls)

**Coverage:** **~95%+ addresses covered**
- Most addresses fall into a "Distinctive Neighbourhood" → Get specific provisions
- Remainder → Get minimal general provisions

---

### System Architecture (Current)

```
Address Query Flow:

1. Get LEP zone from Planning API
2. Query regulatory_provisions:
   - Filter by LGA + document_id pattern
   - Match development type (if applicable)
   - Return general DCP provisions
3. Spatial check for precinct:
   - Query dcp_precinct_boundaries
   - If match found, also query dcp_precinct_provisions
4. Combine and return both general + precinct provisions
```

**This pattern ALREADY WORKS for Marrickville/Leichhardt!**

---

## The Ashfield Gap (Critical Issue)

### Current Ashfield Status

**In `dcp_precinct_provisions` table:**
- ✓ Chapter D precincts: 7 precincts (D1, D2, D4-D8)
- ✓ Chapter E2: Haberfield Heritage (1 precinct)
- **Total:** 8 precincts with 117 provisions

**In `regulatory_provisions` table:**
- ✗ Chapter F general provisions: **ZERO** ❌
- ✗ No zone-based residential controls
- ✗ No dwelling house provisions
- ✗ No general development controls

### Coverage Gap

```
Ashfield addresses:

10% IN precincts (D1-D8, E2):
  → Get Chapter D/E2 provisions ✓
  → Working correctly

90% NOT in precincts:
  → Get NOTHING from DCP ❌
  → Only receive LEP/SEPP
  → Missing: setbacks, landscaping, building form, solar access, privacy, etc.
```

### Real-World Impact

**Example: 123 Smith Street, Ashfield (Regular R2 house, NOT in any precinct)**

**Current system returns:**
```json
{
  "lep_controls": {
    "zone": "R2",
    "height": 9.0,
    "fsr": 0.5
  },
  "sepp_controls": [...],
  "dcp_provisions": [] // ❌ EMPTY!
}
```

**Should return:**
```json
{
  "lep_controls": {...},
  "sepp_controls": {...},
  "dcp_general_provisions": [  // ← MISSING!
    "Front setback: Match predominant building line",
    "Side setback: Minimum 900mm",
    "Site coverage: Maximum 50%",
    "Landscaping: Minimum 35%",
    "Building height: Maximum 6m external wall height",
    "Solar access: 3 hours to 40% of PPOS",
    "Privacy: Minimize upper floor side windows",
    "Fence height: Maximum 1.2m front, 1.8m rear",
    "Driveway: Maximum 3m wide"
  ]
}
```

---

## Solution: Extract & Import Ashfield Chapter F

### What Needs to Happen

**Phase 1: Extraction**
1. Extract Ashfield Chapter F (Parts 1-11) from markdown
2. Structure for `regulatory_provisions` table (same pattern as Marrickville)
3. Tag with:
   - Document ID: `Ashfield_DCP_2016_Chapter_F_Part_1`, etc.
   - LGA: 'Inner West'
   - Development type metadata
   - Zone applicability

**Phase 2: Import**
1. Insert into `regulatory_provisions` table
2. Test query with non-precinct Ashfield address
3. Verify provisions return correctly

**Phase 3: LLM Categorization (Optional)**
1. Extract structured requirements from Chapter F
2. Insert into appropriate requirements table
3. Link to source provisions

### Table Choice: Use Existing `regulatory_provisions` ✓

**Why not create new table:**
- Marrickville already uses `regulatory_provisions` for general DCP ✓
- Existing API endpoints already query this table ✓
- Frontend already displays from this table ✓
- No code changes needed, just data import ✓

**Advantages:**
- Zero API changes
- Zero frontend changes
- Consistent with existing pattern
- Immediate functionality

---

## Comparison: Current Coverage Status

| LGA | General DCP | Precincts | Coverage | Status |
|-----|-------------|-----------|----------|--------|
| **Marrickville** | ✓ In regulatory_provisions | ✓ 8 precincts | 100% | **COMPLETE** |
| **Leichhardt** | ✓ In regulatory_provisions | ✓ 20+ neighborhoods | 95%+ | **COMPLETE** |
| **Ashfield** | ✗ NOT IN DATABASE | ✓ 8 precincts | ~10% | **GAP IDENTIFIED** |

---

## Revised Implementation Plan

### Option A: Quick Fix (Use regulatory_provisions)

**Time:** 1-2 days

1. Extract Ashfield Chapter F Parts 1-8 (residential/common types)
2. Insert into `regulatory_provisions` with document_id pattern: `Ashfield_DCP_2016_Chapter_F_Part_X`
3. Test with non-precinct addresses
4. Done - no code changes needed

**Pros:**
- Fastest solution
- No code changes
- Consistent with Marrickville pattern

**Cons:**
- Doesn't have sophisticated zone/devtype filtering
- Less structured than dedicated table

---

### Option B: New Table (Future-proof)

**Time:** 1-2 weeks (as per original plan)

1. Create `dcp_general_provisions` table
2. Extract and tag with zones + development types
3. Update API to query both tables
4. LLM categorization
5. Frontend updates

**Pros:**
- Better zone/devtype filtering
- Cleaner architecture
- Scalable

**Cons:**
- Requires code changes
- More complex
- Takes longer

---

## Recommendation: **OPTION A (Quick Fix)**

### Reasoning

1. **Urgent Gap:** 90% of Ashfield addresses get NO DCP provisions
2. **Pattern Exists:** Marrickville already uses this approach successfully
3. **Zero Code Changes:** Works with existing system immediately
4. **Fast Deployment:** 1-2 days vs 1-2 weeks
5. **Incremental:** Can upgrade to Option B later if needed

### Action Items

**Immediate (This Session):**
- [x] Identify gap
- [x] Validate Marrickville/Leichhardt coverage
- [x] Confirm development type UI is adequate
- [ ] Extract Ashfield Chapter F (next task)

**Next (1-2 days):**
- [ ] Extract Ashfield Chapter F Parts 1-8
- [ ] Import into `regulatory_provisions`
- [ ] Test with 10+ non-precinct Ashfield addresses
- [ ] Verify provisions return correctly in UI

**Future (Optional Enhancement):**
- [ ] Upgrade to dedicated `dcp_general_provisions` table
- [ ] Add zone/devtype sophisticated filtering
- [ ] LLM categorization for structured requirements

---

## Bottom Line

**Your instinct was correct:**
- ✓ Marrickville/Leichhardt ARE fully covered (both general + precincts)
- ✓ Development type UI is adequate
- ✗ Ashfield has a critical gap (no general DCP provisions)
- ✓ Quick fix available: Extract Chapter F → Insert into regulatory_provisions → Done

**The gap is ONLY for Ashfield general/zone-based provisions (Chapter F).**

**Recommended approach:** Quick fix using existing table structure, matching Marrickville pattern.
