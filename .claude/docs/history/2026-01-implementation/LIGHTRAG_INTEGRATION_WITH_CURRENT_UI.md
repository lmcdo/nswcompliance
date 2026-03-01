# LightRAG Integration with Current UI Pipeline
**Date:** 2025-10-23
**Purpose:** How LightRAG pre-processing fits into the EXISTING UI/UX

---

## Current UI Pipeline (What Happens When User Enters Address)

### Step 1: Address Input → Property API
```
User enters: "14 Illawarra Rd, Marrickville"
↓
API: /api/property
↓
Returns: NSW Planning Portal data
```

**What's returned:**
- Property ID, coordinates
- Zone: R2
- LGA: Inner West
- LEP data: Height 9.5m, FSR 0.6:1
- **SEPP special provisions** (from Planning API)
  - Example: "40% water reduction (SEPP Sustainable Buildings)"
  - Example: "Climate Zone 56 for BASIX"
- LEP clauses: Clause 4.3, Clause 4.4
- Heritage status, flood status, etc.

---

### Step 2: Constraints API
```
API: /api/compliance/constraints
Input: { address, zone, lga, developmentType }
↓
Returns: Database-extracted controls + provisions
```

**What's returned:**
- **Building envelope** (from database):
  - Height limits (LEP)
  - FSR limits (LEP)
  - Extracted setback controls (if any in development_controls table)

- **Environmental** (from database):
  - Heritage controls
  - Environmental overlays

- **Special provisions** (from database):
  - SEPP overrides

---

### Step 3: UI Renders Cards (ComplianceDashboard.tsx)

**Currently displays 5 main cards:**

#### 1. 🟥 SEPP Special Provisions (Orange Card)
- **Source:** Planning API special provisions
- **Example content:**
  - "40% water reduction"
  - "Climate Zone 56"
  - "Heritage consideration required"
- **Authority level:** SEPP (highest priority)
- **Status:** ✅ Already displaying from Planning API

#### 2. 🟦 LEP Building Envelope (Blue Card)
- **Source:** Planning API + database
- **Example content:**
  - Height: 9.5m (Clause 4.3)
  - FSR: 0.6:1 (Clause 4.4)
  - Lot size: 500m²
- **Authority level:** LEP
- **Status:** ✅ Already displaying from Planning API

#### 3. 🟢 DCP Design Controls (Green Card)
- **Source:** Database (regulatory_provisions table)
- **Contains TWO browsers:**

  **A. Generic DCP Browser (DCPProvisionsBrowser)**
  - Query: Part 2 + Part 4.1 provisions
  - Returns: **241 provisions** for R2 + Dwelling House
  - **Problem:** Too many provisions, hard to browse
  - Filters: Setback | Parking | Landscaping | Privacy
  - **Status:** ❌ Needs LightRAG categorization

  **B. Precinct Browser (PrecinctProvisionsBrowser)**
  - Query: dcp_precinct_provisions for matched precinct
  - Returns: **3-48 provisions** depending on precinct
  - **Problem:** Still raw text provisions, not categorized
  - **Status:** ❌ Needs LightRAG categorization

#### 4. 🅿️ DCP Parking (Green Card)
- **Source:** Database parking-specific query
- **Status:** ✅ Working (structured data)

#### 5. 🌳 Environmental (if applicable)
- **Source:** Database environmental controls
- **Status:** ✅ Working

---

## WHERE LIGHTRAG FITS IN

### The Problem
**DCP Design Controls card currently shows:**
- 241 generic provisions (Part 2 + Part 4.1)
- 3-48 precinct provisions
- **Total: 244-289 raw text provisions**

**User wants:**
- 15-20 actual REQUIREMENTS (not 241 text chunks)
- Clear categories: Setback, Parking, Landscaping, etc.
- Numeric values where applicable

---

## LightRAG Solution: Pre-Process Provisions → Structured Requirements

### Architecture

