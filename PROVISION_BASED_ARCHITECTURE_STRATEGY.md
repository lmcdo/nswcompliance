# Provision-Based Architecture Strategy

## Document Purpose

This document defines the architecture for the compliance engine. It is structured by importance: **the runtime flow comes first** because everything else exists to support it.

---

## Part 1: Runtime Architecture (THE CORE)

This is what the system does when a user enters an address.

### The Complete Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                    USER ENTERS ADDRESS                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE A: PLANNING PORTAL API                       │
│                                                                 │
│  Automatic call to NSW Planning Portal returns:                 │
│                                                                 │
│  Location:           zone, lga, coordinates                     │
│  Numeric controls:   maxHeight, maxFsr, minLotSize              │
│  Site conditions:    heritage, floodProne, bushfireProne        │
│  Strategic overlays: todPrecinct, hiaArea                       │
│                                                                 │
│  Code: frontend-nextjs/lib/nsw-planning-portal.ts               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE B: PRECINCT DETECTION                        │
│                                                                 │
│  Spatial query using coordinates → precinct_id                  │
│                                                                 │
│  Code: frontend-nextjs/lib/precinct-service.ts                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE C: AUTOMATIC FILTERING (4-Layer Model)       │
│                                                                 │
│  Planning Portal data drives database query using 4 layers:     │
│                                                                 │
│  LAYER 1 - Generic (Part 2/Section 1): ALWAYS include           │
│    → v2_dcp_layer = 'generic'                                   │
│                                                                 │
│  LAYER 2 - Use-specific (Part 4/Section 3): Zone-filtered       │
│    → v2_dcp_layer = 'use_specific'                              │
│    → zone = "R2" filters to Part 4.1 (low density)              │
│                                                                 │
│  LAYER 3 - Condition (Part 8/heritage markers): IF applicable   │
│    → heritage = false → EXCLUDE heritage-required               │
│    → floodProne = false → EXCLUDE flood-required                │
│    → bushfireProne = false → EXCLUDE bushfire-required          │
│                                                                 │
│  LAYER 4 - Precinct (Part 9/Section 2): Location-filtered       │
│    → precinct = "X" → Include precinct X provisions             │
│                                                                 │
│  Result: ~350-400 provisions (no user input yet)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE D: USER SELECTION                            │
│                                                                 │
│  Development Type dropdown:                                     │
│    Residential > Alterations > Rear addition                    │
│    → Filter: v2_applicable_dev_types contains 'rear_addition'   │
│                                                                 │
│  Assessment Type dropdown:                                      │
│    ○ CDC  ○ DA  ○ Exempt                                        │
│    → CDC: Only quantitative controls                            │
│    → DA: All applicable provisions                              │
│                                                                 │
│  Result: ~50-90 provisions                                      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│              PHASE E: DISPLAY                                   │
│                                                                 │
│  Provisions grouped by category, showing:                       │
│  • Original provision text (not LLM summary)                    │
│  • Extracted numeric values                                     │
│  • PDF page link                                                │
│  • Precinct override/supplement indicators                      │
│                                                                 │
│  + Keyword search within filtered results                       │
└─────────────────────────────────────────────────────────────────┘
```

### Planning Portal Fields Used

| Portal Field | Type | Filter Logic (4-Layer Model) |
|--------------|------|------------------------------|
| `lga` | string | Which council's DCP to query |
| `zone` | string | Layer 2 only: Filter use-specific provisions (Part 4) |
| `heritage` | boolean | Layer 3: If false, exclude heritage-required provisions |
| `floodProne` | boolean | Layer 3: If false, exclude flood-required provisions |
| `bushfireProne` | boolean | Layer 3: If false, exclude bushfire-required provisions |
| `coordinates` | {x,y} | Layer 4: Spatial lookup for precinct |
| `maxHeight` | number | Display; future: auto-check compliance |
| `maxFsr` | number | Display; future: auto-check compliance |

**Note:** Layer 1 (Generic) provisions are ALWAYS included regardless of zone.

### User Selection Options

**Development Type (hierarchical dropdown):**
```
▼ Residential
  ├─ New dwelling house
  ├─ Alterations & additions
  │   ├─ Ground floor addition
  │   ├─ First floor addition
  │   └─ Rear addition
  ├─ Secondary dwelling (granny flat)
  ├─ Dual occupancy - attached
  ├─ Dual occupancy - detached
  └─ Multi-dwelling housing
