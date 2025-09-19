# PRP-P2: Phase 2 - Land Use Table Parsing

## OBJECTIVE
Parse structured LEP land use tables to extract zone-specific development permissions in tabular format.

## SUCCESS CRITERIA
- [ ] Identify all LEP provisions containing land use tables
- [ ] Parse table structure: Zone → Development Type → Permission Status
- [ ] Extract 200+ zone/development type permission combinations
- [ ] Handle table variations across different LEPs
- [ ] Create structured development_permissions table

## TECHNICAL SPECIFICATION

### Phase 2A: Table Identification
```sql
-- Find provisions containing structured tables
SELECT id, zone, provision_text, document_id
FROM regulatory_provisions 
WHERE document_id IN (SELECT id FROM documents WHERE document_type = 'LEP')
AND (
    provision_text LIKE '%Land Use Table%'
    OR provision_text LIKE '%Zoning Table%'
    OR provision_text LIKE '%Permitted%Prohibited%'
    OR provision_text LIKE '%I%II%III%'  -- Roman numerals in tables
    OR provision_text LIKE '%zone objectives%'
)
ORDER BY zone;
```

### Phase 2B: Table Structure Recognition
Common LEP table patterns:
```
Pattern A - Standard Instrument:
Zone R2 Low Density Residential
1 Objectives of zone
2 Permitted without consent
3 Permitted with consent  
4 Prohibited

Pattern B - Tabular Format:
Development Type | Zone R2 | Zone R3 | Zone R4
Dwelling houses  |    I    |    I    |    I
Dual occupancy   |   II    |   II    |    I
Multi dwelling   |   III   |   II    |    I

Legend: I=Permitted, II=Consent, III=Prohibited
```

### Phase 2C: Parsing Algorithm
```python
def parse_land_use_table(provision_text, zone):
    """
    Parse LEP land use table structure
    Returns: List of (development_type, permission_status, conditions)
    """
    table_patterns = {
        'standard_instrument': parse_standard_instrument_table,
        'tabular_format': parse_tabular_format,
        'objective_list': parse_objective_list_format
    }
    # Detect table type and apply appropriate parser
```

## IMPLEMENTATION STEPS

### Step 1: Create Development Permissions Schema (10 minutes)
```sql
CREATE TABLE development_permissions (
    id INTEGER PRIMARY KEY,
    zone TEXT NOT NULL,
    development_type TEXT NOT NULL,
    permission_status TEXT NOT NULL, -- permitted/consent/prohibited
    conditions TEXT, -- Additional requirements
    source_provision_id INTEGER,
    lep_name TEXT,
    extraction_method TEXT, -- table_parsing/pattern_matching
    confidence_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(zone, development_type, source_provision_id)
);

CREATE INDEX idx_dev_perm_zone ON development_permissions(zone);
CREATE INDEX idx_dev_perm_type ON development_permissions(development_type);
```

### Step 2: Implement Table Parsers (45 minutes)
```python
class LEPTableParser:
    def __init__(self):
        self.development_type_mappings = {
            'dwelling house': 'dwelling_house',
            'dual occupancy': 'dual_occupancy',
            'multi dwelling housing': 'multi_dwelling_housing',
            'residential flat building': 'residential_flat_building',
            'shop': 'retail',
            'office premises': 'office',
            'warehouse': 'warehouse'
        }
    
    def parse_standard_instrument(self, text, zone):
        # Parse sections 2, 3, 4 for permissions
        pass
    
    def parse_tabular_format(self, text, zone):
        # Parse matrix-style tables
        pass
```

### Step 3: Execute Table Parsing (30 minutes)
```python
def phase2_parsing():
    # Get LEP provisions with table structures
    # Apply appropriate parser for each table type
    # Extract zone/dev_type/permission combinations
    # Store in development_permissions table
    # Handle parsing conflicts and duplicates
```

### Step 4: Cross-Reference Validation (25 minutes)
```python
def validate_table_parsing():
    # Compare parsed results against known standard instrument zones
    # Check for consistency across similar zones (R2 vs R3)
    # Validate against NSW standard instrument reference
    # Flag anomalies for manual review
```

## VERIFICATION CHECKLIST

### Automated Verification
- [ ] Table parsing completes without errors
- [ ] At least 200 zone/development type combinations extracted
- [ ] All extracted permissions have valid zone assignments
- [ ] No duplicate zone/development_type combinations per source
- [ ] All permission_status values are valid (permitted/consent/prohibited)

### Manual Verification (Sample 25 combinations)
- [ ] Parsed permissions match source LEP table
- [ ] Zone assignments are accurate
- [ ] Development type standardization is correct
- [ ] Permission status correctly interpreted
- [ ] Conditions field captures relevant requirements

### Quality Metrics
- [ ] Table parsing accuracy: >95%
- [ ] Zone coverage: >10 unique zones from LEPs
- [ ] Development type coverage: >12 unique standardized types
- [ ] Cross-LEP consistency: Similar zones have similar permissions

## DELIVERABLES

1. **development_permissions table** - Populated with parsed permissions
2. **table_parsing_report.json** - Parsing statistics and validation results
3. **parsing_validation_sample.csv** - Manual verification dataset
4. **lep_table_parser.py** - Reusable table parsing implementation
5. **anomaly_report.json** - Inconsistencies requiring manual review

## VERIFICATION SCRIPTS

### Automated Quality Checks
```python
def run_quality_checks():
    # Check for required zones (R1, R2, R3, R4, B1, B2, etc.)
    # Validate development type standardization
    # Check permission status distribution
    # Compare against NSW standard instrument expectations
```

### Sample Verification
```python
def generate_verification_sample():
    # Random sample of 25 parsed combinations
    # Include source provision text for manual verification
    # Generate CSV for planning expert review
```

## ROLLBACK PLAN
```sql
-- If parsing issues found
DELETE FROM development_permissions WHERE extraction_method = 'table_parsing';
-- Restore from backup if needed
```

## DEPENDENCIES
- **Requires:** PRP-P1 completion (permissibility patterns identified)
- **Feeds into:** PRP-P3 (development type standardization)

## ESTIMATED TIME
**2.5 hours total**
- Schema setup: 15 minutes
- Parser implementation: 60 minutes
- Execution: 45 minutes
- Validation: 30 minutes
- Documentation: 20 minutes

## COMPLETION CRITERIA
✅ All verification checkboxes completed
✅ development_permissions table populated with >200 combinations
✅ Manual verification sample shows >95% accuracy
✅ Anomaly report identifies <5% inconsistencies requiring review
✅ Ready for development type standardization (PRP-P3)