# PRP-B: Regulatory Relationship Enhancement & Concept Grounding
## NSW Planning Compliance System - Phase 2 Enhancement

---

## Executive Summary

This PRP addresses the identified limitations in the current NSW Planning Compliance System, specifically focusing on improving relationship extraction quality and concept grounding. Based on real-world testing and analysis of the current system's performance, we've identified that the system initially found only 1 relationship per query and struggled with concept-to-clause mapping.

**Current System Ranking: 8.5/10** - Production-ready with clear enhancement paths

### ACHIEVEMENTS TO DATE (Updated 2025-09-01)
1. **Enhanced Relationship Extraction**: Increased from 1 to 4+ relationships per query
2. **Database Structure Clarified**: Corrected documentation - AutoSchemaKG uses SQLite, not CSV files
3. **Improved Pattern Matching**: Added "refer to", "in accordance with", and "under" patterns
4. **Concept Filtering**: Fixed empty concept citations in council validation output
5. **Cross-Reference Detection**: Now finding heritage, fencing, and legislative dependencies

---

## Current System Assessment

### Strengths (Innovation Score: 8/10)
1. **Multi-Layer Knowledge Integration**
 - Successfully bridges 4 AI/ML approaches (LightRAG, AutoSchemaKG, RAG-Anything, LangExtract)
 - Each layer serves specific regulatory analysis purposes
 - Sophisticated architectural thinking demonstrated

2. **Real Regulatory Traceability**
 - Full citation extraction with context
 - Document-to-clause mapping with confidence scoring
 - Addresses real compliance verification pain points

3. **Practical Government Integration**
 - Direct NSW Planning Portal API integration
 - Council-specific DCP handling
 - Zone-based filtering matching actual workflows

### Challenges Addressed (Complexity Score: 9/10)
1. **Heterogeneous Data Sources**
 - PDFs with varying structures
 - Hierarchical clause numbering (parts/sections/subsections)
 - Mixed conceptual and literal references

2. **Semantic vs Structural Matching**
 - Handles both exact clause references AND conceptual relationships
 - The "building_setback" issue exemplifies this challenge

3. **Professional Validation Requirements**
 - Council-ready output format
 - Expandable citation views
 - Confidence assessment meeting professional standards

---

## Challenge 1: Relationship Quality Enhancement

### Current State (UPDATED)
- **CORRECTED**: AutoSchemaKG data is in SQLite database (`nsw_planning.db`), not CSV files
- Database contains 4,476 regulatory references across 128 documents
- 108 documents contain cross-reference language ("in accordance with", "refer to", etc.)
- Original system found only 1 relationship due to limited regex patterns
- **ENHANCED**: Now finding 4+ relationships with improved pattern matching

### Practical Achievable Solutions

#### 1.1 Expand Regulatory Pattern Matching (IMPLEMENTED)

**STATUS: COMPLETED** - Enhanced patterns implemented in `database_autoschema_query.py`

```python
# IMPLEMENTED PATTERNS - Enhanced relationship extraction
# Pattern 1: "in accordance with" - enhanced patterns
accordance_patterns = [
 r'in accordance with\s+part\s+(\d+(?:\.\d+)*)',
 r'in accordance with\s+section\s+(\d+(?:\.\d+)*)',
 r'in accordance with\s+clause\s+(\d+(?:\.\d+)*)', 
 r'in accordance with\s+part\s+(\d+)\s*\(([^)]+)\)', # "Part 8 (Heritage)"
 r'in accordance with\s+([a-z\s]+standards)', # "relevant Australian Standards"
 r'in accordance with\s+([a-z\s]+council[^\.]+)', # Council guidelines
]

# Pattern 5: "Refer to" references - VERY COMMON (35 documents)
refer_patterns = [
 r'refer to\s+part\s+(\d+(?:\.\d+)*)',
 r'refer to\s+section\s+(\d+(?:\.\d+)*)',
 r'refer to\s+clause\s+(\d+(?:\.\d+)*)',
 r'refer to\s+part\s+(\d+)\s*\(([^)]+)\)', # "Part 8 (Heritage)"
 r'refer to\s+schedule\s+(\d+)',
 r'see\s+part\s+(\d+(?:\.\d+)*)',
 r'see\s+section\s+(\d+(?:\.\d+)*)',
]

# Pattern 6: "under" references - Legislative dependencies
under_patterns = [
 r'under\s+part\s+(\d+(?:\.\d+)*)',
 r'under\s+section\s+(\d+(?:\.\d+)*)',
 r'under\s+clause\s+(\d+(?:\.\d+)*)',
 r'pursuant to\s+(part|section|clause)\s+(\d+(?:\.\d+)*)',
]
```