▼ Commercial
  ├─ Shop fit-out
  ├─ Change of use
  └─ New commercial building
```

**Assessment Type (radio):**
- CDC (Complying Development) → Only quantitative controls
- DA (Development Application) → All provisions
- Exempt Development → Exempt thresholds only
- State Significant → State-level provisions

### Provision Count Cascade

```
48,374 total provisions in database

Phase A-C (Automatic - Planning Portal):
├─ LGA filter (Inner West):     ~2,000
├─ Zone filter (R2):            ~800
├─ Precinct (general + match):  ~850
├─ Heritage = false:            ~836 (-14)
├─ Flood = false:               ~820 (-16)
└─ Bushfire = false:            ~812 (-8)

Phase D (User selection):
├─ Dev type (rear_addition):    ~200
└─ Assessment (CDC):            ~90

FINAL: ~90 provisions (~45 quantitative)
```

### API Design

```typescript
// POST /api/provisions/for-property
{
  "address": "180 Addison Road, Marrickville NSW 2204",
  "development_type": "dwelling_addition_rear",  // optional
  "assessment_type": "CDC"                       // optional
}

// Response
{
  "property": {
    "address": "180 Addison Road, Marrickville NSW 2204",
    "zone": "R2",
    "precinct": "Lewisham North",
    "heritage": false,
    "flood": false,
    "bushfire": false
  },
  "filters_applied": {
    "automatic": ["lga=Inner West", "zone=R2", "heritage=false", ...],
    "user": ["development_type=rear_addition", "assessment_type=CDC"]
  },
  "provisions": {
    "total": 87,
    "quantitative": 45,
    "qualitative": 42
  },
  "categories": [
    {
      "name": "Setbacks",
      "count": 6,
      "provisions": [...]
    }
  ]
}
```

---

## Part 2: Data Model

The provision enrichment must support the runtime flow in Part 1.

### Required Fields on regulatory_provisions

```sql
-- Core identification
id                          -- existing
provision_text              -- existing (THE PRIMARY DISPLAY TEXT)
document_id                 -- existing
page_number                 -- existing
pdf_page_image_url          -- existing

-- NEW: Type classification
v2_provision_type           -- control/objective/definition/note/procedural

-- NEW: DCP Layer (4-layer model from web research)
v2_dcp_layer                -- 'generic' | 'use_specific' | 'condition' | 'precinct'
                            -- generic = Part 2 (Mville), Section 1 (Leich), always apply
                            -- use_specific = Part 4 (Mville), Section 3 (Leich), zone-filtered
                            -- condition = Part 8 (heritage), filtered by site condition
                            -- precinct = Part 9/Section 2, location-filtered

-- NEW: DCP Part/Section (source location)
v2_dcp_part                 -- e.g., 'Part 2.6', 'Part C Section 1', 'Chapter D'

-- NEW: Topic for UI grouping
v2_topic                    -- 'setbacks' | 'parking' | 'solar' | 'privacy' | 'landscaping' | etc.

-- NEW: Categories for UI sub-grouping
v2_categories               -- text[] e.g., ['setback_front', 'setback']

-- NEW: Scope (DEPRECATED - use v2_dcp_layer instead)
v2_scope                    -- 'general' | 'precinct' (kept for backwards compat)
v2_precinct_id              -- if layer = 'precinct'

-- NEW: Numeric extraction
v2_has_numeric_value        -- boolean
v2_extracted_values         -- jsonb {value_min, value_max, unit}

