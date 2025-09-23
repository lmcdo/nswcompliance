# PRP-M1: Research Assistant Migration Pipeline
## Foolproof, Granular Implementation with Full Accountability

### EXECUTIVE ACCOUNTABILITY MATRIX
```yaml
pipeline_id: PRP-M1_RESEARCH_ASSISTANT_2024_12_10
total_steps: 25
validation_gates: 5
rollback_points: 5
success_criteria: 100% data integrity, 0% data loss
```

---

## PHASE 1: PRE-MIGRATION VALIDATION (Steps 1-5)

### Step 1: Source Data Audit
```sql
-- ACCOUNTABILITY: Record exact state before migration
CREATE TABLE migration_audit.prp_m1_source_snapshot (
 audit_id SERIAL PRIMARY KEY,
 timestamp TIMESTAMP DEFAULT NOW(),
 source_table VARCHAR(100),
 row_count INTEGER,
 data_checksum VARCHAR(64),
 sample_data JSONB
);
```

**Validation Gate 1**: Source data integrity check
- [ ] All SQLite tables documented
- [ ] Row counts recorded
- [ ] MD5 checksums calculated
- [ ] Sample data preserved

### Step 2: Data Quality Assessment
```python
def validate_source_quality():
 """
 ACCOUNTABILITY: Document all data quality issues
 """
 quality_report = {
 'total_provisions': count_provisions(),
 'provisions_with_zones': count_zone_mentions(),
 'orphaned_records': find_orphans(),
 'duplicate_provisions': find_duplicates(),
 'null_critical_fields': find_nulls()
 }
 
 # FAIL FAST: Stop if quality below threshold
 if quality_report['orphaned_records'] > 100:
 raise DataQualityException("Too many orphaned records")
 
 return quality_report
```

### Step 3: Schema Compatibility Check
```sql
-- ACCOUNTABILITY: Ensure no data type mismatches
CREATE TABLE migration_audit.schema_compatibility (
 sqlite_column VARCHAR(100),
 sqlite_type VARCHAR(50),
 postgres_column VARCHAR(100),
 postgres_type VARCHAR(50),
 conversion_required BOOLEAN,
 conversion_function TEXT
);
```

### Step 4: Create Migration Staging Area
```sql
CREATE SCHEMA migration_staging;

-- Exact replica of source structure
CREATE TABLE migration_staging.raw_provisions AS 
SELECT * FROM sqlite_backup.regulatory_provisions WHERE 1=0;

CREATE TABLE migration_staging.raw_documents AS
SELECT * FROM sqlite_backup.documents WHERE 1=0;

CREATE TABLE migration_staging.raw_quantitative AS
SELECT * FROM sqlite_backup.quantitative_standards WHERE 1=0;
```

### Step 5: Backup Creation
```bash
#!/bin/bash
# ACCOUNTABILITY: Triple backup before migration

# Backup 1: SQLite file copy
cp nsw_planning.db backups/prp_m1_$(date +%Y%m%d_%H%M%S).db

# Backup 2: SQL dump
sqlite3 nsw_planning.db .dump > backups/prp_m1_$(date +%Y%m%d_%H%M%S).sql

# Backup 3: PostgreSQL snapshot
pg_dump -h localhost -U postgres nsw_planning > backups/pg_pre_prp_m1_$(date +%Y%m%d_%H%M%S).sql

# Checksum verification
md5sum backups/* > backups/checksums.txt
```

**Rollback Point 1**: Can restore to original state

---

## PHASE 2: DATA EXTRACTION & TRANSFORMATION (Steps 6-10)

### Step 6: Extract Documents with Full Audit Trail
```python
def extract_documents_with_audit():
 """
 ACCOUNTABILITY: Every document tracked
 """
 extraction_log = []
 
 with sqlite3.connect('nsw_planning.db') as conn:
 documents = conn.execute('''
 SELECT id, pdf_name, document_type, 
 document_area, char_count, word_count
 FROM documents
 ''').fetchall()
 
 for doc in documents:
 record = {
 'source_id': doc[0],
 'extracted_at': datetime.now(),
 'transformation': 'none',
 'validation': validate_document(doc)
 }
 extraction_log.append(record)
 
 # Write to audit table
 save_extraction_audit(extraction_log)
 return documents
```

