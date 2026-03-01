# Optimal Marrickville DCP Extraction Prompt

## Extraction Scope

**Purpose:** Extract general (non-precinct-specific) DCP provisions into `dcp_general_requirements` table

**Target Documents:**
- **Marrickville Parts 1-8** (Priority 1): Introduction, Heritage, Parking, Residential Development, Waste, Signage, Subdivision, Other
- **Ashfield Chapter F** (Priority 2): Development Categories (F1-F7)
- **Leichhardt Parts A-F** (Priority 3): General Controls

**Example Source:** Marrickville DCP 2011 - 4.1 Low Density Residential Development
- Section 4.1.6 "Built form and character" (page 11)
- Expected output: 28+ separate requirements from C7-C13 with all sub-items

## Task
Extract ALL prescriptive controls from the given DCP provision text. You must systematically enumerate EVERY control (C1, C2, C3...) and EVERY sub-item (i., ii., iii..., a., b., c...) as separate requirements.

## Critical Rules

### 1. Controls vs Objectives
- **Controls** (C1, C2, C3...) → Extract as requirements
- **Objectives** (O1, O2, O3...) → Store in `objective` field, NOT as separate requirements
- **Notes** (NB) → Skip entirely

### 2. Systematic Extraction (100% Coverage Required)
- Extract EVERY control number in sequence (if you see C7, C8, C9, you must extract all three)
- Extract EVERY sub-item as a separate requirement:
  - C8 with sub-items i., ii., iii. → Create 3 separate requirements (C8i, C8ii, C8iii)
  - Sub-item with further breakdown a., b., c. → Each is separate (C10ia, C10ib, C10ic)
- If a control has no sub-items, extract it as a single requirement
- **VALIDATION**: Count controls in source text, verify count matches output requirements

### 3. Requirement Identification Pattern
```
C7
Maximum permissible FSR and height...
→ Extract as requirement: "C7 - Maximum permissible FSR and height..."

C8
Notwithstanding compliance...:
i. Overshadowing and privacy;
ii. Streetscape (bulk and scale);
iii. Building setbacks;
→ Extract as 3 separate requirements:
  - "C8i - Overshadowing and privacy"
  - "C8ii - Streetscape (bulk and scale)"
  - "C8iii - Building setbacks"

C10 Secondary dwellings
i. Front setback:
a. Secondary dwellings must be located behind...
b. On corner lots...
→ Extract as separate requirements:
  - "C10i - Front setback for secondary dwellings"
  - "C10ia - Secondary dwellings must be located behind..."
  - "C10ib - On corner lots..."
```

### 4. Verbatim Text Extraction
- `verbatim_source_text`: EXACT text from PDF including control number
- `requirement_text`: Clear, professional summary preserving all specifics
- NEVER paraphrase numeric values, dimensions, or thresholds
- NEVER lose conditional context (e.g., "for corner lots", "where there is rear lane access")

**IMPORTANT for sub-items:** Include FULL parent control text in verbatim:
```
WRONG:
"verbatim_source_text": "C8\n\nii. Streetscape (bulk and scale);"

RIGHT:
"verbatim_source_text": "C8 Notwithstanding compliance with the numerical standards, applicants must demonstrate that the bulk and relative mass of development is acceptable for the street and adjoining dwellings in terms of:\n\nii. Streetscape (bulk and scale);"
```

### 5. PDF Metadata (MANDATORY)
Every requirement MUST include:
- `pdf_page`: Integer page number in PDF
- `pdf_page_image_url`: URL to page image

### 6. DCP Section Cross-References (VERY HIGH VALUE - 50% frequency)
When a requirement refers to another DCP section:

**Detection patterns:**
- "Section X.X"
- "Part X"
- "Chapter X"
- "refer Section X.X"
- "refer to Section X.X"

**Output fields:**
```json
{
  "references_section": true,
  "section_reference": "Section 2.9",
  "section_title": "Community Safety"  // If mentioned in text, otherwise null
}
```

**Examples:**
```
Text: "For details refer Section 2.9 (Community Safety) of this DCP"
Output:
{
  "requirement_text": "Refer to DCP Section 2.9 (Community Safety)",
  "references_section": true,
  "section_reference": "Section 2.9",
  "section_title": "Community Safety"
}

Text: "Development must comply with Part 4"
Output:
{
  "requirement_text": "Development must comply with DCP Part 4",
  "references_section": true,
  "section_reference": "Part 4",
  "section_title": null
}
```

