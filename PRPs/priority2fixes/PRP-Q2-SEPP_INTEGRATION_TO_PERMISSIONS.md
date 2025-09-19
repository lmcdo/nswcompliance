# PRP-Q2: SEPP Integration to Development Permissions

## OBJECTIVE
Connect existing SEPP provisions (3,173 total) to development_permissions table, extracting development types and permission rules from SEPP (Housing) 2021 and other key SEPPs to enhance zone-based development queries.

## SUCCESS CRITERIA
- [ ] Extract 200+ new development permissions from SEPP provisions
- [ ] Link SEPP 65 triggers for apartment development
- [ ] Add SEPP (Housing) 2021 affordable housing provisions
- [ ] Achieve 90%+ accuracy on SEPP-derived permissions
- [ ] Integrate with existing development_permissions table
- [ ] Create sepp_permissions mapping table

## TECHNICAL SPECIFICATION

### Phase Q2A: SEPP Development Type Extraction
```sql
-- Extract development types from SEPP (Housing) 2021
SELECT
    document_id,
    provision_text,
    zone,
    development_type
FROM regulatory_provisions
WHERE LOWER(document_id) LIKE '%housing%'
AND provision_text IS NOT NULL
AND (
    LOWER(provision_text) LIKE '%permitted%' OR
    LOWER(provision_text) LIKE '%prohibited%' OR
    LOWER(provision_text) LIKE '%consent%'
);
```

### Phase Q2B: SEPP 65 Apartment Triggers
```sql
-- Extract SEPP 65 design quality triggers
SELECT
    provision_text,
    zone
FROM regulatory_provisions
WHERE document_id LIKE '%65%'
AND (
    LOWER(provision_text) LIKE '%residential flat%' OR
    LOWER(provision_text) LIKE '%apartment%' OR
    LOWER(provision_text) LIKE '%design quality%'
);
```

### Phase Q2C: Permission Mapping Logic
```python
class SEPPPermissionExtractor:
    def extract_sepp_permissions(self) -> List[Dict]:
        """Extract development permissions from SEPP provisions"""

        permissions = []

        # SEPP (Housing) 2021 specific extractions
        housing_provisions = self.get_housing_sepp_provisions()

        for provision in housing_provisions:
            # Pattern: "development for the purpose of [type] is permitted"
            if 'permitted with consent' in provision.text.lower():
                dev_type = self.extract_development_type(provision.text)
                permissions.append({
                    'source': 'SEPP_Housing_2021',
                    'zone': provision.zone or 'ALL',
                    'development_type': dev_type,
                    'permission_status': 'consent',
                    'confidence': 0.85
                })

            # Pattern: "the following development is prohibited"
            elif 'prohibited' in provision.text.lower():
                dev_types = self.extract_prohibited_types(provision.text)
                for dev_type in dev_types:
                    permissions.append({
                        'source': 'SEPP_Housing_2021',
                        'zone': provision.zone or 'ALL',
                        'development_type': dev_type,
                        'permission_status': 'prohibited',
                        'confidence': 0.9
                    })

        return permissions
```

## IMPLEMENTATION STEPS

### Step 1: Create SEPP Permissions Schema (10 minutes)
```sql
CREATE TABLE sepp_permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sepp_name TEXT NOT NULL,
    sepp_clause TEXT,
    zone TEXT,  -- NULL means applies to all zones
    development_type TEXT NOT NULL,
    permission_status TEXT CHECK(permission_status IN ('permitted', 'consent', 'prohibited')),
    additional_criteria TEXT,  -- JSON for conditions
    source_provision_id INTEGER REFERENCES regulatory_provisions(id),
    confidence_score REAL DEFAULT 0.8,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sepp_name, zone, development_type)
);

CREATE TABLE sepp_overrides (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sepp_name TEXT NOT NULL,
    overrides_lep BOOLEAN DEFAULT TRUE,
    priority_order INTEGER,  -- Higher number = higher priority
    development_category TEXT,
    active BOOLEAN DEFAULT TRUE
);

CREATE INDEX idx_sepp_zone_dev ON sepp_permissions(zone, development_type);
CREATE INDEX idx_sepp_name ON sepp_permissions(sepp_name);
```

