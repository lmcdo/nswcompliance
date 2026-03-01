# Backend Processing Differences: Ashfield vs Marrickville vs Leichhardt

## Executive Summary

All 3 councils now use the **same dual-field extraction** (summary + verbatim text), but differ in:
1. **Data sources** (new table vs legacy table)
2. **Filtering approach** (zone+devtype vs devtype vs universal)
3. **DCP structure** (Chapter F vs Part 4.x vs Part C)
4. **Precinct handling** (Chapter D vs Part 9 vs Part C Section 2)

---

## Comparison Matrix

| Feature | Ashfield | Marrickville | Leichhardt |
|---------|----------|--------------|------------|
| **DCP Document** | Ashfield DCP 2016 | Marrickville DCP 2011 | Leichhardt DCP 2013 |
| **General Provisions** | Chapter F | Parts 2, 4.x, 7 | Parts A, B, C, D, E |
| **Precinct Provisions** | Chapter D (20 precincts) | Part 9 (neighborhoods) | Part C Section 2 (neighborhoods) |
| **Data Source** | `dcp_general_requirements` (NEW) | `regulatory_provisions` (LEGACY) + `dcp_general_requirements` (NEW) | `regulatory_provisions` (LEGACY) + `dcp_general_requirements` (NEW) |
| **Filtering Level** | Zone + Dev Type | Dev Type (partial) | Universal (minimal filtering) |
| **LGA Value in DB** | `INNER WEST` | `MARRICKVILLE` | `LEICHHARDT` |
| **Dual-Field Extraction** | ✅ Yes (54 requirements) | ✅ Yes (274 requirements) | ✅ Yes (27 requirements) |
| **Verbatim Coverage** | 100% | 100% | 100% |
| **Quality (Identical %)** | 0% (excellent) | 4% (very good) | 0% (excellent) |

---

## 1. Data Storage Architecture

### Ashfield (Newest - Fully Migrated)
```
dcp_general_requirements
├── 54 requirements
├── Former Council: 'Ashfield'
├── LGA: 'Inner West'
├── Zones: Filtered (e.g., R2, B1, etc.)
└── Development Types: Filtered (e.g., dwelling_house, multi_dwelling_housing)

Schema:
- requirement_text (summary)
- verbatim_source_text (exact PDF text)
- applicable_zones: ['R2', 'R3'] (POPULATED)
- development_types: ['dwelling_house', 'multi_dwelling_housing'] (POPULATED)
```

### Marrickville (Hybrid - Partially Migrated)
```
GENERAL PROVISIONS (new extraction):
dcp_general_requirements
├── 274 requirements
├── Former Council: 'Marrickville'
└── LGA: 'Inner West'

LEGACY PROVISIONS (still in use):
regulatory_provisions
├── Used for: Part 4.1 (setbacks), Part 7 (specific uses)
└── No zone/devtype filtering

Data Flow:
1. Check dcp_general_requirements (NEW)
2. If empty, fallback to regulatory_provisions (LEGACY)
3. Combine with precinct data from dcp_precinct_requirements
```

### Leichhardt (Hybrid - Partially Migrated)
```
GENERAL PROVISIONS (new extraction):
dcp_general_requirements
├── 27 requirements
├── Former Council: 'Leichhardt'
└── LGA: 'Inner West'

LEGACY PROVISIONS (still in use):
regulatory_provisions
├── Used for: Some Part A-E provisions
└── No zone/devtype filtering

Data Flow:
1. Check dcp_general_requirements (NEW)
2. If empty, fallback to regulatory_provisions (LEGACY)
3. Combine with precinct data from dcp_precinct_requirements
```

---

## 2. API Query Logic

### Ashfield - Primary Path (Zone + DevType Filtering)

```typescript
// Step 1: Query dcp_general_requirements
const query = `
  SELECT * FROM dcp_general_requirements
  WHERE lga = 'INNER WEST'
    AND 'R2' = ANY(applicable_zones)          // Zone filtering
    AND 'dwelling_house' = ANY(development_types)  // DevType filtering
    AND former_council = 'Ashfield'