### 7. LEP References (MEDIUM VALUE - 13% frequency)
When a requirement references the Local Environment Plan or LEP maps:

**Detection patterns:**
- "LEP", "MLEP", "ILEP", "Inner West LEP"
- "Height of Buildings Map" or "HOB Map"
- "FSR Map"
- "Clause X.X" (when referring to LEP)

**Output fields:**
```json
{
  "references_lep": true,
  "lep_document": "MLEP 2011",  // or "Inner West LEP 2022"
  "lep_clause": "5.4",  // If specific clause mentioned
  "lep_map_type": "Height of Buildings"  // If map mentioned
}
```

**Examples:**
```
Text: "Maximum FSR and height must be consistent with the Height of Buildings (HOB) and FSR Maps of MLEP 2011"
Output:
{
  "requirement_text": "Maximum FSR and height per MLEP 2011 HOB and FSR Maps",
  "references_lep": true,
  "lep_document": "MLEP 2011",
  "lep_clause": null,
  "lep_map_type": "Height of Buildings, FSR"
}

Text: "See Clause 5.4 of Inner West LEP 2022"
Output:
{
  "requirement_text": "Refer to Inner West LEP 2022 Clause 5.4",
  "references_lep": true,
  "lep_document": "Inner West LEP 2022",
  "lep_clause": "5.4",
  "lep_map_type": null
}
```

### 8. SEPP References (MEDIUM VALUE - 3% frequency)
When a requirement references a State Environmental Planning Policy:

**Detection patterns:**
- "SEPP"
- "State Environmental Planning Policy"
- "Affordable Housing SEPP"
- "BASIX SEPP"

**Output fields:**
```json
{
  "references_sepp": true,
  "sepp_name": "Affordable Rental Housing SEPP 2009",
  "sepp_clause": null  // If specific clause mentioned
}
```

**Examples:**
```
Text: "State Environmental Planning Policy (Affordable Rental Housing) 2009 (Affordable Housing SEPP) may override DCP controls"
Output:
{
  "requirement_text": "Affordable Housing SEPP 2009 may override DCP controls",
  "references_sepp": true,
  "sepp_name": "Affordable Rental Housing SEPP 2009",
  "sepp_clause": null
}

Text: "Building Sustainability Index: BASIX) 2004 (BASIX SEPP) requires..."
Output:
{
  "requirement_text": "BASIX SEPP 2004 sustainability requirements apply",
  "references_sepp": true,
  "sepp_name": "BASIX SEPP 2004",
  "sepp_clause": null
}
```

### 9. Categorization
Use these categories ONLY:
- building_form, setbacks, parking, landscaping, heritage, sustainability, signage, subdivision, other

Subcategories (examples):
- building_form: height, fsr, site_coverage, building_envelope
- setbacks: front_setback, side_setback, rear_setback, building_separation
- heritage: hca_controls, heritage_items, streetscape_character

### 10. Value Extraction
- `value_numeric`: Single value (e.g., "6 metres" → 6)
- `value_min`: Minimum in range (e.g., "4-6 metres" → 4)
- `value_max`: Maximum in range (e.g., "4-6 metres" → 6)
- `unit`: metres, sqm, storeys, percent, degrees, etc.

### 13. Conditionals
- `has_conditionals`: true if requirement has "if", "where", "for", "on sites", etc.
- `conditional_text`: EXACT conditions (e.g., "for corner lots where there is consistent secondary boundary setback")

### 14. Applicability
- `applicable_zones`: Array of zone codes (e.g., ["R2", "R3", "B1"])
- `development_types`: Array of types (e.g., ["dwelling_house", "attached_dwelling", "multi_dwelling_housing"])
- If not specified in provision, leave arrays empty []

## Output Format

Return ONLY valid JSON (no markdown, no code fences, no explanations):

