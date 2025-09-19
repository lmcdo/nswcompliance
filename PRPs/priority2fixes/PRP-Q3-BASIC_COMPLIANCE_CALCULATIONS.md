# PRP-Q3: Basic Compliance Calculations Engine

## OBJECTIVE
Implement simple numeric compliance calculations (parking, FSR, site coverage, height) using existing provisions without requiring spatial/GIS data.

## SUCCESS CRITERIA
- [ ] Extract parking requirements from existing provisions
- [ ] Implement FSR (Floor Space Ratio) calculator
- [ ] Implement site coverage percentage calculator
- [ ] Implement numeric height limit checker
- [ ] Response time <100ms per calculation
- [ ] 95%+ accuracy on standard calculations

## TECHNICAL SPECIFICATION

### Phase Q3A: Parking Requirements Extraction
```sql
-- Extract parking requirements from provisions
SELECT
    document_id,
    provision_text,
    zone,
    development_type
FROM regulatory_provisions
WHERE (
    LOWER(provision_text) LIKE '%parking%space%' OR
    LOWER(provision_text) LIKE '%car space%' OR
    LOWER(provision_text) LIKE '%vehicle%space%'
)
AND provision_text REGEXP '[0-9]';  -- Contains numeric values
```

### Phase Q3B: FSR and Height Limits
```sql
-- Extract FSR and height limits
SELECT
    zone,
    provision_text
FROM regulatory_provisions
WHERE (
    LOWER(provision_text) LIKE '%floor space ratio%' OR
    LOWER(provision_text) LIKE '%fsr%' OR
    LOWER(provision_text) LIKE '%maximum height%' OR
    LOWER(provision_text) LIKE '%height limit%'
)
AND provision_text REGEXP '[0-9]+\.?[0-9]*';  -- Contains numeric values
```

### Phase Q3C: Calculation Engine
```python
class ComplianceCalculator:
    def calculate_parking_requirements(self, development_type: str,
                                      units: int = None,
                                      floor_area: float = None) -> Dict:
        """Calculate required parking spaces"""

        # Residential parking rates
        if development_type == 'dwelling_house':
            return {'required_spaces': 2, 'formula': '2 spaces per dwelling'}

        elif development_type == 'residential_flat_building':
            if units:
                # 1 space per unit + 0.25 visitor spaces
                resident_spaces = units
                visitor_spaces = math.ceil(units * 0.25)
                return {
                    'resident_spaces': resident_spaces,
                    'visitor_spaces': visitor_spaces,
                    'total_spaces': resident_spaces + visitor_spaces,
                    'formula': '1/unit + 0.25 visitor/unit'
                }

        # Commercial parking rates
        elif development_type == 'retail_premises':
            if floor_area:
                # 1 space per 25sqm retail
                spaces = math.ceil(floor_area / 25)
                return {
                    'required_spaces': spaces,
                    'formula': '1 space per 25sqm'
                }

        return {'error': 'Unable to calculate parking requirements'}

    def calculate_fsr(self, gross_floor_area: float, site_area: float) -> Dict:
        """Calculate Floor Space Ratio"""
        if site_area <= 0:
            return {'error': 'Invalid site area'}

        fsr = gross_floor_area / site_area

        return {
            'fsr': round(fsr, 2),
            'gross_floor_area': gross_floor_area,
            'site_area': site_area,
            'formula': 'GFA / Site Area'
        }

    def check_fsr_compliance(self, zone: str, fsr: float) -> Dict:
        """Check if FSR complies with zone limits"""

        # Get zone FSR limit
        fsr_limit = self.get_zone_fsr_limit(zone)

        if fsr_limit:
            compliant = fsr <= fsr_limit
            return {
                'compliant': compliant,
                'fsr': fsr,
                'fsr_limit': fsr_limit,
                'zone': zone,
                'margin': round(fsr_limit - fsr, 2)
            }

        return {'error': f'No FSR limit found for zone {zone}'}
```

## IMPLEMENTATION STEPS

### Step 1: Create Calculations Schema (10 minutes)
```sql
CREATE TABLE compliance_standards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    zone TEXT NOT NULL,
    development_type TEXT,
    standard_type TEXT NOT NULL,  -- parking, fsr, height, coverage
    standard_value REAL,
    standard_unit TEXT,
    formula TEXT,
    conditions TEXT,  -- JSON
    source_provision_id INTEGER,
    confidence_score REAL DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(zone, development_type, standard_type)
);

CREATE TABLE parking_rates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    development_type TEXT NOT NULL,
    zone TEXT,
    rate_value REAL NOT NULL,
    rate_unit TEXT,  -- per_dwelling, per_sqm, per_bedroom
    visitor_rate REAL,
    accessible_rate REAL,
    source_document TEXT,
    UNIQUE(development_type, zone)
);

CREATE INDEX idx_standards_zone ON compliance_standards(zone);
CREATE INDEX idx_parking_dev ON parking_rates(development_type);
```

