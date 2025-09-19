# PRP-E1: Entity & Relationship Extraction Pipeline
## Foolproof, Granular Implementation with Full Accountability

### EXECUTIVE ACCOUNTABILITY MATRIX
```yaml
pipeline_id: PRP-E1_ENTITY_RELATIONSHIP_2024_12_10
total_steps: 20
validation_gates: 4
rollback_points: 4
success_criteria: 80% entity coverage, 60% relationship accuracy
data_sources: 112 processed documents in /output
```

### PHASE 1: PRE-EXTRACTION VALIDATION (Steps 1-5)

**Step 1: Document Inventory & Assessment**
- Audit all 112 processed documents in /output folder
- Validate content_list.json integrity for each document
- Calculate text coverage and hierarchical completeness
- **Success Criteria:** 100% documents readable, >95% content extractable

**Step 2: API Provider Configuration**
- Configure primary and fallback extraction providers
- Test API connectivity and rate limits
- Establish cost controls and monitoring
- **Success Criteria:** 2+ providers operational, cost limits set

**Step 3: Planning Domain Schema Validation**
- Load NSW planning entity schema definitions
- Validate extraction patterns against known planning law
- Test rule-based extractors on sample documents
- **Success Criteria:** Schema covers 90%+ planning entity types

**Step 4: Extraction Environment Setup**
- Deploy enhanced PostgreSQL schema with entity/relationship tables
- Configure extraction logging and progress tracking
- Set up validation checkpoints and rollback procedures
- **Success Criteria:** Database ready, all tools operational

**Step 5: Baseline Quality Measurement**
- Run rule-based extraction on 10 sample documents
- Manual verification of extraction accuracy
- Establish quality benchmarks for automated validation
- **Success Criteria:** >70% baseline accuracy on manual verification

### PHASE 2: RULE-BASED EXTRACTION (Steps 6-10)

**Step 6: Zone & Development Type Extraction**
```python
# Extract zone codes, development types from text
patterns = {
    'zones': r'\b([RBCINE]{1,2}\d{1,2})\s*[Zz]one\b|\b[Zz]one\s+([RBCINE]{1,2}\d{1,2})\b',
    'dev_types': r'(dwelling house|dual occupancy|multi dwelling|residential flat|townhouse)',
    'measurements': r'(\d+(?:\.\d+)?)\s*(m|metres?|%|:1)\b'
}
```

**Step 7: Quantitative Standards Extraction**
```python
# Extract heights, setbacks, FSR, coverage with context
setback_patterns = [
    r'(?:front|side|rear)\s+setback[s]?\s*(?:of|is|must be|shall be)?\s*(\d+(?:\.\d+)?)\s*(m|metres?)',
    r'(\d+(?:\.\d+)?)\s*(m|metres?)\s+(?:front|side|rear)\s+setback',
    r'setback[s]?.*?(\d+(?:\.\d+)?)\s*(m|metres?)'
]
```

**Step 8: Clause Reference & Citation Network**
```python
# Build citation network between documents
citation_patterns = [
    r'[Cc]lause\s+(\d+(?:\.\d+)*)',
    r'[Ss]ection\s+(\d+(?:\.\d+)*)',
    r'pursuant to.*?([Cc]lause\s+\d+(?:\.\d+)*)',
    r'subject to.*?([Cc]lause\s+\d+(?:\.\d+)*)'
]
```

**Step 9: Authority Hierarchy Relationships**
```python
# Extract SEPP->LEP->DCP hierarchy and override relationships
hierarchy_patterns = [
    r'(SEPP.*?(?:overrides?|prevails? over|takes precedence).*?(?:LEP|DCP))',
    r'((?:this|the)\s+(?:LEP|DCP).*?implements?.*?SEPP)',
    r'(State Environmental Planning Policy.*?applies? to)'
]
```

**Step 10: Process & Compliance Relationships**
```python
# Extract DA processes, consent requirements, assessment criteria
process_patterns = [
    r'development consent.*?(?:is required|must be obtained)',
    r'(?:Council|consent authority).*?(?:must|shall).*?(?:consider|assess)',
    r'(?:exempt|complying|prohibited) development'
]
```

