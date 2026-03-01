# Optimal Ashfield DCP Extraction Prompt

## Extraction Scope

**Purpose:** Extract general (non-precinct-specific) Ashfield DCP provisions into `dcp_general_requirements` table

**Target Documents:**
- **Ashfield Chapter A** (Priority 1): Miscellaneous/General Controls - 256 provisions
- **Ashfield Chapter C** (Priority 2): Sustainability - 221 provisions
- **Ashfield Chapter B** (Priority 3): Public Domain - 9 provisions
- **Ashfield Chapter E1** (Selective): Heritage - Only provisions with DS/PC codes

**Example Source:** Ashfield DCP 2016 - Chapter F Part 1 - Dwelling Houses
- DS8.2 "Minimum landscaped area complies with the table below:"
- DS9.1 "Principal private open space is directly accessible..."
- Expected output: 6-10 requirements per DS code with all bullet points

## Task
Extract ALL Design Standards (DS codes) and Performance Criteria (PC codes) from the given Ashfield DCP provision text. You must systematically enumerate EVERY DS/PC code and EVERY bullet point as separate requirements.

## Critical Rules

### 1. Ashfield Code System

**Design Standards (DS)** - Prescriptive Requirements:
- Format: `DS[number].[sub-number]` (e.g., DS8.1, DS8.2, DS11.1)
- These are concrete, measurable requirements
- Extract as individual requirements