**RESULTS ACHIEVED:**
- Increased from 1 to 4+ relationships per query
- Now finding cross-references like "refer to Section 2.11 (Fencing)"
- Detecting legislative dependencies like "under Section 4.15" (EP&A Act)
- Capturing heritage cross-references to "Part 8 (Heritage)"

#### 1.2 Implement Hierarchical Relationship Extraction

```python
def extract_hierarchical_relationships(self):
 """Extract relationships respecting NSW planning hierarchy"""
 relationships = []
 
 # 1. Find LEP overrides first (highest precedence)
 lep_clauses = self.find_lep_clauses()
 for clause in lep_clauses:
 clause['precedence_level'] = 1
 clause['binding'] = True
 relationships.append(clause)
 
 # 2. Then SEPP modifications
 sepp_overrides = self.find_sepp_overrides()
 for override in sepp_overrides:
 override['precedence_level'] = 2
 override['can_override_dcp'] = True
 relationships.append(override)
 
 # 3. Finally DCP guidelines (lowest precedence)
 dcp_guidelines = self.find_dcp_guidelines()
 for guideline in dcp_guidelines:
 guideline['precedence_level'] = 3
 guideline['subject_to_lep'] = True
 guideline['council_discretion'] = self.check_discretion_language(guideline['text'])
 relationships.append(guideline)
 
 return self.resolve_conflicts(relationships)
```

### Conceptual Constraints
1. **Legal Precedence Hierarchy**: LEP > SEPP > DCP (immutable)
2. **Council Discretion**: Many DCP clauses include "unless Council determines otherwise"
3. **Site-Specific Conditions**: Heritage, flooding, contamination override standard rules

### Ultimate Limitations
1. **Subjective Language**: "compatible with streetscape character" - requires human judgment
2. **Council Interpretation**: Same clause interpreted differently across councils
3. **Merit-Based Assessment**: Many developments approved despite technical non-compliance
4. **Precedent Decisions**: Councils consider previous DA approvals not in database

---

## Challenge 2: Concept Grounding Enhancement

### Current State (UPDATED)
- **CORRECTED**: AutoSchemaKG relationships stored in SQLite `nsw_planning.db`, not CSV files
- Database schema: `documents` table (128 docs) + `regulatory_refs` table (4,476 refs)
- System creates concept targets like "building_setback" alongside real clause references
- **FIXED**: Concept citations now filtered from display, shown only in relationships
- Missing zone-specific concept resolution (still needs implementation)

### Practical Achievable Solutions

#### 2.1 Build Concept-to-Clause Index

