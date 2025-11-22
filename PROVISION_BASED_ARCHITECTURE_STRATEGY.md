# Provision-Based Architecture Strategy

## Document Purpose
This document consolidates the strategic thinking for refactoring the compliance engine from a "requirements extraction" approach to a "provision enrichment" approach. This is the reference for implementation.

---

## Part 1: The Core Problem

### Current Approach (Requirements-Based)

```
PDF → Provisions → LLM "extracts requirements" → dcp_*_requirements tables
```

**What happens:**
- Original DCP text sits in `regulatory_provisions` table
- LLM reads provisions and creates NEW "requirement" records in `dcp_general_requirements` and `dcp_precinct_requirements`
- UI displays the LLM's summary text
- Original text stored as `verbatim_source_text` but treated as secondary
- Page linkage is often broken

**Example of the problem:**

Original DCP Text:
```
"C4 Buildings must be setback a minimum of 6 metres from the front boundary
to maintain the established streetscape character of the area and provide
adequate separation from the public domain."
```

LLM Output:
```
"Minimum front setback: 6m"
```

We're throwing away the actual regulatory text and replacing it with an LLM summary. This is backwards.

### Why This Matters for Professionals

A professional submitting a DA needs to write:

> "The proposed development complies with Control C4 of Ashfield DCP Chapter D
> which states that 'Buildings must be setback a minimum of 6 metres from the
> front boundary'. The proposed setback of 6.5m satisfies this requirement."

They cannot cite "Minimum front setback: 6m" - that's not what the DCP says.

### Optimal Approach (Provision-Based)

```
PDF → Provisions → LLM CATEGORIZES/ENRICHES provisions → Enriched provisions
```

**The provision IS the requirement. Don't create synthetic text.**

---

## Part 2: What Professionals Actually Need

### The Professional Workflow

1. Enter address → get zone, precinct, overlays
2. Filter by category (setbacks, heights, parking, etc.)
3. See ACTUAL provision text with:
   - Category tags
   - Extracted numeric values
   - Applicable zones/dev types
   - Link to PDF page
4. Click to view source PDF for citation

### User Needs Analysis

**Finding relevant controls:**
- Filter by category (setbacks, heights, etc.)
- Current approach works for this

**Citing in DA submissions:**
- Need original provision text, not LLM summary
- Current approach fails this

**Verifying numeric compliance:**
- Need extracted values (6m, 9m, 0.5:1)
- Current approach works for this

**Checking source PDF:**
- Need direct, correct page link
- Current approach often broken

**Understanding conditional applicability:**
- Need structured conditionals
- Current approach sometimes captures this

---

## Part 3: Provision Types to Classify

### Type Taxonomy

**CONTROL** - The actual rules
- Pattern: "must", "shall", "minimum", "maximum", "required"
- Example: "Buildings must be setback minimum 6m"
- Primary compliance requirements. Most important for users.

**OBJECTIVE** - The "why" behind the controls
- Pattern: "To ensure...", "To protect...", "Purpose:", "O1:", "O2:"
- Example: "To maintain the established streetscape character"
- Useful context. Helps when seeking variations.

**PERFORMANCE CRITERIA** - Outcome-based alternatives
- Pattern: "PC1:", "Performance Criteria:", "must achieve"
- Example: "Development must achieve adequate visual privacy"
- Important for merit-based assessments.

**DEFINITION** - What terms mean
- Pattern: "means", "includes", "is defined as"
- Example: "Front setback means the distance from..."
- Reference material for interpretation.

**NOTE/EXCEPTION** - Conditional applicability
- Pattern: "Note:", "Except where", "Does not apply to"
- Example: "Note: This control does not apply to heritage items"
- Critical for determining what actually applies.

---

## Part 4: The Enrichment Data Model

### What LLM Should Output

Instead of creating new requirement text, the LLM categorizes and enriches existing provisions:

```json
{
  "provision_id": 87445,
  "original_text": "C4 Buildings must be setback minimum 6m from front boundary...",

  "provision_type": "control",

  "categories": ["setback_front"],
  "subcategory": "minimum",

  "values": {
    "value_min": 6,
    "value_max": null,
    "unit": "m"
  },

  "applicable_zones": ["R2", "R3"],
  "development_types": ["dwelling_house", "dual_occupancy"],

  "has_conditionals": true,
  "conditional_logic": "unless heritage item",

  "page_number": 170,
  "pdf_url": "/pdf-pages/ashfield-chapter-d/page_170.png"
}
```

### Database Schema Changes

For EVERY provision (from rules-based extraction):
```
provision_id
provision_text (original - PRIMARY DISPLAY)
document_id
page_number
pdf_page_image_url

has_numeric_value: boolean
extracted_numbers: jsonb {value: 6, unit: "m", type: "minimum"}
explicit_zones: text[] (if stated in text)
explicit_dev_types: text[] (if stated in text)
```

For CLASSIFIED provisions (from batch LLM):
```
provision_type: control/objective/definition/note/procedural
categories: text[]
```

For INHERITED applicability (from document structure):
```
inherited_zones: text[]
inherited_dev_types: text[]
precinct_id: text (if precinct-specific)
scope: "general" | "precinct"
```

For DEEPLY ENRICHED provisions (selective LLM):
```
conditional_logic: text
cross_references: text[]
applicability_notes: text
```

---

## Part 5: Tiered Extraction Strategy (Volume Efficiency)

### The Volume Problem

Ashfield alone has:
- Chapter D (Precincts): 287 provisions
- Chapter E1 (Heritage): 1,126 provisions
- Chapter F (Development): 73 provisions
- Other chapters: 500+ provisions

Marrickville has 1,000+ provisions. Leichhardt similar.

Processing every provision with full LLM enrichment is expensive, slow, and often unnecessary.

### The Solution: Tiered Processing

**Phase 1: Rules-Based Numeric Extraction (Fast, Free)**

Before any LLM involvement, scan all provisions with regex patterns:

