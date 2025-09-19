# PRP-8B CHUNK 2: Authoritative Data Migration with Tier Classification

**SESSION SCOPE**: Data migration only (Lines 224-528 from PRP-8B)  
**DURATION**: Single session (~45-60 minutes)  
**DEPENDENCIES**: CHUNK_1_SCHEMA_COMPLETE.marker must exist  
**ROLLBACK**: Truncate authoritative tables if any failures  

---

## 🎯 **SPECIFIC IMPLEMENTATION TARGET**

### **PRIMARY OBJECTIVE:**
Migrate all regulatory provisions from `public` schema to `authoritative` schema with proper 5-tier classification.

### **SCOPE BOUNDARIES:**
- ✅ **DO**: Migrate provisions, classify tiers, preserve original JSON, create authority mappings
- ❌ **DON'T**: Create schema (Chunk 1), build APIs (Chunk 3), create frontend (Chunk 4)
- ❌ **DON'T**: Import NSW property data (that's phase 2 of this chunk)

### **FILES TO REFERENCE:**
- `PRPs/PRP-8B_AUTHORITATIVE_COMPLIANCE_SYSTEM.md` (lines 224-528)
- `prp_checkpoints/CHUNK_1_SCHEMA_COMPLETE.marker` (dependency verification)

---

## 📋 **SUCCESS CRITERIA (BINARY VERIFICATION)**

### **Primary Success Metrics:**
1. **Data migrated**: `SELECT COUNT(*) FROM authoritative.planning_provisions` > 100
2. **Tiers classified**: `SELECT COUNT(*) FROM authoritative.provision_authority_tiers` > 100  
3. **Authority levels set**: `SELECT COUNT(DISTINCT authority_level) FROM authoritative.planning_provisions` >= 3
4. **Original JSON preserved**: `SELECT COUNT(*) FROM authoritative.planning_provisions WHERE original_json IS NOT NULL` > 0
5. **No data loss**: Source count = target count

### **Tier Distribution Expected:**
- **Tier 1** (SEPP): 10-20 provisions
- **Tier 2** (LEP + clear DCP): 80-120 provisions  
- **Tier 3** (DCP qualitative): 30-50 provisions
- **Tier 4** (Framework): 20-40 provisions
- **Tier 5** (Specialist): 5-15 provisions

---

## 🚨 **FAILURE ANTICIPATION & ERROR CHECKING**

### **Pre-Migration Dependency Checks:**
```python
import os
import json
import psycopg2

# Check 1: Chunk 1 completion marker
if not os.path.exists('prp_checkpoints/CHUNK_1_SCHEMA_COMPLETE.marker'):
    print("❌ FAILURE: CHUNK_1_SCHEMA_COMPLETE.marker not found")
    print("SOLUTION: Execute CHUNK 1 first")
    exit(1)

# Check 2: Verify schema exists
conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'authoritative'")
table_count = cur.fetchone()[0]
if table_count != 7:
    print(f"❌ FAILURE: Expected 7 authoritative tables, found {table_count}")
    print("SOLUTION: Re-run CHUNK 1 or verify schema creation")
    exit(1)

# Check 3: Source data availability
cur.execute("SELECT COUNT(*) FROM public.regulatory_provisions")
source_count = cur.fetchone()[0]
if source_count == 0:
    print("❌ FAILURE: No source data in public.regulatory_provisions")
    print("SOLUTION: Verify data migration from SQLite completed")
    exit(1)

print(f"✅ Pre-migration checks passed. Source data: {source_count} provisions")
```

### **During Migration Error Checks:**

#### **Error Check 1: Authority Level Classification**
```python
def determine_authority_level(document_id: str) -> tuple[int, str]:
    """Returns (authority_level, confidence_reason)"""
    doc_upper = document_id.upper()
    
    if 'STATE_ENVIRONMENTAL' in doc_upper or 'SEPP' in doc_upper:
        return 1, "SEPP document identified"
    elif 'LOCAL_ENVIRONMENTAL' in doc_upper or '_LEP_' in doc_upper:
        return 2, "LEP document identified"  
    elif 'DCP' in doc_upper or 'DEVELOPMENT_CONTROL' in doc_upper:
        return 3, "DCP document identified"
    else:
        return 4, f"Unclear authority from: {document_id[:50]}"

# Error checking during classification
def verify_authority_classification(provisions):
    """Verify authority level distribution makes sense"""
    
    levels = {}
    errors = []
    
    for prov in provisions:
        level = prov['authority_level']
        levels[level] = levels.get(level, 0) + 1
        
        # Error check: SEPP should be rare
        if level == 1 and levels[1] > 50:
            errors.append("❌ Too many SEPP provisions (>50) - check classification logic")
        
        # Error check: Most should be DCP (level 3)
        if level == 3 and len(provisions) > 100 and levels.get(3, 0) < len(provisions) * 0.3:
            errors.append("❌ Too few DCP provisions - check document_id patterns")
    
    return levels, errors
```