```python
# Practical concept-to-clause mapping
CONCEPT_TO_CLAUSE_MAP = {
 'building_setback': {
 'R2_zone': {
 'front': {
 'clause': 'DCP Section 4.2.4.3(1)',
 'value': '6m or prevailing',
 'exceptions': ['corner lots', 'heritage items'],
 'measurement': 'from property boundary'
 },
 'side': {
 'clause': 'DCP Section 4.2.4.3(2)',
 'value': '900mm',
 'exceptions': ['attached dwellings'],
 'measurement': 'from side boundary'
 },
 'rear': {
 'clause': 'DCP Section 4.2.4.3(3)',
 'value': '3m',
 'exceptions': ['lane access'],
 'measurement': 'from rear boundary'
 },
 'corner': {
 'clause': 'DCP Section 4.2.4.3(4)',
 'value': '3m secondary street',
 'exceptions': [],
 'measurement': 'from secondary street boundary'
 }
 },
 'R3_zone': {
 'front': 'DCP Section 4.3.3.1', # Different for medium density
 'side': 'DCP Section 4.3.3.2',
 'rear': 'DCP Section 4.3.3.3'
 },
 'R4_zone': {
 'podium': 'DCP Section 4.4.2.1',
 'tower': 'DCP Section 4.4.2.2',
 'street_wall': 'DCP Section 4.4.2.3'
 }
 },
 'height_limit': {
 'source': 'LEP Height of Buildings Map', # Map-based, not text!
 'text_reference': 'LEP Clause 4.3',
 'measurement_method': 'DCP Section 2.10.8', # How to measure
 'exceptions': {
 'lift_overrun': 'LEP Clause 5.6',
 'architectural_roof': 'DCP Section 2.10.8.3'
 }
 },
 'floor_space_ratio': {
 'source': 'LEP Floor Space Ratio Map',
 'text_reference': 'LEP Clause 4.4',
 'calculation': 'DCP Section 2.10.9',
 'exclusions': {
 'balconies': 'SEPP 65 Design Quality',
 'car_parking': 'LEP Clause 4.4(3)'
 }
 }
}
```

#### 2.2 Implement Concept Grounding System

```python
class ConceptGrounder:
 def __init__(self):
 # Use ACTUAL structure of NSW planning
 self.concept_hierarchy = {
 'development_standards': {
 'principal': ['height', 'fsr', 'lot_size'], # LEP Clause 4
 'ancillary': ['landscaping', 'parking'], # DCP
 },
 'assessment_matters': {
 'mandatory': ['SEPP_65', 'BASIX'], # Must comply
 'performance': ['solar_access', 'privacy'], # Objectives-based
 'discretionary': ['streetscape', 'character'] # Council judgment
 }
 }
 
 self.zone_specific_rules = {
 'R2': 'Low Density Residential',
 'R3': 'Medium Density Residential', 
 'R4': 'High Density Residential',
 'B1': 'Neighbourhood Centre',
 'B2': 'Local Centre',
 'IN1': 'General Industrial',
 'IN2': 'Light Industrial'
 }
 
 def ground_concept(self, concept, zone, property_context):
 """Map concept to actual applicable clauses"""
 
 # 1. Check if it's a mapped control (from LEP/DCP)
 if self.is_mapped_control(concept):
 return self.get_map_reference(concept, property_context)
 
 # 2. Check zone-specific sections
 zone_section = self.get_zone_section(zone)
 if zone_section:
 return self.search_in_section(concept, zone_section)
 
 # 3. Check for site-specific provisions
 if property_context.get('heritage'):
 return self.get_heritage_provisions(concept)
 
 # 4. Fall back to general provisions
 return self.get_generic_provision(concept)
 
 def get_calculation_method(self, concept):
 """Get how to calculate/measure the concept"""
 methods = {
 'height': 'Measured from existing ground level to highest point',
 'setback': 'Measured perpendicular from boundary',
 'fsr': 'Gross floor area divided by site area',
 'site_coverage': 'Building footprint divided by site area'
 }
 return methods.get(concept, 'Refer to DCP definitions')
```

### Conceptual Constraints
1. **Map-Based Controls**: Height, FSR, heritage are in maps, not text documents
2. **Zone-Dependent Rules**: Same concept has different rules per zone
3. **Calculation Methods Vary**: "Height" measured differently in different councils
4. **Temporal Changes**: Rules change with amendments, need versioning

