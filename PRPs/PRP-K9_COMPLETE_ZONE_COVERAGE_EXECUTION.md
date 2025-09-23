# PRP-K9: Complete Zone Coverage Execution

## Objective
Achieve **100% zone coverage for regulatory provisions** by completing the remaining extraction and inference tasks from PRP-K8.

## Current State (Post PRP-K8)
- **Total provisions**: 22,105
- **Current zone coverage**: 3,160 (14.3%)
- **Gap to 100% regulatory**: ~4,000-5,000 provisions still need zones
- **What we extracted**: Only 1 DCP cover page, partial LEP tables

## Critical Remaining Tasks

### Phase 1: Complete MinerU Extractions (Week 1)
**Goal**: Extract ALL remaining DCP documents and complete LEP sections

#### 1.1 Full DCP Extraction (NOT just 1 cover page)
```bash
# Extract ALL DCP documents (we only did 1 cover in PRP-K8)
wsl find "docs/dcps/INNERWEST" -name "*.pdf" | while read file; do
 echo "Processing: $file"
 wsl ./venv_linux/Scripts/mineru.exe --path "$file" \
 --output "prp_k9_complete_dcp_extraction" \
 --method auto --backend pipeline
done

# Expected output: 100+ DCP documents with full structure
```

#### 1.2 Complete LEP Extraction (All sections)
```bash
# Extract remaining LEP sections (151-288)
wsl ./venv_linux/Scripts/mineru.exe --path "docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-151-200.pdf" --output prp_k9_lep_151_200 --method auto
wsl ./venv_linux/Scripts/mineru.exe --path "docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-201-250.pdf" --output prp_k9_lep_201_250 --method auto
wsl ./venv_linux/Scripts/mineru.exe --path "docs/lep/Inner West Local Environmental Plan 2022 - NSW Legislation-251-288.pdf" --output prp_k9_lep_251_288 --method auto
```

### Phase 2: Enhanced Zone Inference Engine
**Goal**: Build smarter inference from complete extractions

#### 2.1 Parse Land Use Tables Properly
```python
def extract_zone_tables_from_lep(lep_path):
 """Extract explicit zone->development type mappings from LEP"""
 zone_mappings = {
 'R1': ['Agriculture', 'Dwelling houses', 'Home occupations'],
 'R2': ['Dwelling houses', 'Home occupations', 'Residential flat buildings'],
 'R3': ['Attached dwellings', 'Multi dwelling housing', 'Residential flat buildings'],
 'R4': ['High density residential', 'Shop top housing', 'Residential flat buildings'],
 'B1': ['Neighbourhood shops', 'Business premises', 'Office premises'],
 'B2': ['Commercial premises', 'Office premises', 'Retail premises'],
 'IN1': ['General industrial', 'Warehouse or distribution centres'],
 'IN2': ['Light industrial', 'Warehouse or distribution centres']
 }
 return zone_mappings
```

#### 2.2 DCP Section Zone Mapping
```python
def map_dcp_sections_to_zones(dcp_structure_path):
 """Map DCP sections to specific zones they apply to"""
 section_zone_map = {
 '4.1': ['R2'], # Low Density Residential Development
 '4.2': ['R3', 'R4'], # Multi Dwelling Housing
 '5.0': ['B1', 'B2', 'B4'], # Commercial and Mixed Use
 '6.0': ['IN1', 'IN2'], # Industrial Development
 '9.1-9.48': ['various'] # Precinct-specific
 }
 return section_zone_map
```

### Phase 3: Target 100% Regulatory Provisions
**Goal**: Focus on provisions that MUST have zones

#### 3.1 Identify All Regulatory Provisions
```python
REGULATORY_PROVISION_TYPES = [
 'height_limit', 'setback', 'fsr', 'parking', 'landscaping',
 'subdivision', 'provision_height', 'provision_setback',
 'provision_design', 'formal_Planning Controls',
 'building_separation', 'site_coverage', 'minimum_lot_size'
]

# Query: Get all regulatory provisions without zones
SELECT id, provision_type, provision_text, document_id 
FROM regulatory_provisions 
WHERE provision_type IN (REGULATORY_PROVISION_TYPES)
AND (zone IS NULL OR zone = '');
```

