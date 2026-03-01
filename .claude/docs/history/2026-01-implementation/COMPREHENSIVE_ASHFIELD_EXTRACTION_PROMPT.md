# Comprehensive Ashfield DCP Extraction Prompt
**Based on:** OPTIMAL_ASHFIELD_EXTRACTION_PROMPT.md + OPTIMAL_MARRICKVILLE_EXTRACTION_PROMPT.md
**Created:** 2025-11-02
**Purpose:** Extract ALL fields including references (tables, figures, sections, LEP, SEPP)

---

## Ashfield DCP Structure

**Format:** Performance-based system with DS/PC codes (NOT C/O codes like Marrickville)

- **DS codes** = Design Standards (prescriptive requirements like C1, C2, C3 in Marrickville)
- **PC codes** = Performance Criteria (objectives like O1, O2, O3 in Marrickville)
- **Bullet character:** � (NOT •)
- **Each bullet point = separate requirement**

---

## Extraction Rules

### 1. DS/PC Code System

**Extract as requirements:**
- DS codes (e.g., DS8.1, DS8.2, DS11.1) - prescriptive standards
- DS codes with bullet points - each bullet is a SEPARATE requirement
- Standalone PC codes - when they're not just context

**Store as objectives:**
- PC codes when they appear alongside DS codes (similar to O1/O2 in Marrickville)

**Example:**
```
DS11.1 Siting appropriately responds to:
� lot size and shape           → Extract as DS11.1a
� solar access                 → Extract as DS11.1b
� SEPP 65 compliance           → Extract as DS11.1c (also set references_sepp=true)
```

### 2. PDF Metadata (MANDATORY)

Every requirement MUST include:
- `pdf_page`: Integer page number
- `pdf_page_image_url`: URL to page image

### 3. Table References (3.4% frequency - 55 of 1,622 provisions)

**Detection patterns:**
- "complies with the table below"
- "in accordance with the following table"
- "must be determined by table"
- "see table"
- "Table"

**Output fields:**
```json
{
  "references_table": true,
  "table_location": "below",
  "table_page": 15
}
```

**Examples:**
```
"DS8.2 Minimum landscaped area complies with the table below:"
→ references_table=true, table_location="below", table_page=[same as pdf_page]

"Parking rates per table on page 47"
→ references_table=true, table_location="page 47", table_page=47
```

### 4. Figure References (1.0% frequency - 16 of 1,622 provisions)

**Detection patterns:**
- "Figure [number]" or "Fig. [number]"
- "(Figure X)"
- "as shown in Figure X"
- "see diagram"

**Output fields:**
```json
{
  "references_figure": true,
  "figure_number": "5",
  "figure_description": "Site layout diagram",
  "figure_page": 22
}
```

### 5. Section Cross-References (21.3% frequency - HIGH - 345 of 1,622 provisions)

**Detection patterns:**
- "Section [number]"
- "Part [letter/number]"
- "refer to Section"
- "see Section [X] – Design Checklist"
- "reference should also be made to Section 1–Preliminary"

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
"reference should also be made to Section 1–Preliminary"
→ references_section=true, section_reference="Section 1", section_title="Preliminary"