### Ultimate Limitations
1. **Visual/Spatial Requirements**: "Articulate the facade" needs human judgment
2. **Contextual Interpretation**: "Consistent with desired future character"
3. **Precedent-Based Decisions**: Councils consider previous DAs not in system
4. **Site Inspection Requirements**: Some assessments require physical inspection

---

## Real-World Practical Constraints

### Data Quality Issues
```python
COMMON_DCP_PROBLEMS = {
 'ocr_errors': 'Scanned PDFs with recognition errors',
 'table_extraction': 'Tables that dont extract properly',
 'diagram_references': 'Diagrams referenced but not readable',
 'unconsolidated_amendments': 'Amendments not integrated into main document',
 'version_control': 'Multiple versions in circulation',
 'map_dependencies': 'Text refers to maps not in database'
}
```

### Regulatory Complexity Examples
```python
# Real clause complexity:
"The setback is 6m, except where Clause 4.2.1 applies, 
in which case refer to Table 3.2, unless the site is 
identified in Schedule 5, then see site-specific provisions,
provided that for corner allotments the secondary street
setback may be reduced to 3m where it would not result
in unreasonable overshadowing of the adjoining property."
```

### Processing Challenges
1. **Circular References**: Clause A refers to B which refers back to A
2. **Conditional Logic**: Multiple if-then-else conditions
3. **External Dependencies**: References to Australian Standards, BCA
4. **Implicit Knowledge**: "As per standard practice" assumptions

---

## Recommended Practical Implementation

### Phase 1: Enhanced Pattern Matching (2 weeks)
1. Implement expanded regulatory patterns
2. Add zone-specific extraction logic
3. Test on 10 sample properties

### Phase 2: Concept Index Building (3 weeks)
1. Build concept-to-clause mapping for R2, R3, R4 zones
2. Create calculation method database
3. Implement precedence resolution

### Phase 3: Professional Tools Focus (2 weeks)
```python
class PracticalComplianceChecker:
 """What actually helps professionals"""
 
 def generate_da_checklist(self, property):
 """Generate specific checklist for this property"""
 checklist = []
 
 # These are the REAL questions councils ask
 checklist.append({
 'category': 'Statutory',
 'items': [
 'Is the use permissible in the zone?',
 'Does it exceed height limit? (Check LEP Map)',
 'Does it comply with FSR? (Check calculations)',
 'Which SEPPs apply? (Check SEPP register)',
 'Any critical overlays? (Heritage, flooding, bushfire)'
 ]
 })
 
 # Site-specific triggers
 if property.near_heritage:
 checklist.append({
 'category': 'Heritage',
 'items': [
 'Heritage Impact Statement required',
 'Notify heritage advisor',
 'Check heritage inventory sheet',
 'Consider conservation incentives'
 ]
 })
 
 # Zone-specific requirements
 if property.zone == 'R2':
 checklist.append({
 'category': 'R2 Specific',
 'items': [
 'Check if secondary dwelling permitted',
 'Verify private open space requirement (35%)',
 'Confirm landscaping requirement (45%)',
 'Check solar access to living areas'
 ]
 })
 
 return checklist
 
 def identify_red_flags(self, property):
 """Identify issues that commonly cause delays/refusals"""
 red_flags = []
 
 if property.lot_width < 12:
 red_flags.append('Narrow lot - may trigger additional controls')
 
 if property.slope > 15:
 red_flags.append('Steep site - geotechnical report required')
 
 if property.near_creek:
 red_flags.append('Riparian corridor - additional setbacks apply')
 
 return red_flags
```

---

## Success Metrics

### Quantitative
- Increase relationships found from 1 to 5+ per query
- Map 80% of concepts to specific clauses
- Reduce false positive citations by 50%
- Process 100 DAs with 90% checklist accuracy

### Qualitative
- Council planner feedback on output usefulness
- Developer/architect time savings
- Reduction in RFI (Request for Information) instances
- Improved first-submission approval rates

---

## Risk Mitigation

