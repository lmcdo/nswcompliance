# PRP-P3: Phase 3 - Development Type Standardization

## OBJECTIVE
Consolidate PRP-P1 and PRP-P2 datasets, add missing NSW Standard Instrument permissions, and standardize development type terminology to create comprehensive zone-based development permissions.

## SUCCESS CRITERIA
- [ ] Combine PRP-P1 patterns (958) + PRP-P2 permissions (14) datasets
- [ ] Add manual NSW Standard Instrument permissions for major zones
- [ ] Standardize development type terminology to NSW Standard Instrument format
- [ ] Target: 1000+ zone/development type combinations
- [ ] Create unified development_permissions table

## TECHNICAL SPECIFICATION

### Phase 3A: Development Type Inventory
```sql
-- Extract all unique development type mentions
SELECT DISTINCT development_type, COUNT(*) as usage_count
FROM regulatory_provisions 
WHERE development_type IS NOT NULL
UNION ALL
SELECT DISTINCT development_types_extracted, COUNT(*)
FROM permissibility_analysis
WHERE development_types_extracted IS NOT NULL
ORDER BY usage_count DESC;
```

### Phase 3B: NSW Standard Instrument Reference
Based on NSW Environmental Planning and Assessment Regulation 2021:
```python
NSW_STANDARD_INSTRUMENT_TYPES = {
    # Residential
    'dwelling_house': ['dwelling house', 'single dwelling', 'detached house', 'house'],
    'dual_occupancy': ['dual occupancy', 'duplex', 'two dwellings', 'dual occ'],
    'multi_dwelling_housing': ['multi dwelling housing', 'villa', 'townhouse', 'terrace', 'MDH'],
    'residential_flat_building': ['residential flat building', 'apartment', 'unit', 'RFB', 'flats'],
    'seniors_housing': ['seniors housing', 'retirement village', 'aged care'],
    
    # Commercial
    'retail_premises': ['shop', 'retail premises', 'retail', 'store'],
    'office_premises': ['office premises', 'office', 'commercial office'],
    'business_premises': ['business premises', 'business'],
    'restaurant': ['restaurant', 'cafe', 'food premises'],
    
    # Industrial  
    'warehouse': ['warehouse', 'storage premises', 'storage'],
    'light_industry': ['light industry', 'light industrial'],
    'general_industry': ['general industry', 'heavy industry', 'industrial'],
    
    # Infrastructure
    'roads': ['road', 'roads', 'street', 'transport corridor'],
    'utilities': ['electricity', 'water supply', 'sewerage', 'telecommunications']
}
```

### Phase 3C: Fuzzy Matching Algorithm
```python
def standardize_development_type(input_type):
    """
    Standardize development type using fuzzy matching and rules
    Returns: (standard_type, confidence_score, mapping_method)
    """
    # 1. Exact match
    # 2. Lowercase/trim match  
    # 3. Fuzzy string matching (Levenshtein distance)
    # 4. Keyword matching
    # 5. Manual review queue if confidence < 80%
```

## IMPLEMENTATION STEPS

### Step 1: Data Consolidation (30 minutes)
```python
def consolidate_prp_datasets():
    # Combine PRP-P1 patterns with PRP-P2 permissions
    # Extract zone/dev_type combinations from both sources
    # Identify gaps in major zones (R1-R4, B1-B6, IN1-IN2)
    # Prepare for NSW Standard Instrument insertion
```

### Step 2: NSW Standard Instrument Addition (45 minutes)
```python
NSW_STANDARD_PERMISSIONS = {
    'R2': {
        'dwelling_house': 'permitted',
        'dual_occupancy': 'consent',
        'multi_dwelling_housing': 'consent',
        'retail_premises': 'prohibited',
        'warehouse': 'prohibited'
    },
    'B1': {
        'retail_premises': 'permitted',
        'office_premises': 'permitted',
        'restaurant': 'consent',
        'warehouse': 'prohibited'
    }
    # Add for all major zones
}

def add_standard_permissions():
    # Insert known NSW Standard Instrument permissions
    # Fill gaps for major zone/dev type combinations
    # Ensure coverage of common planner queries
```