```
┌─────────────────────────────────────────┐
│ ONE-TIME PRE-PROCESSING (Offline)       │
│                                         │
│ Input: 241 provisions for (LGA, Zone,  │
│        DevType) combination             │
│                                         │
│ LightRAG: "Categorize these into       │
│            requirements"                │
│                                         │
│ Output: 15-20 structured requirements  │
│         stored in dcp_base_requirements│
└─────────────────────────────────────────┘
                   ↓
┌─────────────────────────────────────────┐
│ RUNTIME (When User Searches)            │
│                                         │
│ Query: SELECT * FROM                    │
│        dcp_base_requirements            │
│        WHERE lga='Marrickville'         │
│        AND zone='R2'                    │
│        AND dev_type='dwelling_house'    │
│                                         │
│ Returns: 15-20 categorized requirements│
│          ($0 cost, instant)             │
└─────────────────────────────────────────┘
```

---

## Updated UI Flow with LightRAG

### Card 3: DCP Design Controls (ENHANCED)

**Instead of:**
```
🟢 DCP Design Controls
   └─ Browse All DCP Provisions (241)
      ├─ Filter: Setback (62 provisions)
      ├─ Filter: Landscaping (35 provisions)
      └─ Filter: Parking (28 provisions)
```

**Show:**
```
🟢 DCP Design Controls
   └─ Categorized Requirements (18)

      📏 SETBACKS
      ├─ Front: 5.5m (Part 4.1, Section 3.2)
      ├─ Side: 0.9m (Part 4.1, Section 3.3)
      └─ Rear: 6m (Part 4.1, Section 3.4)

      🌳 LANDSCAPING
      ├─ Front setback: 40% landscaped (Part 2.8)
      └─ Tree retention: Existing trees >5m protected (Part 2.8.5)

      🅿️ PARKING
      ├─ Dwelling house: 1 space minimum (Part 2.10)
      └─ Dual occupancy: 2 spaces (Part 2.10)

      🏠 BUILDING DESIGN
      ├─ Roof pitch: 20-30° preferred (Part 4.1.8)
      └─ Material: Brick/render consistent with street (Part 4.1.9)

      [🔍 View Source Provisions (241)] ← Collapsed by default
```

**Plus precinct supplements:**
```
      📍 PRECINCT-SPECIFIC (South Western Marrickville)
      ├─ Character: Maintain low-density residential character
      ├─ Setback variation: Match existing street pattern
      └─ Landscaping: Front fence <1.2m height

      [🔍 View Source Provisions (3)] ← Collapsed by default
```

---

## Database Schema Integration

### New Tables (Pre-Processed Requirements)

```sql
-- Generic base requirements (constant per LGA/Zone/DevType)
CREATE TABLE dcp_base_requirements (
  id SERIAL PRIMARY KEY,
  lga TEXT NOT NULL,
  zone TEXT NOT NULL,
  dev_type TEXT NOT NULL,

  -- Categorized requirement
  category TEXT NOT NULL,           -- 'setback_front', 'landscaping_street', etc.
  requirement_text TEXT NOT NULL,   -- "Front setback: 5.5 metres"
  value_numeric NUMERIC,            -- 5.5
  value_text TEXT,                  -- "match existing pattern"
  unit TEXT,                        -- 'm', '%', 'degrees'

  -- Source tracking
  source_provision_ids INTEGER[],   -- [12345, 12346] - links to original provisions
  source_documents TEXT[],          -- ['Part_4.1_Section_3.2']
  confidence TEXT,                  -- 'high', 'medium', 'low'

  authority_level TEXT DEFAULT 'DCP',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dcp_base_lookup ON dcp_base_requirements(lga, zone, dev_type);
CREATE INDEX idx_dcp_base_category ON dcp_base_requirements(category);

-- Precinct supplements (varies by address)
CREATE TABLE dcp_precinct_requirements (
  id SERIAL PRIMARY KEY,
  precinct_id TEXT NOT NULL,
  lga TEXT NOT NULL,

  -- Categorized requirement
  category TEXT NOT NULL,
  requirement_text TEXT NOT NULL,
  value_numeric NUMERIC,
  value_text TEXT,
  unit TEXT,

  -- Source tracking
  source_provision_ids INTEGER[],
  source_documents TEXT[],
  confidence TEXT,

  authority_level TEXT DEFAULT 'DCP_PRECINCT',
  created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_dcp_precinct_lookup ON dcp_precinct_requirements(precinct_id, lga);
CREATE INDEX idx_dcp_precinct_category ON dcp_precinct_requirements(category);
```

---

## Updated API Flow

### Current API: /api/compliance/constraints

**Add new endpoint or extend existing:**