"as indicated by Section 5 – Design Checklist 1"
→ references_section=true, section_reference="Section 5", section_title="Design Checklist 1"
```

### 6. LEP References (18.9% frequency - HIGH - 307 of 1,622 provisions)

**Detection patterns:**
- "Inner West LEP 2022"
- "Ashfield LEP"
- "LEP"
- "Heritage Conservation Area" (HCA)
- "HCA"
- "Height of Buildings Map"
- "FSR Map"

**Output fields:**
```json
{
  "references_lep": true,
  "lep_document": "Inner West LEP 2022",
  "lep_clause": null,
  "lep_map_type": "Heritage Conservation Area"
}
```

### 7. SEPP References (0.9% frequency - LOW - 14 of 1,622 provisions)

**Note:** SEPP 65/ADG references are RARE in Ashfield (not 20% as initially claimed)

**Detection patterns:**
- "SEPP 65"
- "SEPP"
- "Design Quality of Residential Flat Development"
- "Apartment Design Guide"
- "ADG"
- "compliance with the provisions of SEPP 65"

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

### 8. Heritage Conservation Areas (HCA) - Ashfield Specific

**Detection patterns:**
- "Within [HCA Name] HCA"
- "Heritage Conservation Area"
- "Applies to Heritage Items and HCAs except Haberfield"
- Specific HCA names: Edwin Street North, Summer Hill Central

**Output fields:**
```json
{
  "applicable_hcas": ["Edwin Street North HCA"],
  "heritage_context": "Applies to Heritage Items and HCAs except Haberfield"
}
```

### 9. Verbatim Text for Bullet Points

**CRITICAL:** For bullet-point requirements, include FULL parent DS text in verbatim:

**WRONG:**
```json
"verbatim_source_text": "� solar access for varying orientations"
```

**RIGHT:**
```json
"verbatim_source_text": "DS11.1 Siting of a building appropriately responds to factors such as:\n\n� solar access for varying orientations"
```

---

## Complete Output Schema

Every requirement must return:

```json
{
  "verbatim_source_text": "EXACT text including DS/PC code and full context",
  "requirement_text": "Clear professional summary",
  "category": "setback_front|setback_side|setback_rear|building_height|building_form|site_coverage|parking|landscaping|deep_soil|tree_preservation|character|heritage|streetscape|privacy|solar_access|water_management|stormwater|waste_management|energy_efficiency|contamination|fencing|signage|subdivision|accessibility|acoustic|safety|da_requirements|sustainability|biodiversity|environmental|other",
  "subcategory": "optional specific type",
  "value_numeric": null,
  "value_min": null,
  "value_max": null,
  "unit": "m|sqm|%|hours|etc",
  "has_conditionals": false,
  "conditional_text": null,
  "applicable_zones": ["ALL"],
  "development_types": ["ALL"],
  "applicable_hcas": null,
  "primary_source_provision_id": 12345,
  "confidence": "high|medium|low",
  "objective": null,
  "performance_criteria": null,
  "heritage_context": null,
  "allows_alternative_solutions": false,
  "alternative_solutions_criteria": null,
  "pdf_page": 15,
  "pdf_page_image_url": "/pdf-pages/Ashfield_Chapter_A_page_15.png",
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

---

## Complete Example (Ashfield DS Code with Bullet Points)

**Input:**
```
DS11.1 Siting of a building appropriately responds to factors such as:

� lot size and shape
� good streetscape principles (i.e. being similar to typical setbacks in the street, front and side)
� solar access for varying orientations
� compliance with the provisions of SEPP 65 (Design Quality of Residential Flat Development) and the requirements of the accompanying Apartment Design Guide
```

**Output (4 separate requirements):**

```json
[
  {
    "verbatim_source_text": "DS11.1 Siting of a building appropriately responds to factors such as:\n\n� lot size and shape",
    "requirement_text": "Building siting must respond to lot size and shape",
    "category": "building_form",
    "subcategory": "siting",
    "value_numeric": null,
    "value_min": null,
    "value_max": null,
    "unit": null,
    "has_conditionals": false,
    "conditional_text": null,
    "applicable_zones": ["ALL"],
    "development_types": ["ALL"],
    "applicable_hcas": null,
    "primary_source_provision_id": 76560,
    "confidence": "medium",
    "objective": null,
    "performance_criteria": "Siting appropriately responds to site characteristics",
    "heritage_context": null,
    "allows_alternative_solutions": false,
    "alternative_solutions_criteria": null,
    "pdf_page": 35,
    "pdf_page_image_url": "/pdf-pages/Ashfield_Chapter_F_page_35.png",
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
    "verbatim_source_text": "DS11.1 Siting of a building appropriately responds to factors such as:\n\n� good streetscape principles (i.e. being similar to typical setbacks in the street, front and side)",
    "requirement_text": "Building siting must follow good streetscape principles, matching typical setbacks",
    "category": "streetscape",
    "subcategory": "siting_alignment",
    "value_numeric": null,
    "value_min": null,
    "value_max": null,
    "unit": null,
    "has_conditionals": false,
    "conditional_text": null,
    "applicable_zones": ["ALL"],
    "development_types": ["ALL"],
    "applicable_hcas": null,
    "primary_source_provision_id": 76560,
    "confidence": "medium",
    "objective": null,
    "performance_criteria": "Siting respects streetscape character",
    "heritage_context": null,
    "allows_alternative_solutions": false,
    "alternative_solutions_criteria": null,
    "pdf_page": 35,
    "pdf_page_image_url": "/pdf-pages/Ashfield_Chapter_F_page_35.png",
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
    "verbatim_source_text": "DS11.1 Siting of a building appropriately responds to factors such as:\n\n� solar access for varying orientations",
    "requirement_text": "Building siting must respond to solar access for varying orientations",
    "category": "solar_access",
    "subcategory": "site_orientation",
    "value_numeric": null,
    "value_min": null,
    "value_max": null,
    "unit": null,
    "has_conditionals": false,
    "conditional_text": null,
    "applicable_zones": ["ALL"],
    "development_types": ["ALL"],
    "applicable_hcas": null,
    "primary_source_provision_id": 76560,
    "confidence": "medium",
    "objective": null,
    "performance_criteria": "Siting optimizes solar access",
    "heritage_context": null,
    "allows_alternative_solutions": false,
    "alternative_solutions_criteria": null,
    "pdf_page": 35,
    "pdf_page_image_url": "/pdf-pages/Ashfield_Chapter_F_page_35.png",
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
    "verbatim_source_text": "DS11.1 Siting of a building appropriately responds to factors such as:\n\n� compliance with the provisions of SEPP 65 (Design Quality of Residential Flat Development) and the requirements of the accompanying Apartment Design Guide",
    "requirement_text": "Building siting must comply with SEPP 65 and Apartment Design Guide requirements",
    "category": "sustainability",
    "subcategory": "sepp_compliance",
    "value_numeric": null,
    "value_min": null,
    "value_max": null,
    "unit": null,
    "has_conditionals": false,
    "conditional_text": null,
    "applicable_zones": ["ALL"],
    "development_types": ["ALL"],
    "applicable_hcas": null,
    "primary_source_provision_id": 76560,
    "confidence": "high",
    "objective": null,
    "performance_criteria": "Compliance with SEPP 65 design quality principles",
    "heritage_context": null,
    "allows_alternative_solutions": false,
    "alternative_solutions_criteria": null,
    "pdf_page": 35,
    "pdf_page_image_url": "/pdf-pages/Ashfield_Chapter_F_page_35.png",
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
    "references_sepp": true,
    "sepp_name": "SEPP 65 (Design Quality of Residential Flat Development)",
    "sepp_clause": "Apartment Design Guide"
  }
]
```

---

## Field Extraction Priority (Based on ACTUAL Database Analysis)

**HIGH PRIORITY (extract whenever present):**
1. `references_section` (21.3% in Ashfield - HIGH VALUE!)
2. `references_lep` (18.9% in Ashfield - HIGH VALUE!)
3. `pdf_page`, `pdf_page_image_url` (MANDATORY)
4. `verbatim_source_text` (MANDATORY - exact text)
5. `primary_source_provision_id` (MANDATORY)

**MEDIUM PRIORITY:**
6. `references_table` (3.4% in Ashfield)
7. `applicable_hcas` (for Chapter E1 Heritage)

**LOW PRIORITY (rare but still extract):**
8. `references_figure` (1.0% in Ashfield)
9. `references_sepp` (0.9% in Ashfield)

**STANDARD FIELDS:**
10. All other fields per normal extraction

---

## Quality Checklist

Before returning JSON, verify:

- [ ] DS codes extracted with each bullet as separate requirement
- [ ] PC codes stored in `objective` or `performance_criteria` fields
- [ ] **Section cross-references detected** (21.3% frequency - HIGH PRIORITY)
- [ ] **LEP/HCA references detected** (18.9% frequency - HIGH PRIORITY)
- [ ] Table references flagged when present (3.4% frequency)
- [ ] Figure references flagged when present (1.0% frequency - rare)
- [ ] SEPP references flagged when present (0.9% frequency - rare)
- [ ] HCA names extracted for heritage provisions
- [ ] PDF metadata present on every requirement
- [ ] Verbatim text includes full DS/PC context for bullet points
- [ ] All reference boolean fields present (even if false)

**Expected Reference Detection Rate:**
- ~21% of requirements should have `references_section: true`
- ~19% of requirements should have `references_lep: true`
- ~3% should have table references
- ~1% should have figure or SEPP references