### Step 2: Extract Parking Requirements (30 minutes)
```python
def extract_parking_requirements():
    """Extract parking requirements from provisions"""

    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()

    # Query provisions with parking requirements
    cursor.execute("""
    SELECT id, provision_text, zone, development_type
    FROM regulatory_provisions
    WHERE LOWER(provision_text) LIKE '%parking%'
    AND provision_text IS NOT NULL
    """)

    provisions = cursor.fetchall()
    parking_rates = []

    for prov_id, text, zone, dev_type in provisions:
        # Pattern: "1 space per dwelling"
        match = re.search(r'(\d+\.?\d*)\s*space[s]?\s*per\s*(\w+)', text.lower())
        if match:
            rate_value = float(match.group(1))
            rate_unit = match.group(2)

            parking_rates.append({
                'development_type': dev_type or 'general',
                'zone': zone,
                'rate_value': rate_value,
                'rate_unit': f'per_{rate_unit}',
                'source_provision_id': prov_id
            })

        # Pattern: "minimum 2 car parking spaces"
        match = re.search(r'minimum\s*(\d+)\s*(?:car\s*)?parking\s*space', text.lower())
        if match:
            min_spaces = int(match.group(1))
            parking_rates.append({
                'development_type': dev_type or 'dwelling_house',
                'zone': zone,
                'rate_value': min_spaces,
                'rate_unit': 'per_dwelling',
                'source_provision_id': prov_id
            })

    # Insert extracted rates
    for rate in parking_rates:
        cursor.execute("""
        INSERT OR IGNORE INTO parking_rates
        (development_type, zone, rate_value, rate_unit)
        VALUES (?, ?, ?, ?)
        """, (rate['development_type'], rate['zone'],
              rate['rate_value'], rate['rate_unit']))

    conn.commit()
    conn.close()

    return len(parking_rates)
```

### Step 3: Extract FSR and Height Limits (30 minutes)
```python
def extract_fsr_height_limits():
    """Extract FSR and height limits from provisions"""

    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()

    standards = []

    # Extract FSR limits
    cursor.execute("""
    SELECT id, provision_text, zone
    FROM regulatory_provisions
    WHERE LOWER(provision_text) LIKE '%floor space ratio%'
    OR LOWER(provision_text) LIKE '%fsr%'
    """)

    fsr_provisions = cursor.fetchall()

    for prov_id, text, zone in fsr_provisions:
        # Pattern: "maximum floor space ratio of 0.5:1"
        match = re.search(r'(?:maximum\s*)?(?:floor\s*space\s*ratio|fsr)\s*(?:of\s*)?(\d+\.?\d*)(?::1)?', text.lower())
        if match:
            fsr_value = float(match.group(1))
            standards.append({
                'zone': zone,
                'standard_type': 'fsr',
                'standard_value': fsr_value,
                'standard_unit': 'ratio',
                'source_provision_id': prov_id
            })

    # Extract height limits
    cursor.execute("""
    SELECT id, provision_text, zone
    FROM regulatory_provisions
    WHERE LOWER(provision_text) LIKE '%maximum height%'
    OR LOWER(provision_text) LIKE '%height limit%'
    """)

    height_provisions = cursor.fetchall()

    for prov_id, text, zone in height_provisions:
        # Pattern: "maximum height of 8.5 metres"
        match = re.search(r'maximum\s*height\s*(?:of\s*)?(\d+\.?\d*)\s*(?:metres|m)', text.lower())
        if match:
            height_value = float(match.group(1))
            standards.append({
                'zone': zone,
                'standard_type': 'height',
                'standard_value': height_value,
                'standard_unit': 'metres',
                'source_provision_id': prov_id
            })

    # Insert standards
    for std in standards:
        cursor.execute("""
        INSERT OR IGNORE INTO compliance_standards
        (zone, standard_type, standard_value, standard_unit, source_provision_id)
        VALUES (?, ?, ?, ?, ?)
        """, (std['zone'], std['standard_type'], std['standard_value'],
              std['standard_unit'], std.get('source_provision_id')))

    conn.commit()
    conn.close()

    return len(standards)
```