-- NEW: Applicability (maps to Planning Portal)
v2_applicable_zones         -- text[] e.g., ['R2', 'R3'] or ['ALL']
v2_applicable_dev_types     -- text[] e.g., ['dwelling_addition_rear']

-- NEW: Site condition requirements (KEY FOR FILTERING)
v2_site_condition_required  -- 'heritage' | 'flood' | 'bushfire' | null
                            -- If 'heritage': only show when property IS heritage
                            -- If null: always show (general provision)

-- NEW: Precinct relationships
v2_relationship_type        -- 'override' | 'supplement' | 'standalone'
v2_overrides_provision_id   -- FK to general provision this overrides

-- NEW: Conditionals
v2_has_conditionals         -- boolean
v2_conditional_summary      -- text summary of conditions

-- NEW: Processing metadata
v2_enrichment_version       -- version string
v2_enriched_at              -- timestamp
```

### Mapping: Portal Fields → Provision Fields (4-Layer Model)

| Portal Returns | Layer | Provision Field | Query Logic |
|----------------|-------|-----------------|-------------|
| `lga: "Inner West"` | All | `document_id` | Filter by council DCP |
| (always) | 1-Generic | `v2_dcp_layer` | `v2_dcp_layer = 'generic'` (ALWAYS include) |
| `zone: "R2"` | 2-Use | `v2_dcp_layer`, `v2_applicable_zones` | `v2_dcp_layer = 'use_specific' AND 'R2' = ANY(v2_applicable_zones)` |
| `heritage: false` | 3-Condition | `v2_site_condition_required` | `v2_site_condition_required != 'heritage'` |
| `floodProne: false` | 3-Condition | `v2_site_condition_required` | `v2_site_condition_required != 'flood'` |
| `bushfireProne: false` | 3-Condition | `v2_site_condition_required` | `v2_site_condition_required != 'bushfire'` |
| `precinct: "X"` | 4-Precinct | `v2_dcp_layer`, `v2_precinct_id` | `v2_dcp_layer = 'precinct' AND v2_precinct_id = 'X'` |
| (user selects) | All | `v2_applicable_dev_types` | `dev_type = ANY(v2_applicable_dev_types)` |

### Site Condition Logic

This is critical for filtering:

```sql
-- Provision: "Heritage items must maintain original facade"
-- v2_site_condition_required = 'heritage'
-- This provision ONLY appears if property IS heritage

-- Provision: "Setback minimum 6m"
-- v2_site_condition_required = NULL
-- This provision appears for ALL properties (general)

-- Query when heritage = false:
WHERE (v2_site_condition_required IS NULL
       OR v2_site_condition_required != 'heritage')
