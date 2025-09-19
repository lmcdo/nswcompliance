# PRP-Q1: Assessment Pathway Determination Engine

## OBJECTIVE
Extract and implement development assessment pathway logic from existing SEPP (Exempt and Complying) provisions (2,186 provisions already in database) to determine whether development requires DA, CDC, or is exempt.

## SUCCESS CRITERIA
- [ ] Extract exempt development criteria from existing SEPP provisions
- [ ] Extract complying development criteria from existing SEPP provisions
- [ ] Create decision tree logic for pathway determination
- [ ] Achieve 95%+ accuracy on test scenarios
- [ ] Response time <500ms for pathway queries
- [ ] Create assessment_pathways table with 100+ pathway rules

## TECHNICAL SPECIFICATION

### Phase Q1A: Extract Exempt Development Criteria
```sql
-- Extract exempt development rules from existing SEPP provisions
SELECT
    document_id,
    provision_text,
    development_type,
    zone
FROM regulatory_provisions
WHERE LOWER(document_id) LIKE '%exempt%'
AND (
    LOWER(provision_text) LIKE '%does not require%consent%' OR
    LOWER(provision_text) LIKE '%exempt development%' OR
    LOWER(provision_text) LIKE '%no consent required%'
)
ORDER BY zone, development_type;
```

### Phase Q1B: Extract Complying Development Criteria
```sql
-- Extract complying development rules
SELECT
    document_id,
    provision_text,
    development_type,
    zone
FROM regulatory_provisions
WHERE LOWER(document_id) LIKE '%complying%'
AND (
    LOWER(provision_text) LIKE '%complying development%' OR
    LOWER(provision_text) LIKE '%may be carried out%certificate%' OR
    LOWER(provision_text) LIKE '%cdc%'
)
ORDER BY zone, development_type;
```

### Phase Q1C: Decision Tree Logic
```python
class AssessmentPathwayEngine:
    def determine_pathway(self, zone: str, development_type: str,
                         site_area: float = None, height: float = None) -> Dict:
        """
        Determine development assessment pathway
        Returns: exempt, complying, or development_application
        """
        # Check exempt criteria first
        if self.is_exempt(zone, development_type, site_area, height):
            return {
                'pathway': 'exempt',
                'requirements': 'No approval required',
                'confidence': 0.95
            }

        # Check complying criteria
        if self.is_complying(zone, development_type, site_area, height):
            return {
                'pathway': 'complying',
                'requirements': 'CDC required',
                'certifier': 'Council or Private',
                'confidence': 0.9
            }

        # Default to DA
        return {
            'pathway': 'development_application',
            'requirements': 'DA required',
            'assessment_path': 'Council assessment',
            'confidence': 0.85
        }
```

## IMPLEMENTATION STEPS

### Step 1: Create Assessment Pathways Schema (15 minutes)
```sql
CREATE TABLE assessment_pathways (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone TEXT NOT NULL,
    development_type TEXT NOT NULL,
    pathway_type TEXT CHECK(pathway_type IN ('exempt', 'complying', 'da_required')),
    max_site_area REAL,
    max_height REAL,
    max_floor_area REAL,
    additional_criteria TEXT,  -- JSON
    source_provision_id INTEGER,
    source_document TEXT,
    confidence_score REAL DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(zone, development_type, pathway_type)
);

CREATE TABLE pathway_criteria (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pathway_id INTEGER REFERENCES assessment_pathways(id),
    criterion_type TEXT,  -- height_limit, site_area, setback, etc.
    criterion_operator TEXT,  -- less_than, greater_than, equals
    criterion_value TEXT,
    criterion_unit TEXT,
    is_mandatory BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_pathway_zone_dev ON assessment_pathways(zone, development_type);
CREATE INDEX idx_pathway_type ON assessment_pathways(pathway_type);
```

### Step 2: Extract Exempt Development Rules (30 minutes)
```python
def extract_exempt_development_rules():
    """Extract exempt development rules from SEPP provisions"""

    # Query existing SEPP Exempt and Complying provisions
    provisions = query_exempt_provisions()

    rules = []
    for provision in provisions:
        # Pattern matching for exempt criteria
        if 'dwelling' in provision.text.lower():
            if 'single storey' in provision.text.lower():
                rules.append({
                    'development_type': 'dwelling_alterations',
                    'pathway': 'exempt',
                    'max_height': 3.8,
                    'conditions': ['single_storey', 'no_heritage']
                })

        if 'carport' in provision.text.lower():
            if 'maximum' in provision.text.lower() and 'area' in provision.text.lower():
                # Extract numeric values
                area = extract_numeric_value(provision.text, 'area')
                rules.append({
                    'development_type': 'carport',
                    'pathway': 'exempt',
                    'max_area': area,
                    'conditions': ['behind_building_line']
                })

    return rules
```

