# PRP-J: Clause Code Classification System
## Systematic Integration of Context-Aware Legislative Intelligence

**Document ID:** PRP-J_CLAUSE_CODE_CLASSIFICATION_SYSTEM 
**Version:** 1.0 
**Date:** 2025-09-05 
**Dependencies:** inner_west_compliance_engine.py, dynamic_setback_calc.py, database infrastructure 
**Status:** Design Phase

---

## Executive Summary

The Inner West Compliance Engine successfully extracts legislative setbacks with hierarchical intelligence (2.8m front, 3.0m side/rear with real DCP sources). However, it lacks **context-aware classification**, leading to irrelevant results like signage setbacks being applied to residential buildings.

This PRP establishes a **Clause Code Classification System** that layers semantic understanding on top of existing extraction achievements, ensuring regulatory precision without disrupting functional components.

---

## Current State Assessment

### Proven Achievements to Preserve
- **Hierarchical extraction engine** with 70+ quantitative standards (Marrickville)
- **Legal source verification** with confidence scoring (1.0, 0.9 vs generic) 
- **Multi-council integration** (Marrickville/Leichhardt/Ashfield)
- **API integration layer** with dynamic zone/property_id handling
- **Combined boundary logic** (side and rear from single clause)
- **Database intelligence** with relationship mapping

### Critical Reliability Gap
- **Context-blind matching**: Signage setbacks applied to residential queries
- **Domain contamination**: Section 2.12 (Signs) → Section 4.2 (Buildings) 
- **False confidence**: 100% confidence for contextually incorrect results
- **No semantic filtering**: Numerical match ≠ regulatory relevance

---

## Technical Architecture

### Core Principle: **Additive Enhancement**
Build classification layer **on top of** existing extraction without disrupting proven functionality.

### 1. Clause Code Format Specification

```
Format: [COUNCIL]_[DOCUMENT]_[SECTION]_[CONTROL_TYPE]_[BOUNDARY]_[APPLICABILITY]

Examples:
 MARRICKVILLE_DCP_4.2_BUILDING_SETBACK_FRONT_RESIDENTIAL
 MARRICKVILLE_DCP_2.12_SIGN_SETBACK_FRONT_SIGNAGE

Components:
- COUNCIL: marrickville | leichhardt | ashfield
- DOCUMENT: DCP | LEP | SEPP 
- SECTION: Hierarchical section number (4.2, 2.12, etc.)
- CONTROL_TYPE: BUILDING | SIGN | PARKING | LANDSCAPING
- BOUNDARY: FRONT | SIDE | REAR | GENERAL
- APPLICABILITY: RESIDENTIAL | COMMERCIAL | INDUSTRIAL | MIXED
```

### 2. Enhanced Data Structures

**Extend existing SetbackRequirement:**
```python
@dataclass
class ClassifiedSetbackRequirement(SetbackRequirement):
 """Enhanced setback with classification intelligence"""
 clause_code: str # Full classification code
 control_domain: str # BUILDING | SIGN | PARKING
 section_hierarchy: str # 4.2.1.a 
 applicability_zones: List[str] # ['R2', 'R3', 'R4']
 applicability_building_types: List[str] # ['dwelling', 'dual_occupancy']
 relevance_score: float # Context relevance (0-1)
 classification_confidence: float # Classification certainty (0-1)
```

### 3. Classification Engine Architecture

**Phase 1: Domain Classification**
```python
class DomainClassifier:
 """Classify extracted clauses by regulatory domain"""
 
 SECTION_DOMAINS = {
 # Residential Building Controls
 '4.1': 'BUILDING_RESIDENTIAL',
 '4.2': 'BUILDING_RESIDENTIAL', 
 '4.3': 'BUILDING_RESIDENTIAL',
 
 # Non-Building Controls
 '2.12': 'SIGN_ADVERTISING',
 '3.1': 'COMMERCIAL_BUILDING',
 '5.1': 'PARKING_TRANSPORT',
 }
 
 def classify_clause(self, legal_source: str, section: str) -> str:
 """Return domain classification for clause"""
 return self.SECTION_DOMAINS.get(section, 'GENERAL')
```

