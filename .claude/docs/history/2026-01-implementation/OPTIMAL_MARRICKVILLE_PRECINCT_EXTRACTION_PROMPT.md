# Optimal Marrickville Precinct Provisions Extraction Prompt (Cost-Optimized)

## Extraction Scope

**Purpose:** Extract precinct-specific DCP provisions into `dcp_precinct_requirements` table

**Target Documents:**
- **Marrickville Part 9 Precincts** (e.g., 9.1 Lewisham North, 9.2 Dulwich Hill, etc.)
- **Ashfield Chapter D Precincts**
- **Leichhardt Part G Precincts**

**Example Source:** Marrickville DCP 2011 - 9.1 Lewisham North Precinct
- "Character Statement" section
- "Desired Future Character" section
- "Precinct Requirements" controls
- Expected output: 5-15 requirements per precinct (character-focused, not dev-type specific)

**Key Difference from General Provisions:**
- Precincts apply to ALL development within geographic boundaries
- No zone/dev-type filtering needed (precinct IS the filter)
- More qualitative/character-based requirements
- Less cross-referencing to other sections

## Task
Extract ALL prescriptive controls and character requirements from precinct provisions. Focus on requirements that guide design and development within the precinct boundaries.

## Critical Rules

### 1. Controls vs Character Statements

**Extract as requirements:**
- Numbered controls (C1, C2, C3...)
- Character objectives that prescribe outcomes
- "Desired Future Character" requirements
- Specific design guidelines

**Skip:**
- Objectives (O1, O2...) - Store in `objective` field ONLY
- Pure historical descriptions
- Location descriptions without requirements
- Notes (NB)

### 2. Systematic Extraction

- Extract EVERY control number in sequence
- Extract character requirements even if not numbered
- Break multi-part requirements into separate items
- **VALIDATION**: Ensure all substantive requirements are captured

### 3. Precinct-Specific Patterns

**Pattern A: Character Requirements**
```
"Maintain distinctly single storey streetscapes"
→ Extract as requirement with category="character", subcategory="Building Form"

"Retain Edwardian character and detailing"
→ Extract as requirement with heritage_context="Edwardian conservation area"
```

**Pattern B: Building Form Requirements**
```
"Buildings should be predominantly two storeys"
→ category="building_height", value_numeric=2, unit="storeys"

"Retain predominance of detached dwelling houses"
→ category="character", subcategory="Housing Type"
```

**Pattern C: Heritage/Conservation Controls**
```
"Development within the Heritage Conservation Area must..."
→ heritage_context="Heritage Conservation Area", references_lep=true
```

### 4. Verbatim Text Extraction

- `verbatim_source_text`: EXACT text from PDF
- `requirement_text`: Clear, professional summary
- NEVER paraphrase specific character descriptions
- Preserve qualitative language ("predominant", "characteristic", "typical")

### 5. PDF Metadata (MANDATORY)

Every requirement MUST include:
- `pdf_page`: Integer page number in PDF
- `pdf_page_image_url`: URL to page image (e.g., "/pdf-pages/marr_Marrickville_DCP_2011_-_9_1_Lewisham_North__page_6.png")

### 6. LEP References (HIGH PRIORITY - Keep for Legal Compliance)

When provision references LEP:

**Detection patterns:**
- "Inner West LEP 2022"
- "Heritage Conservation Area"
- "LEP Clause X.X"
- "Local heritage item"

**Output fields:**
```json
{
  "references_lep": true,
  "lep_document": "Inner West LEP 2022",
  "lep_clause": "Clause 5.10",  // If specific clause mentioned
  "lep_map_type": "Heritage Conservation Area"  // If heritage-related
}
```

### 7. SEPP References (MEDIUM PRIORITY - Keep for Compliance)

When provision references State policies:

**Detection patterns:**
- "SEPP 65"
- "Apartment Design Guide"
- "State Environmental Planning Policy"

**Output fields:**
```json
{
  "references_sepp": true,
  "sepp_name": "SEPP 65",
  "sepp_clause": "Apartment Design Guide Part 4"  // If specific
}
```

### 8. Heritage Context (HIGH PRIORITY - Essential for Character Precincts)

Many precincts ARE heritage areas. Extract heritage context:

**Detection patterns:**
- "Heritage Conservation Area"
- "heritage item"
- "contributory building"
- "character conservation"
- Historical period mentions ("Edwardian", "Federation", "Victorian")