```

### Development Type Granularity

**Problem:** Coarse tagging like `['dwelling']` returns too many provisions.

**Solution:** Granular sub-types:

```
dwelling                    → TOO BROAD
dwelling_new                → New dwelling house
dwelling_addition           → Any addition
dwelling_addition_ground    → Ground floor addition
dwelling_addition_first     → First floor addition
dwelling_addition_rear      → Rear addition
dwelling_secondary          → Granny flat
dual_occupancy              → Either type
dual_occupancy_attached     → Attached
dual_occupancy_detached     → Detached
```

Provisions tagged with `dwelling_addition_rear` only match when user selects "rear addition".

---

## Part 3: Why Provision-Based

### The Problem with Current Approach

```
Current: PDF → Provisions → LLM "extracts requirements" → dcp_*_requirements
```

**What happens:**
- Original DCP text in `regulatory_provisions` table
- LLM creates NEW "requirement" records with summary text
- UI displays LLM summary, not original
- Page linkage often broken

**Example:**

Original DCP:
```
"C4 Buildings must be setback a minimum of 6 metres from the front boundary
to maintain the established streetscape character of the area."
```

LLM output:
```
"Minimum front setback: 6m"
```

This throws away the actual regulatory text.

### Why This Fails Professionals

A professional writing a DA submission needs:

> "The proposed development complies with Control C4 of Ashfield DCP Chapter D
> which states that 'Buildings must be setback a minimum of 6 metres from the
> front boundary'. The proposed setback of 6.5m satisfies this requirement."

They cannot cite "Minimum front setback: 6m" - that's not what the DCP says.

### The Optimal Approach

```
Optimal: PDF → Provisions → LLM ENRICHES provisions → Same provisions with metadata
```

**The provision IS the requirement. Don't create synthetic text.**

The LLM adds metadata (type, categories, values) to existing provisions. It does not create new text.

### Provision Types

| Type | Pattern | Example |
|------|---------|---------|
| CONTROL | "must", "shall", "minimum" | "Buildings must be setback minimum 6m" |
| OBJECTIVE | "To ensure...", "Purpose:" | "To maintain streetscape character" |
| PERFORMANCE_CRITERIA | "PC1:", "must achieve" | "Must achieve adequate privacy" |
| DEFINITION | "means", "includes" | "Front setback means the distance..." |
| NOTE | "Note:", "Except where" | "Does not apply to heritage items" |
| PROCEDURAL | "Applications must", "Submit" | "Applications must include site plan" |

---

## Part 4: Enrichment Pipeline

How to prepare provisions to support the runtime flow.

### Tiered Processing (97% API Cost Reduction)

**Phase 1: Regex Numeric Extraction (Free, Instant)**

```python
patterns = [
    r"minimum\s+(\d+\.?\d*)\s*(m|metres)",
    r"maximum\s+(\d+\.?\d*)\s*(m|storeys)",
    r"setback of\s+(\d+\.?\d*)\s*m",
    r"FSR\s+(\d+\.?\d*):1",
    r"height limit\s+(\d+\.?\d*)\s*m"
]
```

Result: 80% of numeric values extracted, 0 API calls.

**Phase 2: Type Classification (Batch LLM)**

Send 50-100 provisions per batch:
```
Classify each as: CONTROL | OBJECTIVE | DEFINITION | NOTE | PROCEDURAL
```

Simple classification = fast, cheap.

**Phase 3: Applicability Tagging (Rules + LLM)**

Many provisions state applicability explicitly:
- "This applies to R2 zones" → regex extracts
- "For dwelling houses" → regex extracts

Inherit from document structure:
- "Chapter F1: Dwelling Houses" → all provisions inherit `dwelling_house`

LLM only for ambiguous cases.

**Phase 4: Site Condition Tagging**

Identify provisions that require specific site conditions:
- Contains "heritage item" → `v2_site_condition_required = 'heritage'`
- Contains "flood prone" → `v2_site_condition_required = 'flood'`
- Contains "bushfire prone" → `v2_site_condition_required = 'bushfire'`

**Phase 5: Deep Enrichment (Selective)**

Only for provisions that are:
- Type = CONTROL
- AND have conditionals OR cross-references

This is ~20% of provisions.

**Phase 6: Layer + Topic Tagging (NEW - from web research)**

Assign each provision to the 4-layer model based on document_id:

```python
# Marrickville
"Part 2" → v2_dcp_layer = 'generic', v2_topic from section (2.6→privacy, 2.7→solar)
"Part 4" → v2_dcp_layer = 'use_specific'
"Part 8" → v2_dcp_layer = 'condition', v2_site_condition = 'heritage'
"Part 9" → v2_dcp_layer = 'precinct'

# Leichhardt
"Section 1" → v2_dcp_layer = 'generic', v2_topic from C marker
"Section 2" → v2_dcp_layer = 'precinct'
"Section 3" → v2_dcp_layer = 'use_specific'
"Part D/E" → v2_dcp_layer = 'generic', v2_topic = 'energy'/'water'