### Step 3: Create Unified Schema (15 minutes)
```sql
CREATE TABLE development_type_mappings (
    id INTEGER PRIMARY KEY,
    original_text TEXT NOT NULL UNIQUE,
    standardized_type TEXT NOT NULL,
    mapping_method TEXT, -- exact/fuzzy/keyword/manual
    confidence_score REAL,
    usage_count INTEGER,
    validated_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE standardization_conflicts (
    id INTEGER PRIMARY KEY,
    original_text TEXT,
    suggested_mappings TEXT, -- JSON array of options
    context_provisions TEXT, -- Sample provisions for manual review
    resolution_status TEXT DEFAULT 'pending',
    resolved_mapping TEXT,
    resolved_by TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Reference table for NSW Standard Instrument
CREATE TABLE nsw_standard_instrument_types (
    standard_type TEXT PRIMARY KEY,
    definition TEXT,
    category TEXT, -- residential/commercial/industrial/other
    requires_consent TEXT, -- typically/always/never
    common_zones TEXT -- JSON array of typical zones
);
```

### Step 4: Standardization & Mapping (30 minutes)
```python
def standardize_development_types():
    # Apply NSW Standard Instrument mappings to consolidated data
    # Use fuzzy matching for variations
    # Generate unified development_permissions table
    # Track mapping statistics
```

### Step 5: Validation & Target Achievement (20 minutes)
```python
def validate_standardization():
    # Check mapping consistency across similar provisions
    # Validate against NSW Standard Instrument categories
    # Sample verification by planning expert
    # Identify outliers and anomalies
```

## VERIFICATION CHECKLIST

### Automated Verification
- [ ] Standardization mapping created for all development types
- [ ] Confidence scores calculated for all mappings
- [ ] No unmapped development types remain (>80% confidence)
- [ ] All standardized types match NSW Standard Instrument format
- [ ] Circular mappings detected and resolved

### Quality Metrics
- [ ] Mapping accuracy: >95% (based on sample verification)
- [ ] Coverage: >95% of development type instances standardized
- [ ] Consistency: Same input always maps to same output
- [ ] NSW compliance: All standard types are valid Standard Instrument types
- [ ] Conflict resolution: <5% require manual review

### Manual Verification (Sample 30 mappings)
- [ ] Sample mappings are logically correct
- [ ] Fuzzy matches preserve original meaning
- [ ] Edge cases handled appropriately
- [ ] No semantic drift in standardization
- [ ] Planning expert review approves sample

## DELIVERABLES

1. **development_type_mappings table** - Complete mapping dictionary
2. **standardization_report.json** - Mapping statistics and quality metrics
3. **conflict_resolution_queue.csv** - Items requiring manual review
4. **validation_sample.csv** - Manual verification dataset
5. **dev_type_standardizer.py** - Reusable standardization implementation
6. **nsw_compliance_check.json** - Validation against Standard Instrument

## QUALITY ASSURANCE SCRIPTS

### Consistency Validation
```python
def check_mapping_consistency():
    # Ensure same input always produces same output
    # Check for circular or conflicting mappings
    # Validate confidence score calculations
```

### NSW Compliance Check
```python
def validate_nsw_compliance():
    # Check all standardized types against Standard Instrument
    # Flag non-standard types for review
    # Validate typical zone assignments
```

### Sample Generation
```python
def generate_validation_sample():
    # Stratified sample across confidence scores
    # Include edge cases and fuzzy matches
    # Generate review spreadsheet for planning expert
```

## ROLLBACK PLAN
```sql
-- Restore original development types if issues found
UPDATE regulatory_provisions 
SET development_type = development_type_original 
WHERE development_type_original IS NOT NULL;

-- Clear standardization tables
DELETE FROM development_type_mappings;
DELETE FROM standardization_conflicts;
```

## DEPENDENCIES
- **Requires:** PRP-P1 and PRP-P2 completion (extraction and parsing complete)
- **Feeds into:** PRP-P4 (verification and quality assurance)

## ESTIMATED TIME
**2.5 hours total**
- Data consolidation: 30 minutes
- NSW Standard Instrument addition: 45 minutes
- Schema setup: 15 minutes
- Standardization & mapping: 30 minutes
- Validation: 20 minutes

## COMPLETION CRITERIA
✅ PRP-P1 and PRP-P2 datasets successfully consolidated
✅ 1000+ zone/development type combinations achieved
✅ NSW Standard Instrument permissions added for major zones
✅ Development type standardization accuracy >95%
✅ Unified development_permissions table created
✅ Ready for consolidated dataset testing (PRP-P4)