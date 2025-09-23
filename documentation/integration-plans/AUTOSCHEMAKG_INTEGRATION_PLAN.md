# AutoSchemaKG + LangExtract Integration Plan - Compliance Engine

## Overview
Replace inadequate regex at `setback_processor.py:40` with semantic understanding using **AutoSchemaKG + LangExtract** dual pipeline while maintaining all existing integrations.

**Goal**: Extract complex setback rules with precise source grounding for legally defensible compliance responses

**Key Innovation**: Combine AutoSchemaKG's semantic relationships with LangExtract's precise source citation to provide authority-backed compliance decisions.

---

## Phase 1: Dual Pipeline Setup (Immediate)

### 1. Install and Configure LangExtract
- [x] Install LangExtract: `pip install langextract`
- [x] Set up API keys (using existing OpenAI key)
- [x] Create regulatory extraction examples and prompts
- **Output**: Source-grounded rule extraction with exact citations
- **Files created**: `examples/regulatory-engine/langextract_config.py`

### 2. Create Hybrid Semantic Processor 
- [x] Build `dual_semantic_processor.py` combining both tools
- [x] **LangExtract**: Extract rules with precise source grounding
- [x] **AutoSchemaKG**: Build knowledge graph of rule relationships 
- [x] Merge outputs: semantic understanding + source authority
- **Files created**: `examples/regulatory-engine/dual_semantic_processor.py`

### 2.5. Implement Three-Tier Rule Classification System
- [x] **Tier 1**: Hard Requirements (enforceable) - "shall", "must", "not permitted"
- [x] **Tier 2**: Strong Guidance (pattern-based) - descriptive with measurements 
- [x] **Tier 3**: Descriptive Context (informational) - qualitative, historical
- [x] Add linguistic analysis for prescriptive vs descriptive language
- [x] Implement confidence-based enforcement logic
- **Files modified**: `examples/regulatory-engine/dual_semantic_processor.py`

### 3. Create Regulatory Processing Configs
- [ ] **LangExtract config**: Define setback extraction prompts and examples
- [ ] **AutoSchemaKG config**: Adapt `ProcessingConfig` for planning documents
- [ ] **Unified config**: Coordinate both pipelines
- **Key settings**: Source grounding + semantic relationships
- **Files to create**: `examples/regulatory-engine/regulatory_configs.py`

### 4. Test Dual Pipeline with Real DCP Text 
- [ ] Use existing `temp_extraction_*/` chunks as input
- [ ] Run both LangExtract + AutoSchemaKG pipelines
- [ ] Compare outputs: source citations + semantic triples
- **Validation**: Extract "0.9m OR 0.5 times building height" WITH source citation
- **Test data**: `temp_extraction_Ashfield/chunk_*.txt`

---

## Phase 2: Enhanced API Integration (Week 2)

### 5. Bridge Dual Pipeline → Compliance API
- [ ] Convert LangExtract + AutoSchemaKG outputs to enhanced `SetbackRule` format
- [ ] **New fields**: `source_text`, `source_location`, `confidence_score`, `highlighted_span`
- [ ] Update `extract_setback_rules()` function to consume dual outputs
- [ ] Maintain backward compatibility while adding source grounding
- **Critical**: Enhanced JSON with source authority
- **Files to modify**: `examples/regulatory-engine/setback_processor.py`

### 6. Update Compliance Checking Logic with Source Authority
- [ ] Modify `lib/api/compliance-check.ts` to handle semantic rules + citations
- [ ] Support conditional calculations with source justification
- [ ] Handle purpose-specific rules with regulatory backing
- [ ] **New capability**: "Rule applies because DCP Section 4.3.2 states: '...'"
- **Files to modify**: `lib/api/compliance-check.ts`, related API files

---

## Phase 3: Production Optimization (Week 3-4)

### 6. Performance & Caching
- [ ] Pre-process DCPs into knowledge graphs (one-time)
- [ ] Cache extracted rules in `public/regulatory-data/`
- [ ] Optimize LLM calls for production usage
- **Goal**: Sub-second compliance checking
- **Files to create**: Caching layer, batch processing scripts