# Ashfield
"Chapter F" → v2_dcp_layer = 'generic' (with marker-based display rules)
"Chapter D" → v2_dcp_layer = 'precinct'
"Chapter E1" → v2_dcp_layer = 'condition', v2_site_condition = 'heritage'
```

Extract topic from:
- Section number (Marrickville: 2.6 = privacy)
- C marker (Leichhardt: C3 = parking)
- Keyword matching (fallback)

### Cost Comparison

| Approach | API Calls |
|----------|-----------|
| Full LLM on all provisions | 2,000 |
| Tiered approach | ~60 |
| **Reduction** | **97%** |

---

## Part 5: Precinct Integration (4-Layer Model)

### The Hierarchy (Revised)

```
SEPP (State) → LEP → DCP Layer 1 (Generic) → DCP Layer 2 (Use) → DCP Layer 3 (Condition) → DCP Layer 4 (Precinct)
```

**How layers combine for a property in Summer Hill precinct, R2 zone, non-heritage:**

| Layer | Provisions | Action |
|-------|------------|--------|
| 1-Generic | Part 2 (privacy, solar, parking, etc.) | ALWAYS include |
| 2-Use | Part 4.1 (R2 low density) | Include (zone match) |
| 3-Condition | Part 8 (heritage) | EXCLUDE (property not heritage) |
| 4-Precinct | Part 9.X (Summer Hill) | Include (location match) |

All 4 layers apply simultaneously - they don't override each other like SEPP/LEP.
Precinct provisions may override/supplement specific General controls (see below).

### Relationship Types

**Override:**
- General: "Front setback minimum 6m"
- Precinct: "Front setback minimum 4m for Smith Street"
- Result: 4m applies to Smith Street properties, not 6m

**Supplement:**
- General: "Landscaping 30% of site"
- Precinct: "Corner sites must also provide street tree"
- Result: Both apply

**Standalone:**
- Precinct: "Maintain views to railway heritage corridor"
- Result: No general equivalent, unique to precinct

### Detection Patterns

Override indicators:
- "notwithstanding Part F..."
- "instead of the requirements in..."
- "in lieu of..."

Supplement indicators:
- "in addition to..."
- "as well as..."

### Query Logic

```sql
-- Get general provisions
SELECT * FROM provisions
WHERE v2_scope = 'general'
AND 'R2' = ANY(v2_applicable_zones);

-- Get precinct provisions
SELECT * FROM provisions
WHERE v2_scope = 'precinct'
AND v2_precinct_id = 'summer_hill';

-- Application logic resolves:
-- If precinct has override → show precinct only
-- If precinct has supplement → show both
-- If precinct silent → show general only
```

---

## Part 6: DCP Configuration

Each council's DCP has different structure. Core processing is universal; applicability inheritance is configured per DCP.

### Key Insight: All Three DCPs Share Similar Architecture

Despite surface differences, all three councils follow the same pattern:
1. **Generic/General provisions** - Topic-based, apply to ALL development
2. **Use-specific provisions** - Apply to residential, commercial, etc.
3. **Location-specific provisions** - Precincts/neighbourhoods
4. **Condition-based provisions** - Heritage, flood, bushfire

### Structure Comparison (Revised via Web Research)

**MARRICKVILLE DCP 2011:**
```
Part 2: Generic Provisions (topic-based) → ALL development
  - 2.3 Site Analysis, 2.6 Privacy, 2.7 Solar, 2.10 Parking
  - 2.14 Environmental, 2.17 WSUD, 2.18 Landscaping, 2.21 Waste
Part 4: Residential (zone-based)
  - 4.1 Low Density (R2) → dwelling_house, alterations
  - 4.2 Multi-dwelling (R3/R4) → townhouses, apartments
Part 5: Commercial/Mixed Use (B zones)
Part 8: Heritage (condition-based) → only if heritage item/HCA
Part 9: Planning Precincts (47 precincts with character statements)
```

**LEICHHARDT DCP 2013:**
```
Part C Section 1: General Provisions (topic-based via C markers) → ALL development
  - C1 Site Analysis, C2 Heritage, C3 Parking, C15 Parking Rates
  - C18-C21 Bicycle Parking, C43-C55 Vehicle Access
Part C Section 2: Urban Character / Distinctive Neighbourhoods (23+)
Part C Section 3: Residential Provisions (use-specific)
  - Setbacks, height envelopes (2.4m, 3.6m, 6.0m, 7.2m)
  - Solar (3hrs min), privacy, dormers