```typescript
// NEW: Return pre-processed requirements instead of raw provisions

interface ConstraintsResponse {
  // Existing fields (from Planning API)
  lep: {
    height: { value: 9.5, unit: 'm', clause: 'Clause 4.3' },
    fsr: { value: 0.6, unit: ':1', clause: 'Clause 4.4' }
  },
  sepp: {
    // From Planning API special provisions
    water_reduction: { value: 40, unit: '%', source: 'SEPP Sustainable Buildings 2022' }
  },

  // NEW: Pre-processed DCP requirements
  dcp_base: [
    {
      category: 'setback_front',
      text: 'Front setback: 5.5 metres',
      value: 5.5,
      unit: 'm',
      source_provisions: [12345],
      confidence: 'high'
    },
    {
      category: 'landscaping_street',
      text: 'Front setback landscaped: 40%',
      value: 40,
      unit: '%',
      source_provisions: [12367],
      confidence: 'high'
    },
    // ... ~15-20 total
  ],

  // NEW: Precinct supplements (if address in precinct)
  dcp_precinct: [
    {
      category: 'character',
      text: 'Maintain low-density residential character',
      source_provisions: [55],
      confidence: 'high'
    },
    // ... ~3-8 total
  ],

  // Existing: Link to browse raw provisions
  provision_browse_links: {
    dcp_base: '/api/dcp/provisions?lga=Marrickville&zone=R2&devType=dwelling_house',
    dcp_precinct: '/api/precinct/provisions?precinctId=29_'
  }
}
```

---

## UI Component Updates

### ComplianceDashboard.tsx Enhancement

**Change DCP Design Controls card:**

```tsx
{/* DCP Design Controls Section */}
<Card className="border-green-200">
  <CardHeader className="bg-green-50">
    <CardTitle className="flex items-center gap-2">
      <span className="text-xl">🟢</span>
      DCP Design Controls
    </CardTitle>
    <p className="text-sm text-gray-600 mt-1">
      Development Control Plan - Categorized Requirements
    </p>
  </CardHeader>
  <CardContent className="pt-4">

    {/* NEW: Categorized Requirements */}
    {dcpRequirements && (
      <div className="space-y-4">
        {/* Group by category */}
        {Object.entries(groupByCategory(dcpRequirements)).map(([category, reqs]) => (
          <div key={category} className="border-l-4 border-green-500 pl-4">
            <h4 className="font-semibold text-sm mb-2">
              {categoryIcons[category]} {categoryLabels[category]}
            </h4>
            <div className="space-y-2">
              {reqs.map(req => (
                <RequirementItem
                  key={req.id}
                  text={req.requirement_text}
                  value={req.value_numeric}
                  unit={req.unit}
                  sources={req.source_provisions}
                  confidence={req.confidence}
                />
              ))}
            </div>
          </div>
        ))}
      </div>
    )}

    {/* Precinct supplements */}
    {precinctRequirements && precinctRequirements.length > 0 && (
      <div className="mt-6 border-t pt-4">
        <h4 className="font-semibold text-sm mb-3">
          📍 Precinct-Specific ({{precinctName}})
        </h4>
        <div className="space-y-2">
          {precinctRequirements.map(req => (
            <RequirementItem key={req.id} {...req} />
          ))}
        </div>
      </div>
    )}

    {/* Collapsible: View raw provisions */}
    <details className="mt-6">
      <summary className="cursor-pointer text-sm text-blue-600 hover:text-blue-800">
        🔍 View all source provisions (241 generic + {precinctProvisionCount} precinct)
      </summary>
      <div className="mt-4 space-y-4">
        <DCPProvisionsBrowser {...props} />
        <PrecinctProvisionsBrowser {...props} />
      </div>
    </details>

  </CardContent>
</Card>
```

---

## Category Mapping