### PHASE 3: LLM ENHANCEMENT (Steps 11-15)

**Step 11: API Provider Setup & Testing**
**Required API Keys:**
```yaml
primary_provider:
  name: "OpenAI GPT-4"
  api_key: "OPENAI_API_KEY"
  model: "gpt-4o"
  rate_limit: "10,000 requests/day"
  cost_estimate: "$0.03/1K tokens"

fallback_provider_1:
  name: "Anthropic Claude"
  api_key: "ANTHROPIC_API_KEY" 
  model: "claude-3-5-sonnet-20241022"
  rate_limit: "5,000 requests/day"
  cost_estimate: "$0.015/1K tokens"

fallback_provider_2:
  name: "Local Ollama"
  model: "llama3.1:70b"
  endpoint: "http://localhost:11434"
  rate_limit: "unlimited"
  cost_estimate: "$0 (local)"

backup_provider:
  name: "Google Gemini"
  api_key: "GOOGLE_API_KEY"
  model: "gemini-1.5-pro"
  rate_limit: "1,500 requests/day"
  cost_estimate: "$0.0075/1K tokens"
```

**Step 12: Planning-Specific Prompt Engineering**
```python
planning_extraction_prompt = """
You are an expert NSW planning law analyst. Extract structured entities and relationships from this planning provision:

TEXT: {text}

EXTRACT:
1. ENTITIES:
   - Zones: R1, R2, B1, etc.
   - Measurements: heights, setbacks, ratios (with units)
   - Development types: dwelling house, dual occupancy, etc.
   - Authority levels: SEPP, LEP, DCP
   - Clause references: section X.X, clause Y.Y

2. RELATIONSHIPS:
   - Authority hierarchy: X overrides Y
   - Conditional logic: unless X then Y  
   - Process sequences: A requires B requires C
   - Spatial relationships: applies to, adjacent to

OUTPUT as structured JSON with confidence scores.
CONTEXT: NSW planning law, Inner West LGA focus.
"""
```

**Step 13: Batch Processing with Retry Logic**
```python
def extract_with_fallback(text_chunk):
    providers = [openai_gpt4, anthropic_claude, local_ollama, google_gemini]
    
    for provider in providers:
        try:
            result = provider.extract_entities(text_chunk)
            if validate_extraction_quality(result):
                return result
        except (APIError, RateLimitError, TimeoutError) as e:
            log_provider_failure(provider, e)
            continue
    
    # All providers failed - use rule-based fallback
    return rule_based_extraction(text_chunk)
```

**Step 14: Quality Validation & Verification**
```python
def validate_extraction_quality(extraction):
    validation_checks = [
        validate_zone_format(extraction.get('zones', [])),
        validate_measurement_units(extraction.get('measurements', [])),
        validate_clause_references(extraction.get('clauses', [])),
        validate_relationship_logic(extraction.get('relationships', []))
    ]
    
    # Require 80% of validations to pass
    return sum(validation_checks) / len(validation_checks) >= 0.8
```

**Step 15: Cross-Document Relationship Building**
```python
def build_citation_network(all_extractions):
    citation_graph = {}
    
    for doc_id, extraction in all_extractions.items():
        for relationship in extraction.get('relationships', []):
            if relationship['type'] == 'cites':
                source = f"{doc_id}#{relationship['source_clause']}"
                target = f"{relationship['target_doc']}#{relationship['target_clause']}"
                citation_graph[source] = citation_graph.get(source, []) + [target]
    
    return citation_graph
```

### PHASE 4: INTEGRATION & VALIDATION (Steps 16-20)

