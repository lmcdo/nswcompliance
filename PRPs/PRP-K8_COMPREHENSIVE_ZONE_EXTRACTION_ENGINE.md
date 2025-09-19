# PRP-K8: Comprehensive Zone Extraction & Mapping Engine

## Objective
Achieve **100% zone coverage for regulatory provisions** by implementing intelligent zone extraction, document structure analysis, and validation against NSW Planning API data.

## Current State Analysis
- **Total provisions**: 22,105
- **Current zone coverage**: 1,924 (8.7%)
- **Critical gap**: 100% of height/setback/FSR provisions lack zones
- **Root cause**: Zone assignment logic failure, not extraction failure

## Technical Implementation Strategy

### WSL2 Environment Requirements
```bash
# MinerU requires WSL2 environment with specific antlr4 version
wsl ./venv_linux/Scripts/pip.exe install 'antlr4-python3-runtime==4.9.3' --force-reinstall

# Verify MinerU functionality
wsl ./venv_linux/Scripts/mineru.exe --help

# Set UTF-8 encoding for proper PDF text extraction
wsl export PYTHONUTF8=1
wsl export PYTHONIOENCODING=utf-8
```

### Database Integration Strategy: Merging RAG-Anything Data + Zone Extraction

#### Existing RAG-Anything Data to PRESERVE:
```
✅ KEEP IN FINAL DATABASE:
- autoschemakg_data_ollama_final/*.json     # Images, diagrams, tables, captions
- langextract_verified_output/*.json       # Verified provisions with relationships  
- output_structured/                        # Document structure and metadata
```

#### How PRP-K8 Zone Data INTEGRATES with Existing Data:

**Current Database Schema (22,105 provisions):**
- ✅ **Existing provision text** (from RAG-Anything)
- ✅ **Images/diagrams/tables** (from RAG-Anything) 
- ✅ **Document relationships** (from RAG-Anything)
- ❌ **Zone field**: 91.3% missing (PRP-K8 fixes this)

**PRP-K8 ADDS zone data to existing provisions:**
```sql
-- PRP-K8 updates existing records, doesn't replace them
UPDATE regulatory_provisions 
SET 
    zone = 'R2',                           -- NEW: from zone inference
    zone_confidence = 0.85,                -- NEW: confidence score  
    zone_inference_method = 'document_structure', -- NEW: how zone was inferred
    zone_validation_status = 'validated'    -- NEW: Planning API validation
WHERE provision_id = existing_provision_id;

-- Existing RAG-Anything data stays unchanged:
-- provision_text, images, tables, relationships, etc.
```

#### Integration Workflow:
1. **Keep all existing data** (images, tables, relationships from RAG-Anything)
2. **Add new zone fields** to existing regulatory_provisions records  
3. **Link zone data** to existing images/diagrams where relevant
4. **Enhance search** - now provisions can be filtered by zone AND include existing images/tables

### Phase 1: Enhanced Document Structure Extraction
**Goal**: Parse complete DCP/LEP hierarchies to identify zone-specific sections

#### 1.1 Extract ONLY 2 Critical Missing Documents (MinerU MUST Work)
```bash
# Prerequisites: Fix MinerU antlr issues in WSL2 (MUST WORK)
wsl ./venv_linux/Scripts/pip.exe install 'antlr4-python3-runtime==4.9.3' --force-reinstall
wsl export PYTHONUTF8=1
wsl export PYTHONIOENCODING=utf-8

# CRITICAL EXTRACTION 1: LEP Land Use Tables (Zone → Development Type Mapping)
wsl ./venv_linux/Scripts/mineru.exe parse "docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-1-50.pdf" --output prp_k8_lep_land_use_tables --method auto

# CRITICAL EXTRACTION 2: Complete DCP Structure Mapping (Section → Zone Context)  
# Extract complete DCP documents to understand section hierarchy and zone applicability
wsl find "docs/dcps/INNERWEST" -name "*.pdf" -exec ./venv_linux/Scripts/mineru.exe parse {} --output prp_k8_dcp_structure --method auto --preserve-hierarchy \;

# INTEGRATION: Merge with existing RAG-Anything data
wsl ./venv_linux/Scripts/python.exe scripts/build_comprehensive_zone_mapping.py \
  --existing-raganything "autoschemakg_data_ollama_final" \
  --lep-tables "prp_k8_lep_land_use_tables" \
  --dcp-structure "prp_k8_dcp_structure" \
  --planning-api-validation \
  --output "prp_k8_complete_zone_system"
```

**⚠️ CRITICAL: 2 Missing Pieces That MinerU MUST Extract:**

```
CRITICAL MISSING 1: LEP Land Use Tables (Zone → Development Type Mapping)
📍 Location: "docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-1-50.pdf" 
🎯 Purpose: Map development types like "Commercial Mixed Use" → B1/B2/B4 zones
📊 Content: Zone permission matrices, land use definitions
→ Output: prp_k8_lep_land_use_tables/

CRITICAL MISSING 2: Complete DCP Section → Zone Context Mapping  
📍 Location: "docs/dcps/INNERWEST" (complete structure analysis)
🎯 Purpose: Understand which DCP sections apply to which zones
📊 Content: Document hierarchy, section-to-zone relationships
→ Output: prp_k8_dcp_structure/
```