### Step 4: Build Calculation Engine (25 minutes)
```python
def build_calculation_engine():
    """Build comprehensive calculation engine"""

    class ComplianceCalculationEngine:

        def __init__(self):
            self.load_standards()

        def load_standards(self):
            """Load compliance standards from database"""
            conn = sqlite3.connect('nsw_planning.db')
            cursor = conn.cursor()

            # Load FSR limits
            cursor.execute("""
            SELECT zone, standard_value
            FROM compliance_standards
            WHERE standard_type = 'fsr'
            """)
            self.fsr_limits = dict(cursor.fetchall())

            # Load height limits
            cursor.execute("""
            SELECT zone, standard_value
            FROM compliance_standards
            WHERE standard_type = 'height'
            """)
            self.height_limits = dict(cursor.fetchall())

            # Load parking rates
            cursor.execute("""
            SELECT development_type, zone, rate_value, rate_unit
            FROM parking_rates
            """)
            self.parking_rates = cursor.fetchall()

            conn.close()

        def calculate_all_compliance(self, inputs: Dict) -> Dict:
            """Calculate all compliance metrics"""

            results = {}

            # Parking calculation
            if 'development_type' in inputs:
                results['parking'] = self.calculate_parking(
                    inputs['development_type'],
                    inputs.get('units'),
                    inputs.get('floor_area')
                )

            # FSR calculation
            if 'gross_floor_area' in inputs and 'site_area' in inputs:
                results['fsr'] = self.calculate_fsr(
                    inputs['gross_floor_area'],
                    inputs['site_area']
                )

                if 'zone' in inputs:
                    results['fsr_compliance'] = self.check_fsr_compliance(
                        inputs['zone'],
                        results['fsr']['fsr']
                    )

            # Height compliance
            if 'height' in inputs and 'zone' in inputs:
                results['height_compliance'] = self.check_height_compliance(
                    inputs['zone'],
                    inputs['height']
                )

            # Site coverage
            if 'building_area' in inputs and 'site_area' in inputs:
                results['site_coverage'] = self.calculate_site_coverage(
                    inputs['building_area'],
                    inputs['site_area']
                )

            return results

    return ComplianceCalculationEngine()
```

### Step 5: Create Verification Tests (15 minutes)
```python
def verify_calculations():
    """Verify calculation accuracy"""

    engine = build_calculation_engine()

    test_cases = [
        {
            'description': 'Dwelling house parking',
            'inputs': {'development_type': 'dwelling_house'},
            'expected': {'parking': {'required_spaces': 2}}
        },
        {
            'description': 'FSR calculation',
            'inputs': {
                'gross_floor_area': 200,
                'site_area': 500,
                'zone': 'R2'
            },
            'expected': {'fsr': {'fsr': 0.4}}
        },
        {
            'description': 'Height compliance R2',
            'inputs': {
                'zone': 'R2',
                'height': 8.5
            },
            'expected': {'height_compliance': {'compliant': True}}
        }
    ]

    results = []
    for test in test_cases:
        actual = engine.calculate_all_compliance(test['inputs'])

        # Compare results
        passed = verify_calculation_result(actual, test['expected'])

        results.append({
            'test': test['description'],
            'passed': passed,
            'actual': actual,
            'expected': test['expected']
        })

    return results
```

## VERIFICATION CHECKLIST

### Automated Verification
- [ ] Parking requirements extracted for >10 development types
- [ ] FSR limits extracted for major zones
- [ ] Height limits extracted for major zones
- [ ] All calculations return in <100ms
- [ ] Test scenarios achieve 95%+ accuracy

### Quality Metrics
- [ ] Parking rates: >20 extracted
- [ ] FSR limits: >10 zones
- [ ] Height limits: >10 zones
- [ ] Calculation formulas: Documented
- [ ] Unit handling: Correct for all types

### Manual Verification
- [ ] Parking calculations match DCP standards
- [ ] FSR calculations mathematically correct
- [ ] Height compliance logic accurate
- [ ] Site coverage calculations valid

## DELIVERABLES

1. **compliance_standards table** - Extracted numeric standards
2. **parking_rates table** - Comprehensive parking requirements
3. **calculation_engine.py** - Complete calculation implementation
4. **calculation_tests.json** - Test results and validation
5. **calculation_api.py** - API endpoint for calculations

## ESTIMATED TIME
**2 hours total**
- Schema creation: 10 minutes
- Parking extraction: 30 minutes
- FSR/Height extraction: 30 minutes
- Calculation engine: 25 minutes
- Verification tests: 15 minutes

## COMPLETION CRITERIA
✅ 20+ parking requirements extracted
✅ FSR limits for major zones extracted
✅ Height limits for major zones extracted
✅ All calculations <100ms response time
✅ 95%+ accuracy on test scenarios