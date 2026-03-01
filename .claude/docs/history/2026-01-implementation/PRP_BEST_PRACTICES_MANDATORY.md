# PRP BEST PRACTICES - MANDATORY ENFORCEMENT
**Created**: 2025-09-08 13:02 UTC 
**Priority**: ARCHITECTURAL CRITICAL 
**Status**: MANDATORY COMPLIANCE REQUIRED

## THE CATASTROPHIC FAILURE ANALYSIS

### **What Went Wrong:**
1. **Schema designed without migration compatibility**
2. **Verification scripts tested wrong database**
3. **4x migration failures with 100% error rate**
4. **No end-to-end integration testing**
5. **Frontend connected to empty database for weeks**

### **Root Cause**: **SCHEMA INCOMPATIBILITY**
- **SQLite**: `zone` (string), `development_type` (string) 
- **PostgreSQL**: `applicable_zones` (array), `applicable_dev_types` (array)
- **Migration**: Tries to insert string into array → 100% FAILURE

## MANDATORY PRP BEST PRACTICES

### **1. DATABASE SCHEMA COMPATIBILITY (CRITICAL)**

#### **RULE 1A: Schema Compatibility Verification**
```sql
-- MANDATORY: Every migration must include compatibility test
-- Test script: test_schema_compatibility.py

-- Source Schema (SQLite)
CREATE TABLE regulatory_provisions (
 zone TEXT, -- Single value
 development_type TEXT -- Single value 
);

-- Target Schema (PostgreSQL) 
CREATE TABLE authoritative.planning_provisions (
 applicable_zones TEXT[], -- Array value INCOMPATIBLE
 applicable_dev_types TEXT[] -- Array value INCOMPATIBLE
);

-- COMPATIBILITY: FAILED 
-- MIGRATION RESULT: 100% failure rate
```

#### **RULE 1B: Migration-First Schema Design**
- **Design target schema to accept source data directly** 
- **OR design transformation layer that actually works**
- **Test migration with 100 sample records before full migration**
- **NEVER assume field types are compatible**

### **2. VERIFICATION TARGET ENFORCEMENT (CRITICAL)**

#### **RULE 2A: Production Database Verification Only**
```python
# WRONG - Testing source database
conn = sqlite3.connect('nsw_planning.db') # Source data
# Verification: PASSES (testing wrong system)

# CORRECT - Testing target database 
conn = psycopg2.connect(database='nsw_planning') # Production target
# Verification: FAILS (testing correct system)
```

#### **RULE 2B: End-to-End Integration Testing**
- **MANDATORY**: Test frontend API → PostgreSQL → Data return
- **MANDATORY**: Verify actual production data flow
- **FORBIDDEN**: Testing intermediate components in isolation
- **EXAMPLE**: `curl localhost:3007/api/setbacks/calculate` must return data

### **3. DEPENDENCY CHAIN VALIDATION (CRITICAL)**

#### **RULE 3A: Execution Environment Verification**
```bash
# MANDATORY: Check dependencies before claiming completion
python -c "import psycopg2; print('PostgreSQL Ready')"
./venv_linux/Scripts/python.exe -c "import psycopg2; print('Venv Ready')" 

# FORBIDDEN: Assuming dependencies are installed
# RESULT: "No module named 'psycopg2'" → Script never runs
```

#### **RULE 3B: Execution Confirmation**
- **MANDATORY**: Log actual execution with timestamps
- **MANDATORY**: Verify process completion with data counts 
- **FORBIDDEN**: Marking complete based on script existence
- **EXAMPLE**: Check `migrated_entries > 0` in migration_state.json

### **4. DATA FLOW TRACEABILITY (CRITICAL)**

#### **RULE 4A: Complete Data Pipeline Verification**
```bash
# MANDATORY VERIFICATION CHAIN:
1. Source data exists: SELECT COUNT(*) FROM sqlite.regulatory_provisions
2. Migration runs: python migration_engine.py → SUCCESS
3. Target data exists: SELECT COUNT(*) FROM postgres.authoritative.planning_provisions 
4. Frontend connects: curl API → returns actual data
5. No empty responses: No "No setback rules available" warnings
```

#### **RULE 4B: Multi-Layer Validation**
- **Database Layer**: PostgreSQL contains expected records
- **API Layer**: Endpoints return data not errors
- **Integration Layer**: Frontend displays actual regulatory data
- **User Layer**: Real property queries return setbacks