**Step 16: PostgreSQL Integration**
```sql
-- Enhanced schema for entities and relationships
CREATE TABLE research_assistant.extracted_entities (
    id SERIAL PRIMARY KEY,
    document_id INTEGER REFERENCES research_assistant.documents(id),
    entity_type VARCHAR(50), -- zone, measurement, clause_ref, dev_type
    entity_value TEXT,
    context_text TEXT,
    confidence_score NUMERIC(3,2),
    extraction_method VARCHAR(20), -- rule_based, llm_openai, llm_claude
    validation_status VARCHAR(20), -- validated, suspect, failed
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE research_assistant.extracted_relationships (
    id SERIAL PRIMARY KEY,
    source_entity_id INTEGER REFERENCES research_assistant.extracted_entities(id),
    target_entity_id INTEGER REFERENCES research_assistant.extracted_entities(id),
    relationship_type VARCHAR(50), -- overrides, implements, requires, cites
    confidence_score NUMERIC(3,2),
    context_text TEXT,
    extraction_method VARCHAR(20),
    validation_status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Step 17: Comprehensive Validation Suite**
```python
validation_tests = [
    test_zone_coverage(),           # Target: 80% zones identified
    test_setback_extraction(),      # Target: 60% setbacks with measurements  
    test_citation_network(),        # Target: 50% cross-references mapped
    test_authority_hierarchy(),     # Target: 90% SEPP/LEP/DCP relationships
    test_measurement_accuracy(),    # Target: 95% measurements with correct units
]
```

**Step 18: Performance & Cost Monitoring**
```python
extraction_metrics = {
    'documents_processed': 0,
    'entities_extracted': 0,
    'relationships_found': 0,
    'api_calls_made': {'openai': 0, 'anthropic': 0, 'local': 0},
    'total_cost_usd': 0.0,
    'processing_time_hours': 0.0,
    'quality_score': 0.0
}
```

**Step 19: Planning API Integration Testing**
```python
def test_planning_api_integration():
    # Test extracted zones against Planning API zones
    property_id = 1972074  # Test property
    api_data = planning_api.get_property(property_id)
    
    # Find extracted entities for R2 zone
    extracted_r2_provisions = db.query_entities_by_zone('R2')
    
    # Validate integration works
    compliance_results = generate_compliance_report(api_data, extracted_r2_provisions)
    
    return validate_compliance_results(compliance_results)
```

**Step 20: Final Acceptance Criteria**
```yaml
acceptance_criteria:
  entity_extraction:
    zones: ">80% coverage (target: 20,000 entities vs current 194)"
    measurements: ">1,000 setback/height measurements with units"
    clauses: ">2,000 clause references mapped"
  
  relationship_extraction:
    authority_hierarchy: ">200 SEPP->LEP->DCP relationships"
    citations: ">1,000 cross-document references"
    conditionals: ">500 unless/where/provided relationships"
  
  quality_metrics:
    validation_accuracy: ">85% automated validation pass rate"
    manual_verification: ">80% accuracy on sample verification"
    api_integration: "Planning API + extractions = working compliance reports"
  
  performance:
    processing_time: "<48 hours total pipeline"
    cost_control: "<$500 total API costs"
    data_integrity: "100% rollback capability, full audit trail"
```

### EXECUTION COMMANDS

**Environment Setup:**
```bash
# Set API keys
export OPENAI_API_KEY="your-openai-key"
export ANTHROPIC_API_KEY="your-anthropic-key"
export GOOGLE_API_KEY="your-google-key"

# Start local Ollama (fallback)
ollama serve
ollama pull llama3.1:70b
```

**Pipeline Execution:**
```bash
# Make executable and run
chmod +x execute_prp_e1.py
./venv_linux/Scripts/python.exe execute_prp_e1.py --mode=interactive
```

**Monitoring:**
```bash
# Real-time progress monitoring
tail -f logs/prp_e1_extraction_*.log

# Cost monitoring
./venv_linux/Scripts/python.exe monitor_extraction_costs.py
```

### SUCCESS METRICS DASHBOARD

After completion, the system will provide:
- **Entity Coverage:** From 194 zones → 20,000+ entities
- **Relationship Network:** From 0 citations → 1,000+ cross-references  
- **Business Value:** From document search → compliance intelligence platform
- **API Integration:** Planning API + entities = automated compliance reports

**Total Investment:** 48-hour automated pipeline, <$500 API costs
**ROI:** Transform $200/month search tool → $1,000+/month compliance platform