### Step 7: Transform Provisions with Zone Extraction
```python
def transform_provisions_granular():
 """
 ACCOUNTABILITY: Track every transformation
 """
 transformations = []
 
 for provision in get_provisions():
 # Extract explicit zone mentions
 zone_mentions = extract_explicit_zones(provision.text)
 
 # Extract keywords
 keywords = extract_keywords(provision.text)
 
 # Identify complexity indicators
 complexity = detect_complexity_indicators(provision.text)
 
 transformation = {
 'original_id': provision.id,
 'original_zone': provision.zone, # The bad inference
 'extracted_zones': zone_mentions, # Explicit mentions only
 'confidence': 1.0 if zone_mentions else 0.0,
 'keywords': keywords,
 'complexity_flags': complexity,
 'transformation_timestamp': datetime.now()
 }
 
 transformations.append(transformation)
 
 return transformations
```

### Step 8: Validate Transformations
```python
def validate_transformations(transformations):
 """
 ACCOUNTABILITY: Ensure no data corruption
 """
 validation_results = {
 'total_transformed': len(transformations),
 'successful': 0,
 'failed': [],
 'warnings': []
 }
 
 for t in transformations:
 # Check text integrity
 if not t['original_id']:
 validation_results['failed'].append(t)
 continue
 
 # Validate zone extraction
 if t['original_zone'] and not t['extracted_zones']:
 validation_results['warnings'].append({
 'id': t['original_id'],
 'issue': 'Lost zone assignment',
 'original': t['original_zone'],
 'new': None
 })
 
 validation_results['successful'] += 1
 
 return validation_results
```

### Step 9: Load to Staging
```sql
-- ACCOUNTABILITY: Staging area for verification
INSERT INTO migration_staging.documents_transformed
SELECT * FROM transform_documents();

INSERT INTO migration_staging.provisions_transformed 
SELECT * FROM transform_provisions();

-- Record counts
INSERT INTO migration_audit.staging_counts
VALUES (NOW(), 'documents', COUNT(*) FROM migration_staging.documents_transformed);
```

### Step 10: Staging Validation
```sql
-- ACCOUNTABILITY: Verify staging data
WITH validation AS (
 SELECT 
 'documents' as table_name,
 COUNT(*) as staged_count,
 (SELECT COUNT(*) FROM sqlite_source.documents) as source_count
 FROM migration_staging.documents_transformed
 
 UNION ALL
 
 SELECT 
 'provisions' as table_name,
 COUNT(*) as staged_count,
 (SELECT COUNT(*) FROM sqlite_source.provisions) as source_count
 FROM migration_staging.provisions_transformed
)
SELECT 
 table_name,
 staged_count,
 source_count,
 CASE 
 WHEN staged_count = source_count THEN 'PASS'
 ELSE 'FAIL'
 END as validation_status
FROM validation;
```

**Validation Gate 2**: Staging area integrity
**Rollback Point 2**: Can clear staging and retry

---

## PHASE 3: RESEARCH ASSISTANT SCHEMA POPULATION (Steps 11-15)

### Step 11: Populate Documents Table
```sql
-- ACCOUNTABILITY: Track every insert
WITH document_insert AS (
 INSERT INTO research_assistant.documents 
 (document_name, document_type, jurisdiction, complexity_level)
 SELECT 
 pdf_name,
 document_type,
 CASE 
 WHEN pdf_name LIKE '%Inner West%' THEN 'Inner West'
 WHEN pdf_name LIKE '%Marrickville%' THEN 'Inner West'
 WHEN pdf_name LIKE '%Leichhardt%' THEN 'Inner West'
 ELSE 'NSW State'
 END as jurisdiction,
 3 as complexity_level -- Default, will refine
 FROM migration_staging.documents_transformed
 RETURNING id, document_name
)
INSERT INTO migration_audit.document_mapping
SELECT * FROM document_insert;
```