### **5. COMPLETION CRITERIA ENFORCEMENT (CRITICAL)**

#### **RULE 5A: Production-Ready Definition**
```bash
# COMPLETION CRITERIA - ALL MUST PASS:
 PostgreSQL authoritative.planning_provisions COUNT > 20,000
 Frontend API returns setback data for R2 zone
 No "No data available" warnings in production
 Migration success rate > 95%
 End-to-end property lookup works
```

#### **RULE 5B: False Positive Prevention**
- **FORBIDDEN**: Completion based on source data verification
- **FORBIDDEN**: Completion based on schema creation only 
- **FORBIDDEN**: Completion without frontend integration test
- **MANDATORY**: Production system must work end-to-end

### **6. SCHEMA EVOLUTION STRATEGY (ARCHITECTURAL)**

#### **RULE 6A: Backward Compatibility**
```sql
-- WRONG: Breaking schema changes
-- Old: zone TEXT
-- New: applicable_zones TEXT[] Incompatible

-- RIGHT: Compatible schema evolution 
-- Phase 1: Add new field alongside old
ALTER TABLE provisions ADD COLUMN applicable_zones TEXT[];
-- Phase 2: Populate new field from old 
UPDATE provisions SET applicable_zones = ARRAY[zone];
-- Phase 3: Update code to use new field
-- Phase 4: Remove old field after verification
```

#### **RULE 6B: Migration Testing Strategy**
- **Test with 100 records first**
- **Verify field mapping works correctly**
- **Check data type compatibility** 
- **Test constraint compliance**
- **Validate foreign key relationships**

### **7. ARCHITECTURAL PRINCIPLES (STRATEGIC)**

#### **RULE 7A: Single Source of Truth**
- **ONE production database** (PostgreSQL)
- **NO SQLite fallbacks** in production 
- **ALL verification tests target production database**
- **Frontend connects to production database only**

#### **RULE 7B: Environment Consistency**
- **Development mirrors production schema exactly**
- **Migration scripts tested in identical environment**
- **Dependencies managed in controlled virtual environment**
- **No "it works on my machine" acceptable**

### **8. FAILURE PREVENTION PROTOCOLS (OPERATIONAL)**

#### **RULE 8A: Pre-Migration Validation**
```bash
# MANDATORY PRE-FLIGHT CHECKS:
1. Target schema exists and is accessible
2. Source data is readable and complete 
3. Field mappings are explicitly defined
4. Sample migration (100 records) succeeds
5. Dependencies are installed and working
```

#### **RULE 8B: Migration Monitoring**
```bash
# MANDATORY DURING MIGRATION:
1. Real-time success/failure rate monitoring
2. Stop migration if failure rate > 5%
3. Log specific error messages (not just "0")
4. Verify target table row counts increase
5. Test API endpoints every 1000 records
```

#### **RULE 8C: Post-Migration Verification**
```bash 
# MANDATORY POST-MIGRATION:
1. Full data count verification: source vs target
2. Spot check 100 random records for accuracy
3. Frontend API integration test
4. Performance test with realistic queries
5. Rollback plan tested and ready
```

## IMPLEMENTATION CHECKLIST

### **For Every Future PRP:**
- [ ] **Schema compatibility verified with test migration**
- [ ] **All verification scripts target production database** 
- [ ] **Dependencies explicitly documented and tested**
- [ ] **End-to-end integration test defined**
- [ ] **Rollback procedure documented and tested**
- [ ] **Completion criteria include frontend working**
- [ ] **No completion markers until production proven**

### **For This Current Issue:**
- [ ] **Fix schema compatibility or mapping layer**
- [ ] **Rewrite verification scripts to target PostgreSQL**
- [ ] **Test migration with 100 records first** 
- [ ] **Verify frontend integration before completion**

## ENFORCEMENT MECHANISMS

### **PRP Approval Requirements:**
1. **Migration compatibility test** with sample data
2. **End-to-end integration test** specification
3. **Production database verification** script
4. **Rollback plan** with tested procedure
5. **Completion criteria** including frontend functionality

### **Completion Validation:**
- **Independent tester** must verify completion criteria
- **Production system** must demonstrate functionality
- **API endpoints** must return actual data
- **No exceptions** for "schema created" or "data exists in source"

---

**Following these practices will prevent the 4x migration failure clusterfuck from ever happening again.**