```python
patterns = [
    r"minimum\s+(\d+\.?\d*)\s*(m|metres|meters)",
    r"maximum\s+(\d+\.?\d*)\s*(m|metres|meters|storeys)",
    r"at least\s+(\d+\.?\d*)\s*(m|%|sqm)",
    r"no more than\s+(\d+\.?\d*)",
    r"setback of\s+(\d+\.?\d*)\s*m",
    r"FSR\s+(\d+\.?\d*):1",
    r"height limit\s+(\d+\.?\d*)\s*m"
]
```

This extracts 80% of numeric values without any LLM cost.

Result: Every provision gets `has_numeric_value` flag and `extracted_values` if found.

**Phase 2: Provision Type Classification (Batch LLM)**

Send provisions in large batches (50-100) to LLM with a simple task:

```
For each provision, classify as:
CONTROL | OBJECTIVE | PERFORMANCE_CRITERIA | DEFINITION | NOTE | PROCEDURAL
```

This is fast because it's simple classification, not extraction.

Result: Every provision gets a `provision_type`.

**Phase 3: Zone/DevType Tagging (Rules + LLM Hybrid)**

Many provisions explicitly state applicability:
- "This applies to R2 and R3 zones" - regex catches this
- "For dwelling houses and dual occupancies" - regex catches this

For provisions without explicit tagging, inherit from document structure:
- "Part 4.1: Low Density Residential" → applies to R2, dwelling_house
- "Chapter D8: Summer Hill" → applies to Summer Hill precinct

Only use LLM for ambiguous cases.

**Phase 4: Deep Enrichment (Selective LLM)**

Only fully enrich provisions that are:
- Type = CONTROL
- AND have conditionals OR cross-references OR complex applicability

This is maybe 20% of provisions. The other 80% don't need deep analysis.

### The Efficiency Math

Current approach:
- 2,000 provisions × full LLM enrichment = 2,000 API calls

Smart approach:
- Phase 1 (regex): 2,000 provisions, 0 API calls, instant
- Phase 2 (type classification): 2,000 provisions in 40 batches = 40 API calls
- Phase 3 (zone tagging): 80% rules-based, 20% LLM = ~10 API calls
- Phase 4 (deep enrichment): 400 provisions (20%) in 8 batches = 8 API calls

Total: ~60 API calls vs 2,000. That's 97% reduction.

---

## Part 6: Precinct Integration

### The Regulatory Hierarchy

```
SEPP (State)
    ↓ overrides
LEP (Local Environmental Plan)
    ↓ overrides
DCP General Provisions
    ↓ overrides (if precinct-specific control exists)
DCP Precinct Provisions
```

If property is in Summer Hill precinct:
- Summer Hill provisions apply
- General provisions ALSO apply UNLESS Summer Hill has a specific control on that topic
- Where Summer Hill is silent, general provisions fill the gap

If property is NOT in any precinct:
- Only general provisions apply

### Relationship Types

**Override:**
General: "Front setback minimum 6m"
Precinct: "Front setback minimum 4m for properties fronting Smith Street"
→ For Smith Street properties in Summer Hill, 4m applies, not 6m.

**Supplement:**
General: "Landscaping must cover 30% of site"
Precinct: "In addition, corner sites must provide street tree planting"
→ Both apply. Precinct adds to general requirement.

**Standalone:**
Precinct: "Development must maintain views to the railway heritage corridor"
→ No general equivalent. Unique to precinct.

### Data Model for Precinct Provisions

```
provision_id: 456
provision_text: "Front setback minimum 4m for properties fronting Smith Street"
scope: "precinct"
precinct_id: "summer_hill"
category: "setback_front"
applicable_zones: ["B2"]

relationship_type: "override" | "supplement" | "standalone"
overrides_provision_id: 123  (links to the general provision it replaces)
override_condition: "properties fronting Smith Street"
```

### Override Detection

Text patterns that indicate override:
- "notwithstanding Part F..."
- "instead of the requirements in..."
- "in lieu of..."
- "despite the provisions of..."

Text patterns that indicate supplement:
- "in addition to..."
- "as well as..."
- "supplementary to..."

### Query Logic for Precinct Properties

```sql
-- Step 1: Get applicable general provisions
SELECT * FROM provisions
WHERE scope = 'general'
AND ('B2' = ANY(applicable_zones) OR 'ALL' = ANY(applicable_zones));

-- Step 2: Get applicable precinct provisions
SELECT * FROM provisions
WHERE scope = 'precinct'
AND precinct_id = 'summer_hill'
AND ('B2' = ANY(applicable_zones) OR 'ALL' = ANY(applicable_zones));

-- Step 3: Resolve overrides (application logic)
-- For each category:
--   If precinct has override → show precinct, hide general
--   If precinct has supplement → show both
--   If precinct silent → show general only
```

---

## Part 7: UI Display Strategy

### Current UI (Broken)

```
Category: Setback Front
Requirement: "Minimum front setback: 6m"  ← LLM summary
[View PDF Page] ← often wrong page
Source: 0 provisions ← broken linkage
```

### Optimal UI

```
CONTROL - Front Setback

"C4 Buildings must be setback a minimum of 6 metres from the
front boundary to maintain the established streetscape character
of the area."  ← ACTUAL TEXT

📊 Extracted: minimum 6m
🏗️ Applies to: R2, R3 zones | Dwelling house, Dual occupancy
⚠️ Conditional: Excludes heritage items (see C4.1)

[Objective] "To maintain the established streetscape character..."

📄 Source: Ashfield DCP Ch.D p.170 [View PDF]
```

### Precinct Display

For Summer Hill property, grouped by category:

```
SETBACKS

[PRECINCT - Summer Hill]
"C4 Front setback minimum 4m for properties fronting Smith Street"
Overrides general provision. Applies to: Smith Street frontages only.

[GENERAL - Ashfield LGA]
"Front setback minimum 6m"
Applies to: All other Summer Hill properties not on Smith Street.

---

BUILDING HEIGHT

[PRECINCT - Summer Hill]
"Maximum height 2 storeys to maintain village character"
Overrides general provision.

[GENERAL - Ashfield LGA] (greyed out)
"Maximum height 9m"
Overridden by precinct provision.

---

LANDSCAPING

[GENERAL - Ashfield LGA]
"Landscaping minimum 30% of site"
No precinct override.

[PRECINCT - Summer Hill] (supplement badge)
"Corner sites must provide street tree planting"
Additional requirement.
```