**Performance Criteria (PC)** - Performance-Based Objectives:
- Format: `PC[number]` or `PC[number].[sub-number]` (e.g., PC1, PC2, PC5, PC1.1)
- These are objectives/outcomes (similar to Marrickville's O codes)
- Store in `objective` field when they appear with DS codes
- Extract as separate requirements when they stand alone

**Key Difference from Marrickville:**
- ❌ NO C1/C2/C3 codes
- ❌ NO O1/O2/O3 codes
- ✅ DS codes = Concrete requirements
- ✅ PC codes = Performance objectives

### 2. Systematic Extraction (100% Coverage Required)
- Extract EVERY DS code in the provision (DS8.1, DS8.2, DS8.3... DS11.1, DS11.3...)
- Extract EVERY bullet point (�) under a DS code as a separate requirement
- Extract EVERY PC code as either an objective or standalone requirement
- **VALIDATION**: Count DS codes in source text, verify count matches output requirements

### 3. Requirement Identification Pattern

**Pattern 1: DS Code with Single Requirement**
```
DS8.1 A Landscape Concept Plan is to be prepared and submitted
      with the development application

→ Extract as: "DS8.1 - Landscape Concept Plan submission"
```

**Pattern 2: DS Code with Bullet Points (EACH BULLET = SEPARATE REQUIREMENT)**
```
DS11.1 Siting of a building appropriately responds to factors such as:
� lot size and shape
� good streetscape principles
� solar access for varying orientations
� visual and acoustic privacy
� the need for planting to screen developments

→ Extract as 5 separate requirements:
  - "DS11.1a - Lot size and shape consideration"
  - "DS11.1b - Good streetscape principles"
  - "DS11.1c - Solar access for varying orientations"
  - "DS11.1d - Visual and acoustic privacy"
  - "DS11.1e - Planting to screen developments"
```

**Pattern 3: DS Code with Table Reference**
```
DS8.2 Minimum landscaped area complies with the table below:

→ Extract as: "DS8.2 - Minimum landscaped area (see table)"
→ Set: references_table=true, table_location="below"
```

**Pattern 4: PC Code with Bullet Points**
```
PC1. Development is located to:
� avoid clustering of drive-in take-away food outlets
� not compromise employment uses within business zones
� not cause traffic issues

→ Extract as 3 separate requirements:
  - "PC1a - Avoid clustering of drive-in take-away outlets"
  - "PC1b - Not compromise employment uses"
  - "PC1c - Not cause traffic issues"
```

**Pattern 5: Prohibitive Requirements (NOT/MUST NOT)**
```
DS1.1 Development is not located:
� within 200m of another drive-in take-away food outlet
� on corner sites visible from residential zones

→ Extract as 2 separate requirements:
  - "DS1.1a - Not within 200m of similar use"
  - "DS1.1b - Not on corner sites visible from residential"
```

### 4. Ashfield-Specific Language Patterns

**Pattern A: "Development is [verb]..."**
```
"Development is not located within..."
"Development is sited and designed to..."
"Development is located to avoid..."
```

**Pattern B: "[Thing] is to be..."**
```
"A Landscape Concept Plan is to be prepared..."
"Minimum landscaped area is to comply..."
```

**Pattern C: "[Thing] appropriately responds to..."**
```
"Siting appropriately responds to factors such as:"
```

**Pattern D: Site requirements**
```
"Site have a minimum frontage of 100 metres"
"Sites must be a minimum of 450 m²"
```

**Pattern E: Compliance references**
```
"complies with the table below"
"compliance with SEPP 65"
"in accordance with the Apartment Design Guide"
```

### 5. Bullet Point Handling (CRITICAL FOR ASHFIELD)

**Bullet Character:** Ashfield uses `�` (NOT `•`)

**Each bullet = separate requirement:**
```
DS11.1 Siting appropriately responds to:
� lot size and shape           → DS11.1a
� good streetscape principles  → DS11.1b
� solar access                 → DS11.1c
� visual and acoustic privacy  → DS11.1d
� planting to screen           → DS11.1e
� daylight and ventilation     → DS11.1f
� obstruction of views         → DS11.1g
� SEPP 65 compliance           → DS11.1h (also set references_sepp=true)
```

**Result:** 8 separate requirements from one DS code

### 6. Verbatim Text Extraction

- `verbatim_source_text`: EXACT text from PDF including DS/PC code
- `requirement_text`: Clear, professional summary preserving all specifics
- NEVER paraphrase numeric values, dimensions, or thresholds
- NEVER lose conditional context

**For bullet points, include parent DS text:**
```
RIGHT:
"verbatim_source_text": "DS11.1 Siting of a building appropriately responds to factors such as:\n\n� solar access for varying orientations"

"requirement_text": "Siting must respond to solar access for varying orientations"
```

### 7. PDF Metadata (MANDATORY)
Every requirement MUST include:
- `pdf_page`: Integer page number in PDF
- `pdf_page_image_url`: URL to page image (e.g., "/pdf-pages/Ashfield_Chapter_A_page_15.png")

### 8. Table References (15% frequency in Ashfield)

**Detection patterns:**
- "complies with the table below"
- "in accordance with the following table"
- "must be determined by table"
- "see table"

**Output fields:**
```json
{
  "references_table": true,
  "table_location": "below",  // or "above", "following", "page X"
  "table_page": 15
}
```

### 9. Figure References (10% frequency)

**Detection patterns:**
- "Figure [number]"
- "see diagram"
- "as shown in Figure"

**Output fields:**
```json
{
  "references_figure": true,
  "figure_number": "3",
  "figure_description": "Site layout for corner lots",
  "figure_page": 22
}
```

### 10. Section Cross-References (30% frequency - HIGH in Ashfield)

**Detection patterns:**
- "Section [number]"
- "Part [letter/number]"
- "refer to Section"
- "see Section [X] � Design Checklist"

**Output fields:**
```json
{
  "references_section": true,
  "section_reference": "Section 5",
  "section_title": "Design Checklist 1"
}
```

**Examples:**
```
"reference should also be made to Section 1�Preliminary"
→ references_section=true, section_reference="Section 1", section_title="Preliminary"

"as indicated by Section 5 � Design Checklist 1"
→ references_section=true, section_reference="Section 5", section_title="Design Checklist 1"
```

### 11. LEP References (10% frequency)

**Detection patterns:**
- "Inner West LEP 2022"
- "Haberfield Conservation Area which has its specific controls in the Inner West LEP 2022"

**Output fields:**
```json
{
  "references_lep": true,
  "lep_document": "Inner West LEP 2022",
  "lep_clause": null,
  "lep_map_type": "Heritage Conservation Area"
}
```

### 12. SEPP References (20% frequency - VERY HIGH in Ashfield!)

**Ashfield heavily references SEPP 65 and Apartment Design Guide**

**Detection patterns:**
- "SEPP 65"
- "Design Quality of Residential Flat Development"
- "Apartment Design Guide"
- "ADG"

**Output fields:**
```json
{
  "references_sepp": true,
  "sepp_name": "SEPP 65 (Design Quality of Residential Flat Development)",
  "sepp_clause": "Apartment Design Guide Part 4"
}
```

**Special case - ADG references:**
```
"compliance with the provisions of SEPP 65 and the requirements
of the accompanying Apartment Design Guide"

→ references_sepp=true
→ sepp_name="SEPP 65 (Design Quality of Residential Flat Development)"
→ sepp_clause="Apartment Design Guide"
```

### 13. Heritage Chapter Filtering

**Chapter E1 has 1,126 provisions - MOSTLY descriptive/historical text**

**Skip provisions that:**
- Have NO DS or PC codes
- Are purely descriptive (e.g., "The building applications describe...")
- Are historical narratives
- Are image captions

**Only extract provisions with:**
- DS codes
- PC codes
- Clear prescriptive language ("must", "is to be", "minimum")

### 14. Conditional Text Handling

**Ashfield uses many variations/exceptions:**

**Pattern: "Variations may be accepted..."**
```
DS8.4 Variations to the minimum landscaped area requirements
      may be accepted in cases where it is necessary to meet
      heritage conservation criterion.

→ has_conditionals=true
→ conditional_text="Variations may be accepted for heritage conservation"
```

**Pattern: "This clause applies to..."**
```
DS8.2 Minimum landscaped area complies with the table below:

This clause applies to Heritage Items and sites within Heritage
Conservation Areas, but does not include the Haberfield Conservation Area...

→ has_conditionals=true
→ conditional_text="Applies to Heritage Items and HCAs except Haberfield"
```

### 15. Categorization (Same as Marrickville)

Use standard categories:
- `building_height`
- `setbacks_front`, `setbacks_side`, `setbacks_rear`
- `landscaping_deep_soil`, `landscaping_open_space_private`
- `site_area`, `site_coverage`
- `parking_car_spaces`, `parking_bicycle`
- `sustainability_solar`, `sustainability_water`
- etc.

### 16. Confidence Levels

**High (>90%):**
- DS codes with numeric values
- Table references
- Clear SEPP 65 references

**Medium (70-90%):**
- DS codes with bullet points (qualitative)
- PC performance criteria
- Conditional clauses

**Low (<70%):**
- Descriptive text without DS/PC codes
- Narrative sections
- Heritage chapter historical content

## Output Schema

```json
{
  "verbatim_source_text": "EXACT text from provision including DS/PC code",
  "requirement_text": "Clear professional summary",
  "category": "primary_category",
  "subcategory": "specific_type",
  "value_numeric": 20.0,
  "value_min": null,
  "value_max": null,
  "unit": "m²",
  "has_conditionals": false,
  "conditional_text": null,
  "applicable_zones": [],
  "development_types": [],
  "primary_source_provision_id": 76557,
  "confidence": "high",
  "objective": null,
  "performance_criteria": null,
  "heritage_context": null,
  "allows_alternative_solutions": false,
  "alternative_solutions_criteria": null,
  "pdf_page": 15,
  "pdf_page_image_url": "/pdf-pages/Ashfield_Chapter_F_page_15.png",
  "references_table": false,
  "table_location": null,
  "table_page": null,
  "references_figure": false,
  "figure_number": null,
  "figure_description": null,
  "figure_page": null,
  "references_section": false,
  "section_reference": null,
  "section_title": null,
  "references_lep": false,
  "lep_document": null,
  "lep_clause": null,
  "lep_map_type": null,
  "references_sepp": false,
  "sepp_name": null,
  "sepp_clause": null
}
```

## Complete Example

**Input Provision:**
```
DS11.1 Siting of a building appropriately responds to factors such as:

� lot size and shape
� good streetscape principles (i.e. being similar to typical
  setbacks in the street, front and side)
� solar access for varying orientations
� visual and acoustic privacy
� the need for planting to screen and soften developments
� the need to provide an open and attractive outlook to new
  and existing dwellings
� the need to achieve minimum standards of daylight and ventilation
� obstruction of views
� compliance with the provisions of SEPP 65 (Design Quality of
  Residential Flat Development) and the requirements of the
  accompanying Apartment Design Guide
```

**Output: 9 separate requirements**

```json
[
  {
    "verbatim_source_text": "DS11.1 Siting of a building appropriately responds to factors such as:\n\n� lot size and shape",
    "requirement_text": "Building siting must respond to lot size and shape",
    "category": "building_siting",
    "subcategory": "Lot Size Consideration",
    "primary_source_provision_id": 76560,
    "confidence": "medium",
    "pdf_page": 35,
    "pdf_page_image_url": "/pdf-pages/Ashfield_Chapter_F_page_35.png"
  },
  {
    "verbatim_source_text": "DS11.1 Siting of a building appropriately responds to factors such as:\n\n� good streetscape principles (i.e. being similar to typical setbacks in the street, front and side)",
    "requirement_text": "Building siting must follow good streetscape principles, matching typical setbacks",
    "category": "building_siting",
    "subcategory": "Streetscape Alignment",
    "primary_source_provision_id": 76560,
    "confidence": "medium",
    "pdf_page": 35,
    "pdf_page_image_url": "/pdf-pages/Ashfield_Chapter_F_page_35.png"
  },
  {
    "verbatim_source_text": "DS11.1 Siting of a building appropriately responds to factors such as:\n\n� solar access for varying orientations",
    "requirement_text": "Building siting must respond to solar access for varying orientations",
    "category": "solar_access",
    "subcategory": "Site Orientation",
    "primary_source_provision_id": 76560,
    "confidence": "medium",
    "pdf_page": 35,
    "pdf_page_image_url": "/pdf-pages/Ashfield_Chapter_F_page_35.png"
  },
  // ... (6 more requirements for remaining bullets)
  {
    "verbatim_source_text": "DS11.1 Siting of a building appropriately responds to factors such as:\n\n� compliance with the provisions of SEPP 65 (Design Quality of Residential Flat Development) and the requirements of the accompanying Apartment Design Guide",
    "requirement_text": "Building siting must comply with SEPP 65 and Apartment Design Guide",
    "category": "sepp_compliance",
    "subcategory": "SEPP 65 Compliance",
    "primary_source_provision_id": 76560,
    "confidence": "high",
    "pdf_page": 35,
    "pdf_page_image_url": "/pdf-pages/Ashfield_Chapter_F_page_35.png",
    "references_sepp": true,
    "sepp_name": "SEPP 65 (Design Quality of Residential Flat Development)",
    "sepp_clause": "Apartment Design Guide"
  }
]
```

## Quality Checklist

Before returning results, verify:

1. ✅ **DS Code Coverage:** Found ~80% of provisions have DS codes?
2. ✅ **Bullet Explosion:** Each bullet point extracted as separate requirement?
3. ✅ **PC Handling:** PC codes stored in `objective` OR extracted as requirements?
4. ✅ **Reference Detection:**
   - Tables: ~15% of requirements
   - SEPP refs: ~20% (higher than Marrickville!)
   - Section cross-refs: ~30%
5. ✅ **PDF Metadata:** Every requirement has `pdf_page` and `pdf_page_image_url`?
6. ✅ **Verbatim Text:** Includes full parent DS/PC text for bullet points?
7. ✅ **Conditionals:** Extracted variations/exceptions to `conditional_text`?

## Return Format

Return ONLY a valid JSON array of requirements. No markdown, no explanations.

```json
[
  { requirement object 1 },
  { requirement object 2 },
  ...
]
```