`;

// Step 2: If successful, format and return
// Returns: Chapter F requirements filtered to zone + devtype
```

**Result**: Highly targeted - only shows requirements for your specific zone and development type.

---

### Marrickville - Fallback Path (Legacy + New Data)

```typescript
// Step 1: Try dcp_general_requirements
const mainQuery = `
  SELECT * FROM dcp_general_requirements
  WHERE lga = 'INNER WEST'
    AND former_council = 'Marrickville'
`;

// Step 2: If empty (which it currently is for most), use FALLBACK
if (mainQuery.rows.length === 0) {
  // FALLBACK A: Get precinct-specific requirements
  const precinctQuery = `
    SELECT * FROM dcp_precinct_requirements
    WHERE precinct_id = 'marrickville_9_13_henson_park'
  `;

  // FALLBACK B: Get general provisions from LEGACY table
  const legacyQuery = `
    SELECT * FROM regulatory_provisions
    WHERE document_id ILIKE '%Marrickville%'
      AND (
        document_id ~ '_2011_[247][_.]'     -- Parts 2, 4, 7
        OR document_id ILIKE '%_4.1_%'      -- Low density
        OR document_id ILIKE '%_2__1%'      -- Urban Design
        OR document_id ILIKE '%_2__10%'     -- Parking
        OR document_id ILIKE '%_2__18%'     -- Landscaping
      )
  `;

  // COMBINE both precinct + general
  return { precinct: precinctResults, general: legacyResults };
}
```

**Result**: Shows neighbourhood-specific requirements + general provisions from legacy data.

---

### Leichhardt - Fallback Path (Similar to Marrickville)

```typescript
// Step 1: Try dcp_general_requirements (NEW)
const mainQuery = `
  SELECT * FROM dcp_general_requirements
  WHERE lga = 'INNER WEST'
    AND former_council = 'Leichhardt'
`;

// Step 2: If empty, use FALLBACK
if (mainQuery.rows.length === 0) {
  // FALLBACK A: Get neighbourhood requirements
  const neighbourhoodQuery = `
    SELECT * FROM dcp_precinct_requirements
    WHERE precinct_id = 'leichhardt_c2_2_3_2_west_leichhardt'
  `;

  // FALLBACK B: Get general provisions from LEGACY table
  const legacyQuery = `
    SELECT * FROM regulatory_provisions
    WHERE document_id ILIKE '%Leichhardt%'
      AND document_id ILIKE '%Part%General%'
  `;

  return { neighbourhood: neighbourhoodResults, general: legacyResults };
}
```

**Result**: Shows neighbourhood-specific requirements + general provisions from legacy data.

---

## 3. Filtering Philosophy

### Ashfield: Strict Filtering (Zone + Development Type)
```
User Query: 180 Addison Road, R2 zone, dwelling_house

Database Filtering:
├── Zone: R2 ✓
├── Dev Type: dwelling_house ✓
└── Former Council: Ashfield ✓

Result: ONLY requirements that apply to R2 + dwelling_house
Example: 54 requirements (highly specific)
```

**Why**: Ashfield DCP Chapter F has explicit zone and development type controls in structured format.

---

### Marrickville: Partial Filtering (Development Type + Geography)
```
User Query: 40 Lackey Street, Henson Park neighbourhood, dwelling_house

Database Filtering:
├── Precinct: Henson Park ✓ (geographic boundary)
├── Dev Type: Low Density Residential (Part 4.1) ✓
└── General: Part 2 controls (apply to ALL development) ✓

Result: Neighbourhood controls + some filtered general controls
Example: 274 requirements (neighbourhood-specific + general)
```

**Why**: Marrickville DCP has strong neighbourhood character areas that override general controls.

---