### Step 3: Extract Complying Development Rules (30 minutes)
```python
def extract_complying_development_rules():
    """Extract complying development rules from SEPP provisions"""

    provisions = query_complying_provisions()

    rules = []
    for provision in provisions:
        # Pattern matching for complying criteria
        if 'dwelling house' in provision.text.lower():
            if 'maximum height' in provision.text.lower():
                height = extract_numeric_value(provision.text, 'height')
                rules.append({
                    'development_type': 'dwelling_house',
                    'pathway': 'complying',
                    'zone': extract_zone(provision.text),
                    'max_height': height,
                    'max_site_coverage': 0.6,
                    'conditions': ['not_heritage', 'not_flood']
                })

    return rules
```

### Step 4: Build Decision Tree Engine (25 minutes)
```python
def build_pathway_decision_tree():
    """Build decision tree for pathway determination"""

    # Load extracted rules
    exempt_rules = load_exempt_rules()
    complying_rules = load_complying_rules()

    # Create decision nodes
    decision_tree = {
        'dwelling_house': {
            'R1': check_dwelling_r1_pathway,
            'R2': check_dwelling_r2_pathway,
            'R3': check_dwelling_r3_pathway
        },
        'alterations': {
            'all_zones': check_alterations_pathway
        },
        'commercial': {
            'B1': check_commercial_b1_pathway,
            'B2': check_commercial_b2_pathway
        }
    }

    return decision_tree
```

### Step 5: Create Verification Tests (20 minutes)
```python
def run_pathway_verification():
    """Verify pathway determination accuracy"""

    test_scenarios = [
        {
            'development': 'dwelling_alterations',
            'zone': 'R2',
            'height': 3.5,
            'expected': 'exempt'
        },
        {
            'development': 'dwelling_house',
            'zone': 'R2',
            'height': 8.5,
            'site_area': 450,
            'expected': 'complying'
        },
        {
            'development': 'residential_flat_building',
            'zone': 'R2',
            'expected': 'da_required'
        }
    ]

    results = []
    for scenario in test_scenarios:
        pathway = determine_pathway(
            scenario['zone'],
            scenario['development'],
            scenario.get('height'),
            scenario.get('site_area')
        )

        results.append({
            'test': scenario,
            'result': pathway,
            'passed': pathway['pathway'] == scenario['expected']
        })

    return results
```

## VERIFICATION CHECKLIST

### Automated Verification
- [ ] 2,186 SEPP Exempt/Complying provisions processed
- [ ] 100+ pathway rules extracted
- [ ] Decision tree covers major development types
- [ ] Test scenarios achieve 95%+ accuracy
- [ ] Response time <500ms per query

### Quality Metrics
- [ ] Exempt development rules: >30 extracted
- [ ] Complying development rules: >50 extracted
- [ ] DA required rules: Clear defaults
- [ ] Zone coverage: R1-R4, B1-B4, IN1-IN2
- [ ] Development type coverage: >20 types

### Manual Verification
- [ ] Sample pathway determinations logical
- [ ] Criteria thresholds match SEPP standards
- [ ] Decision tree handles edge cases
- [ ] Clear distinction between pathways

## DELIVERABLES

1. **assessment_pathways table** - Complete pathway rules database
2. **pathway_determination.py** - Decision tree engine implementation
3. **pathway_extraction_report.json** - Statistics on extracted rules
4. **verification_results.csv** - Test scenario results
5. **pathway_api_endpoint.py** - API integration for pathway queries

## ESTIMATED TIME
**2 hours total**
- Schema creation: 15 minutes
- Exempt rule extraction: 30 minutes
- Complying rule extraction: 30 minutes
- Decision tree engine: 25 minutes
- Verification tests: 20 minutes

## COMPLETION CRITERIA
✅ 100+ pathway rules extracted from existing SEPP provisions
✅ Decision tree handles 95%+ of test scenarios correctly
✅ Clear exempt vs complying vs DA determination
✅ Response time <500ms
✅ API endpoint ready for integration