#### **Error Check 2: Data Integrity During Migration**
```python
def verify_migration_integrity(source_count, target_count, failed_count):
    """Check data integrity during migration"""
    
    errors = []
    
    # Check 1: No data loss
    if target_count + failed_count != source_count:
        errors.append(f"❌ Data loss detected: {source_count} source != {target_count + failed_count} processed")
    
    # Check 2: Reasonable success rate
    success_rate = target_count / source_count if source_count > 0 else 0
    if success_rate < 0.80:
        errors.append(f"❌ Low success rate: {success_rate:.1%} (expected >80%)")
    
    # Check 3: No complete failures
    if target_count == 0:
        errors.append("❌ Complete migration failure - no records migrated")
    
    return errors
```

#### **Error Check 3: Tier Classification Logic**
```python
def determine_tier(authority_level, has_numeric_value, provision_text):
    """Determine authority tier with error checking"""
    
    try:
        # Tier 1: Direct statutory values  
        if authority_level <= 2 and has_numeric_value:
            return 1, 1.00, "Statutory provision with numeric value"
        
        # Tier 2: Clear DCP measurements
        elif authority_level == 3 and has_numeric_value:
            return 2, 0.85, "DCP provision with clear measurement"
        
        # Tier 3: Qualitative provisions
        elif not has_numeric_value:
            confidence = 0.70 if len(provision_text) > 50 else 0.60
            return 3, confidence, "Qualitative provision requiring interpretation"
        
        # Tier 4: Framework guidance
        else:
            return 4, 0.60, "Framework guidance level"
            
    except Exception as e:
        # Error fallback
        return 5, 0.30, f"Classification error: {str(e)}"
```

### **Common Failure Scenarios & Diagnosis:**

#### **Failure Scenario 1: Foreign Key Constraint Violation**
```
ERROR: insert or update on table "provision_authority_tiers" violates foreign key constraint
DIAGNOSIS: Provision inserted into tiers table before main provisions table
SOLUTION: Fix insertion order - provisions first, then tiers
ROLLBACK: TRUNCATE authoritative.provision_authority_tiers, authoritative.planning_provisions CASCADE;
```

#### **Failure Scenario 2: JSON Serialization Error**
```
ERROR: invalid input syntax for type json
DIAGNOSIS: Python object not properly serialized to JSON
SOLUTION: Use json.dumps() with proper encoding
ROLLBACK: TRUNCATE affected table and restart migration
```

#### **Failure Scenario 3: Document ID Pattern Mismatch**
```
WARNING: 95% of provisions classified as authority_level 4 (unclear)
DIAGNOSIS: Document ID patterns don't match classification logic  
SOLUTION: Update authority classification patterns
ROLLBACK: TRUNCATE and re-run with fixed patterns
```

#### **Failure Scenario 4: Memory/Performance Issues**
```
ERROR: out of memory
DIAGNOSIS: Trying to migrate too many records at once
SOLUTION: Implement batch processing (1000 records at a time)
ROLLBACK: TRUNCATE and restart with batch processing
```

---

## 🔧 **IMPLEMENTATION PROCEDURE**

### **Step 1: Pre-flight Verification**
Execute dependency checks above. **STOP if any fail.**

### **Step 2: Create Migration Service**
Create file: `services/authoritative_migration_chunk2.py` based on PRP-8B lines 224-528.

### **Step 3: Batch Migration with Error Handling**
```python
class SafeMigration:
    def __init__(self):
        self.batch_size = 1000
        self.success_count = 0
        self.failure_count = 0
        self.errors = []
    
    def migrate_batch(self, batch):
        """Migrate batch with error isolation"""
        for provision in batch:
            try:
                # Migration logic here
                self.success_count += 1
            except Exception as e:
                self.failure_count += 1
                self.errors.append(f"Provision {provision.get('id')}: {str(e)}")
                
                # Stop if error rate too high
                if self.failure_count / (self.success_count + self.failure_count) > 0.20:
                    raise Exception("❌ Migration failure rate >20% - stopping")
```