Part C Section 4: Non-Residential Provisions
Part C Section 5: Special Entertainment Precincts
Part D/E: Energy/Water (topic-based, ALL dev types)
Part G: Site-Specific Controls
```

**ASHFIELD DCP 2016:**
```
Chapter E1: Heritage (condition-based)
Chapter D: Precincts (D1-D17 with specific controls)
Chapter F: Development Category (PC/DS format)
  - DS (Design Solutions): 29 quantitative controls → CDC
  - PC (Performance Criteria): 134 objectives → DA
  - C/O controls: 99 additional controls
  - Unmarked: 1,264 narrative/context → collapsed display
```

### Professional Workflow (How All Three Are Actually Used)

For residential alteration, professionals check:

| Council | Generic Topics | Zone/Use | Condition | Location |
|---------|---------------|----------|-----------|----------|
| Marrickville | Part 2 (ALL) | Part 4.1/4.2 | Part 8 (if heritage) | Part 9 (precinct) |
| Leichhardt | Section 1 (ALL) | Section 3 | C2, C37 (if heritage) | Section 2 (neighbourhood) |
| Ashfield | Chapter F (ALL) | Chapter F (by marker) | Chapter E1 (if heritage) | Chapter D (precinct) |

### Configuration Files (Updated)

```python
# config/marrickville_config.py
STRUCTURE = {
    # Part 2 - Generic (ALL apply)
    "Part 2.3": {"topic": "site_analysis", "applies_to": "ALL"},
    "Part 2.6": {"topic": "privacy", "applies_to": "ALL"},
    "Part 2.7": {"topic": "solar", "applies_to": "ALL"},
    "Part 2.10": {"topic": "parking", "applies_to": "ALL"},
    "Part 2.18": {"topic": "landscaping", "applies_to": "ALL"},
    # Part 4 - Zone-specific
    "Part 4.1": {"zones": ["R2"], "dev_types": ["dwelling_house", "alterations"]},
    "Part 4.2": {"zones": ["R3", "R4"], "dev_types": ["multi_dwelling", "rfb"]},
    # Part 8 - Condition-based
    "Part 8": {"site_condition": "heritage"},
    # Part 9 - Location-specific
    "Part 9": {"scope": "precinct"},
}

# config/leichhardt_config.py
STRUCTURE = {
    # Section 1 - General (topic via C markers)
    "Part C Section 1": {
        "applies_to": "ALL",
        "markers": {
            "C1": "site_analysis", "C2": "heritage", "C3": "parking",
            "C15": "parking_rates", "C18-C21": "bicycle_parking"
        }
    },
    # Section 3 - Residential
    "Part C Section 3": {"dev_types": ["residential"]},
    # Section 2 - Neighbourhoods
    "Part C Section 2": {"scope": "precinct"},
}