---

## Part 8: Implementation Priorities

### Enrichment Priority Order

1. **Applicability determination** - What properties does this apply to?
2. **Provision type** - Control vs objective vs definition
3. **Scope** - General vs precinct
4. **Category** - Setback, height, parking, etc.
5. **Numeric extraction** - Values, units
6. **Override relationships** - Only for precinct provisions
7. **Conditional logic** - Only for complex provisions

### Processing Priority by Provision Tier

**Tier 1: Numeric Controls** - MOST VALUABLE
- "Minimum setback: 6m", "Maximum height: 9m", "FSR: 0.5:1"
- Calculable. User enters proposal, app can check compliance.
- Full enrichment priority.

**Tier 2: Qualitative Controls** - IMPORTANT
- "Development must be sympathetic to surrounding character"
- Not calculable but still mandatory.
- Type classification + category tagging.

**Tier 3: Objectives** - CONTEXT
- "To maintain streetscape character"
- Useful for variations.
- Type classification only.

**Tier 4: Definitions** - REFERENCE
- "Front setback means the distance from..."
- Lookup material.
- Type classification only.

**Tier 5: Administrative/Procedural** - LOW PRIORITY
- "Applications must be lodged with Council"
- Rarely needed.
- Minimal processing.

---

## Part 9: Key Principles Summary

1. **The provision IS the requirement.** Don't create synthetic text.

2. **Source fidelity is paramount.** Professionals need to cite actual DCP text.

3. **Use rules first, LLM second.** Regex catches 80% of numeric values for free.

4. **Batch classification, selective deep enrichment.** Type-classify everything in batches, only deeply analyze controls with complexity.

5. **Prioritize applicability over categorization.** The most important metadata is "does this apply to my property" not "what category is this."

6. **Precinct provisions must be understood in relationship to general provisions.** They don't exist in isolation - they override, supplement, or stand alone.

7. **Tiered processing for efficiency.** Not all provisions are equal. Process accordingly.

---

## Part 10: Migration Path

### Phase 1: Data Model Changes
- Add new columns to `regulatory_provisions` table
- Keep existing `dcp_*_requirements` tables temporarily

### Phase 2: Rules-Based Enrichment
- Run regex extraction on all provisions
- Populate `has_numeric_value`, `extracted_numbers`

### Phase 3: Batch Classification
- Run LLM batch classification for provision types
- Run LLM batch classification for categories

### Phase 4: Scope and Applicability
- Tag provisions with scope (general/precinct)
- Inherit zone/dev_type from document structure
- Detect override relationships for precinct provisions

### Phase 5: UI Migration
- Update UI to display original provision text as primary
- Show enrichment metadata alongside
- Implement precinct/general resolution logic

### Phase 6: Deprecate Requirements Tables
- Once UI is using enriched provisions, deprecate `dcp_*_requirements`
- All data lives in enriched `regulatory_provisions`

---

## Part 11: DCP Structure Differences (Ashfield, Marrickville, Leichhardt)

### DCP Structure Comparison

**Ashfield DCP 2016:**
```
Chapter A: Miscellaneous
Chapter B: Public Domain
Chapter C: Sustainability
Chapter D: Precinct Guidelines (D1-D12 specific areas)
Chapter E1: Heritage
Chapter F: Development Category (organized BY DEV TYPE)
  - F1: Dwelling Houses
  - F2: Dual Occupancy
  - F3: Multi Dwelling
  - etc.
```

**Marrickville DCP 2011:**
```
Part 1: Statutory Information
Part 2: Generic Provisions
Part 3: Subdivision
Part 4: Residential (organized BY DEV TYPE)
  - 4.1: Low Density
  - 4.2: Multi Dwelling
Part 5: Commercial
Part 6: Industrial
Part 7: Miscellaneous
Part 8: Heritage
Part 9: Precincts (9.1-9.48 specific areas)
```

**Leichhardt DCP 2013:**
```
Part A: Introduction
Part B: Connections
Part C: Place (organized BY TOPIC)
Part D: Energy (organized BY TOPIC)
Part E: Water (organized BY TOPIC)
Part F: Food (organized BY TOPIC)
Part G: Neighbourhoods (G1-G12 specific areas)
```

### Key Differences

**Organization Philosophy:**

Ashfield and Marrickville organize general provisions BY DEVELOPMENT TYPE.
- "This chapter applies to dwelling houses"
- "This part applies to multi-dwelling housing"
- Easy to inherit `applicable_dev_types` from document structure.

Leichhardt organizes general provisions BY TOPIC.
- "Part D: Energy" applies to ALL development types
- "Part E: Water" applies to ALL development types
- Harder to inherit `applicable_dev_types` - most are "ALL".

**Precinct Naming:**
- Ashfield: D1, D2, D3... D12 (12 precincts)
- Marrickville: 9.1, 9.2... 9.48 (48 precincts)
- Leichhardt: G1, G2... G12 (12 neighbourhoods)

Different naming conventions but same concept.

**Control Numbering:**
- Ashfield: "C1", "C2", "C3" style controls
- Marrickville: "4.2.1", "4.2.2" section numbering
- Leichhardt: "PC1", "PC2" performance criteria style

Different patterns for regex extraction.

### What Works Universally

**Provision Type Classification** - YES
Controls, objectives, definitions, notes exist in all DCPs. The patterns are the same:
- "must", "shall" → Control
- "To ensure...", "Purpose:" → Objective
- "means", "includes" → Definition

**Category Tagging** - YES
Setbacks, heights, parking, landscaping exist in all DCPs regardless of how they're organized.

**Numeric Extraction** - YES (with pattern variations)
All DCPs have numeric controls. Regex patterns work universally:
- "minimum X metres" - all DCPs use this
- "maximum Y storeys" - all DCPs use this

**Precinct vs General Scope** - YES
All three have:
- General provisions (apply LGA-wide)
- Precinct provisions (apply to specific areas)

