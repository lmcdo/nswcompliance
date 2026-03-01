# LLM Extraction Purpose - User-Centric Analysis

## Target Users

1. **Property Developers** - Feasibility analysis, site selection, DA preparation
2. **Architects/Designers** - Design compliance, variation justification
3. **Certifiers** - Compliance assessment, certification sign-off
4. **Town Planners** - DA lodgement, council negotiations
5. **Homeowners** - Understanding requirements for renovations/additions

## User's Core Questions

### 1. "Can I build this?" (Binary compliance check)
**User needs:**
- Height limits (numeric)
- Setback requirements (numeric, conditional)
- FSR limits (numeric)
- Heritage restrictions (yes/no + specific requirements)
- Parking requirements (numeric, by development type)

**NOT useful:**
- "Development should be compatible with character" (too vague)
- "To maintain streetscape quality" (context, not requirement)

### 2. "What are the specific numbers?" (Actionable data)
**User needs:**
- "Front setback: 6m minimum"
- "Parking: 1 space per dwelling"
- "Height: 9m max OR 12m with 3m upper setback"
- "Side setback: 900mm for single storey, 1.5m for two storey"

**NOT useful:**
- "Adequate setbacks must be provided" (what is adequate?)
- "Parking must meet community needs" (how many spaces?)

### 3. "Why is this required?" (Context for flexibility)
**User needs:**
- Objectives that explain intent (helps justify variations)
- Performance criteria (shows what outcome is actually needed)
- Alternative solutions criteria (when can rules be varied?)

**Workflow:**
- Read objective: "To maintain garden setting character"
- Understand control: "6m front setback" exists to achieve that objective
- Propose alternative: "5m setback + additional landscaping achieves same outcome"

### 4. "Can I see the source?" (Verification)
**User needs:**
- PDF page link to view original text
- Check diagrams, tables, photos
- Read detailed explanations
- Verify LLM didn't misinterpret

## Real-World User Workflow Example

**Scenario:** Architect designing dual occupancy at 40 Lackey Street, Summer Hill

### Current Manual Process (2-4 hours):
1. Google "Marrickville DCP dual occupancy"
2. Download 400-page PDF
3. Ctrl+F "dual occupancy" → 47 matches
4. Read through each match to find relevant controls
5. Cross-reference Part 4 (residential), Part 3 (parking), Part 2 (heritage - property is in HCA)
6. Extract setbacks, height, parking into spreadsheet
7. Check if any precinct-specific controls apply
8. Call council to verify interpretation

### Ideal App Workflow (5 minutes):
1. Enter "40 Lackey Street" + select "Dual Occupancy"
2. App shows:
   - **General DCP controls** (applies to all dual occupancy in Marrickville)
   - **Precinct-specific controls** (Precinct 40 - Summer Hill)
   - **Heritage controls** (Summer Hill HCA 27)
3. Each requirement shows:
   - Clear statement: "Front setback: 6m minimum"
   - Numeric value extracted: 6.0m
   - PDF page link: View source (page 11)
   - Objective: "To maintain garden setting character"
4. User clicks "View PDF" for any unclear requirements
5. User exports checklist for DA submission

## What This Means for Extraction

### PRIMARY GOAL: Actionable Compliance Requirements

**Extract every discrete requirement a certifier would check:**

✅ **Good extraction:**
- "C7 - Maximum FSR and height per MLEP 2011 maps"
- "C8i - Overshadowing and privacy impacts acceptable"
- "C8ii - Streetscape bulk and scale acceptable"
- "C10i - Front setback consistent with adjoining development"
- "C10ia - Minimum 6m from front boundary"
- "C10ib - On corner lots: match secondary boundary setback pattern"

❌ **Bad extraction (current):**
- "Alterations to period dwellings must not detract from their character" (1 vague requirement instead of 28 specific ones)

### SECONDARY GOAL: Strategic Context

**Link objectives/performance criteria to requirements:**

✅ **Good:**
```json
{
  "requirement_text": "Front setback: 6m minimum",
  "value_min": 6.0,
  "unit": "m",
  "objective": "O11: To maintain garden setting character of HCA",
  "allows_alternative_solutions": true,
  "alternative_solutions_criteria": "Alternative solutions considered if equivalent landscaping outcome achieved"
}
```

❌ **Bad:**
```json
{
  "requirement_text": "To maintain garden setting character",
  "category": "character"
}
```
(This is an objective, not a requirement!)

### TERTIARY GOAL: Navigation & Verification

**Enable source traceability:**
- Every requirement has `pdf_page`, `pdf_page_image_url`, `pdf_path`
- User can click through to verify
- Critical for high-stakes decisions (multi-million dollar projects)

## Certifier's Compliance Checklist Perspective

**A certifier reviewing a DA asks:**

### Marrickville (Prescriptive):
- ✅ Does it meet C7? (height/FSR per LEP)
- ✅ Does it meet C8i? (overshadowing acceptable)
- ✅ Does it meet C8ii? (streetscape acceptable)
- ✅ Does it meet C10i? (front setback matches adjoining)
- ... (28 total checks for section 4.1.6)

### Ashfield (Performance-based):
- ✅ Does it meet Performance Criterion 1? (deep soil planting provided)
- ✅ Does it meet Performance Criterion 2? (landscaping consistent with character)
- ✅ Does it meet Performance Criterion 3? (tree retention where possible)
- ... (N performance criteria per part)