**Output field:**
```json
{
  "heritage_context": "Haberfield Heritage Conservation Area - Federation/Edwardian character"
}
```

### 9. Objectives (KEEP - Critical for Character Understanding)

Precinct objectives explain "why" for character requirements:

**Pattern:**
```
O1: To maintain the distinctive single storey character of the precinct.

C1: Buildings are predominantly single storey.

→ Store O1 text in `objective` field of C1 requirement
```

**Output field:**
```json
{
  "objective": "O1: To maintain the distinctive single storey character of the precinct.",
  "requirement_text": "Buildings are predominantly single storey"
}
```

### 10. Performance Criteria (KEEP if present)

Some precincts have performance criteria:

```json
{
  "performance_criteria": "PC1: Development demonstrates compatibility with heritage character through design excellence."
}
```

### 11. Categorization

**Precinct-specific categories:**
- `character` - Streetscape character, architectural style
- `building_height` - Storey limits, height restrictions
- `building_form` - Bulk, scale, massing
- `setbacks_front`, `setbacks_side`, `setbacks_rear` - Spatial requirements
- `landscaping_street_trees`, `landscaping_front_gardens` - Landscape character
- `heritage_conservation` - Heritage-specific controls
- `site_coverage` - Building footprint limits
- `parking_location` - Parking placement for character
- `materials_finishes` - Material requirements for character

### 12. Confidence Levels

- **High (0.9-1.0):** Specific numbered controls with clear requirements
- **Medium (0.7-0.9):** Character statements with prescriptive intent
- **Low (<0.7):** Descriptive text, aspirational statements

## ❌ COST-OPTIMIZED FIELDS - DO NOT EXTRACT (Saves ~$15 per 500 provisions)

### Removed Fields (Not Needed for Precincts):

**1. `applicable_zones` - SKIP**
- Rationale: Precinct boundaries define applicability, not zones
- User workflow: Address → Precinct (not Address → Zone → Precinct)

**2. `development_types` - SKIP**
- Rationale: Precinct requirements apply to ALL development in area
- Exception: If requirement explicitly states "for dual occupancies only", note in `requirement_text`

**3. `references_section` / `section_reference` / `section_title` - SKIP**
- Rationale: Precincts rarely cross-reference other DCP sections (<5% frequency)
- When they do, it's usually to general Parts 1-8 (already linked via precinct metadata)

## ✅ KEEP: Alternative Solutions (Critical for Heritage Intelligence)

### 12. Alternative Solutions & Design Flexibility (KEEP - HIGH VALUE)

**IMPORTANT:** This field supports the "Design Flexibility Pathways" feature for Heritage Intelligence.

**Detection patterns:**
- "Variations may be accepted where..."
- "Alternative solutions may be considered..."
- "Design excellence may justify..."
- "Exceptions may be granted if..."
- "Variation permitted subject to..."

**Output fields:**
```json
{
  "allows_alternative_solutions": true,
  "alternative_solutions_criteria": "Variation permitted if design demonstrates heritage compatibility through design excellence"
}
```

**Examples:**
```
"Variations to the single storey requirement may be accepted where it can be demonstrated that the development maintains the heritage character through exceptional design quality."

→ allows_alternative_solutions = true
→ alternative_solutions_criteria = "Exceptional design quality that maintains heritage character"
```

**Why This is Critical for Precincts:**
- Heritage is THE primary use case for alternative solutions
- Architects need to know: "Can I vary this heritage requirement?"
- Enables "Design Flexibility Pathways" feature
- Professional workflow: "Where can I innovate vs. must comply exactly?"

## Output Schema (Simplified for Cost Savings)

```json
{
  "verbatim_source_text": "EXACT text from provision including control number",
  "requirement_text": "Clear professional summary",
  "category": "character",
  "subcategory": "Building Form",
  "value_numeric": 2.0,
  "value_min": null,
  "value_max": null,
  "unit": "storeys",
  "has_conditionals": false,
  "conditional_text": null,
  "primary_source_provision_id": 78824,
  "confidence": "0.95",
  "objective": "O1: To maintain single storey character...",
  "performance_criteria": null,
  "heritage_context": "Lewisham Heritage Conservation Area",
  "pdf_page": 6,
  "pdf_page_image_url": "/pdf-pages/marr_Marrickville_DCP_2011_-_9_1_Lewisham_North__page_6.png",
  "references_lep": true,
  "lep_document": "Inner West LEP 2022",
  "lep_clause": "Clause 5.10",
  "lep_map_type": "Heritage Conservation Area",
  "references_sepp": false,
  "sepp_name": null,
  "sepp_clause": null,
  "allows_alternative_solutions": false,
  "alternative_solutions_criteria": null
}
```