The concept of override/supplement relationships exists in all.

### What Varies By DCP

**Applicability Inheritance:**

```
Ashfield Chapter F1 (Dwelling Houses):
→ Can inherit: applicable_dev_types = ["dwelling_house"]
→ Provisions here automatically apply to dwelling houses

Leichhardt Part D (Energy):
→ Cannot inherit specific dev type
→ applicable_dev_types = ["ALL"] for most provisions
→ Must look at provision text itself for applicability
```

**Document Structure Parsing:**

Each DCP needs its own mapping:

```python
# Ashfield
ASHFIELD_STRUCTURE = {
    "Chapter F1": {"dev_types": ["dwelling_house"]},
    "Chapter F2": {"dev_types": ["dual_occupancy"]},
    "Chapter D": {"scope": "precinct"},
}

# Marrickville
MARRICKVILLE_STRUCTURE = {
    "Part 4.1": {"dev_types": ["dwelling_house"], "zones": ["R2"]},
    "Part 4.2": {"dev_types": ["multi_dwelling_housing"]},
    "Part 9": {"scope": "precinct"},
}

# Leichhardt
LEICHHARDT_STRUCTURE = {
    "Part D": {"topic": "energy", "dev_types": ["ALL"]},
    "Part E": {"topic": "water", "dev_types": ["ALL"]},
    "Part G": {"scope": "precinct"},
}
```

**Precinct ID Extraction:**

```python
# Ashfield - Extract from "D8" → precinct_id = "D8"
# Marrickville - Extract from "9.15" → precinct_id = "9.15"
# Leichhardt - Extract from "G7" → precinct_id = "G7"
```

Different regex patterns needed per DCP.

### Strategy Adaptation

The core strategy works. The implementation needs DCP-specific configuration.

**Phase 1 (Regex Numeric Extraction):**
Same patterns work across all DCPs. No adaptation needed.

**Phase 2 (Type Classification):**
Same LLM prompt works. No adaptation needed.

**Phase 3 (Applicability Tagging):**
NEEDS ADAPTATION per DCP:

```python
def get_inherited_applicability(provision, dcp_type):
    if dcp_type == "ashfield":
        return ashfield_inheritance_rules(provision.document_id)
    elif dcp_type == "marrickville":
        return marrickville_inheritance_rules(provision.document_id)
    elif dcp_type == "leichhardt":
        return leichhardt_inheritance_rules(provision.document_id)
```

**Phase 4 (Deep Enrichment):**
Same approach. Override detection patterns are universal ("notwithstanding", "in lieu of").

### The Leichhardt Challenge

Leichhardt is most different because:

1. Topic-based organization means most provisions apply to ALL dev types
2. Applicability must be determined from provision text, not document structure
3. More work for LLM, less inheritance from structure

**Solution for Leichhardt:**

Since we can't inherit dev_type from structure, we need more text analysis:

```python
# Look for explicit applicability in provision text
patterns = [
    r"for (dwelling houses|residential development)",
    r"applies to (commercial|industrial)",
    r"in (R2|R3|B2) zones",
]
```

If no explicit applicability found, default to "ALL" - which is often correct for Leichhardt's topic-based provisions.

### Implementation Recommendation

**Create DCP-specific configuration files:**

```
config/
  ashfield_dcp_config.py
  marrickville_dcp_config.py
  leichhardt_dcp_config.py
```

Each config contains:
- Document structure mapping
- Precinct ID extraction patterns
- Inheritance rules
- Any DCP-specific regex patterns

**Core processing remains universal:**
- Type classification
- Category tagging
- Numeric extraction
- Override detection

**Applicability logic is DCP-specific:**
- Ashfield: Heavy inheritance from Chapter structure
- Marrickville: Heavy inheritance from Part structure
- Leichhardt: Light inheritance, more text analysis

### Summary

**YES, the strategy works for all three.**

The core approach (provision-based, tiered processing, type classification) is universal.

The adaptation needed is in applicability inheritance - each DCP has different document structure that implies different applicability rules.

This is a configuration problem, not an architecture problem.

---

## Part 12: Migration Preparation (Best Practices)

### Current State Assessment

**Database Tables:**
```
regulatory_provisions     - Raw extracted text from PDFs (SOURCE OF TRUTH)
dcp_general_requirements  - LLM-generated requirements (TO BE DEPRECATED)
dcp_precinct_requirements - LLM-generated precinct requirements (TO BE DEPRECATED)
dcp_precinct_provisions   - Another provisions table (UNCLEAR PURPOSE)
```

**API Routes:**
```
/api/compliance/          - Serves requirements data
/api/compliance/precinct-requirements/
/api/compliance/general-requirements/
```

**UI Components:**
```
CategorizedRequirementsCard - Displays LLM-generated requirements
ComplianceDashboard        - Main compliance view
```

### Recommended Approach: Parallel Build, Not In-Place Migration

**DO NOT** modify existing tables/routes/UI in place.

**Instead:** Build the new system alongside the old, test it, then switch over.

### Database Preparation

**Step 1: Create New Columns on regulatory_provisions**

Don't create new tables. Enrich the existing source table.

```sql
ALTER TABLE regulatory_provisions ADD COLUMN IF NOT EXISTS
  -- Type classification
  provision_type TEXT,  -- control/objective/definition/note/procedural

  -- Categories
  categories TEXT[],

  -- Scope
  scope TEXT,  -- general/precinct
  precinct_id TEXT,

  -- Extracted values
  has_numeric_value BOOLEAN DEFAULT FALSE,
  extracted_values JSONB,  -- {value_min: 6, value_max: null, unit: "m"}

  -- Applicability
  applicable_zones TEXT[],
  applicable_dev_types TEXT[],

  -- Conditionals
  has_conditionals BOOLEAN DEFAULT FALSE,
  conditional_summary TEXT,

  -- Relationships (for precinct provisions)
  relationship_type TEXT,  -- override/supplement/standalone
  overrides_provision_id INTEGER REFERENCES regulatory_provisions(id),

  -- Processing metadata
  enrichment_version TEXT,
  enriched_at TIMESTAMP;
```