### **Step 4: Real-time Verification During Migration**
```python
def verify_during_migration(self):
    """Check progress every 1000 records"""
    
    cur.execute("SELECT COUNT(*) FROM authoritative.planning_provisions")
    current_count = cur.fetchone()[0]
    
    cur.execute("""
        SELECT authority_level, COUNT(*) 
        FROM authoritative.planning_provisions 
        GROUP BY authority_level 
        ORDER BY authority_level
    """)
    
    distribution = dict(cur.fetchall())
    
    print(f"Progress: {current_count} provisions migrated")
    print(f"Distribution: {distribution}")
    
    # Error checks
    if distribution.get(4, 0) > current_count * 0.8:
        print("⚠️ WARNING: Too many unclear authorities - check patterns")
```

---

## 📊 **COMPLETION VERIFICATION**

### **Final Verification Script:**
```python
#!/usr/bin/env python3
"""
CHUNK 2 Comprehensive Verification
Tests all migration requirements
"""
import psycopg2
import json
from datetime import datetime

def verify_chunk2_completion():
    conn = psycopg2.connect(host='localhost', database='nsw_planning', user='postgres', password='postgres')
    cur = conn.cursor()
    
    tests = []
    errors = []
    
    # Test 1: Data migrated
    cur.execute("SELECT COUNT(*) FROM public.regulatory_provisions")
    source_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM authoritative.planning_provisions")
    target_count = cur.fetchone()[0]
    
    migration_rate = target_count / source_count if source_count > 0 else 0
    tests.append(('Data migrated', migration_rate >= 0.8, f'{migration_rate:.1%} migration rate'))
    
    # Test 2: Authority tiers created
    cur.execute("SELECT COUNT(*) FROM authoritative.provision_authority_tiers")
    tier_count = cur.fetchone()[0]
    tests.append(('Authority tiers', tier_count > 0, f'{tier_count} tiers created'))
    
    # Test 3: Authority level distribution
    cur.execute("""
        SELECT authority_level, COUNT(*) 
        FROM authoritative.planning_provisions 
        GROUP BY authority_level 
        ORDER BY authority_level
    """)
    
    distribution = dict(cur.fetchall())
    
    # Check reasonable distribution
    sepp_count = distribution.get(1, 0)
    lep_count = distribution.get(2, 0)  
    dcp_count = distribution.get(3, 0)
    unclear_count = distribution.get(4, 0) + distribution.get(5, 0)
    
    tests.append(('SEPP provisions', 5 <= sepp_count <= 50, f'{sepp_count} SEPP provisions'))
    tests.append(('LEP provisions', 10 <= lep_count <= 200, f'{lep_count} LEP provisions'))
    tests.append(('DCP provisions', dcp_count > 0, f'{dcp_count} DCP provisions'))
    tests.append(('Clear authorities', unclear_count < target_count * 0.5, f'{unclear_count} unclear authorities'))
    
    # Test 4: Original JSON preserved
    cur.execute("SELECT COUNT(*) FROM authoritative.planning_provisions WHERE original_json IS NOT NULL")
    json_count = cur.fetchone()[0]
    tests.append(('JSON preservation', json_count > 0, f'{json_count} provisions with JSON'))
    
    # Test 5: Tier confidence levels
    cur.execute("""
        SELECT tier_level, AVG(confidence_level), COUNT(*)
        FROM authoritative.provision_authority_tiers 
        GROUP BY tier_level 
        ORDER BY tier_level
    """)
    
    tier_confidence = cur.fetchall()
    for tier, avg_confidence, count in tier_confidence:
        expected_confidence = {1: 0.95, 2: 0.85, 3: 0.70, 4: 0.60, 5: 0.30}.get(tier, 0.50)
        tests.append((f'Tier {tier} confidence', avg_confidence >= expected_confidence - 0.1, 
                     f'Avg confidence: {avg_confidence:.2f}'))
    
    # Print results
    print('CHUNK 2 VERIFICATION RESULTS:')
    print('=' * 60)
    
    all_passed = True
    for test_name, passed, detail in tests:
        status = 'PASS' if passed else 'FAIL'
        print(f'{status:4} | {test_name:<25} | {detail}')
        if not passed:
            all_passed = False
    
    print('=' * 60)
    print(f'SOURCE DATA: {source_count} provisions')
    print(f'MIGRATED: {target_count} provisions ({migration_rate:.1%})')
    print(f'AUTHORITY DISTRIBUTION: {distribution}')
    print('=' * 60)
    
    if all_passed:
        print('✅ ALL TESTS PASSED - CHUNK 2 COMPLETE')
        
        # Create completion marker
        with open('prp_checkpoints/CHUNK_2_MIGRATION_COMPLETE.marker', 'w') as f:
            json.dump({
                'chunk': 'PRP-8B-CHUNK-2',
                'completed_at': datetime.now().isoformat(),
                'provisions_migrated': target_count,
                'migration_rate': f'{migration_rate:.1%}',
                'authority_distribution': distribution,
                'verification_passed': True,
                'next_chunk': 'CHUNK_3_HIERARCHY_API'
            }, f, indent=2)
            
        print('📄 Completion marker created: CHUNK_2_MIGRATION_COMPLETE.marker')
        
    else:
        print('❌ VERIFICATION FAILED - INVESTIGATE AND ROLLBACK')
        errors.append("Chunk 2 verification failed")
    
    conn.close()
    return all_passed, errors

if __name__ == "__main__":
    success, errors = verify_chunk2_completion()
    exit(0 if success else 1)
```