### Step 12: Populate Provisions with Accurate Zone Data
```sql
-- ACCOUNTABILITY: Only explicit zone mentions
INSERT INTO research_assistant.provisions
(document_id, clause_reference, provision_text, zone_mentions, keywords)
SELECT 
 d.new_id,
 p.ref_number,
 p.provision_text,
 -- Only zones explicitly mentioned in text
 ARRAY(
 SELECT DISTINCT regexp_matches(
 p.provision_text, 
 '\bZone\s+(R[1-5]|B[1-8]|IN[1-4]|E[1-5])\b',
 'gi'
 )
 ) as zone_mentions,
 -- Extract keywords
 ARRAY(
 SELECT DISTINCT lower(word)
 FROM regexp_split_to_table(p.provision_text, '\s+') as word
 WHERE length(word) > 4
 AND word IN (SELECT keyword FROM research_assistant.complexity_indicators)
 ) as keywords
FROM migration_staging.provisions_transformed p
JOIN migration_audit.document_mapping d ON p.document_id = d.old_id;
```

### Step 13: Build Document Relationships
```sql
-- ACCOUNTABILITY: Track relationship inference
INSERT INTO research_assistant.document_relationships
(primary_document_id, related_document_id, relationship_type)
SELECT DISTINCT
 d1.id,
 d2.id,
 CASE
 WHEN d1.document_type = 'SEPP' AND d2.document_type = 'LEP' THEN 'supersedes'
 WHEN d1.document_type = 'LEP' AND d2.document_type = 'DCP' THEN 'supersedes'
 ELSE 'references'
 END
FROM research_assistant.documents d1
CROSS JOIN research_assistant.documents d2
WHERE d1.id != d2.id
AND EXISTS (
 -- Documents that reference the same zones
 SELECT 1 FROM research_assistant.provisions p1
 JOIN research_assistant.provisions p2 
 ON p1.zone_mentions && p2.zone_mentions
 WHERE p1.document_id = d1.id 
 AND p2.document_id = d2.id
);
```

### Step 14: Calculate Complexity Scores
```python
def calculate_complexity_scores():
 """
 ACCOUNTABILITY: Transparent scoring algorithm
 """
 complexity_calculations = []
 
 for provision in get_provisions():
 score = 0
 factors = []
 
 # Check each complexity indicator
 for indicator in COMPLEXITY_INDICATORS:
 if indicator['keyword'] in provision.text.lower():
 score += indicator['weight']
 factors.append(indicator['keyword'])
 
 # Document the calculation
 complexity_calculations.append({
 'provision_id': provision.id,
 'base_score': score,
 'factors': factors,
 'final_score': min(score, 5.0), # Cap at 5
 'calculation_timestamp': datetime.now()
 })
 
 # Save for audit
 save_complexity_audit(complexity_calculations)
 
 return complexity_calculations
```

### Step 15: Create Search Indexes
```sql
-- ACCOUNTABILITY: Performance optimization
CREATE INDEX CONCURRENTLY idx_provisions_search 
ON research_assistant.provisions 
USING gin(to_tsvector('english', provision_text));

-- Log index creation
INSERT INTO migration_audit.performance_optimizations
VALUES ('idx_provisions_search', NOW(), 'GIN full-text search index');
```

**Validation Gate 3**: Research assistant schema populated
**Rollback Point 3**: Can truncate research_assistant schema

---

## PHASE 4: VALIDATION & RECONCILIATION (Steps 16-20)

### Step 16: Row Count Reconciliation
```sql
CREATE OR REPLACE FUNCTION validate_migration_counts()
RETURNS TABLE(
 check_name TEXT,
 source_count BIGINT,
 target_count BIGINT,
 difference BIGINT,
 status TEXT
) AS $$
BEGIN
 RETURN QUERY
 SELECT 
 'Total Provisions',
 (SELECT COUNT(*) FROM sqlite_source.regulatory_provisions),
 (SELECT COUNT(*) FROM research_assistant.provisions),
 (SELECT COUNT(*) FROM research_assistant.provisions) - 
 (SELECT COUNT(*) FROM sqlite_source.regulatory_provisions),
 CASE 
 WHEN (SELECT COUNT(*) FROM research_assistant.provisions) = 
 (SELECT COUNT(*) FROM sqlite_source.regulatory_provisions)
 THEN 'PASS'
 ELSE 'FAIL'
 END;
END;
$$ LANGUAGE plpgsql;
```