**What RAG-Anything Already Provides (KEEP):**
- ✅ 1,247+ regulatory clauses with content
- ✅ 156 regulatory tables (parking, setbacks, heights)
- ✅ Images, diagrams, complex layouts
- ✅ Cross-references and relationships

**What Planning API Provides:**
- ✅ Property → zone mappings (validation)
- ✅ Current zone boundaries and status  
- ✅ Development controls (height, FSR)

**Target Documents:**

#### LEP Documents (Primary Zone Sources):
```
docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-1-50.pdf      # MISSING SECTIONS
docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-51-100.pdf    # ✅ EXTRACTED
docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-101-150.pdf   # ✅ EXTRACTED  
docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-151-200.pdf   # ⚠️  PARTIAL
docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-201-250.pdf   # ⚠️  PARTIAL
docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-251-288.pdf   # ⚠️  PARTIAL
docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation.pdf           # ✅ COMPLETE DOC
```

#### DCP Documents (Zone-Specific Controls):
```
docs/dcps/INNERWEST/leichhardt/Leichhardt DCP 2013 - 12 - Part G Section 1-12 - Amdt 19 - Nov 2023-*.pdf
docs/dcps/INNERWEST/Marrickville/Marrickville DCP 2011 - *.pdf
docs/dcps/INNERWEST/*/Inner West Ashfield DCP 2016 - *.pdf
```

#### SEPP Documents (State-Level Zones):
```
docs/sepps/State Environmental Planning Policy (Housing) 2021 - NSW Legislation.pdf
docs/sepps/State Environmental Planning Policy (Industry and Employment) 2021 - NSW Legislation.pdf
docs/sepps/State Environmental Planning Policy (Biodiversity and Conservation) 2021 - NSW Legislation.pdf
```

#### 1.2 Structured Data Extraction
- **Table extraction**: LEP zone/use matrices  
- **Section hierarchy**: Map document sections to zones
- **Geographic references**: Extract suburb/street zone mentions
- **Cross-references**: Link provisions to zone-specific clauses

### Phase 2: Multi-Layer Zone Inference Engine  
**Goal**: 100% zone assignment for regulatory provisions

#### 2.1 Document Structure Mapping
```python
# Primary zone inference method
def infer_zone_from_document_structure(provision):
    - Extract parent section headers
    - Match against zone patterns: "R2 Residential", "Commercial B1"  
    - Inherit zone from document context
    - Confidence: HIGH (80-95%)
```

#### 2.2 Development Type Cross-Reference
```python  
# Secondary inference using existing development_type field
def infer_zone_from_development_type(provision):
    - "Low Density Residential" → R2
    - "Commercial Mixed Use" → B1/B2/B4
    - "Industrial Development" → IN1/IN2
    - Cross-reference with LEP zone objectives
    - Confidence: MEDIUM (60-80%)
```

#### 2.3 Text Pattern Analysis
```python
# Tertiary inference from provision text
def infer_zone_from_text_patterns(provision):
    - Direct mentions: "in R2 zones", "B1 zoned land"  
    - Street/address references → GIS lookup
    - Spatial keywords: "residential areas", "commercial centres"
    - Confidence: LOW-MEDIUM (40-70%)
```

### Phase 3: Planning API Validation Integration
**Goal**: Validate and improve zone assignments using existing NSW Planning API

#### 3.1 Ground Truth Validation Service
```python
class PlanningAPIValidator:
    def validate_zone_assignment(self, address_sample, inferred_zone):
        # Use existing API calls:
        # 1. Get propId from address
        # 2. Get zone data from layerintersect API  
        # 3. Compare with our inference
        # 4. Update confidence scores
```

**API Integration Points:**
- **Address → Zone**: `planning/viewersf/V1/ePlanningApi/address`
- **Zone Details**: `planning/viewersf/V1/ePlanningApi/layerintersect?layers=epi`
- **Property Context**: `maps.six.nsw.gov.au/arcgis/rest/services/public/Valuation`

#### 3.2 Confidence Scoring System
```python
CONFIDENCE_LEVELS = {
    'HIGH': 0.85-1.0,    # Direct zone mention, validated against API
    'MEDIUM': 0.60-0.84, # Document structure inference, partial validation  
    'LOW': 0.40-0.59,    # Pattern matching only
    'REJECT': 0.0-0.39   # Conflicting signals, needs manual review
}
```

### Phase 4: Automated Verification & Quality Assurance

#### 4.1 Verification Scripts
```python
# scripts/verify_zone_assignments.py
def run_verification_suite():
    1. Sample 100 provisions with inferred zones
    2. Validate against Planning API where possible
    3. Generate accuracy report by inference method
    4. Identify systematic errors for correction
```

#### 4.2 Completion Tracking
```python  
# Automatic progress markers
class ZoneMappingProgress:
    def track_completion(self):
        - Total provisions processed
        - Zone assignment success rate by method
        - Validation accuracy against API
        - Remaining gaps and recommended actions
```