### 7. Frontend Updates with Source Authority Display
- [ ] Update rule display to show semantic relationships + source citations
- [ ] Add confidence scores, source text, and regulatory references
- [ ] Implement interactive source highlighting (LangExtract visualization)
- [ ] Handle complex rule explanations with legal backing
- **UX**: "Rule applies because Ashfield DCP 2014, Section 4.3.2 states: *highlighted text*"
- **New feature**: Click to see full regulatory context
- **Files to modify**: Frontend components, add source citation UI

---

## Phase 4: Validation & Rollout

### 8. A/B Testing
- [ ] Run both regex and semantic extraction in parallel
- [ ] Compare accuracy on known test cases 
- [ ] Validate with planning experts
- **Metrics**: Precision, recall, edge case handling
- **Files to create**: Testing framework, comparison scripts

---

## Key Integration Points

### Input Sources
- `temp_extraction_Ashfield/chunk_*.txt`
- `temp_extraction_Leichhardt/chunk_*.txt` 
- `temp_extraction_Marrickville/chunk_*.txt`

### Processing Pipeline
```
DCP Text → AutoSchemaKG → Semantic Triples → Structured Rules → API Response
```

### Output Compatibility
- Must match existing `inner-west_setbacks.json` format
- Same API endpoints and response structure
- Gradual enhancement of rule explanations

### Current Problem Case → Dual Pipeline Solution
**Regex fails**: `r'side\s*setback.*?must\s*not\s*exceed\s*(\d+\.?\d*)\s*m'` 
**Real rule**: "Side setbacks shall be 0.9m minimum OR 0.5 times building height, whichever is greater"

**LangExtract should extract**:
```json
{
 "extraction_text": "Side setbacks shall be 0.9m minimum OR 0.5 times building height, whichever is greater",
 "source_location": "Page 45, Section 4.3.2, Paragraph 2", 
 "highlighted_span": [145, 234],
 "confidence": 0.95
}
```

**AutoSchemaKG should extract**:
- `(side_setback, has_minimum_distance, 0.9m)`
- `(side_setback, calculated_as, 0.5_times_building_height)`
- `(side_setback, selection_rule, whichever_is_greater)`

**Combined Output**: Semantic understanding + Legal authority = Defensible compliance decisions

---

## Immediate Next Steps - Dual Pipeline

1. **Install LangExtract** and set up API keys
2. **Create regulatory extraction examples** for LangExtract prompts
3. **Write dual_semantic_processor.py** combining both tools
4. **Test dual pipeline on Ashfield DCP** with real text 
5. **Compare outputs**: Regex vs LangExtract+AutoSchemaKG vs Dual Pipeline

---

## Status Tracking

**Current Phase**: Phase 1 - Core Integration 
**Started**: 2025-01-24 
**Last Updated**: 2025-01-24

### Completed Items
- Analyzed AutoSchemaKG pipeline from `atlas_full_pipeline.ipynb`
- Identified working examples in `examples/compliance/`
- Located actual DCP text in `temp_extraction_*/` folders
- Discovered LangExtract for precise source grounding
- Designed dual pipeline approach combining both tools

### In Progress
- Setting up dual pipeline integration (LangExtract + AutoSchemaKG)

### Blockers
- None currently identified

---

## Files to Track

### New Files to Create
- `examples/regulatory-engine/dual_semantic_processor.py` (main integration)
- `examples/regulatory-engine/langextract_config.py` (LangExtract setup)
- `examples/regulatory-engine/regulatory_configs.py` (unified config)
- Enhanced caching and optimization scripts
- Source citation UI components

### Existing Files to Modify 
- `examples/regulatory-engine/setback_processor.py` (replace regex with dual pipeline)
- `lib/api/compliance-check.ts` (handle semantic rules + source authority)
- Frontend rule display components (add source citations and highlighting)

### Reference Files
- `examples/compliance/atlas_full_pipeline.ipynb` (AutoSchemaKG pipeline)
- `examples/compliance/1_slice_kg_extraction.py` (AutoSchemaKG extraction)
- `examples/compliance/langextract-main/` (LangExtract examples and docs)
- `examples/regulatory-engine/setback_patterns.json` (pattern config)