# config/ashfield_config.py
STRUCTURE = {
    # Chapter F - by marker type
    "Chapter F": {
        "marker_types": {
            "DS": {"display": "always_cdc", "type": "control"},
            "PC": {"display": "da_variations", "type": "objective"},
            "C/O": {"display": "da", "type": "control"},
            "unmarked": {"display": "collapsed_context"}
        }
    },
    # Chapter E1 - Heritage
    "Chapter E1": {"site_condition": "heritage"},
    # Chapter D - Precincts
    "Chapter D": {"scope": "precinct"},
}
```

### What's Universal vs. Configured

**Universal (same code):**
- Type classification (control/objective/definition/note)
- Category tagging by topic keywords
- Numeric extraction (regex patterns)
- Site condition detection (heritage/flood/bushfire)
- Override detection

**Configured per DCP:**
- Which parts apply to ALL vs specific zones/dev-types
- Topic extraction method (numbered sections vs C markers vs PC/DS)
- Precinct ID extraction patterns
- Display behavior by marker type (Ashfield PC/DS)
- How to map sections to topics

---

## Part 7: Migration Execution

### Approach: Parallel Build

**DO NOT** modify existing tables/routes/UI in place.
Build new alongside old, test, then switch.

### Database Changes

```sql
-- Add v2_ columns to regulatory_provisions
ALTER TABLE regulatory_provisions
ADD COLUMN IF NOT EXISTS v2_provision_type TEXT,
ADD COLUMN IF NOT EXISTS v2_categories TEXT[],
ADD COLUMN IF NOT EXISTS v2_scope TEXT,
ADD COLUMN IF NOT EXISTS v2_precinct_id TEXT,
ADD COLUMN IF NOT EXISTS v2_has_numeric_value BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS v2_extracted_values JSONB,
ADD COLUMN IF NOT EXISTS v2_applicable_zones TEXT[],
ADD COLUMN IF NOT EXISTS v2_applicable_dev_types TEXT[],
ADD COLUMN IF NOT EXISTS v2_site_condition_required TEXT,
ADD COLUMN IF NOT EXISTS v2_has_conditionals BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS v2_conditional_summary TEXT,
ADD COLUMN IF NOT EXISTS v2_relationship_type TEXT,
ADD COLUMN IF NOT EXISTS v2_overrides_provision_id INTEGER,
ADD COLUMN IF NOT EXISTS v2_enrichment_version TEXT,
ADD COLUMN IF NOT EXISTS v2_enriched_at TIMESTAMP;

-- Indexes
CREATE INDEX idx_v2_provision_type ON regulatory_provisions(v2_provision_type);
CREATE INDEX idx_v2_scope ON regulatory_provisions(v2_scope);
CREATE INDEX idx_v2_categories ON regulatory_provisions USING GIN(v2_categories);
CREATE INDEX idx_v2_applicable_zones ON regulatory_provisions USING GIN(v2_applicable_zones);
CREATE INDEX idx_v2_site_condition ON regulatory_provisions(v2_site_condition_required);

-- Deprecation comments on legacy tables
COMMENT ON TABLE dcp_general_requirements IS 'DEPRECATED: Use regulatory_provisions.v2_* instead';
COMMENT ON TABLE dcp_precinct_requirements IS 'DEPRECATED: Use regulatory_provisions.v2_* instead';
```

### Directory Structure

```
compliance-engine/
├── enrichment/                     # NEW
│   ├── config/
│   │   ├── ashfield_config.py
│   │   ├── marrickville_config.py
│   │   └── leichhardt_config.py
│   ├── extractors/
│   │   ├── numeric_extractor.py
│   │   ├── type_classifier.py
│   │   ├── applicability_tagger.py
│   │   └── site_condition_tagger.py
│   ├── pipeline.py
│   └── tests/
│
├── frontend-nextjs/
│   ├── app/api/
│   │   ├── compliance/             # LEGACY
│   │   └── provisions/             # NEW
│   │       └── for-property/
│   │           └── route.ts
│   └── components/
│       ├── compliance/             # LEGACY
│       └── provisions/             # NEW
│
└── DEPRECATED/                     # Move old extraction scripts
```

### Execution Steps (Updated 2025-11-23)

**Phase 0: Setup** ✅ COMPLETE
- [x] Backup database (`backups/regulatory_provisions_before_v2_20251122_231205.json`)
- [x] Create feature branch: `feature/provision-based-architecture`

**Phase 1: Schema** ✅ COMPLETE
- [x] Run migration SQL (16 v2_ columns)
- [x] Create indexes (9 indexes)
- [x] Verify columns exist

**Phase 2: Build Pipeline** ✅ COMPLETE
- [x] Actionable classifier (v2_is_actionable: 11,835 actionable / 36,539 boilerplate)
- [x] Numeric extractor (regex) - 451 provisions with numeric values
- [x] Type classifier (control/objective/definition/note/procedural)
- [x] Site condition tagger (heritage: 1,926 / flood / bushfire)
- [x] Applicability tagger (zones + dev types)
- [x] Council-specific configs (`enrichment/config/`)

**Phase 3: Web Research** ✅ COMPLETE (2025-11-23)
- [x] Research professional workflow for Marrickville
- [x] Research professional workflow for Leichhardt
- [x] Research professional workflow for Ashfield
- [x] Document 4-layer model (Generic → Use → Condition → Precinct)
- [x] Update strategy document

**Phase 4: Layer + Topic Tagging** ❌ NOT STARTED
- [ ] Add v2_dcp_layer column
- [ ] Add v2_dcp_part column
- [ ] Add v2_topic column
- [ ] Implement layer tagger (Part 2 → generic, Part 4 → use_specific, etc.)
- [ ] Implement topic extractor (section numbers, C markers, keywords)
- [ ] Run on all 3 councils

**Phase 5: Marker Extraction** ❌ NOT STARTED
- [ ] Leichhardt C marker extraction (C1, C2, C3, etc.)
- [ ] Ashfield PC/DS marker extraction
- [ ] Map markers to topics

**Phase 6: New API** ❌ NOT STARTED
- [ ] Create `/api/provisions/for-property`
- [ ] Implement 4-layer query logic
- [ ] Test with real addresses

**Phase 7: New UI** ❌ NOT STARTED
- [ ] ProvisionCard component
- [ ] Development type dropdown
- [ ] Assessment type selector
- [ ] Topic grouping (by v2_topic)

**Phase 8: Cutover**
- [ ] Feature flag flip
- [ ] Monitor
- [ ] Deprecate old routes

### Rollback Plan

```bash
# Database
psql $SUPABASE_DB_URL -f backups/pre_v2_migration.sql

