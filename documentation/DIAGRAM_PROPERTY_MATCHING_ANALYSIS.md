# Diagram-Property Matching Analysis for Visual Compliance Dashboard

## Problem Statement
Diagrams in planning documents have varying applicability scope - some apply to all properties in a zone, others only to specific addresses or heritage areas. We need systematic rules for matching the right diagrams to property queries.

## Diagram Categories Identified

### 1. **Area-Specific Diagrams** (High Confidence)
**Haberfield Heritage Conservation Area:**
- Figure 2: "Where additions should be located"
- Figure 3: "Where new structures should be located in Haberfield" 
- Figure 4: "Roofs in Haberfield"
- Figure 5: "Characteristics of basement levels"
- Figure 6-10: Various Haberfield-specific design guidelines

**Applicability**: Properties within C54 Haberfield Heritage Conservation Area only
**Justification Method**: Property address → zoning lookup → heritage overlay check

### 2. **Zone-Wide Diagrams** (Medium Confidence)  
**General Development Controls:**
- Map 1: "Extent of Land where this DCP applies"
- Generic setback diagrams not specific to heritage areas
- Standard height/FSR control diagrams

**Applicability**: All properties within specific zoning categories (R1, R2, B1, etc.)
**Justification Method**: Property address → zone classification → applicable diagram set

### 3. **Site-Specific Diagrams** (Maximum Confidence)
**Individual Properties:**
- Figure 13: "Proposed subdivision for 140A Hawthorne Parade Haberfield"

**Applicability**: Exact address match only
**Justification Method**: Direct address matching

### 4. **Universal Diagrams** (Low Confidence for Specific Properties)
**General Guidelines:**
- Flood control diagrams
- General design principles
- Generic development patterns

**Applicability**: Fallback for properties without specific controls
**Justification Method**: Use when no more specific diagrams available

## Matching Algorithm Proposal

### Step 1: Property Classification
```
Property Address Input → Spatial Query → Returns:
- Zone Classification (R1, R2, B1, etc.)
- Heritage Overlays (C54, etc.)
- Special Area Designations
- Flood Control Areas
```

### Step 2: Diagram Prioritization
```
1. Site-Specific (Exact address match)
2. Heritage Area-Specific (Heritage overlay match)  
3. Zone-Specific (Zoning classification match)
4. Universal/Generic (Default fallback)
```

### Step 3: Confidence Scoring
```
- Exact Address Match: 95% confidence
- Heritage Overlay Match: 85% confidence  
- Zone Classification Match: 70% confidence
- Generic Application: 40% confidence
```

## Implementation Requirements

### Data Structure Needed
```json
{
  "diagram_id": "figure_3_haberfield_structures",
  "source_document": "Chapter E2 Haberfield Neighbourhood",
  "applicability": {
    "type": "heritage_area",
    "area_code": "C54",
    "area_name": "Haberfield Heritage Conservation Area",
    "confidence": 85
  },
  "extracted_measurements": ["6m setback", "single storey", "nil side setbacks not permitted"],
  "regulatory_context": "new structure placement controls"
}
```

### Geographic Lookup Service
- Property address → coordinate mapping
- Coordinate → zoning/overlay intersection
- Zoning/overlay → applicable diagram set

## Quality Assurance Rules

### High Confidence Use Cases
✅ **Haberfield property + Figure 3** = Strong match (heritage area specific)
✅ **140A Hawthorne Parade + Figure 13** = Perfect match (exact address)

### Medium Confidence Use Cases
⚠️ **Generic R2 property + General setback diagram** = Reasonable match
⚠️ **Commercial zone + Commercial building diagram** = Applicable

### Low Confidence/Warning Cases
❌ **Non-heritage property + Heritage-specific diagram** = Mismatch
❌ **Residential property + Commercial diagram** = Invalid application

## User Interface Implications
- Always show confidence score: "This diagram applies with 85% confidence"
- Explain matching logic: "Applicable because property is in Haberfield Heritage Conservation Area (C54)"
- Warn on low confidence: "Generic diagram shown - no specific controls found for this property"
- Allow manual diagram selection with confidence override

---
*Next Steps: Implement spatial lookup service and diagram classification system*