**Step 2: Create Migration Tracking Table**

```sql
CREATE TABLE IF NOT EXISTS provision_enrichment_log (
  id SERIAL PRIMARY KEY,
  provision_id INTEGER REFERENCES regulatory_provisions(id),
  phase TEXT,  -- 'numeric', 'type', 'applicability', 'deep'
  status TEXT,  -- 'pending', 'completed', 'failed'
  processed_at TIMESTAMP,
  error_message TEXT
);
```

**Step 3: Backup Current State**

```bash
pg_dump -t regulatory_provisions -t dcp_general_requirements -t dcp_precinct_requirements > backup_before_enrichment.sql
```

### Git Strategy

**Step 1: Create Feature Branch**

```bash
git checkout -b feature/provision-based-architecture
```

**Step 2: Directory Structure for New Code**

```
compliance-engine/
├── enrichment/                    # NEW - Enrichment pipeline
│   ├── __init__.py
│   ├── config/
│   │   ├── ashfield_config.py
│   │   ├── marrickville_config.py
│   │   └── leichhardt_config.py
│   ├── extractors/
│   │   ├── numeric_extractor.py   # Phase 1 - Regex
│   │   ├── type_classifier.py     # Phase 2 - LLM batch
│   │   └── applicability_tagger.py # Phase 3 - Hybrid
│   ├── pipeline.py                # Orchestrates all phases
│   └── tests/
│       ├── test_numeric_extractor.py
│       └── test_type_classifier.py
│
├── frontend-nextjs/
│   ├── app/
│   │   ├── api/
│   │   │   ├── compliance/        # EXISTING - Keep working
│   │   │   └── provisions/        # NEW - New API routes
│   │   │       ├── route.ts
│   │   │       └── [id]/route.ts
│   │   └── assessment/
│   │       ├── page.tsx           # EXISTING - Keep working
│   │       └── v2/                # NEW - New UI
│   │           └── page.tsx
│   └── components/
│       ├── compliance/            # EXISTING - Keep working
│       └── provisions/            # NEW - New components
│           ├── ProvisionCard.tsx
│           └── ProvisionList.tsx
```

**Key principle:** New code goes in new directories. Don't modify existing until ready to switch.

### API Strategy