# Code
git checkout main

# Feature flag
USE_PROVISIONS_V2=false
```

---

## Part 8: Reference

### Category Distribution (Inner West)

```
character: 56      landscaping: 40
parking: 42        privacy: 34
safety: 34         building_form: 30
building_height: 26   accessibility: 19
setback_front: 19     streetscape: 18
fencing: 18        stormwater: 16
environmental: 16     solar_access: 14
heritage: 14       ...and 36 more
```

### UI Display

**Optimal provision display:**

```
CONTROL - Front Setback

"C4 Buildings must be setback a minimum of 6 metres from the
front boundary to maintain the established streetscape character
of the area."  ← ACTUAL TEXT

📊 Extracted: minimum 6m
🏗️ Applies to: R2, R3 | Dwelling house, Dual occupancy
⚠️ Conditional: Excludes heritage items (see C4.1)

📄 Source: Ashfield DCP Ch.D p.170 [View PDF]
```

**Precinct display:**

```
SETBACKS

[PRECINCT - Summer Hill]
"Front setback minimum 4m for Smith Street"
Overrides general.

[GENERAL - Ashfield] (greyed)
"Front setback minimum 6m"
Overridden by precinct.
```

### Legacy Code Management

**File markers:**
```typescript
/**
 * @deprecated Use /api/provisions instead.
 * DO NOT ADD NEW FEATURES.
 */
```

**Environment variables:**
```bash
USE_PROVISIONS_V2=false  # Toggle new system
```

### Success Criteria

- [ ] All provisions have v2_provision_type
- [ ] All provisions have v2_categories
- [ ] Numeric controls have v2_extracted_values
- [ ] Site conditions properly tagged
- [ ] New API returns correct filtered results
- [ ] New UI displays original provision text
- [ ] PDF page links work
- [ ] Legacy tables can be dropped

---

*Document created: 2024-11-22*
*Restructured: 2025-11-22*
*Major revision: 2025-11-23*
  - *Parts 1,2,4,5,7 updated for 4-layer model (Generic → Use → Condition → Precinct)*
  - *Part 6 revised with web research on professional DCP workflows*
  - *Added v2_dcp_layer, v2_dcp_part, v2_topic fields*
  - *Execution checklist updated to reflect actual completion state*
*Purpose: Authoritative reference for provision-based architecture implementation*