---

## 🔄 **ROLLBACK PROCEDURES**

### **Complete Rollback (Any Critical Failure):**
```sql
-- Remove all migrated data
TRUNCATE TABLE authoritative.provision_authority_tiers CASCADE;
TRUNCATE TABLE authoritative.property_provision_analysis CASCADE;  
TRUNCATE TABLE authoritative.planning_provisions CASCADE;
TRUNCATE TABLE authoritative.hierarchy_resolution_cache CASCADE;

-- Verify clean state
SELECT table_name, 
       (SELECT COUNT(*) FROM authoritative.|| table_name) as row_count
FROM information_schema.tables 
WHERE table_schema = 'authoritative' 
AND table_name IN ('planning_provisions', 'provision_authority_tiers');

-- Expected: All row_count = 0
```

### **Partial Rollback (Specific Issues):**
```sql
-- If only tier classification wrong:
TRUNCATE TABLE authoritative.provision_authority_tiers;
-- Re-run tier classification only

-- If authority levels wrong:
UPDATE authoritative.planning_provisions SET authority_level = NULL;
-- Re-run authority level classification
```

---

## 📁 **COMPLETION ARTIFACTS**

### **Files Created:**
- `services/authoritative_migration_chunk2.py` - Migration service
- `prp_checkpoints/CHUNK_2_MIGRATION_COMPLETE.marker` - Completion verification
- `logs/chunk2_migration_YYYYMMDD.log` - Migration execution log

### **Database Changes:**
- `authoritative.planning_provisions`: 100+ records with authority levels
- `authoritative.provision_authority_tiers`: Tier classifications
- Original JSON preserved in `original_json` column
- Authority hierarchy properly classified

### **Next Chunk Preparation:**
Upon completion, `CHUNK_3_HIERARCHY_API.md` can be executed to:
- Build HierarchyResolver service
- Create hierarchy resolution cache
- Implement authority override logic

---

## ⚠️ **CRITICAL SUCCESS FACTORS**

1. **Dependency Verification**: CHUNK_1_SCHEMA_COMPLETE.marker must exist
2. **Batch Processing**: Handle large datasets without memory issues  
3. **Error Isolation**: Single provision failures don't stop entire migration
4. **Authority Classification**: Reasonable distribution across authority levels
5. **Data Integrity**: Source count matches target count within tolerance
6. **Performance**: Complete migration in <60 minutes

<function_calls>
<invoke name="TodoWrite">
<parameter name="todos">[{"content": "Create PRP-8B implementation chunks with failure anticipation", "status": "completed", "activeForm": "Creating PRP-8B implementation chunks with failure anticipation"}, {"content": "Design 6 atomic chunks with rollback procedures", "status": "in_progress", "activeForm": "Designing 6 atomic chunks with rollback procedures"}, {"content": "Add comprehensive error checking and failure diagnosis", "status": "in_progress", "activeForm": "Adding comprehensive error checking and failure diagnosis"}]