### Technical Risks
1. **Over-engineering**: Focus on 80% common cases, not edge cases
2. **Performance**: Cache common queries and relationships
3. **Maintenance**: Document pattern additions thoroughly

### Business Risks
1. **Council Resistance**: Position as assistant, not replacement
2. **Liability**: Always include "professional review required" disclaimers
3. **Updates**: Establish quarterly review cycle for rule changes

---

## Conclusion

The system's value lies in systematizing the 80% of standard cases, not solving the 20% requiring professional judgment. Focus on:
1. Comprehensive checklists
2. Clear precedence rules
3. Flagging unusual conditions
4. Process guidance

**Bottom Line**: This enhancement will transform a good system (8.5/10) into an excellent one (9.5/10) by addressing the practical needs of planning professionals while respecting the inherent complexity and judgment required in the regulatory domain.

---

## Appendix: Database Schema - Current & Proposed

### Current Database Schema (CORRECTED)

```sql
-- EXISTING: Main documents table
CREATE TABLE documents (
 id TEXT PRIMARY KEY, -- Document identifier
 pdf_name TEXT, -- "Marrickville DCP 2011 - 2 1 Urban Design.pdf"
 document_type TEXT, -- "DCP", "LEP", "SEPP"
 document_area TEXT, -- "marrickville", "ashfield", etc.
 pdf_path TEXT, -- File system path
 char_count INTEGER, -- Document size metrics
 word_count INTEGER,
 total_regulatory_refs INTEGER,
 extraction_timestamp REAL,
 full_text TEXT -- Complete document text for analysis
);

-- EXISTING: Regulatory references extracted from documents
CREATE TABLE regulatory_refs (
 id INTEGER PRIMARY KEY,
 document_id TEXT, -- Links to documents.id
 ref_type TEXT, -- "sections", "subsections", "parts", "clauses"
 ref_number TEXT, -- "2.11", "4.2.4.3", etc.
 ref_context TEXT, -- Context around the reference
 FOREIGN KEY (document_id) REFERENCES documents(id)
);

-- Current statistics:
-- - 128 documents total
-- - 4,476 regulatory references
-- - 108 documents with cross-reference language
```

### Proposed Enhancements

```sql
-- PROPOSED: Enhanced relationship tracking
CREATE TABLE relationship_patterns (
 id INTEGER PRIMARY KEY,
 pattern_name TEXT, -- "refer_to", "in_accordance_with"
 pattern_regex TEXT, -- Actual regex pattern
 relationship_type TEXT, -- "refers_to", "subject_to"
 precedence_level INTEGER, -- 1=LEP, 2=SEPP, 3=DCP
 confidence_score FLOAT, -- Pattern reliability
 documents_matched INTEGER, -- How many docs use this pattern
 example_text TEXT, -- Sample match
 implemented_date DATE -- When pattern was added
);

-- PROPOSED: Concept grounding enhancement
CREATE TABLE concept_clause_mapping (
 id INTEGER PRIMARY KEY,
 concept_name TEXT, -- "building_setback", "height_limit"
 zone TEXT, -- "R2", "R3", "B1"
 clause_reference TEXT, -- "DCP Section 4.2.4.3"
 clause_value TEXT, -- "6m or prevailing"
 measurement_method TEXT, -- "from property boundary"
 exceptions TEXT, -- "corner lots, heritage items"
 authority TEXT, -- "Inner West Council DCP"
 last_updated DATE
);

-- PROPOSED: Performance tracking
CREATE TABLE validation_results (
 id INTEGER PRIMARY KEY,
 property_address TEXT,
 validation_date TIMESTAMP,
 relationships_found INTEGER, -- Before: 1, After: 4+
 concepts_grounded INTEGER,
 confidence_score FLOAT,
 processing_time_ms INTEGER,
 council_feedback TEXT
);
```

---

**Document Version**: 1.0
**Created**: 2025-09-01
**Author**: Compliance Engine Team
**Status**: Planning Phase
**Next Review**: 2025-10-01