```typescript
const categoryIcons = {
  setback_front: '📏',
  setback_side: '📏',
  setback_rear: '📏',
  landscaping_front: '🌳',
  landscaping_rear: '🌳',
  parking: '🅿️',
  building_height: '📐',
  building_design: '🏠',
  character: '📍',
  privacy: '🔒',
  solar_access: '☀️',
  stormwater: '💧',
  fencing: '🚧'
};

const categoryLabels = {
  setback_front: 'SETBACKS - Front',
  setback_side: 'SETBACKS - Side',
  setback_rear: 'SETBACKS - Rear',
  landscaping_front: 'LANDSCAPING - Street',
  landscaping_rear: 'LANDSCAPING - Rear',
  parking: 'PARKING',
  building_height: 'BUILDING HEIGHT',
  building_design: 'BUILDING DESIGN',
  character: 'PRECINCT CHARACTER',
  privacy: 'PRIVACY',
  solar_access: 'SOLAR ACCESS',
  stormwater: 'STORMWATER',
  fencing: 'FENCING'
};
```

---

## Regulatory Hierarchy Display

### All 4 levels in one view:

```
┌─ 🟥 SEPP (State Policy) ────────────────┐
│ Water: 40% reduction                    │
│ BASIX: Climate Zone 56                  │
└─────────────────────────────────────────┘

┌─ 🟦 LEP (Local Law) ────────────────────┐
│ Height: 9.5m max (Clause 4.3)           │
│ FSR: 0.6:1 (Clause 4.4)                │
└─────────────────────────────────────────┘

┌─ 🟢 DCP Base (Guidelines) ──────────────┐
│ SETBACKS                                │
│ ├─ Front: 5.5m                          │
│ ├─ Side: 0.9m                           │
│ └─ Rear: 6m                             │
│                                         │
│ LANDSCAPING                             │
│ └─ Front: 40% landscaped                │
└─────────────────────────────────────────┘

┌─ 📍 Precinct (Neighborhood) ────────────┐
│ Character: Low-density residential      │
│ Setback: Match existing pattern         │
└─────────────────────────────────────────┘
```

**Visual hierarchy:**
- Red border = SEPP (highest priority)
- Blue border = LEP (statutory)
- Green border = DCP (guidelines)
- Light green = Precinct (supplements)

---

## Implementation Steps

### Phase 1: Pre-Process Base Requirements ($10)
1. Extract all (LGA, Zone, DevType) combinations (~100)
2. For each combo, get 241 provisions
3. Run LightRAG: "Categorize into requirements"
4. Store in `dcp_base_requirements` table
5. **Cost:** ~$10 one-time

### Phase 2: Pre-Process Precinct Requirements ($0.75)
1. For each precinct (41 total), get provisions
2. Run LightRAG: "Categorize precinct-specific requirements"
3. Store in `dcp_precinct_requirements` table
4. **Cost:** ~$0.75 one-time

### Phase 3: Update API
1. Modify `/api/compliance/constraints` to query new tables
2. Return categorized requirements instead of raw provisions
3. Keep link to browse raw provisions

### Phase 4: Update UI
1. Update ComplianceDashboard to display categorized requirements
2. Group by category with icons
3. Collapse raw provision browsers by default
4. Show precinct supplements separately

### Phase 5: Add SEPP/LEP to Same Schema (Future)
1. Process SEPP provisions → `sepp_requirements`
2. Process LEP provisions → `lep_requirements`
3. Merge all 4 levels in UI with hierarchy

---

## Cost & Performance

### One-Time Processing
```
DCP Base: 100 combos × $0.10 = $10.00
Precinct: 41 precincts × $0.02 = $0.82
Total: $10.82
```

### Runtime (Per Address)
```
Query 1: dcp_base_requirements (instant, $0)
Query 2: dcp_precinct_requirements (instant, $0)
Merge: Client-side
Total: $0 per address, <100ms
```

### User Experience
- Before: 241-289 provisions to browse
- After: 18-28 categorized requirements
- Improvement: **~92% reduction in noise**

---

## Summary

**Current State:**
- Planning API returns: SEPP + LEP data ✅
- Database returns: 241 + 3-48 raw provisions ❌

**After LightRAG Integration:**
- Planning API returns: SEPP + LEP data ✅
- Database returns: 15-20 base + 3-8 precinct = **18-28 categorized requirements** ✅

**How it fits existing pipeline:**
1. User enters address → Planning API (unchanged)
2. Constraints API → **NEW:** Query pre-processed requirements tables
3. UI displays → **ENHANCED:** Categorized requirements with source links
4. Raw provisions → Still accessible via collapsible section

**Key insight:** LightRAG doesn't change the data flow - it just pre-processes the 241 provisions into structured requirements that are easier to display.