### Step 2: Extract SEPP (Housing) 2021 Permissions (35 minutes)
```python
def extract_housing_sepp_permissions():
    """Extract permissions from SEPP (Housing) 2021 provisions"""

    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()

    # Get all Housing SEPP provisions
    cursor.execute("""
    SELECT id, document_id, provision_text, zone
    FROM regulatory_provisions
    WHERE LOWER(document_id) LIKE '%housing%'
    AND provision_text IS NOT NULL
    """)

    provisions = cursor.fetchall()
    extracted_permissions = []

    for prov_id, doc_id, text, zone in provisions:
        # Extract affordable housing provisions
        if 'affordable housing' in text.lower():
            if 'permitted' in text.lower():
                extracted_permissions.append({
                    'sepp_name': 'SEPP_Housing_2021',
                    'development_type': 'affordable_housing',
                    'permission_status': 'consent',
                    'zone': zone or 'R1,R2,R3,R4',
                    'source_provision_id': prov_id
                })

        # Extract boarding house provisions
        if 'boarding house' in text.lower():
            status = determine_permission_status(text)
            if status:
                extracted_permissions.append({
                    'sepp_name': 'SEPP_Housing_2021',
                    'development_type': 'boarding_house',
                    'permission_status': status,
                    'zone': zone or 'R2,R3,R4,B1,B2',
                    'source_provision_id': prov_id
                })

        # Extract secondary dwelling provisions
        if 'secondary dwelling' in text.lower():
            if 'permitted without consent' in text.lower():
                extracted_permissions.append({
                    'sepp_name': 'SEPP_Housing_2021',
                    'development_type': 'secondary_dwelling',
                    'permission_status': 'permitted',
                    'zone': zone or 'R1,R2,R3,R4,R5',
                    'source_provision_id': prov_id,
                    'additional_criteria': json.dumps({
                        'max_area': 60,
                        'condition': 'attached_to_principal'
                    })
                })

    # Insert into sepp_permissions table
    for perm in extracted_permissions:
        cursor.execute("""
        INSERT OR IGNORE INTO sepp_permissions
        (sepp_name, zone, development_type, permission_status,
         source_provision_id, confidence_score)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (perm['sepp_name'], perm.get('zone'), perm['development_type'],
              perm['permission_status'], perm.get('source_provision_id'), 0.85))

    conn.commit()
    conn.close()

    return len(extracted_permissions)
```

### Step 3: Extract SEPP 65 Design Quality Triggers (25 minutes)
```python
def extract_sepp65_triggers():
    """Extract SEPP 65 design quality triggers for apartments"""

    triggers = []

    # SEPP 65 applies to:
    # - Residential flat buildings (3+ storeys, 4+ dwellings)
    # - Mixed use with residential component
    # - Boarding houses with 3+ storeys

    triggers.append({
        'sepp_name': 'SEPP_65_Design_Quality',
        'development_type': 'residential_flat_building',
        'trigger_criteria': {
            'min_storeys': 3,
            'min_dwellings': 4,
            'requires_design_review': True
        }
    })

    triggers.append({
        'sepp_name': 'SEPP_65_Design_Quality',
        'development_type': 'shop_top_housing',
        'trigger_criteria': {
            'min_storeys': 3,
            'requires_design_review': True
        }
    })

    triggers.append({
        'sepp_name': 'SEPP_65_Design_Quality',
        'development_type': 'mixed_use_development',
        'trigger_criteria': {
            'min_storeys': 3,
            'residential_component': True,
            'requires_design_review': True
        }
    })

    return triggers
```