**Phase 2: Relevance Matching Engine**
```python
class RelevanceEngine:
 """Match classified clauses to query context"""
 
 def calculate_relevance(self, 
 query_intent: QueryIntent,
 classified_clause: ClassifiedSetbackRequirement) -> float:
 
 # Domain match scoring
 domain_score = self._score_domain_match(query_intent.domain, 
 classified_clause.control_domain)
 
 # Zone applicability scoring 
 zone_score = self._score_zone_applicability(query_intent.zone,
 classified_clause.applicability_zones)
 
 # Building type scoring
 building_score = self._score_building_type(query_intent.building_type,
 classified_clause.applicability_building_types)
 
 return (domain_score * 0.5) + (zone_score * 0.3) + (building_score * 0.2)
```

---

## Implementation Strategy

### MVP Phase 1: Immediate Reliability Fix (2-3 days)

**1.1 Hard-coded Domain Filters**
- Extend `inner_west_compliance_engine.py` with section blacklists
- Block sections 2.12 (Signs) for residential building queries
- Add domain validation to `dynamic_setback_calc.py`

**1.2 Enhanced Confidence Calculation**
```python
def calculate_enhanced_confidence(base_confidence: float, 
 section: str, 
 query_domain: str) -> float:
 """Penalize confidence for cross-domain results"""
 if is_cross_domain_match(section, query_domain):
 return base_confidence * 0.1 # Severe penalty
 return base_confidence
```

**Files to Modify:**
- `inner_west_compliance_engine.py`: Add domain filtering
- `dynamic_setback_calc.py`: Add relevance validation 
- New: `services/domain_classifier.py`: Core classification logic

### Phase 2: Systematic Classification (1-2 weeks)

**2.1 Database Schema Extension**
```sql
-- Add classification columns to existing tables
ALTER TABLE regulatory_provisions ADD COLUMN clause_code TEXT;
ALTER TABLE regulatory_provisions ADD COLUMN control_domain TEXT;
ALTER TABLE regulatory_provisions ADD COLUMN section_hierarchy TEXT;
ALTER TABLE regulatory_provisions ADD COLUMN applicability_zones TEXT; -- JSON array
ALTER TABLE regulatory_provisions ADD COLUMN relevance_metadata TEXT; -- JSON
```

**2.2 Batch Classification Pipeline**
- Analyze existing 245 quantitative standards + 131 setback controls
- Generate clause codes for all extracted provisions
- Calculate applicability matrices (zone + building type combinations)

**2.3 Enhanced Query Engine**
```python
class EnhancedComplianceEngine(InnerWestComplianceEngine):
 """Classification-aware compliance engine"""
 
 def get_classified_setback_requirements(self, 
 zone: str, 
 council_area: str,
 building_type: str = 'dwelling') -> List[ClassifiedSetbackRequirement]:
 
 # Get base requirements (existing logic)
 base_requirements = super().get_reliable_setback_requirements(zone, council_area)
 
 # Apply classification and relevance filtering
 classified_requirements = []
 for req in base_requirements:
 classified = self.classifier.classify_requirement(req)
 relevance = self.relevance_engine.calculate_relevance(
 QueryIntent(domain='BUILDING_RESIDENTIAL', zone=zone, building_type=building_type),
 classified
 )
 
 if relevance > 0.7: # High relevance threshold
 classified.relevance_score = relevance
 classified_requirements.append(classified)
 
 return sorted(classified_requirements, key=lambda x: x.relevance_score, reverse=True)
```

### Phase 3: Advanced Semantic Understanding (Future)

**3.1 Conditional Logic Parsing**
- Handle complex "if-then" requirements
- Parse building height triggers for setback variations
- Manage overlay conflicts (SEPP vs DCP vs LEP)

**3.2 Multi-Council Conflict Resolution**
- Compare requirements across council areas
- Identify and resolve contradictory provisions
- Generate compliance pathway recommendations

---

## Quality Assurance Framework

### Validation Metrics

**Relevance Accuracy:**
- Target: 0% signage results for residential queries
- Measurement: Domain classification accuracy rate
- Threshold: >95% correct domain assignment