### Leichhardt: Minimal Filtering (Mostly Geography)
```
User Query: 181 Addison Road, West Leichhardt neighbourhood

Database Filtering:
├── Neighbourhood: West Leichhardt ✓ (geographic boundary)
└── General: Parts A-E (apply to ALL development) ✓

Result: Neighbourhood controls + universal general controls
Example: 27 requirements (neighbourhood-specific + universal)
```

**Why**: Leichhardt DCP Parts A-E are mostly universal controls that apply regardless of zone/devtype.

---

## 4. Part Number / Category Mapping

### Ashfield Chapter F Structure
```javascript
// Maps part numbers to user-friendly categories
Part F.1 → "Dwelling Houses"
Part F.2 → "Secondary Dwellings"
Part F.3 → "Neighbourhood Shops"
Part F.4 → "Multi Dwelling Housing"
Part F.5 → "Residential Flat Buildings"
```

### Marrickville Part Structure
```javascript
// Maps document IDs to categories
_2011_2_1  → "Urban Design"          (Part 2.1)
_2011_2_10 → "Parking"               (Part 2.10)
_2011_2_18 → "Landscaping"           (Part 2.18)
_2011_4.1  → "Setbacks & Building Form"  (Part 4.1)
_2011_9_13 → "Henson Park Neighbourhood" (Part 9.13)
```

### Leichhardt Part Structure
```javascript
// Maps document IDs to categories
Part A → "Administration"
Part B → "General Controls"
Part C Section 1 → "Site Analysis"
Part C Section 2 → "Distinctive Neighbourhoods"
Part D → "Energy Management"
Part E → "Water Management"
```

---

## 5. Dual-Field Extraction Differences

### All 3 Councils: SAME DUAL-FIELD APPROACH ✅

```python
# Ashfield Extraction
prompt = """
For each requirement, provide TWO pieces of text:
1. "summary": Prescriptive/actionable summary
2. "verbatim_text": Exact text from PDF
"""

# Marrickville Extraction
prompt = """
For each requirement, provide TWO pieces of text:
1. "summary": Prescriptive/actionable summary
2. "verbatim_text": Exact text from PDF
"""

# Leichhardt Extraction
prompt = """
For each requirement, provide TWO pieces of text:
1. "summary": Prescriptive/actionable summary
2. "verbatim_text": Exact text from PDF
"""
```

**Same Output Schema:**
```json
{
  "summary": "Buildings must provide 3m setbacks",
  "verbatim_text": "C1 Buildings are to provide adequate setbacks of 3 metres...",
  "category": "setbacks"
}
```

---

## 6. API Response Differences

### Ashfield Response (Zone + DevType Filtered)
```json
{
  "general_provisions": {
    "source": "Chapter F - General DCP Controls",
    "applicable_to": "All properties in R2 zone with dwelling_house development",
    "requirements_count": 54,
    "requirements": [
      {
        "requirement_text": "Boundary fences must minimize visual dominance...",
        "verbatim_source_text": "achieve an appropriate balance between providing...",
        "category": "privacy"
      }
    ]
  },
  "precinct_provisions": null  // OR precinct data if detected
}
```

### Marrickville Response (Neighbourhood + General)
```json
{
  "general_provisions": {
    "source": "Parts 2, 4.1, 7 - General DCP Controls",
    "applicable_to": "All properties in Marrickville LGA",
    "requirements_count": 150,  // From legacy regulatory_provisions
    "requirements": [
      {
        "requirement_text": "Parking must be provided at 1 space per dwelling",
        "verbatim_source_text": "C1 Parking is to be provided at a rate of 1 space...",
        "category": "parking"
      }
    ]
  },
  "precinct_provisions": {
    "source": "Henson Park Neighbourhood",
    "precinct_name": "Henson Park",
    "requirements_count": 45,  // From dcp_precinct_requirements
    "requirements": [...]
  }
}
```