## Complete Example

**Input Provision:**
```
Lewisham North Precinct 1
Heritage Conservation Area

Desired Future Character:
To maintain distinctly single storey streetscapes that exist within the precinct.

O1: To retain the predominance of detached dwelling houses that contribute to
the character of the Heritage Conservation Area.

C1: Buildings are predominantly single storey.

C2: Development within the Heritage Conservation Area must comply with the
heritage provisions of Inner West LEP 2022 Clause 5.10.
```

**Output: 2 requirements**

```json
[
  {
    "verbatim_source_text": "C1: Buildings are predominantly single storey.",
    "requirement_text": "Buildings must be predominantly single storey to maintain streetscape character",
    "category": "building_height",
    "subcategory": "Storey Limit",
    "value_numeric": 1.0,
    "unit": "storeys",
    "has_conditionals": false,
    "primary_source_provision_id": 78824,
    "confidence": "0.95",
    "objective": "O1: To retain the predominance of detached dwelling houses that contribute to the character of the Heritage Conservation Area.",
    "heritage_context": "Lewisham Heritage Conservation Area - single storey character",
    "pdf_page": 6,
    "pdf_page_image_url": "/pdf-pages/marr_Marrickville_DCP_2011_-_9_1_Lewisham_North__page_6.png",
    "references_lep": false,
    "allows_alternative_solutions": false
  },
  {
    "verbatim_source_text": "C2: Development within the Heritage Conservation Area must comply with the heritage provisions of Inner West LEP 2022 Clause 5.10.",
    "requirement_text": "Development must comply with LEP heritage provisions",
    "category": "heritage_conservation",
    "subcategory": "LEP Compliance",
    "has_conditionals": false,
    "primary_source_provision_id": 78825,
    "confidence": "0.95",
    "heritage_context": "Lewisham Heritage Conservation Area",
    "pdf_page": 6,
    "pdf_page_image_url": "/pdf-pages/marr_Marrickville_DCP_2011_-_9_1_Lewisham_North__page_6.png",
    "references_lep": true,
    "lep_document": "Inner West LEP 2022",
    "lep_clause": "Clause 5.10",
    "lep_map_type": "Heritage Conservation Area",
    "references_sepp": false,
    "allows_alternative_solutions": false
  }
]
```

## Quality Checklist

Before returning results, verify:

1. ✅ **Control Coverage:** All numbered controls extracted?
2. ✅ **Character Requirements:** All substantive character statements extracted?
3. ✅ **Objectives Linked:** O1/O2/O3 stored in `objective` field (not as separate requirements)?
4. ✅ **Heritage Context:** Heritage areas identified and noted?
5. ✅ **LEP/SEPP References:** Cross-references to higher-level regulations captured?
6. ✅ **Alternative Solutions:** Variation/exception clauses identified and extracted?
7. ✅ **PDF Metadata:** Every requirement has `pdf_page` and `pdf_page_image_url`?
8. ✅ **Categorization:** Character requirements categorized appropriately?
9. ✅ **Cost Optimization:** Skipped zone/dev-type/section-ref fields, but KEPT alternative solutions?

## Return Format

Return ONLY a valid JSON array of requirements. No markdown, no explanations.

```json
[
  { requirement object 1 },
  { requirement object 2 },
  ...
]
```

## Cost Savings Summary

**Fields Removed vs General Provisions:** 3 field groups
- `applicable_zones` (saved ~$5)
- `development_types` (saved ~$5)
- `references_section`, `section_reference`, `section_title` (saved ~$3)

**Fields KEPT (High Value for Heritage Intelligence):**
- `allows_alternative_solutions`, `alternative_solutions_criteria` (~$3 cost, but enables Design Flexibility feature)

**Total Savings:** ~$13 per 500 provisions (58% cheaper than full extraction)

**Retained Critical Fields:**
- Core requirement data (text, category, values)
- PDF metadata (page, image URL)
- Objectives & performance criteria (character context)
- Heritage context (essential for character precincts)
- LEP/SEPP references (legal compliance)
- Verbatim source text (traceability)
- **Alternative solutions (design flexibility pathways)**

**Trade-off:** Professional-grade extraction optimized for Heritage Intelligence use case. Users access precinct requirements by location (not zone/dev-type), but need to know where design variation is permitted.