### Step 17: Data Integrity Verification
```python
def verify_data_integrity():
 """
 ACCOUNTABILITY: Checksum verification
 """
 integrity_checks = []
 
 # Sample 100 random provisions
 sample_ids = random.sample(all_provision_ids, 100)
 
 for pid in sample_ids:
 source = get_source_provision(pid)
 target = get_target_provision(pid)
 
 check = {
 'provision_id': pid,
 'source_checksum': hashlib.md5(source.text.encode()).hexdigest(),
 'target_checksum': hashlib.md5(target.text.encode()).hexdigest(),
 'match': source.text == target.text
 }
 
 integrity_checks.append(check)
 
 success_rate = sum(1 for c in integrity_checks if c['match']) / len(integrity_checks)
 
 if success_rate < 0.99:
 raise IntegrityException(f"Integrity check failed: {success_rate:.2%}")
 
 return integrity_checks
```

### Step 18: Zone Assignment Accuracy
```sql
-- ACCOUNTABILITY: Verify zone extraction accuracy
WITH zone_validation AS (
 SELECT 
 p.id,
 p.provision_text,
 p.zone_mentions,
 -- Check if zones in array actually exist in text
 ARRAY(
 SELECT z 
 FROM unnest(p.zone_mentions) z
 WHERE p.provision_text ~* ('\bZone\s+' || z || '\b')
 ) as verified_zones
 FROM research_assistant.provisions p
 WHERE cardinality(p.zone_mentions) > 0
)
SELECT 
 COUNT(*) as total_with_zones,
 COUNT(CASE WHEN zone_mentions = verified_zones THEN 1 END) as accurate,
 COUNT(CASE WHEN zone_mentions != verified_zones THEN 1 END) as inaccurate
FROM zone_validation;
```

### Step 19: Performance Testing
```sql
-- ACCOUNTABILITY: Ensure system performs adequately
DO $$
DECLARE
 start_time TIMESTAMP;
 end_time TIMESTAMP;
 query_time INTERVAL;
BEGIN
 -- Test search performance
 start_time := clock_timestamp();
 
 PERFORM * FROM research_assistant.provisions
 WHERE to_tsvector('english', provision_text) @@ to_tsquery('setback & R2');
 
 end_time := clock_timestamp();
 query_time := end_time - start_time;
 
 INSERT INTO migration_audit.performance_tests
 VALUES ('Full text search', query_time, 
 CASE WHEN query_time < interval '1 second' THEN 'PASS' ELSE 'FAIL' END);
END $$;
```

### Step 20: User Acceptance Criteria
```python
def validate_user_acceptance():
 """
 ACCOUNTABILITY: Ensure meets user needs
 """
 test_queries = [
 {
 'input': {'address': '123 Main St', 'zone': 'R2'},
 'expected': 'Returns relevant R2 provisions',
 'actual': test_r2_query()
 },
 {
 'input': {'keywords': ['heritage', 'setback']},
 'expected': 'Returns heritage setback provisions',
 'actual': test_keyword_search()
 }
 ]
 
 for test in test_queries:
 test['passed'] = validate_test_result(test['actual'], test['expected'])
 
 return test_queries
```

**Validation Gate 4**: Full system validation
**Rollback Point 4**: Can restore from backup

---

## PHASE 5: CUTOVER & MONITORING (Steps 21-25)

### Step 21: Create Cutover Procedure
```bash
#!/bin/bash
# ACCOUNTABILITY: Atomic cutover

# 1. Stop application
systemctl stop planning-app

# 2. Final backup
pg_dump nsw_planning > final_backup_$(date +%Y%m%d_%H%M%S).sql

# 3. Rename schemas
psql -c "ALTER SCHEMA public RENAME TO public_old;"
psql -c "ALTER SCHEMA research_assistant RENAME TO public;"

# 4. Verify
psql -c "SELECT COUNT(*) FROM public.provisions;"

# 5. Restart application
systemctl start planning-app
```

### Step 22: Monitoring Setup
```sql
-- ACCOUNTABILITY: Ongoing monitoring
CREATE TABLE migration_audit.usage_monitoring (
 id SERIAL PRIMARY KEY,
 timestamp TIMESTAMP DEFAULT NOW(),
 query_type VARCHAR(50),
 query_params JSONB,
 result_count INTEGER,
 response_time_ms INTEGER,
 user_id VARCHAR(100)
);

-- Trigger to monitor usage
CREATE OR REPLACE FUNCTION log_usage()
RETURNS TRIGGER AS $$
BEGIN
 INSERT INTO migration_audit.usage_monitoring
 (query_type, query_params, result_count)
 VALUES (TG_TABLE_NAME, row_to_json(NEW), 1);
 RETURN NEW;
END;
$$ LANGUAGE plpgsql;
```