**Step 1: Create New API Routes (Don't Touch Old Ones)**

```
/api/provisions/                    # NEW - Enriched provisions
/api/provisions/search              # NEW - Search with filters
/api/provisions/[id]                # NEW - Single provision detail

/api/compliance/                    # EXISTING - Keep working
/api/compliance/general-requirements/  # EXISTING - Keep working
```

**Step 2: New API Response Shape**

```typescript
// NEW: /api/provisions/search
{
  "provisions": [
    {
      "id": 87445,
      "text": "C4 Buildings must be setback minimum 6m...",  // ORIGINAL TEXT
      "provision_type": "control",
      "categories": ["setback_front"],
      "scope": "precinct",
      "precinct_id": "D8",
      "extracted_values": {
        "value_min": 6,
        "unit": "m"
      },
      "applicable_zones": ["B2", "B4"],
      "has_conditionals": true,
      "conditional_summary": "Excludes heritage items",
      "page_number": 170,
      "pdf_page_image_url": "/pdf-pages/ashfield-chapter-d/page_170.png",
      "document_id": "Ashfield DCP 2016 Chapter D"
    }
  ],
  "filters_applied": {
    "zone": "B2",
    "precinct": "D8",
    "categories": ["setback_front"]
  }
}
```

**Step 3: Feature Flag for API Switching**

```typescript
// In API route
const USE_NEW_PROVISIONS_API = process.env.USE_PROVISIONS_V2 === 'true';

if (USE_NEW_PROVISIONS_API) {
  return fetchFromEnrichedProvisions(params);
} else {
  return fetchFromLegacyRequirements(params);
}
```

### UI Strategy

**Step 1: Create New Components (Don't Modify Old)**

```
components/
├── compliance/
│   └── CategorizedRequirementsCard.tsx  # EXISTING - Don't touch
│
└── provisions/                          # NEW
    ├── ProvisionCard.tsx                # Shows original text + metadata
    ├── ProvisionList.tsx                # Grouped by category
    ├── ProvisionFilter.tsx              # Zone/DevType/Category filters
    └── PrecinctGeneralResolver.tsx      # Shows precinct vs general
```

**Step 2: New Page Route**

```
/assessment         # EXISTING - Uses old components
/assessment/v2      # NEW - Uses new components
```

**Step 3: A/B Testing Capability**

```typescript
// In assessment page
const { searchParams } = useSearchParams();
const useV2 = searchParams.get('v2') === 'true';

if (useV2) {
  return <ProvisionsBasedAssessment />;
} else {
  return <RequirementsBasedAssessment />;  // Current
}
```

Access new UI at: `/assessment?v2=true`

### Enrichment Pipeline Execution

**Step 1: Run Enrichment in Stages**

```bash
# Phase 1: Numeric extraction (fast, no API cost)
python enrichment/pipeline.py --phase=numeric --council=ashfield

# Phase 2: Type classification (batch LLM)
python enrichment/pipeline.py --phase=type --council=ashfield

# Phase 3: Applicability tagging
python enrichment/pipeline.py --phase=applicability --council=ashfield

# Phase 4: Deep enrichment (selective)
python enrichment/pipeline.py --phase=deep --council=ashfield
```

**Step 2: Validate Each Phase Before Proceeding**

```bash
# After each phase, run validation
python enrichment/validate.py --phase=numeric --council=ashfield
# Output: "Numeric extraction complete: 287/287 provisions processed, 156 with values"
```

**Step 3: Run for Each Council Separately**

```bash
# Ashfield first (smallest, good test)
python enrichment/pipeline.py --all-phases --council=ashfield

# Validate, fix issues

# Then Leichhardt
python enrichment/pipeline.py --all-phases --council=leichhardt

# Then Marrickville (largest)
python enrichment/pipeline.py --all-phases --council=marrickville
```

### Testing Strategy

**Step 1: Unit Tests for Extractors**

```python
# test_numeric_extractor.py
def test_extracts_minimum_metres():
    text = "Buildings must be setback minimum 6 metres"
    result = extract_numeric_values(text)
    assert result == {"value_min": 6, "unit": "m"}

def test_extracts_maximum_storeys():
    text = "Maximum height 3 storeys"
    result = extract_numeric_values(text)
    assert result == {"value_max": 3, "unit": "storeys"}
```

**Step 2: Integration Tests for API**

```typescript
// Test new provisions API
describe('/api/provisions/search', () => {
  it('returns provisions filtered by zone', async () => {
    const res = await fetch('/api/provisions/search?zone=R2');
    const data = await res.json();
    expect(data.provisions.every(p =>
      p.applicable_zones.includes('R2') || p.applicable_zones.includes('ALL')
    )).toBe(true);
  });
});
```

**Step 3: Visual Regression Tests for UI**

Compare `/assessment` (old) vs `/assessment?v2=true` (new) for same address.

### Cutover Strategy

**Step 1: Soft Launch**

```
Week 1: New API and UI available at /v2 routes
Week 2: Internal testing, fix bugs
Week 3: Beta users access new UI
Week 4: Gather feedback, iterate
```

**Step 2: Feature Flag Flip**

```bash
# In production environment
USE_PROVISIONS_V2=true
```

Now `/assessment` uses new system, old is at `/assessment/legacy`.

**Step 3: Deprecation**

```
Month 1: Old routes still work, show deprecation warning
Month 2: Old routes redirect to new
Month 3: Remove old routes, drop old tables
```

### What NOT To Do

- **DON'T** delete existing tables until new system is proven
- **DON'T** modify existing API routes in place
- **DON'T** modify existing UI components in place
- **DON'T** run enrichment on production without backup
- **DON'T** try to migrate everything at once

### Immediate Next Steps

1. **Create backup of current database**

2. **Create feature branch**
```bash
git checkout -b feature/provision-based-architecture
```

3. **Add new columns to regulatory_provisions**

4. **Create enrichment directory structure**

5. **Build Phase 1 numeric extractor with tests**

6. **Run on Ashfield as pilot**

7. **Validate results before proceeding**

---

## Part 13: Legacy vs New Code Management

### The Confusion Risk

**Database:**
- `regulatory_provisions` has existing columns + new enrichment columns
- `dcp_general_requirements` (old) vs new enrichment data
- Which columns are legacy? Which are active?

**Code:**
- Old extraction scripts still in repo
- Old API routes still working
- Old UI components still rendering
- New code alongside - which is which?

**Data:**
- Old LLM-extracted "requirements" in database
- New enrichment metadata on provisions
- Both coexist during transition

### Strategy: Explicit Naming + Deprecation Markers

### Database Naming Convention

**New columns get `v2_` prefix during transition:**

```sql
ALTER TABLE regulatory_provisions ADD COLUMN
  v2_provision_type TEXT,
  v2_categories TEXT[],
  v2_scope TEXT,
  v2_has_numeric_value BOOLEAN,
  v2_extracted_values JSONB,
  v2_applicable_zones TEXT[],
  v2_applicable_dev_types TEXT[],
  v2_enrichment_version TEXT,
  v2_enriched_at TIMESTAMP;
```

**Why v2_ prefix:**
- Immediately clear these are new enrichment columns
- Won't conflict with any existing columns
- Easy to query: `SELECT * WHERE v2_provision_type IS NOT NULL`
- After full migration, can rename to remove prefix

**Legacy tables get comment markers:**

```sql
COMMENT ON TABLE dcp_general_requirements IS
  'DEPRECATED: Legacy LLM-extracted requirements. Use regulatory_provisions.v2_* columns instead.
   Scheduled for removal after migration complete.';

COMMENT ON TABLE dcp_precinct_requirements IS
  'DEPRECATED: Legacy LLM-extracted precinct requirements. Use regulatory_provisions.v2_* columns instead.
   Scheduled for removal after migration complete.';
```

### Code Organization

**Directory structure with explicit separation:**

```
compliance-engine/
├── DEPRECATED/                     # Move old code here, don't delete
│   ├── extraction/
│   │   ├── extract_ashfield_chapter_d_precincts.py
│   │   ├── extract_marrickville_v2_COMPLIANT.py
│   │   └── README.md              # "These scripts created legacy requirements tables"
│   └── README.md                  # "Code in this folder is deprecated"
│
├── enrichment/                    # NEW - clearly named
│   ├── __init__.py
│   ├── extractors/
│   └── pipeline.py
│
├── frontend-nextjs/
│   ├── app/
│   │   ├── api/
│   │   │   ├── compliance/        # LEGACY - add deprecation comments
│   │   │   │   └── route.ts       # Add: // DEPRECATED: Use /api/provisions instead
│   │   │   └── provisions/        # NEW
│   │   └── assessment/
│   │       ├── page.tsx           # LEGACY
│   │       └── v2/
│   │           └── page.tsx       # NEW
│   └── components/
│       ├── compliance/            # LEGACY - add deprecation comments
│       │   └── CategorizedRequirementsCard.tsx  # // DEPRECATED
│       └── provisions/            # NEW
```

### File-Level Deprecation Markers

**Every legacy file gets a header comment:**

```typescript
// frontend-nextjs/app/api/compliance/route.ts

/**
 * @deprecated This API route serves legacy LLM-extracted requirements.
 * Use /api/provisions instead which serves enriched provisions.
 *
 * Migration status: DEPRECATED
 * Replacement: /api/provisions/search
 *
 * DO NOT ADD NEW FEATURES TO THIS FILE.
 */
```

```python
# extract_ashfield_chapter_d_precincts.py

"""
DEPRECATED: This script creates legacy dcp_precinct_requirements records.

This extraction approach has been replaced by the provision enrichment pipeline.
See: enrichment/pipeline.py

Migration status: DEPRECATED
Replacement: enrichment/pipeline.py --council=ashfield

DO NOT USE THIS SCRIPT FOR NEW EXTRACTIONS.
"""
```

### Database Query Helpers

**Create views that make the distinction clear:**

```sql
-- View for new system
CREATE VIEW v2_enriched_provisions AS
SELECT
  id,
  provision_text,
  document_id,
  page_number,
  pdf_page_image_url,
  v2_provision_type AS provision_type,
  v2_categories AS categories,
  v2_scope AS scope,
  v2_extracted_values AS extracted_values,
  v2_applicable_zones AS applicable_zones,
  v2_applicable_dev_types AS applicable_dev_types
FROM regulatory_provisions
WHERE v2_enriched_at IS NOT NULL;

-- View that clearly labels legacy data
CREATE VIEW legacy_requirements AS
SELECT
  id,
  requirement_text,
  category,
  'LEGACY - Use v2_enriched_provisions instead' AS migration_note
FROM dcp_general_requirements;
```

### API Response Headers

**Legacy APIs return deprecation warning:**

```typescript
// In legacy API route
export async function GET(request: Request) {
  // Set deprecation header
  const response = NextResponse.json(data);
  response.headers.set('Deprecation', 'true');
  response.headers.set('Link', '</api/provisions>; rel="successor-version"');

  return response;
}
```

### Environment Variables for Routing

```bash
# .env

# Which system to use (for gradual rollout)
USE_PROVISIONS_V2=false          # false = legacy, true = new

# Feature flags for specific components
V2_GENERAL_REQUIREMENTS=false    # Use new for general requirements?
V2_PRECINCT_REQUIREMENTS=false   # Use new for precinct requirements?
V2_UI_COMPONENTS=false           # Use new UI components?
```

### Migration Status Tracking

**Create a migration status table:**

```sql
CREATE TABLE migration_status (
  component TEXT PRIMARY KEY,
  status TEXT,  -- 'legacy', 'migrating', 'v2', 'deprecated'
  legacy_location TEXT,
  v2_location TEXT,
  notes TEXT,
  updated_at TIMESTAMP DEFAULT NOW()
);

INSERT INTO migration_status VALUES
  ('general_requirements_api', 'legacy', '/api/compliance/general-requirements', '/api/provisions/search?scope=general', 'Migration in progress'),
  ('precinct_requirements_api', 'legacy', '/api/compliance/precinct-requirements', '/api/provisions/search?scope=precinct', 'Not started'),
  ('requirements_ui', 'legacy', 'CategorizedRequirementsCard.tsx', 'ProvisionCard.tsx', 'Not started'),
  ('ashfield_data', 'migrating', 'dcp_*_requirements', 'regulatory_provisions.v2_*', 'Phase 1 complete');
```

### Documentation

**Create a MIGRATION_STATUS.md in repo root:**

```markdown
# Migration Status: Requirements → Provisions

## Overview
We are migrating from LLM-extracted "requirements" to enriched "provisions".

## Status by Component

| Component | Status | Legacy Location | New Location |
|-----------|--------|-----------------|--------------|
| General Requirements API | DEPRECATED | /api/compliance/general-requirements | /api/provisions/search |
| Precinct Requirements API | DEPRECATED | /api/compliance/precinct-requirements | /api/provisions/search |
| Requirements UI | DEPRECATED | CategorizedRequirementsCard | ProvisionCard |
| Ashfield Data | MIGRATING | dcp_*_requirements | regulatory_provisions.v2_* |

## How to Know Which System You're Using

**Database:**
- Legacy: Tables named `dcp_*_requirements`
- New: Columns prefixed with `v2_` on `regulatory_provisions`

**API:**
- Legacy: Routes under `/api/compliance/*`
- New: Routes under `/api/provisions/*`

**UI:**
- Legacy: Components in `components/compliance/`
- New: Components in `components/provisions/`

## DO NOT
- Add features to legacy code
- Create new legacy-style extractions
- Query legacy tables for new features
```

### Quick Reference Summary

**Database:**
- Legacy tables: `dcp_general_requirements`, `dcp_precinct_requirements`
- New columns: `v2_*` prefix on `regulatory_provisions`
- New views: `v2_enriched_provisions`

**API Routes:**
- Legacy: `/api/compliance/*`
- New: `/api/provisions/*`

**UI Components:**
- Legacy: `components/compliance/`
- New: `components/provisions/`

**Python Scripts:**
- Legacy: `DEPRECATED/` folder
- New: `enrichment/` folder

**File Markers:**
- Legacy: `@deprecated` docstring at top
- New: Normal (no deprecation marker)

---

## Part 14: Execution Steps (Getting Started)

### Prerequisites Checklist

Before starting migration:
- [ ] This strategy document committed to repo
- [ ] Database backup created
- [ ] Feature branch created
- [ ] Team notified of migration plan (if applicable)

### Phase 0: Setup (Do First)

**Step 0.1: Commit this strategy document**
```bash
git add PROVISION_BASED_ARCHITECTURE_STRATEGY.md
git commit -m "docs: Add provision-based architecture strategy document"
```

**Step 0.2: Create feature branch**
```bash
git checkout -b feature/provision-based-architecture
```

**Step 0.3: Create database backup**
```bash
# Using pg_dump
pg_dump $SUPABASE_DB_URL > backups/pre_v2_migration_$(date +%Y%m%d).sql

# Or using Python backup script
python backup_db_now.py
```

### Phase 1: Schema Changes

**Step 1.1: Create migration SQL file**

Create file: `migrations/001_add_v2_enrichment_columns.sql`

```sql
-- Add v2 enrichment columns to regulatory_provisions
ALTER TABLE regulatory_provisions
ADD COLUMN IF NOT EXISTS v2_provision_type TEXT,
ADD COLUMN IF NOT EXISTS v2_categories TEXT[],
ADD COLUMN IF NOT EXISTS v2_scope TEXT,
ADD COLUMN IF NOT EXISTS v2_precinct_id TEXT,
ADD COLUMN IF NOT EXISTS v2_has_numeric_value BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS v2_extracted_values JSONB,
ADD COLUMN IF NOT EXISTS v2_applicable_zones TEXT[],
ADD COLUMN IF NOT EXISTS v2_applicable_dev_types TEXT[],
ADD COLUMN IF NOT EXISTS v2_has_conditionals BOOLEAN DEFAULT FALSE,
ADD COLUMN IF NOT EXISTS v2_conditional_summary TEXT,
ADD COLUMN IF NOT EXISTS v2_relationship_type TEXT,
ADD COLUMN IF NOT EXISTS v2_overrides_provision_id INTEGER,
ADD COLUMN IF NOT EXISTS v2_enrichment_version TEXT,
ADD COLUMN IF NOT EXISTS v2_enriched_at TIMESTAMP;

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_v2_provision_type ON regulatory_provisions(v2_provision_type);
CREATE INDEX IF NOT EXISTS idx_v2_scope ON regulatory_provisions(v2_scope);
CREATE INDEX IF NOT EXISTS idx_v2_precinct_id ON regulatory_provisions(v2_precinct_id);
CREATE INDEX IF NOT EXISTS idx_v2_categories ON regulatory_provisions USING GIN(v2_categories);
CREATE INDEX IF NOT EXISTS idx_v2_applicable_zones ON regulatory_provisions USING GIN(v2_applicable_zones);
CREATE INDEX IF NOT EXISTS idx_v2_enriched_at ON regulatory_provisions(v2_enriched_at);

-- Add deprecation comments to legacy tables
COMMENT ON TABLE dcp_general_requirements IS
  'DEPRECATED: Use regulatory_provisions.v2_* columns instead';
COMMENT ON TABLE dcp_precinct_requirements IS
  'DEPRECATED: Use regulatory_provisions.v2_* columns instead';
```

**Step 1.2: Run migration**
```bash
psql $SUPABASE_DB_URL -f migrations/001_add_v2_enrichment_columns.sql
```

**Step 1.3: Verify columns added**
```sql
SELECT column_name FROM information_schema.columns
WHERE table_name = 'regulatory_provisions' AND column_name LIKE 'v2_%';
```

### Phase 2: Build Enrichment Pipeline

**Step 2.1: Create directory structure**
```bash
mkdir -p enrichment/extractors enrichment/config enrichment/tests
touch enrichment/__init__.py
touch enrichment/extractors/__init__.py
touch enrichment/config/__init__.py
```

**Step 2.2: Build numeric extractor (Phase 1 - no LLM)**

Create `enrichment/extractors/numeric_extractor.py` with regex patterns for:
- Minimum/maximum values
- Units (m, metres, storeys, %, sqm)
- FSR ratios
- Height limits

**Step 2.3: Build tests**

Create `enrichment/tests/test_numeric_extractor.py` with test cases:
- "minimum 6 metres" → {value_min: 6, unit: "m"}
- "maximum 3 storeys" → {value_max: 3, unit: "storeys"}
- "FSR 0.5:1" → {fsr: 0.5}
- Edge cases and failures

**Step 2.4: Run tests**
```bash
pytest enrichment/tests/test_numeric_extractor.py -v
```

### Phase 3: Pilot on Ashfield

**Step 3.1: Run numeric extraction on Ashfield only**
```bash
python enrichment/pipeline.py --phase=numeric --council=ashfield --dry-run
# Review output
python enrichment/pipeline.py --phase=numeric --council=ashfield
```

**Step 3.2: Verify results**
```sql
SELECT COUNT(*),
       COUNT(v2_has_numeric_value) as enriched,
       SUM(CASE WHEN v2_has_numeric_value THEN 1 ELSE 0 END) as with_values
FROM regulatory_provisions
WHERE document_id LIKE '%Ashfield%';
```

**Step 3.3: Build type classifier (Phase 2 - batch LLM)**

Create `enrichment/extractors/type_classifier.py` for:
- Classifying: CONTROL, OBJECTIVE, DEFINITION, NOTE, PROCEDURAL
- Batch processing (50 provisions per call)

**Step 3.4: Run type classification on Ashfield**
```bash
python enrichment/pipeline.py --phase=type --council=ashfield
```

**Step 3.5: Verify type classification**
```sql
SELECT v2_provision_type, COUNT(*)
FROM regulatory_provisions
WHERE document_id LIKE '%Ashfield%' AND v2_provision_type IS NOT NULL
GROUP BY v2_provision_type;
```

### Phase 4: Expand to Other Councils

After Ashfield is validated:

```bash
# Leichhardt
python enrichment/pipeline.py --all-phases --council=leichhardt

# Marrickville (largest - do last)
python enrichment/pipeline.py --all-phases --council=marrickville
```

### Phase 5: Build New API

**Step 5.1: Create new API route**

Create `frontend-nextjs/app/api/provisions/search/route.ts`

**Step 5.2: Test new API**
```bash
curl "http://localhost:3000/api/provisions/search?zone=R2&council=ashfield"
```

### Phase 6: Build New UI

**Step 6.1: Create new components**
- `components/provisions/ProvisionCard.tsx`
- `components/provisions/ProvisionList.tsx`

**Step 6.2: Create v2 assessment page**

Create `frontend-nextjs/app/assessment/v2/page.tsx`

**Step 6.3: Test at `/assessment?v2=true`**

### Phase 7: Cutover

**Step 7.1: Flip feature flag**
```bash
# .env.production
USE_PROVISIONS_V2=true
```

**Step 7.2: Monitor for issues**

**Step 7.3: Deprecate old routes (after stability confirmed)**

### Rollback Plan

If issues occur at any phase:

**Database rollback:**
```bash
psql $SUPABASE_DB_URL -f backups/pre_v2_migration_YYYYMMDD.sql
```

**Code rollback:**
```bash
git checkout main
```

**Feature flag rollback:**
```bash
USE_PROVISIONS_V2=false
```

### Success Criteria

Migration is complete when:
- [ ] All provisions have v2_provision_type populated
- [ ] All provisions have v2_categories populated
- [ ] Numeric controls have v2_extracted_values
- [ ] New API returns correct filtered results
- [ ] New UI displays original provision text
- [ ] PDF page links work correctly
- [ ] Legacy tables can be dropped without impact

---

*Document created: 2024-11-22*
*Last updated: 2024-11-22*
*Purpose: Reference for provision-based architecture implementation*