## Implementation Phases

### **Phase 1: Extract ONLY 2 Critical Missing Pieces (Week 1)**
```bash
# Prerequisites: Fix MinerU antlr4 issues (MUST WORK)
wsl ./venv_linux/Scripts/pip.exe install 'antlr4-python3-runtime==4.9.3' --force-reinstall
wsl export PYTHONUTF8=1
wsl export PYTHONIOENCODING=utf-8

# CRITICAL 1: Extract LEP Land Use Tables (Zone → Development Type mapping)
wsl ./venv_linux/Scripts/mineru.exe parse "docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-1-50.pdf" --output prp_k8_lep_land_use_tables --method auto

# CRITICAL 2: Extract complete DCP structure (Section → Zone context)
wsl find "docs/dcps/INNERWEST" -name "*.pdf" -exec ./venv_linux/Scripts/mineru.exe parse {} --output prp_k8_dcp_structure --method auto --preserve-hierarchy \;

# Step 3: Build comprehensive zone mapping using ALL data sources
wsl ./venv_linux/Scripts/python.exe scripts/build_comprehensive_zone_mapping.py \
  --existing-raganything "autoschemakg_data_ollama_final" \
  --lep-tables "prp_k8_lep_land_use_tables" \
  --dcp-structure "prp_k8_dcp_structure" \
  --planning-api-validation
```

**Tasks:**
- [ ] Extract LEP sections 1-50 (Land Use Tables) ✅ **Path**: `docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-1-50.pdf`
- [ ] Extract complete DCP structure for zone context ✅ **Path**: `docs/dcps/INNERWEST/`
- [ ] Build zone mapping matrix using RAG-Anything + new extractions + Planning API
- [ ] **Verification**: Validate against Planning API (100 sample properties)

### **Phase 2: Zone Inference Engine (Week 2)**
- [ ] Implement document structure inference (primary method)
- [ ] Implement development type cross-reference (secondary)
- [ ] Implement text pattern analysis (tertiary)
- [ ] **Verification**: Test on 500 provision sample, target 80% accuracy

### **Phase 3: Planning API Integration (Week 2-3)**  
- [ ] Build Planning API validation service
- [ ] Implement confidence scoring system
- [ ] Validate inference accuracy against API data
- [ ] **Verification**: Achieve 90%+ accuracy on regulatory provisions

### **Phase 4: Quality Assurance (Week 3)**
```bash
# Step 1: Run zone verification suite against Planning API (WSL2 for network calls)
wsl ./venv_linux/Scripts/python.exe scripts/zone_verification_suite.py --sample-size 100

# Step 2: Run completion tracking
wsl ./venv_linux/Scripts/python.exe scripts/prp_k8_completion_tracker.py

# Step 3: Generate final validation report  
wsl ./venv_linux/Scripts/python.exe scripts/generate_zone_coverage_report.py --output "PRP_K8_COMPLETION_REPORT.md"
```
- [ ] Build automated verification scripts ✅ **Created**: `scripts/zone_verification_suite.py`
- [ ] Implement completion tracking dashboard ✅ **Created**: `scripts/prp_k8_completion_tracker.py`
- [ ] Run full database zone assignment using extracted documents from **Phase 1**
- [ ] **Target**: 100% zone coverage for height/setback/FSR provisions

## Success Metrics

### **Quantitative Targets:**
- **Regulatory provisions**: 100% zone coverage (height, setback, FSR, parking)
- **Overall coverage**: 15-25% (excluding policy/guidance provisions)
- **Validation accuracy**: 95%+ against Planning API
- **Processing time**: <2 hours for full database

### **Qualitative Validation:**
- Manual review of 100 high-value provisions
- Cross-check with planning consultant
- User acceptance testing with property queries

## Risk Mitigation

### **Technical Risks:**
- **Document structure variation**: Build flexible parsing with fallback methods
- **API rate limiting**: Implement caching and batch processing
- **Zone boundary edge cases**: Flag for manual review with LOW confidence

### **Data Quality Risks:**  
- **Outdated zoning**: Use API currency dates for validation
- **Multiple zone overlays**: Capture all applicable zones/constraints
- **Document amendments**: Track LEP/DCP amendment dates

## Deliverables

1. **Enhanced extraction scripts** with structure preservation
2. **Multi-layer zone inference engine** with confidence scoring
3. **Planning API validation service** integrated with existing endpoints
4. **Automated verification suite** with progress tracking
5. **Updated database** with 100% regulatory provision zone coverage
6. **Documentation** of zone assignment methodology and accuracy metrics

## Integration with Existing System

**Database Schema Updates:**
- Add `zone_confidence` field (0.0-1.0)
- Add `zone_inference_method` field (document_structure|dev_type|text_pattern)
- Add `validation_status` field (validated|pending|failed)

**API Enhancements:**
- Leverage existing Planning API integration
- Extend property search with zone-specific provision filtering
- Add zone validation endpoints for quality assurance

This PRP transforms the compliance engine from a document search tool into a precise, zone-aware regulatory advisor with 100% coverage of compliance-critical provisions.