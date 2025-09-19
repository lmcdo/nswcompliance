# PRP-P1: Phase 1 - Permissibility Pattern Extraction

## OBJECTIVE
Extract development permissibility patterns from regulatory provisions to enable "What can I build in [zone]?" queries.

## SUCCESS CRITERIA
- [ ] Identify all provisions containing permission keywords
- [ ] Extract 500+ permissibility statements
- [ ] Categorize provisions by permission type (permitted/prohibited/consent)
- [ ] Generate permissibility pattern analysis report
- [ ] Create extraction validation dataset

## TECHNICAL SPECIFICATION

### Phase 1A: Pattern Discovery
```sql
-- Target provisions with permissibility keywords
SELECT id, zone, provision_text, document_id
FROM regulatory_provisions 
WHERE provision_text LIKE '%permitted%' 
   OR provision_text LIKE '%prohibited%' 
   OR provision_text LIKE '%consent%'
   OR provision_text LIKE '%development may%'
   OR provision_text LIKE '%purposes%'
   OR provision_text LIKE '%following development%'
ORDER BY zone, document_id;
```

### Phase 1B: Pattern Classification
Create classification for extracted patterns:
- **Type A:** "The following development is permitted: (a) dwelling houses"
- **Type B:** "Development for X purposes is prohibited"  
- **Type C:** "Development may be carried out with consent"
- **Type D:** "Subject to this Plan, development for X is permitted"

### Phase 1C: Extraction Algorithm
```python
def extract_permissibility_patterns(provision_text):
    patterns = {
        'permitted_without_consent': r'permitted without consent.*?(?:\(.*?\)|\d+\..*?(?=\d+\.|$))',
        'permitted_with_consent': r'permitted with consent.*?(?:\(.*?\)|\d+\..*?(?=\d+\.|$))',
        'prohibited': r'prohibited.*?(?:\(.*?\)|\d+\..*?(?=\d+\.|$))',
        'development_may': r'development may.*?(?:\(.*?\)|\d+\..*?(?=\d+\.|$))'
    }
    # Extract and return structured data
```

## IMPLEMENTATION STEPS

### Step 1: Create Analysis Tables (15 minutes)
```sql
CREATE TABLE permissibility_analysis (
    id INTEGER PRIMARY KEY,
    provision_id INTEGER,
    zone TEXT,
    pattern_type TEXT,
    extracted_text TEXT,
    development_types TEXT, -- JSON array
    permission_status TEXT, -- permitted/prohibited/consent
    confidence_score REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE pattern_validation (
    id INTEGER PRIMARY KEY,
    pattern_type TEXT,
    sample_text TEXT,
    expected_result TEXT,
    validation_status TEXT -- pass/fail/manual_review
);
```

### Step 2: Execute Pattern Extraction (30 minutes)
```python
def phase1_extraction():
    # Connect to database
    # Run permissibility query
    # Apply extraction patterns
    # Store results in permissibility_analysis table
    # Generate summary statistics
```

### Step 3: Quality Validation (20 minutes)
```python
def validate_extraction():
    # Sample 50 random extractions
    # Manual verification against source text
    # Calculate accuracy metrics
    # Flag false positives/negatives
```

## VERIFICATION CHECKLIST

### Automated Verification
- [ ] Pattern extraction runs without errors
- [ ] At least 500 provisions identified with permissibility keywords
- [ ] All extractions have valid zone assignments
- [ ] No duplicate pattern extractions
- [ ] JSON development_types arrays are valid

### Manual Verification (Sample 20 cases)
- [ ] Extracted text accurately represents permission logic
- [ ] Zone assignment is correct for sample provisions
- [ ] Development types correctly identified
- [ ] Permission status correctly classified

### Quality Metrics
- [ ] Pattern extraction accuracy: >90%
- [ ] Zone coverage: >15 unique zones
- [ ] Permission type coverage: All 3 types (permitted/prohibited/consent)
- [ ] Development type diversity: >8 unique types identified

## DELIVERABLES

1. **permissibility_analysis table** - Populated with extracted patterns
2. **Phase1_extraction_report.json** - Summary statistics and metrics
3. **validation_sample.csv** - Manual verification dataset
4. **phase1_extraction_script.py** - Reusable extraction implementation

## ROLLBACK PLAN
```sql
-- If issues found, clean up tables
DROP TABLE IF EXISTS permissibility_analysis;
DROP TABLE IF EXISTS pattern_validation;
```

## NEXT PRP DEPENDENCY
This PRP must complete successfully before PRP-P2 (Land Use Table Parsing) can begin.

## ESTIMATED TIME
**2 hours total**
- Setup: 30 minutes
- Extraction: 45 minutes  
- Validation: 30 minutes
- Documentation: 15 minutes

## COMPLETION CRITERIA
✅ All verification checkboxes completed
✅ Phase1_extraction_report.json shows >90% accuracy
✅ Manual validation sample shows consistent results
✅ Ready for Phase 2 land use table parsing