**NOT:**
- ❌ "Does it maintain character?" (too subjective without specific criteria)
- ❌ "Does it meet the purpose?" (purpose is context, not assessment criteria)

## Critical Distinction: Requirements vs Context

### REQUIREMENTS (extract as separate records):
- **Marrickville/Leichhardt**: Controls (C1, C2, C3...) + all sub-items (i., ii., iii...)
- **Ashfield**: Performance Criteria + Design Solutions

### CONTEXT (link to requirements, don't create separate records):
- **Marrickville/Leichhardt**: Objectives (O1, O2, O3...)
- **Ashfield**: Purpose statements

### EXAMPLE - Section 4.1.6 Built form and character:

**Context (store in `objective` field):**
- O10: "To ensure development is of a scale and form that enhances the character and quality of streetscapes"
- O11: "To ensure alterations and additions to residential period dwellings do not detract from the individual character and appearance of the dwelling being added to and the wider streetscape character"

**Requirements (create separate records for each):**
1. C7 - Maximum FSR/height per MLEP 2011
2. C8 - Demonstrate acceptable bulk/mass in terms of:
   - C8i - Overshadowing and privacy
   - C8ii - Streetscape (bulk and scale)
   - C8iii - Building setbacks
   - C8iv - Parking and landscape requirements
   - C8v - Visual impact and views
   - C8vi - Significant trees
   - C8vii - Lot size, shape, topography
3. C9 - Secondary dwellings max 2 storeys
4. C10 - Attached dwellings setbacks:
   - C10i - Front setback:
     - C10ia - Consistent with adjoining development
     - C10ib - Corner lots: match secondary boundary pattern
   - C10ii - Side setback per table
   - C10iii - Rear setback: maintain building line or merit assessment
... (continues for 28+ total requirements)

**Current extraction: 1 record (O11 objective)**
**Correct extraction: 28+ records (all C7-C13 controls + sub-items)**

## Optimal Extraction Purpose Statement

**Extract every discrete, assessable compliance requirement that a certifier/planner would check during DA assessment, preserving all numeric values, conditional logic, and source traceability, while providing strategic context (objectives/performance criteria) to enable understanding of flexibility and intent.**

### Translation to Implementation:

1. **Systematic enumeration** - Extract ALL controls (C1, C2, C3...) or ALL performance criteria - NO random sampling
2. **Discrete requirements** - Each sub-item as separate record (C8i, C8ii, C8iii... not bundled into C8)
3. **Numeric precision** - Exact values, no rounding (6.0m not "approximately 6m")
4. **Conditional preservation** - "for corner lots", "where rear lane exists" context retained
5. **Source linking** - PDF page + URL for every single requirement
6. **Strategic context** - Objectives/Purpose linked but NOT extracted as requirements

## Different Structures = Different User Needs

### Marrickville/Leichhardt (O/C Structure):
**User expectation:** Prescriptive checklist
- "I must meet C1, C2, C3... to get approval"
- Objectives provide context for arguing variations
- Each control is a binary check (complies or doesn't)

**Extraction strategy:**
- All C controls → requirements
- All sub-items → separate requirements
- O objectives → context field on related requirements

### Ashfield (Performance-based):
**User expectation:** Outcome-based assessment
- "I must achieve Performance Criteria to get approval"
- Design Solutions are examples (not mandatory if PC met another way)
- More flexibility, but PC is the actual test

**Extraction strategy:**
- Performance Criteria → requirements (these ARE the compliance test)
- Design Solutions → requirements (prescriptive methods)
- Purpose → context (explains intent but not assessed)

## Success Metrics

**Good extraction enables user to:**
1. ✅ Generate DA compliance checklist in <5 minutes (vs 2-4 hours manual)
2. ✅ Identify all numeric requirements without reading PDFs
3. ✅ Understand flexibility/variation opportunities via objectives
4. ✅ Verify any requirement via PDF source link
5. ✅ Export structured data for consultants/certifiers

**Current extraction fails because:**
1. ❌ Missing 96% of requirements (1 extracted vs 28 exist in section 4.1.6)
2. ❌ No numeric values extracted despite source having "6m", "2 storeys", etc.
3. ❌ Extracting objectives as requirements (backwards)
4. ❌ Random sampling instead of systematic enumeration

## Final Answer: What Should We Extract?

**For the certifier reviewing the DA:**

### Marrickville/Leichhardt:
Extract: C1, C2, C3, C4, C5... (ALL controls)
Extract: i., ii., iii., iv., v... (ALL sub-items as separate requirements)
Extract: a., b., c... (ALL further sub-items)
Context: O1, O2, O3... (objectives linked to requirements)

### Ashfield:
Extract: Every Performance Criterion (these define compliance)
Extract: Every Design Solution (prescriptive methods)
Context: Purpose (explains why but not what)

**NOT extracted as requirements:**
- Purpose statements (context)
- Objectives (context)
- Explanatory paragraphs
- "NB" notes
- Section headers
- Table of contents

**Every extracted requirement must have:**
- Clear actionable statement
- Numeric values where present
- Conditional context preserved
- PDF page link
- Source provision ID