### Leichhardt Response (Neighbourhood + General)
```json
{
  "general_provisions": {
    "source": "Parts A-E - General DCP Controls",
    "applicable_to": "All properties in Leichhardt LGA",
    "requirements_count": 27,
    "requirements": [
      {
        "requirement_text": "Site and context analysis must be submitted...",
        "verbatim_source_text": "C1 Site and context analysis is to be documented...",
        "category": "other"
      }
    ]
  },
  "precinct_provisions": {
    "source": "West Leichhardt Neighbourhood",
    "precinct_name": "West Leichhardt",
    "requirements_count": 35,
    "requirements": [...]
  }
}
```

---

## 7. Code Paths in `/api/compliance/dcp-complete`

### Decision Tree

```
START: User queries 180 Addison Road
  ↓
1. Detect Former Council Area
  ├─ Coordinates → PostGIS query → "Ashfield"
  └─ Fallback → Address parser → "Ashfield"
  ↓
2. Set Query Parameters
  ├─ Ashfield → queryLGA = 'INNER WEST'
  ├─ Marrickville → queryLGA = 'MARRICKVILLE'
  └─ Leichhardt → queryLGA = 'LEICHHARDT'
  ↓
3. Query General Requirements
  ├─ SELECT FROM dcp_general_requirements
  │   WHERE lga = queryLGA
  │     AND zone = ANY(applicable_zones)      ← Ashfield only
  │     AND devtype = ANY(development_types)  ← Ashfield only
  ↓
4. Check Result Count
  ├─ > 0 rows? → Use dcp_general_requirements (Ashfield path)
  └─ = 0 rows? → Use FALLBACK (Marrickville/Leichhardt path)
     ↓
     FALLBACK PATH:
     ├─ Query dcp_precinct_requirements (precinct-specific)
     ├─ Query regulatory_provisions (legacy general)
     └─ Combine both
  ↓
5. Return Combined Response
   ├─ general_provisions: { requirements: [...] }
   └─ precinct_provisions: { requirements: [...] } (if applicable)
```

---

## 8. Why These Differences Exist

### Historical Context

| Council | DCP Structure | Reason for Current Approach |
|---------|---------------|----------------------------|
| **Ashfield** | Highly structured Chapter F with explicit zone/devtype tables | Small council area, uniform approach, data cleanly migrated to new schema |
| **Marrickville** | Mixed structure: General parts + strong neighbourhood character areas | Larger council, diverse neighbourhoods, some data still in legacy schema |
| **Leichhardt** | Universal parts + distinctive neighbourhood overlays | Mixed urban/industrial, neighbourhood character is primary differentiator |

### Migration Status

- **Ashfield**: ✅ 100% migrated to new `dcp_general_requirements` table
- **Marrickville**: 🔄 Partially migrated (274 in new table, rest in legacy)
- **Leichhardt**: 🔄 Partially migrated (27 in new table, rest in legacy)

---

## 9. Summary: Key Takeaways

### Same Across All Councils ✅
- Dual-field extraction (summary + verbatim)
- 100% verbatim coverage
- Same UI display pattern
- Same database schema
- Same extraction methodology

### Different Across Councils ⚠️

| Aspect | Ashfield | Marrickville | Leichhardt |
|--------|----------|--------------|------------|
| **Primary Data Source** | New table | Legacy table (fallback) | Legacy table (fallback) |
| **Filtering** | Zone + DevType | DevType + Geography | Geography only |
| **DCP Structure** | Chapter F (10 parts) | Parts 2, 4, 7, 9 | Parts A-E + C.2 |
| **Requirements Count** | 54 (highly specific) | 274 (broader) | 27 (minimal) |
| **Precinct Integration** | Chapter D (20 precincts) | Part 9 (neighbourhoods) | Part C.2 (neighbourhoods) |

### Future Direction

**Goal**: Migrate Marrickville and Leichhardt fully to `dcp_general_requirements` table with zone+devtype filtering like Ashfield.

**Timeline**: TBD - requires full re-extraction of legacy data with structured metadata.
