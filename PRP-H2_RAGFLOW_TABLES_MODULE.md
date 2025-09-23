# PRP-H2: RAGFlow Table/Diagram Extraction Module
## Structured Data Extraction with Verification

### EXECUTIVE ACCOUNTABILITY MATRIX
```yaml
module_id: PRP-H2_RAGFLOW_TABLES_2024_12_10
dependencies: Unstructured.io, RAGFlow components
validation_gates: 3
rollback_points: 2
success_criteria: Extract 80% of tables, 100% of height/FSR tables
error_tolerance: 10% for critical tables
```

### TABLE EXTRACTION TARGETS
```yaml
height_tables:
 expected: 20+ tables
 format: "Zone | Max Height | Storeys"
 example: "R2 | 8.5m | 2"
 
fsr_tables:
 expected: 15+ tables
 format: "Zone | FSR | Site Coverage"
 example: "R2 | 0.5:1 | 60%"
 
setback_tables:
 expected: 25+ tables
 format: "Lot Width | Front | Side | Rear"
 example: "<12m | 4.5m | 0.9m | 3m"
 
development_matrices:
 expected: 10+ matrices
 format: "Zone x Development Type"
 example: "R2: Dwelling=Yes, Shop=No"
```

### DIAGRAM EXTRACTION
```yaml
setback_diagrams:
 expected: 15+ diagrams
 extract: Measurements, angles, dimensions
 
height_planes:
 expected: 10+ diagrams 
 extract: Building envelope measurements
 
site_coverage:
 expected: 5+ diagrams
 extract: Percentage values, area calculations
```

### VERIFICATION PROCESS
1. **Table Detection**: Identify table boundaries
2. **Header Extraction**: Parse column headers
3. **Data Extraction**: Extract cell values with units
4. **Validation**: Check numeric values are reasonable
5. **Storage**: Save to ragflow_output/

### ERROR SCENARIOS
```yaml
malformed_table:
 action: Attempt repair, flag if failed
 
missing_headers:
 action: Infer from content patterns
 
merged_cells:
 action: Split and distribute values
 
image_tables:
 action: OCR extraction fallback
```

### SUCCESS METRICS
```yaml
minimum_requirements:
 tables_per_document: 2
 measurements_per_table: 5
 accuracy_rate: 95%
 
overall_targets:
 total_tables: 200+
 height_limits_extracted: 50+
 fsr_values_extracted: 40+
 setback_rules_extracted: 100+
```