```json
[
  {
    "verbatim_source_text": "C7\n\nMaximum permissible FSR and height for any development must be consistent with the height and FSR standards prescribed on the Height of Buildings (HOB) and FSR Maps of MLEP 2011.",
    "requirement_text": "Maximum permissible floor space ratio (FSR) and height must be consistent with MLEP 2011 Height of Buildings Map and FSR Map standards",
    "category": "building_form",
    "subcategory": "height_and_fsr",
    "value_numeric": null,
    "value_min": null,
    "value_max": null,
    "unit": null,
    "has_conditionals": false,
    "conditional_text": null,
    "applicable_zones": [],
    "development_types": [],
    "primary_source_provision_id": 78507,
    "confidence": 0.95,
    "objective": "O10: To ensure development is of a scale and form that enhances the character and quality of streetscapes",
    "performance_criteria": null,
    "heritage_context": null,
    "allows_alternative_solutions": false,
    "alternative_solutions_criteria": null,
    "pdf_page": 11,
    "pdf_page_image_url": "https://example.com/page-11.png",
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
    "references_lep": true,
    "lep_document": "MLEP 2011",
    "lep_clause": null,
    "lep_map_type": "Height of Buildings, FSR",
    "references_sepp": false,
    "sepp_name": null,
    "sepp_clause": null
  },
  {
    "verbatim_source_text": "C8\n\nNotwithstanding compliance with the numerical standards, applicants must demonstrate that the bulk and relative mass of development is acceptable for the street and adjoining dwellings in terms of:\n\ni. Overshadowing and privacy;",
    "requirement_text": "C8i - Development must demonstrate acceptable bulk and mass in terms of overshadowing and privacy impacts on adjoining dwellings",
    "category": "building_form",
    "subcategory": "bulk_and_scale",
    "value_numeric": null,
    "value_min": null,
    "value_max": null,
    "unit": null,
    "has_conditionals": true,
    "conditional_text": "notwithstanding compliance with numerical standards",
    "applicable_zones": [],
    "development_types": ["dwelling_house", "attached_dwelling", "semi_detached_dwelling"],
    "primary_source_provision_id": 78507,
    "confidence": 0.95,
    "objective": null,
    "performance_criteria": "bulk and relative mass acceptable for street and adjoining dwellings",
    "heritage_context": null,
    "allows_alternative_solutions": true,
    "alternative_solutions_criteria": "demonstrate acceptable impact on overshadowing and privacy",
    "pdf_page": 11,
    "pdf_page_image_url": "https://example.com/page-11.png",
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
  },
  {
    "verbatim_source_text": "C10\n\nii. Side setback must be determined in accordance with the following table:",
    "requirement_text": "Side setback determined per table",
    "category": "setbacks",
    "subcategory": "side_setback",
    "value_numeric": null,
    "value_min": null,
    "value_max": null,
    "unit": null,
    "has_conditionals": false,
    "conditional_text": null,
    "applicable_zones": [],
    "development_types": ["dwelling_house", "attached_dwelling", "semi_detached_dwelling"],
    "primary_source_provision_id": 78507,
    "confidence": 0.95,
    "objective": null,
    "performance_criteria": null,
    "heritage_context": null,
    "allows_alternative_solutions": false,
    "alternative_solutions_criteria": null,
    "pdf_page": 11,
    "pdf_page_image_url": "https://example.com/page-11.png",
    "references_table": true,
    "table_location": "following",
    "table_page": 11,
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
]
```

## Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| verbatim_source_text | string | YES | EXACT text from PDF including control number |
| requirement_text | string | YES | Clear summary preserving all specifics |
| category | string | YES | One of: building_form, setbacks, parking, landscaping, heritage, sustainability, signage, subdivision, other |
| subcategory | string | NO | Specific type within category |
| value_numeric | float | NO | Single numeric value |
| value_min | float | NO | Minimum in range |
| value_max | float | NO | Maximum in range |
| unit | string | NO | Unit of measurement |
| has_conditionals | boolean | YES | Whether requirement has conditions |
| conditional_text | string | NO | Exact conditional text if present |
| applicable_zones | array | YES | Zone codes (empty if not specified) |
| development_types | array | YES | Development types (empty if not specified) |
| primary_source_provision_id | integer | YES | Database ID of source provision |
| confidence | float | YES | 0.0-1.0 confidence score |
| objective | string | NO | Related objective text (O1, O2...) |
| performance_criteria | string | NO | Performance outcome sought |
| heritage_context | string | NO | Heritage-specific context if applicable |
| allows_alternative_solutions | boolean | YES | Whether alternatives are acceptable |
| alternative_solutions_criteria | string | NO | Criteria for alternative solutions |
| pdf_page | integer | YES | Page number in PDF |
| pdf_page_image_url | string | YES | URL to page image |
| references_table | boolean | YES | Whether requirement references a table |
| table_location | string | NO | "following", "above", "page X" |
| table_page | integer | NO | Page number where table is located |
| references_figure | boolean | YES | Whether requirement references a figure/diagram |
| figure_number | string | NO | Figure number (e.g., "5", "3.2") |
| figure_description | string | NO | Description of figure if provided |
| figure_page | integer | NO | Page number where figure appears |
| references_section | boolean | YES | Whether requirement references another DCP section |
| section_reference | string | NO | Section reference (e.g., "Section 2.9", "Part 4") |
| section_title | string | NO | Title of referenced section if provided |
| references_lep | boolean | YES | Whether requirement references LEP |
| lep_document | string | NO | LEP name (e.g., "MLEP 2011", "Inner West LEP 2022") |
| lep_clause | string | NO | Specific LEP clause if mentioned |
| lep_map_type | string | NO | Type of LEP map (e.g., "Height of Buildings", "FSR") |
| references_sepp | boolean | YES | Whether requirement references SEPP |
| sepp_name | string | NO | SEPP name (e.g., "Affordable Rental Housing SEPP 2009") |
| sepp_clause | string | NO | Specific SEPP clause if mentioned |

## Pre-Submission Validation Checklist

Before returning your JSON output, verify:

- [ ] Extracted ALL controls in sequence (no gaps in C1, C2, C3... numbering)
- [ ] Extracted EVERY sub-item as separate requirement (i., ii., iii... / a., b., c...)
- [ ] Count of output requirements matches count of controls + sub-items in source
- [ ] NO objectives (O1, O2...) in output array (they go in `objective` field only)
- [ ] NO notes (NB) in output
- [ ] Every requirement has pdf_page, pdf_page_image_url
- [ ] Table references detected and flagged with references_table: true
- [ ] Table page set correctly (same as pdf_page for "following", or extracted page number)
- [ ] All numeric values preserved exactly (no rounding or approximation)
- [ ] All conditional context preserved (no loss of "where", "if", "for" clauses)
- [ ] JSON is valid (no trailing commas, proper escaping, balanced braces)
- [ ] Output is pure JSON only (no markdown formatting, no explanations)

## Example Input/Output

**Input Provision Text:**
```
4.1.6.2 Building setbacks

Objectives

O13 To ensure adequate separation between buildings for visual and acoustic privacy, solar access and air circulation.

Controls

C10 Attached dwellings, dwelling houses and semi-detached dwellings

i. Front setback must be:

a. Consistent with the setback of adjoining development or the dominant setback found along the street; and
b. On corner lots where there is a consistent secondary boundary setback to buildings on opposite street corners, reflected in the design of any proposal.

ii. Side setback must be determined in accordance with the following table:

C11 Secondary dwellings

i. Front setback for new, detached secondary dwellings

a. Secondary dwellings must be located behind the front building line of the principal dwelling;
b. On corner lots where there is a consistent secondary boundary setback to buildings on opposite street corners, be reflected in the design of any proposal;
```

**Expected Output Count:**
- C10ia → 1 requirement
- C10ib → 1 requirement
- C10ii → 1 requirement (references table)
- C11ia → 1 requirement
- C11ib → 1 requirement
- **Total: 5 requirements** (NOT 2, NOT 3)

Objective O13 goes in `objective` field of related requirements, NOT as separate requirement.

## Error Prevention

### Common Mistakes to Avoid:
❌ Extracting only "interesting" controls (must extract ALL)
❌ Combining sub-items into parent control (each sub-item is separate)
❌ Extracting objectives as requirements (they're context only)
❌ Losing conditional context in summaries
❌ Approximating numeric values
❌ Forgetting PDF metadata fields
❌ Returning markdown-formatted JSON instead of pure JSON
❌ Using unicode characters that cause encoding errors (stick to ASCII)

### Correct Approach:
✅ Systematic enumeration of every control number
✅ Each sub-item becomes separate requirement
✅ Objectives in `objective` field only
✅ Preserve all conditional context
✅ Exact numeric values
✅ All PDF metadata present
✅ Table references flagged with references_table: true
✅ Table page set to pdf_page for "following table" references
✅ Pure JSON output only
✅ ASCII-safe text encoding