**Confidence Recalibration:**
- Target: Confidence reflects actual reliability
- Measurement: Correlation between confidence and validation outcomes 
- Threshold: >0.85 confidence-accuracy correlation

**Coverage Preservation:**
- Target: Maintain existing successful extractions (2.8m front, 3.0m side/rear)
- Measurement: Before/after result comparison
- Threshold: 100% preservation of validated results

### Testing Strategy

**Unit Tests:**
```python
def test_domain_classification():
 """Ensure correct domain assignment"""
 classifier = DomainClassifier()
 
 # Signs section should never apply to buildings
 assert classifier.classify_section('2.12') == 'SIGN_ADVERTISING'
 assert classifier.is_applicable_to_domain('SIGN_ADVERTISING', 'BUILDING_RESIDENTIAL') == False
 
def test_relevance_scoring():
 """Ensure signage setbacks get low relevance for residential queries"""
 engine = RelevanceEngine()
 
 residential_query = QueryIntent(domain='BUILDING_RESIDENTIAL', zone='R2')
 signage_clause = create_signage_clause()
 
 relevance = engine.calculate_relevance(residential_query, signage_clause)
 assert relevance < 0.1 # Very low relevance
```

**Integration Tests:**
```python
def test_end_to_end_classification():
 """Test complete pipeline with real data"""
 engine = EnhancedComplianceEngine()
 
 # Should return building setbacks only
 results = engine.get_classified_setback_requirements('R2', 'marrickville', 'dwelling')
 
 for result in results:
 assert result.control_domain == 'BUILDING_RESIDENTIAL'
 assert result.relevance_score > 0.7
 assert 'sign' not in result.legal_source.lower()
```

---

## Migration Strategy

### Backward Compatibility
- Maintain existing API endpoints during transition
- Provide parallel `/v2/` endpoints with enhanced classification
- Gradual migration with A/B testing

### Data Preservation
- Never modify existing extraction data
- Add classification as parallel metadata
- Rollback capability if classification introduces errors

### Deployment Phases
1. **Shadow Mode**: Classification runs but doesn't affect results
2. **Validation Mode**: Classification applied with human oversight
3. **Production Mode**: Full autonomous classification

---

## Success Metrics

### MVP Phase 1 Success Criteria
- Zero signage setbacks returned for residential queries
- Confidence scores reflect domain relevance 
- All residential results from sections 4.1-4.3 only
- Preserve existing 2.8m/3.0m results with legal sources

### Long-term Success Indicators
- **Precision**: >98% domain classification accuracy
- **Recall**: No loss of valid regulatory requirements
- **User Trust**: Confidence scores correlate with actual reliability
- **Scalability**: System supports additional councils without degradation

---

## Resource Requirements

### Development Effort
- **Phase 1 (MVP)**: 20-30 hours (immediate reliability fix)
- **Phase 2 (Classification)**: 60-80 hours (systematic enhancement)
- **Phase 3 (Advanced)**: 120+ hours (semantic understanding)

### Technical Dependencies
- Extend existing database schema (non-breaking)
- No new external dependencies required
- Leverage existing classification patterns in codebase

---

## Risk Mitigation

### Technical Risks
- **Risk**: Classification reduces valid results
- **Mitigation**: Comprehensive before/after validation, rollback capability

- **Risk**: Performance degradation with additional processing
- **Mitigation**: Caching, indexing, async processing where possible

### Adoption Risks 
- **Risk**: Users lose confidence in enhanced system
- **Mitigation**: Transparent confidence scoring, validation reporting

---

## Conclusion

This PRP provides a systematic path to transform the Inner West Compliance Engine from a **numerically accurate** system to a **contextually intelligent** one. By building on proven extraction achievements while adding semantic classification, we preserve existing functionality while eliminating reliability issues.

The result will be a compliance engine that returns **the right setbacks for the right reasons** - building setbacks for buildings, signage setbacks for signs, with confidence scores that reflect actual regulatory relevance.

---

**Next Steps:**
1. Review and approve architectural decisions
2. Begin Phase 1 implementation (immediate reliability fixes)
3. Establish validation framework and success metrics 
4. Plan Phase 2 rollout timeline and resource allocation