### Step 4: Integrate with Development Permissions (30 minutes)
```python
def integrate_sepp_with_permissions():
    """Integrate SEPP permissions with main development_permissions table"""

    conn = sqlite3.connect('nsw_planning.db')
    cursor = conn.cursor()

    # Get all SEPP permissions
    cursor.execute("""
    SELECT zone, development_type, permission_status, sepp_name, confidence_score
    FROM sepp_permissions
    WHERE active != FALSE
    """)

    sepp_perms = cursor.fetchall()

    integration_count = 0

    for zone, dev_type, permission, sepp_name, confidence in sepp_perms:
        # Handle multi-zone entries
        zones = zone.split(',') if zone else ['ALL']

        for z in zones:
            # Check if permission already exists
            cursor.execute("""
            SELECT id FROM development_permissions
            WHERE zone = ? AND development_type = ?
            """, (z.strip(), dev_type))

            existing = cursor.fetchone()

            if not existing:
                # Add new permission
                cursor.execute("""
                INSERT INTO development_permissions
                (zone, development_type, permission_status, lep_name,
                 extraction_method, confidence_score, source_type)
                VALUES (?, ?, ?, ?, 'sepp_extraction', ?, 'sepp')
                """, (z.strip(), dev_type, permission, sepp_name, confidence))

                integration_count += 1
            else:
                # Update if SEPP overrides
                cursor.execute("""
                UPDATE development_permissions
                SET permission_status = ?,
                    lep_name = ?,
                    source_type = 'sepp_override'
                WHERE zone = ? AND development_type = ?
                AND confidence_score < ?
                """, (permission, sepp_name, z.strip(), dev_type, confidence))

                if cursor.rowcount > 0:
                    integration_count += 1

    conn.commit()
    conn.close()

    return integration_count
```

### Step 5: Create Verification Tests (20 minutes)
```python
def verify_sepp_integration():
    """Verify SEPP integration accuracy"""

    test_cases = [
        {
            'description': 'Affordable housing in R2',
            'zone': 'R2',
            'development_type': 'affordable_housing',
            'expected_permission': 'consent',
            'expected_source': 'SEPP_Housing_2021'
        },
        {
            'description': 'Secondary dwelling in R1',
            'zone': 'R1',
            'development_type': 'secondary_dwelling',
            'expected_permission': 'permitted',
            'expected_source': 'SEPP_Housing_2021'
        },
        {
            'description': 'Apartment requiring SEPP 65',
            'zone': 'R4',
            'development_type': 'residential_flat_building',
            'min_storeys': 3,
            'expected_trigger': 'SEPP_65_Design_Quality'
        }
    ]

    results = []
    for test in test_cases:
        # Query integrated permissions
        actual = query_permission(test['zone'], test['development_type'])

        results.append({
            'test': test['description'],
            'passed': actual['permission_status'] == test.get('expected_permission'),
            'actual': actual,
            'expected': test
        })

    return results
```

## VERIFICATION CHECKLIST

### Automated Verification
- [ ] 958 SEPP (Housing) 2021 provisions processed
- [ ] 200+ new development permissions extracted
- [ ] SEPP 65 triggers identified for 3+ development types
- [ ] Integration with development_permissions successful
- [ ] No duplicate permissions created

### Quality Metrics
- [ ] SEPP Housing permissions: >50 extracted
- [ ] SEPP 65 triggers: >3 development types
- [ ] Override rules: Correctly prioritized
- [ ] Zone coverage: Expanded with SEPP rules
- [ ] Confidence scores: Appropriate for SEPP vs LEP

### Manual Verification
- [ ] Affordable housing provisions correct
- [ ] Secondary dwelling rules accurate
- [ ] SEPP 65 triggers match legislation
- [ ] Override logic working correctly

## DELIVERABLES

1. **sepp_permissions table** - Complete SEPP permissions database
2. **sepp_extractor.py** - SEPP provision extraction engine
3. **sepp_integration_report.json** - Integration statistics
4. **verification_results.csv** - Test results
5. **sepp_api_enhancement.py** - Enhanced API with SEPP logic

## ESTIMATED TIME
**2 hours total**
- Schema creation: 10 minutes
- SEPP Housing extraction: 35 minutes
- SEPP 65 extraction: 25 minutes
- Permission integration: 30 minutes
- Verification tests: 20 minutes

## COMPLETION CRITERIA
✅ 200+ SEPP-derived permissions added
✅ SEPP 65 triggers implemented
✅ SEPP Housing 2021 provisions integrated
✅ Override logic functioning correctly
✅ 90%+ accuracy on test scenarios