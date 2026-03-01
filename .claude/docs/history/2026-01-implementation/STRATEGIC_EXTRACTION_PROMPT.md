# Strategic DCP Extraction Prompt

## Purpose
Extract BOTH prescriptive requirements AND strategic/descriptive content that provides context, flexibility, and decision-making guidance.

## What to Extract

### 1. PRESCRIPTIVE REQUIREMENTS (as before)
- Controls with "shall", "must", "minimum", "maximum", "required"
- Numeric standards (setbacks, heights, etc.)
- Prohibitions ("not permitted", "prohibited")

### 2. OBJECTIVES (NEW)
- **Pattern**: "To ensure...", "To protect...", "To maintain...", "Purpose:", "O1:", "Objective:"
- **What**: The planning outcome this requirement achieves
- **Why**: Explains the intent behind the control
- **Example**: "To maintain the established streetscape character and garden settings"

### 3. PERFORMANCE CRITERIA (NEW)
- **Pattern**: "PC1:", "PC2:", "Performance Criteria:", outcomes that "must be achieved"
- **What**: The measurable/assessable outcome required
- **Why**: Enables alternative solutions if outcome is met
- **Example**: "PC1: Front setback preserves established rhythm of street and provides landscaping buffer"

### 4. HERITAGE CONTEXT (NEW)
- **Pattern**: "Statement of significance", "heritage significance as...", "aesthetic significance", "historical significance"
- **What**: Why this area/building matters
- **Why**: Justifies strict controls, informs design approach
- **Example**: "Area has aesthetic significance as 1930s subdivision characterized by consistent setbacks and garden settings"

### 5. ALTERNATIVE SOLUTIONS (NEW)
- **Pattern**: "Alternative solutions may be considered", "flexibility", "variation", "subject to merit assessment"
- **What**: Indicates when controls can be varied
- **Why**: Critical for innovative design
- **Example**: "Alternative solutions will be considered if they achieve the performance criteria and demonstrate character compatibility"

## JSON Output Format

```json
[
  {
    "requirement_text": "Minimum front setback: 6m",
    "verbatim_source_text": "C1 Buildings must be setback a minimum of 6 metres from the front boundary.",
    "category": "setback_front",
    "value_min": 6,
    "unit": "m",

    "objective": "To maintain the established streetscape character and garden settings that define the Heritage Conservation Area",
    "performance_criteria": "Front setback preserves established rhythm of street and provides sufficient landscaping buffer consistent with area character",
    "heritage_context": "The 1930s subdivision is characterized by consistent 6m setbacks creating garden settings that contribute to the area's aesthetic significance",
    "allows_alternative_solutions": true,
    "alternative_solutions_criteria": "Alternative solutions will be considered if they demonstrate character compatibility and provide equivalent landscaping outcomes",

    "applicable_zones": ["R2"],
    "development_types": ["dwelling_house"],
    "primary_source_provision_id": 12345,
    "confidence": "high"
  }
]
```

## Extraction Rules

1. **Link objectives to requirements**: If an objective appears near a requirement, associate them
2. **Extract heritage context once per HCA**: Don't repeat same significance statement for every requirement
3. **Performance criteria override prescriptive**: If PC says "achieve 6m setback OR equivalent outcome", mark allows_alternative_solutions=true
4. **Context from surrounding provisions**: Objective may be in preceding provision, requirement in next one
5. **Empty is OK**: If no objective/heritage context found, leave null - don't fabricate

## Priority
1. Extract prescriptive requirements (core functionality)
2. Add objectives when clearly associated
3. Add performance criteria when present
4. Add heritage context for HCA provisions
5. Flag alternative solutions when mentioned