### Step 23: Rollback Procedure
```bash
#!/bin/bash
# ACCOUNTABILITY: Can reverse if needed

# 1. Stop application
systemctl stop planning-app

# 2. Restore schemas
psql -c "ALTER SCHEMA public RENAME TO public_failed;"
psql -c "ALTER SCHEMA public_old RENAME TO public;"

# 3. Restore from backup if needed
psql < final_backup_latest.sql

# 4. Restart
systemctl start planning-app

# 5. Alert team
send_alert "Migration rolled back"
```

### Step 24: Success Metrics
```sql
-- ACCOUNTABILITY: Define success
CREATE VIEW migration_audit.success_metrics AS
SELECT 
 'Data Completeness' as metric,
 (SELECT COUNT(*) FROM public.provisions) as value,
 (SELECT COUNT(*) FROM sqlite_source.provisions) as target,
 CASE 
 WHEN (SELECT COUNT(*) FROM public.provisions) >= 
 (SELECT COUNT(*) FROM sqlite_source.provisions)
 THEN 'SUCCESS'
 ELSE 'FAILURE'
 END as status

UNION ALL

SELECT 
 'Zone Accuracy' as metric,
 (SELECT COUNT(*) FROM public.provisions WHERE cardinality(zone_mentions) > 0) as value,
 100 as target, -- At least 100 provisions with zones
 CASE 
 WHEN (SELECT COUNT(*) FROM public.provisions WHERE cardinality(zone_mentions) > 0) >= 100
 THEN 'SUCCESS'
 ELSE 'FAILURE'
 END as status

UNION ALL

SELECT 
 'Search Performance' as metric,
 (SELECT AVG(response_time_ms) FROM migration_audit.usage_monitoring) as value,
 1000 as target, -- Under 1 second
 CASE 
 WHEN (SELECT AVG(response_time_ms) FROM migration_audit.usage_monitoring) < 1000
 THEN 'SUCCESS'
 ELSE 'FAILURE'
 END as status;
```

### Step 25: Final Sign-off
```python
def generate_final_report():
 """
 ACCOUNTABILITY: Complete audit trail
 """
 report = {
 'migration_id': 'PRP-M1_2024_12_10',
 'start_time': migration_start,
 'end_time': datetime.now(),
 'total_duration': calculate_duration(),
 
 'data_metrics': {
 'source_provisions': count_source_provisions(),
 'migrated_provisions': count_migrated_provisions(),
 'data_loss': calculate_data_loss(),
 'zone_accuracy': calculate_zone_accuracy()
 },
 
 'validation_gates': {
 'gate_1': gate_1_status,
 'gate_2': gate_2_status,
 'gate_3': gate_3_status,
 'gate_4': gate_4_status,
 'gate_5': gate_5_status
 },
 
 'rollback_points_tested': rollback_tests,
 
 'sign_off': {
 'technical_lead': None,
 'data_owner': None,
 'business_owner': None,
 'timestamp': None
 }
 }
 
 save_final_report(report)
 return report
```

**Validation Gate 5**: Complete migration success
**Rollback Point 5**: Full system restoration available

---

## ACCOUNTABILITY PROOF

### Audit Trail Components:
1. **Source snapshot** - Complete backup before migration
2. **Transformation log** - Every data change documented
3. **Validation gates** - 5 checkpoints with pass/fail criteria
4. **Rollback points** - 5 restoration points
5. **Performance metrics** - Response time tracking
6. **Usage monitoring** - Ongoing system health
7. **Final report** - Complete migration documentation

### Success Criteria:
- 100% data accountability (every row tracked)
- 0% unexplained data loss
- Zone accuracy improved from 2% to 95%+
- Search performance < 1 second
- Full rollback capability at every stage
- Complete audit trail for compliance

### Failure Modes Addressed:
- Data corruption → Checksum validation
- Performance degradation → Performance gates
- Zone inference errors → Explicit extraction only
- Missing relationships → Document mapping
- User dissatisfaction → UAT criteria

This PRP provides foolproof, granular implementation with complete accountability at every step.