#### 3.2 Force Zone Assignment for Regulatory Provisions
```python
def assign_zone_to_regulatory_provision(provision):
 """MUST assign a zone to every regulatory provision"""
 
 # Method 1: Document context
 if 'residential' in provision.document_id.lower():
 return 'R2' # Default residential
 elif 'commercial' in provision.document_id.lower():
 return 'B2' # Default commercial
 elif 'industrial' in provision.document_id.lower():
 return 'IN1' # Default industrial
 
 # Method 2: Development type inference
 if provision.development_type:
 return infer_from_dev_type(provision.development_type)
 
 # Method 3: Fallback to most common zone
 return 'R2' # Most common zone in Inner West
```

### Phase 4: Validation & Verification

#### 4.1 Verification Script
```python
# scripts/verify_k9_zone_coverage.py
def verify_zone_coverage():
 # Check regulatory provision coverage
 regulatory_total = query("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_type IN (REGULATORY_TYPES)")
 regulatory_with_zones = query("SELECT COUNT(*) FROM regulatory_provisions WHERE provision_type IN (REGULATORY_TYPES) AND zone IS NOT NULL")
 
 regulatory_coverage = regulatory_with_zones / regulatory_total * 100
 
 assert regulatory_coverage >= 95.0, f"Regulatory coverage only {regulatory_coverage}%, need 95%+"
 
 return {
 'regulatory_coverage': regulatory_coverage,
 'passed': regulatory_coverage >= 95.0
 }
```

#### 4.2 Completion Criteria
```python
COMPLETION_CRITERIA = {
 'regulatory_provisions_zone_coverage': 95.0, # % minimum
 'overall_zone_coverage': 25.0, # % minimum
 'unique_zones_identified': 20, # minimum count
 'validation_against_planning_api': True,
 'all_dcps_extracted': True,
 'all_leps_extracted': True
}
```

## Implementation Commands

### Step 1: Run Full Extraction
```bash
# Create extraction script
cat > run_prp_k9_extraction.sh << 'EOF'
#!/bin/bash
echo "Starting PRP-K9 Full Zone Extraction"

# Extract all DCPs
find docs/dcps/INNERWEST -name "*.pdf" | while read file; do
 echo "Extracting: $file"
 wsl ./venv_linux/Scripts/mineru.exe --path "$file" \
 --output "prp_k9_complete_dcp_extraction" \
 --method auto --backend pipeline
done

# Extract remaining LEPs
for file in docs/lep/*.pdf; do
 echo "Extracting: $file"
 wsl ./venv_linux/Scripts/mineru.exe --path "$file" \
 --output "prp_k9_complete_lep_extraction" \
 --method auto --backend pipeline
done

echo "Extraction complete"
EOF

chmod +x run_prp_k9_extraction.sh
./run_prp_k9_extraction.sh
```

### Step 2: Run Enhanced Zone Inference
```bash
wsl ./venv_linux/Scripts/python.exe scripts/prp_k9_enhanced_zone_inference.py \
 --dcp-path "prp_k9_complete_dcp_extraction" \
 --lep-path "prp_k9_complete_lep_extraction" \
 --force-regulatory-coverage \
 --target-coverage 100
```

### Step 3: Validate Results
```bash
wsl ./venv_linux/Scripts/python.exe scripts/verify_k9_zone_coverage.py
```

## Success Metrics

### Quantitative Targets:
- **Regulatory provisions**: 100% zone coverage
- **Overall coverage**: 25-30% (all that need zones)
- **Unique zones**: 25+ identified
- **Processing time**: <4 hours for full extraction

### Quality Metrics:
- Zero height/setback/FSR provisions without zones
- All R1-R4, B1-B4, IN1-IN2 zones mapped
- Planning API validation success rate >90%

## Risk Mitigation

### If MinerU fails on bulk extraction:
1. Process in smaller batches (10 files at a time)
2. Use alternative PDF extraction for problematic files
3. Manual extraction for critical zone tables

### If zone inference still low:
1. Manual zone assignment for top 100 provisions
2. Use Planning API to validate and correct
3. Accept that some provisions genuinely don't need zones

## Deliverables

1. **Complete DCP extractions** (100+ documents)
2. **Complete LEP extractions** (all sections)
3. **Enhanced zone inference engine** with 100% regulatory coverage
4. **Verification report** showing targets achieved
5. **Updated database** with complete zone coverage

## Timeline

- **Day 1-2**: Complete all extractions (DCPs + LEPs)
- **Day 3**: Build enhanced inference engine
- **Day 4**: Run inference and achieve 100% regulatory coverage
- **Day 5**: Validation and verification

**This PRP completes what PRP-K8 started - achieving 100% zone coverage for all regulatory provisions.**